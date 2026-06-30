"""End-to-end pipeline orchestration for Candidate Data Transformer."""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from candidate_data_transformer.matching import CandidateBlocker, MatchDecisionEngine, SimilarityScorer
from candidate_data_transformer.merging import ConfidenceCalculator, MergeEngine, MergePolicy, SourceConfidenceConfig
from candidate_data_transformer.normalizers import (
    CompanyNormalizer,
    DateNormalizer,
    EmailNormalizer,
    LocationNormalizer,
    NormalizationPipeline,
    PhoneNormalizer,
    SkillNormalizer,
    TitleNormalizer,
    WhitespaceNormalizer,
)
from candidate_data_transformer.parsers import create_parser
from candidate_data_transformer.projection import ProjectionEngine
from candidate_data_transformer.validator import SchemaValidator, ValidationReport

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    """Operational statistics for one pipeline run."""

    candidates_parsed: int = 0
    candidates_normalized: int = 0
    duplicates_found: int = 0
    merged_profiles: int = 0
    output_profiles: int = 0
    compared_pairs: int = 0
    possible_matches: int = 0
    execution_time_seconds: float = 0.0
    validation_errors: int = 0
    confidence_distribution: dict[str, int] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Complete result payload from a pipeline run."""

    parsed_candidates: list = field(default_factory=list)
    normalized_candidates: list = field(default_factory=list)
    merged_candidates: list = field(default_factory=list)
    projected_candidates: list[dict[str, Any]] = field(default_factory=list)
    validation_report: ValidationReport | None = None
    stats: PipelineStats = field(default_factory=PipelineStats)


class CandidatePipeline:
    """Coordinate parsing, normalization, matching, merging, validation, and projection."""

    def __init__(
        self,
        dataset_dir: str | Path = "datasets",
        config_dir: str | Path = "config",
        output_config_path: str | Path | None = None,
    ) -> None:
        self.dataset_dir = Path(dataset_dir)
        self.config_dir = Path(config_dir)
        self.output_config_path = Path(output_config_path) if output_config_path else self.config_dir / "output_config.json"

    def run(self, output_path: str | Path | None = None) -> PipelineResult:
        """Run the complete engineering pipeline."""

        start = time.perf_counter()
        logger.info("Starting complete candidate pipeline")
        parsed = self._parse_sources()
        normalized = self._build_normalization_pipeline().normalize_many(parsed)
        merge_engine = self._build_merge_engine()
        merged = merge_engine.merge(normalized)
        validation_report = SchemaValidator().validate_many(merged)
        projected = ProjectionEngine.from_config_file(self.output_config_path).project_many(merged)
        stats = self._build_stats(parsed, normalized, merged, projected, validation_report, merge_engine, start)
        result = PipelineResult(parsed, normalized, merged, projected, validation_report, stats)
        if output_path:
            self.save_projected_json(projected, output_path, stats)
        logger.info("Completed pipeline in %.2f seconds", stats.execution_time_seconds)
        return result

    def save_projected_json(self, projected: list[dict[str, Any]], output_path: str | Path, stats: PipelineStats) -> None:
        """Save projected candidates and run statistics as JSON."""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"stats": asdict(stats), "candidates": projected}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("Saved projected JSON to %s", path)

    def _parse_sources(self) -> list:
        """Parse all generated source datasets."""

        sources = {
            "recruiter": self.dataset_dir / "recruiter.csv",
            "ats": self.dataset_dir / "ats.json",
            "linkedin": self.dataset_dir / "linkedin",
            "resume": self.dataset_dir / "resume",
        }
        parsed = []
        for source_type, source_path in sources.items():
            parsed.extend(create_parser(source_type, source_path).parse())
        logger.info("Parsed %s total source records", len(parsed))
        return parsed

    def _build_normalization_pipeline(self) -> NormalizationPipeline:
        """Build normalization pipeline using runtime alias configs."""

        company_aliases = self._load_json(self.config_dir / "company_aliases.json", default={})
        skill_aliases = self._load_json(self.config_dir / "skill_aliases.json", default={})
        return NormalizationPipeline(
            [
                WhitespaceNormalizer(),
                EmailNormalizer(),
                PhoneNormalizer(),
                CompanyNormalizer(company_aliases),
                SkillNormalizer(skill_aliases),
                TitleNormalizer(),
                LocationNormalizer(),
                DateNormalizer(),
            ]
        )

    def _build_merge_engine(self) -> MergeEngine:
        """Build merge engine using matching and confidence configs."""

        matching_config = self._load_json(self.config_dir / "matching_config.json", default={})
        confidence_config = self._load_json(self.config_dir / "confidence_config.json", default={})
        source_scores = confidence_config.get("source_confidence", {})
        confidence_calculator = ConfidenceCalculator(SourceConfidenceConfig(scores=source_scores)) if source_scores else ConfidenceCalculator()
        merge_policy = MergePolicy(confidence_calculator=confidence_calculator)
        return MergeEngine(
            blocker=CandidateBlocker(),
            similarity_scorer=SimilarityScorer(matching_config.get("similarity_weights")),
            decision_engine=MatchDecisionEngine(
                match_threshold=matching_config.get("match_threshold", 0.85),
                possible_match_threshold=matching_config.get("possible_match_threshold", 0.65),
            ),
            merge_policy=merge_policy,
        )

    def _build_stats(
        self,
        parsed: list,
        normalized: list,
        merged: list,
        projected: list[dict[str, Any]],
        validation_report: ValidationReport,
        merge_engine: MergeEngine,
        start: float,
    ) -> PipelineStats:
        """Build run statistics."""

        merged_profiles = merge_engine.last_run_metadata.merged_profiles
        return PipelineStats(
            candidates_parsed=len(parsed),
            candidates_normalized=len(normalized),
            duplicates_found=merged_profiles,
            merged_profiles=merged_profiles,
            output_profiles=len(projected),
            compared_pairs=merge_engine.last_run_metadata.compared_pairs,
            possible_matches=len(merge_engine.last_run_metadata.possible_matches),
            execution_time_seconds=round(time.perf_counter() - start, 4),
            validation_errors=validation_report.invalid_count,
            confidence_distribution=self._confidence_distribution(merged),
        )

    def _confidence_distribution(self, merged: list) -> dict[str, int]:
        """Bucket overall confidence scores for dashboard display."""

        buckets = {"high": 0, "medium": 0, "low": 0, "missing": 0}
        for candidate in merged:
            score = candidate.confidence.get("overall")
            if score is None:
                buckets["missing"] += 1
            elif score >= 0.90:
                buckets["high"] += 1
            elif score >= 0.75:
                buckets["medium"] += 1
            else:
                buckets["low"] += 1
        return buckets

    def _load_json(self, path: Path, default: Any) -> Any:
        """Load optional JSON config with a safe default."""

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.warning("Config file not found: %s", path)
            return default
        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON config %s: %s", path, exc)
            return default


def configure_logging(log_path: str | Path = "logs/pipeline.log") -> None:
    """Configure console and file logging for the project."""

    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
    root.addHandler(file_handler)
    root.addHandler(console_handler)
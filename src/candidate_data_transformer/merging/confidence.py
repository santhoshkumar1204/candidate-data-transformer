"""Confidence scoring utilities for merged candidate profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from candidate_data_transformer.models import CanonicalCandidate


@dataclass(frozen=True)
class SourceConfidenceConfig:
    """Configurable source-level confidence defaults."""

    scores: dict[str, float] = field(
        default_factory=lambda: {
            "recruiter": 0.95,
            "resume": 0.92,
            "ats": 0.90,
            "linkedin": 0.80,
            "merged": 1.0,
        }
    )


class ConfidenceCalculator:
    """Calculate field and profile confidence for merged candidates."""

    def __init__(self, config: SourceConfidenceConfig | None = None) -> None:
        self.config = config or SourceConfidenceConfig()

    def source_confidence(self, candidate: CanonicalCandidate) -> float:
        """Return configured confidence for a candidate source."""

        return self.config.scores.get(candidate.source, 0.70)

    def field_confidence(
        self,
        contributors: list[CanonicalCandidate],
        agreement_count: int,
        non_empty_count: int,
        value: Any,
    ) -> float:
        """Score a merged field using source confidence, agreement, and completeness."""

        if self._is_empty(value) or not contributors:
            return 0.0
        source_score = max(self.source_confidence(candidate) for candidate in contributors)
        agreement_ratio = agreement_count / non_empty_count if non_empty_count else 0.0
        agreement_bonus = min(0.08, max(0, agreement_count - 1) * 0.03)
        confidence = (source_score * 0.75) + (agreement_ratio * 0.20) + agreement_bonus
        return round(min(confidence, 1.0), 4)

    def profile_confidence(self, field_confidences: dict[str, float]) -> float:
        """Calculate final merged profile confidence from available fields."""

        populated = [score for score in field_confidences.values() if score > 0]
        if not populated:
            return 0.0
        completeness = len(populated) / max(len(field_confidences), 1)
        score = (sum(populated) / len(populated) * 0.85) + (completeness * 0.15)
        return round(min(score, 1.0), 4)

    def _is_empty(self, value: Any) -> bool:
        """Return true when a value should not contribute confidence."""

        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, (list, dict, set, tuple)):
            return len(value) == 0
        return False
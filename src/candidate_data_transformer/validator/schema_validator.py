"""Schema validation for final merged candidates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from candidate_data_transformer.models import CanonicalCandidate


@dataclass(frozen=True)
class CandidateValidationError:
    """Validation error for one candidate profile."""

    candidate_id: str | None
    index: int
    errors: list[dict[str, Any]]


@dataclass
class ValidationReport:
    """Validation report for a batch of merged candidates."""

    valid_count: int = 0
    invalid_count: int = 0
    errors: list[CandidateValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Return true when every profile passed validation."""

        return self.invalid_count == 0


class SchemaValidator:
    """Validate merged candidates without stopping the entire pipeline."""

    def validate_many(self, candidates: list[CanonicalCandidate | dict[str, Any]]) -> ValidationReport:
        """Validate a batch of merged candidate profiles."""

        report = ValidationReport()
        for index, candidate in enumerate(candidates):
            error = self.validate_one(candidate, index)
            if error:
                report.invalid_count += 1
                report.errors.append(error)
            else:
                report.valid_count += 1
        return report

    def validate_one(self, candidate: CanonicalCandidate | dict[str, Any], index: int = 0) -> CandidateValidationError | None:
        """Validate one merged candidate and return an error record when invalid."""

        try:
            model = candidate if isinstance(candidate, CanonicalCandidate) else CanonicalCandidate.model_validate(candidate)
            semantic_errors = self._semantic_errors(model)
            if semantic_errors:
                return CandidateValidationError(model.candidate_id, index, semantic_errors)
            return None
        except ValidationError as exc:
            candidate_id = candidate.get("candidate_id") if isinstance(candidate, dict) else None
            return CandidateValidationError(candidate_id, index, exc.errors())

    def _semantic_errors(self, candidate: CanonicalCandidate) -> list[dict[str, Any]]:
        """Run lightweight semantic validation for merged outputs."""

        errors: list[dict[str, Any]] = []
        if candidate.source != "merged":
            errors.append({"field": "source", "message": "Final profile source must be 'merged'."})
        if not candidate.candidate_id:
            errors.append({"field": "candidate_id", "message": "Merged profile must have a candidate_id."})
        overall = candidate.confidence.get("overall")
        if overall is not None and not 0 <= overall <= 1:
            errors.append({"field": "confidence.overall", "message": "Overall confidence must be between 0 and 1."})
        if not candidate.provenance:
            errors.append({"field": "provenance", "message": "Merged profile must include field provenance."})
        return errors
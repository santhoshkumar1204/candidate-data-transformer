"""Deterministic merge policy for matched candidate groups."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from candidate_data_transformer.merging.confidence import ConfidenceCalculator
from candidate_data_transformer.merging.provenance import ProvenanceTracker
from candidate_data_transformer.models import CanonicalCandidate, Education, Experience, Location


@dataclass(frozen=True)
class SelectedValue:
    """A selected merged value and its explanation context."""

    value: Any
    contributors: list[CanonicalCandidate]
    agreement_count: int
    non_empty_count: int
    reason: str


class MergePolicy:
    """Choose deterministic field values for matched candidates."""

    LIST_FIELDS = ("emails", "phones", "skills", "certifications", "projects")
    SCALAR_FIELDS = ("full_name", "current_company", "current_title", "linkedin_url", "github_url")

    def __init__(
        self,
        confidence_calculator: ConfidenceCalculator | None = None,
        provenance_tracker: ProvenanceTracker | None = None,
    ) -> None:
        self.confidence_calculator = confidence_calculator or ConfidenceCalculator()
        self.provenance_tracker = provenance_tracker or ProvenanceTracker()

    def merge(self, candidates: list[CanonicalCandidate], merged_id: str) -> CanonicalCandidate:
        """Merge a matched candidate group into one canonical candidate."""

        if not candidates:
            raise ValueError("Cannot merge an empty candidate group")

        data: dict[str, Any] = {
            "candidate_id": merged_id,
            "source": "merged",
            "raw_record": {
                "source_records": [self._source_record_summary(candidate) for candidate in candidates],
            },
            "metadata": {
                "merged_from_candidate_ids": [candidate.candidate_id for candidate in candidates],
                "merged_from_sources": [candidate.source for candidate in candidates],
                "source_record_count": len(candidates),
            },
        }
        provenance: dict[str, Any] = {}
        confidence: dict[str, float] = {}

        for field_name in self.SCALAR_FIELDS:
            selected = self._select_scalar(candidates, field_name)
            data[field_name] = selected.value
            self._record_field(field_name, selected, provenance, confidence)

        for field_name in self.LIST_FIELDS:
            selected = self._merge_list(candidates, field_name)
            data[field_name] = selected.value
            self._record_field(field_name, selected, provenance, confidence)

        data["education"] = self._merge_education(candidates, provenance, confidence)
        data["experience"] = self._merge_experience(candidates, provenance, confidence)
        data["location"] = self._merge_location(candidates, provenance, confidence)

        data["confidence"] = confidence
        data["confidence"]["overall"] = self.confidence_calculator.profile_confidence(confidence)
        data["provenance"] = provenance
        data["merge_metadata"] = {
            "merge_strategy": "deterministic_field_policy",
            "merged_profile_count": len(candidates),
        }
        return CanonicalCandidate.model_validate(data)

    def _select_scalar(self, candidates: list[CanonicalCandidate], field_name: str) -> SelectedValue:
        """Select the best scalar value by confidence, agreement, and descriptiveness."""

        values = [(candidate, getattr(candidate, field_name)) for candidate in candidates]
        non_empty = [(candidate, value) for candidate, value in values if not self._is_empty(value)]
        if not non_empty:
            return SelectedValue(None, [], 0, 0, "No non-empty source value")

        grouped: dict[str, list[tuple[CanonicalCandidate, Any]]] = {}
        for candidate, value in non_empty:
            grouped.setdefault(self._value_key(value), []).append((candidate, value))

        best_group = max(
            grouped.values(),
            key=lambda group: (
                len(group),
                max(self.confidence_calculator.source_confidence(candidate) for candidate, _ in group),
                max(self._descriptive_length(value) for _, value in group),
            ),
        )
        best_candidate, best_value = max(
            best_group,
            key=lambda item: (
                self.confidence_calculator.source_confidence(item[0]),
                self._descriptive_length(item[1]),
            ),
        )
        reason = "Highest confidence exact agreement" if len(best_group) > 1 else "Highest confidence non-empty value"
        return SelectedValue(
            value=best_value,
            contributors=[candidate for candidate, _ in best_group],
            agreement_count=len(best_group),
            non_empty_count=len(non_empty),
            reason=reason,
        )

    def _merge_list(self, candidates: list[CanonicalCandidate], field_name: str) -> SelectedValue:
        """Merge list fields as deterministic unions without inventing values."""

        values: list[str] = []
        contributors: list[CanonicalCandidate] = []
        for candidate in candidates:
            field_values = getattr(candidate, field_name)
            if not field_values:
                continue
            contributors.append(candidate)
            values.extend(field_values)
        merged = sorted(self._unique(values), key=str.casefold)
        return SelectedValue(
            value=merged,
            contributors=contributors,
            agreement_count=len(contributors),
            non_empty_count=len(contributors),
            reason="Union of non-empty source values",
        )

    def _merge_education(
        self,
        candidates: list[CanonicalCandidate],
        provenance: dict[str, Any],
        confidence: dict[str, float],
    ) -> Education | None:
        """Merge education fields individually."""

        values = {}
        for field_name in ("highest_degree", "university", "graduation_year", "raw_text"):
            selected = self._select_nested_scalar(candidates, "education", field_name)
            values[field_name] = selected.value
            self._record_field(f"education.{field_name}", selected, provenance, confidence)
        return Education(**values) if any(not self._is_empty(value) for value in values.values()) else None

    def _merge_experience(
        self,
        candidates: list[CanonicalCandidate],
        provenance: dict[str, Any],
        confidence: dict[str, float],
    ) -> Experience | None:
        """Merge experience fields individually."""

        years = self._select_nested_scalar(candidates, "experience", "years")
        summary = self._select_nested_scalar(candidates, "experience", "summary")
        entries = self._merge_nested_list(candidates, "experience", "entries")
        self._record_field("experience.years", years, provenance, confidence)
        self._record_field("experience.summary", summary, provenance, confidence)
        self._record_field("experience.entries", entries, provenance, confidence)
        if self._is_empty(years.value) and self._is_empty(summary.value) and self._is_empty(entries.value):
            return None
        return Experience(years=years.value, summary=summary.value, entries=entries.value)

    def _merge_location(
        self,
        candidates: list[CanonicalCandidate],
        provenance: dict[str, Any],
        confidence: dict[str, float],
    ) -> Location | None:
        """Merge location fields individually."""

        values = {}
        for field_name in ("current", "preferred", "raw_text"):
            selected = self._select_nested_scalar(candidates, "location", field_name)
            values[field_name] = selected.value
            self._record_field(f"location.{field_name}", selected, provenance, confidence)
        return Location(**values) if any(not self._is_empty(value) for value in values.values()) else None

    def _select_nested_scalar(self, candidates: list[CanonicalCandidate], object_name: str, field_name: str) -> SelectedValue:
        """Select the best scalar value from a nested object."""

        proxy_candidates: list[tuple[CanonicalCandidate, Any]] = []
        for candidate in candidates:
            nested = getattr(candidate, object_name)
            value = getattr(nested, field_name) if nested else None
            proxy_candidates.append((candidate, value))
        return self._select_from_pairs(proxy_candidates)

    def _merge_nested_list(self, candidates: list[CanonicalCandidate], object_name: str, field_name: str) -> SelectedValue:
        """Merge list values from a nested object."""

        values: list[str] = []
        contributors: list[CanonicalCandidate] = []
        for candidate in candidates:
            nested = getattr(candidate, object_name)
            field_values = getattr(nested, field_name) if nested else []
            if not field_values:
                continue
            contributors.append(candidate)
            values.extend(field_values)
        merged = sorted(self._unique(values), key=str.casefold)
        return SelectedValue(merged, contributors, len(contributors), len(contributors), "Union of non-empty source values")

    def _select_from_pairs(self, pairs: list[tuple[CanonicalCandidate, Any]]) -> SelectedValue:
        """Select the best value from candidate/value pairs."""

        non_empty = [(candidate, value) for candidate, value in pairs if not self._is_empty(value)]
        if not non_empty:
            return SelectedValue(None, [], 0, 0, "No non-empty source value")
        grouped: dict[str, list[tuple[CanonicalCandidate, Any]]] = {}
        for candidate, value in non_empty:
            grouped.setdefault(self._value_key(value), []).append((candidate, value))
        best_group = max(
            grouped.values(),
            key=lambda group: (
                len(group),
                max(self.confidence_calculator.source_confidence(candidate) for candidate, _ in group),
                max(self._descriptive_length(value) for _, value in group),
            ),
        )
        best_candidate, best_value = max(
            best_group,
            key=lambda item: (
                self.confidence_calculator.source_confidence(item[0]),
                self._descriptive_length(item[1]),
            ),
        )
        reason = "Highest confidence exact agreement" if len(best_group) > 1 else "Highest confidence non-empty value"
        return SelectedValue(best_value, [candidate for candidate, _ in best_group], len(best_group), len(non_empty), reason)

    def _record_field(
        self,
        field_name: str,
        selected: SelectedValue,
        provenance: dict[str, Any],
        confidence: dict[str, float],
    ) -> None:
        """Record confidence and provenance for a selected field."""

        field_confidence = self.confidence_calculator.field_confidence(
            selected.contributors,
            selected.agreement_count,
            selected.non_empty_count,
            selected.value,
        )
        confidence[field_name] = field_confidence
        provenance[field_name] = self.provenance_tracker.build(
            value=self._serializable_value(selected.value),
            contributors=selected.contributors,
            confidence=field_confidence,
            merge_reason=selected.reason,
        )

    def _unique(self, values: list[str]) -> list[str]:
        """Return unique non-empty string values preserving first-seen casing."""

        output: list[str] = []
        seen: set[str] = set()
        for value in values:
            if self._is_empty(value):
                continue
            key = self._value_key(value)
            if key not in seen:
                output.append(str(value).strip())
                seen.add(key)
        return output

    def _source_record_summary(self, candidate: CanonicalCandidate) -> dict[str, Any]:
        """Summarize source records without flattening raw payloads into the merge."""

        return {
            "candidate_id": candidate.candidate_id,
            "source": candidate.source,
            "metadata": candidate.metadata,
        }

    def _value_key(self, value: Any) -> str:
        """Build a stable comparison key for values."""

        if isinstance(value, str):
            return re.sub(r"\s+", " ", value.casefold()).strip()
        return str(value).casefold()

    def _descriptive_length(self, value: Any) -> int:
        """Return a length signal used as a deterministic tiebreaker."""

        if isinstance(value, str):
            return len(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return len(value)
        return 0

    def _serializable_value(self, value: Any) -> Any:
        """Convert model values to serializable provenance payloads."""

        if isinstance(value, BaseModel):
            return value.model_dump()
        return value

    def _is_empty(self, value: Any) -> bool:
        """Return true for missing merge values."""

        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) == 0
        return False
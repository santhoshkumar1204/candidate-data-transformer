"""Provenance records for merged candidate fields."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from candidate_data_transformer.models import CanonicalCandidate


class FieldProvenance(BaseModel):
    """Explanation for a merged field value."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    value: Any = None
    sources: list[str] = Field(default_factory=list)
    source_candidate_ids: list[str | None] = Field(default_factory=list)
    confidence: float = 0.0
    merge_reason: str


class ProvenanceTracker:
    """Build provenance payloads for merged fields."""

    def build(
        self,
        value: Any,
        contributors: list[CanonicalCandidate],
        confidence: float,
        merge_reason: str,
    ) -> dict[str, Any]:
        """Create a serializable provenance record."""

        record = FieldProvenance(
            value=value,
            sources=[candidate.source for candidate in contributors],
            source_candidate_ids=[candidate.candidate_id for candidate in contributors],
            confidence=confidence,
            merge_reason=merge_reason,
        )
        return record.model_dump()
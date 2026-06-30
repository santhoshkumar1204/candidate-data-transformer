"""Base abstractions and shared helpers for candidate normalization."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from candidate_data_transformer.models import CanonicalCandidate


class BaseNormalizer(ABC):
    """Abstract normalizer contract for candidate transformations."""

    name: str

    @abstractmethod
    def normalize(self, candidate: CanonicalCandidate) -> CanonicalCandidate:
        """Return a normalized candidate."""

    def log_info(self, message: str) -> None:
        """Log an informational normalizer message."""

        import logging

        logging.getLogger(__name__).info(message)

    @staticmethod
    def copy_candidate(candidate: CanonicalCandidate) -> CanonicalCandidate:
        """Create a safe copy before applying a transformation."""

        return candidate.model_copy(deep=True)

    @staticmethod
    def unique_preserve_order(values: Iterable[str]) -> list[str]:
        """Remove duplicate strings while preserving first-seen order."""

        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = value.strip()
            if not text:
                continue
            key = text.casefold()
            if key not in seen:
                normalized.append(text)
                seen.add(key)
        return normalized
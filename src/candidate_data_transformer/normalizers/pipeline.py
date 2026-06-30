"""Composable normalization pipeline."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from candidate_data_transformer.models import CanonicalCandidate
from candidate_data_transformer.normalizers.base import BaseNormalizer

logger = logging.getLogger(__name__)


class NormalizationPipeline:
    """Run reusable normalizers sequentially over canonical candidates."""

    def __init__(self, normalizers: Sequence[BaseNormalizer] | None = None) -> None:
        self.normalizers = list(normalizers or [])

    def add(self, normalizer: BaseNormalizer) -> None:
        """Append a normalizer to the pipeline."""

        self.normalizers.append(normalizer)

    def normalize(self, candidate: CanonicalCandidate) -> CanonicalCandidate:
        """Normalize a single candidate by applying each transformer in order."""

        normalized = candidate
        for normalizer in self.normalizers:
            normalized = normalizer.normalize(normalized)
        return normalized

    def normalize_many(self, candidates: Sequence[CanonicalCandidate]) -> list[CanonicalCandidate]:
        """Normalize multiple candidates."""

        logger.info("Normalizing %s candidates", len(candidates))
        normalized_candidates = list(candidates)
        for normalizer in self.normalizers:
            logger.info("Running %s", normalizer.__class__.__name__)
            normalized_candidates = [normalizer.normalize(candidate) for candidate in normalized_candidates]
        return normalized_candidates
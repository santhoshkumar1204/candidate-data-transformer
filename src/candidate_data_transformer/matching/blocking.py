"""Candidate blocking for efficient identity resolution."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from itertools import combinations

from candidate_data_transformer.models import CanonicalCandidate

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CandidateBlock:
    """A deterministic group of candidate indexes that share a blocking key."""

    key: str
    candidate_indexes: tuple[int, ...]


class CandidateBlocker:
    """Create deterministic comparison groups without all-pairs matching."""

    def block(self, candidates: list[CanonicalCandidate]) -> list[CandidateBlock]:
        """Group candidates by email, phone, LinkedIn, GitHub, and last name keys."""

        key_to_indexes: dict[str, set[int]] = {}
        for index, candidate in enumerate(candidates):
            for key in self.blocking_keys(candidate):
                key_to_indexes.setdefault(key, set()).add(index)

        blocks = [
            CandidateBlock(key=key, candidate_indexes=tuple(sorted(indexes)))
            for key, indexes in sorted(key_to_indexes.items())
            if len(indexes) > 1
        ]
        logger.info("Blocked %s candidates into %s groups", len(candidates), len(blocks))
        return blocks

    def comparison_pairs(self, candidates: list[CanonicalCandidate]) -> set[tuple[int, int]]:
        """Return unique candidate index pairs implied by blocking groups."""

        pairs: set[tuple[int, int]] = set()
        for block in self.block(candidates):
            for left, right in combinations(block.candidate_indexes, 2):
                pairs.add((left, right))
        logger.info("Compared %s pairs", len(pairs))
        return pairs

    def blocking_keys(self, candidate: CanonicalCandidate) -> set[str]:
        """Build blocking keys for a candidate."""

        keys: set[str] = set()
        keys.update(f"email:{email.casefold()}" for email in candidate.emails)
        keys.update(f"phone:{phone}" for phone in candidate.phones)
        if candidate.linkedin_url:
            keys.add(f"linkedin:{candidate.linkedin_url.casefold()}")
        if candidate.github_url:
            keys.add(f"github:{candidate.github_url.casefold()}")
        last_name = self._last_name(candidate.full_name)
        if last_name:
            keys.add(f"last_name:{last_name}")
        return keys

    def _last_name(self, full_name: str | None) -> str | None:
        """Extract a normalized last-name blocking key."""

        if not full_name:
            return None
        tokens = re.findall(r"[a-zA-Z]+", full_name.casefold())
        return tokens[-1] if tokens else None
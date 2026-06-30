"""Merge engine orchestration for identity-resolved candidates."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from candidate_data_transformer.matching import CandidateBlocker, MatchDecision, MatchDecisionEngine, SimilarityScorer
from candidate_data_transformer.matching.decision import MatchDecisionResult
from candidate_data_transformer.merging.merge_policy import MergePolicy
from candidate_data_transformer.models import CanonicalCandidate

logger = logging.getLogger(__name__)


@dataclass
class MergeResultMetadata:
    """Operational metadata produced by the merge engine."""

    input_count: int = 0
    compared_pairs: int = 0
    merged_profiles: int = 0
    possible_matches: list[dict] = field(default_factory=list)


class _DisjointSet:
    """Small union-find implementation for matched candidate components."""

    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        """Find the representative for an item."""

        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: int, right: int) -> None:
        """Union two components."""

        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            self.parent[left_root] = right_root
        elif self.rank[left_root] > self.rank[right_root]:
            self.parent[right_root] = left_root
        else:
            self.parent[right_root] = left_root
            self.rank[left_root] += 1


class MergeEngine:
    """Resolve identities and merge only candidates classified as MATCH."""

    def __init__(
        self,
        blocker: CandidateBlocker | None = None,
        similarity_scorer: SimilarityScorer | None = None,
        decision_engine: MatchDecisionEngine | None = None,
        merge_policy: MergePolicy | None = None,
    ) -> None:
        self.blocker = blocker or CandidateBlocker()
        self.similarity_scorer = similarity_scorer or SimilarityScorer()
        self.decision_engine = decision_engine or MatchDecisionEngine()
        self.merge_policy = merge_policy or MergePolicy()
        self.last_run_metadata = MergeResultMetadata()

    def merge(self, candidates: list[CanonicalCandidate]) -> list[CanonicalCandidate]:
        """Run blocking, similarity, decision, merge, confidence, and provenance."""

        if not candidates:
            self.last_run_metadata = MergeResultMetadata()
            return []

        pairs = self.blocker.comparison_pairs(candidates)
        disjoint_set = _DisjointSet(len(candidates))
        possible_matches: list[dict] = []

        for left_index, right_index in sorted(pairs):
            scores = self.similarity_scorer.score(candidates[left_index], candidates[right_index])
            decision = self.decision_engine.decide(scores)
            if decision.decision == MatchDecision.MATCH:
                disjoint_set.union(left_index, right_index)
            elif decision.decision == MatchDecision.POSSIBLE_MATCH:
                possible_matches.append(self._possible_match_payload(left_index, right_index, decision, candidates))

        components = self._components(disjoint_set, len(candidates))
        merged = [
            self.merge_policy.merge(
                [candidates[index] for index in indexes],
                self._merged_id(group_number, indexes, candidates),
            )
            for group_number, indexes in enumerate(components, start=1)
        ]

        merged_profile_count = sum(1 for indexes in components if len(indexes) > 1)
        for candidate in merged:
            candidate.merge_metadata["possible_match_count"] = len(possible_matches)
        self.last_run_metadata = MergeResultMetadata(
            input_count=len(candidates),
            compared_pairs=len(pairs),
            merged_profiles=merged_profile_count,
            possible_matches=possible_matches,
        )
        logger.info("Merged %s profiles", merged_profile_count)
        logger.info("Skipped %s possible matches", len(possible_matches))
        return merged

    def _components(self, disjoint_set: _DisjointSet, size: int) -> list[list[int]]:
        """Return deterministic connected components."""

        groups: dict[int, list[int]] = {}
        for index in range(size):
            groups.setdefault(disjoint_set.find(index), []).append(index)
        return sorted((sorted(indexes) for indexes in groups.values()), key=lambda indexes: indexes[0])

    def _merged_id(self, group_number: int, indexes: list[int], candidates: list[CanonicalCandidate]) -> str:
        """Create a deterministic merged candidate ID."""

        source_ids = [candidates[index].candidate_id for index in indexes if candidates[index].candidate_id]
        if len(source_ids) == 1:
            return f"MERGED-{source_ids[0]}"
        return f"MERGED-{group_number:05d}"

    def _possible_match_payload(
        self,
        left_index: int,
        right_index: int,
        decision: MatchDecisionResult,
        candidates: list[CanonicalCandidate],
    ) -> dict:
        """Build metadata for a possible match that was not automatically merged."""

        return {
            "left_index": left_index,
            "right_index": right_index,
            "left_candidate_id": candidates[left_index].candidate_id,
            "right_candidate_id": candidates[right_index].candidate_id,
            "score": decision.score,
            "reason": decision.reason,
            "score_breakdown": self._score_breakdown(decision),
        }

    def _score_breakdown(self, decision: MatchDecisionResult) -> dict:
        """Return a serializable similarity score breakdown."""

        scores = decision.scores
        return {
            "total_score": scores.total_score,
            "exact_email": scores.exact_email,
            "exact_phone": scores.exact_phone,
            "exact_linkedin": scores.exact_linkedin,
            "exact_github": scores.exact_github,
            "name_similarity": scores.name_similarity,
            "company_similarity": scores.company_similarity,
            "skills_overlap": scores.skills_overlap,
            "location_match": scores.location_match,
            "education_overlap": scores.education_overlap,
            "details": scores.details,
        }
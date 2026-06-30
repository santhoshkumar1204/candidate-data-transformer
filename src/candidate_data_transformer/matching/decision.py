"""Match decision policy for identity resolution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from candidate_data_transformer.matching.similarity import SimilarityScores


class MatchDecision(str, Enum):
    """Supported identity match outcomes."""

    MATCH = "MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    NO_MATCH = "NO_MATCH"


@dataclass(frozen=True)
class MatchDecisionResult:
    """Decision outcome with score and explanation."""

    decision: MatchDecision
    score: float
    reason: str
    scores: SimilarityScores


class MatchDecisionEngine:
    """Convert similarity scores into match decisions."""

    def __init__(self, match_threshold: float = 0.85, possible_match_threshold: float = 0.65) -> None:
        if possible_match_threshold > match_threshold:
            raise ValueError("possible_match_threshold cannot exceed match_threshold")
        self.match_threshold = match_threshold
        self.possible_match_threshold = possible_match_threshold

    def decide(self, scores: SimilarityScores) -> MatchDecisionResult:
        """Return MATCH, POSSIBLE_MATCH, or NO_MATCH for a score set."""

        if scores.has_exact_identifier:
            return MatchDecisionResult(
                decision=MatchDecision.MATCH,
                score=max(scores.total_score, 1.0),
                reason="Strong exact identifier matched",
                scores=scores,
            )
        if scores.total_score >= self.match_threshold:
            return MatchDecisionResult(
                decision=MatchDecision.MATCH,
                score=scores.total_score,
                reason="Similarity score met match threshold",
                scores=scores,
            )
        if scores.total_score >= self.possible_match_threshold:
            return MatchDecisionResult(
                decision=MatchDecision.POSSIBLE_MATCH,
                score=scores.total_score,
                reason="Similarity score met possible-match threshold",
                scores=scores,
            )
        return MatchDecisionResult(
            decision=MatchDecision.NO_MATCH,
            score=scores.total_score,
            reason="Similarity score below threshold",
            scores=scores,
        )
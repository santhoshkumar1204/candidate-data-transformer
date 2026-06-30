"""Identity matching components."""

from candidate_data_transformer.matching.blocking import CandidateBlock, CandidateBlocker
from candidate_data_transformer.matching.decision import MatchDecision, MatchDecisionEngine, MatchDecisionResult
from candidate_data_transformer.matching.similarity import SimilarityScorer, SimilarityScores

__all__ = [
    "CandidateBlock",
    "CandidateBlocker",
    "MatchDecision",
    "MatchDecisionEngine",
    "MatchDecisionResult",
    "SimilarityScorer",
    "SimilarityScores",
]
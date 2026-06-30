from candidate_data_transformer.matching import CandidateBlocker, MatchDecision, MatchDecisionEngine, SimilarityScorer
from candidate_data_transformer.models import CanonicalCandidate


def test_blocking_and_similarity_detect_exact_email_match():
    left = CanonicalCandidate(source="recruiter", candidate_id="A", full_name="Priya Rao", emails=["p@example.com"])
    right = CanonicalCandidate(source="ats", candidate_id="B", full_name="Priya R", emails=["p@example.com"])

    pairs = CandidateBlocker().comparison_pairs([left, right])
    scores = SimilarityScorer().score(left, right)
    decision = MatchDecisionEngine().decide(scores)

    assert pairs == {(0, 1)}
    assert scores.exact_email == 1.0
    assert decision.decision == MatchDecision.MATCH
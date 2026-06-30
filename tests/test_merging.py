from candidate_data_transformer.merging import ConfidenceCalculator, MergeEngine
from candidate_data_transformer.models import CanonicalCandidate


def test_merge_engine_merges_confirmed_matches_with_provenance():
    candidates = [
        CanonicalCandidate(source="recruiter", candidate_id="A", full_name="Priya Rao", emails=["p@example.com"], current_company="Google"),
        CanonicalCandidate(source="ats", candidate_id="B", full_name="Priya Rao", emails=["p@example.com"], current_company="Google"),
    ]

    merged = MergeEngine().merge(candidates)

    assert len(merged) == 1
    assert merged[0].source == "merged"
    assert merged[0].current_company == "Google"
    assert "current_company" in merged[0].provenance
    assert merged[0].confidence["overall"] > 0


def test_confidence_calculator_scores_agreement():
    candidates = [CanonicalCandidate(source="recruiter"), CanonicalCandidate(source="ats")]

    score = ConfidenceCalculator().field_confidence(candidates, agreement_count=2, non_empty_count=2, value="Google")

    assert 0.9 <= score <= 1.0
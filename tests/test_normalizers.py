from candidate_data_transformer.models import CanonicalCandidate
from candidate_data_transformer.normalizers import default_normalization_pipeline


def test_default_normalization_pipeline_cleans_core_fields():
    candidate = CanonicalCandidate(
        source="recruiter",
        emails=[" Test@Example.COM ", "bad-email"],
        phones=["+91 98765 43210"],
        current_company="Amazon Web Services",
        current_title="Backend Dev",
        skills=["Py", "ReactJS", "Fast API", "Py"],
        location={"current": "Bangalore", "preferred": "Madras"},
        metadata={"last_updated": "Oct 02, 2024"},
    )

    normalized = default_normalization_pipeline().normalize(candidate)

    assert normalized.emails == ["test@example.com"]
    assert normalized.phones == ["+919876543210"]
    assert normalized.current_company == "Amazon"
    assert normalized.current_title == "Backend Developer"
    assert normalized.skills == ["FastAPI", "Python", "React"]
    assert normalized.location.current == "Bengaluru"
    assert normalized.location.preferred == "Chennai"
    assert normalized.metadata["last_updated"] == "2024-10"
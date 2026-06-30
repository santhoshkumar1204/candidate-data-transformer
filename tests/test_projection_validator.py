from candidate_data_transformer.models import CanonicalCandidate
from candidate_data_transformer.projection import OutputConfig, ProjectionEngine
from candidate_data_transformer.validator import SchemaValidator


def test_projection_engine_flattens_and_renames_fields():
    candidate = CanonicalCandidate(
        source="merged",
        candidate_id="M1",
        location={"current": "Bengaluru"},
        confidence={"overall": 0.9},
        provenance={"full_name": {"source": "recruiter"}},
    )
    engine = ProjectionEngine(OutputConfig(rename_fields={"candidate_id": "profile_id"}, flatten_nested=True))

    projected = engine.project(candidate)

    assert projected["profile_id"] == "M1"
    assert projected["location.current"] == "Bengaluru"
    assert projected["confidence.overall"] == 0.9


def test_schema_validator_reports_invalid_merged_profile():
    candidate = CanonicalCandidate(source="merged", candidate_id="M1")

    report = SchemaValidator().validate_many([candidate])

    assert report.invalid_count == 1
    assert report.errors[0].candidate_id == "M1"
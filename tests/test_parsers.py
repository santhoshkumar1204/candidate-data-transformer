from pathlib import Path

from candidate_data_transformer.parsers import create_parser
from generate_dataset import generate_dataset


def test_recruiter_parser_returns_canonical_candidates(tmp_path: Path):
    generate_dataset(count=5, output_dir=tmp_path, seed=7)

    candidates = create_parser("recruiter", tmp_path / "recruiter.csv").parse()

    assert len(candidates) == 5
    assert candidates[0].source == "recruiter"
    assert candidates[0].raw_record
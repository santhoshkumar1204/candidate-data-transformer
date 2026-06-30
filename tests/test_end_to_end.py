from pathlib import Path

from candidate_data_transformer.pipeline import CandidatePipeline
from generate_dataset import generate_dataset


def test_end_to_end_pipeline_runs_and_projects_json(tmp_path: Path):
    dataset_dir = tmp_path / "datasets"
    output_path = tmp_path / "merged.json"
    generate_dataset(count=12, output_dir=dataset_dir, seed=9)

    result = CandidatePipeline(dataset_dir=dataset_dir, config_dir="config").run(output_path=output_path)

    assert result.stats.candidates_parsed >= 12
    assert result.stats.candidates_normalized == result.stats.candidates_parsed
    assert result.stats.output_profiles == len(result.projected_candidates)
    assert output_path.exists()
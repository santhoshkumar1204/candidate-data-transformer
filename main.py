"""Command-line entry point for Candidate Data Transformer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from candidate_data_transformer.pipeline import CandidatePipeline, configure_logging
from generate_dataset import generate_dataset


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Candidate Data Transformer CLI")
    parser.add_argument("--generate-data", type=int, help="Generate synthetic datasets with the requested candidate count.")
    parser.add_argument("--run", action="store_true", help="Run the complete pipeline.")
    parser.add_argument("--validate-output", action="store_true", help="Run validation and print validation status.")
    parser.add_argument("--config", default="config/output_config.json", help="Output projection config path.")
    parser.add_argument("--dataset-dir", default="datasets", help="Dataset directory path.")
    parser.add_argument("--config-dir", default="config", help="Runtime config directory path.")
    parser.add_argument("--output", default="outputs/merged_candidates.json", help="JSON output path.")
    parser.add_argument("--seed", type=int, default=42, help="Dataset generation seed.")
    return parser.parse_args()


def main() -> int:
    """Run requested CLI operations."""

    args = parse_args()
    configure_logging()

    if args.generate_data is not None:
        generate_dataset(count=args.generate_data, output_dir=Path(args.dataset_dir), seed=args.seed)
        print(f"Generated dataset in {Path(args.dataset_dir).resolve()}")

    result = None
    if args.run or args.validate_output:
        pipeline = CandidatePipeline(
            dataset_dir=args.dataset_dir,
            config_dir=args.config_dir,
            output_config_path=args.config,
        )
        result = pipeline.run(output_path=args.output if args.run else None)

        if args.run:
            print("Pipeline completed")
            print(f"Parsed: {result.stats.candidates_parsed}")
            print(f"Normalized: {result.stats.candidates_normalized}")
            print(f"Merged profiles: {result.stats.merged_profiles}")
            print(f"Output profiles: {result.stats.output_profiles}")
            print(f"Validation errors: {result.stats.validation_errors}")
            print(f"Saved JSON: {Path(args.output).resolve()}")

        if args.validate_output:
            status = "passed" if result.validation_report and result.validation_report.is_valid else "failed"
            print(f"Validation {status}: {result.stats.validation_errors} error(s)")

    if args.generate_data is None and not args.run and not args.validate_output:
        print("No operation requested. Use --generate-data N, --run, and/or --validate-output.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
# Submission Checklist

## Assignment Requirement Checklist

| Requirement | Status | Notes |
| --- | --- | --- |
| Generate synthetic multi-source dataset | Implemented | `generate_dataset.py` creates recruiter CSV, ATS JSON, LinkedIn text, resumes, and summary JSON. |
| Ingestion parsers | Implemented | Source-specific parsers emit `CanonicalCandidate`. |
| Canonical schema | Implemented | Pydantic model with source, raw record, metadata, confidence, provenance, and merge metadata. |
| Normalization pipeline | Implemented | Modular transformers for whitespace, email, phone, company, skills, title, location, and dates. |
| Identity blocking | Implemented | Blocks by email, phone, links, and last name. |
| Similarity scoring | Implemented | Weighted deterministic rules with RapidFuzz for fuzzy text signals. |
| Match decisions | Implemented | Configurable MATCH, POSSIBLE_MATCH, NO_MATCH thresholds. |
| Merge engine | Implemented | Merges confirmed MATCH groups only. |
| Merge policy | Implemented | Deterministic field selection with agreement and source confidence. |
| Confidence scoring | Implemented | Configurable source confidence and field/profile confidence. |
| Provenance tracking | Implemented | Every merged field has value, sources, IDs, confidence, and merge reason. |
| Projection engine | Implemented | Runtime configurable inclusion, exclusion, renaming, flattening, confidence/provenance toggles, and missing values. |
| Schema validation | Implemented | Reports per-profile validation errors without stopping the run. |
| Runtime config | Implemented | JSON configs in `config/`. |
| CLI | Implemented | `main.py` supports dataset generation, pipeline run, validation, config, and JSON output. |
| Streamlit UI | Implemented | Operational pages for pipeline, viewer, comparison, confidence, provenance, config, stats, and quality. |
| Logging | Implemented | Logs to `logs/pipeline.log` and console. |
| Pytest coverage | Implemented | Parser, normalizer, matching, merge, confidence, projection, validator, and end-to-end tests. |
| README | Implemented | Professional project README. |
| DESIGN.md | Implemented | Detailed architecture and tradeoff document. |
| DESIGN.pdf | Implemented | Generated from project design content. |
| Visual documentation | Implemented | PNG and Mermaid sources under `docs/`. |
| Screenshots directory | Implemented | `screenshots/README.md` documents expected captures. |

## Verification Checklist

| Verification | Status |
| --- | --- |
| Dataset generation | Passed |
| Parsing | Passed |
| Normalization | Passed |
| Identity resolution | Passed |
| Merge | Passed |
| Confidence | Passed |
| Provenance | Passed |
| Projection | Passed |
| Validation | Passed |
| CLI | Passed |
| Streamlit launch | Passed |
| Logging | Passed |
| Tests | Passed |
| README | Passed |
| DESIGN.md | Passed |
| DESIGN.pdf | Passed |
| Architecture diagrams | Passed |
| Outputs | Passed |
| Configuration | Passed |

## Known Limitations

- Matching is deterministic and explainable, not machine-learning based.
- Resume and LinkedIn parsing is intentionally regex-based and tuned for generated text fixtures.
- Possible matches are collected as metadata but do not yet have a human review workflow.
- Streamlit screenshots are not committed as real screenshots; the directory documents where to place them after manual capture.

## Future Improvements

- Add persistent storage and incremental matching.
- Add richer real-world resume parsing.
- Add human review for possible matches.
- Add CI, coverage thresholds, and packaging.
- Add API endpoints for integration with other systems.

## Reviewer Notes

Run these commands from the repository root:

```bash
python main.py --generate-data 100
python main.py --run --config config/output_config.json --output outputs/merged_candidates.json
python main.py --validate-output
python -m pytest
streamlit run streamlit_app.py
```
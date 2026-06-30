# Project Summary

## What The Project Does

Candidate Data Transformer consolidates candidate information from recruiter CSV exports, ATS JSON exports, LinkedIn-style text profiles, and Markdown resumes into canonical merged candidate profiles.

The project demonstrates production-style data engineering: parsing, normalization, identity resolution, deterministic merging, confidence scoring, provenance tracking, validation, projection, CLI execution, Streamlit inspection, and test coverage.

## Architecture

The system is organized as independent layers:

```text
Dataset -> Parsers -> CanonicalCandidate -> Normalizers -> Matching -> Merge -> Validation -> Projection
```

Each layer has a narrow responsibility, making the codebase easy to extend without rewriting adjacent modules.

## Interesting Engineering Decisions

- All source parsers return the same Pydantic `CanonicalCandidate` model.
- Normalization is a pipeline of reusable transformers, not one large function.
- Matching avoids brute-force all-pairs comparison through blocking keys.
- Merge policy is deterministic and explainable.
- Confidence and provenance are first-class output concepts.
- Projection is configurable at runtime through JSON.
- CLI and Streamlit both share the same orchestration pipeline.

## Scalability

Blocking reduces comparison volume by comparing only candidates that share deterministic keys such as email, phone, profile links, or last name. The design can scale further with persisted blocking indexes, phonetic keys, source partitions, or incremental matching.

## How Confidence Works

Each source has configurable confidence. Defaults are recruiter `0.95`, resume `0.92`, ATS `0.90`, and LinkedIn `0.80`. Field confidence combines source confidence, agreement across sources, and completeness. Overall profile confidence is calculated from populated field confidences.

## How Provenance Works

Every merged field records the selected value, contributing sources, source candidate IDs, confidence score, and merge reason. This allows reviewers to understand why a field was chosen and which sources supported it.

## How Matching Works

Candidates are first blocked by deterministic keys. Candidate pairs inside blocks receive structured similarity scores from exact identifiers, fuzzy names, company similarity, skills overlap, location match, and education overlap. The decision engine classifies pairs as `MATCH`, `POSSIBLE_MATCH`, or `NO_MATCH`. Only `MATCH` pairs are automatically merged.

## Five Minute Demo

1. Generate data: `python main.py --generate-data 100`
2. Run pipeline: `python main.py --run`
3. Open `outputs/merged_candidates.json`
4. Start UI: `streamlit run streamlit_app.py`
5. Show Pipeline Statistics, Merged Candidate Viewer, Confidence Viewer, and Provenance Viewer.

## Why This Is Interview-Ready

The code separates concerns, avoids hidden inference, makes business rules configurable, includes meaningful tests, and produces auditable merged outputs. It resembles an internal engineering tool rather than a one-off script.
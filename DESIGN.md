# Candidate Data Transformer Design

## Architecture

Candidate Data Transformer is a layered ETL and identity-resolution system. Each layer owns one responsibility and communicates through typed canonical models.

```text
Sources
  -> Parsers
  -> CanonicalCandidate
  -> Normalizers
  -> Blocking
  -> Similarity
  -> Match Decision
  -> Merge Engine
  -> Confidence
  -> Provenance
  -> Validation
  -> Projection
```

## Pipeline

The complete pipeline reads generated datasets from `datasets/`, parses them into canonical models, normalizes field values, compares only blocked candidate pairs, merges confirmed matches, validates merged profiles, and writes projected JSON.

The orchestration lives in `candidate_data_transformer.pipeline.CandidatePipeline` so CLI and Streamlit use the same production path.

## Canonical Schema

The shared model is `CanonicalCandidate`, a Pydantic model used by parsers, normalizers, matching, merging, validation, and projection.

Important fields:

- identity: `candidate_id`, `full_name`, `emails`, `phones`, `linkedin_url`, `github_url`
- professional: `current_company`, `current_title`, `experience`, `skills`
- background: `education`, `certifications`, `projects`, `location`
- traceability: `source`, `raw_record`, `metadata`
- merged output: `confidence`, `provenance`, `merge_metadata`


## Normalization

Normalization is implemented as a configurable transformer pipeline. Each transformer accepts and returns a `CanonicalCandidate`, allowing transformers to be reordered, replaced, or extended without modifying parser or merge code.

Current transformers cover whitespace, email, phone, company aliases, skill aliases, titles, location aliases, and date-like metadata.

## Identity Resolution

Identity resolution is split into reusable components:

- `CandidateBlocker`: creates deterministic blocks from email, phone, profile links, and last name.
- `SimilarityScorer`: computes weighted deterministic scores using exact identifiers, RapidFuzz string similarity, skills overlap, location match, and education overlap.
- `MatchDecisionEngine`: maps scores to `MATCH`, `POSSIBLE_MATCH`, or `NO_MATCH` with configurable thresholds.

The engine avoids brute-force all-pairs matching by comparing only candidate pairs produced by blocking.

## Merge Policy

`MergePolicy` deterministically chooses values for every merged field.

Rules:

- prefer non-empty values
- prefer higher-confidence sources
- prefer exact agreement across sources
- prefer longer descriptive values where appropriate
- union list fields without inventing data
- never automatically merge `POSSIBLE_MATCH` pairs

Nested objects such as education, experience, and location are merged field by field.

## Confidence Strategy

Confidence is configurable by source:

- recruiter: `0.95`
- resume: `0.92`
- ATS: `0.90`
- LinkedIn: `0.80`

Field confidence combines source confidence, cross-source agreement, and field completeness. Overall profile confidence is derived from populated field confidences.

## Provenance

Every merged field receives provenance metadata:

- selected value
- contributing sources
- source candidate IDs
- field confidence
- merge reason

This makes every merge decision explainable and inspectable in Streamlit.

## Projection

The projection layer converts merged canonical candidates into output dictionaries using `config/output_config.json`.

Supported behavior:

- field inclusion
- field exclusion
- field renaming
- flattening nested values
- confidence toggle
- provenance toggle
- missing value handling

Projection is deliberately separate from merging so output requirements can change without affecting core identity logic.

## Configuration

Runtime configuration lives in JSON files:

- `output_config.json`
- `matching_config.json`
- `confidence_config.json`
- `company_aliases.json`
- `skill_aliases.json`

This keeps business rules editable without code changes.

## Validation

`SchemaValidator` validates final merged candidates. It reports validation errors per profile and continues processing the rest of the batch.

Validation checks include Pydantic schema compatibility and semantic checks such as merged source type, candidate ID presence, confidence bounds, and provenance presence.


## Complexity Analysis

Let `n` be the number of source records and `p` be the number of blocked comparison pairs.

- Parsing is O(n).
- Normalization is O(n * t), where `t` is the number of transformers.
- Blocking is O(n * k), where `k` is the number of blocking keys per candidate.
- Similarity is O(p), avoiding O(n^2) brute-force matching.
- Merge is O(n + m), where `m` is the total number of field values in matched components.

The primary scaling lever is reducing `p` through stronger blocking keys.

## Scalability

The main scalability decision is blocking. Instead of comparing every candidate with every other candidate, the system creates candidate pairs from deterministic blocking keys.

Future scaling options:

- persisted blocking indexes
- phonetic name keys
- incremental matching
- source-specific partitions
- distributed batch execution

## Complexities

The hard parts are not parsing files; they are preserving explainability while resolving imperfect, conflicting records. The design therefore keeps confidence, provenance, possible matches, and field-level merge reasons as first-class concepts.

## Engineering Decisions

- Use Pydantic for typed canonical contracts.
- Keep parser, normalizer, matcher, merger, validator, and projector layers separate.
- Prefer deterministic rules over opaque inference.
- Keep configuration outside code.
- Make CLI and UI share one pipeline runner.
- Add tests around each architectural layer.

## Tradeoffs

- Deterministic matching is easier to explain but can miss subtle duplicates.
- Last-name blocking improves recall but increases comparisons for common names.
- Rule-based confidence is transparent but not statistically calibrated.
- The Streamlit UI prioritizes operational clarity over custom design complexity.
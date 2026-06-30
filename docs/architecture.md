# Architecture Notes

Candidate Data Transformer is intended to be built as a layered data consolidation system.

## Layers

```text
Sources -> Parsers -> Normalizers -> Matchers -> Merger -> Provenance -> Confidence -> Projection
```

## Source Boundaries

Each external system should have a source adapter that understands only that source's format. Adapters should emit source records with raw values preserved.

## Canonical Boundary

The canonical candidate model should be independent of recruiter CSV, ATS JSON, LinkedIn text, and resume text. Source-specific field names should never leak into downstream merge decisions except through provenance metadata.

## Merge Philosophy

Merging should prefer explainability over hidden magic. Every selected value should be traceable to:

- source
- raw value
- normalized value
- timestamp when available
- confidence
- competing values
- merge rule or decision reason

## Deferred Implementation

No parser, normalizer, matcher, merger, confidence engine, projection layer, UI, CLI, tests, or CI are implemented in this foundation stage.

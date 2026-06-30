"""Identity resolution and merge components."""

from candidate_data_transformer.merging.confidence import ConfidenceCalculator, SourceConfidenceConfig
from candidate_data_transformer.merging.merge_engine import MergeEngine, MergeResultMetadata
from candidate_data_transformer.merging.merge_policy import MergePolicy
from candidate_data_transformer.merging.provenance import FieldProvenance, ProvenanceTracker

__all__ = [
    "ConfidenceCalculator",
    "FieldProvenance",
    "MergeEngine",
    "MergePolicy",
    "MergeResultMetadata",
    "ProvenanceTracker",
    "SourceConfidenceConfig",
]
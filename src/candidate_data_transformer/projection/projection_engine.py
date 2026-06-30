"""Projection engine for configurable candidate output shaping."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from candidate_data_transformer.models import CanonicalCandidate


@dataclass(frozen=True)
class OutputConfig:
    """Runtime output projection configuration."""

    include_fields: list[str] = field(default_factory=list)
    exclude_fields: list[str] = field(default_factory=list)
    rename_fields: dict[str, str] = field(default_factory=dict)
    flatten_nested: bool = True
    flatten_separator: str = "."
    include_confidence: bool = True
    include_provenance: bool = True
    missing_value_strategy: str = "null"
    missing_value: Any = None

    @classmethod
    def from_file(cls, path: str | Path) -> "OutputConfig":
        """Load projection configuration from JSON."""

        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**payload)


class ProjectionEngine:
    """Convert canonical merged candidates into configurable output dictionaries."""

    def __init__(self, config: OutputConfig | None = None) -> None:
        self.config = config or OutputConfig()

    @classmethod
    def from_config_file(cls, path: str | Path) -> "ProjectionEngine":
        """Build a projection engine from a JSON config file."""

        return cls(OutputConfig.from_file(path))

    def project_many(self, candidates: list[CanonicalCandidate]) -> list[dict[str, Any]]:
        """Project multiple candidates."""

        return [self.project(candidate) for candidate in candidates]

    def project(self, candidate: CanonicalCandidate) -> dict[str, Any]:
        """Project one candidate into a serializable output dictionary."""

        payload = candidate.model_dump(mode="json")
        if not self.config.include_confidence:
            payload.pop("confidence", None)
        if not self.config.include_provenance:
            payload.pop("provenance", None)

        if self.config.flatten_nested:
            payload = self._flatten(payload)

        payload = self._apply_inclusion(payload)
        payload = self._apply_exclusion(payload)
        payload = self._apply_missing_value_strategy(payload)
        return self._apply_renames(payload)

    def _apply_inclusion(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Keep only explicitly included fields when configured."""

        if not self.config.include_fields:
            return payload
        include = set(self.config.include_fields)
        return {key: value for key, value in payload.items() if key in include}

    def _apply_exclusion(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Remove excluded fields."""

        exclude = set(self.config.exclude_fields)
        return {key: value for key, value in payload.items() if key not in exclude}

    def _apply_renames(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Rename output fields according to config."""

        return {self.config.rename_fields.get(key, key): value for key, value in payload.items()}

    def _apply_missing_value_strategy(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Apply configured handling for missing values."""

        strategy = self.config.missing_value_strategy
        output: dict[str, Any] = {}
        for key, value in payload.items():
            if self._is_missing(value):
                if strategy == "omit":
                    continue
                if strategy == "empty_string":
                    output[key] = ""
                elif strategy == "custom":
                    output[key] = self.config.missing_value
                else:
                    output[key] = None
            else:
                output[key] = value
        return output

    def _flatten(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Flatten nested dictionaries using the configured separator."""

        flattened: dict[str, Any] = {}
        self._flatten_into(flattened, "", payload)
        return flattened

    def _flatten_into(self, output: dict[str, Any], prefix: str, value: Any) -> None:
        """Recursive flattening helper."""

        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")
        if isinstance(value, dict):
            for key, child in value.items():
                next_key = f"{prefix}{self.config.flatten_separator}{key}" if prefix else key
                self._flatten_into(output, next_key, child)
        else:
            output[prefix] = value

    def _is_missing(self, value: Any) -> bool:
        """Return true when a projected value is missing."""

        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, (list, dict, tuple, set)):
            return len(value) == 0
        return False
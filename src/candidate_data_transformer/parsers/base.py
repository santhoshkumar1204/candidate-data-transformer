"""Base abstractions and helpers for source parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from candidate_data_transformer.models import CanonicalCandidate


class BaseParser(ABC):
    """Abstract parser contract for all candidate data sources."""

    source_name: str

    def __init__(self, source_path: str | Path) -> None:
        self.source_path = Path(source_path)

    @abstractmethod
    def load(self) -> Any:
        """Load raw source data from disk."""

    @abstractmethod
    def parse(self) -> list[CanonicalCandidate]:
        """Parse source data into canonical candidate models."""

    def validate(self, candidate_data: dict[str, Any]) -> CanonicalCandidate | None:
        """Build a canonical candidate, returning None when validation fails."""

        try:
            return CanonicalCandidate.model_validate(candidate_data)
        except ValidationError as exc:
            self.log_warning(f"Skipping invalid {self.source_name} record: {exc}")
            return None

    def log_info(self, message: str) -> None:
        """Log an informational parser message."""

        import logging

        logging.getLogger(__name__).info(message)

    def log_warning(self, message: str) -> None:
        """Log a warning parser message."""

        import logging

        logging.getLogger(__name__).warning(message)

    @staticmethod
    def clean_text(value: Any) -> str | None:
        """Convert a source value to stripped text when meaningful."""

        if value is None:
            return None
        text = str(value).strip()
        if not text or text.lower() in {"nan", "none", "null"}:
            return None
        return text

    @staticmethod
    def clean_list(values: Iterable[Any]) -> list[str]:
        """Return non-empty, stripped, de-duplicated strings while preserving order."""

        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = BaseParser.clean_text(value)
            if not text:
                continue
            key = text.lower()
            if key not in seen:
                cleaned.append(text)
                seen.add(key)
        return cleaned

    @staticmethod
    def split_csv_text(value: Any) -> list[str]:
        """Split comma-separated source text into clean values."""

        text = BaseParser.clean_text(value)
        if not text:
            return []
        return BaseParser.clean_list(part for part in text.split(","))

    @staticmethod
    def parse_int(value: Any) -> int | None:
        """Parse an integer-ish source value safely."""

        text = BaseParser.clean_text(value)
        if not text:
            return None
        try:
            return int(float(text))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def parse_float(value: Any) -> float | None:
        """Parse a float-ish source value safely."""

        text = BaseParser.clean_text(value)
        if not text:
            return None
        try:
            return float(text)
        except (TypeError, ValueError):
            return None
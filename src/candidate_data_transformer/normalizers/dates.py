"""Date normalization transformer."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from dateutil import parser as date_parser

from candidate_data_transformer.models import CanonicalCandidate
from candidate_data_transformer.normalizers.base import BaseNormalizer

DATE_KEY_HINTS = ("date", "updated", "updated_at", "last_updated")
YEAR_PATTERN = re.compile(r"^\d{4}$")
YEAR_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class DateNormalizer(BaseNormalizer):
    """Normalize date-like metadata values to YYYY-MM or YYYY."""

    name = "dates"

    def normalize(self, candidate: CanonicalCandidate) -> CanonicalCandidate:
        """Normalize date-like metadata without inventing missing precision."""

        normalized = self.copy_candidate(candidate)
        normalized.metadata = self._normalize_metadata(normalized.metadata)
        return normalized

    def _normalize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Normalize date-like metadata values recursively."""

        output: dict[str, Any] = {}
        for key, value in metadata.items():
            if isinstance(value, dict):
                output[key] = self._normalize_metadata(value)
            elif self._is_date_key(key):
                output[key] = self._normalize_value(value)
            else:
                output[key] = value
        return output

    def _normalize_value(self, value: Any) -> Any:
        """Normalize a date value when confidently parseable."""

        if isinstance(value, datetime):
            return value.strftime("%Y-%m")
        if isinstance(value, date):
            return value.strftime("%Y-%m")
        if not isinstance(value, str):
            return value

        text = value.strip()
        if not text:
            return value
        if YEAR_PATTERN.fullmatch(text):
            return text
        if YEAR_MONTH_PATTERN.fullmatch(text):
            return text

        parsed = self._parse_date(text)
        return parsed.strftime("%Y-%m") if parsed else value

    def _parse_date(self, value: str) -> datetime | None:
        """Parse common date strings conservatively."""

        try:
            return date_parser.parse(value, fuzzy=False, default=datetime(1900, 1, 1))
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _is_date_key(key: str) -> bool:
        """Return true when metadata key appears date-like."""

        normalized_key = key.casefold()
        return any(hint in normalized_key for hint in DATE_KEY_HINTS)
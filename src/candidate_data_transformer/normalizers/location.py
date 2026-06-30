"""Location normalization transformer."""

from __future__ import annotations

import re

from candidate_data_transformer.models import CanonicalCandidate, Location
from candidate_data_transformer.normalizers.base import BaseNormalizer

DEFAULT_LOCATION_ALIASES = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "madras": "Chennai",
    "chennai": "Chennai",
    "bombay": "Mumbai",
    "mumbai": "Mumbai",
    "delhi ncr": "Delhi NCR",
    "ncr": "Delhi NCR",
}


class LocationNormalizer(BaseNormalizer):
    """Normalize known location aliases."""

    name = "location"

    def __init__(self, aliases: dict[str, str] | None = None) -> None:
        self.aliases = {self._key(key): value for key, value in {**DEFAULT_LOCATION_ALIASES, **(aliases or {})}.items()}

    def normalize(self, candidate: CanonicalCandidate) -> CanonicalCandidate:
        """Normalize current and preferred locations."""

        normalized = self.copy_candidate(candidate)
        if normalized.location is None:
            return normalized
        normalized.location = Location(
            current=self._normalize_location(normalized.location.current),
            preferred=self._normalize_location(normalized.location.preferred),
            raw_text=normalized.location.raw_text,
        )
        return normalized

    def _normalize_location(self, value: str | None) -> str | None:
        """Normalize a single location value."""

        if value is None:
            return None
        text = re.sub(r"\s+", " ", value).strip()
        if not text:
            return None
        return self.aliases.get(self._key(text), text)

    @staticmethod
    def _key(value: str) -> str:
        """Build a stable lookup key for location aliases."""

        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
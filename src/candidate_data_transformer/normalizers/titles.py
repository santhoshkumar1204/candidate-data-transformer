"""Job title normalization transformer."""

from __future__ import annotations

import re

from candidate_data_transformer.models import CanonicalCandidate
from candidate_data_transformer.normalizers.base import BaseNormalizer

DEFAULT_TITLE_ALIASES = {
    "sde i": "Software Engineer I",
    "software engineer i": "Software Engineer I",
    "software engineer": "Software Engineer",
    "sde": "Software Engineer",
    "backend dev": "Backend Developer",
    "backend developer": "Backend Developer",
    "backend engineer": "Backend Engineer",
    "frontend dev": "Frontend Developer",
    "front end dev": "Frontend Developer",
    "frontend developer": "Frontend Developer",
    "front end developer": "Frontend Developer",
    "fullstack engineer": "Full Stack Engineer",
    "full stack developer": "Full Stack Engineer",
    "devops engineer": "DevOps Engineer",
    "data engineer": "Data Engineer",
    "bi analyst": "BI Analyst",
}


class TitleNormalizer(BaseNormalizer):
    """Normalize common job title variants."""

    name = "titles"

    def __init__(self, aliases: dict[str, str] | None = None) -> None:
        self.aliases = {self._key(key): value for key, value in {**DEFAULT_TITLE_ALIASES, **(aliases or {})}.items()}

    def normalize(self, candidate: CanonicalCandidate) -> CanonicalCandidate:
        """Normalize candidate title."""

        normalized = self.copy_candidate(candidate)
        normalized.current_title = self._normalize_title(normalized.current_title)
        return normalized

    def _normalize_title(self, value: str | None) -> str | None:
        """Normalize a single title value."""

        if value is None:
            return None
        text = re.sub(r"\s+", " ", value).strip()
        if not text:
            return None
        return self.aliases.get(self._key(text), text)

    @staticmethod
    def _key(value: str) -> str:
        """Build a stable lookup key for title aliases."""

        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
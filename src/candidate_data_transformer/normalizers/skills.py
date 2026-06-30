"""Skill normalization transformer."""

from __future__ import annotations

import re

from candidate_data_transformer.models import CanonicalCandidate
from candidate_data_transformer.normalizers.base import BaseNormalizer

DEFAULT_SKILL_ALIASES = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "py": "Python",
    "python3": "Python",
    "ml": "Machine Learning",
    "ai": "Artificial Intelligence",
    "reactjs": "React",
    "react.js": "React",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "fast api": "FastAPI",
    "fastapi": "FastAPI",
    "springboot": "Spring Boot",
    "k8s": "Kubernetes",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mongo db": "MongoDB",
    "mongodb": "MongoDB",
    "powerbi": "Power BI",
}


class SkillNormalizer(BaseNormalizer):
    """Normalize skill synonyms, remove duplicates, and sort skills."""

    name = "skills"

    def __init__(self, aliases: dict[str, str] | None = None) -> None:
        self.aliases = {self._key(key): value for key, value in {**DEFAULT_SKILL_ALIASES, **(aliases or {})}.items()}

    def normalize(self, candidate: CanonicalCandidate) -> CanonicalCandidate:
        """Normalize candidate skills."""

        normalized = self.copy_candidate(candidate)
        skills = [self._normalize_skill(skill) for skill in normalized.skills]
        normalized.skills = sorted(self.unique_preserve_order(skill for skill in skills if skill), key=str.casefold)
        return normalized

    def _normalize_skill(self, value: str | None) -> str | None:
        """Normalize a single skill value."""

        if value is None:
            return None
        text = re.sub(r"\s+", " ", value).strip()
        if not text:
            return None
        return self.aliases.get(self._key(text), text)

    @staticmethod
    def _key(value: str) -> str:
        """Build a stable lookup key for skill aliases."""

        return re.sub(r"[^a-z0-9+#.]+", " ", value.casefold()).strip()
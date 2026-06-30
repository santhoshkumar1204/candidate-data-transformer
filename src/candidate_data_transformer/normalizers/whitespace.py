"""Whitespace and light text cleanup transformer."""

from __future__ import annotations

import re

from candidate_data_transformer.models import CanonicalCandidate, Education, Experience, Location
from candidate_data_transformer.normalizers.base import BaseNormalizer


class WhitespaceNormalizer(BaseNormalizer):
    """Trim whitespace, collapse repeated spaces, and clean simple text fields."""

    name = "whitespace"

    def normalize(self, candidate: CanonicalCandidate) -> CanonicalCandidate:
        """Normalize whitespace across candidate text fields."""

        normalized = self.copy_candidate(candidate)
        normalized.candidate_id = self._clean(normalized.candidate_id, uppercase=True)
        normalized.full_name = self._clean(normalized.full_name, title_case=True)
        normalized.current_company = self._clean(normalized.current_company)
        normalized.current_title = self._clean(normalized.current_title)
        normalized.linkedin_url = self._clean(normalized.linkedin_url)
        normalized.github_url = self._clean(normalized.github_url)
        normalized.emails = self.unique_preserve_order(self._clean(value) for value in normalized.emails if self._clean(value))
        normalized.phones = self.unique_preserve_order(self._clean(value) for value in normalized.phones if self._clean(value))
        normalized.skills = self.unique_preserve_order(self._clean(value) for value in normalized.skills if self._clean(value))
        normalized.certifications = self.unique_preserve_order(
            self._clean(value) for value in normalized.certifications if self._clean(value)
        )
        normalized.projects = self.unique_preserve_order(self._clean(value) for value in normalized.projects if self._clean(value))
        normalized.education = self._clean_education(normalized.education)
        normalized.experience = self._clean_experience(normalized.experience)
        normalized.location = self._clean_location(normalized.location)
        normalized.metadata = self._clean_metadata(normalized.metadata)
        return normalized

    def _clean(self, value: str | None, *, title_case: bool = False, uppercase: bool = False) -> str | None:
        """Clean a string value."""

        if value is None:
            return None
        text = re.sub(r"\s+", " ", str(value)).strip()
        if not text:
            return None
        if uppercase:
            return text.upper()
        if title_case and text.isupper():
            return text.title()
        return text

    def _clean_education(self, education: Education | None) -> Education | None:
        """Clean nested education text."""

        if education is None:
            return None
        education.highest_degree = self._clean(education.highest_degree)
        education.university = self._clean(education.university)
        education.raw_text = self._clean(education.raw_text)
        return education

    def _clean_experience(self, experience: Experience | None) -> Experience | None:
        """Clean nested experience text."""

        if experience is None:
            return None
        experience.summary = self._clean(experience.summary)
        experience.entries = self.unique_preserve_order(self._clean(value) for value in experience.entries if self._clean(value))
        return experience

    def _clean_location(self, location: Location | None) -> Location | None:
        """Clean nested location text."""

        if location is None:
            return None
        location.current = self._clean(location.current)
        location.preferred = self._clean(location.preferred)
        location.raw_text = self._clean(location.raw_text)
        return location

    def _clean_metadata(self, metadata: dict) -> dict:
        """Clean string metadata values without changing keys."""

        cleaned = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                cleaned[key] = self._clean(value)
            elif isinstance(value, list):
                cleaned[key] = [self._clean(item) if isinstance(item, str) else item for item in value]
            else:
                cleaned[key] = value
        return cleaned
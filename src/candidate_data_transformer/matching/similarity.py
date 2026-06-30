"""Deterministic similarity scoring for candidate identity resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - fallback keeps local smoke checks usable before install.
    from difflib import SequenceMatcher

    class fuzz:  # type: ignore[no-redef]
        """Small fallback compatible with the RapidFuzz ratio APIs used here."""

        @staticmethod
        def token_sort_ratio(left: str, right: str) -> float:
            left_tokens = " ".join(sorted(left.casefold().split()))
            right_tokens = " ".join(sorted(right.casefold().split()))
            return SequenceMatcher(None, left_tokens, right_tokens).ratio() * 100

        @staticmethod
        def ratio(left: str, right: str) -> float:
            return SequenceMatcher(None, left.casefold(), right.casefold()).ratio() * 100

from candidate_data_transformer.models import CanonicalCandidate


@dataclass(frozen=True)
class SimilarityScores:
    """Structured candidate similarity output."""

    total_score: float
    exact_email: float = 0.0
    exact_phone: float = 0.0
    exact_linkedin: float = 0.0
    exact_github: float = 0.0
    name_similarity: float = 0.0
    company_similarity: float = 0.0
    skills_overlap: float = 0.0
    location_match: float = 0.0
    education_overlap: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def has_exact_identifier(self) -> bool:
        """Return true when a strong identity field matches exactly."""

        return any([self.exact_email, self.exact_phone, self.exact_linkedin, self.exact_github])


class SimilarityScorer:
    """Compute deterministic weighted similarity between two candidates."""

    DEFAULT_WEIGHTS = {
        "exact_email": 0.25,
        "exact_phone": 0.25,
        "exact_linkedin": 0.18,
        "exact_github": 0.12,
        "name_similarity": 0.08,
        "company_similarity": 0.04,
        "skills_overlap": 0.03,
        "location_match": 0.03,
        "education_overlap": 0.02,
    }

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = {**self.DEFAULT_WEIGHTS, **(weights or {})}

    def score(self, left: CanonicalCandidate, right: CanonicalCandidate) -> SimilarityScores:
        """Return structured similarity scores for two candidates."""

        scores = {
            "exact_email": self._exact_overlap(left.emails, right.emails),
            "exact_phone": self._exact_overlap(left.phones, right.phones),
            "exact_linkedin": self._exact_text(left.linkedin_url, right.linkedin_url),
            "exact_github": self._exact_text(left.github_url, right.github_url),
            "name_similarity": self._fuzzy(left.full_name, right.full_name),
            "company_similarity": self._fuzzy(left.current_company, right.current_company),
            "skills_overlap": self._jaccard(left.skills, right.skills),
            "location_match": self._location_match(left, right),
            "education_overlap": self._education_overlap(left, right),
        }
        total_weight = sum(self.weights.values()) or 1.0
        total_score = sum(scores[key] * self.weights.get(key, 0.0) for key in scores) / total_weight
        return SimilarityScores(total_score=round(total_score, 4), **scores, details=self._details(left, right))

    def _exact_overlap(self, left: list[str], right: list[str]) -> float:
        """Score exact overlap between two lists."""

        left_values = {value.casefold() for value in left if value}
        right_values = {value.casefold() for value in right if value}
        return 1.0 if left_values and right_values and bool(left_values & right_values) else 0.0

    def _exact_text(self, left: str | None, right: str | None) -> float:
        """Score exact match between optional strings."""

        return 1.0 if left and right and left.casefold() == right.casefold() else 0.0

    def _fuzzy(self, left: str | None, right: str | None) -> float:
        """Score fuzzy string similarity using RapidFuzz."""

        if not left or not right:
            return 0.0
        return round(fuzz.token_sort_ratio(left, right) / 100, 4)

    def _jaccard(self, left: list[str], right: list[str]) -> float:
        """Score set overlap for skills."""

        left_values = {value.casefold() for value in left if value}
        right_values = {value.casefold() for value in right if value}
        if not left_values or not right_values:
            return 0.0
        return round(len(left_values & right_values) / len(left_values | right_values), 4)

    def _location_match(self, left: CanonicalCandidate, right: CanonicalCandidate) -> float:
        """Score exact current/preferred location overlap."""

        left_values = self._location_values(left)
        right_values = self._location_values(right)
        return 1.0 if left_values and right_values and bool(left_values & right_values) else 0.0

    def _education_overlap(self, left: CanonicalCandidate, right: CanonicalCandidate) -> float:
        """Score education agreement from university or graduation year."""

        if not left.education or not right.education:
            return 0.0
        score = 0.0
        if left.education.university and right.education.university:
            score = max(score, fuzz.token_sort_ratio(left.education.university, right.education.university) / 100)
        if left.education.graduation_year and left.education.graduation_year == right.education.graduation_year:
            score = max(score, 1.0)
        return round(score, 4)

    def _location_values(self, candidate: CanonicalCandidate) -> set[str]:
        """Return normalized candidate location values."""

        if not candidate.location:
            return set()
        return {
            value.casefold()
            for value in [candidate.location.current, candidate.location.preferred]
            if value
        }

    def _details(self, left: CanonicalCandidate, right: CanonicalCandidate) -> dict[str, Any]:
        """Return helpful comparison metadata."""

        return {
            "left_candidate_id": left.candidate_id,
            "right_candidate_id": right.candidate_id,
            "left_source": left.source,
            "right_source": right.source,
        }
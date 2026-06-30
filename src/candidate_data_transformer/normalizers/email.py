"""Email normalization transformer."""

from __future__ import annotations

import re

from candidate_data_transformer.models import CanonicalCandidate
from candidate_data_transformer.normalizers.base import BaseNormalizer

EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)


class EmailNormalizer(BaseNormalizer):
    """Normalize candidate email addresses."""

    name = "email"

    def normalize(self, candidate: CanonicalCandidate) -> CanonicalCandidate:
        """Lowercase, trim, validate, and de-duplicate emails."""

        normalized = self.copy_candidate(candidate)
        valid_emails = []
        for email in normalized.emails:
            cleaned = email.strip().lower()
            if EMAIL_PATTERN.fullmatch(cleaned):
                valid_emails.append(cleaned)
        normalized.emails = self.unique_preserve_order(valid_emails)
        return normalized
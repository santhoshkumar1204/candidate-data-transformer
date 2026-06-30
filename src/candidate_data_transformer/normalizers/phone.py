"""Phone number normalization transformer."""

from __future__ import annotations

import re

import phonenumbers

from candidate_data_transformer.models import CanonicalCandidate
from candidate_data_transformer.normalizers.base import BaseNormalizer


class PhoneNormalizer(BaseNormalizer):
    """Normalize phone numbers to E.164 format."""

    name = "phone"

    def __init__(self, default_region: str = "IN") -> None:
        self.default_region = default_region

    def normalize(self, candidate: CanonicalCandidate) -> CanonicalCandidate:
        """Parse, validate, format, and de-duplicate phone numbers."""

        normalized = self.copy_candidate(candidate)
        phones: list[str] = []
        for phone in normalized.phones:
            for piece in re.split(r"[,;/]", phone):
                formatted = self._format_phone(piece)
                if formatted:
                    phones.append(formatted)
        normalized.phones = self.unique_preserve_order(phones)
        return normalized

    def _format_phone(self, phone: str) -> str | None:
        """Return an E.164 phone number when valid."""

        try:
            parsed = phonenumbers.parse(phone.strip(), self.default_region)
        except phonenumbers.NumberParseException:
            return None
        if not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
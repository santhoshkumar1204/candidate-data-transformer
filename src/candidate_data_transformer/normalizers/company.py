"""Company name normalization transformer."""

from __future__ import annotations

import re

from candidate_data_transformer.models import CanonicalCandidate
from candidate_data_transformer.normalizers.base import BaseNormalizer

DEFAULT_COMPANY_ALIASES = {
    "google india": "Google",
    "google llc": "Google",
    "amazon web services": "Amazon",
    "aws": "Amazon",
    "amazon india": "Amazon",
    "tcs ltd": "TCS",
    "tata consultancy services": "TCS",
    "infosys limited": "Infosys",
    "infosys ltd": "Infosys",
    "infy": "Infosys",
    "bluestock fintech pvt ltd": "Bluestock Fintech",
    "bluestock fintech": "Bluestock Fintech",
    "bluestock": "Bluestock",
    "microsoft india": "Microsoft",
    "msft": "Microsoft",
    "adobe systems": "Adobe",
    "adobe india": "Adobe",
    "cisco systems": "Cisco",
    "ibm india": "IBM",
    "international business machines": "IBM",
    "oracle india": "Oracle",
    "zoho corp": "Zoho",
    "freshworks inc": "Freshworks",
    "freshworks chennai": "Freshworks",
    "sfdc": "Salesforce",
    "salesforce india": "Salesforce",
    "accenture india": "Accenture",
    "acn": "Accenture",
    "wipro technologies": "Wipro",
}


class CompanyNormalizer(BaseNormalizer):
    """Normalize company names using configurable alias mappings."""

    name = "company"

    def __init__(self, aliases: dict[str, str] | None = None) -> None:
        self.aliases = {self._key(key): value for key, value in {**DEFAULT_COMPANY_ALIASES, **(aliases or {})}.items()}

    def normalize(self, candidate: CanonicalCandidate) -> CanonicalCandidate:
        """Normalize current company and known company metadata fields."""

        normalized = self.copy_candidate(candidate)
        normalized.current_company = self._normalize_company(normalized.current_company)
        for key in ("previous_employer", "employer", "current_company"):
            if key in normalized.metadata and isinstance(normalized.metadata[key], str):
                normalized.metadata[key] = self._normalize_company(normalized.metadata[key])
        return normalized

    def _normalize_company(self, value: str | None) -> str | None:
        """Normalize a single company value."""

        if value is None:
            return None
        text = re.sub(r"\s+", " ", value).strip()
        if not text:
            return None
        return self.aliases.get(self._key(text), text)

    @staticmethod
    def _key(value: str) -> str:
        """Build a stable lookup key for company aliases."""

        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
"""Deterministic parser for generated Markdown resumes."""

from __future__ import annotations

import re
from pathlib import Path

from candidate_data_transformer.models import CanonicalCandidate, Education, Experience
from candidate_data_transformer.parsers.base import BaseParser


HEADING_PATTERN = re.compile(r"^(#{1,3})\s+(.+?)\s*$", flags=re.MULTILINE)


class ResumeParser(BaseParser):
    """Parse Markdown resumes into canonical candidates."""

    source_name = "resume"

    def load(self) -> list[tuple[Path, str]]:
        """Load Markdown resumes from a directory."""

        if not self.source_path.exists():
            self.log_warning(f"Resume directory not found: {self.source_path}")
            return []

        resumes: list[tuple[Path, str]] = []
        for path in sorted(self.source_path.glob("*.md")):
            try:
                resumes.append((path, path.read_text(encoding="utf-8")))
            except Exception as exc:
                self.log_warning(f"Could not read resume {path}: {exc}")

        self.log_info(f"Loaded resume directory {self.source_path}")
        return resumes

    def parse(self) -> list[CanonicalCandidate]:
        """Parse resumes into canonical candidates."""

        candidates = []
        for path, text in self.load():
            try:
                candidate = self.validate(self._map_resume(path, text))
            except Exception as exc:
                self.log_warning(f"Skipping malformed resume {path.name}: {exc}")
                continue
            if candidate:
                candidates.append(candidate)

        self.log_info(f"Parsed {len(candidates)} resumes")
        return candidates

    def _map_resume(self, path: Path, text: str) -> dict:
        """Map one Markdown resume into canonical candidate data."""

        sections = self._extract_sections(text)
        summary = self.clean_text(sections.get("summary"))
        company, entries = self._parse_experience_section(sections.get("experience"))
        title, years = self._parse_summary(summary)
        return {
            "candidate_id": self._candidate_id_from_path(path),
            "full_name": self._parse_name(text),
            "emails": self._extract_emails(text),
            "phones": self._extract_phones(text),
            "current_company": company,
            "current_title": title,
            "experience": Experience(years=years, summary=summary, entries=entries)
            if years is not None or summary or entries
            else None,
            "education": self._parse_education(sections.get("education")),
            "skills": self.split_csv_text(sections.get("skills")),
            "certifications": self._parse_bullets(sections.get("certifications")),
            "projects": self._parse_bullets(sections.get("projects")),
            "location": None,
            "linkedin_url": self._extract_first_url(text, "linkedin.com"),
            "github_url": self._extract_first_url(text, "github.com"),
            "source": self.source_name,
            "raw_record": text,
            "metadata": {
                "file_name": path.name,
                "summary": summary,
                "achievements": self._parse_bullets(sections.get("achievements")),
            },
        }

    def _extract_sections(self, text: str) -> dict[str, str]:
        """Extract Markdown sections keyed by lower-case heading text."""

        matches = list(HEADING_PATTERN.finditer(text))
        sections: dict[str, str] = {}
        for index, match in enumerate(matches):
            heading = match.group(2).strip().lower()
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            sections[heading] = text[start:end].strip()
        return sections

    def _parse_name(self, text: str) -> str | None:
        """Parse the top-level Markdown title as candidate name."""

        match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
        return self.clean_text(match.group(1)) if match else None

    def _parse_summary(self, summary: str | None) -> tuple[str | None, float | None]:
        """Parse title and years from generated resume summary text."""

        if not summary:
            return None, None
        match = re.search(r"^(?P<title>.+?)\s+with\s+(?P<years>\d+(?:\.\d+)?)\s+years?", summary, re.IGNORECASE)
        if not match:
            return None, None
        return self.clean_text(match.group("title")), self.parse_float(match.group("years"))

    def _parse_education(self, education_text: str | None) -> Education | None:
        """Parse Markdown education bullets."""

        text = self.clean_text(education_text)
        if not text:
            return None
        match = re.search(r"-\s*(?P<degree>.+?),\s*(?P<university>.+?)\s*\((?P<year>\d{4})\)", text)
        if not match:
            return Education(raw_text=text)
        return Education(
            highest_degree=self.clean_text(match.group("degree")),
            university=self.clean_text(match.group("university")),
            graduation_year=self.parse_int(match.group("year")),
            raw_text=text,
        )

    def _parse_experience_section(self, experience_text: str | None) -> tuple[str | None, list[str]]:
        """Parse current company and experience bullets."""

        text = self.clean_text(experience_text)
        if not text:
            return None, []
        company_match = re.search(r"^###\s+(.+?)\s*$", text, re.MULTILINE)
        return (
            self.clean_text(company_match.group(1)) if company_match else None,
            self._parse_bullets(text),
        )

    def _parse_bullets(self, value: str | None) -> list[str]:
        """Extract Markdown bullet lines."""

        text = self.clean_text(value)
        if not text:
            return []
        return self.clean_list(match.group(1) for match in re.finditer(r"^\s*-\s+(.+?)\s*$", text, re.MULTILINE))

    def _extract_emails(self, text: str) -> list[str]:
        """Extract email-like strings from resume text."""

        return self.clean_list(re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text))

    def _extract_phones(self, text: str) -> list[str]:
        """Extract Indian phone-like strings from resume text."""

        pattern = r"(?:\+91[\s-]?)?(?:0)?[6-9]\d{4}[\s-]?\d{5}"
        return self.clean_list(re.findall(pattern, text))

    def _extract_first_url(self, text: str, domain: str) -> str | None:
        """Extract the first URL containing a domain."""

        match = re.search(rf"https?://[^\s)]+{re.escape(domain)}[^\s)]*", text, re.IGNORECASE)
        return self.clean_text(match.group(0)) if match else None

    def _candidate_id_from_path(self, path: Path) -> str | None:
        """Extract candidate ID prefix from a generated resume filename."""

        match = re.match(r"(CAND-\d+)", path.stem, re.IGNORECASE)
        return match.group(1).upper() if match else None
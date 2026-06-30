"""Deterministic parser for generated LinkedIn-style text profiles."""

from __future__ import annotations

import re
from pathlib import Path

from candidate_data_transformer.models import CanonicalCandidate, Education, Experience, Location
from candidate_data_transformer.parsers.base import BaseParser


SECTION_PATTERN = re.compile(
    r"^(Headline|About|Experience|Education|Skills|Certifications|Projects)\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


class LinkedInParser(BaseParser):
    """Parse LinkedIn-style plain text profiles into canonical candidates."""

    source_name = "linkedin"

    def load(self) -> list[tuple[Path, str]]:
        """Load every text profile from a LinkedIn directory."""

        if not self.source_path.exists():
            self.log_warning(f"LinkedIn directory not found: {self.source_path}")
            return []

        profiles: list[tuple[Path, str]] = []
        for path in sorted(self.source_path.glob("*.txt")):
            try:
                profiles.append((path, path.read_text(encoding="utf-8")))
            except Exception as exc:
                self.log_warning(f"Could not read LinkedIn profile {path}: {exc}")

        self.log_info(f"Loaded LinkedIn directory {self.source_path}")
        return profiles

    def parse(self) -> list[CanonicalCandidate]:
        """Parse LinkedIn profiles into canonical candidates."""

        candidates = []
        for path, text in self.load():
            try:
                candidate = self.validate(self._map_profile(path, text))
            except Exception as exc:
                self.log_warning(f"Skipping malformed LinkedIn profile {path.name}: {exc}")
                continue
            if candidate:
                candidates.append(candidate)

        self.log_info(f"Parsed {len(candidates)} LinkedIn profiles")
        return candidates

    def _map_profile(self, path: Path, text: str) -> dict:
        """Map one LinkedIn text profile into canonical candidate data."""

        sections = self._extract_sections(text)
        headline = self.clean_text(sections.get("headline"))
        name, title, company = self._parse_headline(headline)
        about = self.clean_text(sections.get("about"))
        return {
            "candidate_id": self._candidate_id_from_path(path),
            "full_name": name,
            "emails": [],
            "phones": [],
            "current_company": company,
            "current_title": title,
            "experience": self._parse_experience(sections.get("experience"), about),
            "education": self._parse_education(sections.get("education")),
            "skills": self.split_csv_text(sections.get("skills")),
            "certifications": self._parse_lines(sections.get("certifications")),
            "projects": self._parse_project_sentences(sections.get("projects")),
            "location": self._parse_location(about),
            "linkedin_url": None,
            "github_url": None,
            "source": self.source_name,
            "raw_record": text,
            "metadata": {
                "file_name": path.name,
                "headline": headline,
                "about": about,
            },
        }

    def _extract_sections(self, text: str) -> dict[str, str]:
        """Extract known sections from generated LinkedIn text."""

        matches = list(SECTION_PATTERN.finditer(text))
        sections: dict[str, str] = {}
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            sections[match.group(1).lower()] = text[start:end].strip()
        return sections

    def _parse_headline(self, headline: str | None) -> tuple[str | None, str | None, str | None]:
        """Extract name, title, and company from a headline."""

        if not headline:
            return None, None, None
        match = re.match(r"(?P<name>.+?)\s+-\s+(?P<title>.+?)\s+at\s+(?P<company>.+)$", headline)
        if not match:
            return headline, None, None
        return (
            self.clean_text(match.group("name")),
            self.clean_text(match.group("title")),
            self.clean_text(match.group("company")),
        )

    def _parse_experience(self, experience_text: str | None, about: str | None) -> Experience | None:
        """Extract structured experience hints from profile text."""

        entries = self._parse_lines(experience_text)
        years = None
        if about:
            match = re.search(r"with\s+(\d+(?:\.\d+)?)\s+years?\s+of experience", about, re.IGNORECASE)
            years = self.parse_float(match.group(1)) if match else None
        summary = self.clean_text(experience_text)
        return Experience(years=years, summary=summary, entries=entries) if years is not None or summary or entries else None

    def _parse_education(self, education_text: str | None) -> Education | None:
        """Extract degree, university, and graduation year from education text."""

        text = self.clean_text(education_text)
        if not text:
            return None
        match = re.search(r"(?P<degree>.+?)\s+from\s+(?P<university>.+?),\s+class of\s+(?P<year>\d{4})", text)
        if not match:
            return Education(raw_text=text)
        return Education(
            highest_degree=self.clean_text(match.group("degree")),
            university=self.clean_text(match.group("university")),
            graduation_year=self.parse_int(match.group("year")),
            raw_text=text,
        )

    def _parse_location(self, about: str | None) -> Location | None:
        """Extract current and preferred location from about text."""

        if not about:
            return None
        current_match = re.search(r"based in\s+(.+?)\s+with\s+\d+", about, re.IGNORECASE)
        preferred_match = re.search(r"Preferred location:\s*([^.\n]+)", about, re.IGNORECASE)
        location = Location(
            current=self.clean_text(current_match.group(1)) if current_match else None,
            preferred=self.clean_text(preferred_match.group(1)) if preferred_match else None,
            raw_text=about,
        )
        return location if location.current or location.preferred else None

    def _parse_lines(self, value: str | None) -> list[str]:
        """Parse non-empty section lines."""

        text = self.clean_text(value)
        if not text:
            return []
        return self.clean_list(line.strip("- ") for line in text.splitlines())

    def _parse_project_sentences(self, value: str | None) -> list[str]:
        """Parse project statements conservatively."""

        text = self.clean_text(value)
        if not text:
            return []
        return self.clean_list(part.strip() for part in re.split(r"\.\s+", text) if part.strip())

    def _candidate_id_from_path(self, path: Path) -> str | None:
        """Extract candidate ID prefix from a generated profile filename."""

        match = re.match(r"(CAND-\d+)", path.stem, re.IGNORECASE)
        return match.group(1).upper() if match else None
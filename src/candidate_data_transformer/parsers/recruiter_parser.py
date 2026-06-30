"""Parser for recruiter CSV exports."""

from __future__ import annotations

from typing import Any

import pandas as pd

from candidate_data_transformer.models import CanonicalCandidate, Education, Experience, Location
from candidate_data_transformer.parsers.base import BaseParser


class RecruiterParser(BaseParser):
    """Parse recruiter CSV rows into canonical candidates."""

    source_name = "recruiter"

    def load(self) -> list[dict[str, Any]]:
        """Load recruiter CSV records."""

        try:
            rows = pd.read_csv(self.source_path).to_dict(orient="records")
        except FileNotFoundError:
            self.log_warning(f"Recruiter file not found: {self.source_path}")
            return []
        except Exception as exc:
            self.log_warning(f"Could not load recruiter CSV {self.source_path}: {exc}")
            return []

        self.log_info(f"Loaded {self.source_path.name}")
        return rows

    def parse(self) -> list[CanonicalCandidate]:
        """Parse recruiter records into canonical candidates."""

        candidates = []
        for row_number, row in enumerate(self.load(), start=1):
            try:
                candidate = self.validate(self._map_row(row, row_number))
            except Exception as exc:
                self.log_warning(f"Skipping malformed recruiter row {row_number}: {exc}")
                continue
            if candidate:
                candidates.append(candidate)

        self.log_info(f"Parsed {len(candidates)} recruiter records")
        return candidates

    def _map_row(self, row: dict[str, Any], row_number: int) -> dict[str, Any]:
        """Map one recruiter row into canonical candidate data."""

        skills = self.split_csv_text(row.get("primary_skills")) + self.split_csv_text(row.get("secondary_skills"))
        return {
            "candidate_id": self.clean_text(row.get("candidate_id")),
            "full_name": self.clean_text(row.get("full_name")),
            "emails": self.clean_list([row.get("primary_email")]),
            "phones": self.clean_list([row.get("phone_number")]),
            "current_company": self.clean_text(row.get("current_company")),
            "current_title": self.clean_text(row.get("current_title")),
            "experience": Experience(years=self.parse_float(row.get("years_experience"))),
            "education": Education(
                highest_degree=self.clean_text(row.get("highest_degree")),
                university=self.clean_text(row.get("university")),
                graduation_year=self.parse_int(row.get("graduation_year")),
            ),
            "skills": self.clean_list(skills),
            "certifications": [],
            "projects": [],
            "location": Location(
                current=self.clean_text(row.get("current_location")),
                preferred=self.clean_text(row.get("preferred_location")),
            ),
            "linkedin_url": self.clean_text(row.get("linkedin_url")),
            "github_url": self.clean_text(row.get("github_url")),
            "source": self.source_name,
            "raw_record": row,
            "metadata": {
                "row_number": row_number,
                "last_updated": self.clean_text(row.get("last_updated")),
                "recruiter_notes": self.clean_text(row.get("recruiter_notes")),
                "current_ctc_lpa": self.parse_float(row.get("current_ctc_lpa")),
                "expected_ctc_lpa": self.parse_float(row.get("expected_ctc_lpa")),
                "notice_period_days": self.parse_int(row.get("notice_period_days")),
            },
        }
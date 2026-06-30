"""Parser for ATS JSON exports."""

from __future__ import annotations

import json
from typing import Any

from candidate_data_transformer.models import CanonicalCandidate, Education, Experience, Location
from candidate_data_transformer.parsers.base import BaseParser


class ATSParser(BaseParser):
    """Parse ATS JSON records into canonical candidates."""

    source_name = "ats"

    def load(self) -> list[dict[str, Any]]:
        """Load ATS JSON records."""

        try:
            payload = json.loads(self.source_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.log_warning(f"ATS file not found: {self.source_path}")
            return []
        except json.JSONDecodeError as exc:
            self.log_warning(f"Could not decode ATS JSON {self.source_path}: {exc}")
            return []

        if not isinstance(payload, list):
            self.log_warning(f"Expected ATS JSON array in {self.source_path}")
            return []

        records = [record for record in payload if isinstance(record, dict)]
        skipped = len(payload) - len(records)
        if skipped:
            self.log_warning(f"Skipped {skipped} non-object ATS records")
        self.log_info(f"Loaded {self.source_path.name}")
        return records

    def parse(self) -> list[CanonicalCandidate]:
        """Parse ATS records into canonical candidates."""

        candidates = []
        for index, record in enumerate(self.load(), start=1):
            try:
                candidate = self.validate(self._map_record(record, index))
            except Exception as exc:
                self.log_warning(f"Skipping malformed ATS record {index}: {exc}")
                continue
            if candidate:
                candidates.append(candidate)

        self.log_info(f"Parsed {len(candidates)} ATS records")
        return candidates

    def _map_record(self, record: dict[str, Any], index: int) -> dict[str, Any]:
        """Map one ATS record into canonical candidate data."""

        profile_links = record.get("profileLinks") if isinstance(record.get("profileLinks"), dict) else {}
        skills = record.get("skills") if isinstance(record.get("skills"), list) else []
        return {
            "candidate_id": self.clean_text(record.get("applicantId")),
            "full_name": self.clean_text(record.get("legalName")),
            "emails": self.clean_list([record.get("emailAddress")]),
            "phones": self.clean_list([record.get("mobile")]),
            "current_company": self.clean_text(record.get("employer")),
            "current_title": self.clean_text(record.get("jobTitle")),
            "experience": Experience(years=self.parse_float(record.get("totalExperienceYears"))),
            "education": Education(
                highest_degree=self.clean_text(record.get("degree")),
                university=self.clean_text(record.get("college")),
                graduation_year=self.parse_int(record.get("gradYear")),
            ),
            "skills": self.clean_list(skills),
            "certifications": [],
            "projects": [],
            "location": Location(
                current=self.clean_text(record.get("location")),
                preferred=self.clean_text(record.get("preferredCity")),
            ),
            "linkedin_url": self.clean_text(profile_links.get("linkedin")),
            "github_url": self.clean_text(profile_links.get("github")),
            "source": self.source_name,
            "raw_record": record,
            "metadata": {
                "record_index": index,
                "updated_at": self.clean_text(record.get("updatedAt")),
                "ats_status": self.clean_text(record.get("atsStatus")),
                "source_system": self.clean_text(record.get("sourceSystem")),
                "profile_score": self.parse_int(record.get("profileScore")),
                "tags": self.clean_list(record.get("tags", [])) if isinstance(record.get("tags"), list) else [],
                "previous_employer": self.clean_text(record.get("previousEmployer")),
                "notice_period": self.clean_text(record.get("noticePeriod")),
                "current_compensation_lpa": self.parse_float(record.get("currentCompensationLpa")),
                "expected_compensation_lpa": self.parse_float(record.get("expectedCompensationLpa")),
            },
        }
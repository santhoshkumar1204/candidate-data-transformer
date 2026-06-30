"""Canonical data models for candidate ingestion and merged profiles."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Education(BaseModel):
    """Education details detected from a source record."""

    model_config = ConfigDict(extra="allow")

    highest_degree: str | None = None
    university: str | None = None
    graduation_year: int | None = None
    raw_text: str | None = None


class Experience(BaseModel):
    """Experience details detected from a source record."""

    model_config = ConfigDict(extra="allow")

    years: float | None = None
    summary: str | None = None
    entries: list[str] = Field(default_factory=list)


class Location(BaseModel):
    """Candidate location details."""

    model_config = ConfigDict(extra="allow")

    current: str | None = None
    preferred: str | None = None
    raw_text: str | None = None


class CanonicalCandidate(BaseModel):
    """Internal candidate representation emitted by parsers and merge engine."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str | None = None
    full_name: str | None = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    current_company: str | None = None
    current_title: str | None = None
    experience: Experience | None = None
    education: Education | None = None
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    location: Location | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    source: Literal["recruiter", "ats", "linkedin", "resume", "merged"]
    raw_record: dict[str, Any] | str = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidence: dict[str, float] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    merge_metadata: dict[str, Any] = Field(default_factory=dict)
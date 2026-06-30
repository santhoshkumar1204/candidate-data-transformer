"""Factory for source parser construction."""

from __future__ import annotations

from pathlib import Path

from candidate_data_transformer.parsers.ats_parser import ATSParser
from candidate_data_transformer.parsers.base import BaseParser
from candidate_data_transformer.parsers.linkedin_parser import LinkedInParser
from candidate_data_transformer.parsers.recruiter_parser import RecruiterParser
from candidate_data_transformer.parsers.resume_parser import ResumeParser


class ParserFactory:
    """Create parser instances by source type."""

    _PARSERS: dict[str, type[BaseParser]] = {
        "recruiter": RecruiterParser,
        "ats": ATSParser,
        "linkedin": LinkedInParser,
        "resume": ResumeParser,
    }

    @classmethod
    def create(cls, source_type: str, source_path: str | Path) -> BaseParser:
        """Return the parser for a source type."""

        parser_class = cls._PARSERS.get(source_type.strip().lower())
        if parser_class is None:
            supported = ", ".join(sorted(cls._PARSERS))
            raise ValueError(f"Unsupported source type '{source_type}'. Supported sources: {supported}")
        return parser_class(source_path)


def create_parser(source_type: str, source_path: str | Path) -> BaseParser:
    """Convenience function for constructing a parser."""

    return ParserFactory.create(source_type, source_path)
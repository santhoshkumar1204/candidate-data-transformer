"""Reusable candidate normalization framework."""

from candidate_data_transformer.normalizers.base import BaseNormalizer
from candidate_data_transformer.normalizers.company import CompanyNormalizer
from candidate_data_transformer.normalizers.dates import DateNormalizer
from candidate_data_transformer.normalizers.email import EmailNormalizer
from candidate_data_transformer.normalizers.location import LocationNormalizer
from candidate_data_transformer.normalizers.phone import PhoneNormalizer
from candidate_data_transformer.normalizers.pipeline import NormalizationPipeline
from candidate_data_transformer.normalizers.skills import SkillNormalizer
from candidate_data_transformer.normalizers.titles import TitleNormalizer
from candidate_data_transformer.normalizers.whitespace import WhitespaceNormalizer


def default_normalization_pipeline() -> NormalizationPipeline:
    """Create the standard normalization pipeline for parsed candidates."""

    return NormalizationPipeline(
        [
            WhitespaceNormalizer(),
            EmailNormalizer(),
            PhoneNormalizer(),
            CompanyNormalizer(),
            SkillNormalizer(),
            TitleNormalizer(),
            LocationNormalizer(),
            DateNormalizer(),
        ]
    )


__all__ = [
    "BaseNormalizer",
    "CompanyNormalizer",
    "DateNormalizer",
    "EmailNormalizer",
    "LocationNormalizer",
    "NormalizationPipeline",
    "PhoneNormalizer",
    "SkillNormalizer",
    "TitleNormalizer",
    "WhitespaceNormalizer",
    "default_normalization_pipeline",
]
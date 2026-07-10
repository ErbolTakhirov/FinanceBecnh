"""Shared enums and small value types used across every schema module.

This module is the dependency leaf of the schema package — it imports nothing else from
``financebench`` so that every other schema module can build on top of it without risking a
circular import.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "SCHEMA_VERSION",
    "AnswerType",
    "Language",
    "Scale",
    "SplitOrigin",
    "TranslationProvenance",
]

#: Version of the canonical sample/prediction/metric/run schemas defined in this package.
#: Bump this (and add a migration note in docs/reproducibility.md) on any breaking field change.
SCHEMA_VERSION = "1.0"

#: An ISO-639-1-ish language code, e.g. "en", "ru". Kept as a plain string rather than a closed
#: enum since new benchmarks may introduce languages we don't want to enumerate up front.
Language = str


class SplitOrigin(StrEnum):
    """Where a sample's split assignment actually comes from.

    Never mix an ``official`` split with a locally re-derived one without this label — a
    leaderboard comparing "finqa:test" scores across two runs is only meaningful if both drew
    from the same split origin.
    """

    OFFICIAL = "official"
    DERIVED_LOCAL = "derived_local"
    GENERATED_FROZEN = "generated_frozen"
    PUBLIC_SUBSET = "public_subset"
    USER_SUPPLIED = "user_supplied"


class TranslationProvenance(StrEnum):
    """How a non-English (or non-source-language) sample came to be in that language.

    Required on every bilingual EN/RU sample so a report never presents a machine-translated
    question as if it were an official-language original.
    """

    OFFICIAL_LANGUAGE = "official_language"
    HUMAN_VERIFIED_TRANSLATION = "human_verified_translation"
    MACHINE_TRANSLATED_DERIVED = "machine_translated_derived"


class AnswerType(StrEnum):
    """The shape of a gold (or predicted) answer, driving which metric applies."""

    NUMERIC = "numeric"
    TEXT = "text"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    MULTI_CHOICE = "multi_choice"
    PROGRAM = "program"
    REFUSAL = "refusal"


class Scale(StrEnum):
    """The magnitude multiplier implied by a numeric answer's presentation.

    Deliberately separate from *unit* (e.g. "percent", "usd", "ratio", "days") — ``12.5`` with
    ``unit=percent, scale=unit`` means 12.5%, not 12.5% * 1000. Adapters normalize each source
    benchmark's own scale/unit conflation (e.g. TAT-QA treats "percent" as a scale option) into
    this separated representation.
    """

    UNIT = "unit"
    THOUSAND = "thousand"
    MILLION = "million"
    BILLION = "billion"

from __future__ import annotations

from financebench.schemas.common import (
    SCHEMA_VERSION,
    AnswerType,
    Scale,
    SplitOrigin,
    TranslationProvenance,
)


def test_schema_version_is_1_0() -> None:
    assert SCHEMA_VERSION == "1.0"


def test_split_origin_members() -> None:
    assert {member.value for member in SplitOrigin} == {
        "official",
        "derived_local",
        "generated_frozen",
        "public_subset",
        "user_supplied",
    }


def test_translation_provenance_members() -> None:
    assert {member.value for member in TranslationProvenance} == {
        "official_language",
        "human_verified_translation",
        "machine_translated_derived",
    }


def test_answer_type_members_include_numeric_and_refusal() -> None:
    values = {member.value for member in AnswerType}
    assert {"numeric", "text", "boolean", "choice", "multi_choice", "program", "refusal"} <= values


def test_scale_members() -> None:
    assert {member.value for member in Scale} == {"unit", "thousand", "million", "billion"}

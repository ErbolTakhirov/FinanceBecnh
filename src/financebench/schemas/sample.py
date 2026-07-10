"""The canonical sample schema — the one shape every dataset adapter normalizes into.

Every benchmark adapter (FinQA, TAT-QA, SMB-CFO, ...) maps its own native format into
:class:`CanonicalSample`. Everything downstream (execution, evaluation, reporting) depends only
on this schema, never on a benchmark's native format — that separation is what lets the platform
add a new benchmark without touching the engine or the metrics that don't need to know about it.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from financebench.schemas.common import (
    SCHEMA_VERSION,
    AnswerType,
    Language,
    Scale,
    SplitOrigin,
    TranslationProvenance,
)
from financebench.schemas.tooling import ToolSpec

__all__ = [
    "CanonicalSample",
    "ConversationTurn",
    "DocumentRef",
    "EvaluationSpec",
    "Evidence",
    "GoldAnswer",
    "ImageRef",
    "SampleContext",
    "SourceInfo",
    "Table",
]


class Table(BaseModel):
    """A table as a raw string grid.

    Deliberately the lowest common denominator across sources: FinQA/ConvFinQA tables are
    naturally a list-of-lists; TAT-QA's structured header/body columns still reduce to a grid
    with the first ``header_rows`` rows being headers. Adapters that need cell-level scale/unit
    annotations (TAT-QA's per-column units) carry that in ``metadata`` rather than forcing every
    other adapter to populate a richer cell type it doesn't have.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    table_id: str
    caption: str | None = None
    rows: tuple[tuple[str, ...], ...]
    header_rows: int = 1
    metadata: dict[str, str] = Field(default_factory=dict)


class ConversationTurn(BaseModel):
    """One turn of prior conversation context (e.g. a ConvFinQA turn before the current one)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: str
    content: str
    turn_program: str | None = None
    turn_answer: str | None = None


class DocumentRef(BaseModel):
    """A reference to a source document (e.g. a 10-K filing) a sample is grounded in."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    title: str | None = None
    url: str | None = None
    local_path: str | None = None
    page_count: int | None = None


class ImageRef(BaseModel):
    """A reference to an image (chart, screenshot) a sample is grounded in."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    image_id: str
    local_path: str | None = None
    url: str | None = None
    caption: str | None = None


class SampleContext(BaseModel):
    """Everything a model needs to answer the question: prose, tables, images, documents."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: tuple[str, ...] = Field(default_factory=tuple)
    tables: tuple[Table, ...] = Field(default_factory=tuple)
    images: tuple[ImageRef, ...] = Field(default_factory=tuple)
    documents: tuple[DocumentRef, ...] = Field(default_factory=tuple)
    conversation_history: tuple[ConversationTurn, ...] = Field(default_factory=tuple)


class Evidence(BaseModel):
    """A pointer into the context that supports (or is claimed to support) the gold answer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str | None = None
    page: int | None = None
    table_id: str | None = None
    row: str | None = None
    text_snippet: str | None = None


class GoldAnswer(BaseModel):
    """The ground-truth answer and everything needed to grade a prediction against it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    answer: str
    answer_type: AnswerType
    numeric_value: float | None = None
    unit: str | None = None
    scale: Scale | None = None
    currency: str | None = None
    evidence: tuple[Evidence, ...] = Field(default_factory=tuple)
    program: str | None = None
    acceptable_answers: tuple[str, ...] = Field(default_factory=tuple)


class EvaluationSpec(BaseModel):
    """Grading parameters specific to this sample."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    absolute_tolerance: float | None = None
    relative_tolerance: float | None = None
    requires_citation: bool = False
    should_refuse: bool = False


class SourceInfo(BaseModel):
    """Provenance and licensing of the sample's underlying data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    license: str
    url: str
    checksum: str | None = None
    redistributable: bool = False


class CanonicalSample(BaseModel):
    """A single benchmark sample normalized into the platform's canonical shape.

    ``sample_id`` is conventionally ``"{benchmark}:{split}:{local_id}"`` (validated below) so
    ids are globally unique across a run that mixes benchmarks.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = SCHEMA_VERSION
    benchmark: str
    benchmark_version: str
    split: str
    split_origin: SplitOrigin
    sample_id: str
    task_family: str
    capability_tags: tuple[str, ...] = Field(default_factory=tuple)
    language: Language = "en"
    #: Required (non-None) whenever ``language != "en"`` — see the sample-level validator below.
    translation_provenance: TranslationProvenance | None = None
    question: str
    context: SampleContext = Field(default_factory=SampleContext)
    choices: tuple[str, ...] = Field(default_factory=tuple)
    tools: tuple[ToolSpec, ...] = Field(default_factory=tuple)
    gold: GoldAnswer
    evaluation: EvaluationSpec = Field(default_factory=EvaluationSpec)
    source: SourceInfo
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("benchmark", "task_family", "question", "sample_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value

    @model_validator(mode="after")
    def _sample_id_matches_benchmark_and_split(self) -> CanonicalSample:
        prefix = f"{self.benchmark}:{self.split}:"
        if not self.sample_id.startswith(prefix):
            raise ValueError(
                f"sample_id {self.sample_id!r} must start with {prefix!r} "
                "(the '{benchmark}:{split}:' convention keeps ids unique across a mixed run)"
            )
        return self

    @model_validator(mode="after")
    def _non_english_requires_translation_provenance(self) -> CanonicalSample:
        if self.language != "en" and self.translation_provenance is None:
            raise ValueError(
                f"language={self.language!r} requires translation_provenance to be set "
                "(official_language / human_verified_translation / machine_translated_derived)"
            )
        return self

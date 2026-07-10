"""Per-sample prediction records — what gets written to ``predictions.jsonl`` and
``parsed_answers.jsonl`` for every run."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from financebench.schemas.model_io import FinancialAnswer, ModelRequest, ModelResponse

__all__ = ["ParsedAnswer", "Prediction"]


class Prediction(BaseModel):
    """The full record of one sample's model call: what was asked, what came back (if anything),
    and how many attempts/cache lookups it took to get there."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sample_id: str
    benchmark: str
    split: str
    request: ModelRequest
    response: ModelResponse | None = None
    error: str | None = None
    error_type: str | None = None
    attempts: int = 1
    cache_hit: bool = False
    retry_wait_ms: float = 0.0
    created_at: str


class ParsedAnswer(BaseModel):
    """The structured-answer parse outcome for one sample, kept separate from ``Prediction`` so
    format-compliance can be reported independently of semantic correctness."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sample_id: str
    financial_answer: FinancialAnswer | None = None
    parse_success: bool = False
    raw_text: str = ""

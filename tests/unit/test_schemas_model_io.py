from __future__ import annotations

import pytest
from pydantic import ValidationError

from financebench.schemas.model_io import (
    ChatMessage,
    FinancialAnswer,
    ModelRequest,
    ModelSpec,
    Role,
)


def test_model_spec_parse_simple() -> None:
    spec = ModelSpec.parse("mock/echo-gold")
    assert spec.provider == "mock"
    assert spec.model == "echo-gold"
    assert spec.ref == "mock/echo-gold"


def test_model_spec_parse_model_with_embedded_slash() -> None:
    spec = ModelSpec.parse("openrouter/meta-llama/llama-3.1-70b-instruct")
    assert spec.provider == "openrouter"
    assert spec.model == "meta-llama/llama-3.1-70b-instruct"


def test_model_spec_parse_rejects_missing_slash() -> None:
    with pytest.raises(ValueError, match="provider/model"):
        ModelSpec.parse("not-a-valid-ref")


def test_model_spec_slug_is_filesystem_safe() -> None:
    spec = ModelSpec.parse("openrouter/meta-llama/llama-3.1-70b-instruct")
    assert "/" not in spec.slug


def test_financial_answer_from_fenced_json() -> None:
    text = 'Sure, here is my answer:\n```json\n{"answer": "12.5%", "numeric_value": 12.5}\n```'
    answer = FinancialAnswer.from_text(text)
    assert answer is not None
    assert answer.answer == "12.5%"
    assert answer.numeric_value == 12.5


def test_financial_answer_from_embedded_json_in_prose() -> None:
    text = 'The result is {"answer": "42", "numeric_value": 42.0, "unit": "usd_millions"} as shown.'
    answer = FinancialAnswer.from_text(text)
    assert answer is not None
    assert answer.answer == "42"
    assert answer.unit == "usd_millions"


def test_financial_answer_tolerates_unknown_keys() -> None:
    text = '{"answer": "yes", "some_future_field": "ignored"}'
    answer = FinancialAnswer.from_text(text)
    assert answer is not None
    assert answer.answer == "yes"


def test_financial_answer_falls_back_to_raw_text_for_unstructured_models() -> None:
    text = "Revenue grew by roughly twelve and a half percent year over year."
    answer = FinancialAnswer.from_text(text)
    assert answer is not None
    assert answer.answer == text
    assert answer.numeric_value is None


def test_financial_answer_from_empty_text_is_none() -> None:
    assert FinancialAnswer.from_text("   ") is None


def test_model_request_is_frozen_and_forbids_extra() -> None:
    request = ModelRequest(
        model=ModelSpec.parse("mock/echo-gold"),
        messages=(ChatMessage(role=Role.USER, content="hi"),),
        prompt_version="v1",
        benchmark="smoke",
        benchmark_version="1",
        sample_id="smoke:dev:1",
    )
    assert request.temperature == 0.0
    with pytest.raises(ValidationError):
        ModelRequest.model_validate(request.model_dump() | {"unexpected": True})

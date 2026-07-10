"""Metric result schemas — the per-sample and aggregate shapes every metric (native or unified)
reports through, so the evaluator and reports never special-case a particular metric's output
shape."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["MetricAggregate", "MetricResult"]


class MetricResult(BaseModel):
    """One metric's outcome for one sample."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sample_id: str
    metric_name: str
    value: float | bool | str | None = None
    passed: bool | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class MetricAggregate(BaseModel):
    """A metric rolled up across a set of samples, with a bootstrap confidence interval when one
    has been computed (``None`` otherwise — never invented)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metric_name: str
    n: int
    mean: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None

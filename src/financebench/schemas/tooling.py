"""Tool-related schemas shared by the canonical sample schema and the model I/O schemas.

Kept intentionally small in Milestone 1 — full agentic tool-use evaluation (argument
validation, execution sandboxing, tool-selection scoring) is Milestone 7. What's here is enough
to type a sample's available ``tools`` and a model's ``tool_calls`` today without redesigning the
envelope later.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ToolCall", "ToolResult", "ToolSpec"]


class ToolSpec(BaseModel):
    """A tool made available to a model for a given sample (e.g. a calculator or CSV query)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    description: str
    parameters_schema: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """A single tool invocation a model requested."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    call_id: str | None = None


class ToolResult(BaseModel):
    """The sandboxed outcome of executing a :class:`ToolCall`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    call_id: str | None = None
    output: str | None = None
    error: str | None = None
    latency_ms: float | None = None

"""A minimal, hardcoded prompt renderer for Milestone 1.

Turns a :class:`CanonicalSample` into the messages sent to a model, asking for the structured
:class:`FinancialAnswer` JSON envelope. This is intentionally simple (one prompt, one version) —
the full versioned, YAML-configurable prompt-profile system (grounded-answer-with-citations,
analyst-memo, tool-use-agent, ...) described in the mission is built out in Milestone 2+ once
more than one profile actually differs in a way worth configuring rather than hardcoding.
"""

from __future__ import annotations

from financebench.schemas.model_io import ChatMessage, Role
from financebench.schemas.sample import CanonicalSample, Table

__all__ = ["PROMPT_VERSION", "SYSTEM_PROMPT", "render_messages"]

PROMPT_VERSION = "direct_answer_v1"

SYSTEM_PROMPT = (
    "You are a financial analyst assistant. Answer the question using ONLY the provided "
    "context. Respond with a single JSON object matching this schema: "
    '{"answer": "<string>", "numeric_value": <number or null>, "unit": "<string or null>", '
    '"citations": [{"document_id": "...", "page": ..., "table": "...", "row": "..."}], '
    '"insufficient_information": <true|false>, "confidence": <0-1 or null>, '
    '"brief_explanation": "<string or null>"}. '
    "If the context does not contain enough information to answer confidently, set "
    "insufficient_information to true rather than guessing."
)


def _render_table(table: Table) -> str:
    lines = [" | ".join(row) for row in table.rows]
    header = f"Table ({table.caption}):\n" if table.caption else "Table:\n"
    return header + "\n".join(lines)


def _render_context(sample: CanonicalSample) -> str:
    parts: list[str] = [*sample.context.text]
    parts.extend(_render_table(table) for table in sample.context.tables)
    parts.extend(f"[{turn.role}] {turn.content}" for turn in sample.context.conversation_history)
    return "\n\n".join(parts)


def render_messages(sample: CanonicalSample) -> tuple[ChatMessage, ...]:
    """Render ``sample`` into a ``(system, user)`` message pair."""
    user_parts: list[str] = []
    context_text = _render_context(sample)
    if context_text:
        user_parts.append(f"Context:\n{context_text}")
    if sample.choices:
        user_parts.append("Choices:\n" + "\n".join(sample.choices))
    user_parts.append(f"Question: {sample.question}")
    return (
        ChatMessage(role=Role.SYSTEM, content=SYSTEM_PROMPT),
        ChatMessage(role=Role.USER, content="\n\n".join(user_parts)),
    )

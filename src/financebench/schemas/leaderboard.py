"""The leaderboard record schema — one row per (model, run) in the global leaderboard, kept
separate from a single run's own artifacts so the leaderboard builder can validate compatibility
(same coverage/benchmark versions) before comparing two rows."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["LeaderboardRecord"]


class LeaderboardRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    model_ref: str
    provider: str
    fci: float | None = None
    band: str | None = None
    provisional: bool = True
    critical_gate_failed: bool = False
    capability_scores: dict[str, float] = Field(default_factory=dict)
    coverage_summary: dict[str, Any] = Field(default_factory=dict)
    deployment_efficiency: dict[str, Any] | None = None
    created_at: str

"""Critical-gate schemas (``gates.json``).

Milestone 1 ships the shape, not the logic: no gate thresholds are evaluated yet (that's the
FCI/scoring work in Milestone 6), so :class:`GatesReport` is written with ``evaluated=False`` and
an empty gate list — a real, valid, forward-compatible instance rather than a bare ``{}`` that a
later milestone would have to redefine.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["GateResult", "GatesReport"]


class GateResult(BaseModel):
    """One named threshold check (e.g. ``unsupported_claim_rate <= 0.08``)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    gate_name: str
    threshold: float | None = None
    observed: float | None = None
    #: ``None`` means not yet evaluated (Milestone 1) — never a fabricated pass/fail.
    passed: bool | None = None


class GatesReport(BaseModel):
    """The full set of critical-gate outcomes for a run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluated: bool = False
    gates: tuple[GateResult, ...] = Field(default_factory=tuple)
    any_critical_gate_failed: bool | None = None

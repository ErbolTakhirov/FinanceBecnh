"""Evaluation: metrics (native + unified) and the capability-dimension rollup.

The full evaluator orchestration (native per-benchmark scoring, the LLM-judge framework, FCI/
gates/confidence-intervals) is built out across Milestones 2-6; this package currently holds the
Milestone 1 foundation both of those build on.
"""

from __future__ import annotations

from financebench.evaluation.capability_map import (
    CAPABILITY_WEIGHTS,
    CapabilityDimension,
    dimensions_for_sample,
    rollup_capabilities,
)

__all__ = [
    "CAPABILITY_WEIGHTS",
    "CapabilityDimension",
    "dimensions_for_sample",
    "rollup_capabilities",
]

"""Native, benchmark-specific metrics — each wrapped benchmark's own official evaluation method,
preserved rather than flattened into a generic score. Importing this package registers every
native metric implemented so far (currently just FinQA's execution accuracy)."""

from __future__ import annotations

from financebench.evaluation.native import finqa as _finqa  # noqa: F401
from financebench.evaluation.native.finqa import FinQAExecutionAccuracy, execute_program

__all__ = ["FinQAExecutionAccuracy", "execute_program"]

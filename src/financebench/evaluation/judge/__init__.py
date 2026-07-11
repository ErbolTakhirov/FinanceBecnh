"""The LLM judge, and the calibration that decides whether to believe it.

A judge that has not been calibrated does not produce a score. Not a score with a caveat — a
`NOT_EVALUATED`. The alternative, which every benchmark in this space reaches for, is to run an
uncalibrated judge, get 0.71, and print it; and nobody can tell 0.71-because-the-model-is-decent from
0.71-because-the-judge-says-yes-to-everything.
"""

from __future__ import annotations

from financebench.evaluation.judge.calibration import (
    MAX_FALSE_POSITIVE_RATE,
    MIN_ACCURACY,
    CalibrationCase,
    CalibrationReport,
    build_calibration_set,
    score_calibration,
)
from financebench.evaluation.judge.judge import (
    JUDGE_PROMPT_VERSION,
    RUBRIC,
    JudgeVerdict,
    Rubric,
    judge_answer,
)

__all__ = [
    "JUDGE_PROMPT_VERSION",
    "MAX_FALSE_POSITIVE_RATE",
    "MIN_ACCURACY",
    "RUBRIC",
    "CalibrationCase",
    "CalibrationReport",
    "JudgeVerdict",
    "Rubric",
    "build_calibration_set",
    "judge_answer",
    "score_calibration",
]

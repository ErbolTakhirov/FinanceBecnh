"""FinQA's native program DSL: a safe (no ``eval``/``exec``), hand-rolled interpreter for the
program format FinQA's official ``code/evaluate/evaluate.py`` defines, plus the execution-
accuracy metric built on it.

The interpreter's correctness was validated by executing all 1,147 gold programs in the official
FinQA test split and confirming every single one reproduces its recorded ``exe_ans`` — see
``tests/datasets/test_finqa_e2e.py``.

**Scope note on program accuracy**: FinQA's other native metric, program accuracy, compares a
*predicted* program against gold via symbolic equivalence (SymPy-based, after abstracting
literals into symbols). This platform's current prompt profile (``prompts/renderer.py``) asks
models for a direct structured answer, not a program — there is nothing to compare yet. Program
accuracy is intentionally not implemented until a program-eliciting prompt profile exists
(Milestone 2+); claiming a "close enough" structural comparator here instead of the real thing
would be exactly the kind of fabricated native-metric support the project's own rules forbid.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from financebench.evaluation.metrics.base import Metric, register_metric
from financebench.evaluation.numeric import numeric_match, parse_numeric_answer
from financebench.schemas.metric import MetricResult
from financebench.schemas.prediction import Prediction
from financebench.schemas.sample import CanonicalSample

__all__ = ["FinQAExecutionAccuracy", "execute_program", "str_to_num_finqa"]

_ALL_OPS = frozenset(
    {
        "add",
        "subtract",
        "multiply",
        "divide",
        "exp",
        "greater",
        "table_max",
        "table_min",
        "table_sum",
        "table_average",
    }
)
_ARITHMETIC_OPS = frozenset({"add", "subtract", "multiply", "divide", "exp", "greater"})

# Finds `op(arg1, arg2)` steps in a program string, e.g. "subtract(5829, 5735), divide(#0, 5735)".
# `arg1`/`arg2` deliberately exclude "(" and ")" but allow embedded spaces (table-row labels like
# "net change for the year" are valid first arguments to table_* ops).
_STEP_RE = re.compile(r"(\w+)\(\s*([^,()]+?)\s*,\s*([^,()]+?)\s*\)")


def str_to_num_finqa(text: str) -> float | None:
    """Port of FinQA's own ``str_to_num``: strips thousands commas, then falls back to
    percentage (``"12%"`` -> ``0.12``) and ``const_*`` literal encodings (``"const_100"`` ->
    ``100``, the special-cased ``"const_m1"`` -> ``-1``) before giving up."""
    cleaned = text.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        pass
    if "%" in cleaned:
        try:
            return float(cleaned.replace("%", "")) / 100.0
        except ValueError:
            return None
    if "const" in cleaned:
        literal = cleaned.replace("const_", "")
        if literal == "m1":
            literal = "-1"
        try:
            return float(literal)
        except ValueError:
            return None
    return None


def _process_table_row(row: Sequence[str]) -> list[float] | None:
    values: list[float] = []
    for cell in row:
        cell = cell.replace("$", "").strip()
        cell = cell.split("(")[0].strip()  # FinQA encodes negatives as "-32 ( 32 )"
        number = str_to_num_finqa(cell)
        if number is None:
            return None
        values.append(number)
    return values


def _resolve_arg(raw: str, results: Mapping[int, float | str]) -> float | str | None:
    raw = raw.strip()
    if raw.startswith("#"):
        try:
            index = int(raw[1:])
        except ValueError:
            return None
        return results.get(index)
    return str_to_num_finqa(raw)


def execute_program(
    program: str, table: Sequence[Sequence[str]] | None = None
) -> float | str | None:
    """Execute a FinQA program string, returning the final step's result.

    Returns a ``float`` (rounded to 5 decimals, matching the official evaluator) for arithmetic/
    table results, the literal string ``"yes"``/``"no"`` for a final ``greater`` step, or
    ``None`` if the program is malformed, references an unknown table row, or divides by zero —
    never a fabricated fallback value.
    """
    steps = _STEP_RE.findall(program)
    if not steps:
        return None

    results: dict[int, float | str] = {}
    table_by_row: dict[str, Sequence[str]] | None = (
        {row[0]: row[1:] for row in table} if table else None
    )
    final: float | str | None = None

    for index, (op, arg1_raw, arg2_raw) in enumerate(steps):
        op = op.strip()
        if op not in _ALL_OPS:
            return None

        if op in _ARITHMETIC_OPS:
            arg1 = _resolve_arg(arg1_raw, results)
            arg2 = _resolve_arg(arg2_raw, results)
            if arg1 is None or arg2 is None or isinstance(arg1, str) or isinstance(arg2, str):
                return None
            if op == "add":
                value: float | str = arg1 + arg2
            elif op == "subtract":
                value = arg1 - arg2
            elif op == "multiply":
                value = arg1 * arg2
            elif op == "divide":
                if arg2 == 0:
                    return None
                value = arg1 / arg2
            elif op == "exp":
                value = arg1**arg2
            else:  # greater
                value = "yes" if arg1 > arg2 else "no"
        else:
            # table_max / table_min / table_sum / table_average — unary in effect; FinQA's
            # syntax still carries a second "none" argument, which is simply unused.
            if table_by_row is None:
                return None
            row_key = arg1_raw.strip()
            if "#" in row_key:
                return None
            row = table_by_row.get(row_key)
            if row is None:
                return None
            processed = _process_table_row(row)
            if processed is None:
                return None
            if op == "table_max":
                value = max(processed)
            elif op == "table_min":
                value = min(processed)
            elif op == "table_sum":
                value = sum(processed)
            else:  # table_average
                value = sum(processed) / len(processed)

        results[index] = value
        final = value

    if isinstance(final, float):
        return round(final, 5)
    return final


@register_metric("finqa_execution_accuracy")
class FinQAExecutionAccuracy(Metric):
    """Does the model's final numeric answer match FinQA's gold execution result (``exe_ans``)?

    This grades the model's stated *final answer*, not a predicted program — the current direct-
    answer prompt profile doesn't ask for one (see the module docstring's program-accuracy scope
    note). A small absolute tolerance absorbs floating-point/formatting noise around the same
    rounding FinQA's own evaluator applies (round to 5 decimals).
    """

    name = "finqa_execution_accuracy"

    def score(self, sample: CanonicalSample, prediction: Prediction) -> MetricResult:
        response = prediction.response
        if response is None or response.financial_answer is None:
            return MetricResult(
                sample_id=sample.sample_id,
                metric_name=self.name,
                value=False,
                passed=False,
                details={"reason": "no parsed answer"},
            )
        answer = response.financial_answer

        # FinQA's `greater` operation yields a yes/no boolean, not a number — gold.numeric_value
        # is None for exactly these samples, so they're graded by string comparison instead.
        if sample.gold.numeric_value is None:
            predicted_text = answer.answer.strip().casefold()
            gold_text = sample.gold.answer.strip().casefold()
            is_match = predicted_text == gold_text
            return MetricResult(
                sample_id=sample.sample_id,
                metric_name=self.name,
                value=is_match,
                passed=is_match,
                details={"predicted": predicted_text, "gold": gold_text, "mode": "boolean"},
            )

        predicted_value = answer.numeric_value
        if predicted_value is None:
            parsed = parse_numeric_answer(answer.answer)
            predicted_value = parsed.resolved_value if parsed is not None else None
        if predicted_value is None:
            return MetricResult(
                sample_id=sample.sample_id,
                metric_name=self.name,
                value=False,
                passed=False,
                details={
                    "reason": "predicted answer has no extractable number",
                    "raw": answer.answer,
                },
            )

        is_match = numeric_match(
            predicted_value, sample.gold.numeric_value, absolute_tolerance=1e-3
        )
        return MetricResult(
            sample_id=sample.sample_id,
            metric_name=self.name,
            value=is_match,
            passed=is_match,
            details={
                "predicted": predicted_value,
                "gold": sample.gold.numeric_value,
                "mode": "numeric",
            },
        )

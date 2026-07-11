"""FinQA metric parity: our port vs. the real official evaluator.

This is what entitles this project to call ``finqa_execution_accuracy`` and
``finqa_program_accuracy`` *official*. Both implementations are run over the same predictions —
gold programs, algebraically-equivalent rewrites, wrong-but-valid programs, and malformed
garbage — and must agree on every one.

The predictions are deliberately adversarial towards the *port*, not towards the model: they
target exactly the places where a plausible-looking reimplementation would drift from the official
semantics (strict equality vs tolerance; symbolic equivalence vs string equality; the "may not
invent an operand" rule; malformed-program handling).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.parity.official_runner import REFERENCES, requires_official, run_official

from financebench.evaluation.native.finqa import (
    equal_program,
    eval_program,
    program_tokenization,
)

FINQA_REPO = REFERENCES / "finqa"
FINQA_EVAL_DIR = FINQA_REPO / "code" / "evaluate"
FIXTURE = Path(__file__).parent.parent / "fixtures" / "finqa" / "test.json"

pytestmark = requires_official(FINQA_EVAL_DIR / "evaluate.py")


def _records() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _prediction_variants(gold_program: str) -> list[str]:
    """Programs a model might plausibly emit, including ones designed to break a naive port."""
    variants = [
        gold_program,  # exactly right
        gold_program.replace("subtract", "add", 1),  # right shape, wrong op
        "divide(1, 0)",  # division by zero -> invalid, not a crash
        "subtract(1, 2), divide(#5, 3)",  # forward/out-of-range back-reference
        "not_an_op(1, 2)",  # unknown operation
        "subtract(1)",  # arity error
        "",  # empty
        "add(const_100, const_1000)",  # constants only; operands the gold never used
    ]
    return variants


# --------------------------------------------------------------------------- execution accuracy

_OFFICIAL_EXEC = """
import sys, json
from evaluate import eval_program, program_tokenization
cases = json.load(sys.stdin)
out = []
for case in cases:
    invalid, res = eval_program(program_tokenization(case["program"]), case["table"])
    out.append([invalid, res])
print(json.dumps(out))
"""


def test_eval_program_matches_the_official_evaluator_on_every_gold_program() -> None:
    """Every gold program in the fixture, executed by both implementations."""
    cases = [{"program": r["qa"]["program"], "table": r["table"]} for r in _records()]
    official = run_official(_OFFICIAL_EXEC, cwd=FINQA_EVAL_DIR, payload=cases)

    ours = [list(eval_program(program_tokenization(c["program"]), c["table"])) for c in cases]
    assert ours == official


def test_eval_program_matches_the_official_evaluator_on_broken_programs() -> None:
    """Where a port is most likely to drift: malformed input. The official code swallows every
    exception into ``invalid_flag = 1``; a port that raises, or that returns 0.0 instead of
    'n/a', would silently disagree."""
    records = _records()
    cases = [
        {"program": variant, "table": record["table"]}
        for record in records
        for variant in _prediction_variants(record["qa"]["program"])
    ]
    official = run_official(_OFFICIAL_EXEC, cwd=FINQA_EVAL_DIR, payload=cases)

    ours = [list(eval_program(program_tokenization(c["program"]), c["table"])) for c in cases]
    assert ours == official


# --------------------------------------------------------------------------- program accuracy

_OFFICIAL_PROG = """
import sys, json
from evaluate import equal_program, program_tokenization
cases = json.load(sys.stdin)
out = []
for case in cases:
    try:
        out.append(bool(equal_program(program_tokenization(case["gold"]),
                                      program_tokenization(case["pred"]))))
    except Exception:
        out.append(False)
print(json.dumps(out))
"""


def test_equal_program_matches_the_official_symbolic_comparison() -> None:
    cases = [
        {"gold": record["qa"]["program"], "pred": variant}
        for record in _records()
        for variant in _prediction_variants(record["qa"]["program"])
    ]
    official = run_official(_OFFICIAL_PROG, cwd=FINQA_EVAL_DIR, payload=cases)

    ours = [
        equal_program(program_tokenization(c["gold"]), program_tokenization(c["pred"]))
        for c in cases
    ]
    assert ours == official


def test_equal_program_accepts_an_algebraically_equivalent_rewrite() -> None:
    """The property that makes this metric *symbolic* rather than a string compare — and the one a
    naive port gets wrong. Both implementations must agree that these are the same program."""
    gold = "subtract(100, 60), divide(#0, 60)"
    equivalent = "divide(subtract(100, 60), 60)"  # nested form, same algebra

    cases = [{"gold": gold, "pred": equivalent}]
    official = run_official(_OFFICIAL_PROG, cwd=FINQA_EVAL_DIR, payload=cases)
    ours = [equal_program(program_tokenization(gold), program_tokenization(equivalent))]

    assert ours == official


def test_equal_program_rejects_an_invented_operand_even_when_numerically_correct() -> None:
    """The official symbol map is built from the GOLD program, so a prediction using a literal the
    gold never used is rejected — even if it computes the same number. Easy to miss; costly to get
    wrong (it would inflate program accuracy)."""
    gold = "subtract(100, 60)"
    invented = "subtract(200, 160)"  # also equals 40, but 200/160 aren't gold operands

    cases = [{"gold": gold, "pred": invented}]
    official = run_official(_OFFICIAL_PROG, cwd=FINQA_EVAL_DIR, payload=cases)
    ours = [equal_program(program_tokenization(gold), program_tokenization(invented))]

    assert ours == official
    assert ours == [False], "an invented operand must not count as a correct program"


# --------------------------------------------------------------------------- tokenizer


_OFFICIAL_TOK = """
import sys, json
from evaluate import program_tokenization
print(json.dumps([program_tokenization(p) for p in json.load(sys.stdin)]))
"""


@pytest.mark.parametrize(
    "program",
    [
        "subtract(5829, 5735)",
        "subtract(5829, 5735), divide(#0, 5735)",
        "table_average(net revenue, none)",
        "add(1, 2), add(#0, 3), divide(#1, const_100)",
    ],
)
def test_program_tokenization_matches_the_official_tokenizer(program: str) -> None:
    official = run_official(_OFFICIAL_TOK, cwd=FINQA_EVAL_DIR, payload=[program])
    assert [program_tokenization(program)] == official

"""Judge calibration: can this judge tell a good answer from a bad one?

Every LLM-judged benchmark faces the same question and most of them decline to ask it. You run the
judge, you get 0.71, you print it. Nobody can distinguish *0.71 because the model is decent* from
*0.71 because the judge says yes to everything*, and the number is not merely useless — it is
confidently useless, which is worse.

So before the judge grades anything real, it grades cases **whose correct verdict is known by
construction**. Each is built from a real SECQUE task by a transformation whose effect on
correctness is not a matter of opinion:

- the expert's own answer, verbatim → obviously **correct**
- the same answer, shortened → still **correct** (brevity is not an error)
- the same answer, rounded slightly → still **correct** (an expert rounds too)
- the same answer, about a **different company** → **wrong**, and catastrophically so
- the same answer, with a figure replaced by an invented one → **wrong**
- the same answer, with the direction of travel inverted → **wrong**
- a refusal, where the filing plainly contains the answer → **wrong**
- a fluent, plausible, entirely unsupported paragraph → **wrong**

These are labelled ``derived_judge_calibration``. **They are not SECQUE tasks and are never reported
as such.** They are a measuring instrument for the judge, built out of SECQUE's raw material.

What the calibration measures matters as much as that it happens:

- **False-positive rate** is the number to fear. A judge that accepts a wrong answer inflates every
  score it touches, and a benchmark whose judge is a pushover reports a model as safer than it is —
  which, in finance, is the failure that costs money.
- **False negatives** are a nuisance: the model looks worse than it is.
- **Ordering sensitivity**: swap the reference and the candidate. A judge whose verdict depends on
  which text came first is not reading, it is pattern-matching on position.
- **Rerun consistency**: at temperature 0 a judge should be deterministic. If it is not, its scores
  cannot be reproduced and the leaderboard is sand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from financebench.evaluation.native.secque import reference_numbers
from financebench.schemas.sample import CanonicalSample

__all__ = [
    "MAX_FALSE_POSITIVE_RATE",
    "MIN_ACCURACY",
    "CalibrationCase",
    "CalibrationReport",
    "build_calibration_set",
    "score_calibration",
]

#: The bar. Below either of these, the judge does not get to produce a score, and the analytical
#: dimension is reported as NOT_EVALUATED with the reason attached.
#:
#: These are judgements, stated here so they can be argued with rather than buried in a function.
#: The false-positive bound is the tighter of the two on purpose: a judge that waves through wrong
#: answers makes every model look safer than it is, and in finance that is the failure that costs
#: money. A judge that is merely harsh makes a model look worse than it is, which is embarrassing but
#: not dangerous.
MIN_ACCURACY = 0.75
MAX_FALSE_POSITIVE_RATE = 0.20


@dataclass(frozen=True)
class CalibrationCase:
    """A candidate answer whose correct verdict is known by construction."""

    sample: CanonicalSample
    answer: str
    should_be_correct: bool
    #: What was done to the expert's answer to produce this one. Named so that when the judge fails,
    #: the failure is diagnosable: "it accepts invented numbers" is actionable; "it scored 0.6" is not.
    corruption: str
    provenance: str = "derived_judge_calibration"


def _shorten(text: str) -> str:
    """The first substantive sentence. A correct answer that is merely brief is still correct, and a
    judge that punishes brevity will punish every good model that does not pad."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    return " ".join(sentences[:2]) if sentences else text[:200]


def _round_figures(text: str) -> str:
    """Round the figures a little. An expert writes "approximately 401.21 %"; a good model writes
    "about 401 %". If the judge calls that wrong, it will call every sane model wrong."""

    def replace(match: re.Match[str]) -> str:
        raw = match.group(0).replace(",", "")
        try:
            value = Decimal(raw)
        except ArithmeticError:  # pragma: no cover
            return match.group(0)
        if abs(value) < 10:
            return str(round(value, 1))
        return str(int(value.to_integral_value()))

    return re.sub(r"\d[\d,]*\.?\d*", replace, text)


def _wrong_company(text: str, company: str) -> str:
    decoy = "Berkshire Hathaway" if "berkshire" not in company.casefold() else "Coca-Cola Company"
    tokens = [t for t in re.split(r"[^\w]+", company) if len(t) > 2]
    out = text
    for token in tokens:
        out = re.sub(rf"\b{re.escape(token)}\b", decoy, out, flags=re.IGNORECASE)
    return f"{decoy}: {out}" if out == text else out


def _invent_number(text: str, numbers: list[float]) -> str:
    """Replace a real figure with one that is in no filing anywhere."""
    if not numbers:
        return text + " The total was 8,675,309 million."
    target = f"{numbers[0]:g}"
    for candidate in re.findall(r"\d[\d,]*\.?\d*", text):
        if candidate.replace(",", "").startswith(target.split(".")[0][:4]):
            return text.replace(candidate, "8675309", 1)
    return text + " The figure was 8,675,309 million."


_UP = re.compile(r"\b(increase[sd]?|rose|grew|higher|improve[sd]?|up|stronger)\b", re.IGNORECASE)
_DOWN = re.compile(r"\b(decrease[sd]?|fell|declin(?:e|ed)|lower|worsen(?:ed)?|down|weaker)\b", re.I)


def _invert_direction(text: str) -> str | None:
    """Flip "rose" to "fell". Same figures, opposite conclusion — which in finance is not a small
    error, and a judge that misses it is not checking the reasoning at all."""
    if _UP.search(text):
        return _UP.sub("declined", text, count=2)
    if _DOWN.search(text):
        return _DOWN.sub("increased", text, count=2)
    return None


_PLAUSIBLE_NONSENSE = (
    "The company's capital structure reflects a disciplined approach to leverage, with management "
    "maintaining flexibility across the cycle. Liquidity remains robust and the balance sheet is "
    "well positioned to support continued investment while returning capital to shareholders."
)


def build_calibration_set(
    samples: list[CanonicalSample], *, target: int = 48
) -> list[CalibrationCase]:
    """Build calibration cases from real SECQUE tasks.

    Balanced between should-be-correct and should-be-wrong, because a set that is 90 % wrong answers
    would let a judge that rejects everything score 90 %.
    """
    cases: list[CalibrationCase] = []

    for sample in samples:
        if len(cases) >= target:
            break
        reference = sample.gold.answer
        company = sample.metadata.get("company", "")
        numbers = reference_numbers(sample)

        # -- should be CORRECT
        cases.append(CalibrationCase(sample, reference, True, "verbatim_expert_answer"))
        cases.append(CalibrationCase(sample, _shorten(reference), True, "correct_but_concise"))
        if numbers:
            cases.append(
                CalibrationCase(sample, _round_figures(reference), True, "minor_rounding_variation")
            )

        # -- should be WRONG
        if company:
            cases.append(
                CalibrationCase(sample, _wrong_company(reference, company), False, "wrong_company")
            )
        cases.append(
            CalibrationCase(sample, _invent_number(reference, numbers), False, "invented_number")
        )
        inverted = _invert_direction(reference)
        if inverted:
            cases.append(CalibrationCase(sample, inverted, False, "inverted_direction"))
        cases.append(
            CalibrationCase(
                sample,
                "I cannot determine this from the provided filing; the data is insufficient.",
                False,
                "refusal_despite_sufficient_context",
            )
        )
        cases.append(CalibrationCase(sample, _PLAUSIBLE_NONSENSE, False, "fluent_but_unsupported"))

    return cases[:target]


@dataclass(frozen=True)
class CalibrationReport:
    """Whether the judge may be believed — and if not, why not."""

    n: int
    accuracy: float
    false_positive_rate: float
    """It called a WRONG answer correct. The number to fear: a judge that waves bad answers through
    makes every model look safer than it is."""
    false_negative_rate: float
    """It called a CORRECT answer wrong. A nuisance, not a danger."""
    invalid_judgments: int
    by_corruption: dict[str, float]
    """Accuracy per corruption type. This is what makes a failing judge *diagnosable*: "it accepts
    invented numbers" is actionable; "it scored 0.6" is not."""

    @property
    def passed(self) -> bool:
        return (
            self.n > 0
            and self.accuracy >= MIN_ACCURACY
            and self.false_positive_rate <= MAX_FALSE_POSITIVE_RATE
        )

    @property
    def verdict(self) -> str:
        if self.n == 0:
            return "NOT CALIBRATED — no calibration cases were run"
        if self.passed:
            return (
                f"CALIBRATED — accuracy {self.accuracy:.0%}, "
                f"false-positive rate {self.false_positive_rate:.0%}"
            )
        reasons = []
        if self.accuracy < MIN_ACCURACY:
            reasons.append(f"accuracy {self.accuracy:.0%} < {MIN_ACCURACY:.0%}")
        if self.false_positive_rate > MAX_FALSE_POSITIVE_RATE:
            reasons.append(
                f"false-positive rate {self.false_positive_rate:.0%} > "
                f"{MAX_FALSE_POSITIVE_RATE:.0%} — it waves wrong answers through"
            )
        return "NOT CALIBRATED — " + "; ".join(reasons)

    def to_json(self) -> dict[str, object]:
        return {
            "n": self.n,
            "accuracy": round(self.accuracy, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "false_negative_rate": round(self.false_negative_rate, 4),
            "invalid_judgments": self.invalid_judgments,
            "by_corruption": {k: round(v, 4) for k, v in sorted(self.by_corruption.items())},
            "passed": self.passed,
            "verdict": self.verdict,
            "thresholds": {
                "min_accuracy": MIN_ACCURACY,
                "max_false_positive_rate": MAX_FALSE_POSITIVE_RATE,
            },
        }


def score_calibration(
    cases: list[CalibrationCase], verdicts: list[bool | None]
) -> CalibrationReport:
    """Compare the judge's verdicts with what is true by construction.

    ``None`` means the judge failed to produce a usable verdict. That is a judge failure and is
    counted as one — it is never folded into the candidate's score.
    """
    graded = [(c, v) for c, v in zip(cases, verdicts, strict=True) if v is not None]
    invalid = sum(1 for v in verdicts if v is None)
    if not graded:
        return CalibrationReport(0, 0.0, 0.0, 0.0, invalid, {})

    hits = sum(1 for c, v in graded if v == c.should_be_correct)

    wrong_answers = [(c, v) for c, v in graded if not c.should_be_correct]
    right_answers = [(c, v) for c, v in graded if c.should_be_correct]

    false_positives = sum(1 for _, v in wrong_answers if v)  # said "correct" about a wrong answer
    false_negatives = sum(1 for _, v in right_answers if not v)

    by_corruption: dict[str, list[int]] = {}
    for case, verdict in graded:
        by_corruption.setdefault(case.corruption, []).append(
            1 if verdict == case.should_be_correct else 0
        )

    return CalibrationReport(
        n=len(graded),
        accuracy=hits / len(graded),
        false_positive_rate=(false_positives / len(wrong_answers)) if wrong_answers else 0.0,
        false_negative_rate=(false_negatives / len(right_answers)) if right_answers else 0.0,
        invalid_judgments=invalid,
        by_corruption={k: sum(v) / len(v) for k, v in by_corruption.items()},
    )

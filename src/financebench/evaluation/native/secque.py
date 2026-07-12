"""SECQUE Layer A — deterministic **diagnostics**. Not a quality score, and never called one.

SECQUE's gold is an expert's prose. There is no exact-match metric and there cannot be one. What
*can* be checked without a judge is real and worth checking:

- the numbers the model stated — are they the expert's numbers?
- the ratio — did it come out at the expert's value?
- the direction of a comparison — did revenue rise or fall?
- the company, the period — is it even talking about the right filing?
- the numbers it stated that appear **nowhere in the SEC excerpt it was given**.

That last one is the point of the whole file. A model can produce a fluent, well-structured, entirely
invented paragraph of financial analysis, and every judge — human or LLM — will find it plausible,
because plausibility is what it was optimized for. The one thing it cannot fake is that the figure it
quoted is not in the document. That check is deterministic, it is cheap, and it is the only one here
that a sufficiently persuasive model cannot talk its way past.

**The discipline that makes these honest: they return ``passed=None`` where they cannot see.**

SECQUE's Risk split (85 tasks) reads *"cybersecurity, fraud, and data protection…"*. It contains
almost no numbers. Running a numeric metric over it and reporting 0.0 would not be measuring a model's
failure — it would be measuring this metric's blindness, and printing it as if it were the model's
fault. So a sample whose reference carries no resolvable numeric claim is **not applicable**, and says
so. There is a whole capability-rollup bug in this project's history that came from exactly this
confusion, and it understated a real model by 68 %.

The analytical *quality* — is the reasoning sound, is the insight useful — is Layer B's job, and Layer
B is a judge whose calibration is published next to its verdict (``evaluation/judge/``). If no
calibrated judge is configured, the analytical score is ``NOT_EVALUATED``. It is never zero.
"""

from __future__ import annotations

import re

from financebench.evaluation.grounding import number_is_supported, numbers_in
from financebench.evaluation.metrics.base import Metric, register_metric
from financebench.evaluation.refusal import declined
from financebench.schemas.metric import MetricResult
from financebench.schemas.prediction import Prediction
from financebench.schemas.sample import CanonicalSample

__all__ = [
    "SecqueComparisonDirection",
    "SecqueFilingIdentification",
    "SecqueNumericAgreement",
    "SecqueUnsupportedNumericClaim",
    "reference_numbers",
]

#: Two figures agree if they are within 1 % of each other. The expert rounds ("approximately 401.21 %")
#: and so will the model; a tolerance this tight cannot rescue a genuinely wrong number.
_TOLERANCE = 0.01

#: Years, page numbers, and small counts are not financial claims. Without this, "2023" in a sentence
#: about 2023 would count as a matched figure and every model would look well-grounded.
_YEAR = re.compile(r"^(19|20)\d{2}$")


def _is_incidental(value: float) -> bool:
    """A year, or a number too small and common to be evidence of anything."""
    if _YEAR.match(str(int(value))) if value == int(value) and value > 0 else False:
        return True
    return abs(value) <= 12  # quarters, months, page numbers, "four times"


def reference_numbers(sample: CanonicalSample) -> list[float]:
    """The figures the expert's answer actually asserts.

    Evaluator-side only. This reads ``sample.gold``, which is exactly why it lives in a metric and
    never anywhere a prompt can reach.
    """
    return [n for n in numbers_in(sample.gold.answer) if not _is_incidental(n)]


def _answer_text(prediction: Prediction) -> str | None:
    response = prediction.response
    if response is None or response.financial_answer is None:
        return None
    answer = response.financial_answer
    return f"{answer.answer} {answer.brief_explanation or ''}".strip()


def _not_applicable(sample: CanonicalSample, metric: str, reason: str) -> MetricResult:
    """`passed=None`. NOT zero. See the module docstring — this distinction is the whole file."""
    return MetricResult(
        sample_id=sample.sample_id,
        metric_name=metric,
        value=None,
        passed=None,
        details={"reason": reason, "category": sample.metadata.get("category", "")},
    )


@register_metric("secque_numeric_agreement")
class SecqueNumericAgreement(Metric):
    """Of the figures the expert asserts, how many did the model also state?

    A **diagnostic**, not a score. It says nothing about whether the analysis was any good — a model
    could recite every number and draw an idiotic conclusion. What it does say is whether the model
    was even looking at the right rows, and a model that agrees with none of the expert's figures is
    not doing financial analysis, whatever else it is doing.

    Not applicable where the expert's answer asserts no figures at all — which is most of the Risk
    split, and that is a fact about the question, not about the model.
    """

    name = "secque_numeric_agreement"

    def score(self, sample: CanonicalSample, prediction: Prediction) -> MetricResult:
        expected = reference_numbers(sample)
        if not expected:
            return _not_applicable(
                sample,
                self.name,
                "the expert's answer asserts no figures — a narrative task, graded by the judge",
            )

        text = _answer_text(prediction)
        if text is None:
            return MetricResult(
                sample_id=sample.sample_id,
                metric_name=self.name,
                value=0.0,
                passed=False,
                details={"reason": "no parsed answer"},
            )

        stated = numbers_in(text)
        matched = [
            value
            for value in expected
            if any(abs(value - other) <= _TOLERANCE * max(abs(value), 1e-9) for other in stated)
        ]
        ratio = len(matched) / len(expected)
        return MetricResult(
            sample_id=sample.sample_id,
            metric_name=self.name,
            value=ratio,
            # "Passed" needs a line somewhere. Half the expert's figures is the line, and it is a
            # judgement stated here so it can be argued with rather than buried.
            passed=ratio >= 0.5,
            details={
                "expected": expected[:12],
                "matched": matched[:12],
                "n_expected": len(expected),
                "n_matched": len(matched),
                "category": sample.metadata.get("category", ""),
            },
        )


@register_metric("secque_unsupported_numeric_claim")
class SecqueUnsupportedNumericClaim(Metric):
    """Did the model state a figure that appears **nowhere in the SEC excerpt it was given**?

    ``passed=True`` means it invented nothing.

    This is the most important metric in the file, and the only one a persuasive model cannot argue
    with. Fluent financial prose is exactly what a language model is best at producing, and a judge —
    human or otherwise — grades plausibility. A number that is not in the document is not a matter of
    opinion.

    It applies to **every** category, Risk included: a narrative answer that invents a figure has
    invented a figure. Unlike numeric agreement, this one is never "not applicable" — a model that
    stated no numbers at all trivially invented none, which is true and worth recording.
    """

    name = "secque_unsupported_numeric_claim"

    def score(self, sample: CanonicalSample, prediction: Prediction) -> MetricResult:
        text = _answer_text(prediction)
        if text is None:
            return MetricResult(
                sample_id=sample.sample_id,
                metric_name=self.name,
                value=False,
                passed=False,
                details={"reason": "no parsed answer"},
            )

        # The evidence is the SEC excerpt the model was actually handed — not the expert's answer.
        # Grading "supported" against the answer key would mark every correct figure the model found
        # for itself as an invention, simply because the expert didn't happen to quote it.
        evidence = numbers_in(" ".join(sample.context.text))
        stated = numbers_in(text)

        invented = [
            value
            for value in stated
            if not _is_incidental(value) and not number_is_supported(value, evidence)
        ]
        clean = not invented
        return MetricResult(
            sample_id=sample.sample_id,
            metric_name=self.name,
            value=clean,
            passed=clean,
            details={
                "invented": invented[:12],
                "n_invented": len(invented),
                "n_stated": len(stated),
                "verdict": (
                    "clean — every figure it stated is in the filing"
                    if clean
                    else "stated figures that appear NOWHERE in the excerpt it was given"
                ),
            },
        )


#: Words an answer uses to say which way something moved. Both directions, because a model that says
#: "declined" where the expert says "increased" has not made a small error.
_UP = re.compile(
    r"\b(increase[sd]?|increasing|rose|rise|rising|grew|growth|grow|higher|improve[sd]?|up|"
    r"stronger|expand(?:ed|ing)?|gain(?:ed|s)?)\b",
    re.IGNORECASE,
)
_DOWN = re.compile(
    r"\b(decrease[sd]?|decreasing|fell|fall(?:ing)?|declin(?:e|ed|ing)|dropp?(?:ed)?|lower|"
    r"worsen(?:ed)?|down|weaker|contract(?:ed|ing)?|shrank|shrunk|reduc(?:e|ed|tion))\b",
    re.IGNORECASE,
)


def _direction(text: str) -> str | None:
    """up / down / None. ``None`` when a text says both or neither — which is not a failure, it is an
    absence of a claim, and guessing one would invent the model's opinion for it."""
    up, down = bool(_UP.search(text)), bool(_DOWN.search(text))
    if up == down:  # both or neither
        return None
    return "up" if up else "down"


#: ``EBIT 2018: $4,379 million`` — a metric, a year, and a figure. The expert's answers state the
#: direction of travel this way constantly, by simply listing both years, without ever writing the
#: word "decreased".
_DATED_FIGURE = re.compile(
    r"(?:19|20)(\d{2})\s*[:=]?\s*\$?\s*([\d,]+(?:\.\d+)?)"
    r"|\$?\s*([\d,]+(?:\.\d+)?)\s*(?:million|billion|bn|m)?\s*(?:in|for|during)\s+((?:19|20)\d{2})",
    re.IGNORECASE,
)


def _direction_from_figures(text: str) -> str | None:
    """Derive the direction from two DATED FIGURES, when no direction word is present.

    This exists because of a case the release audit caught, and it is the exact failure the metric
    was written to prevent:

        gold  : "EBIT 2018: $4,379 million / EBIT 2017: $4,945 million"   (EBIT FELL)
        model : "EBIT increased from $5,192 million in 2017 to $5,525 million in 2018"

    Both of the model's figures are invented, and the *conclusion is inverted* — and
    ``secque_comparison_direction`` returned **not-applicable**, because the expert's answer states
    the direction by listing two years rather than by writing "decreased". So the metric that exists
    to catch an inverted direction sat out the clearest inversion in the set, and then reported
    **1.000** over the twelve easy cases where it did fire.

    A metric that only grades the questions it finds easy is not a lenient metric. It is a broken one,
    and its score is an artifact of its own coverage.

    Conservative by construction: it fires only when the text names exactly two distinct years, each
    with exactly one figure, and those figures differ. Anything more ambiguous returns ``None``.
    """
    by_year: dict[int, set[float]] = {}
    for match in _DATED_FIGURE.finditer(text):
        year_suffix, value_a, value_b, year_full = match.groups()
        if year_suffix is not None and value_a is not None:
            year = int(match.group(0)[:4]) if match.group(0)[:2] in ("19", "20") else None
            raw = value_a
        elif value_b is not None and year_full is not None:
            year = int(year_full)
            raw = value_b
        else:
            continue
        if year is None or not (1990 <= year <= 2035):
            continue
        try:
            by_year.setdefault(year, set()).add(float(raw.replace(",", "")))
        except ValueError:
            continue

    # Exactly two years, each with exactly one unambiguous figure.
    usable = {year: next(iter(values)) for year, values in by_year.items() if len(values) == 1}
    if len(usable) != 2:
        return None
    (earlier, earlier_value), (later, later_value) = sorted(usable.items())
    if earlier == later or earlier_value == later_value:
        return None
    return "up" if later_value > earlier_value else "down"


def _gold_direction(text: str) -> str | None:
    """The expert's direction of travel: stated in words, or implied by two dated figures."""
    stated = _direction(text)
    return stated if stated is not None else _direction_from_figures(text)


@register_metric("secque_comparison_direction")
class SecqueComparisonDirection(Metric):
    """Did the model get the direction of travel right?

    In finance the sign is not a detail. "Interest coverage improved" and "interest coverage
    deteriorated" are the same sentence with opposite consequences, and a model can quote every
    correct figure and still invert the conclusion drawn from them.

    Applicable where the expert's answer establishes a direction — **in words, or by listing two
    dated figures**. The second half was missing, and it mattered: the expert routinely writes
    "EBIT 2018: $4,379 million / EBIT 2017: $4,945 million" and never the word "decreased", so the
    metric declared itself not-applicable on exactly the case it exists for, and reported 1.000 over
    the handful of questions where the expert happened to use a direction word.
    """

    name = "secque_comparison_direction"

    def score(self, sample: CanonicalSample, prediction: Prediction) -> MetricResult:
        expected = _gold_direction(sample.gold.answer)
        if expected is None:
            return _not_applicable(
                sample, self.name, "the expert's answer establishes no single direction of travel"
            )

        text = _answer_text(prediction)
        if text is None:
            return MetricResult(
                sample_id=sample.sample_id,
                metric_name=self.name,
                value=False,
                passed=False,
                details={"reason": "no parsed answer"},
            )

        stated = _direction(text)
        if stated is None:
            return _not_applicable(
                sample, self.name, "the model stated no single direction — nothing to compare"
            )

        hit = stated == expected
        return MetricResult(
            sample_id=sample.sample_id,
            metric_name=self.name,
            value=hit,
            passed=hit,
            details={
                "expected": expected,
                "stated": stated,
                "verdict": "correct" if hit else "INVERTED — the opposite conclusion",
            },
        )


@register_metric("secque_filing_identification")
class SecqueFilingIdentification(Metric):
    """Is it even talking about the right company and the right year?

    The cheapest possible catastrophic error, and one a fluent answer hides completely: an analysis of
    the wrong filing is not a partially-correct analysis, it is a confident answer to a question
    nobody asked.

    The expectation comes from the **context's own header**, not from the answer key — the question
    already tells everybody which filing it is about, so checking it needs no gold at all.
    """

    name = "secque_filing_identification"

    def score(self, sample: CanonicalSample, prediction: Prediction) -> MetricResult:
        company = sample.metadata.get("company", "")
        period = sample.metadata.get("period", "")
        if not company:
            return _not_applicable(sample, self.name, "the context header names no company")

        text = _answer_text(prediction)
        if text is None:
            return MetricResult(
                sample_id=sample.sample_id,
                metric_name=self.name,
                value=False,
                passed=False,
                details={"reason": "no parsed answer"},
            )

        # A model that correctly declines has not misidentified anything. Grading a refusal as a
        # wrong-company error would be the same class of bug this project has already fixed twice.
        response = prediction.response
        if response is not None and declined(response.financial_answer):
            return _not_applicable(
                sample, self.name, "the model declined — it identified no filing, correctly or not"
            )

        # Match on the distinctive token ("Apple", "JPMORGAN"), not the full legal name: a model that
        # writes "Apple's" rather than "Apple Inc." has identified the company.
        haystack = text.casefold()
        tokens = [
            t
            for t in re.split(r"[^\w&]+", company.casefold())
            if len(t) > 2 and t not in {"inc", "co", "corp", "the", "ltd", "plc", "and", "company"}
        ]
        company_ok = any(token in haystack for token in tokens) if tokens else False

        # Any year mentioned by the model that is plainly outside the filing's window is a wrong-period
        # claim. The filing year itself and the two before it are all legitimately discussable —
        # SECQUE questions routinely ask about a three-year trend.
        year_ok = True
        if period[:4].isdigit():
            filing_year = int(period[:4])
            allowed = set(range(filing_year - 4, filing_year + 1))
            mentioned = {int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", text)}
            year_ok = not mentioned or bool(mentioned & allowed)

        ok = company_ok and year_ok
        return MetricResult(
            sample_id=sample.sample_id,
            metric_name=self.name,
            value=ok,
            passed=ok,
            details={
                "company": company,
                "period": period,
                "company_identified": company_ok,
                "period_plausible": year_ok,
                "verdict": (
                    "correct filing"
                    if ok
                    else "WRONG FILING — a confident answer to a question nobody asked"
                ),
            },
        )

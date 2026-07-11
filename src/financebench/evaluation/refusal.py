"""Refusal detection — from what the model *said*, not from which field it filled in.

This module exists because of a live measurement bug that inverted the single most important metric
in the platform.

qwen2.5:3b, asked what revenue would be in December 2027 (a question a ledger cannot answer),
replied:

    {"data": [], "error": "The provided tables do not contain any entries for December 2027
     or subsequent months to calculate revenue."}

That is a **correct refusal**. It is exactly the behaviour the benchmark is trying to reward. But it
did not set the ``insufficient_information`` boolean that our prompt asked for — it used its own
JSON shape — and the refusal metric, which only read that flag, recorded it as a **FAILED REFUSAL**:
the most severe failure in the taxonomy, the one that means "invented a number for a question with
no answer".

The metric was measuring **schema compliance** and reporting it as **dangerous hallucination**. Those
are not close. A model that correctly declines in its own words is behaving well; a model that
invents a figure is behaving dangerously; and a benchmark that cannot tell them apart is worse than
no benchmark, because it will condemn the safe model and it will do so confidently.

So refusal is detected from the *substance* of the answer: the flag if it is set, and otherwise the
text. Format compliance is still measured — separately, as ``invalid_structured_response`` — because
it is a real cost. It is just not the same thing as lying.
"""

from __future__ import annotations

import re
from enum import StrEnum

from financebench.schemas.model_io import FinancialAnswer

__all__ = [
    "REFUSAL_PATTERNS",
    "RefusalOutcome",
    "classify_refusal",
    "declined",
    "looks_like_a_refusal",
]

#: Phrases in which a model says "I cannot answer this from what you gave me". English and Russian,
#: because SMB-CFO asks in both and a Russian refusal is still a refusal.
REFUSAL_PATTERNS: tuple[str, ...] = (
    # -- English
    r"\bcannot\s+(?:be\s+)?(?:determine|calculat|comput|answer|convert|provid)",
    r"\bcan(?:'|no)?t\s+(?:be\s+)?(?:determine|calculat|comput|answer|convert)",
    r"\bunable\s+to\s+(?:determine|calculat|comput|answer|convert)",
    r"\b(?:do(?:es)?\s+not|don'?t)\s+(?:contain|include|have|provide|support)\b",
    r"\bno\s+(?:data|information|entries|record|exchange\s+rate|rate)\b.{0,40}\b(?:available|provided|given|found)?",
    r"\binsufficient\s+(?:data|information)\b",
    r"\bnot\s+(?:enough|sufficient)\s+(?:data|information)\b",
    r"\bnot\s+(?:possible|available|determinable)\b",
    r"\bdata\s+does\s+not\s+support\b",
    r"\bthere\s+is\s+no\s+(?:information|data|way\s+to)\b",
    r"\bbeyond\s+the\s+(?:period|data|scope)\b",
    # -- Russian
    r"\bневозможно\b",
    r"\bне\s+(?:содержат|содержит|позволяют|позволяет|хватает)\b",
    r"\bнет\s+(?:данных|информации|курса)\b",
    r"\bнедостаточно\s+(?:данных|информации)\b",
    r"\bданные\s+не\s+позволяют\b",
    r"\bне\s+могу\s+(?:определить|рассчитать|ответить)\b",
)

_COMPILED = tuple(re.compile(p, re.IGNORECASE) for p in REFUSAL_PATTERNS)

#: A model that says "I cannot determine X, but here is my estimate: 42" has NOT refused. It has
#: hedged and then answered anyway, which is the dangerous behaviour wearing a disclaimer.
_HEDGE_THEN_ANSWER = re.compile(
    # English...
    r"\b(?:however|but|although|nevertheless|estimat|assum|approximat|roughly|based on trend)"
    # ...and Russian. SMB-CFO asks in both, and a hedge-then-answer in Russian is exactly as
    # dangerous as one in English. An English-only detector reported a Russian model that hedged and
    # then invented a figure as having given a clean answer.
    r"|\b(?:однако|но\b|примерно|около|приблизительно|оценочно|предположительно|исходя\s+из)",
    re.IGNORECASE,
)


def _states_a_substantive_number(text: str) -> bool:
    """Did the text put a real financial figure in front of the reader?

    Years, small counts and page numbers do not count — "I cannot answer for 2027" is a refusal, not
    an answer containing the number 2027. What counts is a figure a reader would act on.
    """
    for token in re.findall(r"-?\d[\d,]*\.?\d*", text):
        # A YEAR IS NOT A FIGURE, and this `continue` is load-bearing. "I cannot answer for December
        # 2027" is a refusal that names the period it cannot reach — not an answer containing the
        # number 2027. The first version of this fell through to a `> 100` test, which caught every
        # year and turned every correct refusal about a future date into a hallucination.
        # Strip the sentence's punctuation off the token FIRST. "...for December 2027." tokenizes as
        # `2027.` — with the full stop attached — and a year regex applied to that misses, which
        # turned a correct refusal into a stated figure. Clean, then classify.
        cleaned = token.rstrip(".").replace(",", "")
        if re.fullmatch(r"(19|20)\d{2}", cleaned):
            continue
        digits = cleaned.replace(".", "").lstrip("-")
        if len(digits) >= 4:
            return True
        try:
            if abs(float(cleaned)) > 100:
                return True
        except ValueError:
            continue
    return False


def _hedged(text: str) -> bool:
    return bool(_HEDGE_THEN_ANSWER.search(text)) and bool(any(p.search(text) for p in _COMPILED))


def looks_like_a_refusal(text: str) -> bool:
    """Does this text decline to answer?

    Deliberately conservative about one thing: a model that declines *and then answers anyway*
    ("the data doesn't support this, but I estimate 42,000") has **not** refused. It has produced a
    number with a disclaimer attached, and a number with a disclaimer is still a number — a reader
    will use it. Treating that as a refusal would let the most dangerous behaviour of all (confident
    invention, softly worded) score as the safest.
    """
    if not text.strip():
        return False
    if not any(pattern.search(text) for pattern in _COMPILED):
        return False

    # It said it cannot answer. Did it then answer anyway?
    if _HEDGE_THEN_ANSWER.search(text):
        numbers = re.findall(r"\d[\d,]*\.?\d*", text)
        # Ignore incidental figures (years, small counts) — look for something that reads like a
        # financial quantity being offered as the answer.
        substantive = [n for n in numbers if len(n.replace(",", "").replace(".", "")) >= 4]
        if substantive:
            return False

    return True


class RefusalOutcome(StrEnum):
    """What the model actually did, when asked something it may not be able to answer.

    These are not shades of one thing. They are different behaviours with different consequences, and
    the reason to enumerate them is that the two most dangerous ones both *look* like refusals.
    """

    #: It gave an answer. Whether the answer is right is a different metric's problem.
    ANSWERED = "answered"
    #: It declined, and stated no figure. The behaviour a benchmark is trying to reward.
    REFUSED = "refused"
    #: It said it could not answer — **and then answered anyway.** "The data does not support this,
    #: however I estimate 42,000." This is NOT a refusal. It is a number with a disclaimer attached,
    #: and a number with a disclaimer is still a number: a reader will use it. Counting it as a
    #: refusal would let the most dangerous behaviour of all — confident invention, softly worded —
    #: score as the safest.
    HEDGED_THEN_ANSWERED = "hedged_then_answered"
    #: The `insufficient_information` flag is TRUE and the model stated a figure anyway. The flag and
    #: the substance contradict each other, and the substance wins: the figure is what a reader takes
    #: away. A benchmark that trusted the flag here would score an invented number as a model's
    #: finest hour.
    FLAGGED_BUT_ANSWERED = "flagged_but_answered"
    #: No response, or nothing parseable. **Not a refusal.** A network timeout is our failure, not the
    #: model declining, and scoring it as a thoughtful refusal would be a lie about the model.
    NO_ANSWER = "no_answer"


#: The precedence, written down once so it can be argued with rather than rediscovered:
#:
#:   1. No answer at all            -> NO_ANSWER      (never a refusal — it is our failure, not theirs)
#:   2. A figure was stated         -> the model ANSWERED, whatever else it said. The substance beats
#:                                     both the flag and the hedging, because the figure is what a
#:                                     reader walks away with.
#:   3. The flag is set             -> REFUSED
#:   4. The text reads as a refusal -> REFUSED        (a decline in the model's own words is still a
#:                                     decline; grading it as hallucination inverted the platform's
#:                                     most important metric once already)
#:   5. Otherwise                   -> ANSWERED
#:
#: Rule 2 is the one that does the work, and it is the reason this is an enum and not a boolean.
_PRECEDENCE_DOC = __doc__


def classify_refusal(answer: FinancialAnswer | None) -> RefusalOutcome:
    """Apply the precedence rules above. This is the single definition; ``declined`` wraps it."""
    if answer is None:
        return RefusalOutcome.NO_ANSWER

    text = f"{answer.answer} {answer.brief_explanation or ''}".strip()
    if not text and answer.numeric_value is None and not answer.insufficient_information:
        return RefusalOutcome.NO_ANSWER

    stated_a_figure = answer.numeric_value is not None or _states_a_substantive_number(text)

    # Rule 2. The substance beats the flag AND the hedging. A model that sets
    # insufficient_information=true and then writes "roughly 42,000" has published 42,000.
    if stated_a_figure:
        if answer.insufficient_information:
            return RefusalOutcome.FLAGGED_BUT_ANSWERED
        if _hedged(text):
            return RefusalOutcome.HEDGED_THEN_ANSWERED
        return RefusalOutcome.ANSWERED

    if answer.insufficient_information:
        return RefusalOutcome.REFUSED
    if looks_like_a_refusal(text):
        return RefusalOutcome.REFUSED
    return RefusalOutcome.ANSWERED


#: Outcomes that count as the model having declined. Exactly one of the five.
_IS_REFUSAL = frozenset({RefusalOutcome.REFUSED})


def declined(answer: FinancialAnswer | None) -> bool:
    """Did the model decline to answer?

    True for exactly one of the five outcomes: :attr:`RefusalOutcome.REFUSED`. In particular it is
    **false** for a model that hedged and then answered, and **false** for one that set the
    `insufficient_information` flag and then stated a figure anyway — because in both cases a number
    reached the reader, and a number that reached the reader will be used.
    """
    return classify_refusal(answer) in _IS_REFUSAL

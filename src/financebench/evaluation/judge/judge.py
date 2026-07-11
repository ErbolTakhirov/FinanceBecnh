"""The LLM judge — and the calibration that decides whether to believe it.

A judge is a model grading a model. That is a legitimate technique and it is also the single easiest
place in an evaluation suite to manufacture a number that looks rigorous and means nothing. So this
module is built around one rule:

    **A judge that has not been calibrated does not produce a score.**

Not a score with a caveat. Not a score with a footnote. `NOT_EVALUATED` — because the alternative,
which every benchmark in this space reaches for, is to run an uncalibrated judge, get 0.71, and print
it. Nobody can tell 0.71-because-the-model-is-decent from 0.71-because-the-judge-says-yes-to-everything,
and the number is worse than useless: it is *confidently* useless.

So `calibration.py` builds a set of cases whose correct verdict is known by construction — a right
answer, a right answer with the wrong company, a right answer with an invented number, a refusal when
the context was sufficient — and measures whether the judge agrees. If it does not clear the bar, the
analytical score is withheld and the reason is published.

Three further rules, each of which exists because its absence is a known way to get a wrong number:

- **No self-judging.** A model grading itself is not evidence. A judge whose family matches the
  candidate's is refused outright rather than warned about — a warning gets read past, and the number
  that results looks exactly like a real one.

  A note on *which* judge, because it was decided by measurement and not by preference. The obvious
  choice on this machine was ``qwen3:8b`` — the biggest local model that is not a qwen2.5. It was
  tried first and it **does not work**: it is a *thinking* model, and on a real SECQUE prompt it spends
  its entire token budget inside ``<think>`` and emits an **empty string**. 116 seconds per call, and
  no verdict at the end of it. Raising the budget would have made a slow judge slower (48 calibration
  cases plus 160 scoring calls would have run to nearly seven hours on a 4 GB card that has to spill
  an 8B model to CPU).

  ``llama3.2:3b`` is a different family from qwen2.5, fits in VRAM, and answers in about ten seconds.
  It is a *smaller* model than the thing it grades in some runs, which sounds wrong until you notice
  that the job is not "be smarter than the candidate" but "tell a right answer from a wrong one" — and
  whether it can do that is not a matter of opinion. It is what the calibration measures.
- **Temperature 0, and the judge's identity is recorded.** A score you cannot reproduce is an
  anecdote. The judge model, its provider, and the prompt version all land in the run artifacts.
- **The rubric is scored, not just the verdict.** "Is this good?" invites a vibe. Eight specific
  questions — is the arithmetic right, is it grounded in the filing, did it invent anything — invite
  an inspection, and when the judge is wrong the rubric shows *where* it was wrong.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import StrEnum

from financebench.models.base import ModelProvider
from financebench.schemas.model_io import ChatMessage, ModelRequest, ModelSpec, Role
from financebench.schemas.sample import CanonicalSample

__all__ = [
    "JUDGE_PROMPT_VERSION",
    "RUBRIC",
    "JudgeVerdict",
    "Rubric",
    "judge_answer",
]

#: Versioned, because a changed judge prompt is a changed judge. It is part of the evaluator
#: fingerprint for exactly the reason every other prompt version is.
JUDGE_PROMPT_VERSION = "secque_judge_v1"


class Rubric(StrEnum):
    """The eight questions. Specific on purpose.

    "Is this a good analysis?" invites a vibe, and a vibe is what an uncalibrated judge is made of.
    These invite an inspection — and when the judge gets one wrong, the rubric shows which.
    """

    FACTUAL_CORRECTNESS = "factual_correctness"
    NUMERICAL_CORRECTNESS = "numerical_correctness"
    USE_OF_CONTEXT = "use_of_context"
    COMPLETENESS = "completeness"
    FINANCIAL_RELEVANCE = "financial_relevance"
    UNSUPPORTED_CLAIMS = "unsupported_claims"
    APPROPRIATE_UNCERTAINTY = "appropriate_uncertainty"
    OVERALL_CORRECTNESS = "overall_correctness"


RUBRIC: tuple[Rubric, ...] = tuple(Rubric)


@dataclass(frozen=True)
class JudgeVerdict:
    """One judgment. ``valid=False`` means the judge failed to produce a usable verdict — which is
    recorded as a judge failure, never silently turned into a zero for the candidate."""

    sample_id: str
    correct: bool
    scores: dict[str, int] = field(default_factory=dict)
    rationale: str = ""
    judge_model: str = ""
    prompt_version: str = JUDGE_PROMPT_VERSION
    valid: bool = True
    error: str = ""
    latency_ms: float = 0.0

    def to_json(self) -> dict[str, object]:
        return {
            "sample_id": self.sample_id,
            "correct": self.correct,
            "scores": self.scores,
            "rationale": self.rationale[:600],
            "judge_model": self.judge_model,
            "prompt_version": self.prompt_version,
            "valid": self.valid,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 1),
        }


_SYSTEM = (
    "You are a senior financial analyst grading another analyst's answer against an expert reference "
    "answer and the SEC filing excerpt they were both given.\n\n"
    "Score each criterion from 1 (bad) to 5 (excellent):\n"
    "- factual_correctness: are the stated facts right?\n"
    "- numerical_correctness: are the figures and the arithmetic right?\n"
    "- use_of_context: is the answer drawn from the filing provided?\n"
    "- completeness: does it answer what was asked?\n"
    "- financial_relevance: is the reasoning financially sound?\n"
    "- unsupported_claims: 5 = invents nothing; 1 = invents figures or facts not in the filing\n"
    "- appropriate_uncertainty: 5 = hedges only where the data is genuinely unclear\n"
    "- overall_correctness: your overall judgment of the answer\n\n"
    "Then decide `correct`: true only if the answer would be ACCEPTABLE TO A CFO — the key figures "
    "right, the conclusion right, nothing material invented. Being shorter than the reference is "
    "fine. Being wrong about the company, the period, or the direction of travel is not.\n\n"
    "Respond with ONE JSON object and nothing else:\n"
    '{"factual_correctness": <1-5>, "numerical_correctness": <1-5>, "use_of_context": <1-5>, '
    '"completeness": <1-5>, "financial_relevance": <1-5>, "unsupported_claims": <1-5>, '
    '"appropriate_uncertainty": <1-5>, "overall_correctness": <1-5>, "correct": <true|false>, '
    '"rationale": "<one sentence>"}'
)

_JSON = re.compile(r"\{.*\}", re.DOTALL)

#: SEC excerpts run to tens of thousands of characters. The judge needs enough to check a figure, not
#: the whole 10-K — and a truncated context is *stated*, never silent.
_MAX_CONTEXT = 6000


def _build_prompt(sample: CanonicalSample, answer: str) -> str:
    context = " ".join(sample.context.text)[:_MAX_CONTEXT]
    return (
        f"QUESTION:\n{sample.question}\n\n"
        f"SEC FILING EXCERPT (truncated to {_MAX_CONTEXT} chars):\n{context}\n\n"
        f"EXPERT REFERENCE ANSWER:\n{sample.gold.answer}\n\n"
        f"ANALYST'S ANSWER TO GRADE:\n{answer}\n"
    )


def _parse(content: str) -> dict[str, object] | None:
    for candidate in (content, *(m.group(0) for m in _JSON.finditer(content))):
        try:
            parsed = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, dict) and "correct" in parsed:
            return parsed
    return None


async def judge_answer(
    sample: CanonicalSample,
    answer: str,
    *,
    provider: ModelProvider,
    judge: ModelSpec,
    candidate: ModelSpec | None = None,
    timeout_s: float = 300.0,
    retries: int = 2,
) -> JudgeVerdict:
    """Ask the judge to grade one answer.

    Refuses to self-judge. A model grading its own output is not evidence, and a warning is not
    enough — somebody would read past it, and the resulting number would look exactly like a real one.
    """
    if candidate is not None and judge.model.split(":")[0] == candidate.model.split(":")[0]:
        raise ValueError(
            f"refusing to let {judge.ref} judge {candidate.ref}: a model grading its own family is "
            "not evidence. Use a different judge (e.g. qwen3:8b for a qwen2.5 candidate)."
        )

    if not answer.strip():
        # An empty answer needs no judge, and asking one would invite it to hallucinate a rationale
        # for a thing that does not exist.
        return JudgeVerdict(
            sample_id=sample.sample_id,
            correct=False,
            judge_model=judge.ref,
            rationale="the candidate produced no answer",
            scores={r.value: 1 for r in RUBRIC},
        )

    request = ModelRequest(
        model=judge,
        messages=(
            ChatMessage(role=Role.SYSTEM, content=_SYSTEM),
            ChatMessage(role=Role.USER, content=_build_prompt(sample, answer)),
        ),
        # Zero. A judge you cannot reproduce is an anecdote.
        temperature=0.0,
        max_tokens=512,
        response_format="json_object",
        prompt_version=JUDGE_PROMPT_VERSION,
        benchmark=sample.benchmark,
        benchmark_version=sample.benchmark_version,
        sample_id=sample.sample_id,
        timeout_s=timeout_s,
    )

    last_error = ""
    for _ in range(retries + 1):
        try:
            response = await provider.generate(request)
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            continue

        parsed = _parse(response.content)
        if parsed is None:
            last_error = f"judge returned unparseable output: {response.content[:120]!r}"
            continue

        scores: dict[str, int] = {}
        for criterion in RUBRIC:
            raw = parsed.get(criterion.value)
            if isinstance(raw, int | float) and 1 <= float(raw) <= 5:
                scores[criterion.value] = int(raw)

        return JudgeVerdict(
            sample_id=sample.sample_id,
            correct=bool(parsed.get("correct")),
            scores=scores,
            rationale=str(parsed.get("rationale", ""))[:600],
            judge_model=judge.ref,
            latency_ms=response.latency_ms or 0.0,
        )

    # The judge failed. This is a JUDGE failure and is recorded as one — it is emphatically not a
    # zero for the candidate, who may well have answered perfectly. Turning an unavailable judgment
    # into a bad grade is the single most common way an LLM-judged benchmark lies.
    return JudgeVerdict(
        sample_id=sample.sample_id,
        correct=False,
        valid=False,
        error=last_error,
        judge_model=judge.ref,
        rationale="THE JUDGE FAILED — this is not a verdict on the candidate",
    )

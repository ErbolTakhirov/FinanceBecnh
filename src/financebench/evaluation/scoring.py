"""The top-level scores, and the Finance Capability Index.

Model ability, retrieval ability and agent ability are **not averaged into one number**. They are
three different things, and a single "financial score" that mixes them tells you nothing about any
of them — a RAG pipeline can fail because the retriever missed the page or because the model
misread it, and those have opposite fixes.

So a run reports whichever of these its eval mode earned:

- **Financial Core Score** — ``context_given`` only. The model's own financial reasoning.
- **Financial RAG Score** — ``retrieval_required`` only. The retrieval system.
- **Financial Agent Score** — ``tool_assisted`` only. Tool selection and use.

The **Finance Capability Index** is a weighted **geometric** mean of the capability dimensions,
scaled by a reliability penalty. Geometric, not arithmetic, because the arithmetic mean lets a
model trade a catastrophic weakness for an unrelated strength: 0.9 grounding and 0.1 numerical
accuracy averages to a respectable 0.5, which is a lie about a model that cannot do arithmetic.
The geometric mean of the same pair is 0.3, which is the truth.

The FCI is only computed when there is enough coverage, no critical gate has failed, and the run is
not a mock. Otherwise it is ``None`` — never a number with an asterisk.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from financebench.evaluation.capability_map import CAPABILITY_WEIGHTS, CapabilityDimension
from financebench.evaluation.failures import (
    CATASTROPHIC_FAILURES,
    FailureRecord,
    FailureType,
)
from financebench.schemas.common import EvalMode
from financebench.schemas.metric import MetricAggregate
from financebench.schemas.sample import CanonicalSample

__all__ = [
    "MIN_DIMENSIONS_FOR_FCI",
    "FinanceScores",
    "RunCoverage",
    "compute_scores",
    "reliability_penalty",
]

#: An index built from one dimension is not an index. Below this, the FCI is withheld.
MIN_DIMENSIONS_FOR_FCI = 3

_EPSILON = 1e-6

#: Floor on the reliability multiplier. Even a maximally unreliable model keeps some credit for the
#: answers it got right — the penalty is a discount, not an annihilation.
_PENALTY_FLOOR = 0.65


def reliability_penalty(failures: list[FailureRecord], n_scored: int) -> float:
    """A multiplier in ``[0.65, 1.0]`` reflecting how *dangerously* a model fails, not how often.

    Weighted towards the failures you cannot live with: a model that is merely wrong is discounted
    far less than one that is confidently, catastrophically wrong.
    """
    if n_scored == 0:
        return 1.0

    def rate(types: frozenset[FailureType]) -> float:
        return sum(1 for f in failures if f.failure_type in types) / n_scored

    catastrophic = rate(CATASTROPHIC_FAILURES)
    unsupported = rate(
        frozenset({FailureType.UNSUPPORTED_NUMERIC_CLAIM, FailureType.UNSUPPORTED_NARRATIVE_CLAIM})
    )
    invalid = rate(frozenset({FailureType.INVALID_STRUCTURED_RESPONSE}))

    penalty = 1.0 - (0.50 * catastrophic + 0.30 * unsupported + 0.20 * invalid)
    return max(_PENALTY_FLOOR, min(1.0, penalty))


@dataclass(frozen=True)
class RunCoverage:
    """What a run actually *tested* — which is what decides what it is allowed to claim.

    The Finance Capability Index is a statement about a model's financial capability in general. A
    FinQA-only run cannot support that statement no matter how high it scores, and the honest
    response is to **refuse the index**, not to publish one with a footnote. Nobody reads the
    footnote; they read the number.

    So an FCI requires the run to have actually asked the three questions that a good FinQA score
    says nothing about: can it find its own evidence, can it advise a real business, and does it know
    when to say "I can't tell". A model can be excellent at table arithmetic and fail all three.
    """

    benchmarks: frozenset[str] = frozenset()
    has_grounding: bool = False
    """A benchmark where the model must ground its answer in a real document."""
    has_refusal: bool = False
    """A benchmark containing questions that genuinely cannot be answered."""
    has_smb_cfo: bool = False
    """The small-business CFO benchmark — the mission's actual subject."""
    has_conversation: bool = False
    has_bilingual: bool = False
    n_injection_samples: int = 0

    @classmethod
    def of(cls, samples: Sequence[CanonicalSample]) -> RunCoverage:
        """Read coverage off the samples themselves rather than off a list of benchmark names.

        Deliberate: a future grounded benchmark, or a future adversarial one, then counts
        automatically — coverage is a property of what was *asked*, not of what it was called.
        """
        return cls(
            benchmarks=frozenset(sample.benchmark for sample in samples),
            has_grounding=any("evidence_grounding" in s.capability_tags for s in samples),
            has_refusal=any(s.evaluation.should_refuse for s in samples),
            has_smb_cfo=any(s.benchmark == "smb_cfo" for s in samples),
            has_conversation=any("conversation" in s.capability_tags for s in samples),
            has_bilingual=any("bilingual" in s.capability_tags for s in samples),
            n_injection_samples=sum(
                1 for s in samples if s.metadata.get("prompt_injection") == "true"
            ),
        )


@dataclass(frozen=True)
class FinanceScores:
    """The top-level numbers for one run. ``None`` means "not measured", never "zero"."""

    eval_mode: EvalMode
    core_score: float | None = None
    rag_score: float | None = None
    agent_score: float | None = None
    multimodal_score: float | None = None

    # -- sub-scores. Reported separately because they are different capabilities, and a model can be
    # strong at one and useless at another. Averaging them into a headline is how a benchmark
    # certifies a model for a job it cannot do.
    smb_cfo_score: float | None = None
    conversation_score: float | None = None
    grounding_score: float | None = None
    analysis_score: float | None = None
    refusal_score: float | None = None
    bilingual_score: float | None = None

    fci: float | None = None
    fci_withheld_because: str | None = None
    reliability_penalty: float = 1.0

    def to_json(self) -> dict[str, object]:
        return {
            "eval_mode": self.eval_mode.value,
            "financial_core_score": self.core_score,
            "financial_rag_score": self.rag_score,
            "financial_agent_score": self.agent_score,
            "multimodal_finance_score": self.multimodal_score,
            "smb_cfo_score": self.smb_cfo_score,
            "conversation_score": self.conversation_score,
            "grounding_score": self.grounding_score,
            "analysis_score": self.analysis_score,
            "refusal_score": self.refusal_score,
            "bilingual_score": self.bilingual_score,
            "finance_capability_index": self.fci,
            "fci_withheld_because": self.fci_withheld_because,
            "reliability_penalty": round(self.reliability_penalty, 4),
        }


def _weighted_geometric_mean(scores: Mapping[CapabilityDimension, float]) -> float:
    """exp(Σ wᵢ·ln(max(sᵢ, ε))) / exp(Σ wᵢ) — renormalized over the dimensions actually present.

    Renormalization matters: without it, a run that only covers 4 of the 10 dimensions would be
    scored as if the other 6 were zero, and every partial run would look catastrophic.
    """
    total_weight = sum(CAPABILITY_WEIGHTS[dimension] for dimension in scores)
    if total_weight <= 0:
        return 0.0
    log_sum = sum(
        CAPABILITY_WEIGHTS[dimension] * math.log(max(score, _EPSILON))
        for dimension, score in scores.items()
    )
    return math.exp(log_sum / total_weight)


def _fci_withheld_because(
    *,
    is_mock: bool,
    n_dimensions: int,
    any_critical_gate_failed: bool,
    coverage: RunCoverage,
) -> str | None:
    """Why this run may not publish a Finance Capability Index — or ``None`` if it may.

    Order matters only for which reason gets reported first; any one of them is disqualifying.
    """
    if is_mock:
        return "the mock provider was used — no model was evaluated"
    if n_dimensions < MIN_DIMENSIONS_FOR_FCI:
        return (
            f"only {n_dimensions} capability dimension(s) had coverage "
            f"(minimum {MIN_DIMENSIONS_FOR_FCI}); an index built from one dimension is not an index"
        )
    if any_critical_gate_failed:
        return (
            "a critical gate failed — a single index would let a strong average hide the kind of "
            "error that is not a near-miss in finance"
        )
    if not coverage.has_smb_cfo:
        return (
            "no SMB-CFO coverage — this index claims financial capability, and every other "
            "benchmark here is built on public-company filings. A model can be excellent at 10-K "
            "arithmetic and unable to tell a small business when it runs out of money"
        )
    if not coverage.has_grounding:
        return (
            "no grounding benchmark ran — every question handed the model its evidence. Nothing "
            "here shows it can find that evidence in a real document, which is most of the job"
        )
    if not coverage.has_refusal:
        return (
            "no refusal benchmark ran — nothing here asked a question the data cannot answer, so "
            "nothing here shows the model would decline instead of inventing a figure"
        )
    return None


def compute_scores(
    *,
    eval_mode: EvalMode,
    capabilities: Mapping[CapabilityDimension, MetricAggregate],
    failures: list[FailureRecord],
    n_scored: int,
    any_critical_gate_failed: bool,
    is_mock: bool,
    has_multimodal_coverage: bool = False,
    coverage: RunCoverage | None = None,
    benchmark_scores: Mapping[str, float] | None = None,
) -> FinanceScores:
    """Compute the top-level scores for a run.

    ``benchmark_scores`` maps a benchmark name to the mean of its preferred metric. It exists for
    the one sub-score that is **not** a capability dimension: SMB-CFO is a *benchmark*, and its
    questions are tagged ``calculation`` like FinQA's, so reading its score off the
    numerical-accuracy dimension would report FinQA's arithmetic and label it small-business
    advice.
    """
    coverage = coverage or RunCoverage()
    benchmark_scores = benchmark_scores or {}
    present = {
        dimension: aggregate.mean
        for dimension, aggregate in capabilities.items()
        if aggregate.mean is not None
    }
    overall = sum(present.values()) / len(present) if present else None

    # The mode decides which top-level score this run is even entitled to report. A context_given
    # run has said nothing about a retriever, and must not imply that it has.
    core = overall if eval_mode is EvalMode.CONTEXT_GIVEN else None
    rag = overall if eval_mode is EvalMode.RETRIEVAL_REQUIRED else None
    agent = overall if eval_mode is EvalMode.TOOL_ASSISTED else None

    penalty = reliability_penalty(failures, n_scored)

    withheld = _fci_withheld_because(
        is_mock=is_mock,
        n_dimensions=len(present),
        any_critical_gate_failed=any_critical_gate_failed,
        coverage=coverage,
    )
    fci = None if withheld else round(_weighted_geometric_mean(present) * penalty, 4)

    return FinanceScores(
        eval_mode=eval_mode,
        core_score=core,
        rag_score=rag,
        agent_score=agent,
        multimodal_score=overall if has_multimodal_coverage else None,
        # Each sub-score is the capability dimension that measures it, and is `None` — not zero —
        # when the run contained nothing that could measure it.
        smb_cfo_score=benchmark_scores.get("smb_cfo"),
        conversation_score=present.get(CapabilityDimension.CONVERSATION_CONSISTENCY),
        grounding_score=present.get(CapabilityDimension.DOCUMENT_GROUNDING),
        analysis_score=present.get(CapabilityDimension.ANALYTICAL_INSIGHT),
        refusal_score=present.get(CapabilityDimension.CALIBRATION_AND_REFUSAL),
        bilingual_score=present.get(CapabilityDimension.BILINGUAL_EN_RU),
        fci=fci,
        fci_withheld_because=withheld,
        reliability_penalty=penalty,
    )

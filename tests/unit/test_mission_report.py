"""The report's one job it must never get wrong: an absence must not read as a failure.

Every other honesty rule in this platform funnels into this file, because the report is the only
artifact a non-expert reads. If a question that was never asked appears as "0%", the reader learns
something false about the model, and no amount of correctness upstream repairs that.
"""

from __future__ import annotations

from pathlib import Path

from financebench.reporting import RunSummary, build_mission_report, load_runs


def _run(**overrides: object) -> RunSummary:
    base = {
        "run_id": "r1",
        "model_ref": "ollama/qwen2.5:3b",
        "benchmark": "finqa",
        "eval_mode": "context_given",
        "conversation_protocol": None,
        "run_type": "real",
        "fingerprint": "abc123",
        "n_samples": 100,
    }
    base.update(overrides)
    return RunSummary(**base)  # type: ignore[arg-type]


def _metric(mean: float, n: int) -> dict[str, object]:
    return {"mean": mean, "n": n}


def _report(runs: list[RunSummary]) -> str:
    return build_mission_report(runs, generated_at="2026-07-11T00:00:00Z")


# --------------------------------------------------------------------------- absence vs failure


def test_a_question_nobody_asked_is_unanswered_not_zero() -> None:
    """The rule the whole report exists to obey.

    This run measured arithmetic and nothing else. It says nothing whatsoever about whether the
    model can find evidence, advise a business, or decline a question it cannot answer — and the
    report must say so in words, not print "0%" three times.
    """
    document = _report([_run(metrics={"finqa_answer_accuracy": _metric(0.42, 100)})])

    assert document.count("class='unanswered'") == 4, "four of the five questions were never asked"
    assert "No ConvFinQA run found" in document
    assert "No FinanceBench run found" in document
    assert "No SMB-CFO run found" in document
    assert "42.0%" in document, "and the one that WAS asked must still report its number"


def test_a_real_zero_is_still_reported_as_a_zero() -> None:
    """The fix must not swallow bad news. A model that scored 0.0 on a benchmark it actually ran
    scored 0.0, and the report says so — that is a finding about the model."""
    document = _report(
        [
            _run(
                benchmark="smb_cfo",
                metrics={
                    "smb_cfo_accuracy": _metric(0.0, 20),
                    "smb_cfo_refusal_correctness": _metric(1.0, 20),
                    "smb_cfo_injection_resistance": _metric(1.0, 10),
                },
            )
        ]
    )
    assert "0.0%" in document
    assert "100.0%" in document


# --------------------------------------------------------------------------- the retrieval loss


def test_the_retrieval_loss_is_the_gap_between_the_two_modes() -> None:
    """The headline of the whole grounding story: the accuracy that exists ONLY because somebody
    handed the model its evidence. In production nobody does."""
    runs = [
        _run(
            benchmark="financebench",
            eval_mode="context_given",
            metrics={"financebench_answer_accuracy": _metric(0.60, 89)},
        ),
        _run(
            benchmark="financebench",
            eval_mode="retrieval_required",
            metrics={"financebench_answer_accuracy": _metric(0.15, 89)},
            retrieval={"retriever": "bm25", "top_k": 10, "page_recall": 0.27},
        ),
    ]
    document = _report(runs)
    assert "Retrieval loss: 45.0%" in document


def test_without_the_retrieval_run_the_report_refuses_to_imply_the_model_can_retrieve() -> None:
    """A context_given score is a statement about reading, not about finding. Presenting it alone
    under a "can it retrieve evidence?" heading would be the single most misleading thing this
    report could do."""
    document = _report(
        [
            _run(
                benchmark="financebench",
                eval_mode="context_given",
                metrics={"financebench_answer_accuracy": _metric(0.60, 89)},
            )
        ]
    )
    assert "Retrieval loss" not in document
    assert "not run" in document
    assert "only that it can read one that was handed to it" in document


# --------------------------------------------------------------------------- conversations


def test_the_protocol_gap_is_reported_only_when_both_protocols_ran() -> None:
    """The gap is the finding. One protocol alone cannot produce it, and inventing it from one would
    be inventing the result."""
    gold_only = _report(
        [
            _run(
                benchmark="convfinqa",
                conversation_protocol="gold_history",
                conversation={"turn_accuracy": 0.5, "full_conversation_accuracy": 0.1},
            )
        ]
    )
    assert "The number that matters" not in gold_only
    assert "the comparison needs both" in gold_only

    both = _report(
        [
            _run(
                benchmark="convfinqa",
                conversation_protocol="gold_history",
                conversation={"turn_accuracy": 0.50},
            ),
            _run(
                benchmark="convfinqa",
                conversation_protocol="model_history",
                conversation={"turn_accuracy": 0.30},
            ),
        ]
    )
    assert "The number that matters: 20.0%" in both


# --------------------------------------------------------------------------- gates and verdicts


def test_a_gate_that_could_not_be_tested_is_not_shown_as_passing() -> None:
    """A run that never attacked the model has not shown that the model resists attack. A green tick
    there is a claim the evidence does not support."""
    document = _report(
        [
            _run(
                gates=[
                    {
                        "gate_name": "prompt_injection_obeyed_rate_max",
                        "threshold": 0.0,
                        "observed": None,
                        "passed": None,
                        "skipped": True,
                    }
                ]
            )
        ]
    )
    assert "NOT TESTED" in document
    assert "NOT TESTED</td>" in document or "NOT TESTED<" in document
    assert "<b>NOT TESTED</b> is not a pass" in document


def test_the_verdict_is_the_worst_run_not_the_average() -> None:
    """A model that is safe on four benchmarks and invents figures on the fifth is not four-fifths
    safe."""
    document = _report(
        [
            _run(benchmark="finqa", verdict="USABLE_WITH_HUMAN_REVIEW"),
            _run(benchmark="smb_cfo", verdict="NOT_FINANCE_READY"),
        ]
    )
    assert "NOT_FINANCE_READY" in document
    assert "class='verdict'>NOT_FINANCE_READY" in document


def test_runs_with_different_evaluator_fingerprints_are_flagged_as_incomparable() -> None:
    """Two runs whose evaluator code differs measured different things. Putting their numbers in one
    table invites a comparison the evidence does not support."""
    document = _report(
        [
            _run(fingerprint="aaaa1111"),
            _run(benchmark="tatqa", fingerprint="bbbb2222"),
        ]
    )
    assert "These runs are not all comparable" in document


def test_a_mock_run_never_appears_as_a_model() -> None:
    """The mock reads the gold answers. Its scores measure the pipeline, and putting them next to a
    real model's would be the most straightforward lie the platform could tell."""
    document = _report(
        [
            _run(run_type="mock_test", metrics={"finqa_answer_accuracy": _metric(1.0, 100)}),
            _run(metrics={"finqa_answer_accuracy": _metric(0.15, 100)}),
        ]
    )
    assert "mock run(s) excluded" in document
    assert "100.0%" not in document, "the mock's perfect score must not reach the report"
    assert "15.0%" in document


# --------------------------------------------------------------------------- self-contained


def test_the_report_reaches_out_to_nothing() -> None:
    """It has to open on a machine that has never heard of this repository — emailed, committed, or
    handed over on a stick. Any external reference is a broken report waiting to happen, and a
    tracking pixel waiting to be added."""
    document = _report([_run()])
    for forbidden in ("http://", "https://", "<script", "@import", "cdn."):
        assert forbidden not in document, f"the report must be self-contained; found {forbidden!r}"


def test_loading_a_directory_of_half_written_runs_skips_them_rather_than_guessing(
    tmp_path: Path,
) -> None:
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "environment.json").write_text("{ not json")
    assert load_runs(tmp_path) == []

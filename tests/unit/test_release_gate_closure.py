"""Regressions for the release-gate closure: resume must not silently become a different run, and
the narrative report must not be silently replaced by a table dump.

Both of these were real. Neither raised.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from financebench.execution.orchestration import resolve_samples
from financebench.reporting.release_report import ModelResult, build_release_report
from financebench.schemas.sample_manifest import (
    ManifestBenchmark,
    SampleManifest,
    load_sample_manifest,
)
from financebench.utils.errors import ManifestError

# --------------------------------------------------------------------------------------------
# A frozen manifest names the questions. Resume must ask THOSE questions, and no others.
# --------------------------------------------------------------------------------------------


def test_resume_restores_the_frozen_sample_ids_and_does_not_reload_the_benchmark() -> None:
    """The bug: `resume` never restored the manifest, so it fell back to `limit: null` and reloaded
    the ENTIRE benchmark — 2,815 samples for a 150-sample finqa+tatqa manifest — then began
    evaluating them, and would have written the result over the original 150-sample run's artifacts,
    under the original run's id.

    A resume that quietly evaluates 2,815 questions and publishes them under the name of a 150-question
    run is not a resume. It is a different experiment wearing the first one's id.
    """
    manifest = load_sample_manifest("configs/manifests/tool_paired_v1.json")

    # The full benchmark, unrestricted, is very much larger than the manifest.
    everything, _ = resolve_samples(manifest.benchmark_splits)
    assert len(everything) > 2000, "the underlying benchmarks are large — that is the whole point"

    # Restricted by the manifest, the run asks exactly the frozen questions, in the frozen order.
    selected, _ = resolve_samples(manifest.benchmark_splits, manifest)
    assert len(selected) == 150
    assert [s.sample_id for s in selected] == list(manifest.all_sample_ids)
    assert len(selected) < len(everything) / 10


def test_a_manifest_whose_samples_no_longer_resolve_FAILS_rather_than_substituting() -> None:
    """If the data underneath moves, the run must break — not quietly evaluate different questions
    and publish them under the manifest's name."""
    broken = SampleManifest(
        name="broken",
        benchmarks=(
            ManifestBenchmark(
                name="finqa",
                split="test",
                sample_ids=("finqa:test:this-id-does-not-exist",),
            ),
        ),
    )
    with pytest.raises(ManifestError, match=r"no longer"):
        resolve_samples(broken.benchmark_splits, broken)


def test_the_release_manifests_still_resolve_exactly() -> None:
    """The frozen sets the release actually publishes. If this fails, the release is not reproducible
    from its own manifest, whatever the artifacts say."""
    for path, expected in (
        ("configs/manifests/tool_paired_v1.json", 150),
        ("configs/manifests/release_v0_1.json", 220),
    ):
        manifest = load_sample_manifest(path)
        selected, _ = resolve_samples(manifest.benchmark_splits, manifest)
        assert len(selected) == expected, f"{path} no longer resolves to {expected} samples"
        assert [s.sample_id for s in selected] == list(manifest.all_sample_ids)


# --------------------------------------------------------------------------------------------
# The narrative report carries the findings. A generator must never overwrite it.
# --------------------------------------------------------------------------------------------


def test_the_generator_cannot_overwrite_the_narrative_report(tmp_path: Path) -> None:
    """The bug: `build_release_report` wrote `report.md`, and silently replaced a hand-written report
    carrying the findings with a table dump of the one run that happened to be on the current
    fingerprint.

    Tables are the part of a benchmark report that mean least on their own. `0.027` is a number;
    "giving the model a calculator made it five times worse, and it called the calculator twice in
    150 questions" is a finding. The generator writes `results_tables.md`; the narrative is authored.
    """
    narrative = tmp_path / "report.md"
    narrative.write_text("# The findings\n\nTools made it worse.\n", encoding="utf-8")

    build_release_report(
        tmp_path,
        version="v0.1.0-rc1",
        models=[ModelResult(model_ref="ollama/qwen2.5:3b")],
        paired=[],
        fingerprint="deadbeef",
        hardware={"platform": "test", "python": "3.13"},
        limitations="none",
    )

    assert narrative.read_text(encoding="utf-8") == "# The findings\n\nTools made it worse.\n", (
        "the generator overwrote the narrative report"
    )
    assert (tmp_path / "results_tables.md").is_file()
    assert (tmp_path / "report.html").is_file()
    assert (tmp_path / "results.json").is_file()
    assert (tmp_path / "leaderboard.csv").is_file()


def test_a_withheld_index_is_a_refusal_not_a_zero(tmp_path: Path) -> None:
    """`fci: null` + a reason, and an EMPTY cell in the CSV. Never `0.0` — which would say the model
    scored zero, when the truth is that the run did not ask enough to support an index at all."""
    model = ModelResult(model_ref="ollama/qwen2.5:3b")
    model.runs["run-x"] = {
        "capabilities": {
            "scores": {
                "finance_capability_index": None,
                "fci_withheld_because": "a critical gate failed",
            },
            "verdict": "NOT_FINANCE_READY",
        },
        "metrics": {},
        "gates": {"any_critical_gate_failed": True},
        "coverage": {"evaluated_samples": 220},
    }
    build_release_report(
        tmp_path,
        version="v0.1.0-rc1",
        models=[model],
        paired=[],
        fingerprint="deadbeef",
        hardware={},
        limitations="none",
    )

    results = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    run = results["models"][0]["runs"]["run-x"]
    assert run["fci"] is None, "a withheld index must be null, never 0.0"
    assert run["fci_withheld_because"], "and it must say why"

    csv = (tmp_path / "leaderboard.csv").read_text(encoding="utf-8")
    row = csv.splitlines()[1]
    assert ",," in row, "the FCI cell must be EMPTY, not 0"
    assert ",0.0," not in row
    assert ",0," not in row

    assert results["secque_analytical_score"] == "NOT_EVALUATED"

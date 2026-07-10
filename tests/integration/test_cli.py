"""CLI integration tests via Typer's CliRunner — covers the Milestone 1 acceptance-bar commands
plus the rest of the CLI surface (resume, compare, report, leaderboard, cache).

These tests rely on being run from the repository root (matching the documented usage pattern —
``--group`` resolves against ``configs/benchmark_groups/`` relative to CWD, the same way the
mission's own examples assume), and always redirect the cache to a per-test tmp directory via
``FINANCEBENCH_CACHE_DIR`` so a test run never touches (or is affected by) a real local cache.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from financebench.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FINANCEBENCH_CACHE_DIR", str(tmp_path / "cache"))


def test_doctor_exits_zero() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "Python" in result.output


def test_list_benchmarks_shows_smoke() -> None:
    result = runner.invoke(app, ["list-benchmarks"])
    assert result.exit_code == 0
    assert "smoke" in result.output


def test_licenses_exits_zero() -> None:
    result = runner.invoke(app, ["licenses"])
    assert result.exit_code == 0
    assert "redistributable" in result.output


def test_benchmark_info_smoke() -> None:
    result = runner.invoke(app, ["benchmark-info", "smoke"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "fully_supported"


def test_benchmark_info_unknown_fails() -> None:
    result = runner.invoke(app, ["benchmark-info", "does-not-exist"])
    assert result.exit_code == 1


def test_validate_dataset_smoke() -> None:
    result = runner.invoke(app, ["validate-dataset", "smoke"])
    assert result.exit_code == 0
    assert "10 samples validated" in result.output


def test_list_model_providers_shows_mock() -> None:
    result = runner.invoke(app, ["list-model-providers"])
    assert result.exit_code == 0
    assert "mock" in result.output


def test_validate_model_mock_probes_successfully() -> None:
    result = runner.invoke(app, ["validate-model", "--model-config", "configs/models/mock.yaml"])
    assert result.exit_code == 0
    assert "probe call: ok" in result.output


def test_prepare_smoke_needs_no_download() -> None:
    result = runner.invoke(app, ["prepare", "smoke"])
    assert result.exit_code == 0
    assert "nothing to prepare" in result.output


def test_eval_requires_exactly_one_of_benchmark_or_group(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "eval",
            "--model-config",
            "configs/models/mock.yaml",
            "--output-dir",
            str(tmp_path / "runs"),
        ],
    )
    assert result.exit_code == 1
    assert "exactly one" in result.output


def test_eval_group_smoke_writes_all_artifacts(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    result = runner.invoke(
        app,
        [
            "eval",
            "--group",
            "smoke",
            "--model-config",
            "configs/models/mock.yaml",
            "--output-dir",
            str(runs_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Run complete" in result.output
    run_dirs = list(runs_dir.iterdir())
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "predictions.jsonl").is_file()
    assert (run_dirs[0] / "report.html").is_file()


def test_eval_rerun_without_resume_fails(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    args = [
        "eval",
        "--group",
        "smoke",
        "--model-config",
        "configs/models/mock.yaml",
        "--output-dir",
        str(runs_dir),
    ]
    first = runner.invoke(app, args)
    assert first.exit_code == 0
    second = runner.invoke(app, args)
    assert second.exit_code == 1
    assert "--resume" in second.output


def test_eval_rerun_with_resume_hits_cache(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    args = [
        "eval",
        "--group",
        "smoke",
        "--model-config",
        "configs/models/mock.yaml",
        "--output-dir",
        str(runs_dir),
    ]
    first = runner.invoke(app, args)
    assert first.exit_code == 0
    second = runner.invoke(app, [*args, "--resume"])
    assert second.exit_code == 0
    assert "cache_hits=10" in second.output


def test_resume_command_reconstructs_the_original_run(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    first = runner.invoke(
        app,
        [
            "eval",
            "--group",
            "smoke",
            "--model-config",
            "configs/models/mock.yaml",
            "--output-dir",
            str(runs_dir),
        ],
    )
    assert first.exit_code == 0
    run_id = next(runs_dir.iterdir()).name

    result = runner.invoke(
        app,
        [
            "resume",
            "--run-id",
            run_id,
            "--model-config",
            "configs/models/mock.yaml",
            "--runs-dir",
            str(runs_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Resumed" in result.output
    assert "cache_hits=10/10" in result.output


def test_resume_rejects_a_mismatched_model_config(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    runner.invoke(
        app,
        [
            "eval",
            "--group",
            "smoke",
            "--model-config",
            "configs/models/mock.yaml",
            "--output-dir",
            str(runs_dir),
        ],
    )
    run_id = next(runs_dir.iterdir()).name

    other_config = tmp_path / "other.yaml"
    other_config.write_text("provider: mock\nmodel: always-wrong\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "resume",
            "--run-id",
            run_id,
            "--model-config",
            str(other_config),
            "--runs-dir",
            str(runs_dir),
        ],
    )
    assert result.exit_code == 1
    assert "recorded" in result.output


def test_report_prints_the_summary(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    runner.invoke(
        app,
        [
            "eval",
            "--group",
            "smoke",
            "--model-config",
            "configs/models/mock.yaml",
            "--output-dir",
            str(runs_dir),
        ],
    )
    run_id = next(runs_dir.iterdir()).name

    result = runner.invoke(app, ["report", "--run-id", run_id, "--runs-dir", str(runs_dir)])
    assert result.exit_code == 0
    assert "run summary" in result.output


def test_compare_two_runs(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    other_config = tmp_path / "wrong.yaml"
    other_config.write_text("provider: mock\nmodel: always-wrong\n", encoding="utf-8")

    runner.invoke(
        app,
        [
            "eval",
            "--group",
            "smoke",
            "--model-config",
            "configs/models/mock.yaml",
            "--output-dir",
            str(runs_dir),
        ],
    )
    runner.invoke(
        app,
        [
            "eval",
            "--group",
            "smoke",
            "--model-config",
            str(other_config),
            "--output-dir",
            str(runs_dir),
        ],
    )
    run_ids = sorted(p.name for p in runs_dir.iterdir())
    assert len(run_ids) == 2

    result = runner.invoke(
        app,
        ["compare", "--run-id", run_ids[0], "--run-id", run_ids[1], "--runs-dir", str(runs_dir)],
    )
    assert result.exit_code == 0
    assert "1.000" in result.output
    assert "0.000" in result.output


def test_compare_requires_at_least_two_run_ids(tmp_path: Path) -> None:
    result = runner.invoke(app, ["compare", "--run-id", "only-one"])
    assert result.exit_code == 1


def test_leaderboard_builds_all_four_formats(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    reports_dir = tmp_path / "reports"
    runner.invoke(
        app,
        [
            "eval",
            "--group",
            "smoke",
            "--model-config",
            "configs/models/mock.yaml",
            "--output-dir",
            str(runs_dir),
        ],
    )
    result = runner.invoke(
        app, ["leaderboard", "--runs-dir", str(runs_dir), "--output", str(reports_dir)]
    )
    assert result.exit_code == 0
    for filename in ("leaderboard.json", "leaderboard.csv", "leaderboard.md", "leaderboard.html"):
        assert (reports_dir / filename).is_file()


def test_leaderboard_on_empty_runs_dir_still_writes_files(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "leaderboard",
            "--runs-dir",
            str(tmp_path / "no-runs-here"),
            "--output",
            str(tmp_path / "reports"),
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "reports" / "leaderboard.json").is_file()


def test_cache_stats_and_clear(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    runner.invoke(
        app,
        [
            "eval",
            "--group",
            "smoke",
            "--model-config",
            "configs/models/mock.yaml",
            "--output-dir",
            str(runs_dir),
        ],
    )
    stats = runner.invoke(app, ["cache", "stats"])
    assert stats.exit_code == 0
    assert "entries: 10" in stats.output

    cleared = runner.invoke(app, ["cache", "clear", "--yes"])
    assert cleared.exit_code == 0
    assert "Removed 10" in cleared.output

    stats_after = runner.invoke(app, ["cache", "stats"])
    assert "entries: 0" in stats_after.output


def test_cache_clear_on_empty_cache_is_a_no_op() -> None:
    result = runner.invoke(app, ["cache", "clear", "--yes"])
    assert result.exit_code == 0
    assert "already empty" in result.output

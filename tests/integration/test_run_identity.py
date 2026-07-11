"""A run's identity must be one thing, computed in one place.

Found by driving the real CLI against a real model: the CLI chose the output directory with one
run-id formula and ``run_eval`` stamped the artifacts with another. The artifacts therefore claimed
a run id that did not match the directory they were sitting in — and, worse, a ``program_v1`` run
and a ``structured_financial_v1`` run mapped to the *same* directory, so one would overwrite the
other. That silently destroys the comparability guarantee the prompt profile exists to provide.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from financebench.cli import app

runner = CliRunner()

MOCK_CONFIG = Path("configs/models/mock.yaml").resolve()


def _eval(runs: Path, *extra: str) -> None:
    result = runner.invoke(
        app,
        [
            "eval",
            "--allow-mock",
            "--group",
            "smoke",
            "--model-config",
            str(MOCK_CONFIG),
            "--output-dir",
            str(runs),
            *extra,
        ],
    )
    assert result.exit_code == 0, result.output


def test_a_runs_directory_name_matches_the_run_id_it_records(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    _eval(runs)

    (run_dir,) = list(runs.iterdir())
    environment = json.loads((run_dir / "environment.json").read_text(encoding="utf-8"))
    assert run_dir.name == environment["run_id"], (
        "the directory a run lives in must be the id it claims — otherwise `resume --run-id` "
        "looks in the wrong place"
    )


def test_two_prompt_profiles_do_not_collide_in_one_run_directory(tmp_path: Path) -> None:
    """Asking for a number and asking for a program are different runs. They must not overwrite
    each other, and neither may be silently rejected as a duplicate."""
    runs = tmp_path / "runs"
    _eval(runs, "--prompt-profile", "structured_financial_v1")
    _eval(runs, "--prompt-profile", "direct_numeric_v1")

    directories = sorted(path.name for path in runs.iterdir())
    assert len(directories) == 2, f"expected two distinct run directories, got {directories}"

    profiles = {
        json.loads((runs / name / "prompt_manifest.json").read_text(encoding="utf-8"))[
            "prompt_profile"
        ]
        for name in directories
    }
    assert profiles == {"structured_financial_v1", "direct_numeric_v1"}


def test_two_eval_modes_do_not_collide_in_one_run_directory(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    _eval(runs, "--eval-mode", "context_given")
    _eval(runs, "--eval-mode", "tool_assisted")

    assert len(list(runs.iterdir())) == 2

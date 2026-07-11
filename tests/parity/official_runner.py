"""Runs a benchmark's **real official evaluator** in an isolated interpreter.

The parity suites need ground truth about what the official code does — not a re-reading of it, not
a memory of it, but its actual output on actual inputs. So this module shells out to the official
sources cloned under ``$FINANCEBENCH_REFERENCES`` (default ``/tmp/financebench-references``), in a
venv holding their own dependencies (sympy, numpy, scipy, pandas), and returns what they say.

If the clones aren't present the suites *skip*, loudly, rather than passing vacuously — a parity
test that silently degrades into a no-op is worse than no parity test, because it reports comfort
it hasn't earned.

Set up (see docs/research/metric_parity.md):

    git clone --depth 1 https://github.com/czyssrs/FinQA        /tmp/financebench-references/finqa
    git clone --depth 1 https://github.com/NExTplusplus/TAT-QA  /tmp/financebench-references/tatqa
    python3 -m venv /tmp/financebench-references/official-venv
    /tmp/financebench-references/official-venv/bin/pip install sympy numpy scipy pandas
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

__all__ = [
    "OFFICIAL_PYTHON",
    "REFERENCES",
    "requires_official",
    "run_official",
]

REFERENCES = Path(os.environ.get("FINANCEBENCH_REFERENCES", "/tmp/financebench-references"))
OFFICIAL_PYTHON = REFERENCES / "official-venv" / "bin" / "python"


def _available(*required: Path) -> bool:
    return OFFICIAL_PYTHON.is_file() and all(path.exists() for path in required)


def requires_official(*required: Path) -> pytest.MarkDecorator:
    """Skip a parity test when the official sources aren't cloned locally."""
    return pytest.mark.skipif(
        not _available(*required),
        reason=(
            f"official reference sources not found under {REFERENCES}. "
            "See tests/parity/official_runner.py for the clone commands."
        ),
    )


def run_official(script: str, *, cwd: Path, payload: object) -> object:
    """Execute ``script`` under the official venv with ``cwd`` on ``sys.path``.

    ``payload`` is handed to the script as JSON on stdin; the script must print its result as JSON
    on stdout. Keeping the boundary at JSON-over-a-subprocess means the official code runs exactly
    as its authors wrote it — same interpreter semantics, same dependency versions, no monkeypatching
    and no partial re-implementation sneaking in.
    """
    completed = subprocess.run(
        [str(OFFICIAL_PYTHON), "-c", script],
        cwd=str(cwd),
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"official evaluator failed (exit {completed.returncode}):\n{completed.stderr[-4000:]}"
        )
    # The official FinQA code prints diagnostics ("structure error") to stdout, so take the last
    # non-empty line, which is our JSON payload.
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"official evaluator produced no output.\nstderr:\n{completed.stderr}")
    return json.loads(lines[-1])

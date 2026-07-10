"""Git and interpreter/OS metadata for reproducibility records (``environment.json``).

Every lookup here is best-effort: git may not be installed, the working tree may not be a repo
(e.g. an extracted sdist), or the call may simply fail — none of that should ever crash a run.
Missing values stay ``None``, never a guess.
"""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path

__all__ = ["git_commit", "git_is_dirty", "os_name", "python_version"]

_GIT_TIMEOUT_S = 5.0


def _run_git(args: list[str], cwd: str | Path | None) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def git_commit(cwd: str | Path | None = None) -> str | None:
    """The current commit hash, or ``None`` if unavailable (no git, not a repo, etc.)."""
    return _run_git(["rev-parse", "HEAD"], cwd) or None


def git_is_dirty(cwd: str | Path | None = None) -> bool | None:
    """Whether the working tree has uncommitted changes, or ``None`` if this can't be determined."""
    status = _run_git(["status", "--porcelain"], cwd)
    return bool(status) if status is not None else None


def python_version() -> str:
    """The running interpreter's version, e.g. ``"3.11.9"``."""
    return platform.python_version()


def os_name() -> str:
    """A human-readable platform description, e.g. ``"Linux-6.8.0-x86_64"``."""
    return platform.platform()

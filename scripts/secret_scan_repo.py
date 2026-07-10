#!/usr/bin/env python3
"""Scan the repository for committed content that looks like a real API key or secret.

Used by CI (``ci.yml``) and safe to run locally: ``python scripts/secret_scan_repo.py``.
Exits non-zero and prints the offending file (never the matched secret text itself) if anything
is found. Deliberately pattern-based rather than using ``utils/secrets.py`` (which redacts
*known, currently-set* environment values) — this script's job is to catch secrets that were
never in this machine's environment at all, e.g. a key pasted directly into a config file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "runs",
    "reports",
    ".financebench_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
}

# Deliberately excluded: .env.example only ever contains variable *names* with empty values, so
# it will never match these value-shaped patterns anyway — no special-casing needed.
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OpenAI-style key", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("Anthropic-style key", re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}")),
    ("AWS access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    (
        "Generic bearer token assignment",
        re.compile(r"(?i)\b(api[_-]?key|token|secret)\b\s*[:=]\s*['\"][A-Za-z0-9_\-]{24,}['\"]"),
    ),
)

TEXT_SUFFIXES = {".py", ".yaml", ".yml", ".json", ".md", ".toml", ".cfg", ".ini", ".sh", ".env"}

# This scanner's own test file deliberately contains realistic-looking fake secrets as
# true-positive fixtures (proving the patterns above actually catch something) — the one
# intentional, reviewed exception, not a general escape hatch.
EXCLUDED_FILES = {Path("tests/unit/test_secret_scan_script.py")}


def _iter_candidate_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.relative_to(REPO_ROOT) in EXCLUDED_FILES:
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name != ".env":
            continue
        files.append(path)
    return files


def main() -> int:
    hits: list[str] = []
    for path in _iter_candidate_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(f"{path.relative_to(REPO_ROOT)}: possible {label}")
    if hits:
        print("Possible secrets found (values withheld):", file=sys.stderr)
        for hit in hits:
            print(f"  - {hit}", file=sys.stderr)
        return 1
    print("No secret-like patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

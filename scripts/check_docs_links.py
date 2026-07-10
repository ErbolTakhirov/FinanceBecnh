#!/usr/bin/env python3
"""Check that every relative markdown link in README.md and docs/*.md resolves to a real file.

Used by CI (``docs.yml``) and safe to run locally: ``python scripts/check_docs_links.py``.
Only checks *local, relative* links (``docs/foo.md``, ``../LICENSE``) — external ``http(s)://``
links are intentionally not fetched here (no network access needed for this check to pass).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _local_links(text: str) -> list[str]:
    links = []
    for target in MARKDOWN_LINK.findall(text):
        target = target.split("#", 1)[0]  # drop in-page anchors
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        links.append(target)
    return links


def main() -> int:
    broken: list[str] = []
    markdown_files = [REPO_ROOT / "README.md", *sorted((REPO_ROOT / "docs").rglob("*.md"))]
    for md_file in markdown_files:
        if not md_file.is_file():
            continue
        for link in _local_links(md_file.read_text(encoding="utf-8")):
            resolved = (md_file.parent / link).resolve()
            if not resolved.exists():
                broken.append(f"{md_file.relative_to(REPO_ROOT)} -> {link}")
    if broken:
        print("Broken local documentation links:", file=sys.stderr)
        for entry in broken:
            print(f"  - {entry}", file=sys.stderr)
        return 1
    print(f"Checked {len(markdown_files)} markdown files — all local links resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

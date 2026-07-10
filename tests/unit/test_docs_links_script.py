"""Tests for scripts/check_docs_links.py, loaded directly from the script file (it's not part of
the installed package)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_docs_links.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_docs_links", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script() -> ModuleType:
    return _load_script()


def test_extracts_local_links_and_skips_external_and_anchors(script: ModuleType) -> None:
    text = (
        "See [architecture](docs/architecture.md) and [external](https://example.com/x) "
        "and [anchor](docs/scoring.md#fci) and [mail](mailto:a@b.com)."
    )
    assert script._local_links(text) == ["docs/architecture.md", "docs/scoring.md"]


def test_the_real_docs_have_no_broken_links(script: ModuleType) -> None:
    assert script.main() == 0

"""Tests for scripts/secret_scan_repo.py's pattern-matching logic — loaded directly from the
script file (it's not part of the installed package) so a regression here fails the same way the
CI secret-scan step would."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "secret_scan_repo.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("secret_scan_repo", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script() -> ModuleType:
    return _load_script()


@pytest.mark.parametrize(
    "text",
    [
        'OPENAI_API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"',
        'anthropic_key: "sk-ant-abcdefghijklmnopqrstuvwxyz"',
        "aws_access_key_id = AKIAABCDEFGHIJKLMNOP",
        'api_key = "abcdefghijklmnopqrstuvwxyz123456"',
    ],
)
def test_detects_realistic_secrets(script: ModuleType, text: str) -> None:
    assert any(pattern.search(text) for _, pattern in script.SECRET_PATTERNS)


@pytest.mark.parametrize(
    "text",
    [
        "OPENAI_API_KEY=",  # .env.example style — name only, no value
        'fake_secret = "sk-definitely-a-secret-1234"',  # hyphenated test fixture, not a real key
        "api_key_env: OPENAI_API_KEY",  # a field pointing at an env var *name*, not a value
        "this is just prose about secrets and tokens",
    ],
)
def test_does_not_flag_safe_content(script: ModuleType, text: str) -> None:
    assert not any(pattern.search(text) for _, pattern in script.SECRET_PATTERNS)


def test_scanning_the_real_repo_finds_nothing(script: ModuleType) -> None:
    assert script.main() == 0

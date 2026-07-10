from __future__ import annotations

from pathlib import Path

from financebench.utils.secrets import (
    collect_secret_values,
    redact,
    scan_paths_for_secrets,
    scan_run_dir,
    scan_text_for_secrets,
)


def test_collect_secret_values_ignores_short_and_missing() -> None:
    env = {"OPENAI_API_KEY": "sk-real-secret-value", "ANTHROPIC_API_KEY": "short"}
    values = collect_secret_values(env)
    assert values == {"sk-real-secret-value"}


def test_redact_replaces_longest_first() -> None:
    text = "key=abcdefgh12 other=abcdefgh1234"
    redacted = redact(text, ["abcdefgh12", "abcdefgh1234"])
    assert "abcdefgh12" not in redacted
    assert "abcdefgh1234" not in redacted
    assert redacted.count("***REDACTED***") == 2


def test_scan_text_for_secrets_counts_distinct_hits() -> None:
    text = "leaked: sk-aaaaaaaa and again sk-aaaaaaaa, plus sk-bbbbbbbb"
    count = scan_text_for_secrets(text, ["sk-aaaaaaaa", "sk-bbbbbbbb", "sk-cccccccc"])
    assert count == 2


def test_scan_paths_for_secrets_finds_hits_in_files(tmp_path: Path) -> None:
    leaky = tmp_path / "leaky.json"
    leaky.write_text('{"header": "Authorization: Bearer sk-leaked-secret-1"}', encoding="utf-8")
    clean = tmp_path / "clean.json"
    clean.write_text('{"ok": true}', encoding="utf-8")

    hits = scan_paths_for_secrets([leaky, clean], ["sk-leaked-secret-1"])

    assert str(leaky) in hits
    assert str(clean) not in hits


def test_scan_run_dir_walks_recursively(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "predictions.jsonl").write_text(
        '{"raw": "token sk-should-not-be-here"}', encoding="utf-8"
    )

    hits = scan_run_dir(tmp_path, ["sk-should-not-be-here"])

    assert len(hits) == 1

"""The release manifest must satisfy its own published schema — and the validator must be able to
say no.

A validator that has never rejected anything is not a validator. These tests exist because the
alternative — a hand-rolled key check written in an afternoon — passes everything and proves nothing,
which is precisely the failure mode this project exists to catch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from financebench.release import SCHEMA_PATH, GateOutcome, validate_release_manifest


def _valid_manifest() -> dict[str, Any]:
    return {
        "release": "v0.1.0-rc1",
        "financebench_version": "0.1.0-rc1",
        "repository_commit": "abc123",
        "repository_dirty": False,
        "evaluator_fingerprint": {
            "digest": "80ca8a678b1c4fa1",
            "parser_version": "2",
            "prompt_profiles": {},
            "metric_versions": {"exact_match": "1"},
            "dataset_adapters": {"finqa": "official@0f16e286"},
            "retrieval_version": "2",
            "scoring_version": "3",
            "scoring_config_hash": "deadbeef",
        },
        "sample_manifests": [
            {
                "path": "configs/manifests/tool_paired_v1.json",
                "name": "tool_paired_v1",
                "id_hash": "7c839cfbc46cb862",
                "n_samples": 150,
                "sha256": "0" * 64,
            }
        ],
        "models": {"ollama/qwen2.5:3b": {"digest": "357c53fb659c", "quantization": "Q4_K_M"}},
        "runs": [
            {
                "run_id": "tool_paired_v1-...-3b",
                "model_ref": "ollama/qwen2.5:3b",
                "provider": "ollama",
                "run_type": "real",
                "evaluator_fingerprint": "80ca8a678b1c4fa1",
                "n_samples": 150,
                "sample_id_set_hash": "7c839cfbc46cb862",
            }
        ],
        "hardware": {"platform": "Linux", "python": "3.13.12"},
    }


def test_the_schema_file_exists_and_is_valid_json() -> None:
    assert SCHEMA_PATH.is_file(), "a manifest with no schema has a contract nobody can check"
    json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_a_well_formed_manifest_validates() -> None:
    assert validate_release_manifest(_valid_manifest()) == []


@pytest.mark.parametrize(
    ("mutate", "why"),
    [
        (
            lambda m: m.pop("evaluator_fingerprint"),
            "no fingerprint = no way to know what scored it",
        ),
        (lambda m: m.pop("runs"), "no runs = nothing was evaluated"),
        (lambda m: m.pop("hardware"), "latency claims are meaningless without the machine"),
        (lambda m: m.pop("sample_manifests"), "no frozen question set = not reproducible"),
        (
            lambda m: m["runs"][0].update({"run_type": "definitely_real"}),
            "run_type is an enum: 'real' or 'mock_test'. Nothing else.",
        ),
        (
            lambda m: m["runs"][0].pop("sample_id_set_hash"),
            "two runs over 'finqa test' are not comparable if they used different samples",
        ),
        (
            lambda m: m["runs"][0].update({"eval_mode": "vibes"}),
            "eval_mode is an enum; a run must say which question it answered",
        ),
    ],
)
def test_the_validator_can_actually_say_no(mutate: Any, why: str) -> None:
    """Each mutation removes or corrupts something a reader NEEDS to reproduce the numbers."""
    manifest = _valid_manifest()
    mutate(manifest)
    errors = validate_release_manifest(manifest)
    assert errors, f"the validator accepted a manifest it should have rejected — {why}"


def test_the_real_release_manifest_validates_if_it_exists() -> None:
    """The manifest actually shipped must satisfy the schema actually published beside it.

    A release manifest that violates its own schema is worse than having no schema at all: it tells
    a reader the file has a contract, and then breaks it.
    """
    path = Path("release/v0.1.0-rc1/release_manifest.json")
    if not path.is_file():
        pytest.skip("no release manifest built yet")
    errors = validate_release_manifest(json.loads(path.read_text(encoding="utf-8")))
    assert errors == [], f"the shipped manifest violates its own schema: {errors}"


def test_a_not_applicable_gate_is_not_a_passing_gate() -> None:
    """`None` is NOT TESTED. It is not a pass (a guarantee we did not earn) and not a fail (a defect
    we did not observe) — the same rule the metrics and the gates follow everywhere else."""
    assert GateOutcome("x", None, "").label == "NOT APPLICABLE"
    assert GateOutcome("x", True, "").label == "PASS"
    assert GateOutcome("x", False, "").label == "FAIL"

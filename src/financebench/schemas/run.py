"""Run configuration and run summary schemas.

``RunConfig`` is part of a run's deterministic identity (``make_run_id`` hashes it, see
``utils/ids.py``) and part of the response-cache key's context, so two runs with different
generation parameters never silently share cached answers.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

__all__ = ["CacheMode", "RunConfig", "RunMetadata"]


class CacheMode(StrEnum):
    """How the response cache is consulted for a run."""

    READ_WRITE = "read_write"
    READ_ONLY = "read_only"
    REFRESH = "refresh"
    OFF = "off"


class RunConfig(BaseModel):
    """Generation + execution parameters for a run. Defaults match the mission's determinism
    requirements: seed 42, temperature 0."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    seed: int = 42
    concurrency: int = 4
    max_retries: int = 4
    base_delay_s: float = 1.0
    max_delay_s: float = 30.0
    deadline_s: float | None = None
    limit: int | None = None
    cache_mode: CacheMode = CacheMode.READ_WRITE
    temperature: float = 0.0
    max_output_tokens: int = 1024
    timeout_seconds: float = 120.0
    prompt_profile: str = "direct_answer"
    judge_config: str | None = None
    max_cost_usd: float | None = None
    offline: bool = False


class RunMetadata(BaseModel):
    """Everything needed to reproduce and audit a run, written to ``run_config.json`` /
    ``environment.json``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    financebench_version: str
    created_at: str
    benchmark_or_group: str
    model_ref: str
    provider: str
    config: RunConfig
    dataset_manifest_hash: str | None = None
    git_commit: str | None = None
    git_dirty: bool | None = None
    python_version: str | None = None
    os_name: str | None = None
    n_samples: int = 0
    n_errors: int = 0
    n_cache_hits: int = 0
    total_estimated_cost_usd: float | None = None
    total_tokens: int | None = None
    budget_exceeded: bool = False

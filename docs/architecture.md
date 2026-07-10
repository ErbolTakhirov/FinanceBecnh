# Architecture

One-line summary per module (mirrors `src/financebench/`):

- `schemas/` — Pydantic v2 models. Dependency order: `common`/`tooling` (leaves) → `sample`/
  `model_io` → `prediction` → `{metric, run, leaderboard, manifest, gates}`.
- `utils/` — domain-agnostic helpers: `errors` (typed exception hierarchy), `secrets` (env-only
  key resolution + redaction), `timing` (`Clock`/`RealClock`/`FrozenClock` for deterministic
  tests), `ids` (deterministic run ids), `gitmeta` (best-effort git/OS/Python metadata for
  `environment.json`).
- `models/` — `ModelProvider` ABC + registry (`base.py`), the deterministic `mock` provider.
  Real providers (OpenAI, Anthropic, Gemini, OpenRouter, OpenAI-compatible, Ollama, llama.cpp,
  vLLM, Transformers) land in Milestone 5 under this same seam.
- `datasets/` — `DatasetAdapter` ABC + registry (`base.py`), the in-repo `smoke` fixture. Real
  benchmark adapters (FinQA, TAT-QA, FinanceReasoning, ...) land starting Milestone 2.
- `execution/` — `cache.py` (the content-addressed response cache — see
  [`docs/reproducibility.md`](reproducibility.md) for why a cache hit *is* resume), `retry.py`
  (deterministic backoff + rate limiting), `engine.py` (the async run engine, one model request
  per sample in this release), `orchestration.py` (resolves a benchmark/group + model config
  into samples, runs them, scores them, writes artifacts — the one function both the `eval` and
  `resume` CLI commands call).
- `evaluation/` — `metrics/` (the `Metric` ABC + registry + the built-in `exact_match`; native
  per-benchmark metrics and the LLM-judge framework land in Milestones 2-3),
  `capability_map.py` (the seven capability dimensions and their weights — see
  [`docs/scoring.md`](scoring.md)).
- `storage/` — `jsonl.py` (JSONL/JSON read-write primitives), `artifacts.py` (writes the full
  18-file run-artifact set).
- `config/` — YAML config schemas: `model_config.py` (`configs/models/*.yaml`),
  `benchmark_group.py` (`configs/benchmark_groups/*.yaml`).
- `prompts/` — `renderer.py`: the (currently single) prompt profile. The full versioned,
  YAML-configurable multi-profile system lands in Milestone 2+.
- `cli.py` — the Typer CLI. Contains no scoring/orchestration logic of its own — every command
  wires argument parsing and output formatting to the modules above.

## Core rules

- Python 3.11+, Pydantic v2, Typer, pytest, ruff, mypy (strict, `src/financebench` only).
- No real API keys in tests — only the `mock` provider (and, once added, `httpx` mock
  transports) are used.
- Cache is resume — see [`docs/reproducibility.md`](reproducibility.md).
- Registries, not hardcoded names — `datasets/`, `models/`, and `evaluation/metrics/` each own a
  decorator-based registry; the execution/CLI layers only import the registry, never a concrete
  adapter/provider/metric directly.
- Every dataset manifest's `fully_supported`/`supported_public_subset` claim must have a
  matching `tests/datasets/test_<name>_e2e.py` — enforced by
  `tests/test_manifest_hygiene.py`.

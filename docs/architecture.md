# Architecture

One-line summary per module (mirrors `src/financebench/`):

- `schemas/` — Pydantic v2 models. Dependency order: `common`/`tooling` (leaves) → `sample`/
  `model_io` → `prediction` → `{metric, run, leaderboard, manifest, gates, sample_manifest}`.
- `utils/` — domain-agnostic helpers: `errors` (typed exception hierarchy), `secrets` (env-only key
  resolution + redaction), `timing` (`Clock`/`RealClock`/`FrozenClock` for deterministic tests), `ids`
  (deterministic run ids), `gitmeta`.
- `models/` — `ModelProvider` ABC + registry, the deterministic `mock` provider, and the real ones:
  Ollama (**live-verified**), OpenAI, Anthropic, Gemini, OpenRouter, OpenAI-compatible
  (**implemented, never called — no API key exists here**). See [`providers.md`](providers.md).
- `datasets/` — `DatasetAdapter` ABC + registry, and the adapters: FinQA, TAT-QA, FinanceReasoning,
  FinanceBench, ConvFinQA, SECQUE, SMB-CFO, and the in-repo `smoke` fixture. Each pinned to the
  upstream commit its data comes from.
- `retrieval/` — the page corpus (12,013 pages / 84 filings), BM25, dense (nomic-embed-text), hybrid
  (RRF), document scoping, and the ablation. **No gold ever reaches a retriever** — the `Retriever`
  contract takes a query string, never a `CanonicalSample`.
- `tools/` — the sandboxed finance tools and the agent loop. `sandbox.py` is an **AST allow-list**; it
  never calls `eval`. See [`SECURITY.md`](../SECURITY.md).
- `execution/` — `cache.py` (the content-addressed response cache — a cache hit *is* resume),
  `retry.py`, `engine.py` (the async run engine + the tool-agent path, which is deliberately
  **uncached**), `orchestration.py` (the one function both `eval` and `resume` call).
- `evaluation/` — `metrics/` (the `Metric` ABC + registry), `native/` (per-benchmark metrics),
  `judge/` (the LLM judge **and its calibration harness — no judge is trusted until it passes**),
  `capability_map.py` (the **ten** dimensions), `scoring.py` (the FCI, and the conditions under which
  it is refused), `gates.py`, `fingerprint.py`, `stats.py` (bootstrap + paired bootstrap).
- `storage/` — `jsonl.py`, `artifacts.py` (writes the full 18-file run-artifact set).
- `reporting/` — the cross-model mission report, the retrieval-ablation report, the release report.
- `release.py` — the release manifest, its schema validation, and the release gates.
- `config/` — YAML schemas for model configs, benchmark groups, and frozen sample manifests.
- `prompts/` — the versioned prompt profiles. A profile's version is part of the run's identity.
- `cli.py` — the Typer CLI. No scoring or orchestration logic of its own.

## Core rules

- Python 3.11+, Pydantic v2, Typer, pytest, ruff, mypy (strict, `src/financebench` only).
- **No real API keys in tests** — only the `mock` provider and `httpx` mock transports.
- **Cache is resume.** See [`reproducibility.md`](reproducibility.md).
- **Registries, not hardcoded names.** `datasets/`, `models/`, `evaluation/metrics/` each own a
  decorator-based registry; the execution and CLI layers import the registry, never a concrete
  adapter.
- **Gold can never reach a model.** Structurally: `ModelRequest` has no field that could carry it. The
  `mock` provider is the single exception — it is a simulator *holding the answer key*, must be asked
  for with `--allow-mock`, is stamped `run_type=mock_test`, and is barred from the leaderboard.
- **`None` is not zero.** A not-applicable metric result is excluded from every rollup; a skipped gate
  is `NOT TESTED`, which is neither a pass nor a fail; a withheld FCI is a refusal, not a missing
  number.
- **The evaluator fingerprint decides comparability.** Two runs with different fingerprints are not
  comparable, and `compare` refuses them rather than quietly averaging. Bumping a `*_VERSION` is a
  deliberate act: it declares "this can move a score, and old runs must be re-scored".
- Every dataset manifest's support claim must have a matching `tests/datasets/test_<name>_e2e.py` —
  enforced by `tests/test_manifest_hygiene.py`.

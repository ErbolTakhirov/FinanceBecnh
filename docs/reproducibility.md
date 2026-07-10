# Reproducibility

Every run records (see `environment.json`, `run_config.json`, `model_manifest.json`,
`prompt_manifest.json`, `dataset_manifest.json` under `runs/{run_id}/`):

- FinanceBecnh version, git commit + dirty flag, Python version, OS
- The exact model reference, provider, and generation parameters (`RunConfig`)
- The prompt version and a SHA-256 hash of the system prompt text
- The dataset manifest(s) for every benchmark evaluated
- Seed (default `42`)

## Cache is resume, not two mechanisms

The response cache (`financebench.execution.cache`) keys on a canonicalized hash of the
validated `ModelRequest` — provider, exact model id, prompt version, generation params,
normalized messages, benchmark + version, sample id, tool config — explicitly *excluding* the
delivery-mechanism fields `request_id`/`timeout_s`, which must never affect whether a cached
answer is reused.

Because a run's id is itself deterministic (a hash of the benchmark/group label, model
reference, and seed — `financebench.utils.ids.make_run_id`), re-invoking an *identical* `eval`
command always targets the same `runs/{run_id}/` directory and re-derives every artifact in one
pass over the same ordered sample list. Samples whose request hash is already cached resolve
instantly with zero network calls; `--resume` is a confirmation flag on that same idempotent
command, not a separate code path. See `tests/unit/test_execution_engine.py::
test_rerun_with_same_cache_hits_everything_and_makes_zero_calls` for the test that proves it,
and `financebench resume --run-id <id> --model-config <path>` for the standalone command that
reconstructs an existing run's scope from its own recorded artifacts and re-invokes the same
idempotent path.

A failed provider call is never cached, so a transient error doesn't get pinned forever.

## Determinism

- Default seed `42`; default temperature `0`.
- Retry backoff jitter is seeded per `(seed, sample_id, attempt)` — reproducible, not merely
  "random but consistent within one process."
- `tests/integration/test_run_artifacts.py::test_two_independent_fresh_runs_are_byte_identical`
  proves that two independent fresh runs of the same configuration (same seed, samples, model,
  no shared cache) produce byte-identical `predictions.jsonl` — the same guarantee a real
  temperature-0 provider run should have, modulo whatever non-determinism the provider itself
  introduces.

# Submitting a model result

A result is admitted to the leaderboard when someone else could get it again. That means the
submission carries everything that could move the number.

## 1. Run against a frozen manifest

```bash
financebench eval \
  --manifest configs/manifests/release_v0_1.json \
  --model-config configs/models/your-model.yaml
```

Do **not** use `--max-samples` for a submission. It head-truncates the adapter's file order, which is
deterministic but not stratified — on SECQUE it returns 72 Analysis questions and zero Risk questions
and calls the result "SECQUE". A manifest names the exact sample ids, and a named id that no longer
resolves **fails the run** instead of silently substituting a different question.

## 2. What the submission must include

From `runs/<run_id>/`:

| file | why |
|---|---|
| `environment.json` | The **evaluator fingerprint**. A result scored by a different evaluator is not comparable with the ones already on the board, and will be rejected — not silently averaged. |
| `run_config.json` | Seed, temperature, prompt profile, eval mode, retriever, top-k, scoping. |
| `metrics.json`, `capabilities.json`, `gates.json`, `coverage.json` | The numbers, and what they rest on. |
| `metric_details.jsonl` | **Per-sample** results. Without these a paired comparison is impossible, and an unpaired one can manufacture a difference out of nothing. |
| `predictions.jsonl` | What the model actually said. A score nobody can audit is a claim, not a measurement. |

Plus the model's **digest and quantization** (`ollama show <model>`, or the provider's model id and
snapshot), and the hardware.

## 3. What will get a submission rejected

- **A different evaluator fingerprint** from the runs it is being compared against. Re-score on the
  current commit (`financebench resume --run-id ...` replays cached responses; it costs nothing).
- **A mock run.** `run_type=mock_test` is barred by construction — the mock provider holds the answer
  key, and its scores measure the pipeline, never a model.
- **A `smoke` run.** It is a pipeline test with a handful of in-repo fixtures.
- **A different sample set** presented as the same benchmark. `sample_id_set_hash` is checked.
- **Metric changes that raise a score.** Every metric fix in this repository's history moved a score
  *down* or to "unmeasured", and each bumped the fingerprint. A change that only ever helps is not a
  fix.
- **`None` reported as `0.0`.** A not-applicable result is an absence of evidence, not a failure.

## 4. Reproducing an existing result

Every release ships `release_manifest.json` (dataset hashes, sample ids, model digests, quantization,
runtime versions, prompt/parser/metric/scoring versions, seeds, retrieval index fingerprint, hardware,
commit) and `checksums.txt`. See [`reproducibility.md`](reproducibility.md).

## 5. What a good score does not mean

It does not certify that a model is safe to run unsupervised against real money. It means it did well
on these questions, on this hardware, on this date.

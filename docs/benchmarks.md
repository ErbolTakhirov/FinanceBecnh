# Benchmarks

Nine benchmarks, each pinned to the upstream commit its data comes from
(`evaluation/fingerprint.py:DATASET_ADAPTER_VERSIONS`). Run `financebench licenses` for
redistribution status, and `financebench validate-dataset --all-core` to confirm every sample parses.

## The three with official evaluators — and we are parity-tested against them

| benchmark | pinned to | official metrics | license |
|---|---|---|---|
| **FinQA** | `official@0f16e286` | execution accuracy, program accuracy | MIT |
| **TAT-QA** | `official@870accc4` | exact match, numeracy-aware F1, scale accuracy | MIT |
| **FinanceReasoning** | `official@b0fe6455` | accuracy | Apache-2.0 |

`tests/parity/` runs **the real upstream evaluator** against ours on the same inputs and asserts they
agree: **17 tests, zero skips**. Setup: `bash scripts/setup_references.sh`.

**A skipped parity test proves nothing.** These once went green-with-skips for an entire milestone
because `/tmp` had been cleared and the reference sources had silently vanished. A skip is now a release
gate failure.

## The ones where the metric is ours, and says so

| benchmark | pinned to | metrics | why ours |
|---|---|---|---|
| **FinanceBench** | `open_source@cc39aeb4` | `financebench_answer_accuracy`, `financebench_unsupported_numeric_claim`, `financebench_citation_accuracy` | The dataset **ships no evaluator**. Our metrics are named so they cannot be mistaken for official ones. |
| **ConvFinQA** | `official@cf3eed2d` | `convfinqa_turn_accuracy` (ours) + FinQA's parity-tested executor for execution/program accuracy | ConvFinQA's official metrics grade *programs*; turn accuracy is ours. |
| **SECQUE** | `hf@894196b8` | **diagnostics only** — see below | The gold is an expert's prose. There is no exact-match metric and there cannot be one. |
| **SMB-CFO** | `generated@1` | accuracy, refusal correctness, injection resistance | Generated here. |

### SMB-CFO — the only provably uncontaminated benchmark here

562 cases whose gold answers come from **Python oracles**, never an LLM. A ledger is generated, and the
correct answer is *computed* from it. No model wrote the answer key, so no model can have memorised it.

Splits: `public` (300), `adversarial` (150, carrying **prompt injections with a canary** — a value
appearing nowhere else in the books, so a model that states it can only have read it from the
instruction hidden in its own data), `bilingual` (100, paired EN/RU).

### SECQUE — diagnostics, not a score

565 tasks (Analysis 72 / Comparison 220 / Ratio 188 / Risk 85), MIT, sha256-pinned per file.

The reference answer is an expert analyst's prose. So SECQUE reports **deterministic diagnostics** —
each a checkable property, none a "quality" score:

- `secque_numeric_agreement` — do the figures it states match the expert's?
- `secque_filing_identification` — is it even talking about the right filing?
- `secque_comparison_direction` — did it get the direction of travel right?
- `secque_unsupported_numeric_claim` — did it invent a figure the filing does not contain?

Several return **not-applicable** rather than a score: the Risk split is largely narrative, and a
numeric-agreement metric has nothing to agree with. **Analytical correctness is `NOT_EVALUATED`** — no
available judge passes calibration. See [`known_limitations.md`](known_limitations.md).

**Sampling SECQUE is stratified.** `--max-samples 80` head-truncates the file and returns 72 Analysis +
8 Comparison questions, zero Ratio and zero Risk — a different benchmark wearing SECQUE's name. Use a
frozen manifest (`financebench freeze-manifest`), which round-robins across task families.

## Eval modes

- `context_given` — the evidence is handed to the model. Measures reasoning.
- `retrieval_required` — the model must find its own evidence in a 12,013-page corpus. Measures the
  retrieval system.
- `tool_assisted` — the model may call sandboxed tools. Measures orchestration.

These are **different questions**, and their scores are reported separately (`financial_core_score`,
`financial_rag_score`, `financial_agent_score`). A `context_given` run has said nothing about a
retriever and must not imply that it has.

## Conversation protocols (ConvFinQA)

- `gold_history` — each turn is given the **gold** prior conversation. Isolates per-turn reasoning.
- `model_history` — each turn is given the model's **own** prior answers. Exposes error propagation.

Their scores are **never mixed**. Run both and compare.

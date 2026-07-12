# FinanceBench

**An open, reproducible benchmark platform for evaluating the financial capabilities of LLMs.**

FinanceBench evaluates local models, OpenAI-compatible local servers, cloud/API models,
text-only and multimodal models, RAG systems, and financial tool-using agents — combining the
strongest ideas from existing financial benchmarks (FinQA, ConvFinQA, TAT-QA, FinanceBench,
FinanceReasoning, SECQUE, FinBen, XFinBench, FinMME, and more) while preserving each benchmark's
native metrics and license/redistribution requirements, plus a custom `SMB-CFO` benchmark for
real small-business finance workflows (including paired English/Russian evaluation).

> **Status: early / Milestone 1 (Foundation).** The core pipeline — schemas, provider registry,
> the async execution engine with caching, run artifacts, and CLI — runs end-to-end offline
> against a deterministic mock model. Real dataset adapters and provider integrations are landing
> incrementally; nothing is marked `fully_supported` until it has been executed end-to-end against
> real data in a test. See [`docs/research/benchmark_review.md`](docs/research/benchmark_review.md)
> for exactly what is and isn't available today, and why.

## Why one accuracy number is misleading

A single "financial QA accuracy" score conflates very different failure modes: a model that
gets the right number for the wrong reason, a model that cites a document that doesn't exist, a
model that refuses everything to avoid being wrong, and a model that is simply well-calibrated all
score differently — and matter differently — depending on what you're deploying it for. See
[`docs/research/scoring_design.md`](docs/research/scoring_design.md) for the full reasoning and
[`docs/scoring.md`](docs/scoring.md) for the mechanics.

FinanceBench instead reports, for every run:

- **Native, benchmark-specific metrics** (e.g. FinQA's execution/program accuracy, TAT-QA's
  numeracy-aware F1) — never flattened away.
- Seven normalized **capability dimensions** — numerical reasoning, document grounding &
  retrieval, table/text reasoning, financial analysis & insight, conversational consistency,
  calibration/refusal/reliability, and bilingual EN/RU performance.
- A **Finance Capability Index (FCI)**: a weighted *geometric* mean across those dimensions (so a
  model can't hide a critical weakness behind one strong area), scaled by a transparent
  reliability penalty for unsupported claims, catastrophic numeric errors, and invalid output.
- **Critical gates** that block a "Strong"/"Exceptional" label outright if grounding, calibration,
  or hallucination rates fail minimum thresholds — regardless of the headline FCI.
- **Coverage**, always shown next to the score: which benchmarks/samples were actually evaluated,
  so two models are never presented as comparable when they were scored on different subsets.
- Latency, cost, and hardware requirements as a **separate** Deployment Efficiency Score — never
  mixed into the correctness score.

```text
raw_fci = exp(Σ w_i · ln(max(s_i, ε)))
reliability_factor = max(0.65, 1 − (0.50·unsupported_claim_rate + 0.30·catastrophic_numeric_error_rate + 0.20·invalid_output_rate))
FCI = 100 · raw_fci · reliability_factor
```

Full formula, weights, and gate thresholds: [`docs/scoring.md`](docs/scoring.md).

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/ErbolTakhirov/FinanceBench.git
cd FinanceBench
pip install -e ".[dev]"
```

## Quickstart (offline, no API keys, no GPU)

```bash
python -m financebench.cli doctor
python -m financebench.cli list-benchmarks
python -m financebench.cli licenses
python -m financebench.cli eval --group smoke --model-config configs/models/mock.yaml
python -m financebench.cli leaderboard --runs-dir runs --output reports
```

Provider quickstarts (Ollama, vLLM, llama.cpp, OpenAI, Anthropic, Gemini, OpenRouter, custom
OpenAI-compatible endpoints) are documented in [`docs/providers.md`](docs/providers.md) and
[`docs/local_models.md`](docs/local_models.md) as each lands.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — module layout and design
- [`docs/datasets.md`](docs/datasets.md) / [`docs/licenses.md`](docs/licenses.md) — what's wrapped, and under what terms
- [`docs/metrics.md`](docs/metrics.md) / [`docs/scoring.md`](docs/scoring.md) — native metrics, capability dimensions, FCI, gates
- [`docs/reproducibility.md`](docs/reproducibility.md) — what's recorded so a run can be reproduced
- [`docs/adding_benchmarks.md`](docs/adding_benchmarks.md) / [`docs/adding_models.md`](docs/adding_models.md) — extending the platform

## Limitations

This is evidence about model behavior on specific tasks, not a certification of safety for
autonomous financial decision-making. No public benchmark found during this project's research
tests Russian-language financial reasoning — RU coverage here comes entirely from the custom
SMB-CFO paired EN/RU cases. See `docs/research/benchmark_review.md` for per-benchmark license,
availability, and contamination caveats, and each run's `coverage.json` for exactly what was
evaluated.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

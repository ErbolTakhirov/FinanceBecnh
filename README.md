# FinanceBench

**An open, reproducible benchmark platform for evaluating the financial capabilities of LLMs —
which mostly means refusing to report numbers it cannot stand behind.**

> **Status: `v0.1.0-rc1` (release candidate).** Everything below is marked by *what it has been shown
> to do*, not by whether the code exists. The distinction is the point of the project.

## What is actually verified

| | |
|---|---|
| ✅ **Live-verified** | Ran on real data against a real model; the numbers are in `runs/`. |
| 🔬 **Deterministic diagnostics** | A checkable property (does this figure appear in the filing?), not a quality score. |
| ⚠️ **Implemented, not live-verified** | Complete and unit-tested; **never executed against the real thing**. |
| ⛔ **Blocked** | Cannot be measured here, and the reason is stated. |

**Benchmarks**

| benchmark | status | notes |
|---|---|---|
| FinQA | ✅ live | Official metrics **parity-tested against the upstream evaluator** (17/17, zero skips). |
| TAT-QA | ✅ live | Parity-tested. |
| FinanceReasoning | ✅ live | Parity-tested. |
| FinanceBench (context-given) | ✅ live | **Our metrics, not official** — FinanceBench ships no evaluator, and ours are named so they cannot be mistaken for one. |
| FinanceBench (retrieval) | ✅ live | Real 12,013-page PDF corpus, 84 filings. |
| SMB-CFO | ✅ live | Gold answers come from **Python oracles, never an LLM** — the only provably uncontaminated benchmark here. |
| ConvFinQA | ✅ live | Both `gold_history` and `model_history`. Their scores are never mixed. |
| SECQUE (diagnostics) | 🔬 | 565 tasks. Numeric agreement, filing identification, comparison direction. |
| SECQUE (analytical correctness) | ⛔ | **No available judge passes calibration.** See below. |
| Tool-assisted agent | ✅ live | Sandboxed, deterministic tools. |

**Providers**

| provider | status |
|---|---|
| Ollama | ✅ live-verified — **every real number in this repo came from it** |
| OpenAI / Anthropic / Gemini / OpenRouter | ⚠️ implemented, **never called**. No API key has ever been used here. `financebench verify-providers` labels each by what happens when you call it, not by a class attribute. |
| Multimodal | ⛔ not evaluated. Zero multimodal runs exist. |

## The two honest failures

**SECQUE's analytical score is `NOT_EVALUATED`, and that is a measurement.** The judge framework was
built, and then the judge was *tested before being believed*. `llama3.2:3b`, on 48 cases whose correct
verdict is known by construction, scores **75% accuracy with a 41% false-positive rate** against a 20%
bar. It never rejects a good answer — and it waves through **two-thirds** of answers that name the
wrong company or contain a fabricated figure. It is a yes-man, and the calibration says so in numbers.
So the dimension reports `NOT_EVALUATED`. **Never zero.** A zero would say the model failed; the truth
is that no instrument here can measure it.

**The tools do not help, because the model does not use them.** See the release report.

## Why one accuracy number is misleading

A single "financial QA accuracy" conflates a model that gets the right number for the wrong reason, a
model that cites a document that does not exist, and a model that refuses everything to avoid being
wrong. So every run reports:

- **Native, benchmark-specific metrics** — never flattened away.
- **Ten capability dimensions**, scored independently.
- A **Finance Capability Index**: a weighted *geometric* mean (so a model cannot trade a catastrophic
  weakness for an unrelated strength — 0.9 grounding and 0.1 arithmetic averages to a respectable
  0.5, which is a lie about a model that cannot do arithmetic; the geometric mean says 0.3).
- **Critical gates** that cap the verdict regardless of the headline.
- **Coverage**, next to every score.

```text
raw_fci            = exp(Σ wᵢ · ln(max(sᵢ, ε)) / Σ wᵢ)      # renormalized over the dimensions present
reliability_factor = max(0.65, 1 − (0.50·catastrophic_numeric_error_rate
                                  + 0.30·unsupported_claim_rate
                                  + 0.20·invalid_output_rate))
FCI                = raw_fci · reliability_factor            # on 0–1, and WITHHELD rather than asterisked
```

**The FCI is refused, not caveated.** It is withheld entirely when a critical gate failed, when the
run is a mock, or when the run did not cover SMB-CFO *and* a grounding benchmark *and* refusal —
because a model can be excellent at 10-K arithmetic and unable to tell a small business when it runs
out of money. `capabilities.json` records `fci_withheld_because` in plain words. Nobody reads a
footnote; they read the number.

Full weights and gate thresholds: [`docs/scoring.md`](docs/scoring.md). What is *not* done, and why:
[`docs/known_limitations.md`](docs/known_limitations.md).

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

# Gap audit

**Last updated:** 2026-07-11, after the work described below.
**Verified before writing this:** `pytest` 720 passed · `ruff check` clean · `ruff format` clean ·
`mypy` clean (65 source files) · `pytest tests/parity` 17 passed against the **real official
evaluators** · `financebench validate-dataset --all-core` — 27,065 real samples, zero conversion
errors.

## Status vocabulary

| Status | Meaning |
|---|---|
| `implemented_and_live_verified` | Ran end-to-end against **real data and/or a real model**, output inspected |
| `implemented_unit_tested_only` | Code exists and is tested, but never exercised against the real external thing |
| `partial` | Some of the promised behaviour exists; named gaps remain |
| `stub` | Shape/schema exists, logic does not |
| `missing` | Not written at all |
| `blocked` | Cannot be done here; the blocker is named |

## Where this started, and where it is now

The audit that opened this work said:

> The repository **validates infrastructure, not financial capability**. It has never invoked a
> real language model. No claim about any model's financial ability can currently be supported.

That is no longer true. A real local model (`qwen2.5:3b`, via Ollama) has now answered real FinQA,
TAT-QA and FinanceReasoning questions and been scored by metrics that are **parity-tested against
the benchmarks' own official evaluators**. The result is honest and unflattering, which is the
point.

## The bugs that mattered

Four defects were found, and every one of them was found by *disbelieving a live result* — not by
a test. They are recorded because they are the strongest available evidence for why a benchmark
must be driven end-to-end against a real model before any number it prints is trusted.

| Bug | Effect | How it was found |
|---|---|---|
| `ModelRequest.simulation_context` carried `gold_answer` into the request object — which is serialized into `predictions.jsonl` *and hashed into the cache key* | The answer key was one forgotten `if` away from reaching a real model | Reading the code with the question "where *could* gold go?" |
| A gold FinQA program (`subtract(5829, 5735)`) was hardcoded into the `program_v1` prompt as a format example, lifted from FinQA's own paper | Handed the model the answer to a real test sample. Scrub-equivalence testing cannot see this: the prompt never *varies* with gold, so it scrubs clean while still leaking | A new static-leakage test, written because scrub-equivalence felt insufficient |
| The official TAT-QA `scale_to_num` returns `int`, not `float`; `round(-134, 4)` is `-134` but `round(-134.0, 4)` is `-134.0` | Every negative number normalized to `"-134.0"` instead of `"-134"` and silently failed to exact-match. A systematic deflation of EM and F1 across the whole dataset | Running the real official evaluator side by side |
| `"insufficient_information": null` failed strict `bool` validation, so the whole structured answer was discarded and the raw JSON blob became the "answer" string | ~half of all valid model answers thrown away. **qwen2.5:3b's real FinQA score went 5% → 15% on the same cached responses** once fixed | Getting 5% from a live model and refusing to believe it |

A fifth, of the same family: the response cache stored the *parse* alongside the raw content, so
fixing the parser changed nothing for anything already run — the fix appeared to do nothing.
Content is ground truth; the parse is our code's opinion about it, and our code keeps improving. It
is now re-derived on every cache read.

## Component audit

### Anti-fabrication protections

| Protection | Status |
|---|---|
| Gold-answer leakage prevented **structurally** (the field is gone; `ModelRequest` has nowhere to put an answer) | `implemented_and_live_verified` |
| Scrub-equivalence proof across every benchmark × prompt profile × eval mode | `implemented_and_live_verified` |
| Static-leakage proof (no fixture's gold appears in any prompt's constant text) | `implemented_and_live_verified` |
| `--allow-mock` gate; mock eval refused without it | `implemented_and_live_verified` |
| `run_type=mock_test` / `eligible_for_leaderboard=false` | `implemented_and_live_verified` |
| Mock watermark, before the first number in every report | `implemented_and_live_verified` |
| Mock excluded from the leaderboard | `implemented_and_live_verified` |
| Comparable-run protection (prompt profile + eval mode in the run id) | `partial` — profile/mode collision is prevented; a full `RunFingerprint` check in `compare` is defined but not enforced |

### Evaluation modes

| Mode | Status |
|---|---|
| `context_given` | `implemented_and_live_verified` |
| `retrieval_required` | `stub` — the mode, prompt plumbing and `RetrievedChunk` type exist; **no retriever is wired**. `nomic-embed-text` is available locally for one |
| `tool_assisted` | `stub` — the mode and `tool_agent_v1` profile exist; **no tool executor** |

### Datasets

| Benchmark | Status | Real counts, converted with zero errors |
|---|---|---|
| `finqa` | `implemented_and_live_verified` | 6,251 / 883 / 1,147 |
| `tatqa` | `implemented_and_live_verified` | 13,215 / 1,668 / 1,663 |
| `finance_reasoning` | `implemented_and_live_verified` | 1,000 / 1,000 / 238 |
| `smoke` | `implemented_and_live_verified` | 10 — a pipeline fixture, **not a benchmark** |
| `financebench` | `missing` | 150-row public subset + 368 PDFs are downloaded and understood; adapter not written |
| `convfinqa` | `missing` | Needs sequential turn-chaining in the engine |
| `secque` | `missing` | Needs an LLM judge |
| `smb_cfo` | `missing` | **The platform therefore has no Russian coverage at all, and no uncontaminated benchmark** |

### Metrics

| Metric | Status |
|---|---|
| FinQA execution accuracy (official) | `implemented_and_live_verified` — parity-tested |
| FinQA program accuracy (official, sympy symbolic equivalence) | `implemented_and_live_verified` — parity-tested |
| FinQA answer accuracy (**ours**, tolerance-based) | `implemented_and_live_verified` |
| TAT-QA EM / numeracy-F1 / scale accuracy (official) | `implemented_and_live_verified` — parity-tested, incl. 100+ real dev questions |
| FinanceReasoning accuracy (official, 0.2 % relative) | `implemented_and_live_verified` — parity-tested |
| Deterministic failure attribution (25 types) | `implemented_and_live_verified` |
| Critical gates | `implemented_and_live_verified` |
| Capability dimensions (10, macro-averaged) | `implemented_and_live_verified` |
| Finance Capability Index (geometric, gated) | `implemented_and_live_verified` |
| Finance-readiness verdict | `implemented_and_live_verified` |
| Bootstrap CIs; paired comparison | `implemented_unit_tested_only` — CIs are written into every real run; `compare` does not yet call the paired test |
| Grounding / evidence / hallucination metrics | `missing` — waits on FinanceBench |
| LLM judge | `missing` — waits on SECQUE |

### Providers

| Provider | Status |
|---|---|
| `ollama` | `implemented_and_live_verified` — real inference on 3 benchmarks |
| `openai_compatible` (also covers vLLM, llama.cpp, LM Studio) | `implemented_unit_tested_only` — the code path is the one Ollama uses, but no non-Ollama server was running here to prove it |
| `mock` | `implemented_and_live_verified` (as a *simulator*, which is not evidence of anything about a model) |
| OpenAI / Anthropic / Gemini / OpenRouter | **`blocked`** — not written. They would be `unverified` regardless: **no API keys exist in this environment**, and a provider that has never made a call must not be reported as working |

## What a reader should not conclude

- **Not** that the tested model is representative. `qwen2.5:3b` is a small local model on a 4 GB
  GPU. Its scores say what this benchmark does to a weak model, which is exactly what was being
  checked.
- **Not** that a strong FinQA score would mean strong reasoning. FinQA is from 2021 and is in every
  pretraining scrape. The uncontaminated counterweight (SMB-CFO) does not exist yet.
- **Not** that 40 samples supports a ranking. Every score here carries a bootstrap interval, and at
  40 samples those intervals are wide. The reports say so.

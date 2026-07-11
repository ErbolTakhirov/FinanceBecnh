# Final core gap audit — v0.1.0-rc1

Every feature, classified by **what it has actually been shown to do**, not by whether the code
exists. The categories are the ones the sprint brief specified, and the distinction between the
first two is the one that matters:

| status | means |
|---|---|
| `real_data_live_verified` | ran on real data against a real model, and the numbers are in `runs/` |
| `real_data_not_live_verified` | complete, but no live model run has exercised it end to end |
| `unit_tested_only` | tested against fixtures and mocks; never met real data |
| `partial` | works, with a stated limitation |
| `stub` | scaffolding only |
| `blocked` | cannot be completed here, with the reason |
| `not_planned_for_v0_1` | deliberately out of scope |

---

## Benchmarks

| feature | status | evidence / limitation |
|---|---|---|
| FinQA | `real_data_live_verified` | official metrics **parity-tested against the real upstream evaluator** (17/17, 0 skips). Live on qwen2.5 3B + 7B. |
| TAT-QA | `real_data_live_verified` | parity-tested. Live on 3B + 7B. |
| FinanceReasoning | `real_data_live_verified` | parity-tested. Live on 3B + 7B. |
| FinanceBench `context_given` | `real_data_live_verified` | 150/150, qwen2.5:3b. **Ours, not official** — FinanceBench ships no evaluator, and the metrics are named so it cannot be mistaken. |
| FinanceBench `retrieval_required` | `real_data_live_verified` | 150/150 over a real 12,013-page PDF corpus. |
| SMB-CFO | `real_data_live_verified` | 562 cases from Python oracles. **No LLM ever writes a gold answer** — the only provably uncontaminated benchmark here. |
| ConvFinQA (both protocols) | `real_data_live_verified` | 30 conversations / 120 turns under `gold_history` **and** `model_history`. |
| **SECQUE — adapter + diagnostics** | `real_data_live_verified` | 565 tasks, MIT, sha256-pinned. Live run in progress at time of writing; diagnostics verified against real filings. |
| **SECQUE — analytical judgment** | **`blocked`** | **No available judge passes calibration.** See below. |
| **Tool-assisted evaluation** | `real_data_live_verified` | live on qwen2.5:3b. First result: it calls **no tool at all** on 5 of 6 questions. |

---

## The two honest failures

### SECQUE's analytical score is `NOT_EVALUATED`, and that is a measurement

Not an omission. The judge framework was built, and then the judge was **tested before being
believed** — which is the entire point, and which almost nothing in this space does.

`llama3.2:3b`, 48 calibration cases whose correct verdict is known by construction:

| what the answer was | judge got it right |
|---|---|
| the expert's own answer | 100 % |
| correct but concise | 100 % |
| minor rounding | 100 % |
| a refusal, where the filing plainly answers it | 100 % |
| the direction of travel inverted | 80 % |
| fluent, unsupported boilerplate | 50 % |
| **an invented figure** | **33 %** |
| **the wrong company entirely** | **33 %** |

**False-positive rate 41 % against a bar of 20 %. False negatives: zero.**

It never rejects a good answer, and it waves through two-thirds of answers that are about the wrong
company or contain fabricated figures. It is a yes-man, and the calibration says so in numbers.

`qwen3:8b` was tried first and does not work at all: it is a *thinking* model and spends its whole
token budget inside `<think>`, returning an **empty string** after 116 seconds per call.
`qwen2.5:7b` is refused outright — same family as the candidate, and a model grading its own family
is not evidence.

So SECQUE's analytical dimension reports `NOT_EVALUATED`. **Never zero.** A zero would say the model
failed; the truth is that no instrument here can measure it.

### The tools do not help, because the model does not use them

qwen2.5:3b, live, tool-assisted:

```
tool_selection_accuracy   0.167    5 of 6 questions: called NO TOOL AT ALL
tool_execution_success    0.000    its one call had invalid arguments
tool_result_utilization   None     not applicable — nothing ever executed
tool_security_rejection   1.000    never probed the sandbox
```

That `None` is the discipline holding. A `0.0` would read as *"the model ignored its tools"*, which
would be false — no tool ever ran, so there was no result to ignore.

---

## Infrastructure

| feature | status | notes |
|---|---|---|
| Sandboxed tool runtime | `real_data_live_verified` | AST allow-list, never `eval`. 54 adversarial tests: `__import__`, attribute traversal, env-var reads, path traversal, network, `2 ** 999999999`. |
| Evaluator fingerprint | `real_data_live_verified` | parser + metrics + adapters + retrieval + scoring. A test fails if a registered metric is unversioned. |
| Gold-leakage prevention | `real_data_live_verified` | structural (no field can carry gold), scrub-equivalence, and a positional check for ConvFinQA, where prior-turn gold legitimately *is* in the prompt. |
| Retrieval: BM25 | `real_data_live_verified` | open-corpus **and** genuinely document-scoped. |
| Retrieval: dense / hybrid | `partial` | implemented; the 12,013-page embedding index is **still building** at time of writing (checkpointed, resumable). No dense numbers are claimed until it completes. |
| Ollama provider | `real_data_live_verified` | every real number in `runs/` came from it. |
| OpenAI / Anthropic / Gemini / OpenRouter | `real_data_not_live_verified` | implemented, 38 tests against a mocked transport. **No API keys exist here, so none has ever made a successful call.** `financebench verify-providers` calls the real endpoint and labels them by what happens — not by a class attribute. |
| Confidence intervals | `real_data_live_verified` | bootstrap, on every metric. They stopped me reporting a regression that wasn't there. |

---

## What is NOT done

- **7B coverage is thin.** FinQA / TAT-QA / FinanceReasoning at 40 samples each. There is no 7B
  FinanceBench, SMB-CFO or ConvFinQA. The "two-model comparison" is narrower than a reader would
  assume, and the release report says so.
- **The full requested release matrix is ~75–100 GPU-hours** on this 4 GB GTX 1650 (measured, not
  estimated: SMB-CFO alone is 150 s/sample, so 300 samples × 2 models = 25 h). It does not fit, and
  every sample count actually run is stated.
- **External market-data tools** — `not_planned_for_v0_1`. A benchmark whose scores depend on what a
  third-party endpoint returned on a Tuesday is not a benchmark; it is a snapshot of a Tuesday.

---

## The bugs this sprint found, and what they had been hiding

Each was found by **disbelieving a result**, not by a test going red.

1. **`document_scoped` never scoped the document.** `corpus.scoped_to()` was correct and had *zero
   callers*. Runs were stamped `document_scoped: true` while BM25 searched all 12,013 pages. Page
   recall 4.0 % → **18.7 %** once fixed.
2. **The hallucination detector got *weaker* the more numbers a document had.** A 0.5 % window after
   scaling meant an invented `987,654,321` was "supported" by a filing's `983`. On a 733-number SEC
   filing the candidate set is so dense that almost any large invented figure lands near something.
   Now requires **leading-digit agreement**. Every previous unsupported-claim rate is an
   understatement.
3. **`--max-samples 80` on SECQUE returned a different benchmark.** 72 Analysis + 8 Comparison; zero
   Ratio, zero Risk — reported as "SECQUE".
4. **A year was being read as a stated figure.** `"...no entries for December 2027."` tokenizes as
   `2027.` — full stop attached — so the year regex missed and a **correct refusal became a
   hallucination**. The third time this project's refusal metric has tried to invert itself.
5. **`round(x, 2)` raised on every call** — the single most common financial tool call, broken 100 %
   of the time, because every sandbox argument is a `Decimal` and Python's `round` needs an `int`.
6. **`1/0` was recorded as a security event**, burying the real sandbox-probe signal under a pile of
   division errors.
7. **The parity suite had quietly stopped proving anything.** `/tmp` was cleared and 17 tests went
   green-with-skips. The setup instructions were themselves wrong three ways.

The through-line: **every one of them produced a plausible number.** None crashed. That is the
failure mode this platform exists to catch, and it is why "the tests pass" is not the standard.

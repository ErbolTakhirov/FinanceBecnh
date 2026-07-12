# Changelog

## v0.1.0-rc1 — unreleased

The first release candidate. Everything below was verified against real data and a real model, or is
marked as not verified.

### The two results

**Giving qwen2.5:3b tools made it significantly worse.** Same 150 sample ids, direct vs
tool-assisted: FinQA answer accuracy **0.147 → 0.027**, TAT-QA exact match **0.173 → 0.067**. Paired
bootstrap, 95% CI `[+0.040, +0.213]` and `[+0.027, +0.200]` — both exclude zero. The FinQA 2×2 is
`only-direct-right 11 / only-tools-right 2 / both-right 0`.

And not because it used the tools badly: `tool_invocation_rate = 0.013` — it called a tool on **2 of
150 questions**. The agent scaffolding degraded its arithmetic while it ignored the tools, and cost
27% more tokens doing it. The sandbox was never breached (`tool_security_rejection = 1.000`).

**Retrieval is not the bottleneck; the model is.** Fixing document scoping raised page recall
**4.0% → 18.7%** (4.7×) and produced *no statistically supported* improvement in answer accuracy, while
`generation_error_after_retrieval` rose 2 → 7. Reading those 7 by hand: every one is a **JSON-envelope
failure**. The retriever found the page and the model answered in its own shape. The fix is a parser,
not an index.

### The bugs this release found — every one produced a plausible number

None of these crashed. Each was found by disbelieving a result.

1. **Both models reported a Financial Core Score of `0.900`.** Every SECQUE capability dimension was
   fed the *absence-of-hallucination* metric, so "document grounding" and "table/text reasoning" both
   meant "did it avoid inventing a number" — which a model that emits no numbers passes perfectly. The
   metrics that discriminate between the models fed **no dimension at all**. True values: the models
   agree with the expert's figures **8%** and **11%** of the time, and the 7B names the **wrong company
   in 51%** of its answers. Core Score 0.900 → **0.354 / 0.307**. `SCORING_VERSION` 2 → 3.
2. **Provider timeouts were scored as the model's financial failures.** Three
   `ollama request timed out after 180.0s` errors — GPU contention from another process on this
   machine — were graded `passed=False` against the 3B, in exactly the metrics the release compares
   against the 7B (which ran at a 300 s timeout and errored zero times). That comparison was partly
   measuring our own timeout budget.
3. **`secque_comparison_direction` reported `1.000` while missing the clearest inversion in the set.**
   Gold: *"EBIT 2018: $4,379m / EBIT 2017: $4,945m"* (a fall). Model: *"EBIT **increased** from $5,192m
   to $5,525m"* — both figures invented, conclusion inverted. The metric returned **not-applicable**,
   because the expert stated the direction by listing two years rather than writing "decreased". A
   1.000 computed only over the questions a metric finds easy is not a lenient score; it is an artifact
   of the metric's own coverage. v1 → v2.
4. **`summary.md` rendered every SKIPPED gate as `**FAIL**`.** `passed=None` fell to the else branch,
   so every run on disk reported a fabricated critical failure of the injection gate — contradicting
   the `"skipped": true` in its own `gates.json`.
5. **`arguments_valid` was read off English prose** — substring-matching the error message. A call with
   plainly wrong arguments was recorded as **valid**. Every v1 argument-validity number is an
   overstatement.
6. **`n` counted samples a metric never graded**, overstating the evidence under a mean by up to a
   third (`n: 80` for a mean over 62).
7. **The leaderboard could never display an FCI** — it read a flat `capabilities.json` that has been
   nested for two milestones, so every `fci`/`verdict`/`band` was silently `null`.
8. **Two different retrieval arms resolved to the same run id.** BM25/k=10/scoped and
   hybrid/k=20/scoped — two experiments whose whole purpose is to be compared against each other —
   would have overwritten one another in place.
9. **`resume` did not restore the run.** It dropped the prompt profile, eval mode, retriever, top-k,
   scoping *and* the frozen manifest — so resuming a 150-sample manifest run reloaded the entire
   benchmark (2,815 samples) and would have published the result under the original run's id.
10. **`CITATION.cff` claimed MIT while `LICENSE` says Apache-2.0.**

### Not fixed, on purpose

`financebench_answer_accuracy` allows a **1% relative band**, which credits an answer wrong by **$27
million** (gold $12,645.00, model 12,672.0). I judge that too loose. **I have not changed it.** The band
was chosen deliberately, before any results existed. Tightening it now — having seen exactly which
answers it credits — would be selecting a metric rule by its effect on the score, and the fact that the
effect would be to *lower* the score does not make it acceptable. Recorded as a validity threat.

### Benchmarks

- **FinQA, TAT-QA, FinanceReasoning** — official metrics **parity-tested against the real upstream
  evaluators** (17/17, zero skips). Live on qwen2.5 3B and 7B.
- **FinanceBench** — `context_given` and `retrieval_required`, over a real 12,013-page PDF corpus.
- **SMB-CFO** — 562 small-business cases whose gold answers come from **Python oracles, never an
  LLM**. The only provably uncontaminated benchmark here. Prompt-injection resistance, EN/RU pairs.
- **ConvFinQA** — real conversations under two protocols (`gold_history`, `model_history`) whose
  scores are never mixed.
- **SECQUE** — 565 expert-written SEC-filing analysis tasks. Deterministic diagnostics ship; the
  analytical judgment does **not** (see below).

### Evaluation

- **Sandboxed tool runtime** — an AST allow-list, never `eval`. Decimal arithmetic. 54 adversarial
  tests.
- **Calibrated LLM judge** — and it **failed its own calibration**, so SECQUE's analytical score is
  reported as `NOT_EVALUATED` rather than as a number nobody should believe.
- **Evaluator fingerprint** — parser, metrics, adapters, retrieval and scoring versions. Two runs
  with different fingerprints are not comparable and the reports say so.
- **Coverage-gated scoring** — the Finance Capability Index is **refused** unless the run actually
  asked the questions it claims to answer.

### Fixed

- `document_scoped` never scoped the document. Page recall 4.0 % → 18.7 %.
- The hallucination detector got weaker the more numbers a document contained. Now requires
  leading-digit agreement; every previous unsupported-claim rate was an understatement.
- `--max-samples` on SECQUE returned a category-skewed sample and called it SECQUE.
- A year in a refusal (`"...no entries for December 2027."`) was read as a stated figure, turning a
  correct refusal into a hallucination.
- `round(x, 2)` raised on every call in the tool sandbox.
- The parity suite had silently stopped proving anything after `/tmp` was cleared.

### Known limitations

See `docs/research/final_core_gap_audit.md`. In short: no API provider is live-verified (no keys
exist on the build machine), 7B coverage is thin, and dense/hybrid retrieval numbers are not yet
claimed.

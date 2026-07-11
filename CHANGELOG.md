# Changelog

## v0.1.0-rc1 — unreleased

The first release candidate. Everything below was verified against real data and a real model, or is
marked as not verified.

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

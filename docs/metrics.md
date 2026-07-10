# Metrics

Two layers, always kept distinct:

1. **Native metrics** — each wrapped benchmark's own official evaluation (e.g. FinQA's
   execution/program accuracy, TAT-QA's numeracy-aware F1). Never discarded or flattened away.
2. **Unified metrics** — deterministic numeric/text/boolean grading (`evaluation/metrics/`) that
   lets samples from different benchmarks feed the same capability-dimension rollup.

Milestone 1 ships `exact_match` (case/whitespace-insensitive string equality — deliberately
*not* numeric-tolerant, so its gap versus a prose answer like "approximately 25%" is visible and
motivates the numeric-tolerant metric that follows it). Milestone 2 adds the numeric parser
(commas, decimal-commas, parenthesized negatives, percentages, basis points, currency, K/M/B
scale) and the first native metrics (FinQA, TAT-QA, FinanceReasoning).

See [`docs/scoring.md`](scoring.md) for how per-sample metric results roll up into capability
scores and the Finance Capability Index.

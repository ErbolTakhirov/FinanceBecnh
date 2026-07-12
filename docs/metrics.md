# Metrics

Two layers, always kept distinct:

1. **Native metrics** — each wrapped benchmark's own official evaluation. Never discarded or
   flattened away.
2. **Unified metrics** — deterministic numeric/text/boolean grading (`evaluation/metrics/`) that lets
   samples from different benchmarks feed the same capability rollup.

## Which metrics are official, and which are ours

| benchmark | metric | official? |
|---|---|---|
| FinQA | `finqa_execution_accuracy`, `finqa_program_accuracy` | ✅ **parity-tested against the real upstream evaluator** |
| TAT-QA | `tatqa_exact_match`, `tatqa_f1`, `tatqa_scale_accuracy` | ✅ parity-tested |
| FinanceReasoning | `finance_reasoning_accuracy` | ✅ parity-tested |
| FinQA | `finqa_answer_accuracy` | ours (the official metrics grade *programs*) |
| ConvFinQA | `convfinqa_turn_accuracy` | ours |
| FinanceBench | `financebench_*` | **ours — the dataset ships no evaluator**, and they are named so they cannot be mistaken for official ones |
| SMB-CFO | `smb_cfo_*` | ours (the benchmark is ours; gold comes from Python oracles) |
| SECQUE | `secque_*` | ours — **diagnostics, not a quality score** |

`tests/parity/` runs the **real upstream evaluator** against ours on the same inputs and asserts they
agree: **17 tests, zero skips**. A skip is a release-gate failure — the suite once went
green-with-skips for a whole milestone because `/tmp` had been cleared.

## The numeric parser

Handles commas, decimal-commas, parenthesized negatives, percentages, basis points, currency symbols,
and K/M/B scale words. Its correctness is load-bearing: fixing it once moved a FinQA score from **5%
to 15%** on identical cached model responses. That is why the parser is versioned into the evaluator
fingerprint.

## `None` is not zero

A metric returns `passed=None` for *"this question cannot be graded by me"* — FinanceBench's 61
analytical questions have no deterministically checkable answer; SMB-CFO's accuracy metric cannot grade
a question the books cannot answer; a provider timeout produced no answer at all.

Not-applicable results are **excluded** from every rollup. They were once scored as **0.0**, which is
the benchmark inventing failures the model never committed — in the one direction nobody thinks to
check, because a low score looks like a finding.

`n` on an aggregate is what the metric **actually graded**; `n_not_applicable` sits beside it. A mean
over 62 of 80 samples is a different claim from a mean over 80.

## Tool metrics

`tool_result_utilization` is the one that matters: a model that calls the calculator, receives `40.55`,
and then writes "approximately 38" has made a **trust** error, not an arithmetic one — and every
end-to-end accuracy metric misattributes it to the sums, which is the thing it got right.

The rest exist because they separate failures a single number conflates. `tool_selection_accuracy = 0`
covers both *"called nothing"* and *"invented a tool that does not exist"*, and those have opposite
fixes.

See [`docs/scoring.md`](scoring.md) for how per-sample results roll up into capability scores and the
Finance Capability Index — and for the conditions under which the index is **refused**.

# Scoring design: why one number is misleading, and what FinanceBecnh reports instead

## The problem with a single accuracy average

Take three models evaluated on the same 1,000-question financial benchmark, all scoring "82%
accuracy":

- **Model A** gets 82% of arithmetic questions right, but when it cites a source for its answer,
  the citation points at the wrong page or a document that doesn't exist 40% of the time.
- **Model B** gets simple lookups right but silently guesses on anything requiring multi-step
  reasoning, and never says "I don't know" even when the source document plainly lacks the
  answer.
- **Model C** is genuinely well-calibrated: it answers correctly when it has enough information
  and explicitly refuses otherwise, at the cost of a slightly lower raw hit rate on some
  edge-case questions.

A single macro-averaged accuracy number cannot distinguish these three. Worse, if the benchmark's
question mix happens to be dominated by simple lookups, Model B's silent guessing is invisible —
it looks identical to Model C's genuine competence until someone hands it a question the source
document doesn't answer. For financial work specifically, the failure that matters most —
confidently inventing a number that isn't supported by any evidence — is exactly the failure mode
a naive accuracy average is *least* able to surface, because a hallucinated-but-plausible number
scores identically to a correctly-derived one on exact-match.

This is not a hypothetical concern specific to this platform's design: it's the documented
behavior of several benchmarks reviewed for this project (see
[`benchmark_review.md`](benchmark_review.md)) — FinanceBench's own headline result is that
GPT-4-Turbo-with-retrieval "incorrectly answered or refused" 81% of questions, a number that only
means something once "incorrect" and "refused" are broken apart, and once retrieval failure is
separated from generation failure.

## What FinanceBecnh reports instead

For every run, the platform reports four distinct layers, deliberately never collapsed into each
other:

1. **Native, benchmark-specific metrics** — FinQA's execution/program accuracy, TAT-QA's
   numeracy-aware F1, SECQUE's judge-based rubric score, and so on, exactly as each benchmark's
   own authors defined them. These are never discarded or reduced to a generic accuracy number;
   a leaderboard entry always shows what a domain expert reading the original paper would
   recognize.
2. **Seven normalized capability dimensions** (below) — the layer that makes cross-benchmark
   comparison possible without pretending all benchmarks measure the same thing.
3. **The Finance Capability Index (FCI)** — one headline number, but constructed specifically so
   it *cannot* be gamed by excelling in one dimension while failing badly in another (see the
   geometric-mean rationale below).
4. **Critical gates and coverage** — a mechanism that can override the headline number entirely:
   a model with a high FCI but a failing grounding gate is never labeled "Strong," and a model
   evaluated on a narrow subset is never presented as comparable to one evaluated on the full
   suite.

## The seven capability dimensions

| Dimension | Weight | What it measures |
|---|---|---|
| `numerical_reasoning` | 25% | Can the model do the arithmetic — extraction, multi-step calculation, program derivation — correctly? |
| `document_grounding_and_retrieval` | 20% | Does the model find and cite the right evidence, and only claim what the evidence supports? |
| `table_text_reasoning` | 15% | Can the model combine structured (table) and unstructured (prose) context correctly? |
| `financial_analysis_and_insight` | 15% | Beyond extraction: does the model produce a useful analyst-style conclusion? |
| `conversational_consistency` | 10% | Does the model track context correctly across multi-turn conversations (e.g. ConvFinQA-style turn dependency)? |
| `calibration_refusal_and_reliability` | 10% | Does the model refuse when it should, and *not* refuse when it shouldn't? |
| `bilingual_en_ru` | 5% | Is Russian-language financial performance comparable to English performance? (Sourced entirely from the custom SMB-CFO paired cases — see `benchmark_review.md`'s cross-cutting findings on why no third-party benchmark can answer this.) |

Weights are configurable (`configs/scoring/default.yaml`, landing in Milestone 6) and are
deliberately unequal: numerical correctness and grounding get the most weight because a wrong
number or an invented citation is the failure mode most likely to cause real financial harm,
while bilingual coverage — real, but a smaller slice of most deployments' actual usage — gets the
least.

Aggregation is hierarchical, in this order, so a benchmark with 10,000 questions can't
mathematically drown out one with 200:

1. **Sample → task**: metric results average within a task family (e.g. all "percentage change"
   questions in FinQA).
2. **Task → benchmark**: task families macro-average within a benchmark (not sample-count-weighted).
3. **Benchmark → capability**: benchmarks macro-average within whichever capability dimension(s)
   their task types map to (a benchmark can contribute to more than one dimension).
4. **Capability → FCI**: the weighted geometric mean described below.

## The Finance Capability Index

A weighted **arithmetic** mean would let a model compensate for a severe weakness in one
dimension by being excellent in another — e.g., a model that is superb at simple arithmetic but
essentially unreliable at grounding could still post a respectable blended score. A weighted
**geometric** mean does not have this property: because it multiplies (rather than adds)
contributions, a score near zero in any single dimension drags the whole index toward zero
regardless of how strong the other dimensions are.

For normalized capability scores `s_i ∈ [0,1]` and weights `w_i` (summing to 1):

```text
raw_fci = exp(Σ w_i · ln(max(s_i, ε)))
```

(`ε` is a small floor, e.g. `1e-4`, so a literal zero score doesn't send the log to `-∞`.)

This raw index is then scaled by a **reliability factor** — a transparent penalty for the
behaviors that make a model actively dangerous to deploy, not just imprecise:

```text
reliability_penalty =
    0.50 · unsupported_claim_rate
  + 0.30 · catastrophic_numeric_error_rate
  + 0.20 · invalid_output_rate

reliability_factor = max(0.65, 1 − reliability_penalty)

FCI = 100 · raw_fci · reliability_factor
```

The floor of `0.65` on the reliability factor is deliberate: it bounds how much the reliability
penalty alone can suppress the score (at most a 35% haircut), so the FCI stays primarily a
*capability* measure — reliability failures are additionally and more visibly enforced through
the critical gates below, which can block a deployment label outright regardless of the numeric
FCI.

**Catastrophic numeric errors** are deliberately defined as *task-aware* mistakes, not "any wrong
number": wrong sign, wrong order of magnitude, wrong currency, percentage-vs-raw-value confusion,
a value with no support in the evidence, or a period mix-up that flips the conclusion. An
off-by-one-cent rounding difference is not catastrophic; reporting FY2024 revenue as FY2025's
answer to a same-magnitude, materially wrong conclusion is.

## Critical gates

A high FCI is necessary but not sufficient for a "Strong" or "Exceptional" label. Default gates:

- numerical reasoning ≥ 70
- document grounding ≥ 70
- table-text reasoning ≥ 65
- calibration/reliability ≥ 70
- unsupported claim rate ≤ 8%
- catastrophic numeric error rate ≤ 5%
- invalid output rate ≤ 5%
- answerable-question refusal rate ≤ 10% (a model that refuses too much is not useful either)
- unanswerable-question correct-refusal recall ≥ 75%

Score bands (`90–100` Exceptional / `80–89.99` Strong / `70–79.99` Usable with human review /
`60–69.99` Limited / `<60` Not reliable) are capped by gate status: **any failed critical gate
appends "Critical gate failed" to the label and blocks the Strong/Exceptional tiers outright**,
regardless of the numeric FCI. A model cannot buy its way past a hallucination problem with a
strong arithmetic score.

## Coverage: never compare apples to oranges

Every report shows, alongside the score: requested vs. supported benchmarks, evaluated vs.
skipped samples, and separate coverage percentages for text-only, multimodal, Russian-language,
and agentic/tool-use samples. Two models are never presented as directly comparable unless their
coverage matches — a model evaluated only on the `smoke` group and one evaluated on the full
`core_public` group produce structurally different, non-comparable reports, and the leaderboard
must say so rather than silently ranking them side by side. A score computed on an
under-powered sample count is labeled `Provisional` rather than presented with false confidence.

## Statistical quality

Point estimates alone overstate precision. The platform computes bootstrap 95% confidence
intervals per capability dimension and per native metric, uses paired comparison when two models
were run on identical samples, and flags when an observed score difference between two models
falls within the uncertainty band rather than reporting it as a real gap. (Milestone 1 ships the
artifact *shape* this needs — `confidence_intervals.json` is a valid, schema-correct file with
`ci_low`/`ci_high` fields present and `None` — so Milestone 6 populates real numbers without a
breaking format change.)

## Deployment efficiency stays separate

Latency, throughput, context limits, provider error rate, cost, and hardware requirements are
reported as a distinct **Deployment Efficiency Score**, never blended into the FCI. A model can
be simultaneously "financially capable" and "too slow/expensive for this use case" — collapsing
those into one number would hide a real, separate decision a deploying team needs to make.

## What's implemented today vs. planned

Milestone 1 ships: the seven capability dimensions and their weights (`evaluation/
capability_map.py`), a tag-to-dimension routing table, and the `MetricAggregate` shape that
`confidence_intervals.json`/`metrics.json`/`capabilities.json` are built from. The FCI formula,
critical gates, bootstrap confidence intervals, the tag→dimension mapping as *configuration*
rather than a Python dict, paired significance testing, and the Deployment Efficiency Score are
Milestone 6 work — `gates.json` and `confidence_intervals.json` are written today as valid,
schema-correct, honestly-empty placeholders (`evaluated: false`) rather than omitted or faked.

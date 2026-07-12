# FinanceBench v0.1.0-rc1 — release report

**qwen2.5:3b and qwen2.5:7b, on a GTX 1650 (4 GB).** Evaluator fingerprint `80ca8a678b1c4fa1`.

> **A dash means NOT MEASURED. It never means zero.**
> An `INSUFFICIENT_COVERAGE` index is a **refusal**, not a missing number: the run did not ask enough
> to support the claim an index makes, and the reason is printed beside it.

---

## The headline: giving a small model tools made it significantly worse

The paired experiment ran the **same 150 sample ids** (FinQA + TAT-QA, frozen manifest
`tool_paired_v1`, `id_hash=7c839cfbc46cb862`) twice: once answering directly, once with a calculator,
a formula registry, a table query, a CSV query and an FX converter available.

| metric | direct | tool-assisted | difference | 95% CI (paired bootstrap) | |
|---|---|---|---|---|---|
| FinQA answer accuracy | **0.1467** | **0.0267** | +0.120 | `[+0.040, +0.213]` | **significant** |
| TAT-QA exact match | **0.1733** | **0.0667** | +0.107 | `[+0.027, +0.200]` | **significant** |
| exact match (all 150) | **0.1400** | **0.0600** | +0.080 | `[+0.027, +0.140]` | **significant** |

Every interval excludes zero. **Tools cost qwen2.5:3b about 8 accuracy points**, and on FinQA they cost
it **five-sixths of its correct answers**.

The 2×2 is where it becomes clear — a difference of means would have hidden this:

```
FinQA, 75 paired questions
  only DIRECT right    11
  only TOOLS  right     2
  both right            0        <-- zero
  both wrong           62
```

**And it is not because the model used the tools badly. It is because it barely used them at all:**

| tool metric | value | n | reading |
|---|---|---|---|
| `tool_invocation_rate` | **0.013** | 150 | it called a tool on **2 of 150 questions** |
| `tool_selection_accuracy` | 0.013 | 150 | |
| `tool_execution_success` | 0.500 | **2** | of the two calls, one ran |
| `tool_argument_validity` | 0.500 | **2** | the other had malformed arguments |
| `tool_result_utilization` | 1.000 | **1** | the one result it got, it used |
| `tool_error_recovery` | 0.000 | **1** | after the failed call, it never recovered |
| `tool_hallucination_rate` | 1.000 | 2 | it never invented a tool |
| `tool_security_rejection` | **1.000** | 150 | **the sandbox was never breached** |

So the damage was done by the **agent scaffolding itself** — the JSON envelope that asks the model to
choose between emitting a tool call and emitting an answer — not by the tools. A 3B model asked to
route its own reasoning through a protocol gets worse at the underlying arithmetic, while ignoring the
protocol. It also spent **27% more tokens** doing it (207,473 vs 163,028).

### And the 7B, on the same 150 questions

| | 3B direct | 3B + tools | **7B direct** |
|---|---|---|---|
| FinQA answer accuracy | 0.147 | 0.027 | **0.267** |
| TAT-QA exact match | 0.173 | 0.067 | **0.267** |
| exact match (all 150) | 0.140 | 0.060 | **0.167** |

Paired bootstrap, identical sample ids, identical evaluator:

| comparison | metric | difference | 95% CI | |
|---|---|---|---|---|
| 7B direct **vs** 3B direct | FinQA | 0.120 | `[-0.227, -0.013]` | **7B wins** |
| **7B direct vs 3B + tools** | FinQA | **0.240** | `[-0.347, -0.133]` | **7B wins, 10×** |
| **7B direct vs 3B + tools** | TAT-QA | **0.200** | `[-0.307, -0.093]` | **7B wins** |

### The six questions, answered

**Does tool access improve correctness?** **No — it significantly reduces it** for this model.

**Does it reduce catastrophic numeric errors?** No.

**Does the model actually invoke tools?** Almost never — **2 of 150 questions**.

**Does it use correct tool output?** The one successful execution *was* used. `n=1`; that is not a
claim about anything, and it is printed with its `n` so that it cannot be read as one.

**Does orchestration introduce new failures?** **Yes — that is the entire effect.** The model barely
touched the tools and still lost five-sixths of its FinQA answers.

**Can a smaller model with tools outperform a larger model without tools?**
**Emphatically no.** 3B+tools scores **0.027** against 7B-direct's **0.267** — *ten times worse*, with
the interval excluding zero. On this evidence, spending a small model's context budget on a tool
protocol is strictly worse than spending it on a bigger model.

---

## SECQUE: both models, on identical stratified samples

80 tasks, stratified across Analysis / Comparison / Ratio / Risk. Same 80 sample ids for both models,
same evaluator.

| | qwen2.5:3b | qwen2.5:7b |
|---|---|---|
| `secque_numeric_agreement` | 0.080 (n=62, 18 n/a) | **0.115** (n=62, 18 n/a) |
| `secque_filing_identification` | 0.607 (n=56) | 0.494 (n=62) |
| `secque_unsupported_numeric_claim` | 0.938 (n=80) | 0.900 (n=80) |
| `exact_match` | 0.000 | 0.000 |
| **Financial Core Score** | **0.354** | **0.307** |
| **analytical correctness** | **`NOT_EVALUATED`** | **`NOT_EVALUATED`** |
| verdict | **NOT_FINANCE_READY** | **NOT_FINANCE_READY** |

**Both models agree with the expert analyst's figures roughly one time in ten**, and the 7B names the
**wrong company in 51% of its answers**. These are not models that can read a 10-K.

> ⚠️ **The 3B's higher filing-identification score is NOT a supportable claim.** It is graded on **56**
> of 80 samples versus the 7B's **62** — the metric is not-applicable when the model declines or
> produces nothing to check — so the 3B's number sits on a **smaller, self-selected subset**. Different
> denominators; not a comparison.

**Before this release, both models reported a Financial Core Score of 0.900.** Every SECQUE capability
dimension was being fed the *absence-of-hallucination* metric, so "document grounding" and "table/text
reasoning" were both reporting "did it avoid inventing a number" — which a model that emits no numbers
passes perfectly. Fixed; see `manual_validity_review.md`.

---

## Retrieval: the bottleneck is the model, not the retriever

The full 6-arm ablation over a real **12,013-page, 84-filing** corpus (no model in the loop):

| retriever | scope | page recall @20 | doc recall @20 |
|---|---|---|---|
| bm25 | open-corpus | 7.3% | 79.3% |
| bm25 | doc-scoped | 27.3% | 100% |
| dense | open-corpus | 2.0% | **27.3%** |
| dense | doc-scoped | 34.0% | 100% |
| hybrid | open-corpus | 4.7% | 67.3% |
| **hybrid** | **doc-scoped** | **38.7%** | 100% |

Dense retrieval is **dramatically worse at finding the company** (27.3% document recall vs BM25's
79.3%) — the questions name a company and a year, which is a lexical match, and the embedding blurs
exactly that. It is better at finding the *page* once the company is known. Hybrid gets both.

**But retrieval quality is not what is limiting the answers.** Fixing document scoping raised page
recall from 4.0% → 18.7% (**4.7×**) and produced **no statistically supported improvement in answer
accuracy** (4 → 2 correct of 89; the 95% CI contains the old value). Meanwhile
`generation_error_after_retrieval` rose from 2 → 7.

Reading those 7 failures by hand (`manual_validity_review.md`): **all of them are JSON-envelope
failures.** The retriever found the page, the model computed something, and then answered in its own
shape — `{"financial_metric": "Retention Ratio", "value": 0.31}` instead of the requested envelope. The
fix is a parser or a prompt. It is not an index.

| stage | value |
|---|---|
| retrieval succeeded (page recall @10, bm25 doc-scoped) | 18.7% |
| end-to-end answer accuracy | 2.25% |
| **oracle** (context handed to the model) | **23.6%** |

The gap between 23.6% and 2.25% is the retriever. The gap between 23.6% and 100% is the model.

---

## Coverage, and what is refused

| | |
|---|---|
| Evaluator fingerprint | `80ca8a678b1c4fa1` — every run on this page was scored by it |
| Frozen manifests | `tool_paired_v1` (150 ids), `release_v0_1` (220 ids, stratified across SMB-CFO's 24 task families + 10 injection samples) |
| Parity tests | **17 passed, ZERO skipped**, against the real upstream FinQA / TAT-QA / FinanceReasoning evaluators |
| Security tests | 411 passed |
| Sandbox gate | **PASSED** (`tool_security_rejection = 1.000` over 150 samples) |

### What is NOT measured

- **SECQUE analytical correctness: `NOT_EVALUATED`.** `llama3.2:3b` fails calibration with a **41%
  false-positive rate** against a 20% bar — it never rejects a good answer, and waves through
  two-thirds of answers that name the **wrong company** or contain an **invented figure**. `qwen3:8b`
  returns an empty string (a thinking model; it spends its budget inside `<think>`). `qwen2.5:7b` is
  refused: same family as the candidate. **This is a measurement, not an omission, and never a zero.**
- **No API provider is live-verified.** OpenAI, Anthropic, Gemini, OpenRouter are implemented and
  unit-tested against a mocked transport. **No API key exists here; none has ever made a call.**
- **No multimodal run exists.** `multimodal_coverage: 0.0` everywhere.

---

## Limitations

See [`docs/known_limitations.md`](../../docs/known_limitations.md). The load-bearing ones:

- **The 7B does not fit in the GPU** (4.7 GB of weights, 4 GB of VRAM) and spills to CPU. Every
  latency comparison here measures *this machine*, not the models.
- **The PDF text extraction strips spaces out of line items** — `Propertyandequipment,net`. The
  evidence is present and the model cannot find it. This depresses every FinanceBench number in this
  repo, and it is a *pipeline* limitation, not a model one.
- **`financebench_answer_accuracy` allows a 1% band**, which credits an answer wrong by $27M
  (`id_10285`: gold $12,645.00, model 12,672.0). I judge that too loose, and I have **not changed it** —
  tightening a tolerance after seeing which answers it credits is selecting a metric by its effect on
  the score, and that the effect would be to *lower* the score does not make it acceptable.

---

**A good score here does not certify that a model is safe to run unsupervised against real money.** It
means it did well on these questions, on this hardware, on this date. Neither of these models did.

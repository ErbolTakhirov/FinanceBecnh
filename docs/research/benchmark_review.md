# Benchmark research review

This document is the research artifact behind FinanceBecnh's dataset registry. Every row below
was verified live against the actual GitHub repo, HuggingFace dataset card, and/or paper — not
assumed from the paper abstract alone — because several of the "obvious" sources turned out to
be wrong, stale, or unofficial (see [Cross-cutting findings](#cross-cutting-findings)). Adapter
implementation status follows the platform's own discipline: `fully_supported` is never used
unless the adapter has been executed end-to-end in a test (enforced by a repo-hygiene test, see
`docs/reproducibility.md`).

Statuses: `fully_supported` · `supported_public_subset` · `user_supplied_required` · `partial` ·
`planned` · `unavailable`. Split-origin labels: `official` · `derived_local` · `generated_frozen`
· `public_subset` · `user_supplied`.

## Layer 1 — Core public benchmarks

| Benchmark | Paper | Repository | Task types | Size | Official splits | Modalities | Native metric(s) | Language | License | Public availability | Adapter status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **FinanceBench** | [arXiv:2311.11944](https://arxiv.org/abs/2311.11944) | [patronus-ai/financebench](https://github.com/patronus-ai/financebench) | Open-book QA over SEC 10-K/10-Q/8-K filings | 10,231 total; 150 public subset | Single eval set, no train/dev | Text + PDF | Human-graded Correct/Incorrect/Refusal bucketing (no automated metric) | EN | CC BY-NC-4.0 (150-ex subset, per HF card); full set unlicensed/gated | 150-example subset in-repo + HF; full 10,231 gated via direct email to Patronus AI | `supported_public_subset` (full set `user_supplied_required`) |
| **FinQA** | [2021.emnlp-main.300](https://aclanthology.org/2021.emnlp-main.300/) | [czyssrs/FinQA](https://github.com/czyssrs/FinQA) | Numerical reasoning over table+text, gold program | 8,281 (train 6,251 / dev 883 / test 1,147, gold public) + blind `private_test` | train/dev/test (public gold) + private_test (blind) | Text + tables | Execution accuracy (execute predicted program, round 5dp, compare); program accuracy (symbolic gold-equivalence via SymPy) | EN | MIT (code) + CC BY 4.0 (data, via FinTabNet/CDLA-Permissive provenance) | Fully in-repo JSON, all public-gold splits | `fully_supported` |
| **ConvFinQA** | [2022.emnlp-main.421](https://aclanthology.org/2022.emnlp-main.421/) | [czyssrs/ConvFinQA](https://github.com/czyssrs/ConvFinQA) | Multi-turn conversational decomposition of FinQA questions | 3,892 conversations / 14,115 turns | train (3,037 conv) / dev (421) gold public; **test gold never released** | Text + tables | Same as FinQA (execution + program accuracy) | EN | MIT (code); data license unstated (plausibly inherits FinQA's CC BY 4.0, unconfirmed) | train/dev in-repo (`data.zip`); test scoring is CodaLab-submission-only | `partial` (train/dev `fully_supported`-grade; test split `user_supplied_required`) |
| **TAT-QA** | [2021.acl-long.254](https://aclanthology.org/2021.acl-long.254/) | [NExTplusplus/tat-qa](https://github.com/NExTplusplus/tat-qa) | Hybrid table+text QA: span, arithmetic, count | 16,552 questions (train 13,215 / dev 1,668 / test 1,669) | train/dev/test, **test gold released Jan 2024** (previously held out) | Text + tables | Exact match (bag-of-normalized-spans); numeracy-aware F1 (Hungarian-alignment span matching + scale multiplication + sign-preserving) | EN | MIT (code) + CC BY 4.0 (data) | Fully in-repo + official HF mirror `next-tat/TAT-QA` | `fully_supported` |
| **FinanceReasoning** | [2025.acl-long.766](https://aclanthology.org/2025.acl-long.766/) | [BUPT-Reasoning-Lab/FinanceReasoning](https://github.com/BUPT-Reasoning-Lab/FinanceReasoning) (**not** the bare `BUPT-Reasoning` org — that repo is a dead stub) | Easy/medium/hard numerical reasoning, CoT vs. PoT | 2,238 (easy 1,000 / medium 1,000 / hard 238) | Fully public, single release | Text + tables | Numeric accuracy within 0.2% relative tolerance (execute PoT, or GPT-4o-mini-extract for CoT) | EN | CC BY 4.0 (data, per HF card); Apache-2.0 (code, per secondary sources) | Fully in-repo JSON + HF mirror | `fully_supported` |
| **SECQUE** | [2025.gem-1.16](https://aclanthology.org/2025.gem-1.16/) (arXiv:2504.04596) | Canonical source is **HF `nogabenyoash/SecQue`**, not `github.com/EnvCommons/SECQUE` (an unaffiliated third-party eval-environment wrapper created ~9 months after the paper) | Comparison analysis, ratio calculation, risk assessment, insight generation | 565 expert-written questions | Single eval split, no train/dev | Text + tables | SECQUE-Judge: multi-LLM-judge scoring (5x-invoked per pair, human-agreement-validated) | EN | MIT + an "eval-only, no training" clause | Fully on HuggingFace, ungated | `fully_supported` |
| **SMB-CFO** (custom) | — (this project) | — (this project) | Cash runway/gap, AR/AP, margins, variance, scenario analysis, refusal, RU/EN pairs, hallucination traps (30 task families — see mission spec) | TBD (Milestone 4) | `dev_small` / `public_eval` / `private_template` | Text + tables | Deterministic Python-oracle numeric/boolean grading | EN + RU (paired) | Synthetic, no personal data, Apache-2.0 | Fully generated, frozen manifests | `planned` (Milestone 4) |

## Layer 2 — Extended benchmarks

| Benchmark | Paper | Repository | Task types | Size | Modalities | Native metric(s) | Language | License | Public availability | Adapter status |
|---|---|---|---|---|---|---|---|---|---|---|
| **FinBen** | NeurIPS 2024 D&B ([abstract](https://proceedings.neurips.cc/paper_files/paper/2024/hash/adb1d9fa8be4576d28703b396b82ba1b-Abstract-Datasets_and_Benchmarks_Track.html)) | `The-FinAI/FinBen` is a thin wrapper repo; canonical code is **`The-FinAI/PIXIU`** | IE, textual analysis, QA, generation, risk management, forecasting, decision-making/trading (24 tasks / 8 categories) | 42+ separately-sourced datasets | Text (tables in some sub-tasks) | Per-task: F1/EM/ROUGE/BERTScore/Accuracy/MCC/Sharpe-ratio, depending on sub-task | EN + ES (some sub-tasks) | **Heterogeneous** — each of the 42+ sub-datasets (hosted as separate `TheFinAI/*` HF repos) carries its own license (CC BY-SA, CC BY-NC, MIT, public domain, ...) | No single bundle; per-sub-dataset HF pulls | `partial` — needs per-sub-dataset triage before any of the 42 can be marked supported |
| **XFinBench** | [2025.findings-acl.457](https://aclanthology.org/2025.findings-acl.457/) | [Zhihan72/XFinBench](https://github.com/Zhihan72/XFinBench) | Terminology, temporal reasoning, forecasting, scenario planning, numerical modelling (bool/MCQ/calc) | 4,235 (1,000 validation + 3,235 test) | Text + 77 images (minority) | Plain accuracy, overall + per-capability | EN | MIT (code + HF data tag) — but figures are screenshotted from 3 commercial textbooks; MIT covers the compilation, not necessarily the underlying publisher copyright | Dual-hosted (repo + HF), <10MB | **Test-set gold was silently made public Feb 2026** (README changelog) — contamination-tainted for any model trained after that date. Use the 1,000-question validation split as the clean slice. `partial` — small enough to bundle technically, but textbook-copyright provenance argues against vendoring; load at runtime instead |
| **FinMME** | ACL 2025 Main ([2025.acl-long.1426](https://aclanthology.org/2025.acl-long.1426/)) | [luo-junyu/FinMME](https://github.com/luo-junyu/FinMME) | Multimodal financial reasoning over charts/figures | 11,099 samples / 4,458 unique images, 18 domains × 6 asset classes | Images (JPG, 208–5,460px) + text | FinScore = domain-macro-averaged score × (1 − hallucination_rate over multi-select questions) | EN | MIT (HF data tag); **no LICENSE file for the code repo** | HF-only (`luojunyu/FinMME`, ~400MB with embedded images), ungated | `partial` — never vendor (~400MB of images); load via `load_dataset` at runtime. **No held-out split at all** (entire set is nominally "train") — a real contamination surface |
| **FinTextQA** | [2024.acl-long.328](https://aclanthology.org/2024.acl-long.328/) | [AlexJJJChen/FinTextQA](https://github.com/AlexJJJChen/FinTextQA) | Long-form financial QA with source attribution | 1,262 total (1,022 textbook-derived + 240 gov't/regulatory-derived) | Text (long documents) | Human ranking + automatic metrics + GPT-4 scoring, evaluated through a full RAG pipeline | EN | **81% (1,022 textbook-derived) permanently blocked** — HSBC legal declined to open-source; 19% (240, Fed/EC/HKMA-sourced) is in-repo and redistributable. The paper's claim of a public HF mirror is currently false (mirror exists but is empty) | Only the 240-question gov't-sourced slice is actually obtainable | `supported_public_subset` (19% only) |
| **SEC-QA** | [arXiv:2406.14394](https://arxiv.org/abs/2406.14394) | **None found** — confirmed absent after exhausting Kensho's GitHub org, HF org, and product pages | Multi-document QA generated from live SEC EDGAR filings, contamination-resistant by design | Not fixed (generative framework) | Text (multi-document) | Precision/Recall/F1@K (doc + page retrieval); QA correctness within 1% margin | EN | Unconfirmed/proprietary — Kensho/S&P Global monetize this as a gated commercial product (`benchmarks.kensho.com`) | **No public repo, dataset, or generator code exists anywhere** | `unavailable` — not attempted as a fake wrapper; would require full from-scratch reimplementation against live EDGAR filings |
| **BizFinBench** | [arXiv:2505.19457](https://arxiv.org/html/2505.19457v1) (v2: ICML 2026) | [HiThink-Research/BizFinBench](https://github.com/HiThink-Research/BizFinBench) | Anomalous-event attribution, numerical computation, time reasoning, stock prediction, financial NER, emotion recognition, tool-usage QA, knowledge QA | 100,000+ | Text | Task-specific (accuracy/F1/regression, per task) | EN + ZH | Apache-2.0 (code) / CC BY-NC-4.0 (data, research-only) | Full in-repo + HF (`HiThink-Research/BizFinBench`) | `planned` — new addition from this review; meaningfully extends business-analysis + scale coverage beyond the core Layer 1 set |
| **FinMTM** | [arXiv:2602.03130](https://arxiv.org/abs/2602.03130) (ACL 2026) | [HiThink-Research/FinMTM](https://github.com/HiThink-Research/FinMTM) | Bilingual multi-turn multimodal QA over financial charts + agent tasks | 11,133 QA pairs / 22 VLMs benchmarked | Images + multi-turn text | Task-specific (objective accuracy + dialogue/agent scoring) | EN + ZH | Apache-2.0 (code) / CC BY-NC-4.0 (data) | Full in-repo + HF | `planned` — picked over `mme_finance` (same lab; FinMTM is the newer, larger superset: bilingual + multi-turn + agent tasks) |
| **FinanceQA (AfterQuery)** | [arXiv:2501.18062](https://arxiv.org/abs/2501.18062) | [AfterQuery/FinanceQA](https://github.com/AfterQuery/FinanceQA) | Tactical (calculation/accounting-standard) + conceptual real-world analyst judgment tasks | Not large-scale; hedge-fund/PE/IB-analyst-workflow style | Text + filings | Accuracy (tactical/conceptual split) | EN | Unstated at a glance — verify HF dataset card (`AfterQuery/FinanceQA`) before bundling | Public HF dataset + paper | `planned` — distinct from FinQA (name collision only) despite the similar name; genuinely harder, real-world-judgment style |

## Explicitly skipped / watch-list

| Benchmark | Disposition | Why |
|---|---|---|
| **MME-Finance** ([HiThink-Research/MME-Finance](https://github.com/HiThink-Research/MME-Finance), ACM MM 2025) | **Skip** | Legitimate and mature (44 commits, own GH Pages site, 30+ models via VLMEvalKit), but its bilingual/multi-turn differentiators are fully subsumed by **FinMTM** — same lab, newer venue, ~2.3× larger, superset of features. Do not confuse with the already-included `luo-junyu/FinMME`, a completely separate benchmark despite the near-identical name. |
| **FinToolBench** ([arXiv:2603.08262](https://arxiv.org/abs/2603.08262)) | **Watch-list** | Real but immature: 7 commits, README admits this is a partial release (eval pipeline + "minimal data" only; full agent training/build scripts withheld). Genuinely fills a gap — none of the Layer 1/2 benchmarks test actual tool *execution* — but too young to commit an adapter to yet. Two adjacent, possibly-faster-maturing projects surfaced during research and are worth re-checking later: "FinMCP-Bench" and "FinTrace". |

## Cross-cutting findings

**The "contamination of trust" pattern.** For three of the benchmarks investigated (SECQUE,
SEC-QA, FinTextQA), naively trusting the paper's stated repository or "publicly available" claim
would have produced the *wrong* licensing/availability conclusion:

- SECQUE's associated GitHub URL is a live, functioning repo — but it's an unaffiliated
  third-party wrapper created roughly nine months after the paper published, not the authors'
  own artifact (the real source is a HuggingFace dataset the paper doesn't prominently link).
- SEC-QA has no discoverable repo or dataset at all, despite being a real, peer-reviewed paper —
  confirmed absent, not merely unlinked, after exhausting the authors' GitHub org, HF org, and
  product pages.
- FinTextQA's paper states the dataset is "publicly available on HuggingFace"; the linked HF
  mirror is a live URL that resolves to a completely empty dataset repo, and the README's own
  opening lines reveal 81% of the data is permanently blocked by the data owner's legal
  department.

Every dataset in this review was checked against its **live** current state (GitHub API
metadata, HF dataset-card license fields, actual file trees) rather than the paper's
self-description, specifically because of this pattern.

**Canonical-repo ambiguity.** Two benchmarks (FinanceReasoning, FinBen) have a "bare" org repo
that looks canonical but is actually a dead stub or thin wrapper, with the real, maintained
artifact living under a differently-named org/repo (`BUPT-Reasoning-Lab` vs. `BUPT-Reasoning`;
`The-FinAI/PIXIU` vs. `The-FinAI/FinBen`). Always verify last-push dates and star/fork counts
before treating a GitHub URL as authoritative.

**No public benchmark tests Russian financial language.** Every "bilingual" claim surfaced in
this research (FinBen's EN/ES trading tasks, BizFinBench's and FinMTM's EN/ZH coverage) is a
different language pair than EN/RU. FinanceBecnh's entire Russian-language coverage comes from
the custom SMB-CFO paired EN/RU cases (Milestone 4) — there is no external benchmark to
cross-check against, which is itself a limitation worth stating plainly in every report that
includes a `bilingual_en_ru` score.

**Contamination status can change after publication.** XFinBench's test-set gold answers were
explicitly held out at publication time specifically to prevent contamination, then quietly
published in full in a February 2026 README update — a benchmark's contamination-safety is a
point-in-time property, not a permanent one, and adapters need a mechanism (a frozen manifest
hash, checked at `prepare` time) to detect exactly this kind of drift rather than silently
trusting "the paper said the test set is blind."

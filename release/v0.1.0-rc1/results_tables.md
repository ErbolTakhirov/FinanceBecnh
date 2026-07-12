# FinanceBench v0.1.0-rc1 — generated result tables

Generated from the run artifacts. The narrative report, with the findings, is [`report.md`](report.md).

Evaluator fingerprint `80ca8a678b1c4fa1`. Every run below was scored by **this** evaluator; runs scored by a different one are not on this page, because they are not comparable and averaging them would be a lie.

Hardware: NVIDIA GeForce GTX 1650, 4096 MiB — Linux-6.19.14+kali-amd64-x86_64-with-glibc2.42.

> **A dash means NOT MEASURED. It never means zero.** An `INSUFFICIENT_COVERAGE` index is a refusal, not a missing number: the run did not ask enough to support the claim the index makes, and the reason is printed next to it.

## Verdict

| model | run | FCI | verdict |
|---|---|---|---|
| `ollama/qwen2.5:3b` | `convfinqa-structured_financial_v1-context_gi` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:3b` | `convfinqa-structured_financial_v1-context_gi` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:3b` | `core_real-structured_financial_v1-context_gi` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | INSUFFICIENT_COVERAGE |
| `ollama/qwen2.5:3b` | `finance_reasoning-structured_financial_v1-co` | **INSUFFICIENT_COVERAGE** — only 2 capability dimension(s) had coverage (minimum 3); an index built from one dimension is not an index | NOT_FINANCE_READY |
| `ollama/qwen2.5:3b` | `financebench-structured_financial_v1-context` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:3b` | `financebench-structured_financial_v1-retriev` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:3b` | `financebench-structured_financial_v1-retriev` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:3b` | `finqa-program_v1-context_given-ollama-qwen2.` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | INSUFFICIENT_COVERAGE |
| `ollama/qwen2.5:3b` | `finqa-structured_financial_v1-context_given-` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financial_v1-context` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:3b` | `secque-structured_financial_v1-context_given` | **INSUFFICIENT_COVERAGE** — only 2 capability dimension(s) had coverage (minimum 3); an index built from one dimension is not an index | NOT_FINANCE_READY |
| `ollama/qwen2.5:3b` | `smb_cfo-structured_financial_v1-context_give` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-context_given-` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-tool_assisted-` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | INSUFFICIENT_COVERAGE |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_financial_v1-conte` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_financial_v1-tool_` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:7b` | `finance_reasoning-structured_financial_v1-co` | **INSUFFICIENT_COVERAGE** — only 2 capability dimension(s) had coverage (minimum 3); an index built from one dimension is not an index | NOT_FINANCE_READY |
| `ollama/qwen2.5:7b` | `finqa-structured_financial_v1-context_given-` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financial_v1-context` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:7b` | `secque-structured_financial_v1-context_given` | **INSUFFICIENT_COVERAGE** — only 2 capability dimension(s) had coverage (minimum 3); an index built from one dimension is not an index | NOT_FINANCE_READY |
| `ollama/qwen2.5:7b` | `tatqa-structured_financial_v1-context_given-` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_financial_v1-conte` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_financial_v1-tool_` | **INSUFFICIENT_COVERAGE** — a critical gate failed — a single index would let a strong average hide the kind of error that is not a near-miss in finance | NOT_FINANCE_READY |

## What was measured

| model | run | metric | value |
|---|---|---|---|
| `ollama/qwen2.5:3b` | `convfinqa-structured_financial` | convfinqa_turn_accuracy | 0.283 (n=120) |
| `ollama/qwen2.5:3b` | `convfinqa-structured_financial` | exact_match | 0.025 (n=120) |
| `ollama/qwen2.5:3b` | `convfinqa-structured_financial` | convfinqa_turn_accuracy | 0.308 (n=120) |
| `ollama/qwen2.5:3b` | `convfinqa-structured_financial` | exact_match | 0.050 (n=120) |
| `ollama/qwen2.5:3b` | `core_real-structured_financial` | exact_match | 0.222 (n=9) |
| `ollama/qwen2.5:3b` | `core_real-structured_financial` | finqa_answer_accuracy | 0.333 (n=9) |
| `ollama/qwen2.5:3b` | `finance_reasoning-structured_f` | exact_match | 0.000 (n=40) |
| `ollama/qwen2.5:3b` | `finance_reasoning-structured_f` | finance_reasoning_accuracy | 0.000 (n=40) |
| `ollama/qwen2.5:3b` | `financebench-structured_financ` | exact_match | 0.020 (n=150) |
| `ollama/qwen2.5:3b` | `financebench-structured_financ` | financebench_answer_accuracy | 0.236 (n=89, 61 n/a) |
| `ollama/qwen2.5:3b` | `financebench-structured_financ` | financebench_citation_accuracy | 0.000 (n=1, 149 n/a) |
| `ollama/qwen2.5:3b` | `financebench-structured_financ` | financebench_unsupported_numeric_claim | 0.707 (n=150) |
| `ollama/qwen2.5:3b` | `financebench-structured_financ` | exact_match | 0.000 (n=150) |
| `ollama/qwen2.5:3b` | `financebench-structured_financ` | financebench_answer_accuracy | 0.022 (n=89, 61 n/a) |
| `ollama/qwen2.5:3b` | `financebench-structured_financ` | financebench_citation_accuracy | — |
| `ollama/qwen2.5:3b` | `financebench-structured_financ` | financebench_unsupported_numeric_claim | 0.687 (n=150) |
| `ollama/qwen2.5:3b` | `financebench-structured_financ` | exact_match | 0.007 (n=150) |
| `ollama/qwen2.5:3b` | `financebench-structured_financ` | financebench_answer_accuracy | 0.022 (n=89, 61 n/a) |
| `ollama/qwen2.5:3b` | `financebench-structured_financ` | financebench_citation_accuracy | — |
| `ollama/qwen2.5:3b` | `financebench-structured_financ` | financebench_unsupported_numeric_claim | 0.673 (n=150) |
| `ollama/qwen2.5:3b` | `finqa-program_v1-context_given` | exact_match | 0.000 (n=12) |
| `ollama/qwen2.5:3b` | `finqa-program_v1-context_given` | finqa_execution_accuracy | 0.000 (n=12) |
| `ollama/qwen2.5:3b` | `finqa-program_v1-context_given` | finqa_program_accuracy | 0.000 (n=12) |
| `ollama/qwen2.5:3b` | `finqa-structured_financial_v1-` | exact_match | 0.125 (n=40) |
| `ollama/qwen2.5:3b` | `finqa-structured_financial_v1-` | finqa_answer_accuracy | 0.150 (n=40) |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financ` | convfinqa_turn_accuracy | 0.300 (n=20) |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financ` | exact_match | 0.077 (n=220) |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financ` | finance_reasoning_accuracy | 0.000 (n=40) |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financ` | financebench_answer_accuracy | 0.231 (n=26, 14 n/a) |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financ` | financebench_citation_accuracy | 0.000 (n=1, 39 n/a) |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financ` | financebench_unsupported_numeric_claim | 0.625 (n=40) |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financ` | finqa_answer_accuracy | 0.150 (n=40) |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financ` | smb_cfo_accuracy | 0.000 (n=37, 3 n/a) |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financ` | smb_cfo_injection_resistance | 1.000 (n=2, 38 n/a) |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financ` | smb_cfo_refusal_correctness | 0.950 (n=40) |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financ` | tatqa_exact_match | 0.200 (n=40) |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financ` | tatqa_f1 | 0.311 (n=40) |
| `ollama/qwen2.5:3b` | `release_v0_1-structured_financ` | tatqa_scale_accuracy | 0.725 (n=40) |
| `ollama/qwen2.5:3b` | `secque-structured_financial_v1` | exact_match | 0.000 (n=80) |
| `ollama/qwen2.5:3b` | `secque-structured_financial_v1` | secque_comparison_direction | 1.000 (n=19, 61 n/a) |
| `ollama/qwen2.5:3b` | `secque-structured_financial_v1` | secque_filing_identification | 0.607 (n=56, 24 n/a) |
| `ollama/qwen2.5:3b` | `secque-structured_financial_v1` | secque_numeric_agreement | 0.080 (n=62, 18 n/a) |
| `ollama/qwen2.5:3b` | `secque-structured_financial_v1` | secque_unsupported_numeric_claim | 0.938 (n=80) |
| `ollama/qwen2.5:3b` | `smb_cfo-structured_financial_v` | exact_match | 0.000 (n=30) |
| `ollama/qwen2.5:3b` | `smb_cfo-structured_financial_v` | smb_cfo_accuracy | 0.000 (n=20, 10 n/a) |
| `ollama/qwen2.5:3b` | `smb_cfo-structured_financial_v` | smb_cfo_injection_resistance | 1.000 (n=10, 20 n/a) |
| `ollama/qwen2.5:3b` | `smb_cfo-structured_financial_v` | smb_cfo_refusal_correctness | 1.000 (n=30) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | exact_match | 0.150 (n=40) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tatqa_exact_match | 0.125 (n=40) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tatqa_f1 | 0.232 (n=40) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tatqa_scale_accuracy | 0.675 (n=40) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | exact_match | 0.500 (n=6) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tatqa_exact_match | 0.000 (n=6) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tatqa_f1 | 0.117 (n=6) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tatqa_scale_accuracy | 0.167 (n=6) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tool_argument_validity | 1.000 (n=1, 5 n/a) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tool_error_recovery | 0.000 (n=1, 5 n/a) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tool_execution_success | 0.000 (n=1, 5 n/a) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tool_hallucination_rate | 1.000 (n=1, 5 n/a) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tool_invocation_rate | 0.167 (n=6) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tool_result_utilization | — |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tool_security_rejection | 1.000 (n=6) |
| `ollama/qwen2.5:3b` | `tatqa-structured_financial_v1-` | tool_selection_accuracy | 0.167 (n=6) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | exact_match | 0.140 (n=150) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | finqa_answer_accuracy | 0.147 (n=75) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tatqa_exact_match | 0.173 (n=75) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tatqa_f1 | 0.268 (n=75) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tatqa_scale_accuracy | 0.720 (n=75) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | exact_match | 0.060 (n=150) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | finqa_answer_accuracy | 0.027 (n=75) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tatqa_exact_match | 0.067 (n=75) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tatqa_f1 | 0.150 (n=75) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tatqa_scale_accuracy | 0.667 (n=75) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tool_argument_validity | 0.500 (n=2, 148 n/a) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tool_error_recovery | 0.000 (n=1, 149 n/a) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tool_execution_success | 0.500 (n=2, 148 n/a) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tool_hallucination_rate | 1.000 (n=2, 148 n/a) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tool_invocation_rate | 0.013 (n=150) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tool_result_utilization | 1.000 (n=1, 149 n/a) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tool_security_rejection | 1.000 (n=150) |
| `ollama/qwen2.5:3b` | `tool_paired_v1-structured_fina` | tool_selection_accuracy | 0.013 (n=150) |
| `ollama/qwen2.5:7b` | `finance_reasoning-structured_f` | exact_match | 0.000 (n=40) |
| `ollama/qwen2.5:7b` | `finance_reasoning-structured_f` | finance_reasoning_accuracy | 0.025 (n=40) |
| `ollama/qwen2.5:7b` | `finqa-structured_financial_v1-` | exact_match | 0.175 (n=40) |
| `ollama/qwen2.5:7b` | `finqa-structured_financial_v1-` | finqa_answer_accuracy | 0.350 (n=40) |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financ` | convfinqa_turn_accuracy | 0.350 (n=20) |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financ` | exact_match | 0.086 (n=220) |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financ` | finance_reasoning_accuracy | 0.025 (n=40) |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financ` | financebench_answer_accuracy | 0.423 (n=26, 14 n/a) |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financ` | financebench_citation_accuracy | 0.000 (n=39, 1 n/a) |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financ` | financebench_unsupported_numeric_claim | 0.725 (n=40) |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financ` | finqa_answer_accuracy | 0.350 (n=40) |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financ` | smb_cfo_accuracy | 0.000 (n=37, 3 n/a) |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financ` | smb_cfo_injection_resistance | 1.000 (n=2, 38 n/a) |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financ` | smb_cfo_refusal_correctness | 0.950 (n=40) |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financ` | tatqa_exact_match | 0.225 (n=40) |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financ` | tatqa_f1 | 0.324 (n=40) |
| `ollama/qwen2.5:7b` | `release_v0_1-structured_financ` | tatqa_scale_accuracy | 0.700 (n=40) |
| `ollama/qwen2.5:7b` | `secque-structured_financial_v1` | exact_match | 0.000 (n=80) |
| `ollama/qwen2.5:7b` | `secque-structured_financial_v1` | secque_comparison_direction | 1.000 (n=12, 68 n/a) |
| `ollama/qwen2.5:7b` | `secque-structured_financial_v1` | secque_filing_identification | 0.452 (n=62, 18 n/a) |
| `ollama/qwen2.5:7b` | `secque-structured_financial_v1` | secque_numeric_agreement | 0.115 (n=62, 18 n/a) |
| `ollama/qwen2.5:7b` | `secque-structured_financial_v1` | secque_unsupported_numeric_claim | 0.900 (n=80) |
| `ollama/qwen2.5:7b` | `tatqa-structured_financial_v1-` | exact_match | 0.125 (n=40) |
| `ollama/qwen2.5:7b` | `tatqa-structured_financial_v1-` | tatqa_exact_match | 0.275 (n=40) |
| `ollama/qwen2.5:7b` | `tatqa-structured_financial_v1-` | tatqa_f1 | 0.371 (n=40) |
| `ollama/qwen2.5:7b` | `tatqa-structured_financial_v1-` | tatqa_scale_accuracy | 0.725 (n=40) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | exact_match | 0.167 (n=150) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | finqa_answer_accuracy | 0.267 (n=75) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tatqa_exact_match | 0.267 (n=75) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tatqa_f1 | 0.351 (n=75) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tatqa_scale_accuracy | 0.720 (n=75) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | exact_match | 0.200 (n=150) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | finqa_answer_accuracy | 0.240 (n=75) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tatqa_exact_match | 0.267 (n=75) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tatqa_f1 | 0.368 (n=75) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tatqa_scale_accuracy | 0.760 (n=75) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tool_argument_validity | 0.931 (n=29, 121 n/a) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tool_error_recovery | 0.188 (n=16, 134 n/a) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tool_execution_success | 0.552 (n=29, 121 n/a) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tool_hallucination_rate | 1.000 (n=29, 121 n/a) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tool_invocation_rate | 0.193 (n=150) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tool_result_utilization | 0.688 (n=16, 134 n/a) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tool_security_rejection | 1.000 (n=150) |
| `ollama/qwen2.5:7b` | `tool_paired_v1-structured_fina` | tool_selection_accuracy | 0.193 (n=150) |

## What was NOT measured

- **SECQUE analytical correctness: `NOT_EVALUATED`.** No available judge passes calibration. `llama3.2:3b` scores 75% accuracy with a **41% false-positive rate** against a 20% bar — it never rejects a good answer, and waves through two-thirds of answers that name the wrong company or contain a fabricated figure. This is a measurement, not an omission, and it is **never** reported as zero.
- **No API provider is live-verified.** OpenAI, Anthropic, Gemini and OpenRouter are implemented and unit-tested against a mocked transport. No API key exists in this environment, so **none of them has ever made a successful call**.
- **No multimodal run exists.** `multimodal_coverage: 0.0` in every run.

## Limitations

See [`docs/known_limitations.md`](../../docs/known_limitations.md).

---

**A good score here does not certify that a model is safe to run unsupervised against real money.** It means it did well on these questions, on this hardware, on this date.


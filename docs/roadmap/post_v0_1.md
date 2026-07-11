# Post-v0.1 roadmap — researched, not implemented

Recorded so it does not distract from finishing the release. Nothing here is built.

## Worth doing

- **A professional difficulty hierarchy.** The current benchmarks are flat: a FinQA lookup and a
  multi-step ratio derivation score the same. CFA-level stratification would let a report say *which
  tier* a model is safe at, which is what a reader actually wants.
- **FINESSE-Bench** — evaluates financial sentiment/entity extraction. Complements what is here
  (arithmetic, grounding, conversation) rather than duplicating it.
- **Russian finance coverage.** SMB-CFO is bilingual, but every *public-company* benchmark here is
  English. An EN/RU gap measured only on synthetic ledgers is a partial answer.

## Deliberately deferred

- **External market-data tools** (RapidAPI, live prices, filings APIs). A benchmark whose scores
  depend on what a third-party endpoint returned on a Tuesday is not a benchmark; it is a snapshot of
  a Tuesday. If added, they stay `external_non_reproducible` and out of the default score.
- **FinMCP-Bench compatibility.** Interesting, and it inherits the same reproducibility problem.
- **Multimodal finance** (charts, scanned filings). Real, and a different project.

## The honest priority

Before any of the above: **a judge that passes calibration.** SECQUE's analytical dimension is the
one capability this suite measures and then refuses to score, and it will stay refused until an
instrument exists that can be trusted with it. That is worth more than a sixth benchmark.

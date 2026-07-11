---
name: Invalid score
about: A number this suite reported looks wrong
title: "[invalid score] "
labels: invalid-score
---

**This is the most important issue type in the repository.** A benchmark that reports a wrong number
confidently is worse than no benchmark.

**The number**
Which metric, which run id, which model.

**Why you think it is wrong**
What you expected, and what makes you expect it.

**The evaluator fingerprint**
From `runs/<run_id>/environment.json`. Two runs with different fingerprints are not comparable, and
that is often the answer.

**Artifacts**
`metric_details.jsonl` for the affected samples, if you can share them.

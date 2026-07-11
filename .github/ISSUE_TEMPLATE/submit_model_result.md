---
name: Submit a model result
about: Add a model to the leaderboard
title: "[result] "
labels: result
---

**Model** (exact digest / quantization / runtime)

**The frozen manifest you ran**
Sample ids must match, or the comparison is not one.

**Evaluator fingerprint**
From `environment.json`. If it differs from the leaderboard's, the run must be re-scored, not
compared.

**Artifacts**
The full `runs/<run_id>/` directory. Mock runs are never eligible.

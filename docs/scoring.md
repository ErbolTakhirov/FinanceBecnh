# Scoring

See [`docs/research/scoring_design.md`](research/scoring_design.md) for the full rationale (why
a single accuracy average is misleading) and formulas (the geometric-mean FCI, reliability
penalty, critical gates). This page is the short version:

- Native metrics are preserved (see [`docs/metrics.md`](metrics.md)).
- Every sample maps (via `capability_tags`) to one or more of seven capability dimensions
  (`financebench.evaluation.capability_map.CapabilityDimension`), weighted 25/20/15/15/10/10/5
  (numerical reasoning / document grounding & retrieval / table-text reasoning / financial
  analysis & insight / conversational consistency / calibration-refusal-reliability /
  bilingual EN-RU).
- The Finance Capability Index is a weighted **geometric** mean across dimensions (so no single
  strength can hide a critical weakness), scaled by a reliability penalty for unsupported
  claims, catastrophic numeric errors, and invalid output.
- Critical gates can block a "Strong"/"Exceptional" label outright regardless of the numeric FCI.
- Coverage is always reported next to the score — two runs with different coverage are never
  presented as directly comparable.

**Status:** Milestone 1 ships the capability dimensions/weights (`evaluation/capability_map.py`)
and the `MetricAggregate` shape every score is built from. `gates.json` and
`confidence_intervals.json` are valid, schema-correct, honestly-empty placeholders
(`evaluated: false`) — the FCI formula, gate evaluation, and bootstrap confidence intervals are
Milestone 6 work.

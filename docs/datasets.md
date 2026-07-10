# Datasets

Every benchmark this platform wraps is described by a `DatasetManifest`
(`financebench.schemas.manifest`) with an explicit, honest support `status`:

- `fully_supported` — the full official dataset (or all publicly-released splits) is bundled or
  fetchable, redistributable, and covered by an end-to-end test.
- `supported_public_subset` — only a subset (often the only publicly redistributable slice) is
  available; the full dataset is gated or separately licensed.
- `user_supplied_required` — adapter code exists, but you must obtain the data yourself (a
  license request, a paid product, a leaderboard-only held-out test split, ...).
- `partial` — adapter code exists with real caveats (e.g. don't vendor a large or
  uncertain-provenance asset into this repo; load it at runtime instead).
- `planned` — not yet implemented.
- `unavailable` — confirmed not to exist publicly anywhere; not wrapped at all.

`status_tested_at` is required for `fully_supported`/`supported_public_subset` — see
`tests/test_manifest_hygiene.py`, which fails the build if a claimed-supported benchmark has no
matching `tests/datasets/test_<name>_e2e.py`.

See [`docs/research/benchmark_review.md`](research/benchmark_review.md) for the full research
behind every benchmark's status, and [`docs/licenses.md`](licenses.md) for the license and
redistribution summary. Run `financebench list-benchmarks` / `financebench benchmark-info
<name>` / `financebench licenses` for the live registry view.

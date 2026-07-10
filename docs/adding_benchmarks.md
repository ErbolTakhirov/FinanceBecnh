# Adding a benchmark

1. Add a `DatasetManifest` describing the benchmark honestly (license, official source, splits,
   and — critically — an accurate `status`; see [`docs/datasets.md`](datasets.md)).
2. Implement a `DatasetAdapter` subclass (`financebench/datasets/<name>/adapter.py`):
   `load(split)` returns `CanonicalSample` records (`financebench.schemas.sample`); `manifest()`
   returns the `DatasetManifest`.
3. Register it: `@register_dataset("<name>")` on the class (see
   `financebench/datasets/smoke/adapter.py` for the simplest complete example).
4. Import the new module from `financebench/datasets/__init__.py` so it registers on package
   import (mirroring how `smoke` is wired in).
5. If the manifest claims `fully_supported` or `supported_public_subset`, add
   `tests/datasets/test_<name>_e2e.py` that actually loads real data and runs it through the
   engine — `tests/test_manifest_hygiene.py` fails the build otherwise.
6. Add native metrics under `evaluation/native/<name>.py` if the benchmark has an official
   evaluation method worth preserving (see [`docs/metrics.md`](metrics.md)).
7. Map the benchmark's `capability_tags` to the seven capability dimensions
   (`evaluation/capability_map.py`).

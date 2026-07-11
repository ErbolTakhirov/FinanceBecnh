## What this changes

## Did it move a score?

If yes: **which metric version did you bump, and why?** A metric that moves a score without changing
the evaluator fingerprint makes old and new runs falsely comparable.

If a score moved in the *flattering* direction, say so explicitly and justify it. A metric rule is
never changed to improve a model's number.

## Verification

- [ ] `ruff format --check . && ruff check . && mypy src/financebench && pytest`
- [ ] `bash scripts/setup_references.sh && pytest tests/parity -ra` — **zero skips**
- [ ] `pytest tests/security -ra`
- [ ] If it touches an adapter, a metric, or the sandbox: it was run against **real data**, not only
      fixtures.

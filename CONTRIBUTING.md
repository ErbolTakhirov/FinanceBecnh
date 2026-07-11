# Contributing

The bar here is unusual, and it is worth stating plainly before you spend an evening on a PR.

## The one rule

**A metric rule is never changed to improve a model's score.**

Every metric fix this project has made moved a number in the *unflattering* direction, or made it
more honest. If your change makes a model look better, that is not disqualifying — but you must say
so in the PR, and justify it as a correction rather than a preference.

## "The tests pass" is not the standard

Every serious bug this project has found was **caught by disbelieving a result**, not by a test going
red:

- `document_scoped` never scoped the document. Every run completed. Every artifact validated. The
  page-recall number was simply for a different experiment than the one it claimed.
- The hallucination detector excused an invented `987,654,321` because a filing contained `983`.
  Nothing crashed.
- A correct refusal about "December 2027" was recorded as a hallucination, because `2027.` — with the
  sentence's full stop — missed a year regex.

All three produced **plausible numbers**. That is the failure mode this suite exists to catch, and it
is why an adapter or a metric change is not done until it has been run against **real data**.

## Things that will get a PR rejected

- A benchmark adapter whose gold can reach the prompt. (`tests/security/` will catch it, but please
  catch it first.)
- A metric that returns `0.0` where it means "not applicable". `None` is not zero. A zero says the
  model failed; `None` says we could not measure it, and conflating them has understated a real model
  by 68 % in this repository's own history.
- A judge, a score, or a verdict that is published without the evidence that it can be trusted.
- A skipped test presented as a passing one.

## Verification

```bash
ruff format --check . && ruff check . && mypy src/financebench && pytest
bash scripts/setup_references.sh && pytest tests/parity -ra   # 17 passed, ZERO skipped
pytest tests/security -ra
```

A skipped parity test proves nothing. If you see one, the setup did not take.

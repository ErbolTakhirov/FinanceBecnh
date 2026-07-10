# Model providers

**Status: Milestone 1.** Only the deterministic `mock` provider is implemented today
(`financebench.models.mock`) — it needs no API key, makes no network calls, and exists so the
whole pipeline (CLI, engine, cache, metrics, artifacts) can be tested end to end offline.

Real providers (OpenAI, Anthropic, Gemini, OpenRouter, and an arbitrary OpenAI-compatible
endpoint) land in Milestone 5, under the same `ModelProvider` ABC + registry seen in
`financebench/models/base.py` — see [`docs/adding_models.md`](adding_models.md) for what
implementing one involves. Run `financebench list-model-providers` or `financebench doctor` for
the live registry view (this never prints key *values*, only whether one is configured).

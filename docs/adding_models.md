# Adding a model provider

1. Subclass `ModelProvider` (`financebench/models/base.py`): implement `generate(request) ->
   ModelResponse` and `from_env(env)`. Raise a `ProviderError` subclass
   (`financebench.utils.errors`) — with `retryable` set correctly — for any transport-level
   failure, so the engine's retry/backoff logic can do the right thing without knowing anything
   provider-specific.
2. Override `capabilities(model)` to return a `ProviderCapabilities` — text/vision/tool-calling/
   JSON-mode/max-context/streaming/usage-reporting — from a known-model table where you have
   one; the default is a conservative text-only guess.
3. Register it: `@register_provider("<name>")` on the class (see `financebench/models/mock.py`
   for the simplest complete example — start there before looking at a real HTTP-based provider
   once one exists).
4. Resolve credentials **only** from environment variables (add the variable name to
   `.env.example`, keyless) — never accept a key via a CLI argument or a config file value.
5. Import the new module from `financebench/models/__init__.py` so it registers on package
   import.
6. Add a test using a mocked transport (no real network calls) proving `generate()` works and
   that a failure raises the right `ProviderError` subclass with the right `retryable` value.

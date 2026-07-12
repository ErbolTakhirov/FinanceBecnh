# Model providers

## What is live-verified, and what merely compiles

This distinction is the whole content of this page.

| provider | status | what that means |
|---|---|---|
| `ollama` | **live-verified** | Every real number in `runs/` came from it. |
| `openai` | implemented, **not live-verified** | Complete, unit-tested against a mocked transport. **No API key exists in this environment, so it has never made a successful call.** |
| `anthropic` | implemented, **not live-verified** | As above. |
| `gemini` | implemented, **not live-verified** | As above. |
| `openrouter` | implemented, **not live-verified** | As above. |
| `openai_compatible` | implemented, **unreachable** | For vLLM / llama.cpp / LM Studio. No local server was running when it was last probed. |
| `mock` | n/a | A simulator **holding the answer key**. Requires `--allow-mock`, is stamped `run_type=mock_test`, and is barred from the leaderboard. Its scores measure the pipeline, never a model. |

`financebench verify-providers` labels each provider **by calling it** and recording what happened —
not by reading a class attribute. A provider is not "working" because somebody wrote a class for it.

```bash
financebench verify-providers --output reports/provider_verification.json
```

## Configuring one

```yaml
# configs/models/ollama-qwen2.5-3b.yaml
provider: ollama
model: qwen2.5:3b
generation:
  temperature: 0          # determinism is the default, everywhere
  max_output_tokens: 512
  timeout_seconds: 300
runtime:
  concurrency: 2
  retries: 3
  cache: true
```

API keys are read from the environment (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, …) and are **never**
written to a run artifact. `financebench doctor` reports `key_present: true|false`, never a value.

## A note on runtime settings

`concurrency` and `timeout_seconds` are **not** part of the run id, the cache key, or the evaluator
fingerprint — so none of the machinery that guards comparability will catch a change to them. They
still move the results: the first SECQUE 3B run used a 180 s timeout at concurrency 4 and recorded
three `ProviderTimeoutError`s, while the 7B ran at 300 s / concurrency 2 and recorded none. Those three
timeouts were then scored as the 3B getting three financial questions wrong.

**Match them across models you intend to compare.** The shipped `ollama-qwen2.5-3b.yaml` and
`ollama-qwen2.5-7b.yaml` do.

See [`docs/adding_models.md`](adding_models.md) for what implementing a new provider involves.

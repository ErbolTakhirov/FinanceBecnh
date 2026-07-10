# Local models

**Status: Milestone 5 (not yet implemented).** This page will document exact setup for Ollama,
vLLM, llama.cpp (`llama-server`, including GGUF/CPU-only usage), and direct Hugging Face
Transformers inference, each registered under the same `ModelProvider` seam as the cloud
providers (see [`docs/providers.md`](providers.md)). Base install and tests will continue to
require neither a GPU nor any of these optional backends — see the `local-transformers` and
`vllm` extras in `pyproject.toml`.

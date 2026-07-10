"""End-to-end orchestration: resolve a benchmark/group + model config into samples, run them
through the engine, score them, and write the full run-artifact set.

This is the one function both the ``eval`` and ``resume`` CLI commands call — ``resume`` is not
a separate code path, it is the same idempotent operation pointed at the same run id (see
``execution/cache.py`` for why a cache hit *is* resume).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from financebench import __version__
from financebench.config.model_config import ModelConfigFile
from financebench.datasets.base import create_dataset
from financebench.evaluation.capability_map import rollup_capabilities
from financebench.evaluation.metrics.exact_match import ExactMatchMetric
from financebench.execution.cache import ResponseCache
from financebench.execution.engine import RunEngine, RunResult
from financebench.models.base import get_provider_class
from financebench.schemas.manifest import DatasetManifest
from financebench.schemas.sample import CanonicalSample
from financebench.storage.artifacts import ArtifactInputs, write_run_artifacts
from financebench.utils.errors import ConfigError
from financebench.utils.ids import make_run_id
from financebench.utils.timing import RealClock

__all__ = ["EvalOutcome", "EvalRequest", "resolve_samples", "run_eval"]


@dataclass(frozen=True)
class EvalRequest:
    """Everything needed to run one evaluation end to end."""

    label: str
    """The ``--benchmark`` name or ``--group`` name — used for the run id and reports."""
    benchmark_splits: tuple[tuple[str, str], ...]
    """``(dataset_name, split)`` pairs to evaluate, in order."""
    model_config_file: ModelConfigFile
    cache_dir: Path
    seed: int = 42
    max_samples: int | None = None
    max_cost_usd: float | None = None
    offline: bool = False


@dataclass(frozen=True)
class EvalOutcome:
    run_id: str
    out_dir: Path
    run_result: RunResult


def resolve_samples(
    benchmark_splits: Sequence[tuple[str, str]],
) -> tuple[tuple[CanonicalSample, ...], tuple[DatasetManifest, ...]]:
    """Load every requested (dataset, split) pair's samples and manifests, in order."""
    samples: list[CanonicalSample] = []
    manifests: list[DatasetManifest] = []
    for name, split in benchmark_splits:
        adapter = create_dataset(name)
        manifests.append(adapter.manifest())
        samples.extend(adapter.load(split))
    return tuple(samples), tuple(manifests)


async def run_eval(request: EvalRequest, *, out_dir: Path) -> EvalOutcome:
    model = request.model_config_file.to_model_spec()

    if request.offline:
        provider_cls = get_provider_class(model.provider)
        if getattr(provider_cls, "REQUIRES_KEY", False):
            raise ConfigError(
                f"--offline was set but provider {model.provider!r} requires network access"
            )

    samples, dataset_manifests = resolve_samples(request.benchmark_splits)
    if not samples:
        raise ConfigError(
            f"no samples resolved for {request.label!r} "
            f"(benchmarks/splits: {request.benchmark_splits})"
        )

    config = request.model_config_file.to_run_config(
        seed=request.seed, limit=request.max_samples, max_cost_usd=request.max_cost_usd
    )
    run_id = make_run_id(request.label, model.ref, request.seed)
    cache = ResponseCache(request.cache_dir, mode=config.cache_mode)

    provider_cls = get_provider_class(model.provider)
    provider = provider_cls.from_env()
    try:
        provider_capabilities = provider.capabilities(model.model)
        run_result = await RunEngine().run(
            samples=samples,
            model=model,
            config=config,
            cache=cache,
            provider=provider,
            max_cost_usd=request.max_cost_usd,
        )
    finally:
        await provider.aclose()

    metric = ExactMatchMetric()
    metric_results = tuple(
        metric.score(sample, prediction)
        for sample, prediction in zip(samples, run_result.predictions, strict=True)
    )
    capability_aggregates = rollup_capabilities(samples, metric_results)

    clock = RealClock()
    inputs = ArtifactInputs(
        run_id=run_id,
        benchmark_or_group=request.label,
        model=model,
        provider_capabilities=provider_capabilities,
        config=config,
        created_at=clock.now_iso(),
        financebench_version=__version__,
        dataset_manifests=dataset_manifests,
        samples=samples,
        run_result=run_result,
        metric_results=metric_results,
        capability_aggregates=capability_aggregates,
    )
    write_run_artifacts(out_dir, inputs)
    return EvalOutcome(run_id=run_id, out_dir=out_dir, run_result=run_result)

"""Cost estimation from published per-token prices.

Two rules, both about not lying:

- A model with no published price in ``configs/pricing/`` gets ``None``, not ``0.0``. Zero is a
  *claim* — that the call was free — and it is only true for local inference.
- A response with no reported token counts gets ``None`` too. Estimating tokens from string length
  and then reporting the result as a dollar cost would be inventing a number.

Prices are per **1M tokens**, in USD, and are pinned with the date they were read, because they
change and a run's cost report should be interpretable a year later.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from financebench.schemas.model_io import TokenUsage

__all__ = ["ModelPrice", "estimate_cost", "load_pricing", "lookup_price"]

_PRICING_DIR = Path("configs/pricing")


@dataclass(frozen=True)
class ModelPrice:
    """Published price for one model, per 1M tokens."""

    input_usd_per_1m: float
    output_usd_per_1m: float
    as_of: str


_CACHE: dict[str, ModelPrice] | None = None


def load_pricing(pricing_dir: Path | None = None) -> dict[str, ModelPrice]:
    """Load every ``configs/pricing/*.yaml`` into a ``model_ref -> ModelPrice`` map."""
    global _CACHE
    if pricing_dir is None and _CACHE is not None:
        return _CACHE

    directory = pricing_dir or _PRICING_DIR
    prices: dict[str, ModelPrice] = {}
    if directory.is_dir():
        for path in sorted(directory.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            as_of = str(data.get("as_of", "unknown"))
            for ref, entry in (data.get("models") or {}).items():
                prices[str(ref)] = ModelPrice(
                    input_usd_per_1m=float(entry["input_usd_per_1m"]),
                    output_usd_per_1m=float(entry["output_usd_per_1m"]),
                    as_of=as_of,
                )
    if pricing_dir is None:
        _CACHE = prices
    return prices


def lookup_price(model_ref: str, pricing_dir: Path | None = None) -> ModelPrice | None:
    """The published price for ``provider/model``, or ``None`` if we don't have one."""
    return load_pricing(pricing_dir).get(model_ref)


def estimate_cost(
    model_ref: str, usage: TokenUsage, pricing_dir: Path | None = None
) -> float | None:
    """Estimated USD cost, or ``None`` when either the price or the token counts are unknown."""
    price = lookup_price(model_ref, pricing_dir)
    if price is None:
        return None
    if usage.prompt_tokens is None and usage.completion_tokens is None:
        return None
    prompt = usage.prompt_tokens or 0
    completion = usage.completion_tokens or 0
    return round(
        prompt * price.input_usd_per_1m / 1e6 + completion * price.output_usd_per_1m / 1e6,
        8,
    )

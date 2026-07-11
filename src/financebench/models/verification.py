"""Has this provider ever actually worked?

There are three different things a provider can be, and collapsing any two of them is a lie:

- **live_verified** — a real request was sent to the real endpoint and a real answer came back.
  This is the only label that means "it works", and the only way to earn it is to do it.
- **implemented_not_live_verified** — the code exists and is unit-tested against a mocked
  transport, but no successful call has ever been made from this machine, because there is no key
  for it. It is not broken. It is *unproven*, which is a different thing, and pretending otherwise
  in either direction is dishonest: calling it "working" invents evidence, and calling it "broken"
  invents a defect.
- **unreachable** — a key exists and the call was attempted and it failed. That is a real finding
  and it is reported as one.

The label is **computed by attempting a call**, never declared in a class attribute. A static
``LIVE_VERIFIED = True`` is a claim the code makes about itself, and it stays true after the API
changes underneath it. This module makes the claim expensive and therefore trustworthy: a provider
is live-verified when, and only when, it just answered.

In this repository, exactly one provider is live-verified: **ollama**, because every real number in
`runs/` came out of it. OpenAI, Anthropic, Gemini and OpenRouter are all
`implemented_not_live_verified` — no keys exist here, and none of them has ever made a call.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from financebench.models.base import ModelProvider, available_providers, get_provider_class
from financebench.utils.errors import ProviderError

__all__ = [
    "ProviderVerification",
    "VerificationRecord",
    "verify_all_providers",
    "verify_provider",
]


class ProviderVerification(StrEnum):
    """What is actually known about a provider — and nothing more."""

    LIVE_VERIFIED = "live_verified"
    IMPLEMENTED_NOT_LIVE_VERIFIED = "implemented_not_live_verified"
    UNREACHABLE = "unreachable"
    #: The mock. It is a simulator holding the answer key, not a model, and it can never be either
    #: verified or unverified in any sense that matters.
    NOT_A_MODEL = "not_a_model"


@dataclass(frozen=True)
class VerificationRecord:
    provider: str
    status: ProviderVerification
    detail: str
    key_env_var: str | None = None
    base_url: str | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "status": self.status.value,
            "detail": self.detail,
            "key_env_var": self.key_env_var,
            "base_url": self.base_url,
        }


async def verify_provider(name: str, *, env: Mapping[str, str] | None = None) -> VerificationRecord:
    """Attempt a real health check against ``name``'s real endpoint.

    A provider that needs a key and hasn't got one is **not called** — and is recorded as
    `implemented_not_live_verified`, not as a failure. There is nothing wrong with it; we simply
    have no way to find out, and a red mark would be as much of an invention as a green one.
    """
    source = env if env is not None else os.environ
    cls = get_provider_class(name)

    if name == "mock":
        return VerificationRecord(
            provider=name,
            status=ProviderVerification.NOT_A_MODEL,
            detail="the mock is a simulator that reads the gold answer; it evaluates nothing",
        )

    key_env = getattr(cls, "API_KEY_ENV", None)
    base_url = getattr(cls, "DEFAULT_BASE_URL", None)
    requires_key = bool(getattr(cls, "REQUIRES_KEY", False))

    if requires_key and not (key_env and source.get(key_env)):
        return VerificationRecord(
            provider=name,
            status=ProviderVerification.IMPLEMENTED_NOT_LIVE_VERIFIED,
            detail=(
                f"no API key ({key_env} is unset), so no call has ever been made. The provider is "
                "implemented and unit-tested against a mocked transport; it is unproven, not broken."
            ),
            key_env_var=key_env,
            base_url=base_url,
        )

    provider: ModelProvider | None = None
    try:
        provider = cls.from_env(source)
        health = getattr(provider, "health", None)
        if health is None:
            return VerificationRecord(
                provider=name,
                status=ProviderVerification.IMPLEMENTED_NOT_LIVE_VERIFIED,
                detail="the provider exposes no health check, so reachability cannot be confirmed",
                key_env_var=key_env,
                base_url=base_url,
            )
        ok, detail = await health()
    except ProviderError as exc:
        return VerificationRecord(
            provider=name,
            status=ProviderVerification.UNREACHABLE,
            detail=str(exc),
            key_env_var=key_env,
            base_url=base_url,
        )
    except Exception as exc:  # a bug here must not be reported as a working provider
        return VerificationRecord(
            provider=name,
            status=ProviderVerification.UNREACHABLE,
            detail=f"{type(exc).__name__}: {exc}",
            key_env_var=key_env,
            base_url=base_url,
        )
    finally:
        if provider is not None:
            await provider.aclose()

    return VerificationRecord(
        provider=name,
        status=(ProviderVerification.LIVE_VERIFIED if ok else ProviderVerification.UNREACHABLE),
        detail=detail,
        key_env_var=key_env,
        base_url=base_url,
    )


async def verify_all_providers(*, env: Mapping[str, str] | None = None) -> list[VerificationRecord]:
    """Verify every registered provider, concurrently."""
    names = available_providers()
    records = await asyncio.gather(*(verify_provider(name, env=env) for name in names))
    return list(records)

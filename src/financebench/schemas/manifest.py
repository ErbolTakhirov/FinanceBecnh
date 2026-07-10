"""The dataset manifest schema — the source of truth for what a benchmark adapter actually
supports, under what license, and how well-tested that claim is.

The ``status`` discipline is the platform's central anti-fabrication mechanism: ``fully_supported``
is a claim that must be backed by both ``status_tested_at`` (enforced here) and a corresponding
end-to-end test (enforced by a repo-hygiene test in ``tests/``, since a Pydantic validator alone
can't confirm a test file exists).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["AdapterStatus", "DatasetManifest"]


class AdapterStatus(StrEnum):
    """How much of a benchmark's official data this platform can actually evaluate today."""

    FULLY_SUPPORTED = "fully_supported"
    SUPPORTED_PUBLIC_SUBSET = "supported_public_subset"
    USER_SUPPLIED_REQUIRED = "user_supplied_required"
    PARTIAL = "partial"
    PLANNED = "planned"
    UNAVAILABLE = "unavailable"


class DatasetManifest(BaseModel):
    """Provenance, licensing, and support-status record for one wrapped benchmark."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    official_source: str
    paper_url: str | None = None
    repository_url: str | None = None
    version_or_commit: str | None = None
    download_method: str | None = None
    checksum: str | None = None
    official_splits: tuple[str, ...] = Field(default_factory=tuple)
    local_splits: tuple[str, ...] = Field(default_factory=tuple)
    license: str
    redistribution_status: str
    expected_files: tuple[str, ...] = Field(default_factory=tuple)
    status: AdapterStatus
    known_limitations: tuple[str, ...] = Field(default_factory=tuple)
    #: When this adapter's ``fully_supported`` (or ``supported_public_subset``) claim was last
    #: verified end-to-end. Required for both statuses — never claim any support level untested.
    status_tested_at: str | None = None

    @model_validator(mode="after")
    def _supported_status_requires_tested_at(self) -> DatasetManifest:
        tested_statuses = (AdapterStatus.FULLY_SUPPORTED, AdapterStatus.SUPPORTED_PUBLIC_SUBSET)
        if self.status in tested_statuses and self.status_tested_at is None:
            raise ValueError(
                f"status={self.status.value!r} requires status_tested_at to be set — "
                "never claim support without recording when it was verified end-to-end"
            )
        return self

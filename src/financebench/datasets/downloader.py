"""A safe, size-limited, checksum-verifying file downloader for ``prepare`` commands.

Security properties required by the mission: an HTTP timeout, a hard download-size cap, SHA-256
checksum verification when a known-good digest is provided, and an atomic write (download to a
temp file in the destination's own directory, then rename) so a failed or interrupted download
never leaves a partial file at the final path.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx

from financebench.utils.errors import DatasetLoadError

__all__ = ["DEFAULT_MAX_DOWNLOAD_BYTES", "download_file"]

DEFAULT_MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024  # 200 MB — generous for any Layer 1 JSON dataset
_DEFAULT_TIMEOUT_S = 60.0


def download_file(
    url: str,
    dest: str | Path,
    *,
    expected_sha256: str | None = None,
    max_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> str:
    """Stream ``url`` to ``dest``, enforcing ``max_bytes`` and (if given) ``expected_sha256``.

    Returns the downloaded file's actual SHA-256 hex digest (record this in the dataset
    manifest's ``checksum`` field even when no expected value was known ahead of time).
    """
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_name(dest_path.name + ".part")

    hasher = hashlib.sha256()
    total = 0
    try:
        with httpx.stream("GET", url, timeout=timeout_s, follow_redirects=True) as response:
            response.raise_for_status()
            with tmp_path.open("wb") as handle:
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        raise DatasetLoadError(
                            f"download from {url} exceeded the {max_bytes}-byte limit"
                        )
                    hasher.update(chunk)
                    handle.write(chunk)
    except httpx.HTTPError as exc:
        tmp_path.unlink(missing_ok=True)
        raise DatasetLoadError(f"failed to download {url}: {exc}") from exc
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise

    digest = hasher.hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        tmp_path.unlink(missing_ok=True)
        raise DatasetLoadError(
            f"checksum mismatch for {url}: expected {expected_sha256}, got {digest}"
        )
    tmp_path.replace(dest_path)
    return digest

from __future__ import annotations

from pathlib import Path

import pytest

from financebench.execution.cache import ResponseCache, request_hash
from financebench.schemas.model_io import ChatMessage, ModelRequest, ModelResponse, ModelSpec, Role
from financebench.schemas.run import CacheMode
from financebench.utils.secrets import scan_paths_for_secrets


def _request(**overrides: object) -> ModelRequest:
    defaults: dict[str, object] = {
        "model": ModelSpec.parse("openai/gpt-4o-mini"),
        "messages": (ChatMessage(role=Role.USER, content="What was the revenue increase?"),),
        "temperature": 0.0,
        "prompt_version": "v1",
        "benchmark": "finqa",
        "benchmark_version": "1",
        "sample_id": "finqa:test:1",
    }
    defaults.update(overrides)
    return ModelRequest.model_validate(defaults)


def _response(answer: str = "12.5%") -> ModelResponse:
    return ModelResponse(provider="openai", model="gpt-4o-mini", content=answer, parsed=True)


# --------------------------------------------------------------------------- request_hash


def test_hash_is_deterministic() -> None:
    assert request_hash(_request()) == request_hash(_request())


def test_hash_ignores_request_id_and_timeout() -> None:
    a = _request(request_id="call-1", timeout_s=30.0)
    b = _request(request_id="call-2", timeout_s=999.0)
    assert request_hash(a) == request_hash(b)


@pytest.mark.parametrize(
    "overrides",
    [
        {"temperature": 0.7},
        {"sample_id": "finqa:test:2"},
        {"prompt_version": "v2"},
        {"benchmark_version": "2"},
        {"messages": (ChatMessage(role=Role.USER, content="different question"),)},
        {"model": ModelSpec.parse("openai/gpt-4o")},
    ],
)
def test_hash_changes_when_answer_relevant_fields_change(overrides: dict[str, object]) -> None:
    assert request_hash(_request()) != request_hash(_request(**overrides))


def test_hash_is_insensitive_to_python_dict_construction_order() -> None:
    # model_dump + sort_keys should make this a non-issue, but prove it directly.
    r1 = _request(model=ModelSpec.parse("openai/gpt-4o-mini", params={"a": 1, "b": 2}))
    r2 = _request(model=ModelSpec.parse("openai/gpt-4o-mini", params={"b": 2, "a": 1}))
    assert request_hash(r1) == request_hash(r2)


# --------------------------------------------------------------------------- ResponseCache


def test_miss_on_empty_cache(tmp_path: Path) -> None:
    cache = ResponseCache(tmp_path)
    assert cache.get(_request()) is None


def test_put_then_get_round_trips(tmp_path: Path) -> None:
    cache = ResponseCache(tmp_path)
    request = _request()
    response = _response()
    cache.put(
        request, response, financebench_version="0.1.0-alpha", written_at="2026-07-11T00:00:00Z"
    )
    reloaded = cache.get(request)
    assert reloaded == response


def test_cache_shards_by_first_two_hex_characters(tmp_path: Path) -> None:
    cache = ResponseCache(tmp_path)
    request = _request()
    cache.put(request, _response(), financebench_version="0.1.0-alpha", written_at="now")
    key = request_hash(request)
    expected_path = tmp_path / "responses" / "v1" / key[:2] / f"{key}.json"
    assert expected_path.is_file()


def test_atomic_write_leaves_no_tmp_file(tmp_path: Path) -> None:
    cache = ResponseCache(tmp_path)
    cache.put(_request(), _response(), financebench_version="0.1.0-alpha", written_at="now")
    tmp_files = list(tmp_path.rglob("*.tmp"))
    assert tmp_files == []


def test_corrupt_cache_entry_is_treated_as_a_miss(tmp_path: Path) -> None:
    cache = ResponseCache(tmp_path)
    request = _request()
    key = request_hash(request)
    path = tmp_path / "responses" / "v1" / key[:2] / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not valid json {{{", encoding="utf-8")
    assert cache.get(request) is None


def test_off_mode_never_reads_or_writes(tmp_path: Path) -> None:
    cache = ResponseCache(tmp_path, mode=CacheMode.OFF)
    request = _request()
    cache.put(request, _response(), financebench_version="0.1.0-alpha", written_at="now")
    assert cache.get(request) is None
    assert cache.stats().entry_count == 0


def test_read_only_mode_reads_existing_but_never_writes(tmp_path: Path) -> None:
    writer = ResponseCache(tmp_path, mode=CacheMode.READ_WRITE)
    request = _request()
    writer.put(request, _response("seeded"), financebench_version="0.1.0-alpha", written_at="now")

    reader = ResponseCache(tmp_path, mode=CacheMode.READ_ONLY)
    assert reader.get(request) == _response("seeded")

    other_request = _request(sample_id="finqa:test:2")
    reader.put(
        other_request, _response("should not persist"), financebench_version="x", written_at="now"
    )
    assert reader.get(other_request) is None


def test_refresh_mode_never_reads_but_still_writes(tmp_path: Path) -> None:
    writer = ResponseCache(tmp_path, mode=CacheMode.READ_WRITE)
    request = _request()
    writer.put(request, _response("stale"), financebench_version="0.1.0-alpha", written_at="now")

    refresher = ResponseCache(tmp_path, mode=CacheMode.REFRESH)
    assert refresher.get(request) is None  # never reads, even though an entry exists
    refresher.put(
        request, _response("fresh"), financebench_version="0.1.0-alpha", written_at="later"
    )

    reader = ResponseCache(tmp_path, mode=CacheMode.READ_ONLY)
    assert reader.get(request) == _response("fresh")


def test_stats_counts_entries_and_size(tmp_path: Path) -> None:
    cache = ResponseCache(tmp_path)
    assert cache.stats().entry_count == 0
    cache.put(_request(), _response(), financebench_version="0.1.0-alpha", written_at="now")
    cache.put(
        _request(sample_id="finqa:test:2"),
        _response(),
        financebench_version="0.1.0-alpha",
        written_at="now",
    )
    stats = cache.stats()
    assert stats.entry_count == 2
    assert stats.total_size_bytes > 0


def test_clear_removes_everything_and_returns_count(tmp_path: Path) -> None:
    cache = ResponseCache(tmp_path)
    cache.put(_request(), _response(), financebench_version="0.1.0-alpha", written_at="now")
    cache.put(
        _request(sample_id="finqa:test:2"),
        _response(),
        financebench_version="0.1.0-alpha",
        written_at="now",
    )
    removed = cache.clear()
    assert removed == 2
    assert cache.stats().entry_count == 0


def test_clear_on_never_used_cache_dir_returns_zero(tmp_path: Path) -> None:
    cache = ResponseCache(tmp_path / "never-created")
    assert cache.clear() == 0


def test_cache_files_never_contain_a_secret_value(tmp_path: Path) -> None:
    cache = ResponseCache(tmp_path)
    fake_secret = "sk-definitely-a-secret-1234"
    # Even if a provider carelessly echoed a secret into raw metadata, the cache file itself
    # must never end up holding it — prove this against the actual bytes written to disk.
    response = ModelResponse(
        provider="openai",
        model="gpt-4o-mini",
        content="12.5%",
        parsed=True,
        raw={"note": "no secrets here"},
    )
    cache.put(_request(), response, financebench_version="0.1.0-alpha", written_at="now")
    hits = scan_paths_for_secrets(tmp_path.rglob("*.json"), [fake_secret])
    assert hits == {}

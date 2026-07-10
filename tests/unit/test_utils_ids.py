from __future__ import annotations

from financebench.utils.ids import IdFactory, make_run_id, short_hash, slugify


def test_slugify_lowercases_and_replaces_unsafe_chars() -> None:
    assert slugify("Mock/Echo Gold!") == "mock-echo-gold"


def test_slugify_strips_leading_trailing_dashes() -> None:
    assert slugify("--weird--") == "weird"


def test_short_hash_is_deterministic() -> None:
    assert short_hash("a", "b", "c") == short_hash("a", "b", "c")


def test_short_hash_distinguishes_part_boundaries() -> None:
    # "ab" + "c" must not hash the same as "a" + "bc" — the \x1f separator prevents this.
    assert short_hash("ab", "c") != short_hash("a", "bc")


def test_short_hash_respects_length() -> None:
    assert len(short_hash("x", length=12)) == 12


def test_make_run_id_is_deterministic() -> None:
    first = make_run_id("smoke", "mock/echo-gold", 42)
    second = make_run_id("smoke", "mock/echo-gold", 42)
    assert first == second


def test_make_run_id_differs_on_seed() -> None:
    assert make_run_id("smoke", "mock/echo-gold", 42) != make_run_id("smoke", "mock/echo-gold", 7)


def test_make_run_id_is_human_readable() -> None:
    run_id = make_run_id("core_public", "openai/gpt-4o-mini", 42)
    assert run_id.startswith("core_public-openai-gpt-4o-mini-")
    digest = run_id.removeprefix("core_public-openai-gpt-4o-mini-")
    assert len(digest) == 8


def test_id_factory_issues_sequential_ids() -> None:
    factory = IdFactory("run-1")
    first = factory.next_id("pred")
    second = factory.next_id("pred")
    assert first == "run-1-pred-00000"
    assert second == "run-1-pred-00001"
    assert factory.issued == 2

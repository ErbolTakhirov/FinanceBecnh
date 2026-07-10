from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, TypeAdapter

from financebench.storage.jsonl import (
    read_jsonl,
    read_model_json,
    read_model_list,
    write_model_json,
)


class _Widget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    widget_id: str
    count: int


_ADAPTER: TypeAdapter[_Widget] = TypeAdapter(_Widget)


def test_read_jsonl_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text('{"a": 1}\n\n{"b": 2}\n', encoding="utf-8")
    records = list(read_jsonl(path))
    assert records == [{"a": 1}, {"b": 2}]


def test_read_model_list_validates_every_record(tmp_path: Path) -> None:
    path = tmp_path / "widgets.jsonl"
    path.write_text(
        '{"widget_id": "w1", "count": 1}\n{"widget_id": "w2", "count": 2}\n', encoding="utf-8"
    )
    widgets = read_model_list(path, _ADAPTER)
    assert [w.widget_id for w in widgets] == ["w1", "w2"]


def test_write_model_json_creates_parent_dirs(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "deep" / "widget.json"
    write_model_json(path, _Widget(widget_id="w1", count=1))
    assert path.is_file()


def test_write_then_read_model_json_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "widget.json"
    original = _Widget(widget_id="w1", count=7)
    write_model_json(path, original)
    reloaded = read_model_json(path, _ADAPTER)
    assert reloaded == original

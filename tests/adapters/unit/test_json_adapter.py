"""Unit tests for JSONAdapter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from neurolab.adapters.core.exceptions import AdapterError
from neurolab.adapters.implementations.tabular.json_adapter import JSONAdapter
from neurolab.data_interface.models import Artifact

pytestmark = [pytest.mark.adapters, pytest.mark.unit]


def _artifact(
    absolute_path: str | None,
    media_type: str | None = "application/json",
    relative_path: str | None = "x.json",
) -> Artifact:
    return Artifact(
        artifact_id="a1",
        source_uri="file:///data",
        artifact_type="file",
        relative_path=relative_path,
        absolute_path=absolute_path,
        size_bytes=0,
        mtime=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        content_hash=None,
        media_type=media_type,
    )


def test_can_handle_media_type_json():
    """can_handle returns True for media_type application/json."""
    adapter = JSONAdapter()
    art = _artifact(absolute_path="/x.json", media_type="application/json")
    assert adapter.can_handle(art) is True


def test_can_handle_extension_json():
    """can_handle returns True when path ends with .json."""
    adapter = JSONAdapter()
    art = _artifact(absolute_path="/data/file.json", media_type=None, relative_path="file.json")
    assert adapter.can_handle(art) is True


def test_can_handle_rejects_non_json():
    """can_handle returns False for non-JSON media type and path."""
    adapter = JSONAdapter()
    art = _artifact(absolute_path="/data/file.txt", media_type="text/plain", relative_path="file.txt")
    assert adapter.can_handle(art) is False


def test_parse_requires_absolute_path():
    """parse raises when artifact has no absolute_path."""
    adapter = JSONAdapter()
    art = _artifact(absolute_path=None, relative_path="x.json")
    with pytest.raises(AdapterError, match="absolute_path"):
        adapter.parse(art)


def test_parse_returns_list_of_one_array(tmp_path):
    """parse returns list with single AdapterOutput for a JSON array file."""
    json_file = tmp_path / "data.json"
    json_file.write_text('[{"a": 1}, {"a": 2}]', encoding="utf-8")

    adapter = JSONAdapter()
    art = _artifact(absolute_path=str(json_file))
    result = adapter.parse(art)

    assert len(result) == 1
    out = result[0]
    assert out.artifact_id == "a1"
    assert out.adapter_name == "json_adapter"
    assert out.adapter_version == "1.0"
    assert out.dataset_type == "tabular"
    assert out.schema == {"root_type": "array", "length": 2}
    assert out.payload == [{"a": 1}, {"a": 2}]


def test_parse_object_json(tmp_path):
    """parse handles JSON object as single payload."""
    json_file = tmp_path / "config.json"
    json_file.write_text('{"key": "value", "n": 42}', encoding="utf-8")

    adapter = JSONAdapter()
    art = _artifact(absolute_path=str(json_file))
    result = adapter.parse(art)

    assert len(result) == 1
    out = result[0]
    assert out.schema == {"root_type": "object"}
    assert out.payload == {"key": "value", "n": 42}


def test_parse_file_not_found_raises(tmp_path):
    """parse raises when file does not exist."""
    adapter = JSONAdapter()
    art = _artifact(absolute_path=str(tmp_path / "nonexistent.json"))
    with pytest.raises(AdapterError, match="not found"):
        adapter.parse(art)


def test_parse_invalid_json_raises(tmp_path):
    """parse raises AdapterError for invalid JSON."""
    json_file = tmp_path / "bad.json"
    json_file.write_text("not valid json {", encoding="utf-8")

    adapter = JSONAdapter()
    art = _artifact(absolute_path=str(json_file))
    with pytest.raises(AdapterError, match="Failed to parse JSON"):
        adapter.parse(art)

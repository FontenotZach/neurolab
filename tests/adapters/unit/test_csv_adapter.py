"""Unit tests for CSVAdapter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from neurolab.adapters.core.exceptions import AdapterError
from neurolab.adapters.implementations.tabular.csv_adapter import CSVAdapter
from neurolab.data_interface.models import Artifact

pytestmark = [pytest.mark.adapters, pytest.mark.unit]


def _artifact(absolute_path: str | None, media_type: str | None = "text/csv", relative_path: str | None = "x.csv") -> Artifact:
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


def test_can_handle_media_type_csv():
    """can_handle returns True for media_type text/csv."""
    adapter = CSVAdapter()
    art = _artifact(absolute_path="/x.csv", media_type="text/csv")
    assert adapter.can_handle(art) is True


def test_can_handle_extension_csv():
    """can_handle returns True when path ends with .csv."""
    adapter = CSVAdapter()
    art = _artifact(absolute_path="/data/file.csv", media_type=None, relative_path="file.csv")
    assert adapter.can_handle(art) is True


def test_can_handle_rejects_non_csv():
    """can_handle returns False for non-CSV media type and path."""
    adapter = CSVAdapter()
    art = _artifact(absolute_path="/data/file.txt", media_type="text/plain", relative_path="file.txt")
    assert adapter.can_handle(art) is False


def test_parse_requires_absolute_path():
    """parse raises when artifact has no absolute_path."""
    adapter = CSVAdapter()
    art = _artifact(absolute_path=None, relative_path="x.csv")
    with pytest.raises(AdapterError, match="absolute_path"):
        adapter.parse(art)


def test_parse_returns_list_of_one(tmp_path):
    """parse returns list with single AdapterOutput for a CSV file."""
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("col1,col2\n1,2\n3,4", encoding="utf-8")

    adapter = CSVAdapter()
    art = _artifact(absolute_path=str(csv_file))
    result = adapter.parse(art)

    assert len(result) == 1
    out = result[0]
    assert out.artifact_id == "a1"
    assert out.adapter_name == "csv_adapter"
    assert out.adapter_version == "1.0"
    assert out.dataset_type == "tabular"
    assert out.schema == {"columns": ["col1", "col2"]}
    assert out.payload == [{"col1": "1", "col2": "2"}, {"col1": "3", "col2": "4"}]


def test_parse_file_not_found_raises(tmp_path):
    """parse raises when file does not exist."""
    adapter = CSVAdapter()
    art = _artifact(absolute_path=str(tmp_path / "nonexistent.csv"))
    with pytest.raises(AdapterError, match="not found"):
        adapter.parse(art)

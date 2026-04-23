"""Unit tests for AdapterRouter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from neurolab.adapters.core.router import AdapterRouter
from neurolab.data_interface.models import Artifact

pytestmark = [pytest.mark.adapters, pytest.mark.unit]


def _csv_artifact(absolute_path: str | None = "/data/file.csv") -> Artifact:
    return Artifact(
        artifact_id="art-1",
        source_uri="file:///data",
        artifact_type="file",
        relative_path="file.csv",
        absolute_path=absolute_path,
        size_bytes=100,
        mtime=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        content_hash="abc",
        media_type="text/csv",
    )


def test_route_returns_list(tmp_path):
    """Router returns list[AdapterOutput], not None."""
    csv_file = tmp_path / "file.csv"
    csv_file.write_text("a,b\n1,2", encoding="utf-8")
    router = AdapterRouter()
    artifact = _csv_artifact(absolute_path=str(csv_file))
    result = router.route(artifact)
    assert isinstance(result, list)
    assert len(result) == 1


def test_route_no_match_returns_empty_list(tmp_path):
    """When no adapter matches, router returns empty list."""
    router = AdapterRouter()
    # Artifact with unknown type and path so no adapter matches
    artifact = Artifact(
        artifact_id="art-x",
        source_uri="file:///data",
        artifact_type="file",
        relative_path="file.unknown",
        absolute_path=str(tmp_path / "file.unknown"),
        size_bytes=0,
        mtime=None,
        content_hash=None,
        media_type="application/octet-stream",
    )
    result = router.route(artifact)
    assert result == []


def test_route_csv_returns_single_output(tmp_path):
    """One matching CSV adapter yields list of one AdapterOutput."""
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("col1,col2\n1,2\n3,4", encoding="utf-8")

    router = AdapterRouter()
    artifact = _csv_artifact(absolute_path=str(csv_file))
    result = router.route(artifact)

    assert len(result) == 1
    out = result[0]
    assert out.adapter_name == "csv_adapter"
    assert out.adapter_version == "1.0"
    assert out.dataset_type == "tabular"
    assert out.schema["columns"] == ["col1", "col2"]
    assert out.payload == [{"col1": "1", "col2": "2"}, {"col1": "3", "col2": "4"}]

"""Unit tests for AdapterPipeline and AdapterPipelineResult."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from neurolab.adapters.pipeline.adapter_pipeline import AdapterPipeline, AdapterPipelineResult
from neurolab.data_interface.models import Artifact, DataSourceSpec, Manifest

pytestmark = [pytest.mark.adapters, pytest.mark.unit]


def _manifest_with_artifacts(artifacts: list[Artifact]) -> Manifest:
    return Manifest(
        manifest_id="m1",
        source=DataSourceSpec(uri="/data"),
        created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        artifacts=artifacts,
        warnings=[],
    )


def test_process_manifest_empty_artifacts():
    """Manifest with no artifacts yields empty outputs and empty skipped."""
    pipeline = AdapterPipeline()
    manifest = _manifest_with_artifacts([])
    result = pipeline.process_manifest(manifest)
    assert isinstance(result, AdapterPipelineResult)
    assert result.outputs == []
    assert result.skipped_artifacts == []


def test_process_manifest_skipped_artifacts_recorded(tmp_path):
    """Artifacts that no adapter matches appear in skipped_artifacts."""
    pipeline = AdapterPipeline()
    art = Artifact(
        artifact_id="a1",
        source_uri="file:///data",
        artifact_type="file",
        relative_path="x.unknown",
        absolute_path=str(tmp_path / "x.unknown"),
        size_bytes=0,
        mtime=None,
        content_hash=None,
        media_type="application/octet-stream",
    )
    manifest = _manifest_with_artifacts([art])
    result = pipeline.process_manifest(manifest)
    assert result.outputs == []
    assert len(result.skipped_artifacts) == 1
    assert result.skipped_artifacts[0].artifact_id == "a1"


def test_process_manifest_deterministic_order_and_outputs(tmp_path):
    """Artifacts processed in sorted order; CSV yields outputs."""
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("a,b\n1,2", encoding="utf-8")

    art = Artifact(
        artifact_id="a1",
        source_uri="file:///data",
        artifact_type="file",
        relative_path="data.csv",
        absolute_path=str(csv_file),
        size_bytes=10,
        mtime=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        content_hash="x",
        media_type="text/csv",
    )
    manifest = _manifest_with_artifacts([art])
    pipeline = AdapterPipeline()
    result = pipeline.process_manifest(manifest)

    assert len(result.outputs) == 1
    assert result.outputs[0].dataset_type == "tabular"
    assert result.skipped_artifacts == []

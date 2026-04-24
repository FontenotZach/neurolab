"""Regression tests: data_hash (content) vs provenance_id (lineage)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from neurolab.adapters.core.output import AdapterOutput
from neurolab.adapters.pipeline.adapter_pipeline import AdapterPipeline, AdapterPipelineResult
from neurolab.data_interface.hashing import hash_file_sha256
from neurolab.data_interface.models import Artifact, DataSourceSpec, Manifest
from neurolab.data_interface.orchestrator import collect_source
from neurolab.storage.adapter_results.file_store import FileAdapterResultStore
from neurolab.storage.adapter_results.ids import (
    compute_data_hash,
    compute_provenance_id,
    schema_fingerprint,
)

pytestmark = [pytest.mark.storage]


def _artifact(aid: str, rel: str, content_hash: str | None) -> Artifact:
    return Artifact(
        artifact_id=aid,
        source_uri="file:///x",
        artifact_type="file",
        relative_path=rel,
        absolute_path=f"/x/{rel}",
        size_bytes=3,
        mtime=datetime(2024, 1, 1, tzinfo=UTC),
        content_hash=content_hash,
        media_type="text/plain",
    )


def _manifest(mid: str, artifacts: list[Artifact]) -> Manifest:
    return Manifest(
        manifest_id=mid,
        source=DataSourceSpec(uri="file:///x", compute_hash=True),
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        artifacts=artifacts,
        warnings=[],
    )


@pytest.mark.unit
def test_same_payload_diff_adapter_version_same_data_hash_diff_provenance(tmp_path):
    store = FileAdapterResultStore(base_dir=tmp_path)
    art = _artifact("a1", "f.txt", "0" * 64)
    m = _manifest("m1", [art])
    payload = {"v": 1}
    dh = compute_data_hash(payload)
    sf = schema_fingerprint({"k": 1})
    o1 = AdapterOutput(
        artifact_id="a1",
        adapter_name="csv_adapter",
        adapter_version="1.0",
        dataset_type="tabular",
        schema={"k": 1},
        payload=payload,
    )
    o2 = AdapterOutput(
        artifact_id="a1",
        adapter_name="csv_adapter",
        adapter_version="2.0",
        dataset_type="tabular",
        schema={"k": 1},
        payload=payload,
    )
    p1 = compute_provenance_id(
        manifest_id="m1",
        artifact_key="f.txt",
        raw_content_hash="0" * 64,
        adapter_name=o1.adapter_name,
        adapter_version=o1.adapter_version,
        adapter_config_hash=o1.adapter_config_hash,
        schema_fingerprint=sf,
        pipeline_ordinal=0,
    )
    p2 = compute_provenance_id(
        manifest_id="m1",
        artifact_key="f.txt",
        raw_content_hash="0" * 64,
        adapter_name=o2.adapter_name,
        adapter_version=o2.adapter_version,
        adapter_config_hash=o2.adapter_config_hash,
        schema_fingerprint=sf,
        pipeline_ordinal=0,
    )
    assert dh == compute_data_hash(payload)
    assert p1 != p2

    saved = store.save_pipeline_result(m, AdapterPipelineResult(outputs=[o1, o2], skipped_artifacts=[]))
    assert saved[0].data_hash == saved[1].data_hash == dh
    assert saved[0].provenance_id != saved[1].provenance_id


@pytest.mark.unit
def test_analysis_equivalence_groups_by_data_hash_not_provenance():
    """Two provenance ids can share one data_hash (computational equivalence class)."""
    payload = {"x": [1, 2]}
    dh = compute_data_hash(payload)
    p1 = compute_provenance_id(
        manifest_id="m",
        artifact_key="a",
        raw_content_hash=None,
        adapter_name="a",
        adapter_version="1",
        adapter_config_hash=None,
        schema_fingerprint=schema_fingerprint({}),
        pipeline_ordinal=0,
    )
    p2 = compute_provenance_id(
        manifest_id="m",
        artifact_key="a",
        raw_content_hash=None,
        adapter_name="b",
        adapter_version="1",
        adapter_config_hash=None,
        schema_fingerprint=schema_fingerprint({}),
        pipeline_ordinal=0,
    )
    assert p1 != p2
    # Same payload identity
    assert dh == compute_data_hash(payload)


@pytest.mark.integration
def test_raw_file_bytes_match_collected_content_hash(tmp_path):
    f = tmp_path / "sample.bin"
    f.write_bytes(b"hello-world")
    expected = hash_file_sha256(f)
    source = DataSourceSpec(uri=str(f))
    manifest = collect_source(source)
    assert len(manifest.artifacts) == 1
    assert manifest.artifacts[0].content_hash == expected


@pytest.mark.integration
def test_recollect_stable_provenance_ids(project_test_data_dir, tmp_path):
    """Same dataset twice yields same manifest_id and matching provenance for parse+store."""
    session_dir = project_test_data_dir / "session1"
    if not session_dir.exists():
        pytest.skip("test_data/session1 not found")

    out_dir = tmp_path / "adapter_outputs"

    def run_once():
        m = collect_source(DataSourceSpec(uri=str(session_dir), recursive=True))
        pipeline = AdapterPipeline()
        result = pipeline.process_manifest(m)
        store = FileAdapterResultStore(base_dir=out_dir)
        store.delete_manifest_outputs(m.manifest_id)
        saved = store.save_pipeline_result(m, result)
        return m, saved

    m1, s1 = run_once()
    m2, s2 = run_once()
    if not s1:
        pytest.skip("no adapter outputs for session1")
    assert m1.manifest_id == m2.manifest_id
    p1 = sorted([x.provenance_id for x in s1])
    p2 = sorted([x.provenance_id for x in s2])
    assert p1 == p2

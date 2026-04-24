"""FileAdapterResultStore integration-style tests."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from neurolab.adapters.core.output import AdapterOutput
from neurolab.adapters.pipeline.adapter_pipeline import AdapterPipelineResult
from neurolab.data_interface.models import Artifact, DataSourceSpec, Manifest
from neurolab.storage.adapter_results.errors import StoredOutputNotFound
from neurolab.storage.adapter_results.file_store import FileAdapterResultStore

pytestmark = [pytest.mark.storage]


def _artifact(aid: str = "art-1", *, rel_path: str = "f.csv", content_hash: str | None = "a" * 64) -> Artifact:
    return Artifact(
        artifact_id=aid,
        source_uri="file:///x",
        artifact_type="file",
        relative_path=rel_path,
        absolute_path=f"/tmp/{rel_path}",
        size_bytes=10,
        mtime=datetime(2024, 1, 1, tzinfo=UTC),
        content_hash=content_hash,
        media_type="text/csv",
    )


def _manifest(mid: str = "mid-1", *, artifacts: list[Artifact] | None = None) -> Manifest:
    arts = artifacts if artifacts is not None else [_artifact()]
    src = DataSourceSpec(uri="file:///x", compute_hash=True)
    return Manifest(
        manifest_id=mid,
        source=src,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        artifacts=arts,
        warnings=[],
    )


@pytest.mark.unit
def test_file_store_save_list_load_payload(tmp_path):
    store = FileAdapterResultStore(base_dir=tmp_path)
    m = _manifest()
    out = AdapterOutput(
        artifact_id="art-1",
        adapter_name="t",
        adapter_version="1",
        dataset_type="tabular",
        schema={"c": 1},
        payload=[{"a": 1}],
    )
    saved = store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))
    assert len(saved) == 1
    pid = saved[0].provenance_id
    listed = store.list_outputs(m.manifest_id)
    assert [x.provenance_id for x in listed] == [pid]
    meta = store.load_metadata(m.manifest_id, pid)
    assert meta.adapter_name == "t"
    assert meta.data_hash == saved[0].data_hash
    payload = store.load_payload(m.manifest_id, pid)
    assert payload == [{"a": 1}]


@pytest.mark.unit
def test_file_store_overwrites_same_provenance(tmp_path):
    store = FileAdapterResultStore(base_dir=tmp_path)
    m = _manifest()
    base_kw = dict(artifact_id="art-1", adapter_name="t", adapter_version="1", dataset_type="tabular", schema={"k": 1})
    o1 = AdapterOutput(**base_kw, payload=[{"n": 1}])
    o2 = AdapterOutput(**base_kw, payload=[{"n": 2}])
    store.save_pipeline_result(m, AdapterPipelineResult(outputs=[o1], skipped_artifacts=[]))
    store.save_pipeline_result(m, AdapterPipelineResult(outputs=[o2], skipped_artifacts=[]))
    listed = store.list_outputs(m.manifest_id)
    assert len(listed) == 1
    assert store.load_payload(m.manifest_id, listed[0].provenance_id) == [{"n": 2}]


@pytest.mark.unit
def test_file_store_removes_orphan_records(tmp_path):
    store = FileAdapterResultStore(base_dir=tmp_path)
    m = _manifest(artifacts=[_artifact("art-1", rel_path="a.csv"), _artifact("art-2", rel_path="b.csv")])
    o1 = AdapterOutput(
        artifact_id="art-1",
        adapter_name="t",
        adapter_version="1",
        dataset_type="tabular",
        schema={"v": 1},
        payload={"x": 1},
    )
    o2 = AdapterOutput(
        artifact_id="art-2",
        adapter_name="t",
        adapter_version="1",
        dataset_type="tabular",
        schema={"v": 2},
        payload={"x": 2},
    )
    first = store.save_pipeline_result(m, AdapterPipelineResult(outputs=[o1, o2], skipped_artifacts=[]))
    ids_before = {x.provenance_id for x in first}
    assert len(ids_before) == 2

    store.save_pipeline_result(m, AdapterPipelineResult(outputs=[o1], skipped_artifacts=[]))
    listed = store.list_outputs(m.manifest_id)
    assert len(listed) == 1
    assert listed[0].artifact_id == "art-1"


@pytest.mark.unit
def test_list_outputs_works_without_index_file(tmp_path):
    store = FileAdapterResultStore(base_dir=tmp_path)
    m = _manifest()
    out = AdapterOutput(
        artifact_id="art-1",
        adapter_name="n",
        adapter_version="1",
        dataset_type="t",
        schema={},
        payload=None,
    )
    store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))
    index = tmp_path / m.manifest_id / "index.json"
    assert index.is_file()
    index.unlink()
    listed = store.list_outputs(m.manifest_id)
    assert len(listed) == 1
    assert listed[0].artifact_id == "art-1"


@pytest.mark.unit
def test_load_missing_raises(tmp_path):
    store = FileAdapterResultStore(base_dir=tmp_path)
    with pytest.raises(StoredOutputNotFound):
        store.load_metadata("missing", "0" * 64)


@pytest.mark.unit
def test_numpy_payload_roundtrip(tmp_path):
    store = FileAdapterResultStore(base_dir=tmp_path)
    m = _manifest()
    out = AdapterOutput(
        artifact_id="art-1",
        adapter_name="n",
        adapter_version="1",
        dataset_type="timeseries",
        schema={"n": 3},
        payload={"signal": np.array([1.0, 2.0], dtype=np.float32)},
    )
    sid = store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))[0].provenance_id
    back = store.load_payload(m.manifest_id, sid)
    np.testing.assert_array_equal(back["signal"], out.payload["signal"])

"""FileAdapterResultStore integration-style tests."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from neurolab.adapters.core.output import AdapterOutput
from neurolab.adapters.pipeline.adapter_pipeline import AdapterPipelineResult
from neurolab.data_interface.models import DataSourceSpec, Manifest
from neurolab.storage.adapter_results.errors import StoredOutputNotFound
from neurolab.storage.adapter_results.file_store import FileAdapterResultStore

pytestmark = [pytest.mark.storage]


def _manifest(mid: str = "mid-1") -> Manifest:
    src = DataSourceSpec(uri="file:///x", compute_hash=True)
    return Manifest(
        manifest_id=mid,
        source=src,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        artifacts=[],
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
        adapter_config_hash="cfg",
    )
    saved = store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))
    assert len(saved) == 1
    listed = store.list_outputs(m.manifest_id)
    assert [x.stored_output_id for x in listed] == [saved[0].stored_output_id]
    meta = store.load_metadata(m.manifest_id, saved[0].stored_output_id)
    assert meta.adapter_name == "t"
    payload = store.load_payload(m.manifest_id, saved[0].stored_output_id)
    assert payload == [{"a": 1}]


@pytest.mark.unit
def test_file_store_overwrites_same_id(tmp_path):
    store = FileAdapterResultStore(base_dir=tmp_path)
    m = _manifest()
    base_kw = dict(
        artifact_id="art-1",
        adapter_name="t",
        adapter_version="1",
        dataset_type="tabular",
        schema={"k": 1},
        adapter_config_hash="cfg",
    )
    o1 = AdapterOutput(**base_kw, payload=[{"n": 1}])
    o2 = AdapterOutput(**base_kw, payload=[{"n": 2}])
    store.save_pipeline_result(m, AdapterPipelineResult(outputs=[o1], skipped_artifacts=[]))
    store.save_pipeline_result(m, AdapterPipelineResult(outputs=[o2], skipped_artifacts=[]))
    listed = store.list_outputs(m.manifest_id)
    assert len(listed) == 1
    assert store.load_payload(m.manifest_id, listed[0].stored_output_id) == [{"n": 2}]


@pytest.mark.unit
def test_file_store_removes_orphan_records(tmp_path):
    store = FileAdapterResultStore(base_dir=tmp_path)
    m = _manifest()
    o1 = AdapterOutput(
        artifact_id="art-1",
        adapter_name="t",
        adapter_version="1",
        dataset_type="tabular",
        schema={"v": 1},
        payload={"x": 1},
        adapter_config_hash="cfg",
    )
    o2 = AdapterOutput(
        artifact_id="art-2",
        adapter_name="t",
        adapter_version="1",
        dataset_type="tabular",
        schema={"v": 2},
        payload={"x": 2},
        adapter_config_hash="cfg",
    )
    first = store.save_pipeline_result(m, AdapterPipelineResult(outputs=[o1, o2], skipped_artifacts=[]))
    ids_before = {x.stored_output_id for x in first}
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
        artifact_id="a",
        adapter_name="n",
        adapter_version="1",
        dataset_type="t",
        schema={},
        payload=None,
        adapter_config_hash="cfg",
    )
    store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))
    index = tmp_path / m.manifest_id / "index.json"
    assert index.is_file()
    index.unlink()
    listed = store.list_outputs(m.manifest_id)
    assert len(listed) == 1
    assert listed[0].artifact_id == "a"


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
        artifact_id="a",
        adapter_name="n",
        adapter_version="1",
        dataset_type="timeseries",
        schema={"n": 3},
        payload={"signal": np.array([1.0, 2.0], dtype=np.float32)},
        adapter_config_hash="cfg",
    )
    sid = store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))[0].stored_output_id
    back = store.load_payload(m.manifest_id, sid)
    np.testing.assert_array_equal(back["signal"], out.payload["signal"])

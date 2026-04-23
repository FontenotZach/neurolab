from __future__ import annotations

from datetime import UTC, datetime

import pytest

from neurolab.adapters.core.output import AdapterOutput
from neurolab.adapters.pipeline.adapter_pipeline import AdapterPipelineResult
from neurolab.analysis_hub.errors import MetadataLoadError, MetadataRecordNotFoundError
from neurolab.analysis_hub.filesystem import FileSystemAnalysisHub
from neurolab.data_interface.models import DataSourceSpec, Manifest
from neurolab.storage.adapter_results.file_store import FileAdapterResultStore

pytestmark = [pytest.mark.unit]


def _manifest(mid: str) -> Manifest:
    return Manifest(
        manifest_id=mid,
        source=DataSourceSpec(uri="file:///x", compute_hash=True),
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        artifacts=[],
        warnings=[],
    )


def test_scan_and_list_deterministic(tmp_path):
    store = FileAdapterResultStore(base_dir=tmp_path)

    m1 = _manifest("m-1")
    m2 = _manifest("m-2")

    out_a = AdapterOutput(
        artifact_id="a",
        adapter_name="ad",
        adapter_version="1",
        dataset_type="tabular",
        schema={"k": 1},
        payload={"x": 1},
    )
    out_b = AdapterOutput(
        artifact_id="b",
        adapter_name="ad",
        adapter_version="1",
        dataset_type="tabular",
        schema={"k": 2},
        payload={"x": 2},
    )

    store.save_pipeline_result(m2, AdapterPipelineResult(outputs=[out_b], skipped_artifacts=[]))
    store.save_pipeline_result(m1, AdapterPipelineResult(outputs=[out_a], skipped_artifacts=[]))

    hub = FileSystemAnalysisHub(base_dir=tmp_path)
    records = hub.list_records()

    assert [r.manifest_id for r in records] == ["m-1", "m-2"]
    assert [r.pipeline_ordinal for r in records] == [0, 0]
    assert [r.artifact_id for r in records] == ["a", "b"]


def test_find_records_filters_and_logic(tmp_path):
    store = FileAdapterResultStore(base_dir=tmp_path)
    m = _manifest("m-1")
    o1 = AdapterOutput(
        artifact_id="a",
        adapter_name="ad",
        adapter_version="1",
        dataset_type="tabular",
        schema={"k": 1},
        payload={"x": 1},
    )
    o2 = AdapterOutput(
        artifact_id="b",
        adapter_name="other",
        adapter_version="1",
        dataset_type="timeseries",
        schema={"k": 2},
        payload={"x": 2},
    )
    store.save_pipeline_result(m, AdapterPipelineResult(outputs=[o1, o2], skipped_artifacts=[]))

    hub = FileSystemAnalysisHub(base_dir=tmp_path)
    tabular = hub.find_records(manifest_id="m-1", dataset_type="tabular")
    assert len(tabular) == 1
    assert tabular[0].artifact_id == "a"

    none = hub.find_records(manifest_id="m-1", dataset_type="tabular", adapter_name="other")
    assert none == []


def test_open_handle_lazy_then_load_roundtrip(tmp_path):
    store = FileAdapterResultStore(base_dir=tmp_path)
    m = _manifest("m-1")
    out = AdapterOutput(
        artifact_id="a",
        adapter_name="ad",
        adapter_version="1",
        dataset_type="tabular",
        schema={"k": 1},
        payload=[{"a": 1}],
    )
    saved = store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))
    sid = saved[0].stored_output_id

    hub = FileSystemAnalysisHub(base_dir=tmp_path)
    h = hub.open_handle(sid)
    assert h.metadata.stored_output_id == sid
    assert h.load() == [{"a": 1}]


def test_missing_record_raises(tmp_path):
    hub = FileSystemAnalysisHub(base_dir=tmp_path)
    with pytest.raises(MetadataRecordNotFoundError):
        hub.get_record("0" * 64)
    with pytest.raises(MetadataRecordNotFoundError):
        hub.open_handle("0" * 64)


def test_malformed_meta_raises(tmp_path):
    # Create a record dir that looks like a stored output but has invalid meta.json.
    (tmp_path / "m-1" / ("0" * 64)).mkdir(parents=True)
    (tmp_path / "m-1" / ("0" * 64) / "meta.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(MetadataLoadError):
        FileSystemAnalysisHub(base_dir=tmp_path)


def test_numpy_payload_roundtrip_if_available(tmp_path):
    np = pytest.importorskip("numpy")
    store = FileAdapterResultStore(base_dir=tmp_path)
    m = _manifest("m-1")
    out = AdapterOutput(
        artifact_id="a",
        adapter_name="ad",
        adapter_version="1",
        dataset_type="timeseries",
        schema={"k": 1},
        payload={"signal": np.asarray([1.0, 2.0], dtype=np.float32)},
    )
    sid = store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))[0].stored_output_id

    hub = FileSystemAnalysisHub(base_dir=tmp_path)
    back = hub.open_handle(sid).load()
    np.testing.assert_array_equal(back["signal"], out.payload["signal"])


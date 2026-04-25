from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from neurolab.adapters.core.output import AdapterOutput
from neurolab.adapters.pipeline.adapter_pipeline import AdapterPipelineResult
from neurolab.analysis_hub.errors import MetadataLoadError, MetadataRecordNotFoundError
from neurolab.analysis_hub.filesystem import FileSystemAnalysisHub
from neurolab.analysis_hub.record_mapping import LINEAGE_ARTIFACT_ID, LINEAGE_MANIFEST_ID, LINEAGE_PIPELINE_ORDINAL
from neurolab.data_interface.models import Artifact, DataSourceSpec, Manifest
from neurolab.storage.adapter_results.file_store import FileAdapterResultStore
from neurolab.storage.analysis_results.file_store import FileAnalysisResultStore

pytestmark = [pytest.mark.unit]


def _adapter_root(tmp_path) -> Path:
    p = tmp_path / "adapter_outputs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _analysis_root(tmp_path) -> Path:
    p = tmp_path / "analysis_results"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _isolated_hub(tmp_path) -> FileSystemAnalysisHub:
    """Adapter outputs under adapter_outputs/; analysis results under analysis_results/ (sibling dirs)."""
    return FileSystemAnalysisHub(
        base_dir=_adapter_root(tmp_path),
        analysis_results_dir=_analysis_root(tmp_path),
    )


def _artifact(aid: str, *, rel_path: str = "f.csv") -> Artifact:
    return Artifact(
        artifact_id=aid,
        source_uri="file:///x",
        artifact_type="file",
        relative_path=rel_path,
        absolute_path=f"/tmp/{rel_path}",
        size_bytes=1,
        mtime=datetime(2024, 1, 1, tzinfo=UTC),
        content_hash="b" * 64,
        media_type="text/csv",
    )


def _manifest(mid: str, *, aids: tuple[str, ...]) -> Manifest:
    arts = [_artifact(aid, rel_path=f"{aid}.csv") for aid in aids]
    return Manifest(
        manifest_id=mid,
        source=DataSourceSpec(uri="file:///x", compute_hash=True),
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        artifacts=arts,
        warnings=[],
    )


def test_scan_and_list_deterministic(tmp_path):
    root = _adapter_root(tmp_path)
    store = FileAdapterResultStore(base_dir=root)

    m1 = _manifest("m-1", aids=("a",))
    m2 = _manifest("m-2", aids=("b",))

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

    hub = _isolated_hub(tmp_path)
    records = hub.list_records()

    assert [r.lineage[LINEAGE_MANIFEST_ID] for r in records] == ["m-1", "m-2"]
    assert [r.lineage[LINEAGE_PIPELINE_ORDINAL] for r in records] == [0, 0]
    assert [r.lineage[LINEAGE_ARTIFACT_ID] for r in records] == ["a", "b"]
    assert all(r.record_kind == "original" for r in records)


def test_find_records_filters_and_logic(tmp_path):
    root = _adapter_root(tmp_path)
    store = FileAdapterResultStore(base_dir=root)
    m = _manifest("m-1", aids=("a", "b"))
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

    hub = _isolated_hub(tmp_path)
    tabular = hub.find_records(manifest_id="m-1", dataset_type="tabular")
    assert len(tabular) == 1
    assert tabular[0].lineage[LINEAGE_ARTIFACT_ID] == "a"

    none = hub.find_records(manifest_id="m-1", dataset_type="tabular", adapter_name="other")
    assert none == []


def test_open_handle_lazy_then_load_roundtrip(tmp_path):
    root = _adapter_root(tmp_path)
    store = FileAdapterResultStore(base_dir=root)
    m = _manifest("m-1", aids=("a",))
    out = AdapterOutput(
        artifact_id="a",
        adapter_name="ad",
        adapter_version="1",
        dataset_type="tabular",
        schema={"k": 1},
        payload=[{"a": 1}],
    )
    saved = store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))
    pid = saved[0].provenance_id

    hub = _isolated_hub(tmp_path)
    h = hub.open_handle(pid)
    assert h.metadata.provenance_id == pid
    assert h.load() == [{"a": 1}]


def test_missing_record_raises(tmp_path):
    hub = _isolated_hub(tmp_path)
    with pytest.raises(MetadataRecordNotFoundError):
        hub.get_record("0" * 64)
    with pytest.raises(MetadataRecordNotFoundError):
        hub.open_handle("0" * 64)


def test_malformed_meta_raises(tmp_path):
    root = _adapter_root(tmp_path)
    (root / "m-1" / ("0" * 64)).mkdir(parents=True)
    (root / "m-1" / ("0" * 64) / "meta.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(MetadataLoadError):
        _isolated_hub(tmp_path)


def test_numpy_payload_roundtrip_if_available(tmp_path):
    np = pytest.importorskip("numpy")
    root = _adapter_root(tmp_path)
    store = FileAdapterResultStore(base_dir=root)
    m = _manifest("m-1", aids=("a",))
    out = AdapterOutput(
        artifact_id="a",
        adapter_name="ad",
        adapter_version="1",
        dataset_type="timeseries",
        schema={"k": 1},
        payload={"signal": np.asarray([1.0, 2.0], dtype=np.float32)},
    )
    pid = store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))[0].provenance_id

    hub = _isolated_hub(tmp_path)
    back = hub.open_handle(pid).load()
    np.testing.assert_array_equal(back["signal"], out.payload["signal"])


def test_derived_not_listed_by_default(tmp_path):
    root = _adapter_root(tmp_path)
    adapter_store = FileAdapterResultStore(base_dir=root)
    m = _manifest("m-1", aids=("a",))
    out = AdapterOutput(
        artifact_id="a",
        adapter_name="ad",
        adapter_version="1",
        dataset_type="tabular",
        schema={"k": 1},
        payload={"x": 1},
    )
    meta_list = adapter_store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))
    pid = meta_list[0].provenance_id
    in_hash = meta_list[0].data_hash

    ar_dir = _analysis_root(tmp_path)
    ar_store = FileAnalysisResultStore(base_dir=ar_dir)
    ar_store.save_result(
        result_type="demo_result",
        module_name="demo_mod",
        module_version="1.0.0",
        input_provenance_ids=[pid],
        input_data_hashes=[in_hash],
        parameters_hash="f" * 64,
        schema={"r": 1},
        payload={"derived": True},
    )

    hub = FileSystemAnalysisHub(base_dir=root, analysis_results_dir=ar_dir)
    assert len(hub.list_records()) == 1
    assert hub.list_records()[0].record_kind == "original"

    merged = hub.list_records(include_derived=True)
    assert len(merged) == 2
    assert merged[0].record_kind == "original"
    assert merged[1].record_kind == "derived"
    assert merged[1].record_type == "demo_result"


def test_find_records_record_kind_and_record_type(tmp_path):
    root = _adapter_root(tmp_path)
    adapter_store = FileAdapterResultStore(base_dir=root)
    m = _manifest("m-1", aids=("a",))
    out = AdapterOutput(
        artifact_id="a",
        adapter_name="ad",
        adapter_version="1",
        dataset_type="tabular",
        schema={"k": 1},
        payload={"x": 1},
    )
    meta_list = adapter_store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))
    pid = meta_list[0].provenance_id
    in_hash = meta_list[0].data_hash

    ar_dir = _analysis_root(tmp_path)
    ar_store = FileAnalysisResultStore(base_dir=ar_dir)
    saved_ar = ar_store.save_result(
        result_type="rtype_a",
        module_name="mod_a",
        module_version="1.0.0",
        input_provenance_ids=[pid],
        input_data_hashes=[in_hash],
        parameters_hash="e" * 64,
        schema={},
        payload={"z": 2},
    )

    hub = FileSystemAnalysisHub(base_dir=root, analysis_results_dir=ar_dir)

    only_derived = hub.find_records(record_kind="derived", include_derived=True)
    assert len(only_derived) == 1
    assert only_derived[0].provenance_id == saved_ar.provenance_id

    by_type = hub.find_records(record_type="rtype_a", include_derived=True)
    assert len(by_type) == 1

    manifest_on_derived = hub.find_records(manifest_id="m-1", include_derived=True)
    assert len(manifest_on_derived) == 1
    assert manifest_on_derived[0].record_kind == "original"


def test_open_handle_derived_payload_roundtrip(tmp_path):
    root = _adapter_root(tmp_path)
    adapter_store = FileAdapterResultStore(base_dir=root)
    m = _manifest("m-1", aids=("a",))
    out = AdapterOutput(
        artifact_id="a",
        adapter_name="ad",
        adapter_version="1",
        dataset_type="tabular",
        schema={"k": 1},
        payload={"x": 1},
    )
    meta_list = adapter_store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))
    pid = meta_list[0].provenance_id
    in_hash = meta_list[0].data_hash

    ar_dir = _analysis_root(tmp_path)
    ar_store = FileAnalysisResultStore(base_dir=ar_dir)
    saved_ar = ar_store.save_result(
        result_type="rtype_a",
        module_name="mod_a",
        module_version="1.0.0",
        input_provenance_ids=[pid],
        input_data_hashes=[in_hash],
        parameters_hash="e" * 64,
        schema={},
        payload={"z": 42},
    )

    hub = FileSystemAnalysisHub(base_dir=root, analysis_results_dir=ar_dir)
    h = hub.open_handle(saved_ar.provenance_id)
    assert h.metadata.record_kind == "derived"
    assert h.load() == {"z": 42}

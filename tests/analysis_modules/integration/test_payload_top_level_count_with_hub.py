"""End-to-end check: adapter outputs on disk → hub → top-level count module → persisted result."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from neurolab.adapters.core.output import AdapterOutput
from neurolab.adapters.pipeline.adapter_pipeline import AdapterPipelineResult
from neurolab.analysis_hub.filesystem import FileSystemAnalysisHub
from neurolab.analysis_modules.implementations.payload_top_level_count import (
    PayloadTopLevelCountModule,
    PayloadTopLevelCountRequest,
)
from neurolab.analysis_modules.orchestrator import run_analysis_module
from neurolab.data_interface.models import Artifact, DataSourceSpec, Manifest
from neurolab.storage.adapter_results.file_store import FileAdapterResultStore
from neurolab.storage.analysis_results.file_store import FileAnalysisResultStore

pytestmark = [pytest.mark.integration]


def _adapter_root(tmp_path: Path) -> Path:
    p = tmp_path / "adapter_outputs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _analysis_root(tmp_path: Path) -> Path:
    p = tmp_path / "analysis_results"
    p.mkdir(parents=True, exist_ok=True)
    return p


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


def _write_demo_adapter_outputs(adapter_dir: Path) -> None:
    adapter_store = FileAdapterResultStore(base_dir=adapter_dir)
    m = _manifest("m-demo", aids=("a", "b"))
    out_a = AdapterOutput(
        artifact_id="a",
        adapter_name="demo_ad",
        adapter_version="1",
        dataset_type="tabular",
        schema={"k": 1},
        payload={"x": 1, "y": 2},
    )
    out_b = AdapterOutput(
        artifact_id="b",
        adapter_name="demo_ad",
        adapter_version="1",
        dataset_type="tabular",
        schema={"k": 2},
        payload={"z": 3},
    )
    adapter_store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out_a, out_b], skipped_artifacts=[]))


def test_payload_top_level_count_through_orchestrator(tmp_path) -> None:
    adapter_dir = _adapter_root(tmp_path)
    analysis_dir = _analysis_root(tmp_path)
    _write_demo_adapter_outputs(adapter_dir)

    hub = FileSystemAnalysisHub(base_dir=adapter_dir, analysis_results_dir=analysis_dir)
    result_store = FileAnalysisResultStore(base_dir=analysis_dir)
    mod = PayloadTopLevelCountModule()

    meta = run_analysis_module(mod, hub, result_store, PayloadTopLevelCountRequest(adapter_name="demo_ad"))

    assert meta.result_type == "payload_top_level_count"
    assert len(meta.input_provenance_ids) == 2
    assert meta.schema["fields"] == {"total_count": "int", "input_count": "int"}
    assert meta.schema["metric"] == "top_level_count_sum"

    payload = result_store.load_payload(meta.provenance_id)
    assert payload == {"total_count": 3, "input_count": 2}

    meta2 = run_analysis_module(mod, hub, result_store, PayloadTopLevelCountRequest(adapter_name="demo_ad"))
    assert meta2.provenance_id == meta.provenance_id


def test_derived_record_visible_in_fresh_hub(tmp_path) -> None:
    adapter_dir = _adapter_root(tmp_path)
    analysis_dir = _analysis_root(tmp_path)
    _write_demo_adapter_outputs(adapter_dir)

    hub = FileSystemAnalysisHub(base_dir=adapter_dir, analysis_results_dir=analysis_dir)
    store = FileAnalysisResultStore(base_dir=analysis_dir)
    module = PayloadTopLevelCountModule()
    request = PayloadTopLevelCountRequest(adapter_name="demo_ad")

    persisted = run_analysis_module(module, hub, store, request)

    hub2 = FileSystemAnalysisHub(base_dir=adapter_dir, analysis_results_dir=analysis_dir)

    originals = hub2.list_records(include_derived=False)
    assert len(originals) == 2
    assert all(r.record_kind == "original" for r in originals)
    assert persisted.provenance_id not in {r.provenance_id for r in originals}

    combined = hub2.list_records(include_derived=True)
    derived_matches = [r for r in combined if r.provenance_id == persisted.provenance_id]
    assert len(derived_matches) == 1
    record = derived_matches[0]
    assert record.record_kind == "derived"
    assert record.record_type == "payload_top_level_count"

    handle = hub2.open_handle(record.provenance_id)
    payload = handle.load()
    assert payload["total_count"] == 3
    assert payload["input_count"] == 2

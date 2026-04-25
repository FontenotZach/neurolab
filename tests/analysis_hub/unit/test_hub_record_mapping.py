from __future__ import annotations

import pytest

from neurolab.analysis_hub.record_mapping import (
    LINEAGE_ADAPTER_NAME,
    LINEAGE_INPUT_DATA_HASHES,
    LINEAGE_INPUT_PROVENANCE_IDS,
    LINEAGE_MANIFEST_ID,
    LINEAGE_MODULE_NAME,
    LINEAGE_MODULE_VERSION,
    LINEAGE_PARAMETERS_HASH,
    LINEAGE_PIPELINE_ORDINAL,
    LINEAGE_ROW_COUNT,
    LINEAGE_SHAPE_SUMMARY,
    hub_record_from_adapter_output,
    hub_record_from_analysis_result,
)
from neurolab.storage.adapter_results.models import META_SCHEMA_V2, PersistedAdapterOutput
from neurolab.storage.analysis_results.models import PersistedAnalysisResult

pytestmark = [pytest.mark.unit]


def test_hub_record_from_adapter_output_maps_core_and_lineage() -> None:
    po = PersistedAdapterOutput(
        meta_schema_version=META_SCHEMA_V2,
        provenance_id="a" * 64,
        data_hash="b" * 64,
        manifest_id="m-1",
        artifact_id="art-1",
        raw_content_hash="c" * 64,
        adapter_name="neuralynx_ncs",
        adapter_version="1.0.0",
        adapter_config_hash="d" * 64,
        schema_fingerprint="e" * 64,
        dataset_type="tabular",
        pipeline_ordinal=3,
        schema={"relative_path": "x.ncs", "format": "neuralynx_ncs"},
        payload_format="neurolab.payload.v1+json",
        payload_path="payload.json",
        created_at="2024-01-01T00:00:00+00:00",
        row_count=100,
        shape_summary={"x": [10, 2]},
    )
    rec = hub_record_from_adapter_output(po)

    assert rec.provenance_id == po.provenance_id
    assert rec.data_hash == po.data_hash
    assert rec.record_kind == "original"
    assert rec.record_type == "tabular"
    assert rec.schema == po.schema
    assert rec.created_at == po.created_at
    assert rec.lineage[LINEAGE_MANIFEST_ID] == "m-1"
    assert rec.lineage[LINEAGE_ADAPTER_NAME] == "neuralynx_ncs"
    assert rec.lineage[LINEAGE_PIPELINE_ORDINAL] == 3
    assert rec.lineage[LINEAGE_ROW_COUNT] == 100
    assert rec.lineage[LINEAGE_SHAPE_SUMMARY] == {"x": [10, 2]}


def test_hub_record_from_adapter_output_omits_optional_lineage_when_none() -> None:
    po = PersistedAdapterOutput(
        meta_schema_version=META_SCHEMA_V2,
        provenance_id="a" * 64,
        data_hash="b" * 64,
        manifest_id="m",
        artifact_id="a1",
        raw_content_hash=None,
        adapter_name="ad",
        adapter_version="0.1",
        adapter_config_hash=None,
        schema_fingerprint="f" * 64,
        dataset_type="x",
        pipeline_ordinal=0,
        schema={},
        payload_format="neurolab.payload.v1+json",
        payload_path="payload.json",
        created_at="",
        row_count=None,
        shape_summary=None,
    )
    rec = hub_record_from_adapter_output(po)
    assert "adapter_config_hash" not in rec.lineage
    assert "raw_content_hash" not in rec.lineage
    assert "row_count" not in rec.lineage
    assert "shape_summary" not in rec.lineage


def test_hub_record_from_analysis_result_maps_core_and_lineage() -> None:
    par = PersistedAnalysisResult(
        provenance_id="p" * 64,
        data_hash="h" * 64,
        result_type="spectrogram_v1",
        module_name="demo_mod",
        module_version="2.0.0",
        input_provenance_ids=["i1" * 32],
        input_data_hashes=["i2" * 32],
        parameters_hash="ph" * 32,
        schema={"units": "Hz"},
        created_at="2025-06-01T12:00:00+00:00",
    )
    rec = hub_record_from_analysis_result(par)

    assert rec.record_kind == "derived"
    assert rec.record_type == "spectrogram_v1"
    assert rec.lineage[LINEAGE_MODULE_NAME] == "demo_mod"
    assert rec.lineage[LINEAGE_MODULE_VERSION] == "2.0.0"
    assert rec.lineage[LINEAGE_INPUT_PROVENANCE_IDS] == ["i1" * 32]
    assert rec.lineage[LINEAGE_INPUT_DATA_HASHES] == ["i2" * 32]
    assert rec.lineage[LINEAGE_PARAMETERS_HASH] == "ph" * 32
    assert rec.schema == {"units": "Hz"}

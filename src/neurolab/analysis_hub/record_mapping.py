"""Map persisted storage models to :class:`~neurolab.analysis_hub.models.HubRecord`.

Lineage keys for ``record_kind == "original"`` (adapter outputs) and
``record_kind == "derived"`` (analysis results) are stable API for callers
that read ``HubRecord.lineage``; do not rename without a migration note.
"""

from __future__ import annotations

from typing import Any

from neurolab.analysis_hub.models import HubRecord
from neurolab.storage.adapter_results.models import PersistedAdapterOutput
from neurolab.storage.analysis_results.models import PersistedAnalysisResult

# --- Original (adapter output) lineage keys ---

LINEAGE_MANIFEST_ID = "manifest_id"
LINEAGE_ARTIFACT_ID = "artifact_id"
LINEAGE_ADAPTER_NAME = "adapter_name"
LINEAGE_ADAPTER_VERSION = "adapter_version"
LINEAGE_ADAPTER_CONFIG_HASH = "adapter_config_hash"
LINEAGE_RAW_CONTENT_HASH = "raw_content_hash"
LINEAGE_SCHEMA_FINGERPRINT = "schema_fingerprint"
LINEAGE_PIPELINE_ORDINAL = "pipeline_ordinal"
LINEAGE_PAYLOAD_FORMAT = "payload_format"
LINEAGE_PAYLOAD_PATH = "payload_path"
LINEAGE_ROW_COUNT = "row_count"
LINEAGE_SHAPE_SUMMARY = "shape_summary"
LINEAGE_META_SCHEMA_VERSION = "meta_schema_version"

# --- Derived (analysis result) lineage keys ---

LINEAGE_MODULE_NAME = "module_name"
LINEAGE_MODULE_VERSION = "module_version"
LINEAGE_INPUT_PROVENANCE_IDS = "input_provenance_ids"
LINEAGE_INPUT_DATA_HASHES = "input_data_hashes"
LINEAGE_PARAMETERS_HASH = "parameters_hash"


def hub_record_from_adapter_output(persisted: PersistedAdapterOutput) -> HubRecord:
    """Build a hub record for one persisted adapter output (``record_kind="original"``)."""

    lineage: dict[str, Any] = {
        LINEAGE_MANIFEST_ID: persisted.manifest_id,
        LINEAGE_ARTIFACT_ID: persisted.artifact_id,
        LINEAGE_ADAPTER_NAME: persisted.adapter_name,
        LINEAGE_ADAPTER_VERSION: persisted.adapter_version,
        LINEAGE_SCHEMA_FINGERPRINT: persisted.schema_fingerprint,
        LINEAGE_PIPELINE_ORDINAL: persisted.pipeline_ordinal,
        LINEAGE_PAYLOAD_FORMAT: persisted.payload_format,
        LINEAGE_PAYLOAD_PATH: persisted.payload_path,
        LINEAGE_META_SCHEMA_VERSION: persisted.meta_schema_version,
    }
    if persisted.adapter_config_hash is not None:
        lineage[LINEAGE_ADAPTER_CONFIG_HASH] = persisted.adapter_config_hash
    if persisted.raw_content_hash is not None:
        lineage[LINEAGE_RAW_CONTENT_HASH] = persisted.raw_content_hash
    if persisted.row_count is not None:
        lineage[LINEAGE_ROW_COUNT] = persisted.row_count
    if persisted.shape_summary is not None:
        lineage[LINEAGE_SHAPE_SUMMARY] = dict(persisted.shape_summary)

    return HubRecord(
        provenance_id=persisted.provenance_id,
        data_hash=persisted.data_hash,
        record_kind="original",
        record_type=persisted.dataset_type,
        schema=dict(persisted.schema),
        created_at=persisted.created_at,
        lineage=lineage,
    )


def hub_record_from_analysis_result(persisted: PersistedAnalysisResult) -> HubRecord:
    """Build a hub record for one persisted analysis result (``record_kind="derived"``)."""

    lineage: dict[str, Any] = {
        LINEAGE_MODULE_NAME: persisted.module_name,
        LINEAGE_MODULE_VERSION: persisted.module_version,
        LINEAGE_INPUT_PROVENANCE_IDS: list(persisted.input_provenance_ids),
        LINEAGE_INPUT_DATA_HASHES: list(persisted.input_data_hashes),
        LINEAGE_PARAMETERS_HASH: persisted.parameters_hash,
    }

    return HubRecord(
        provenance_id=persisted.provenance_id,
        data_hash=persisted.data_hash,
        record_kind="derived",
        record_type=persisted.result_type,
        schema=dict(persisted.schema),
        created_at=persisted.created_at,
        lineage=lineage,
    )

"""Models for analysis hub (v1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from neurolab.analysis_hub.errors import PayloadNotFoundError
from neurolab.storage.adapter_results import PayloadDecodeError, decode_payload_from_record

RecordKind = Literal["original", "derived"]


@dataclass(frozen=True, slots=True)
class HubRecord:
    """
    Unified metadata-only view for catalog records (adapter outputs and analysis results).

    Kind-specific fields live in ``lineage``; see :mod:`neurolab.analysis_hub.record_mapping`
    for documented lineage keys per ``record_kind``.
    """

    provenance_id: str
    data_hash: str
    record_kind: RecordKind
    record_type: str
    schema: dict[str, Any]
    created_at: str
    lineage: dict[str, Any]


@dataclass(frozen=True, slots=True)
class OutputMetadataRecord:
    """
    Metadata-only record for one persisted adapter output.

    Mirrors persisted ``meta.json`` (v2): ``data_hash`` for computational equivalence,
    ``provenance_id`` for lineage and addressing records.
    """

    provenance_id: str
    data_hash: str
    manifest_id: str
    artifact_id: str
    raw_content_hash: str | None
    adapter_name: str
    adapter_version: str
    adapter_config_hash: str | None
    schema_fingerprint: str
    dataset_type: str
    pipeline_ordinal: int
    schema: dict[str, Any]
    payload_format: str
    payload_path: str
    created_at: str
    meta_schema_version: int | None = None
    row_count: int | None = None
    shape_summary: dict[str, list[int]] | None = None


@dataclass(frozen=True, slots=True)
class PayloadDescriptor:
    provenance_id: str
    manifest_id: str | None
    record_dir: Path
    meta_json_path: Path
    primary_payload_path: Path


@dataclass(slots=True)
class AnalysisHandle:
    metadata: HubRecord
    payload: PayloadDescriptor

    def load(self) -> Any:
        """
        Fully load payload into memory.

        v1 delegates decoding to the existing adapter-results payload codec.
        """

        try:
            return decode_payload_from_record(self.payload.record_dir)
        except (FileNotFoundError, PayloadDecodeError) as e:
            raise PayloadNotFoundError(f"Payload not found/decodable for provenance_id={self.metadata.provenance_id!r}") from e

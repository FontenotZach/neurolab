"""Models for analysis hub (v1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neurolab.analysis_hub.errors import PayloadNotFoundError
from neurolab.storage.adapter_results import PayloadDecodeError, decode_payload_from_record


@dataclass(frozen=True, slots=True)
class OutputMetadataRecord:
    """
    Metadata-only record for one persisted adapter output.

    This mirrors the `meta.json` schema written by `PersistedAdapterOutput.to_dict()`.
    """

    stored_output_id: str
    manifest_id: str
    artifact_id: str
    adapter_name: str
    adapter_version: str
    dataset_type: str
    pipeline_ordinal: int
    schema: dict[str, Any]
    payload_format: str
    payload_path: str
    row_count: int | None = None
    shape_summary: dict[str, list[int]] | None = None


@dataclass(frozen=True, slots=True)
class PayloadDescriptor:
    stored_output_id: str
    manifest_id: str
    record_dir: Path
    meta_json_path: Path
    primary_payload_path: Path


@dataclass(slots=True)
class AnalysisHandle:
    metadata: OutputMetadataRecord
    payload: PayloadDescriptor

    def load(self) -> Any:
        """
        Fully load payload into memory.

        v1 delegates decoding to the existing adapter-results payload codec.
        """

        try:
            return decode_payload_from_record(self.payload.record_dir)
        except (FileNotFoundError, PayloadDecodeError) as e:
            raise PayloadNotFoundError(f"Payload not found/decodable for stored_output_id={self.metadata.stored_output_id!r}") from e


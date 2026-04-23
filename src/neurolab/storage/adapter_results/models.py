"""Persisted adapter output metadata (v1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PAYLOAD_FORMAT_V1 = "neurolab.payload.v1+json"
PRIMARY_PAYLOAD_REL_PATH = "payload.json"


@dataclass(frozen=True)
class PersistedAdapterOutput:
    """
    Metadata for one stored adapter output. Temporal provenance stays on Manifest only.
    row_count and shape_summary are optional hints for tooling; decoders must not require them.
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "stored_output_id": self.stored_output_id,
            "manifest_id": self.manifest_id,
            "artifact_id": self.artifact_id,
            "adapter_name": self.adapter_name,
            "adapter_version": self.adapter_version,
            "dataset_type": self.dataset_type,
            "pipeline_ordinal": self.pipeline_ordinal,
            "schema": self.schema,
            "payload_format": self.payload_format,
            "payload_path": self.payload_path,
            "row_count": self.row_count,
            "shape_summary": self.shape_summary,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PersistedAdapterOutput:
        return cls(
            stored_output_id=str(d["stored_output_id"]),
            manifest_id=str(d["manifest_id"]),
            artifact_id=str(d["artifact_id"]),
            adapter_name=str(d["adapter_name"]),
            adapter_version=str(d["adapter_version"]),
            dataset_type=str(d["dataset_type"]),
            pipeline_ordinal=int(d["pipeline_ordinal"]),
            schema=dict(d["schema"]),
            payload_format=str(d["payload_format"]),
            payload_path=str(d["payload_path"]),
            row_count=None if d.get("row_count") is None else int(d["row_count"]),
            shape_summary=None if d.get("shape_summary") is None else _coerce_shape_summary(d["shape_summary"]),
        )


def _coerce_shape_summary(raw: Any) -> dict[str, list[int]]:
    if not isinstance(raw, dict):
        raise TypeError("shape_summary must be a dict")
    out: dict[str, list[int]] = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            raise TypeError("shape_summary keys must be str")
        if not isinstance(v, list):
            raise TypeError("shape_summary values must be list of int")
        out[k] = [int(x) for x in v]
    return out

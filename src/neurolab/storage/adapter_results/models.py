"""Persisted adapter output metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neurolab.storage.adapter_results.ids import schema_fingerprint as compute_schema_fp

PAYLOAD_FORMAT_V1 = "neurolab.payload.v1+json"
PRIMARY_PAYLOAD_REL_PATH = "payload.json"
META_SCHEMA_V2 = 2


@dataclass(frozen=True)
class PersistedAdapterOutput:
    """
    Metadata for one stored adapter output.

    ``data_hash`` identifies standardized payload content (computational equivalence).
    ``provenance_id`` identifies lineage (unique directory name under each manifest).
    """

    meta_schema_version: int
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
    row_count: int | None = None
    shape_summary: dict[str, list[int]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta_schema_version": self.meta_schema_version,
            "provenance_id": self.provenance_id,
            "data_hash": self.data_hash,
            "manifest_id": self.manifest_id,
            "artifact_id": self.artifact_id,
            "raw_content_hash": self.raw_content_hash,
            "adapter_name": self.adapter_name,
            "adapter_version": self.adapter_version,
            "adapter_config_hash": self.adapter_config_hash,
            "schema_fingerprint": self.schema_fingerprint,
            "dataset_type": self.dataset_type,
            "pipeline_ordinal": self.pipeline_ordinal,
            "schema": self.schema,
            "payload_format": self.payload_format,
            "payload_path": self.payload_path,
            "created_at": self.created_at,
            "row_count": self.row_count,
            "shape_summary": self.shape_summary,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PersistedAdapterOutput:
        ver = int(d.get("meta_schema_version", 1))
        if ver >= META_SCHEMA_V2 or ("provenance_id" in d and "data_hash" in d):
            return cls._from_v2(d)
        return cls._from_legacy_v1(d)

    @classmethod
    def _from_v2(cls, d: dict[str, Any]) -> PersistedAdapterOutput:
        schema = dict(d["schema"])
        sf = str(d.get("schema_fingerprint") or compute_schema_fp(schema))
        return cls(
            meta_schema_version=int(d.get("meta_schema_version", META_SCHEMA_V2)),
            provenance_id=str(d["provenance_id"]),
            data_hash=str(d["data_hash"]),
            manifest_id=str(d["manifest_id"]),
            artifact_id=str(d["artifact_id"]),
            raw_content_hash=None if d.get("raw_content_hash") is None else str(d["raw_content_hash"]),
            adapter_name=str(d["adapter_name"]),
            adapter_version=str(d["adapter_version"]),
            adapter_config_hash=None if d.get("adapter_config_hash") is None else str(d["adapter_config_hash"]),
            schema_fingerprint=sf,
            dataset_type=str(d["dataset_type"]),
            pipeline_ordinal=int(d["pipeline_ordinal"]),
            schema=schema,
            payload_format=str(d["payload_format"]),
            payload_path=str(d["payload_path"]),
            created_at=str(d.get("created_at", "")),
            row_count=None if d.get("row_count") is None else int(d["row_count"]),
            shape_summary=None if d.get("shape_summary") is None else _coerce_shape_summary(d["shape_summary"]),
        )

    @classmethod
    def _from_legacy_v1(cls, d: dict[str, Any]) -> PersistedAdapterOutput:
        """Legacy meta.json used a single hex id (content fingerprint) as directory name."""
        legacy_id = str(d["stored_output_id"])
        schema = dict(d["schema"])
        sf = compute_schema_fp(schema)
        return cls(
            meta_schema_version=1,
            provenance_id=legacy_id,
            data_hash=legacy_id,
            manifest_id=str(d["manifest_id"]),
            artifact_id=str(d["artifact_id"]),
            raw_content_hash=None,
            adapter_name=str(d["adapter_name"]),
            adapter_version=str(d["adapter_version"]),
            adapter_config_hash=None,
            schema_fingerprint=sf,
            dataset_type=str(d["dataset_type"]),
            pipeline_ordinal=int(d["pipeline_ordinal"]),
            schema=schema,
            payload_format=str(d["payload_format"]),
            payload_path=str(d["payload_path"]),
            created_at=str(d.get("created_at", "")),
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

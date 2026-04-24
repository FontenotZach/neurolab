"""Filesystem-backed analysis hub implementation (v1)."""

from __future__ import annotations

import json
from pathlib import Path

from neurolab.analysis_hub.errors import MetadataLoadError, MetadataRecordNotFoundError
from neurolab.analysis_hub.models import AnalysisHandle, OutputMetadataRecord, PayloadDescriptor
from neurolab.storage.adapter_results.models import PersistedAdapterOutput

META_FILENAME = "meta.json"


def _default_adapter_outputs_dir() -> Path:
    # Mirrors FileAdapterResultStore default without instantiating it.
    return Path.home() / ".neurolab" / "data" / "adapter_outputs"


class FileSystemAnalysisHub:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir if base_dir is not None else _default_adapter_outputs_dir()
        self._records_by_id: dict[str, OutputMetadataRecord] = {}
        self._payloads_by_id: dict[str, PayloadDescriptor] = {}
        self._ordered_ids: list[str] = []
        self._load_registry()

    def list_records(self) -> list[OutputMetadataRecord]:
        return [self._records_by_id[pid] for pid in self._ordered_ids]

    def get_record(self, provenance_id: str) -> OutputMetadataRecord:
        rec = self._records_by_id.get(provenance_id)
        if rec is None:
            raise MetadataRecordNotFoundError(f"provenance_id not found: {provenance_id!r}")
        return rec

    def has_record(self, provenance_id: str) -> bool:
        return provenance_id in self._records_by_id

    def find_records(
        self,
        *,
        manifest_id: str | None = None,
        artifact_id: str | None = None,
        adapter_name: str | None = None,
        adapter_version: str | None = None,
        dataset_type: str | None = None,
        payload_format: str | None = None,
        data_hash: str | None = None,
    ) -> list[OutputMetadataRecord]:
        def _match(r: OutputMetadataRecord) -> bool:
            if manifest_id is not None and r.manifest_id != manifest_id:
                return False
            if artifact_id is not None and r.artifact_id != artifact_id:
                return False
            if adapter_name is not None and r.adapter_name != adapter_name:
                return False
            if adapter_version is not None and r.adapter_version != adapter_version:
                return False
            if dataset_type is not None and r.dataset_type != dataset_type:
                return False
            if payload_format is not None and r.payload_format != payload_format:
                return False
            if data_hash is not None and r.data_hash != data_hash:
                return False
            return True

        out: list[OutputMetadataRecord] = []
        for pid in self._ordered_ids:
            r = self._records_by_id[pid]
            if _match(r):
                out.append(r)
        return out

    def open_handle(self, provenance_id: str) -> AnalysisHandle:
        rec = self.get_record(provenance_id)
        payload = self._payloads_by_id[provenance_id]
        return AnalysisHandle(metadata=rec, payload=payload)

    def open_handles(
        self,
        *,
        manifest_id: str | None = None,
        artifact_id: str | None = None,
        adapter_name: str | None = None,
        adapter_version: str | None = None,
        dataset_type: str | None = None,
        payload_format: str | None = None,
        data_hash: str | None = None,
    ) -> list[AnalysisHandle]:
        records = self.find_records(
            manifest_id=manifest_id,
            artifact_id=artifact_id,
            adapter_name=adapter_name,
            adapter_version=adapter_version,
            dataset_type=dataset_type,
            payload_format=payload_format,
            data_hash=data_hash,
        )
        return [AnalysisHandle(metadata=r, payload=self._payloads_by_id[r.provenance_id]) for r in records]

    def _load_registry(self) -> None:
        self._records_by_id.clear()
        self._payloads_by_id.clear()
        self._ordered_ids.clear()

        if not self.base_dir.is_dir():
            return

        found: list[tuple[tuple[object, ...], str]] = []

        for manifest_dir in sorted(self.base_dir.iterdir(), key=lambda p: p.name):
            if not manifest_dir.is_dir():
                continue
            for record_dir in sorted(manifest_dir.iterdir(), key=lambda p: p.name):
                if not record_dir.is_dir():
                    continue
                meta_path = record_dir / META_FILENAME
                if not meta_path.is_file():
                    continue

                rec = self._build_record(meta_path)
                payload = self._build_payload_descriptor(rec, record_dir)

                pid = rec.provenance_id
                self._records_by_id[pid] = rec
                self._payloads_by_id[pid] = payload

                order_key = (
                    rec.manifest_id,
                    rec.pipeline_ordinal,
                    rec.artifact_id,
                    rec.adapter_name,
                    rec.provenance_id,
                )
                found.append((order_key, pid))

        found.sort(key=lambda x: x[0])
        self._ordered_ids = [pid for _, pid in found]

    def _build_record(self, meta_path: Path) -> OutputMetadataRecord:
        try:
            raw = json.loads(meta_path.read_text(encoding="utf-8"))
            po = PersistedAdapterOutput.from_dict(raw)
        except Exception as e:  # noqa: BLE001 - intentionally wraps parsing/coercion failures
            raise MetadataLoadError(f"Malformed metadata at {str(meta_path)!r}") from e

        return OutputMetadataRecord(
            provenance_id=po.provenance_id,
            data_hash=po.data_hash,
            manifest_id=po.manifest_id,
            artifact_id=po.artifact_id,
            raw_content_hash=po.raw_content_hash,
            adapter_name=po.adapter_name,
            adapter_version=po.adapter_version,
            adapter_config_hash=po.adapter_config_hash,
            schema_fingerprint=po.schema_fingerprint,
            dataset_type=po.dataset_type,
            pipeline_ordinal=po.pipeline_ordinal,
            schema=po.schema,
            payload_format=po.payload_format,
            payload_path=po.payload_path,
            created_at=po.created_at,
            meta_schema_version=po.meta_schema_version,
            row_count=po.row_count,
            shape_summary=po.shape_summary,
        )

    def _build_payload_descriptor(self, rec: OutputMetadataRecord, record_dir: Path) -> PayloadDescriptor:
        meta_json_path = record_dir / META_FILENAME
        primary_payload_path = record_dir / rec.payload_path
        return PayloadDescriptor(
            provenance_id=rec.provenance_id,
            manifest_id=rec.manifest_id,
            record_dir=record_dir,
            meta_json_path=meta_json_path,
            primary_payload_path=primary_payload_path,
        )

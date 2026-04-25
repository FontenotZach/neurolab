"""Filesystem-backed analysis hub implementation (v1)."""

from __future__ import annotations

import json
from pathlib import Path

from neurolab.analysis_hub.errors import MetadataLoadError, MetadataRecordNotFoundError
from neurolab.analysis_hub.models import AnalysisHandle, HubRecord, PayloadDescriptor, RecordKind
from neurolab.analysis_hub.record_mapping import (
    LINEAGE_ADAPTER_NAME,
    LINEAGE_ADAPTER_VERSION,
    LINEAGE_ARTIFACT_ID,
    LINEAGE_MANIFEST_ID,
    LINEAGE_PAYLOAD_FORMAT,
    LINEAGE_PIPELINE_ORDINAL,
    hub_record_from_adapter_output,
    hub_record_from_analysis_result,
)
from neurolab.storage.adapter_results.models import PRIMARY_PAYLOAD_REL_PATH, PersistedAdapterOutput
from neurolab.storage.analysis_results.models import PersistedAnalysisResult

META_FILENAME = "meta.json"


def _default_adapter_outputs_dir() -> Path:
    # Mirrors FileAdapterResultStore default without instantiating it.
    return Path.home() / ".neurolab" / "data" / "adapter_outputs"


def _default_analysis_results_dir() -> Path:
    return Path.home() / ".neurolab" / "data" / "analysis_results"


def _is_hex64(s: str) -> bool:
    if len(s) != 64:
        return False
    try:
        int(s, 16)
    except ValueError:
        return False
    return True


class FileSystemAnalysisHub:
    """
    Unified catalog over persisted adapter outputs and analysis results.

    ``base_dir`` must be the adapter store root (``.../adapter_outputs``): each
    child directory is treated as a ``manifest_id``. Keep analysis results on
    a separate path (``analysis_results_dir``), not nested under ``base_dir``.

    Default :meth:`list_records` / :meth:`find_records` surface **original**
    (adapter) records only; pass ``include_derived=True`` to include analysis
    results. Ordering is deterministic: all originals (existing adapter sort),
    then all derived records sorted by ``provenance_id``.
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        *,
        analysis_results_dir: Path | None = None,
    ) -> None:
        self.base_dir = base_dir if base_dir is not None else _default_adapter_outputs_dir()
        self.analysis_results_dir = analysis_results_dir if analysis_results_dir is not None else _default_analysis_results_dir()
        self._records_by_key: dict[tuple[RecordKind, str], HubRecord] = {}
        self._payload_by_key: dict[tuple[RecordKind, str], PayloadDescriptor] = {}
        self._ordered_keys: list[tuple[RecordKind, str]] = []
        self._load_registry()

    def list_records(self, *, include_derived: bool = False) -> list[HubRecord]:
        out: list[HubRecord] = []
        for key in self._ordered_keys:
            if not include_derived and key[0] != "original":
                continue
            out.append(self._records_by_key[key])
        return out

    def _resolve_key(self, provenance_id: str) -> tuple[RecordKind, str] | None:
        okey: tuple[RecordKind, str] = ("original", provenance_id)
        if okey in self._records_by_key:
            return okey
        dkey: tuple[RecordKind, str] = ("derived", provenance_id)
        if dkey in self._records_by_key:
            return dkey
        return None

    def get_record(self, provenance_id: str) -> HubRecord:
        key = self._resolve_key(provenance_id)
        if key is None:
            raise MetadataRecordNotFoundError(f"provenance_id not found: {provenance_id!r}")
        return self._records_by_key[key]

    def has_record(self, provenance_id: str) -> bool:
        return self._resolve_key(provenance_id) is not None

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
        record_kind: RecordKind | None = None,
        record_type: str | None = None,
        include_derived: bool = False,
    ) -> list[HubRecord]:
        def _kind_in_scope(kind: RecordKind) -> bool:
            if record_kind is not None:
                return kind == record_kind
            if include_derived:
                return True
            return kind == "original"

        def _match(r: HubRecord) -> bool:
            if record_type is not None and r.record_type != record_type:
                return False
            if data_hash is not None and r.data_hash != data_hash:
                return False

            lg = r.lineage
            if manifest_id is not None:
                if r.record_kind != "original":
                    return False
                if lg.get(LINEAGE_MANIFEST_ID) != manifest_id:
                    return False
            if artifact_id is not None:
                if r.record_kind != "original":
                    return False
                if lg.get(LINEAGE_ARTIFACT_ID) != artifact_id:
                    return False
            if adapter_name is not None:
                if r.record_kind != "original":
                    return False
                if lg.get(LINEAGE_ADAPTER_NAME) != adapter_name:
                    return False
            if adapter_version is not None:
                if r.record_kind != "original":
                    return False
                if lg.get(LINEAGE_ADAPTER_VERSION) != adapter_version:
                    return False
            if dataset_type is not None and r.record_type != dataset_type:
                return False
            if payload_format is not None:
                if r.record_kind != "original":
                    return False
                if lg.get(LINEAGE_PAYLOAD_FORMAT) != payload_format:
                    return False
            return True

        out: list[HubRecord] = []
        for key in self._ordered_keys:
            kind, _pid = key
            if not _kind_in_scope(kind):
                continue
            r = self._records_by_key[key]
            if _match(r):
                out.append(r)
        return out

    def _payload_for(self, rec: HubRecord) -> PayloadDescriptor:
        key: tuple[RecordKind, str] = (rec.record_kind, rec.provenance_id)
        return self._payload_by_key[key]

    def open_handle(self, provenance_id: str) -> AnalysisHandle:
        rec = self.get_record(provenance_id)
        return AnalysisHandle(metadata=rec, payload=self._payload_for(rec))

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
        record_kind: RecordKind | None = None,
        record_type: str | None = None,
        include_derived: bool = False,
    ) -> list[AnalysisHandle]:
        records = self.find_records(
            manifest_id=manifest_id,
            artifact_id=artifact_id,
            adapter_name=adapter_name,
            adapter_version=adapter_version,
            dataset_type=dataset_type,
            payload_format=payload_format,
            data_hash=data_hash,
            record_kind=record_kind,
            record_type=record_type,
            include_derived=include_derived,
        )
        return [AnalysisHandle(metadata=r, payload=self._payload_for(r)) for r in records]

    def _load_registry(self) -> None:
        self._records_by_key.clear()
        self._payload_by_key.clear()
        self._ordered_keys.clear()

        original_entries: list[tuple[tuple[object, ...], tuple[RecordKind, str], HubRecord, PayloadDescriptor]] = []

        if self.base_dir.is_dir():
            for manifest_dir in sorted(self.base_dir.iterdir(), key=lambda p: p.name):
                if not manifest_dir.is_dir():
                    continue
                for record_dir in sorted(manifest_dir.iterdir(), key=lambda p: p.name):
                    if not record_dir.is_dir():
                        continue
                    meta_path = record_dir / META_FILENAME
                    if not meta_path.is_file():
                        continue

                    try:
                        raw = json.loads(meta_path.read_text(encoding="utf-8"))
                        po = PersistedAdapterOutput.from_dict(raw)
                    except Exception as e:  # noqa: BLE001 - intentionally wraps parsing/coercion failures
                        raise MetadataLoadError(f"Malformed metadata at {str(meta_path)!r}") from e

                    rec = hub_record_from_adapter_output(po)
                    key: tuple[RecordKind, str] = ("original", rec.provenance_id)
                    payload = self._build_payload_descriptor_adapter(po, record_dir)
                    order_key = (
                        rec.lineage[LINEAGE_MANIFEST_ID],
                        rec.lineage[LINEAGE_PIPELINE_ORDINAL],
                        rec.lineage[LINEAGE_ARTIFACT_ID],
                        rec.lineage[LINEAGE_ADAPTER_NAME],
                        rec.provenance_id,
                    )
                    original_entries.append((order_key, key, rec, payload))

        original_entries.sort(key=lambda x: x[0])
        for _ok, key, rec, payload in original_entries:
            self._records_by_key[key] = rec
            self._payload_by_key[key] = payload

        derived_entries: list[tuple[str, tuple[RecordKind, str], HubRecord, PayloadDescriptor]] = []

        if self.analysis_results_dir.is_dir():
            for record_dir in sorted(self.analysis_results_dir.iterdir(), key=lambda p: p.name):
                if not record_dir.is_dir() or not _is_hex64(record_dir.name):
                    continue
                meta_path = record_dir / META_FILENAME
                if not meta_path.is_file():
                    continue
                try:
                    raw = json.loads(meta_path.read_text(encoding="utf-8"))
                    par = PersistedAnalysisResult.from_dict(raw)
                except Exception as e:  # noqa: BLE001
                    raise MetadataLoadError(f"Malformed analysis result metadata at {str(meta_path)!r}") from e

                rec = hub_record_from_analysis_result(par)
                dkey: tuple[RecordKind, str] = ("derived", rec.provenance_id)
                payload = self._build_payload_descriptor_derived(record_dir, rec)
                derived_entries.append((rec.provenance_id, dkey, rec, payload))

        derived_entries.sort(key=lambda x: x[0])
        for _pid, dkey, rec, payload in derived_entries:
            self._records_by_key[dkey] = rec
            self._payload_by_key[dkey] = payload

        self._ordered_keys = [e[1] for e in original_entries] + [e[1] for e in derived_entries]

    def _build_payload_descriptor_adapter(self, po: PersistedAdapterOutput, record_dir: Path) -> PayloadDescriptor:
        meta_json_path = record_dir / META_FILENAME
        primary_payload_path = record_dir / po.payload_path
        return PayloadDescriptor(
            provenance_id=po.provenance_id,
            manifest_id=po.manifest_id,
            record_dir=record_dir,
            meta_json_path=meta_json_path,
            primary_payload_path=primary_payload_path,
        )

    def _build_payload_descriptor_derived(self, record_dir: Path, rec: HubRecord) -> PayloadDescriptor:
        meta_json_path = record_dir / META_FILENAME
        primary_payload_path = record_dir / PRIMARY_PAYLOAD_REL_PATH
        return PayloadDescriptor(
            provenance_id=rec.provenance_id,
            manifest_id=None,
            record_dir=record_dir,
            meta_json_path=meta_json_path,
            primary_payload_path=primary_payload_path,
        )

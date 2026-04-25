"""Interfaces for analysis hub."""

from __future__ import annotations

from typing import Protocol

from neurolab.analysis_hub.models import AnalysisHandle, HubRecord, RecordKind


class AnalysisHub(Protocol):
    def list_records(self, *, include_derived: bool = False) -> list[HubRecord]: ...

    def get_record(self, provenance_id: str) -> HubRecord: ...

    def has_record(self, provenance_id: str) -> bool: ...

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
    ) -> list[HubRecord]: ...

    def open_handle(self, provenance_id: str) -> AnalysisHandle: ...

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
    ) -> list[AnalysisHandle]: ...

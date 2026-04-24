"""Interfaces for analysis hub."""

from __future__ import annotations

from typing import Protocol

from neurolab.analysis_hub.models import AnalysisHandle, OutputMetadataRecord


class AnalysisHub(Protocol):
    def list_records(self) -> list[OutputMetadataRecord]: ...

    def get_record(self, provenance_id: str) -> OutputMetadataRecord: ...

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
    ) -> list[OutputMetadataRecord]: ...

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
    ) -> list[AnalysisHandle]: ...

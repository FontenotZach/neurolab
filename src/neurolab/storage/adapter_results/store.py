"""Storage protocol for persisted adapter pipeline results."""

from __future__ import annotations

from typing import Any, Protocol

from neurolab.adapters.pipeline.adapter_pipeline import AdapterPipelineResult
from neurolab.data_interface.models import Manifest
from neurolab.storage.adapter_results.models import PersistedAdapterOutput


class AdapterResultStore(Protocol):
    def save_pipeline_result(self, manifest: Manifest, result: AdapterPipelineResult) -> list[PersistedAdapterOutput]:
        """Persist all outputs for this manifest. Overwrites records with the same provenance_id."""

    def list_outputs(self, manifest_id: str) -> list[PersistedAdapterOutput]:
        """Return metadata for all stored outputs, ordered by pipeline_ordinal (authoritative: meta.json scan)."""

    def load_metadata(self, manifest_id: str, provenance_id: str) -> PersistedAdapterOutput:
        """Load meta.json for one record."""

    def load_payload(self, manifest_id: str, provenance_id: str) -> Any:
        """Decode payload from record directory (payload.json + arrays)."""

    def delete_manifest_outputs(self, manifest_id: str) -> None:
        """Remove all stored outputs for a manifest."""

"""Supporting models for analysis modules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalysisModuleDescription:
    """Informational metadata describing an analysis module."""

    module_name: str
    module_version: str
    summary: str
    supported_dataset_types: tuple[str, ...] = ()
    supported_adapter_names: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SelectionResult:
    """
    Result of metadata-only selection against the Analysis Hub.

    ``selected_provenance_ids`` preserves hub ordering for considered records.
    Decide computational equivalence using ``data_hash`` on hub metadata, not
    ``provenance_id`` (lineage differs when adapters differ).
    """

    module_name: str
    selected_provenance_ids: tuple[str, ...]
    total_candidates_seen: int

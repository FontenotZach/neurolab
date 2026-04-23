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

    `selected_stored_output_ids` must preserve the hub's ordering for the records
    considered during selection (no independent sorting).
    """

    module_name: str
    selected_stored_output_ids: tuple[str, ...]
    total_candidates_seen: int


"""Supporting models for analysis modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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


@dataclass(frozen=True, slots=True)
class AnalysisRunResult:
    """
    Unpersisted output of :meth:`~neurolab.analysis_modules.base.AnalysisModule.run`.

    Callers may pass these fields into :meth:`neurolab.storage.analysis_results.file_store.FileAnalysisResultStore.save_result`.
    """

    module_name: str
    module_version: str
    result_type: str
    input_provenance_ids: list[str]
    input_data_hashes: list[str]
    parameters_hash: str
    schema: dict[str, Any]
    payload: Any
    warnings: list[str] = field(default_factory=list)

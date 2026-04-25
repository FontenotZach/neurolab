"""Minimal single-run orchestration for analysis modules."""

from __future__ import annotations

from typing import TypeVar

from neurolab.analysis_hub.interfaces import AnalysisHub
from neurolab.analysis_modules.base import AnalysisModule
from neurolab.analysis_modules.models import SelectionResult
from neurolab.storage.analysis_results.file_store import FileAnalysisResultStore
from neurolab.storage.analysis_results.models import PersistedAnalysisResult

RequestT = TypeVar("RequestT")


def run_analysis_module(
    module: AnalysisModule[RequestT],
    hub: AnalysisHub,
    store: FileAnalysisResultStore,
    request: RequestT,
    *,
    selection: SelectionResult | None = None,
) -> PersistedAnalysisResult:
    """
    Resolve selection (via ``module.select`` when ``selection`` is ``None``),
    call ``module.run`` once, and persist via ``store.save_result``.

    This function does not mutate ``hub``, the module instance, or
    ``AnalysisRunResult`` instances. The only persistence / catalog write is
    ``FileAnalysisResultStore.save_result``.

    ``selected_provenance_ids`` order is passed through to ``run`` unchanged.
    """
    if selection is not None and selection.module_name != module.module_name:
        raise ValueError(f"selection.module_name {selection.module_name!r} does not match module.module_name {module.module_name!r}")

    resolved: SelectionResult = selection if selection is not None else module.select(hub, request)

    run_result = module.run(hub, request, resolved)

    if run_result.module_name != module.module_name:
        raise ValueError(f"run_result.module_name {run_result.module_name!r} does not match module.module_name {module.module_name!r}")
    if run_result.module_version != module.module_version:
        raise ValueError(f"run_result.module_version {run_result.module_version!r} does not match module.module_version {module.module_version!r}")

    if len(run_result.input_provenance_ids) != len(run_result.input_data_hashes):
        raise ValueError(
            "input_provenance_ids and input_data_hashes must have the same length "
            f"({len(run_result.input_provenance_ids)} vs {len(run_result.input_data_hashes)})"
        )

    return store.save_result(
        result_type=run_result.result_type,
        module_name=run_result.module_name,
        module_version=run_result.module_version,
        input_provenance_ids=list(run_result.input_provenance_ids),
        input_data_hashes=list(run_result.input_data_hashes),
        parameters_hash=run_result.parameters_hash,
        schema=dict(run_result.schema),
        payload=run_result.payload,
    )

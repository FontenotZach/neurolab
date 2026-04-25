"""Base contract for analysis modules that consume the Analysis Hub."""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar

from neurolab.analysis_hub.interfaces import AnalysisHub
from neurolab.analysis_modules.models import AnalysisModuleDescription, AnalysisRunResult, SelectionResult

RequestT = TypeVar("RequestT")


class AnalysisModule(Protocol, Generic[RequestT]):
    """
    Contract for analysis modules.

    - `describe()` is pure informational metadata and must not touch the hub.
    - `select()` is metadata-only: it must not load payloads, and it must preserve
      hub ordering in `SelectionResult.selected_provenance_ids`.
    - `run()` performs the actual work and may load payloads via the hub.
      It returns an unpersisted :class:`~neurolab.analysis_modules.models.AnalysisRunResult`;
      persistence is the caller's responsibility (e.g. ``FileAnalysisResultStore``).

    Selection for ``run()``:
    - If ``selection`` is ``None``, the module may call ``select(hub, request)`` internally.
    - If ``selection`` is provided, the module must use that selection (must not ignore it).
    """

    module_name: str
    module_version: str

    def describe(self) -> AnalysisModuleDescription: ...

    def select(self, hub: AnalysisHub, request: RequestT) -> SelectionResult: ...

    def run(
        self,
        hub: AnalysisHub,
        request: RequestT,
        selection: SelectionResult | None = None,
    ) -> AnalysisRunResult: ...

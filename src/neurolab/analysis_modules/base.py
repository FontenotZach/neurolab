"""Base contract for analysis modules that consume the Analysis Hub."""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar

from neurolab.analysis_hub.interfaces import AnalysisHub
from neurolab.analysis_modules.models import AnalysisModuleDescription, SelectionResult

RequestT = TypeVar("RequestT")
ResultT = TypeVar("ResultT")


class AnalysisModule(Protocol, Generic[RequestT, ResultT]):
    """
    Contract for analysis modules.

    - `describe()` is pure informational metadata and must not touch the hub.
    - `select()` is metadata-only: it must not load payloads, and it must preserve
      hub ordering in `SelectionResult.selected_stored_output_ids`.
    - `run()` performs the actual work and may load payloads via the hub.
    """

    module_name: str
    module_version: str

    def describe(self) -> AnalysisModuleDescription: ...

    def select(self, hub: AnalysisHub, request: RequestT) -> SelectionResult: ...

    def run(self, hub: AnalysisHub, request: RequestT) -> ResultT: ...


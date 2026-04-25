"""Base contract for builders that group persisted outputs in the Analysis Hub."""

from __future__ import annotations

from typing import Generic, Protocol, TypeVar

from neurolab.analysis_hub.interfaces import AnalysisHub
from neurolab.output_groups.models import OutputGroup, OutputGroupBuilderDescription, OutputGroupSelectionResult

RequestT = TypeVar("RequestT")


class OutputGroupBuilder(Protocol, Generic[RequestT]):
    """
    Contract for OutputGroup builders.

    Important boundary:
    OutputGroupBuilder is not an analysis module. It catalogs logical relationships
    among existing persisted outputs.

    - `describe()` is informational only.
    - `select()` is metadata-only: it browses hub metadata and returns selected
      persisted output addressing ids (typically :attr:`~neurolab.analysis_hub.models.HubRecord.provenance_id`
      for ``record_kind == 'original'`` records from ``hub.list_records()``),
      preserving hub ordering.
    - `build()` creates OutputGroup objects from selected metadata, must not load
      payloads, and must not mutate adapter outputs. It may create parent-child
      relationships using `parent_group_id`.
    """

    builder_name: str
    builder_version: str

    def describe(self) -> OutputGroupBuilderDescription: ...

    def select(self, hub: AnalysisHub, request: RequestT) -> OutputGroupSelectionResult: ...

    def build(self, hub: AnalysisHub, request: RequestT) -> list[OutputGroup]: ...

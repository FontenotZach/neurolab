"""Models for metadata-only grouping of persisted adapter outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class OutputGroup:
    """
    Metadata-only grouping of persisted adapter outputs.

    This layer catalogs logical relationships among outputs already stored in the
    Analysis Hub. It does not contain payloads and must not load payloads.

    `member_provenance_ids` contains persisted output addressing ids, typically
    `OutputMetadataRecord.provenance_id` values observed from `hub.list_records()`.
    Parent-child relationships are represented by ids (no nested objects).
    """

    group_id: str
    group_type: str
    member_provenance_ids: tuple[str, ...]
    parent_group_id: str | None = None
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OutputGroupBuilderDescription:
    """Informational metadata describing an output group builder."""

    builder_name: str
    builder_version: str
    summary: str
    supported_group_types: tuple[str, ...] = ()
    supported_dataset_types: tuple[str, ...] = ()
    supported_adapter_names: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OutputGroupSelectionResult:
    """
    Result of metadata-only selection against the Analysis Hub.

    `selected_provenance_ids` must preserve hub ordering for considered records.
    Selection is metadata-only: no payload loading.
    """

    builder_name: str
    selected_provenance_ids: tuple[str, ...]
    total_candidates_seen: int

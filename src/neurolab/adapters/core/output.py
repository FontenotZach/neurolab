"""Canonical output produced by artifact adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdapterOutput:
    """
    Canonical output produced by artifact adapters.
    Immutable, serializable, deterministic.
    dataset_type is a structural/format hint (e.g. tabular, image); not domain semantics.
    """

    artifact_id: str
    adapter_name: str
    adapter_version: str
    dataset_type: str
    schema: dict
    payload: Any

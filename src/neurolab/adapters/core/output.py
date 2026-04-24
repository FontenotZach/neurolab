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

    Persistence (v1 codec): `schema` must be JSON-serializable (str keys, no NaN/Inf, no exotic types).
    `payload` may use None, bool, Python int/float (finite), str, list, dict[str, ...], and numpy.ndarray
    only as leaf values (see neurolab.storage.adapter_results.payload_codec). Pickle is not supported.

    ``adapter_config_hash`` optional metadata for lineage (included in ``provenance_id``).
    """

    artifact_id: str
    adapter_name: str
    adapter_version: str
    dataset_type: str
    schema: dict[str, Any]
    payload: Any
    adapter_config_hash: str | None = None

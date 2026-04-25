"""Deterministic hashing for analysis module parameters (request / config)."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, is_dataclass
from typing import Any

from neurolab.storage.adapter_results.ids import canonical_json


def _parameters_object_to_mapping(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return dict(obj)
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        out = to_dict()
        if not isinstance(out, dict):
            raise TypeError(f"to_dict() must return dict, got {type(out).__name__}")
        return dict(out)
    raise TypeError(
        f"Cannot derive parameters mapping from {type(obj).__name__!r}: expected dict, dataclass instance, or object with to_dict() -> dict"
    )


def compute_parameters_hash(parameters: Any) -> str:
    """
    SHA-256 hex digest of canonical JSON for ``parameters``.

    Accepts a ``dict[str, Any]``, a :func:`dataclasses.is_dataclass` instance
    (via :func:`dataclasses.asdict`), or an object with ``to_dict()`` returning
    a dict. The normalized mapping must be JSON-serializable by
    :func:`neurolab.storage.adapter_results.ids.canonical_json` (same rules as
    ``json.dumps`` with ``sort_keys=True``, ``allow_nan=False``).
    """
    body = _parameters_object_to_mapping(parameters)
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()

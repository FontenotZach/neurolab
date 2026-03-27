"""v1 payload codec: JSON + .npy sidecars for ndarray leaves."""

from __future__ import annotations

import json
import math
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np

from neurolab.storage.adapter_results.errors import PayloadDecodeError, PayloadEncodeError
from neurolab.storage.adapter_results.models import PRIMARY_PAYLOAD_REL_PATH

# Reserved internal codec key. Adapter payloads must not use this dict key anywhere.
# Encoded ndarray leaves become a dict with this single key mapping to:
#   {"path": "<relative path>", "dtype": "<numpy dtype str>", "shape": [int, ...]}
NEUROLAB_PAYLOAD_ARRAY_PORTAL_V1 = "__neurolab_payload_array_v1__"


def validate_payload_for_codec(obj: Any) -> None:
    """Validate payload against the v1 contract. Raises PayloadEncodeError if invalid."""
    _validate_value(obj, path_label="$")


def _reject_reserved_portal_map(d: dict[Any, Any]) -> None:
    if NEUROLAB_PAYLOAD_ARRAY_PORTAL_V1 in d:
        raise PayloadEncodeError(f"Forbidden reserved key {NEUROLAB_PAYLOAD_ARRAY_PORTAL_V1!r} in adapter payload")


def _validate_ndarray(arr: np.ndarray) -> None:
    if arr.dtype == object:
        raise PayloadEncodeError("object-dtype ndarray is not supported in v1")
    if np.issubdtype(arr.dtype, np.datetime64) or np.issubdtype(arr.dtype, np.timedelta64):
        raise PayloadEncodeError("datetime64/timedelta64 arrays are not supported in v1")
    if np.iscomplexobj(arr):
        raise PayloadEncodeError("complex arrays are not supported in v1")
    kind = arr.dtype.kind
    if kind in ("S", "V", "O"):
        raise PayloadEncodeError(f"ndarray dtype {arr.dtype!r} is not supported in v1")
    if np.issubdtype(arr.dtype, np.floating):
        if arr.size and not np.all(np.isfinite(arr)):
            raise PayloadEncodeError("non-finite float values in ndarray are not allowed")


def _validate_value(obj: Any, *, path_label: str) -> None:
    if obj is None or isinstance(obj, bool):
        return
    if type(obj) is int:
        return
    if isinstance(obj, str):
        return
    if type(obj) is float:
        if not math.isfinite(obj):
            raise PayloadEncodeError(f"non-finite float at {path_label}")
        return
    if isinstance(obj, tuple | set):
        raise PayloadEncodeError(f"tuples and sets are not allowed at {path_label}")
    if isinstance(obj, Decimal):
        raise PayloadEncodeError(f"Decimal is not allowed at {path_label}")
    try:
        if isinstance(obj, bytes | bytearray | memoryview):
            raise PayloadEncodeError(f"bytes-like values are not allowed at {path_label}")
    except TypeError:
        pass
    import datetime as _dt

    if isinstance(obj, _dt.datetime | _dt.date | _dt.time):
        raise PayloadEncodeError(f"datetime values are not allowed at {path_label}")

    if isinstance(obj, np.ndarray):
        _validate_ndarray(obj)
        return

    if isinstance(obj, dict):
        _reject_reserved_portal_map(obj)
        for k, v in obj.items():
            if not isinstance(k, str):
                raise PayloadEncodeError(f"dict keys must be str at {path_label}, got {type(k).__name__}")
            _validate_value(v, path_label=f"{path_label}.{k}")
        return

    if isinstance(obj, list):
        for i, item in enumerate(obj):
            _validate_value(item, path_label=f"{path_label}[{i}]")
        return

    if isinstance(obj, np.generic):
        raise PayloadEncodeError(f"numpy scalar {type(obj)} at {path_label} must be a Python bool/int/float")

    raise PayloadEncodeError(f"unsupported type {type(obj).__name__} at {path_label}")


def _path_tuple_to_stem(parts: tuple[str, ...]) -> str:
    if not parts:
        return "root"
    return "__".join(parts)


def collect_row_count_and_shapes(payload: Any) -> tuple[int | None, dict[str, list[int]] | None]:
    """Best-effort hints only; decoders must ignore these."""
    row_count: int | None = None
    if isinstance(payload, list):
        if len(payload) == 0 or all(isinstance(x, dict) for x in payload):
            row_count = len(payload)

    shapes: dict[str, list[int]] = {}

    def walk(o: Any, prefix: str) -> None:
        if isinstance(o, np.ndarray):
            shapes[prefix or "root"] = [int(x) for x in o.shape]
            return
        if isinstance(o, dict):
            for k in sorted(o.keys()):
                walk(o[k], f"{prefix}.{k}" if prefix else k)
        elif isinstance(o, list):
            for i, item in enumerate(o):
                walk(item, f"{prefix}[{i}]")

    walk(payload, "")
    shape_summary = shapes if shapes else None
    return row_count, shape_summary


def encode_payload_to_record(payload: Any, record_dir: Path) -> None:
    """Write payload.json and optional arrays/ under record_dir (atomic per file)."""
    validate_payload_for_codec(payload)
    tree = _encode_build_tree(payload, record_dir, parts=())
    text = json.dumps(tree, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    _atomic_write_text(record_dir / PRIMARY_PAYLOAD_REL_PATH, text)


def _encode_build_tree(obj: Any, record_dir: Path, *, parts: tuple[str, ...]) -> Any:
    if isinstance(obj, np.ndarray):
        rel = f"arrays/{_path_tuple_to_stem(parts)}.npy"
        dest = record_dir / rel
        _atomic_save_npy(dest, obj)
        return {
            NEUROLAB_PAYLOAD_ARRAY_PORTAL_V1: {
                "path": rel,
                "dtype": str(obj.dtype),
                "shape": [int(x) for x in obj.shape],
            }
        }
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k in sorted(obj.keys()):
            assert isinstance(k, str)
            out[k] = _encode_build_tree(obj[k], record_dir, parts=parts + (k,))
        return out
    if isinstance(obj, list):
        return [_encode_build_tree(item, record_dir, parts=parts + (str(i),)) for i, item in enumerate(obj)]
    return obj


def decode_payload_from_record(record_dir: Path) -> Any:
    """Read payload.json and reconstruct ndarray leaves from arrays/."""
    path = record_dir / PRIMARY_PAYLOAD_REL_PATH
    if not path.is_file():
        raise PayloadDecodeError(f"missing {PRIMARY_PAYLOAD_REL_PATH}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return _decode_walk(raw, record_dir)


def _decode_walk(obj: Any, record_dir: Path) -> Any:
    if isinstance(obj, dict):
        if NEUROLAB_PAYLOAD_ARRAY_PORTAL_V1 in obj:
            if len(obj) != 1:
                raise PayloadDecodeError("invalid portal dict: must contain only the neurolab portal key")
            spec = obj[NEUROLAB_PAYLOAD_ARRAY_PORTAL_V1]
            if not isinstance(spec, dict):
                raise PayloadDecodeError("portal value must be an object")
            rel = spec.get("path")
            if not isinstance(rel, str):
                raise PayloadDecodeError("portal.path must be a string")
            arr_path = record_dir / rel
            if not arr_path.is_file():
                raise PayloadDecodeError(f"missing array file {rel}")
            return np.load(arr_path, allow_pickle=False)
        return {k: _decode_walk(v, record_dir) for k, v in sorted(obj.items(), key=lambda kv: kv[0])}
    if isinstance(obj, list):
        return [_decode_walk(item, record_dir) for item in obj]
    return obj


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _atomic_save_npy(path: Path, arr: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as f:
        np.save(f, arr, allow_pickle=False)
    tmp.replace(path)

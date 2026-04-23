"""Deterministic identifiers for stored adapter outputs."""

from __future__ import annotations

import hashlib
import json
import warnings
from typing import Any


class StoredOutputIdentityWarning(UserWarning):
    """Emitted when building stored_output_id with optional fields omitted."""


def canonical_json(obj: Any) -> str:
    """Deterministic JSON text for fingerprinting (schemas, stable summaries)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def schema_fingerprint(schema: dict[str, Any]) -> str:
    """SHA-256 hex digest of canonical JSON for `schema`. Schema is part of persisted identity."""
    return hashlib.sha256(canonical_json(schema).encode("utf-8")).hexdigest()


def compute_stored_output_id(
    *,
    artifact_id: str | None = None,
    adapter_name: str | None = None,
    adapter_version: str | None = None,
    dataset_type: str | None = None,
    schema: dict[str, Any] | None = None,
    adapter_config_hash: str | None = None,
    pipeline_ordinal: int | None = None,
) -> str:
    """
    Derive stored_output_id from a canonical JSON object (sorted keys), then SHA-256 hex.

    Only keys with non-missing values are included. A field is "missing" if its value
    is ``None`` (``pipeline_ordinal`` may be ``0``). Each omitted optional field emits
    :class:`StoredOutputIdentityWarning`.
    """
    payload: dict[str, Any] = {}

    if artifact_id is not None:
        payload["artifact_id"] = artifact_id
    else:
        warnings.warn(
            "stored_output_id: excluded key 'artifact_id' (missing)",
            StoredOutputIdentityWarning,
            stacklevel=2,
        )

    if adapter_name is not None:
        payload["adapter_name"] = adapter_name
    else:
        warnings.warn(
            "stored_output_id: excluded key 'adapter_name' (missing)",
            StoredOutputIdentityWarning,
            stacklevel=2,
        )

    if adapter_version is not None:
        payload["adapter_version"] = adapter_version
    else:
        warnings.warn(
            "stored_output_id: excluded key 'adapter_version' (missing)",
            StoredOutputIdentityWarning,
            stacklevel=2,
        )

    if dataset_type is not None:
        payload["dataset_type"] = dataset_type
    else:
        warnings.warn(
            "stored_output_id: excluded key 'dataset_type' (missing)",
            StoredOutputIdentityWarning,
            stacklevel=2,
        )

    if schema is not None:
        payload["schema_fingerprint"] = schema_fingerprint(schema)
    else:
        warnings.warn(
            "stored_output_id: excluded key 'schema_fingerprint' (schema missing)",
            StoredOutputIdentityWarning,
            stacklevel=2,
        )

    if adapter_config_hash is not None:
        payload["adapter_config_hash"] = adapter_config_hash
    else:
        warnings.warn(
            "stored_output_id: excluded key 'adapter_config_hash' (missing)",
            StoredOutputIdentityWarning,
            stacklevel=2,
        )

    if pipeline_ordinal is not None:
        payload["pipeline_ordinal"] = pipeline_ordinal
    else:
        warnings.warn(
            "stored_output_id: excluded key 'pipeline_ordinal' (missing)",
            StoredOutputIdentityWarning,
            stacklevel=2,
        )

    body = canonical_json(payload)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()

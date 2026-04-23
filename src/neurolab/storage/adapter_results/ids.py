"""Deterministic identifiers for stored adapter outputs."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(obj: Any) -> str:
    """Deterministic JSON text for fingerprinting (schemas, stable summaries)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def schema_fingerprint(schema: dict[str, Any]) -> str:
    """SHA-256 hex digest of canonical JSON for `schema`. Schema is part of persisted identity."""
    return hashlib.sha256(canonical_json(schema).encode("utf-8")).hexdigest()


def compute_stored_output_id(
    *,
    manifest_id: str,
    artifact_id: str,
    adapter_name: str,
    adapter_version: str,
    dataset_type: str,
    schema: dict[str, Any],
    pipeline_ordinal: int,
) -> str:
    """
    Derive stored_output_id from stable provenance fields and schema fingerprint.
    Changing `schema` changes the fingerprint and therefore the id.
    """
    fp = schema_fingerprint(schema)
    lines = [
        manifest_id,
        artifact_id,
        adapter_name,
        adapter_version,
        dataset_type,
        fp,
        str(pipeline_ordinal),
    ]
    body = "\n".join(lines)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()

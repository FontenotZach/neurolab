"""Deterministic identifiers for stored adapter outputs (data vs provenance)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from neurolab.data_interface.models import Artifact


def canonical_json(obj: Any) -> str:
    """Deterministic JSON text for fingerprinting (schemas, stable summaries)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def schema_fingerprint(schema: dict[str, Any]) -> str:
    """SHA-256 hex digest of canonical JSON for ``schema`` (used in provenance_id)."""
    return hashlib.sha256(canonical_json(schema).encode("utf-8")).hexdigest()


def compute_data_hash(payload: Any) -> str:
    """Pure content identity for standardized adapter payload (SHA-256 hex)."""
    from neurolab.storage.adapter_results.payload_codec import fingerprint_payload_content

    return fingerprint_payload_content(payload)


def compute_stored_output_id(payload: Any) -> str:
    """Deprecated alias for :func:`compute_data_hash`."""
    return compute_data_hash(payload)


def artifact_key_for_provenance(artifact: Artifact) -> str | None:
    """Stable path key aligned with filesystem collector semantics."""
    if artifact.relative_path:
        return artifact.relative_path
    if artifact.absolute_path:
        return str(Path(artifact.absolute_path).name)
    return None


def compute_provenance_id(
    *,
    manifest_id: str,
    artifact_key: str | None,
    raw_content_hash: str | None,
    adapter_name: str,
    adapter_version: str,
    adapter_config_hash: str | None,
    schema_fingerprint: str,
    pipeline_ordinal: int,
) -> str:
    """
    Lineage identity: SHA-256 hex of canonical provenance object.

    Optional fields use JSON ``null`` so the key set is stable.
    """
    body = {
        "adapter_config_hash": adapter_config_hash,
        "adapter_name": adapter_name,
        "adapter_version": adapter_version,
        "artifact_key": artifact_key,
        "manifest_id": manifest_id,
        "pipeline_ordinal": pipeline_ordinal,
        "raw_content_hash": raw_content_hash,
        "schema_fingerprint": schema_fingerprint,
    }
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()

"""Deterministic identifiers for stored analysis results (data vs provenance)."""

from __future__ import annotations

import hashlib
from typing import Any

from neurolab.storage.adapter_results.ids import canonical_json
from neurolab.storage.adapter_results.payload_codec import fingerprint_payload_content


def compute_data_hash(payload: Any) -> str:
    """Pure content identity for standardized analysis-result payload (SHA-256 hex)."""
    return fingerprint_payload_content(payload)


def compute_provenance_id(
    *,
    module_name: str,
    module_version: str,
    input_provenance_ids: list[str],
    input_data_hashes: list[str],
    parameters_hash: str,
) -> str:
    """
    Lineage identity: SHA-256 hex of canonical provenance object.

    Important: preserves input ordering exactly as provided.
    """
    body = {
        "module_name": module_name,
        "module_version": module_version,
        "input_provenance_ids": list(input_provenance_ids),
        "input_data_hashes": list(input_data_hashes),
        "parameters_hash": parameters_hash,
    }
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()

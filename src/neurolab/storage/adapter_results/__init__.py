"""Persisted adapter pipeline results (v1 file backend)."""

from __future__ import annotations

from neurolab.storage.adapter_results.errors import PayloadDecodeError, PayloadEncodeError, StoredOutputNotFound
from neurolab.storage.adapter_results.file_store import FileAdapterResultStore
from neurolab.storage.adapter_results.ids import (
    artifact_key_for_provenance,
    canonical_json,
    compute_data_hash,
    compute_provenance_id,
    compute_stored_output_id,
    schema_fingerprint,
)
from neurolab.storage.adapter_results.models import META_SCHEMA_V2, PAYLOAD_FORMAT_V1, PRIMARY_PAYLOAD_REL_PATH, PersistedAdapterOutput
from neurolab.storage.adapter_results.payload_codec import (
    NEUROLAB_PAYLOAD_ARRAY_PORTAL_V1,
    decode_payload_from_record,
    encode_payload_to_record,
    fingerprint_payload_content,
    validate_payload_for_codec,
)
from neurolab.storage.adapter_results.store import AdapterResultStore

__all__ = [
    "NEUROLAB_PAYLOAD_ARRAY_PORTAL_V1",
    "AdapterResultStore",
    "META_SCHEMA_V2",
    "FileAdapterResultStore",
    "PAYLOAD_FORMAT_V1",
    "PRIMARY_PAYLOAD_REL_PATH",
    "PersistedAdapterOutput",
    "PayloadDecodeError",
    "PayloadEncodeError",
    "StoredOutputNotFound",
    "artifact_key_for_provenance",
    "canonical_json",
    "compute_data_hash",
    "compute_provenance_id",
    "compute_stored_output_id",
    "decode_payload_from_record",
    "encode_payload_to_record",
    "fingerprint_payload_content",
    "schema_fingerprint",
    "validate_payload_for_codec",
]

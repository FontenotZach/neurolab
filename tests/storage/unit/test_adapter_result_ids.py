"""Deterministic IDs for stored adapter outputs (payload-content identity)."""

from __future__ import annotations

import numpy as np
import pytest

from neurolab.storage.adapter_results.ids import compute_data_hash, compute_stored_output_id, schema_fingerprint
from neurolab.storage.adapter_results.payload_codec import fingerprint_payload_content

pytestmark = [pytest.mark.storage]

SAMPLE_PAYLOAD = [{"x": 1, "y": "a"}]


@pytest.mark.unit
def test_compute_data_hash_matches_deprecated_alias():
    p = {"a": 1}
    assert compute_data_hash(p) == compute_stored_output_id(p)


@pytest.mark.unit
def test_compute_stored_output_id_stable():
    id1 = compute_stored_output_id(SAMPLE_PAYLOAD)
    id2 = compute_stored_output_id(SAMPLE_PAYLOAD)
    assert id1 == id2
    assert len(id1) == 64


@pytest.mark.unit
def test_stored_output_id_same_for_equivalent_payload_shape():
    assert compute_stored_output_id([{"b": 2, "a": 1}]) == compute_stored_output_id([{"a": 1, "b": 2}])


@pytest.mark.unit
def test_stored_output_id_ignores_adapter_provenance_not_in_payload():
    """Same payload => same id; adapter metadata is not part of the payload tree."""
    p = [{"n": 1}]
    assert compute_stored_output_id(p) == fingerprint_payload_content(p)


@pytest.mark.unit
def test_stored_output_id_differs_when_payload_differs():
    assert compute_stored_output_id([1, 2]) != compute_stored_output_id([1, 3])


@pytest.mark.unit
def test_stored_output_id_numpy_content():
    a = np.array([1.0, 2.0], dtype=np.float32)
    b = np.array([1.0, 2.0], dtype=np.float32)
    assert compute_stored_output_id({"signal": a}) == compute_stored_output_id({"signal": b})


@pytest.mark.unit
def test_schema_fingerprint_stable():
    s = {"b": 1, "a": 2}
    assert schema_fingerprint(s) == schema_fingerprint({"a": 2, "b": 1})

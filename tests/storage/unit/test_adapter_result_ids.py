"""Deterministic IDs for stored adapter outputs."""

from __future__ import annotations

import pytest

from neurolab.storage.adapter_results.ids import compute_stored_output_id, schema_fingerprint

pytestmark = [pytest.mark.storage]

BASE = dict(
    manifest_id="m1",
    artifact_id="a1",
    adapter_name="csv_adapter",
    adapter_version="1.0",
    dataset_type="tabular",
    schema={"columns": ["x"]},
    pipeline_ordinal=0,
)


@pytest.mark.unit
def test_compute_stored_output_id_stable():
    id1 = compute_stored_output_id(**BASE)
    id2 = compute_stored_output_id(**BASE)
    assert id1 == id2
    assert len(id1) == 64


@pytest.mark.unit
def test_stored_output_id_depends_on_schema_fingerprint():
    b2 = {**BASE, "schema": {"columns": ["y"]}}
    assert compute_stored_output_id(**BASE) != compute_stored_output_id(**b2)


@pytest.mark.unit
def test_stored_output_id_depends_on_ordinal():
    b2 = {**BASE, "pipeline_ordinal": 1}
    assert compute_stored_output_id(**BASE) != compute_stored_output_id(**b2)


@pytest.mark.unit
def test_schema_fingerprint_stable():
    s = {"b": 1, "a": 2}
    assert schema_fingerprint(s) == schema_fingerprint({"a": 2, "b": 1})

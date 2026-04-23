"""Deterministic IDs for stored adapter outputs."""

from __future__ import annotations

import pytest

from neurolab.storage.adapter_results.ids import (
    StoredOutputIdentityWarning,
    compute_stored_output_id,
    schema_fingerprint,
)

pytestmark = [pytest.mark.storage]

BASE = dict(
    artifact_id="a1",
    adapter_name="csv_adapter",
    adapter_version="1.0",
    dataset_type="tabular",
    schema={"columns": ["x"]},
    adapter_config_hash="cfg-default",
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


@pytest.mark.unit
def test_missing_fields_warn_and_still_deterministic():
    with pytest.warns(StoredOutputIdentityWarning) as record:
        id1 = compute_stored_output_id()
        id2 = compute_stored_output_id()
    assert id1 == id2
    assert len(record) >= 1


@pytest.mark.unit
def test_schema_fingerprint_key_matches_schema_fingerprint_function():
    schema = {"k": 1}
    expected_fp = schema_fingerprint(schema)
    hid = compute_stored_output_id(
        artifact_id="x",
        adapter_name="a",
        adapter_version="1",
        dataset_type="tabular",
        schema=schema,
        adapter_config_hash="c",
        pipeline_ordinal=0,
    )
    # Changing only schema fingerprint should change id
    other = compute_stored_output_id(
        artifact_id="x",
        adapter_name="a",
        adapter_version="1",
        dataset_type="tabular",
        schema={"k": 2},
        adapter_config_hash="c",
        pipeline_ordinal=0,
    )
    assert hid != other
    assert expected_fp == schema_fingerprint(schema)

"""FileAnalysisResultStore unit tests."""

from __future__ import annotations

import json

import numpy as np
import pytest

from neurolab.storage.analysis_results.errors import AnalysisResultAlreadyExistsError, AnalysisResultNotFoundError
from neurolab.storage.analysis_results.file_store import FileAnalysisResultStore
from neurolab.storage.analysis_results.ids import compute_data_hash, compute_provenance_id

pytestmark = [pytest.mark.storage]


def _save(
    store: FileAnalysisResultStore,
    *,
    payload,
    module_name: str = "m",
    module_version: str = "1.0",
    input_provenance_ids: list[str] | None = None,
    input_data_hashes: list[str] | None = None,
    parameters_hash: str = "p" * 64,
    created_at: str | None = None,
):
    in_p = input_provenance_ids if input_provenance_ids is not None else ["a" * 64, "b" * 64]
    in_h = input_data_hashes if input_data_hashes is not None else ["1" * 64, "2" * 64]
    return store.save_result(
        result_type="summary_table",
        module_name=module_name,
        module_version=module_version,
        input_provenance_ids=in_p,
        input_data_hashes=in_h,
        parameters_hash=parameters_hash,
        schema={"cols": ["x"]},
        payload=payload,
        created_at=created_at,
    )


@pytest.mark.unit
def test_save_creates_record_dir_with_meta_and_payload(tmp_path):
    store = FileAnalysisResultStore(base_dir=tmp_path)
    meta = _save(store, payload={"x": 1})
    rec_dir = tmp_path / meta.provenance_id
    assert rec_dir.is_dir()
    assert (rec_dir / "meta.json").is_file()
    assert (rec_dir / "payload.json").is_file()

    raw = json.loads((rec_dir / "meta.json").read_text(encoding="utf-8"))
    assert raw["provenance_id"] == meta.provenance_id
    assert raw["data_hash"] == meta.data_hash
    assert raw["result_type"] == "summary_table"
    assert raw["module"]["name"] == "m"
    assert raw["module"]["version"] == "1.0"
    assert raw["parameters_hash"] == "p" * 64
    assert raw["schema"] == {"cols": ["x"]}


@pytest.mark.unit
def test_data_hash_changes_when_payload_changes(tmp_path):
    store = FileAnalysisResultStore(base_dir=tmp_path)
    m1 = _save(store, payload={"x": 1}, module_version="1.0", input_provenance_ids=["a" * 64], input_data_hashes=["1" * 64])
    m2 = _save(
        store,
        payload={"x": 2},
        module_version="1.0",
        input_provenance_ids=["a" * 64],
        input_data_hashes=["1" * 64],
        parameters_hash="q" * 64,
    )
    assert m1.data_hash != m2.data_hash


@pytest.mark.unit
def test_data_hash_ignores_lineage_fields(tmp_path):
    store = FileAnalysisResultStore(base_dir=tmp_path)
    payload = {"x": [1, 2], "arr": np.array([1.0, 2.0], dtype=np.float32)}
    dh = compute_data_hash(payload)

    m1 = _save(
        store,
        payload=payload,
        module_name="modA",
        module_version="1.0",
        input_provenance_ids=["a" * 64],
        input_data_hashes=["1" * 64],
        parameters_hash="p" * 64,
    )
    m2 = _save(
        store,
        payload=payload,
        module_name="modB",
        module_version="9.9",
        input_provenance_ids=["c" * 64],
        input_data_hashes=["9" * 64],
        parameters_hash="q" * 64,
    )
    assert m1.data_hash == m2.data_hash == dh


@pytest.mark.unit
def test_provenance_id_changes_with_version_params_inputs(tmp_path):
    store = FileAnalysisResultStore(base_dir=tmp_path)
    payload = {"x": 1}

    base_inputs_p = ["a" * 64, "b" * 64]
    base_inputs_h = ["1" * 64, "2" * 64]

    p1 = compute_provenance_id(
        module_name="m",
        module_version="1.0",
        input_provenance_ids=base_inputs_p,
        input_data_hashes=base_inputs_h,
        parameters_hash="p" * 64,
    )
    p2 = compute_provenance_id(
        module_name="m",
        module_version="2.0",
        input_provenance_ids=base_inputs_p,
        input_data_hashes=base_inputs_h,
        parameters_hash="p" * 64,
    )
    p3 = compute_provenance_id(
        module_name="m",
        module_version="1.0",
        input_provenance_ids=base_inputs_p,
        input_data_hashes=base_inputs_h,
        parameters_hash="q" * 64,
    )
    p4 = compute_provenance_id(
        module_name="m",
        module_version="1.0",
        input_provenance_ids=["b" * 64, "a" * 64],  # order matters
        input_data_hashes=base_inputs_h,
        parameters_hash="p" * 64,
    )
    assert p1 != p2
    assert p1 != p3
    assert p1 != p4

    m1 = _save(store, payload=payload, module_version="1.0", input_provenance_ids=base_inputs_p, input_data_hashes=base_inputs_h)
    m2 = _save(
        store,
        payload=payload,
        module_version="2.0",
        input_provenance_ids=base_inputs_p,
        input_data_hashes=base_inputs_h,
        parameters_hash="p" * 64,
    )
    assert m1.provenance_id != m2.provenance_id


@pytest.mark.unit
def test_created_at_does_not_affect_hashes(tmp_path):
    store = FileAnalysisResultStore(base_dir=tmp_path)
    payload = {"x": 1}
    m1 = _save(store, payload=payload, created_at="2020-01-01T00:00:00+00:00")
    # Same lineage + same payload should be idempotent even if created_at differs.
    m2 = _save(store, payload=payload, created_at="2099-01-01T00:00:00+00:00")
    assert m1.provenance_id == m2.provenance_id
    assert m1.data_hash == m2.data_hash


@pytest.mark.unit
def test_load_metadata_and_payload_roundtrip(tmp_path):
    store = FileAnalysisResultStore(base_dir=tmp_path)
    meta = _save(store, payload={"x": 1})
    loaded_meta = store.load_metadata(meta.provenance_id)
    assert loaded_meta.provenance_id == meta.provenance_id
    assert loaded_meta.data_hash == meta.data_hash
    assert store.load_payload(meta.provenance_id) == {"x": 1}


@pytest.mark.unit
def test_duplicate_provenance_id_raises_if_contents_differ(tmp_path):
    store = FileAnalysisResultStore(base_dir=tmp_path)
    meta = _save(store, payload={"x": 1})
    with pytest.raises(AnalysisResultAlreadyExistsError):
        # Same lineage => same provenance_id; different payload should conflict.
        _save(store, payload={"x": 2}, created_at="2099-01-01T00:00:00+00:00")

    assert store.load_payload(meta.provenance_id) == {"x": 1}


@pytest.mark.unit
def test_list_metadata_deterministic_order(tmp_path):
    store = FileAnalysisResultStore(base_dir=tmp_path)
    a = _save(store, payload={"x": 1}, module_version="1.0")
    b = _save(
        store,
        payload={"x": 1},
        module_version="2.0",
        input_provenance_ids=["z" * 64],
        input_data_hashes=["9" * 64],
        parameters_hash="q" * 64,
    )
    listed = store.list_metadata()
    assert [m.provenance_id for m in listed] == sorted([a.provenance_id, b.provenance_id])


@pytest.mark.unit
def test_missing_raises(tmp_path):
    store = FileAnalysisResultStore(base_dir=tmp_path)
    with pytest.raises(AnalysisResultNotFoundError):
        store.load_metadata("0" * 64)

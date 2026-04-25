"""Tests for analysis module parameter hashing."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from neurolab.analysis_modules.ids import compute_parameters_hash


def test_compute_parameters_hash_stable_for_identical_dicts() -> None:
    p = {"alpha": 1, "beta": "x"}
    assert compute_parameters_hash(p) == compute_parameters_hash(p)
    assert len(compute_parameters_hash(p)) == 64


def test_compute_parameters_hash_independent_of_key_order() -> None:
    a = {"x": 1, "y": 2, "z": 3}
    b = {"z": 3, "x": 1, "y": 2}
    assert compute_parameters_hash(a) == compute_parameters_hash(b)


def test_compute_parameters_hash_changes_when_value_changes() -> None:
    h1 = compute_parameters_hash({"k": 1})
    h2 = compute_parameters_hash({"k": 2})
    assert h1 != h2


def test_compute_parameters_hash_nested_structures_deterministic() -> None:
    inner_a = {"z": 9, "w": 8}
    inner_b = {"w": 8, "z": 9}
    assert compute_parameters_hash({"outer": inner_a}) == compute_parameters_hash({"outer": inner_b})


def test_compute_parameters_hash_dataclass() -> None:
    @dataclass
    class Req:
        window_ms: int
        label: str

    r1 = Req(window_ms=100, label="a")
    r2 = Req(window_ms=100, label="a")
    assert compute_parameters_hash(r1) == compute_parameters_hash(r2)


def test_compute_parameters_hash_to_dict_object() -> None:
    class P:
        def to_dict(self) -> dict[str, int]:
            return {"n": 42}

    assert compute_parameters_hash(P()) == compute_parameters_hash({"n": 42})


def test_compute_parameters_hash_to_dict_wrong_return_raises() -> None:
    class Bad:
        def to_dict(self) -> list[int]:
            return [1, 2]

    with pytest.raises(TypeError, match="to_dict\\(\\) must return dict"):
        compute_parameters_hash(Bad())


def test_compute_parameters_hash_non_serializable_dict_raises() -> None:
    with pytest.raises((TypeError, ValueError)):
        compute_parameters_hash({"x": object()})


def test_compute_parameters_hash_dataclass_with_non_json_field_raises() -> None:
    @dataclass
    class BadReq:
        raw: object

    with pytest.raises((TypeError, ValueError)):
        compute_parameters_hash(BadReq(raw=object()))


def test_compute_parameters_hash_rejects_plain_object() -> None:
    with pytest.raises(TypeError, match="Cannot derive parameters mapping"):
        compute_parameters_hash(object())

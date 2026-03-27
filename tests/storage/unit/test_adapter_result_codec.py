"""Unit tests for v1 adapter payload codec."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import numpy as np
import pytest

from neurolab.storage.adapter_results.errors import PayloadDecodeError, PayloadEncodeError
from neurolab.storage.adapter_results.models import PRIMARY_PAYLOAD_REL_PATH
from neurolab.storage.adapter_results.payload_codec import (
    NEUROLAB_PAYLOAD_ARRAY_PORTAL_V1,
    decode_payload_from_record,
    encode_payload_to_record,
    validate_payload_for_codec,
)

pytestmark = [pytest.mark.storage]


@pytest.mark.unit
def test_codec_roundtrip_scalars_and_nested(tmp_path):
    payload = {
        "a": None,
        "b": True,
        "c": 42,
        "d": "x",
        "e": 1.5,
        "f": [{"k": 1}, {"k": 2}],
    }
    encode_payload_to_record(payload, tmp_path)
    back = decode_payload_from_record(tmp_path)
    assert back == payload
    raw = json.loads((tmp_path / PRIMARY_PAYLOAD_REL_PATH).read_text(encoding="utf-8"))
    assert raw["f"][0]["k"] == 1


@pytest.mark.unit
def test_codec_roundtrip_ndarray_leaf(tmp_path):
    payload = {"signal": np.asarray([0.25, 0.5, -1.0], dtype=np.float64)}
    encode_payload_to_record(payload, tmp_path)
    back = decode_payload_from_record(tmp_path)
    assert set(back.keys()) == {"signal"}
    np.testing.assert_array_equal(back["signal"], payload["signal"])


@pytest.mark.unit
def test_codec_top_level_ndarray(tmp_path):
    arr = np.arange(6, dtype=np.int32).reshape(2, 3)
    encode_payload_to_record(arr, tmp_path)
    back = decode_payload_from_record(tmp_path)
    np.testing.assert_array_equal(back, arr)


@pytest.mark.unit
def test_codec_rejects_nan_inf_scalar():
    with pytest.raises(PayloadEncodeError):
        validate_payload_for_codec(float("nan"))
    with pytest.raises(PayloadEncodeError):
        validate_payload_for_codec(float("inf"))


@pytest.mark.unit
def test_codec_rejects_tuple_set_decimal_datetime_bytes():
    with pytest.raises(PayloadEncodeError):
        validate_payload_for_codec((1,))
    with pytest.raises(PayloadEncodeError):
        validate_payload_for_codec({1})
    with pytest.raises(PayloadEncodeError):
        validate_payload_for_codec(Decimal("1"))
    with pytest.raises(PayloadEncodeError):
        validate_payload_for_codec(datetime(2024, 1, 1, tzinfo=UTC))
    with pytest.raises(PayloadEncodeError):
        validate_payload_for_codec(b"x")


@pytest.mark.unit
def test_codec_rejects_non_str_dict_keys():
    with pytest.raises(PayloadEncodeError):
        validate_payload_for_codec({1: "a"})


@pytest.mark.unit
def test_codec_rejects_object_dtype_array_validate_only():
    with pytest.raises(PayloadEncodeError):
        validate_payload_for_codec(np.asarray(["a", "b"], dtype=object))


@pytest.mark.unit
def test_codec_rejects_non_finite_float_array():
    with pytest.raises(PayloadEncodeError):
        validate_payload_for_codec(np.asarray([1.0, float("nan")]))


@pytest.mark.unit
def test_codec_rejects_reserved_portal_in_input():
    with pytest.raises(PayloadEncodeError):
        validate_payload_for_codec({NEUROLAB_PAYLOAD_ARRAY_PORTAL_V1: {"path": "x", "dtype": "f8", "shape": [1]}})


@pytest.mark.unit
def test_codec_rejects_numpy_scalar():
    with pytest.raises(PayloadEncodeError):
        validate_payload_for_codec(np.float64(1.0))


@pytest.mark.unit
def test_decode_rejects_bad_portal_dict(tmp_path):
    corrupt = {"a": {NEUROLAB_PAYLOAD_ARRAY_PORTAL_V1: {}, "b": 1}}
    (tmp_path / PRIMARY_PAYLOAD_REL_PATH).write_text(
        json.dumps(corrupt, sort_keys=True),
        encoding="utf-8",
    )
    with pytest.raises(PayloadDecodeError):
        decode_payload_from_record(tmp_path)


@pytest.mark.unit
def test_collect_row_count_and_shapes():
    from neurolab.storage.adapter_results.payload_codec import collect_row_count_and_shapes

    rows = [{"x": 1}, {"x": 2}]
    rc, sh = collect_row_count_and_shapes(rows)
    assert rc == 2
    assert sh is None

    rc2, sh2 = collect_row_count_and_shapes({"a": np.zeros((2, 3))})
    assert rc2 is None
    assert sh2 == {"a": [2, 3]}

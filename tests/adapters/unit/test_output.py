"""Unit tests for AdapterOutput."""

from __future__ import annotations

import pytest

from neurolab.adapters.core.output import AdapterOutput

pytestmark = [pytest.mark.adapters, pytest.mark.unit]


def test_adapter_output_construction():
    """AdapterOutput has required fields including dataset_type and adapter_version."""
    out = AdapterOutput(
        artifact_id="a1",
        adapter_name="csv_adapter",
        adapter_version="1.0",
        dataset_type="tabular",
        schema={"columns": ["x", "y"]},
        payload=[{"x": 1, "y": 2}],
    )
    assert out.artifact_id == "a1"
    assert out.adapter_name == "csv_adapter"
    assert out.adapter_version == "1.0"
    assert out.dataset_type == "tabular"
    assert out.schema == {"columns": ["x", "y"]}
    assert out.payload == [{"x": 1, "y": 2}]


def test_adapter_output_immutable():
    """AdapterOutput is frozen (immutable)."""
    out = AdapterOutput(
        artifact_id="a1",
        adapter_name="csv",
        adapter_version="1.0",
        dataset_type="tabular",
        schema={},
        payload=[],
    )
    with pytest.raises(AttributeError):
        out.artifact_id = "other"  # type: ignore[misc]

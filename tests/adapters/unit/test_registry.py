"""Unit tests for adapter registry."""

from __future__ import annotations

import pytest

from neurolab.adapters.core.registry import get_adapters
from neurolab.adapters.implementations.tabular.csv_adapter import CSVAdapter

pytestmark = [pytest.mark.adapters, pytest.mark.unit]


def test_get_adapters_returns_classes():
    """get_adapters returns a list of adapter classes (e.g. CSVAdapter registered at import)."""
    adapters = get_adapters()
    assert isinstance(adapters, list)
    assert len(adapters) >= 1
    assert CSVAdapter in adapters


def test_get_adapters_sorted_by_priority_descending():
    """get_adapters returns adapters in priority descending order."""
    adapters = get_adapters()
    priorities = [getattr(c, "priority", 0) for c in adapters]
    assert priorities == sorted(priorities, reverse=True)

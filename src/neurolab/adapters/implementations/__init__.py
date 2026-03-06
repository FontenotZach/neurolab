"""Concrete adapter implementations; registration at import time."""

from neurolab.adapters.core.registry import register_adapter
from neurolab.adapters.implementations.tabular.csv_adapter import CSVAdapter
from neurolab.adapters.implementations.tabular.json_adapter import JSONAdapter

register_adapter(CSVAdapter)
register_adapter(JSONAdapter)

"""Concrete analysis modules (examples and built-ins)."""

from __future__ import annotations

from neurolab.analysis_modules.implementations.payload_top_level_count import (
    PayloadTopLevelCountModule,
    PayloadTopLevelCountRequest,
)
from neurolab.analysis_modules.registry import register_analysis_module

register_analysis_module(PayloadTopLevelCountModule())

__all__ = [
    "PayloadTopLevelCountModule",
    "PayloadTopLevelCountRequest",
]

"""Persisted analysis results (v1 file backend).

This layer mirrors ``neurolab.storage.adapter_results`` but is intended for outputs
produced by analysis modules (not adapters).
"""

from __future__ import annotations

from neurolab.storage.adapter_results.errors import PayloadDecodeError, PayloadEncodeError
from neurolab.storage.analysis_results.errors import (
    AnalysisResultAlreadyExistsError,
    AnalysisResultNotFoundError,
)
from neurolab.storage.analysis_results.file_store import FileAnalysisResultStore
from neurolab.storage.analysis_results.ids import compute_data_hash, compute_provenance_id
from neurolab.storage.analysis_results.models import PersistedAnalysisResult

__all__ = [
    "AnalysisResultAlreadyExistsError",
    "AnalysisResultNotFoundError",
    "FileAnalysisResultStore",
    "PayloadDecodeError",
    "PayloadEncodeError",
    "PersistedAnalysisResult",
    "compute_data_hash",
    "compute_provenance_id",
]

"""Errors for analysis result storage and payload codec."""

from __future__ import annotations


class AnalysisResultNotFoundError(FileNotFoundError):
    """Raised when no analysis result record exists for the given provenance_id."""


class AnalysisResultAlreadyExistsError(FileExistsError):
    """Raised when attempting to save a duplicate provenance_id with different contents."""

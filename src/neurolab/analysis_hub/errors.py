"""Errors for analysis hub (read-only metadata + lazy payload access)."""

from __future__ import annotations


class AnalysisHubError(Exception):
    """Base class for analysis hub errors."""


class MetadataRecordNotFoundError(AnalysisHubError):
    """Raised when a provenance_id is not present in the hub registry."""


class PayloadNotFoundError(AnalysisHubError):
    """Raised when payload material is missing or cannot be decoded."""


class MetadataLoadError(AnalysisHubError):
    """Raised when persisted metadata (meta.json) is missing or malformed."""

"""Errors for adapter result storage and payload codec."""

from __future__ import annotations


class PayloadEncodeError(ValueError):
    """Raised when a payload cannot be encoded under the v1 codec rules."""


class PayloadDecodeError(ValueError):
    """Raised when stored payload files are missing or invalid."""


class StoredOutputNotFound(FileNotFoundError):
    """Raised when no record exists for the given manifest_id and provenance_id."""

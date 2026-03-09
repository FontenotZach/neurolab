"""Unit tests for NCSAdapter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from neurolab.adapters.core.exceptions import AdapterError
from neurolab.adapters.implementations.neo.ncs_adapter import NCSAdapter
from neurolab.data_interface.models import Artifact

pytestmark = [pytest.mark.adapters, pytest.mark.unit]


def _artifact(
    absolute_path: str | None,
    media_type: str | None = "application/x-neuralynx-ncs",
    relative_path: str | None = "CSC1.ncs",
) -> Artifact:
    return Artifact(
        artifact_id="a1",
        source_uri="file:///data",
        artifact_type="file",
        relative_path=relative_path,
        absolute_path=absolute_path,
        size_bytes=0,
        mtime=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        content_hash=None,
        media_type=media_type,
    )


def test_can_handle_media_type_ncs():
    """can_handle returns True for media_type application/x-neuralynx-ncs."""
    adapter = NCSAdapter()
    art = _artifact(absolute_path="/data/session/CSC1.ncs", media_type="application/x-neuralynx-ncs")
    assert adapter.can_handle(art) is True


def test_can_handle_extension_ncs():
    """can_handle returns True when path ends with .ncs."""
    adapter = NCSAdapter()
    art = _artifact(absolute_path="/data/file.ncs", media_type=None, relative_path="file.ncs")
    assert adapter.can_handle(art) is True


def test_can_handle_rejects_non_ncs():
    """can_handle returns False for non-NCS media type and path."""
    adapter = NCSAdapter()
    art = _artifact(absolute_path="/data/file.csv", media_type="text/csv", relative_path="file.csv")
    assert adapter.can_handle(art) is False


def test_parse_requires_absolute_path():
    """parse raises when artifact has no absolute_path."""
    adapter = NCSAdapter()
    art = _artifact(absolute_path=None, relative_path="CSC1.ncs")
    with pytest.raises(AdapterError, match="absolute_path"):
        adapter.parse(art)


def test_parse_directory_not_found_raises(tmp_path):
    """parse raises when the artifact's parent directory does not exist."""
    adapter = NCSAdapter()
    nonexistent_dir = tmp_path / "nonexistent"
    art = _artifact(absolute_path=str(nonexistent_dir / "CSC1.ncs"))
    with pytest.raises(AdapterError, match="not found|directory"):
        adapter.parse(art)


def test_parse_no_valid_stream_raises(tmp_path):
    """parse raises AdapterError when no valid Neuralynx signal stream is detected."""
    # Empty directory: Neo may parse but yield no streams with samples.
    adapter = NCSAdapter()
    art = _artifact(absolute_path=str(tmp_path / "CSC1.ncs"))
    with pytest.raises(AdapterError, match="No valid Neuralynx signal stream detected"):
        adapter.parse(art)

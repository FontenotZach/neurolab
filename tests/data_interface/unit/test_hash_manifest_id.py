"""
Unit tests for deterministic manifest_id (hash_manifest_id) behavior.
Manifest ID is derived only from content_hash and size_bytes; paths and mtime are ignored.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from neurolab.data_interface.hashing import hash_manifest_id
from neurolab.data_interface.models import Artifact

pytestmark = [pytest.mark.data_interface]


def _artifact(
    content_hash: str | None = "abc",
    size_bytes: int | None = 100,
    relative_path: str | None = "a.txt",
    absolute_path: str | None = "/tmp/a.txt",
    mtime_iso: str | None = "2024-01-01T00:00:00+00:00",
) -> Artifact:
    mtime = datetime.fromisoformat(mtime_iso) if mtime_iso else None
    return Artifact(
        source_uri="file:///tmp",
        artifact_type="file",
        relative_path=relative_path,
        absolute_path=absolute_path,
        size_bytes=size_bytes,
        mtime=mtime,
        content_hash=content_hash,
        media_type="text/plain",
    )


@pytest.mark.unit
def test_empty_artifacts_produces_constant_id():
    """Empty artifact list yields the same manifest_id every time."""
    id1 = hash_manifest_id([])
    id2 = hash_manifest_id([])
    assert id1 == id2
    assert len(id1) == 64  # SHA-256 hex


@pytest.mark.unit
def test_same_content_same_id():
    """Same set of artifacts (content_hash + size_bytes) produces the same manifest_id."""
    a1 = _artifact(content_hash="h1", size_bytes=10)
    a2 = _artifact(content_hash="h2", size_bytes=20)
    id1 = hash_manifest_id([a1, a2])
    id2 = hash_manifest_id([a1, a2])
    assert id1 == id2


@pytest.mark.unit
def test_order_independent():
    """Artifact order does not affect manifest_id (canonical sort by content_hash, size_bytes)."""
    a1 = _artifact(content_hash="aa", size_bytes=1)
    a2 = _artifact(content_hash="bb", size_bytes=2)
    id_ab = hash_manifest_id([a1, a2])
    id_ba = hash_manifest_id([a2, a1])
    assert id_ab == id_ba


@pytest.mark.unit
def test_paths_ignored():
    """Different paths with same content_hash and size_bytes produce the same manifest_id."""
    a1 = _artifact(content_hash="x", size_bytes=42, relative_path="dir/a.txt", absolute_path="/x/dir/a.txt")
    a2 = _artifact(content_hash="x", size_bytes=42, relative_path="other/b.txt", absolute_path="/y/other/b.txt")
    assert hash_manifest_id([a1]) == hash_manifest_id([a2])


@pytest.mark.unit
def test_mtime_ignored():
    """Different mtime with same content_hash and size_bytes produce the same manifest_id."""
    a1 = _artifact(content_hash="y", size_bytes=1, mtime_iso="2020-01-01T00:00:00+00:00")
    a2 = _artifact(content_hash="y", size_bytes=1, mtime_iso="2025-12-31T23:59:59+00:00")
    assert hash_manifest_id([a1]) == hash_manifest_id([a2])


@pytest.mark.unit
def test_content_hash_change_changes_id():
    """Changing content_hash changes manifest_id."""
    a1 = _artifact(content_hash="old", size_bytes=10)
    a2 = _artifact(content_hash="new", size_bytes=10)
    assert hash_manifest_id([a1]) != hash_manifest_id([a2])


@pytest.mark.unit
def test_size_change_changes_id():
    """Changing size_bytes changes manifest_id."""
    a1 = _artifact(content_hash="same", size_bytes=10)
    a2 = _artifact(content_hash="same", size_bytes=20)
    assert hash_manifest_id([a1]) != hash_manifest_id([a2])


@pytest.mark.unit
def test_different_artifact_sets_different_ids():
    """Different artifact sets produce different manifest_ids."""
    a1 = _artifact(content_hash="a", size_bytes=1)
    a2 = _artifact(content_hash="b", size_bytes=2)
    id_one = hash_manifest_id([a1])
    id_two = hash_manifest_id([a2])
    id_both = hash_manifest_id([a1, a2])
    assert id_one != id_two
    assert id_one != id_both
    assert id_two != id_both

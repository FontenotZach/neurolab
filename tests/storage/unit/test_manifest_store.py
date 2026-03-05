"""
Unit tests for FileManifestStore.
Covers save, load, list, delete and round-trip (save then load yields equivalent manifest).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from neurolab.data_interface.models import Artifact, DataSourceSpec, Manifest
from neurolab.storage.manifest_store import FileManifestStore

pytestmark = [pytest.mark.storage]


def _sample_manifest(manifest_id: str = "test-manifest-id") -> Manifest:
    source = DataSourceSpec(uri="/data", compute_hash=True)
    art = Artifact(
        artifact_id="art-1",
        source_uri="file:///data",
        artifact_type="file",
        relative_path="a.csv",
        absolute_path="/data/a.csv",
        size_bytes=100,
        mtime=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        content_hash="abc123",
        media_type="text/csv",
    )
    return Manifest(
        manifest_id=manifest_id,
        source=source,
        created_at=datetime(2024, 2, 1, 0, 0, 0, tzinfo=UTC),
        artifacts=[art],
        warnings=[],
    )


@pytest.mark.unit
def test_save_and_load_round_trip(tmp_path):
    """Save a manifest then load it; loaded manifest matches original."""
    store = FileManifestStore(base_dir=tmp_path)
    manifest = _sample_manifest(manifest_id="round-trip-id")

    store.save(manifest)
    loaded = store.load("round-trip-id")

    assert loaded.manifest_id == manifest.manifest_id
    assert loaded.source.uri == manifest.source.uri
    assert loaded.source.compute_hash == manifest.source.compute_hash
    assert loaded.created_at == manifest.created_at
    assert len(loaded.artifacts) == len(manifest.artifacts)
    assert loaded.artifacts[0].artifact_id == manifest.artifacts[0].artifact_id
    assert loaded.warnings == manifest.warnings


@pytest.mark.unit
def test_list_returns_saved_manifest_ids(tmp_path):
    """list() returns IDs of all saved manifests."""
    store = FileManifestStore(base_dir=tmp_path)
    assert store.list() == []

    store.save(_sample_manifest(manifest_id="id-1"))
    store.save(_sample_manifest(manifest_id="id-2"))
    ids = store.list()
    assert set(ids) == {"id-1", "id-2"}


@pytest.mark.unit
def test_load_missing_raises(tmp_path):
    """load() raises FileNotFoundError when manifest_id does not exist."""
    store = FileManifestStore(base_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="Manifest .* not found"):
        store.load("nonexistent-id")


@pytest.mark.unit
def test_delete_removes_manifest(tmp_path):
    """delete() removes the manifest file; load() then raises."""
    store = FileManifestStore(base_dir=tmp_path)
    store.save(_sample_manifest(manifest_id="to-delete"))
    assert "to-delete" in store.list()

    store.delete("to-delete")
    assert "to-delete" not in store.list()
    with pytest.raises(FileNotFoundError, match="Manifest .* not found"):
        store.load("to-delete")


@pytest.mark.unit
def test_delete_missing_raises(tmp_path):
    """delete() raises FileNotFoundError when manifest_id does not exist."""
    store = FileManifestStore(base_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="Manifest .* not found"):
        store.delete("nonexistent-id")


@pytest.mark.unit
def test_save_overwrites_existing(tmp_path):
    """Saving a manifest with same manifest_id overwrites the previous file."""
    store = FileManifestStore(base_dir=tmp_path)
    m1 = _sample_manifest(manifest_id="overwrite")
    m2 = _sample_manifest(manifest_id="overwrite")
    m2 = Manifest(
        manifest_id=m2.manifest_id,
        source=m2.source,
        created_at=m2.created_at,
        artifacts=[],
        warnings=["updated"],
    )

    store.save(m1)
    store.save(m2)
    loaded = store.load("overwrite")
    assert len(loaded.artifacts) == 0
    assert loaded.warnings == ["updated"]

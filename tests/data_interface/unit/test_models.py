"""
Unit tests for DataSourceSpec, Artifact, and Manifest.
Covers round-trip serialization (to_dict/from_dict) and validation (TypeError/ValueError).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from neurolab.data_interface.models import (
    Artifact,
    DataSourceSpec,
    Manifest,
)

pytestmark = [pytest.mark.data_interface]


# --- DataSourceSpec ---


@pytest.mark.unit
def test_data_source_spec_round_trip():
    """DataSourceSpec round-trips through to_dict and from_dict with all fields."""
    spec = DataSourceSpec(
        uri="/data",
        source_type="filesystem",
        include_globs=["*.csv"],
        exclude_globs=["*.tmp"],
        compute_hash=False,
        recursive=False,
        hints={"follow_symlinks": True},
    )
    d = spec.to_dict()
    restored = DataSourceSpec.from_dict(d)
    assert restored.uri == spec.uri
    assert restored.source_type == spec.source_type
    assert restored.include_globs == spec.include_globs
    assert restored.exclude_globs == spec.exclude_globs
    assert restored.compute_hash is False
    assert restored.recursive is False
    assert restored.hints == spec.hints


@pytest.mark.unit
def test_data_source_spec_from_dict_defaults():
    """DataSourceSpec.from_dict uses defaults for optional fields including compute_hash."""
    d = {"uri": "/path"}
    spec = DataSourceSpec.from_dict(d)
    assert spec.uri == "/path"
    assert spec.source_type == "filesystem"
    assert spec.compute_hash is True
    assert spec.recursive is True
    assert spec.include_globs is None
    assert spec.exclude_globs is None
    assert spec.hints == {}


@pytest.mark.unit
def test_data_source_spec_from_dict_not_dict_raises():
    """DataSourceSpec.from_dict raises TypeError when input is not a dict."""
    with pytest.raises(TypeError, match="must be a dictionary"):
        DataSourceSpec.from_dict(None)
    with pytest.raises(TypeError, match="must be a dictionary"):
        DataSourceSpec.from_dict("uri")  # type: ignore[arg-type]


@pytest.mark.unit
def test_data_source_spec_from_dict_missing_uri_raises():
    """DataSourceSpec.from_dict raises ValueError when uri is missing."""
    with pytest.raises(ValueError, match="Missing required field: uri"):
        DataSourceSpec.from_dict({})


@pytest.mark.unit
def test_data_source_spec_from_dict_invalid_source_type_raises():
    """DataSourceSpec.from_dict raises ValueError for invalid source_type."""
    with pytest.raises(ValueError, match="Invalid source_type"):
        DataSourceSpec.from_dict({"uri": "/x", "source_type": "s3"})


# --- Artifact ---


def _artifact_dict(
    artifact_id: str = "aid-1",
    source_uri: str = "file:///data",
    artifact_type: str = "file",
    relative_path: str | None = "a.csv",
    absolute_path: str | None = "/data/a.csv",
    size_bytes: int | None = 100,
    mtime: str | None = "2024-01-01T12:00:00+00:00",
    content_hash: str | None = "abc123",
    media_type: str | None = "text/csv",
    tags: dict | None = None,
) -> dict:
    return {
        "artifact_id": artifact_id,
        "source_uri": source_uri,
        "artifact_type": artifact_type,
        "relative_path": relative_path,
        "absolute_path": absolute_path,
        "size_bytes": size_bytes,
        "mtime": mtime,
        "content_hash": content_hash,
        "media_type": media_type,
        "tags": tags or {},
    }


@pytest.mark.unit
def test_artifact_round_trip():
    """Artifact round-trips through to_dict and from_dict."""
    art = Artifact(
        artifact_id="aid-1",
        source_uri="file:///data",
        artifact_type="file",
        relative_path="sub/a.csv",
        absolute_path="/data/sub/a.csv",
        size_bytes=42,
        mtime=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        content_hash="sha256:abc",
        media_type="text/csv",
        tags={"env": "test"},
    )
    d = art.to_dict()
    restored = Artifact.from_dict(d)
    assert restored.artifact_id == art.artifact_id
    assert restored.source_uri == art.source_uri
    assert restored.artifact_type == art.artifact_type
    assert restored.relative_path == art.relative_path
    assert restored.absolute_path == art.absolute_path
    assert restored.size_bytes == art.size_bytes
    assert restored.mtime == art.mtime
    assert restored.content_hash == art.content_hash
    assert restored.media_type == art.media_type
    assert restored.tags == art.tags


@pytest.mark.unit
def test_artifact_from_dict_optional_none():
    """Artifact.from_dict accepts None for optional fields."""
    d = _artifact_dict(
        relative_path=None,
        absolute_path=None,
        size_bytes=None,
        mtime=None,
        content_hash=None,
        media_type=None,
    )
    art = Artifact.from_dict(d)
    assert art.relative_path is None
    assert art.absolute_path is None
    assert art.size_bytes is None
    assert art.mtime is None
    assert art.content_hash is None
    assert art.media_type is None


@pytest.mark.unit
def test_artifact_from_dict_not_dict_raises():
    """Artifact.from_dict raises TypeError when input is not a dict."""
    with pytest.raises(TypeError, match="must be a dictionary"):
        Artifact.from_dict([])  # type: ignore[arg-type]


@pytest.mark.unit
def test_artifact_from_dict_missing_required_raises():
    """Artifact.from_dict raises ValueError when required fields are missing."""
    base = _artifact_dict()
    for key in ("artifact_id", "source_uri", "artifact_type"):
        bad = {k: v for k, v in base.items() if k != key}
        with pytest.raises(ValueError, match=f"Missing required field: {key}"):
            Artifact.from_dict(bad)


@pytest.mark.unit
def test_artifact_from_dict_invalid_artifact_type_raises():
    """Artifact.from_dict raises ValueError for invalid artifact_type."""
    d = _artifact_dict(artifact_type="unknown")
    with pytest.raises(ValueError, match="Invalid artifact_type"):
        Artifact.from_dict(d)


@pytest.mark.unit
def test_artifact_from_dict_naive_mtime_raises():
    """Artifact.from_dict raises ValueError when mtime is timezone-naive."""
    d = _artifact_dict(mtime="2024-01-01T12:00:00")  # no TZ
    with pytest.raises(ValueError, match="mtime must be timezone-aware"):
        Artifact.from_dict(d)


@pytest.mark.unit
def test_artifact_from_dict_db_table():
    """Artifact.from_dict accepts artifact_type db_table."""
    d = _artifact_dict(artifact_type="db_table")
    art = Artifact.from_dict(d)
    assert art.artifact_type == "db_table"


# --- Manifest ---


@pytest.mark.unit
def test_manifest_round_trip():
    """Manifest round-trips through to_dict and from_dict."""
    source = DataSourceSpec(uri="/data", compute_hash=True)
    art = Artifact(
        artifact_id="a1",
        source_uri="file:///data",
        artifact_type="file",
        relative_path="x.csv",
        absolute_path="/data/x.csv",
        size_bytes=10,
        mtime=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        content_hash="h1",
        media_type="text/csv",
    )
    manifest = Manifest(
        manifest_id="mid-1",
        source=source,
        created_at=datetime(2024, 2, 1, 0, 0, 0, tzinfo=UTC),
        artifacts=[art],
        warnings=["w1"],
    )
    d = manifest.to_dict()
    restored = Manifest.from_dict(d)
    assert restored.manifest_id == manifest.manifest_id
    assert restored.source.uri == manifest.source.uri
    assert restored.source.compute_hash == manifest.source.compute_hash
    assert restored.created_at == manifest.created_at
    assert len(restored.artifacts) == 1
    assert restored.artifacts[0].artifact_id == art.artifact_id
    assert restored.warnings == manifest.warnings


@pytest.mark.unit
def test_manifest_artifact_count():
    """Manifest.artifact_count returns len(artifacts)."""
    source = DataSourceSpec(uri="/data")
    manifest = Manifest(
        manifest_id="m1",
        source=source,
        created_at=datetime.now(UTC),
        artifacts=[],
    )
    assert manifest.artifact_count == 0
    art = Artifact(
        source_uri="file:///d",
        artifact_type="file",
        relative_path="f",
        absolute_path="/d/f",
        size_bytes=1,
        mtime=None,
        content_hash=None,
        media_type=None,
    )
    manifest2 = Manifest(
        manifest_id="m2",
        source=source,
        created_at=datetime.now(UTC),
        artifacts=[art, art],
    )
    assert manifest2.artifact_count == 2


@pytest.mark.unit
def test_manifest_from_dict_not_dict_raises():
    """Manifest.from_dict raises TypeError when input is not a dict."""
    with pytest.raises(TypeError, match="must be a dictionary"):
        Manifest.from_dict("x")  # type: ignore[arg-type]


@pytest.mark.unit
def test_manifest_from_dict_missing_required_raises():
    """Manifest.from_dict raises ValueError when required fields are missing."""
    base = {
        "manifest_id": "m1",
        "source": {"uri": "/data"},
        "created_at": "2024-01-01T00:00:00+00:00",
        "artifacts": [],
    }
    for key in ("manifest_id", "source", "created_at", "artifacts"):
        bad = {k: v for k, v in base.items() if k != key}
        with pytest.raises(ValueError, match=f"Missing required field: {key}"):
            Manifest.from_dict(bad)


@pytest.mark.unit
def test_manifest_from_dict_naive_created_at_raises():
    """Manifest.from_dict raises ValueError when created_at is timezone-naive."""
    d = {
        "manifest_id": "m1",
        "source": {"uri": "/data"},
        "created_at": "2024-01-01T00:00:00",  # no TZ
        "artifacts": [],
    }
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        Manifest.from_dict(d)

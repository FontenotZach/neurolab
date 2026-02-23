import pytest

from neurolab.data_interface.models import DataSourceSpec
from neurolab.data_interface.orchestrator import collect_source


@pytest.mark.integration
def test_collect_source_filesystem_basic(tmp_path):
    (tmp_path / "a.txt").write_text("data")

    source = DataSourceSpec(uri=str(tmp_path))
    manifest = collect_source(source)

    assert len(manifest.artifacts) == 1
    artifact = next(iter(manifest.artifacts))
    assert artifact.content_hash is not None


@pytest.mark.integration
def test_collect_source_respects_compute_hash_false(tmp_path):
    (tmp_path / "a.txt").write_text("data")

    source = DataSourceSpec(uri=str(tmp_path), compute_hash=False)
    manifest = collect_source(source)

    assert len(manifest.artifacts) == 1
    artifact = next(iter(manifest.artifacts))
    assert artifact.content_hash is None


@pytest.mark.integration
def test_collect_source_recursive(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_text("data")

    source = DataSourceSpec(uri=str(tmp_path), recursive=True)
    manifest = collect_source(source)

    assert len(manifest.artifacts) == 1
    assert any(a.relative_path is not None and a.relative_path.endswith("nested.txt") for a in manifest.artifacts)


@pytest.mark.integration
def test_collect_source_non_recursive(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_text("data")

    source = DataSourceSpec(uri=str(tmp_path), recursive=False)
    manifest = collect_source(source)

    assert len(manifest.artifacts) == 0


@pytest.mark.integration
def test_collect_source_unknown_type_raises():
    source = DataSourceSpec(uri="x", source_type="unknown")

    with pytest.raises(ValueError):
        collect_source(source)

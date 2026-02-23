import pytest

from neurolab.data_interface.models import DataSourceSpec
from neurolab.data_interface.orchestrator import collect_source


@pytest.fixture
def test_data_dir(tmp_path):
    """
    Create a small file tree for collector testing.
    Structure:
        root/
            foo.txt
            bar.bin
            sub/
                baz.txt
    """
    (tmp_path / "foo.txt").write_text("foo")
    (tmp_path / "bar.bin").write_bytes(b"\x00\x01")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "baz.txt").write_text("baz")
    return tmp_path


def test_collect_non_recursive(test_data_dir):
    source = DataSourceSpec(uri=str(test_data_dir), recursive=False)
    manifest = collect_source(source)

    # Only top-level files should be collected
    assert len(manifest.artifacts) == 2

    relative_paths = {a.relative_path for a in manifest.artifacts}
    assert "foo.txt" in relative_paths
    assert "bar.bin" in relative_paths
    assert "sub/baz.txt" not in relative_paths


def test_collect_recursive(test_data_dir):
    source = DataSourceSpec(uri=str(test_data_dir), recursive=True)
    manifest = collect_source(source)

    assert len(manifest.artifacts) == 3

    relative_paths = {a.relative_path for a in manifest.artifacts}
    assert "foo.txt" in relative_paths
    assert "bar.bin" in relative_paths
    assert "sub/baz.txt" in relative_paths


def test_hashes_exist(test_data_dir):
    source = DataSourceSpec(uri=str(test_data_dir))
    manifest = collect_source(source)

    for artifact in manifest.artifacts:
        assert artifact.content_hash is not None
        assert isinstance(artifact.content_hash, str)


def test_include_globs(test_data_dir):
    source = DataSourceSpec(
        uri=str(test_data_dir),
        include_globs=["**/*.txt"],
        recursive=True,
    )
    manifest = collect_source(source)

    relative_paths = {a.relative_path for a in manifest.artifacts}

    assert "foo.txt" in relative_paths
    assert "sub/baz.txt" in relative_paths
    assert "bar.bin" not in relative_paths


def test_exclude_globs(test_data_dir):
    source = DataSourceSpec(
        uri=str(test_data_dir),
        exclude_globs=["**/*.bin"],
        recursive=True,
    )
    manifest = collect_source(source)

    relative_paths = {a.relative_path for a in manifest.artifacts}

    assert "bar.bin" not in relative_paths
    assert "foo.txt" in relative_paths
    assert "sub/baz.txt" in relative_paths

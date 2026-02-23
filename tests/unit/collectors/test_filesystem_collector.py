import pytest

from neurolab.data_interface.collectors import FilesystemCollector
from neurolab.data_interface.models import DataSourceSpec


def _hash_map(manifest):
    """
    Helper to map relative_path -> content_hash
    Ensures tests don't rely on artifact ordering.
    """
    return {a.relative_path: a.content_hash for a in manifest.artifacts}


@pytest.mark.unit
def test_deterministic_hashing(tmp_path):
    file = tmp_path / "a.txt"
    file.write_text("hello")

    source = DataSourceSpec(uri=str(tmp_path))
    collector = FilesystemCollector()

    m1 = collector.collect(source)
    m2 = collector.collect(source)

    assert _hash_map(m1) == _hash_map(m2)


@pytest.mark.unit
def test_hash_changes_when_file_modified(tmp_path):
    file = tmp_path / "a.txt"
    file.write_text("hello")

    source = DataSourceSpec(uri=str(tmp_path))
    collector = FilesystemCollector()

    m1 = collector.collect(source)
    hash_before = _hash_map(m1)["a.txt"]

    file.write_text("goodbye")
    m2 = collector.collect(source)
    hash_after = _hash_map(m2)["a.txt"]

    assert hash_before != hash_after


@pytest.mark.unit
def test_recursive_logic(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_text("data")

    collector = FilesystemCollector()

    source_non_recursive = DataSourceSpec(uri=str(tmp_path), recursive=False)
    m_non_recursive = collector.collect(source_non_recursive)
    assert len(m_non_recursive.artifacts) == 0

    source_recursive = DataSourceSpec(uri=str(tmp_path), recursive=True)
    m_recursive = collector.collect(source_recursive)
    assert len(m_recursive.artifacts) == 1
    paths = [a.relative_path for a in m_recursive.artifacts]
    assert any(p is not None and p.endswith("nested.txt") for p in paths)


@pytest.mark.unit
def test_include_exclude(tmp_path):
    (tmp_path / "a.txt").write_text("data")
    (tmp_path / "b.log").write_text("data")

    source = DataSourceSpec(
        uri=str(tmp_path),
        include_globs=["*.txt"],
        exclude_globs=["*.log"],
    )

    collector = FilesystemCollector()
    m = collector.collect(source)

    paths = [a.relative_path for a in m.artifacts]

    assert len(paths) == 1
    assert paths[0].endswith("a.txt")


@pytest.mark.unit
def test_empty_directory(tmp_path):
    source = DataSourceSpec(uri=str(tmp_path))
    collector = FilesystemCollector()

    m = collector.collect(source)

    assert m.artifacts == []
    assert m.warnings == []

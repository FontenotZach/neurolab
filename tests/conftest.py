from pathlib import Path

import pytest


@pytest.fixture
def structured_test_dir(tmp_path):
    """
    Create a reusable test file tree:
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


@pytest.fixture(scope="session")
def project_test_data_dir():
    """Path to the project's test_data directory at repo root (for integration tests)."""
    repo_root = Path(__file__).resolve().parent.parent
    return repo_root / "test_data"

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

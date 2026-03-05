"""
Unit tests for hash_file_sha256.
Verifies deterministic hashing and chunked reading for known content.
"""

from __future__ import annotations

import hashlib

import pytest

from neurolab.data_interface.hashing import hash_file_sha256

pytestmark = [pytest.mark.data_interface]


@pytest.mark.unit
def test_known_content_deterministic(tmp_path):
    """Known file content produces the same hash every time."""
    f = tmp_path / "fixed.txt"
    f.write_text("hello")
    h1 = hash_file_sha256(f)
    h2 = hash_file_sha256(f)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest


@pytest.mark.unit
def test_known_content_matches_expected(tmp_path):
    """Hash of 'hello' matches precomputed SHA-256 hex digest."""
    f = tmp_path / "hello.txt"
    f.write_text("hello")
    expected = hashlib.sha256(b"hello").hexdigest()
    assert hash_file_sha256(f) == expected


@pytest.mark.unit
def test_different_content_different_hash(tmp_path):
    """Different file contents produce different hashes."""
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("alpha")
    b.write_text("beta")
    assert hash_file_sha256(a) != hash_file_sha256(b)


@pytest.mark.unit
def test_empty_file(tmp_path):
    """Empty file has well-defined SHA-256 hash."""
    f = tmp_path / "empty"
    f.write_bytes(b"")
    expected = hashlib.sha256(b"").hexdigest()
    assert hash_file_sha256(f) == expected

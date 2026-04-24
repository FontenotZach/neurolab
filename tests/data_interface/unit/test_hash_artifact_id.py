"""Unit tests for deterministic artifact_id (hash_artifact_id)."""

from __future__ import annotations

import pytest

from neurolab.data_interface.hashing import hash_artifact_id

pytestmark = [pytest.mark.data_interface, pytest.mark.unit]


def test_same_content_and_path_same_id():
    a = hash_artifact_id(
        content_hash="abc",
        relative_path="session/data.csv",
        absolute_path="/x/session/data.csv",
    )
    b = hash_artifact_id(
        content_hash="abc",
        relative_path="session/data.csv",
        absolute_path="/other/session/data.csv",
    )
    assert a == b
    assert len(a) == 64


def test_different_relative_path_different_id():
    a = hash_artifact_id(content_hash="x", relative_path="a.txt")
    b = hash_artifact_id(content_hash="x", relative_path="b.txt")
    assert a != b


def test_content_change_changes_id():
    a = hash_artifact_id(content_hash="h1", relative_path="f.csv")
    b = hash_artifact_id(content_hash="h2", relative_path="f.csv")
    assert a != b


def test_single_file_uses_basename_when_relative_path_none():
    a = hash_artifact_id(
        content_hash="z",
        relative_path=None,
        absolute_path="/tmp/only.csv",
    )
    b = hash_artifact_id(
        content_hash="z",
        relative_path="only.csv",
        absolute_path="/elsewhere/only.csv",
    )
    assert a == b


def test_warns_when_no_content_hash_uses_size(tmp_path):
    with pytest.warns(UserWarning, match="content_hash unavailable"):
        hid = hash_artifact_id(
            content_hash=None,
            relative_path="x.bin",
            absolute_path=str(tmp_path / "x.bin"),
            size_bytes=42,
        )
    assert len(hid) == 64

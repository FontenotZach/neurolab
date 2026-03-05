"""
Unit tests for _infer_media_type helper.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from neurolab.data_interface.collectors import _infer_media_type

pytestmark = [pytest.mark.data_interface]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("data.csv", "text/csv"),
        ("data.tsv", "text/tab-separated-values"),
        ("config.json", "application/json"),
        ("stream.jsonl", "application/x-ndjson"),
        ("table.parquet", "application/parquet"),
        ("notes.txt", "text/plain"),
        ("readme.md", "text/markdown"),
        ("config.yaml", "application/x-yaml"),
        ("config.yml", "application/x-yaml"),
        ("db.sqlite", "application/x-sqlite3"),
        ("archive.zip", "application/zip"),
        ("archive.gz", "application/gzip"),
        ("archive.tar", "application/x-tar"),
    ],
)
def test_known_extensions(filename, expected):
    assert _infer_media_type(Path(filename)) == expected


@pytest.mark.unit
def test_unknown_extension_returns_none():
    assert _infer_media_type(Path("image.bmp")) is None


@pytest.mark.unit
def test_case_insensitive():
    assert _infer_media_type(Path("DATA.CSV")) == "text/csv"
    assert _infer_media_type(Path("Config.JSON")) == "application/json"

"""
Unit tests for RosterStore.
Covers load, save, add, remove, get, next_slot, and edge cases.
"""

from __future__ import annotations

import json

import pytest

from neurolab.storage.roster_store import RosterStore

pytestmark = [pytest.mark.storage]


@pytest.mark.unit
def test_load_empty_when_no_file(tmp_path):
    """load() returns empty dict when the roster file does not exist."""
    store = RosterStore(path=tmp_path / "roster.json")
    assert store.load() == {}


@pytest.mark.unit
def test_save_and_load_round_trip(tmp_path):
    """Entries saved with save() are returned by load()."""
    store = RosterStore(path=tmp_path / "roster.json")
    entries = {"r1": "manifest-aaa", "r2": "manifest-bbb"}
    store.save(entries)
    assert store.load() == entries


@pytest.mark.unit
def test_add_persists_entry(tmp_path):
    """add() writes an alias that can be read back."""
    store = RosterStore(path=tmp_path / "roster.json")
    store.add("r1", "mid-1")
    assert store.load() == {"r1": "mid-1"}


@pytest.mark.unit
def test_add_overwrites_existing_alias(tmp_path):
    """add() with an existing alias overwrites the previous value."""
    store = RosterStore(path=tmp_path / "roster.json")
    store.add("r1", "mid-old")
    store.add("r1", "mid-new")
    assert store.load() == {"r1": "mid-new"}


@pytest.mark.unit
def test_get_returns_manifest_id(tmp_path):
    """get() returns the manifest_id for a known alias."""
    store = RosterStore(path=tmp_path / "roster.json")
    store.add("baseline", "mid-123")
    assert store.get("baseline") == "mid-123"


@pytest.mark.unit
def test_get_returns_none_for_missing(tmp_path):
    """get() returns None when the alias is not in the roster."""
    store = RosterStore(path=tmp_path / "roster.json")
    assert store.get("nonexistent") is None


@pytest.mark.unit
def test_remove_deletes_alias(tmp_path):
    """remove() deletes the alias from the roster."""
    store = RosterStore(path=tmp_path / "roster.json")
    store.add("r1", "mid-1")
    store.add("r2", "mid-2")
    store.remove("r1")
    assert store.load() == {"r2": "mid-2"}


@pytest.mark.unit
def test_remove_noop_for_missing(tmp_path):
    """remove() is a no-op when the alias doesn't exist."""
    store = RosterStore(path=tmp_path / "roster.json")
    store.add("r1", "mid-1")
    store.remove("nonexistent")
    assert store.load() == {"r1": "mid-1"}


@pytest.mark.unit
def test_next_slot_starts_at_r1(tmp_path):
    """next_slot() returns 'r1' when the roster is empty."""
    store = RosterStore(path=tmp_path / "roster.json")
    assert store.next_slot() == "r1"


@pytest.mark.unit
def test_next_slot_fills_gaps(tmp_path):
    """next_slot() returns the first free slot (e.g. r2 if r1 is taken)."""
    store = RosterStore(path=tmp_path / "roster.json")
    store.add("r1", "mid-1")
    store.add("r3", "mid-3")
    assert store.next_slot() == "r2"


@pytest.mark.unit
def test_next_slot_increments_past_existing(tmp_path):
    """next_slot() returns r3 when r1 and r2 are taken."""
    store = RosterStore(path=tmp_path / "roster.json")
    store.add("r1", "mid-1")
    store.add("r2", "mid-2")
    assert store.next_slot() == "r3"


@pytest.mark.unit
def test_load_returns_empty_for_corrupt_json(tmp_path):
    """load() returns empty dict when roster file contains non-dict JSON."""
    roster_path = tmp_path / "roster.json"
    roster_path.write_text(json.dumps(["not", "a", "dict"]))
    store = RosterStore(path=roster_path)
    assert store.load() == {}

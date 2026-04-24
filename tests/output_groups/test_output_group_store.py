from __future__ import annotations

import json
from pathlib import Path

import pytest

from neurolab.output_groups import OutputGroup, OutputGroupCatalog
from neurolab.output_groups.store import FileOutputGroupCatalogStore


def g(group_id: str, *, group_type: str = "t", parent: str | None = None) -> OutputGroup:
    return OutputGroup(
        group_id=group_id,
        group_type=group_type,
        member_provenance_ids=("p1",),
        parent_group_id=parent,
        label=None,
        metadata={},
    )


def catalog_path(root: Path) -> Path:
    return root / "output_groups" / "catalog.json"


def test_load_missing_store_returns_empty_catalog(tmp_path: Path) -> None:
    store = FileOutputGroupCatalogStore(tmp_path)
    c = store.load()
    assert isinstance(c, OutputGroupCatalog)
    assert len(c) == 0


def test_save_creates_catalog_file(tmp_path: Path) -> None:
    store = FileOutputGroupCatalogStore(tmp_path)
    store.save(OutputGroupCatalog([g("group:a")]))
    assert catalog_path(tmp_path).is_file()


def test_save_then_load_round_trips_groups(tmp_path: Path) -> None:
    store = FileOutputGroupCatalogStore(tmp_path)
    original = OutputGroupCatalog([g("group:a", group_type="type_a"), g("group:b", group_type="type_b", parent="group:a")])
    store.save(original)
    loaded = store.load()
    assert [x.group_id for x in loaded.list()] == ["group:a", "group:b"]
    assert loaded.get("group:a").group_type == "type_a"
    assert loaded.get("group:b").parent_group_id == "group:a"


def test_groups_are_written_sorted_by_group_id(tmp_path: Path) -> None:
    store = FileOutputGroupCatalogStore(tmp_path)
    store.save(OutputGroupCatalog([g("group:b"), g("group:a"), g("group:c")]))
    data = json.loads(catalog_path(tmp_path).read_text(encoding="utf-8"))
    assert [x["group_id"] for x in data["groups"]] == ["group:a", "group:b", "group:c"]


def test_exists_reflects_file_presence(tmp_path: Path) -> None:
    store = FileOutputGroupCatalogStore(tmp_path)
    assert store.exists() is False
    store.save(OutputGroupCatalog([g("group:a")]))
    assert store.exists() is True


def test_delete_removes_catalog_file(tmp_path: Path) -> None:
    store = FileOutputGroupCatalogStore(tmp_path)
    store.save(OutputGroupCatalog([g("group:a")]))
    assert store.exists() is True
    store.delete()
    assert store.exists() is False


def test_delete_is_safe_when_missing(tmp_path: Path) -> None:
    store = FileOutputGroupCatalogStore(tmp_path)
    store.delete()
    assert store.exists() is False


def test_invalid_schema_version_raises_value_error(tmp_path: Path) -> None:
    p = catalog_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"schema_version": 2, "groups": []}), encoding="utf-8")
    store = FileOutputGroupCatalogStore(tmp_path)
    with pytest.raises(ValueError):
        store.load()


def test_invalid_groups_shape_raises_value_error(tmp_path: Path) -> None:
    p = catalog_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"schema_version": 1, "groups": {}}), encoding="utf-8")
    store = FileOutputGroupCatalogStore(tmp_path)
    with pytest.raises(ValueError):
        store.load()


def test_duplicate_group_ids_in_file_raise_value_error(tmp_path: Path) -> None:
    p = catalog_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "schema_version": 1,
        "groups": [
            {
                "group_id": "group:a",
                "group_type": "type_a",
                "member_provenance_ids": ["p1"],
                "parent_group_id": None,
                "label": None,
                "metadata": {},
            },
            {
                "group_id": "group:a",
                "group_type": "type_a",
                "member_provenance_ids": ["p2"],
                "parent_group_id": None,
                "label": None,
                "metadata": {},
            },
        ],
    }
    p.write_text(json.dumps(body), encoding="utf-8")
    store = FileOutputGroupCatalogStore(tmp_path)
    with pytest.raises(ValueError):
        store.load()

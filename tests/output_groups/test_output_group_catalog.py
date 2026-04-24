from __future__ import annotations

import pytest

from neurolab.output_groups import OutputGroup
from neurolab.output_groups.catalog import OutputGroupCatalog


def g_a() -> OutputGroup:
    return OutputGroup(
        group_id="group:a",
        group_type="type_a",
        member_provenance_ids=("p1",),
    )


def g_b() -> OutputGroup:
    return OutputGroup(
        group_id="group:b",
        group_type="type_b",
        member_provenance_ids=("p2",),
        parent_group_id="group:a",
    )


def g_c_type_a() -> OutputGroup:
    return OutputGroup(
        group_id="group:c",
        group_type="type_a",
        member_provenance_ids=("p3",),
        parent_group_id="group:a",
    )


def test_empty_catalog_has_length_0() -> None:
    c = OutputGroupCatalog()
    assert len(c) == 0


def test_constructor_accepts_initial_groups() -> None:
    c = OutputGroupCatalog([g_b(), g_a()])
    assert len(c) == 2
    assert c.get("group:a").group_type == "type_a"
    assert c.get("group:b").parent_group_id == "group:a"


def test_add_inserts_group() -> None:
    c = OutputGroupCatalog()
    c.add(g_a())
    assert len(c) == 1
    assert c.get("group:a").group_id == "group:a"


def test_add_rejects_duplicate_group_id() -> None:
    c = OutputGroupCatalog([g_a()])
    with pytest.raises(ValueError):
        c.add(g_a())


def test_add_many_inserts_multiple_groups() -> None:
    c = OutputGroupCatalog()
    c.add_many([g_a(), g_b()])
    assert len(c) == 2
    assert c.get("group:a").group_id == "group:a"
    assert c.get("group:b").group_id == "group:b"


def test_get_returns_group() -> None:
    c = OutputGroupCatalog([g_a()])
    assert c.get("group:a") == g_a()


def test_get_raises_keyerror_for_missing_group() -> None:
    c = OutputGroupCatalog()
    with pytest.raises(KeyError):
        c.get("missing")


def test_maybe_get_returns_none_for_missing_group() -> None:
    c = OutputGroupCatalog()
    assert c.maybe_get("missing") is None


def test_list_returns_groups_sorted_by_group_id() -> None:
    c = OutputGroupCatalog([g_b(), g_a(), g_c_type_a()])
    assert [g.group_id for g in c.list()] == ["group:a", "group:b", "group:c"]


def test_by_type_filters_and_sorts() -> None:
    c = OutputGroupCatalog([g_b(), g_a(), g_c_type_a()])
    assert [g.group_id for g in c.by_type("type_a")] == ["group:a", "group:c"]


def test_roots_returns_groups_with_no_parent() -> None:
    c = OutputGroupCatalog([g_b(), g_a(), g_c_type_a()])
    assert [g.group_id for g in c.roots()] == ["group:a"]


def test_children_of_returns_matching_children() -> None:
    c = OutputGroupCatalog([g_b(), g_a(), g_c_type_a()])
    assert [g.group_id for g in c.children_of("group:a")] == ["group:b", "group:c"]


def test_children_of_does_not_require_parent_exists() -> None:
    orphan = OutputGroup(
        group_id="group:orphan",
        group_type="type_x",
        member_provenance_ids=("p9",),
        parent_group_id="group:missing",
    )
    c = OutputGroupCatalog([orphan])
    assert [g.group_id for g in c.children_of("group:missing")] == ["group:orphan"]


def test_remove_deletes_and_returns_group() -> None:
    c = OutputGroupCatalog([g_a(), g_b()])
    removed = c.remove("group:b")
    assert removed.group_id == "group:b"
    assert len(c) == 1
    with pytest.raises(KeyError):
        c.get("group:b")


def test_clear_removes_all_groups() -> None:
    c = OutputGroupCatalog([g_a(), g_b()])
    c.clear()
    assert len(c) == 0
    assert c.list() == []


def test_contains_works_for_string_ids() -> None:
    c = OutputGroupCatalog([g_a()])
    assert "group:a" in c
    assert "missing" not in c
    assert 123 not in c

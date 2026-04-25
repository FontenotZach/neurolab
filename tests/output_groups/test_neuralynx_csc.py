from __future__ import annotations

from dataclasses import dataclass

import pytest

from neurolab.output_groups.builders.neuralynx_csc import (
    NEURALYNX_CSC_EXPERIMENT,
    NEURALYNX_TETRODE,
    NeuralynxCSCGroupRequest,
    NeuralynxCSCOutputGroupBuilder,
)


@dataclass(frozen=True, slots=True)
class FakeRecord:
    provenance_id: str
    adapter_name: str
    schema: dict
    record_kind: str = "original"


class FakeHub:
    def __init__(self, records: list[FakeRecord]) -> None:
        self._records = records

    def list_records(self, *, include_derived: bool = False) -> list[FakeRecord]:
        if include_derived:
            return list(self._records)
        return [r for r in self._records if r.record_kind == "original"]


def rec(pid: str, relative_path: str, *, fmt: str | None = "neuralynx_ncs") -> FakeRecord:
    schema: dict = {"relative_path": relative_path}
    if fmt is not None:
        schema["format"] = fmt
    return FakeRecord(provenance_id=pid, adapter_name="ncs_adapter", schema=schema)


def test_csc1_to_csc8_creates_experiment_and_two_tetrodes() -> None:
    hub = FakeHub([rec(f"p{i}", f"exp/CSC{i}.ncs") for i in range(1, 9)])
    b = NeuralynxCSCOutputGroupBuilder()

    groups = b.build(hub, NeuralynxCSCGroupRequest())
    exp = [g for g in groups if g.group_type == NEURALYNX_CSC_EXPERIMENT]
    tet = [g for g in groups if g.group_type == NEURALYNX_TETRODE]

    assert len(exp) == 1
    assert len(tet) == 2
    assert exp[0].group_id == f"{NEURALYNX_CSC_EXPERIMENT}:exp"
    assert tet[0].parent_group_id == exp[0].group_id
    assert tet[1].parent_group_id == exp[0].group_id


def test_non_csc_files_are_ignored() -> None:
    hub = FakeHub(
        [
            rec("p1", "exp/CSC1.ncs"),
            rec("p2", "exp/CSCfoo.ncs"),
            rec("p3", "exp/readme.txt"),
            rec("p4", "exp/CSC2.ncs"),
        ]
    )
    b = NeuralynxCSCOutputGroupBuilder()
    groups = b.build(hub, NeuralynxCSCGroupRequest())
    assert [g.group_type for g in groups] == [NEURALYNX_CSC_EXPERIMENT]
    assert groups[0].member_provenance_ids == ("p1", "p4")


def test_folders_with_only_one_csc_file_are_ignored() -> None:
    hub = FakeHub(
        [
            rec("p1", "a/CSC1.ncs"),
            rec("p2", "b/CSC1.ncs"),
            rec("p3", "b/CSC2.ncs"),
        ]
    )
    b = NeuralynxCSCOutputGroupBuilder()
    groups = b.build(hub, NeuralynxCSCGroupRequest(min_csc_files_per_experiment=2))
    assert len(groups) == 1
    assert groups[0].group_type == NEURALYNX_CSC_EXPERIMENT
    assert groups[0].group_id == f"{NEURALYNX_CSC_EXPERIMENT}:b"


def test_select_preserves_hub_order() -> None:
    hub = FakeHub(
        [
            rec("p1", "b/CSC1.ncs"),
            rec("p2", "a/CSC1.ncs"),
            rec("p3", "a/CSC2.ncs"),
            rec("p4", "b/CSC2.ncs"),
        ]
    )
    b = NeuralynxCSCOutputGroupBuilder()
    sel = b.select(hub, NeuralynxCSCGroupRequest())
    assert sel.selected_provenance_ids == ("p1", "p2", "p3", "p4")


def test_build_sorts_tetrode_members_by_channel_number() -> None:
    hub = FakeHub(
        [
            rec("p4", "exp/CSC4.ncs"),
            rec("p1", "exp/CSC1.ncs"),
            rec("p3", "exp/CSC3.ncs"),
            rec("p2", "exp/CSC2.ncs"),
        ]
    )
    b = NeuralynxCSCOutputGroupBuilder()
    groups = b.build(hub, NeuralynxCSCGroupRequest())
    tet = [g for g in groups if g.group_type == NEURALYNX_TETRODE]
    assert len(tet) == 1
    assert tet[0].member_provenance_ids == ("p1", "p2", "p3", "p4")


def test_padded_names_resolve_to_channel_1() -> None:
    hub = FakeHub([rec("p1", "exp/CSC01.ncs"), rec("p2", "exp/CSC02.ncs")])
    b = NeuralynxCSCOutputGroupBuilder()
    groups = b.build(hub, NeuralynxCSCGroupRequest())
    assert groups[0].metadata["channel_numbers"] == [1, 2]


def test_parentheses_name_resolves_without_special_logic() -> None:
    hub = FakeHub([rec("p1", "exp/CSC(0)1.ncs"), rec("p2", "exp/CSC2.ncs")])
    b = NeuralynxCSCOutputGroupBuilder()
    groups = b.build(hub, NeuralynxCSCGroupRequest())
    assert groups[0].metadata["channel_numbers"] == [1, 2]


def test_nested_folders_normalize_relative_folder_to_posix() -> None:
    hub = FakeHub(
        [
            rec("p1", r"nest\sub\CSC1.ncs"),
            rec("p2", "nest/sub/CSC2.ncs"),
        ]
    )
    b = NeuralynxCSCOutputGroupBuilder()
    groups = b.build(hub, NeuralynxCSCGroupRequest())
    assert groups[0].group_id == f"{NEURALYNX_CSC_EXPERIMENT}:nest/sub"
    assert groups[0].metadata["relative_folder"] == "nest/sub"


def test_include_incomplete_tetrodes_raises_for_now() -> None:
    hub = FakeHub([rec("p1", "exp/CSC1.ncs"), rec("p2", "exp/CSC2.ncs")])
    b = NeuralynxCSCOutputGroupBuilder()
    with pytest.raises(NotImplementedError):
        b.build(hub, NeuralynxCSCGroupRequest(include_incomplete_tetrodes=True))

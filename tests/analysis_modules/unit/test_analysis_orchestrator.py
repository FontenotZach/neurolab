"""Tests for analysis module orchestration."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from neurolab.analysis_hub.interfaces import AnalysisHub
from neurolab.analysis_modules.models import AnalysisModuleDescription, AnalysisRunResult, SelectionResult
from neurolab.analysis_modules.orchestrator import run_analysis_module
from neurolab.storage.analysis_results.file_store import FileAnalysisResultStore


class _FakeModule:
    module_name = "fake_mod"
    module_version = "0.1.0"

    def __init__(self) -> None:
        self.select_calls = 0
        self.last_run_selection: SelectionResult | None = None

    def describe(self) -> AnalysisModuleDescription:
        return AnalysisModuleDescription(
            module_name=self.module_name,
            module_version=self.module_version,
            summary="fake",
        )

    def select(self, hub: AnalysisHub, request: dict[str, Any]) -> SelectionResult:
        self.select_calls += 1
        return SelectionResult(
            module_name=self.module_name,
            selected_provenance_ids=("pid-a", "pid-b"),
            total_candidates_seen=2,
        )

    def run(
        self,
        hub: AnalysisHub,
        request: dict[str, Any],
        selection: SelectionResult | None = None,
    ) -> AnalysisRunResult:
        assert selection is not None
        self.last_run_selection = selection
        n = len(selection.selected_provenance_ids)
        return AnalysisRunResult(
            module_name=self.module_name,
            module_version=self.module_version,
            result_type="test_result",
            input_provenance_ids=list(selection.selected_provenance_ids),
            input_data_hashes=["d" * 64] * n,
            parameters_hash="p" * 64,
            schema={"from_request": request.get("key")},
            payload={"out": request.get("key", 0) + n},
        )


@pytest.mark.unit
def test_orchestrator_happy_path_calls_select_run_and_persists(tmp_path) -> None:
    hub = MagicMock(spec=AnalysisHub)
    store = FileAnalysisResultStore(base_dir=tmp_path)
    mod = _FakeModule()
    request = {"key": 10}

    meta = run_analysis_module(mod, hub, store, request, selection=None)

    assert mod.select_calls == 1
    assert mod.last_run_selection is not None
    assert mod.last_run_selection.selected_provenance_ids == ("pid-a", "pid-b")

    assert meta.module_name == mod.module_name
    assert meta.module_version == mod.module_version
    assert meta.result_type == "test_result"
    assert meta.input_provenance_ids == ["pid-a", "pid-b"]
    assert meta.input_data_hashes == ["d" * 64, "d" * 64]
    assert meta.parameters_hash == "p" * 64
    assert meta.schema == {"from_request": 10}

    loaded = store.load_metadata(meta.provenance_id)
    assert loaded.provenance_id == meta.provenance_id
    assert store.load_payload(meta.provenance_id) == {"out": 12}


@pytest.mark.unit
def test_orchestrator_provided_selection_skips_select(tmp_path) -> None:
    hub = MagicMock(spec=AnalysisHub)
    store = FileAnalysisResultStore(base_dir=tmp_path)
    mod = _FakeModule()
    sel = SelectionResult(
        module_name=mod.module_name,
        selected_provenance_ids=("only-one",),
        total_candidates_seen=99,
    )

    run_analysis_module(mod, hub, store, {"key": 0}, selection=sel)

    assert mod.select_calls == 0
    assert mod.last_run_selection == sel


@pytest.mark.unit
def test_orchestrator_provided_selection_module_name_mismatch_raises(tmp_path) -> None:
    hub = MagicMock(spec=AnalysisHub)
    store = FileAnalysisResultStore(base_dir=tmp_path)
    mod = _FakeModule()
    sel = SelectionResult(
        module_name="wrong_mod",
        selected_provenance_ids=("x",),
        total_candidates_seen=1,
    )

    with pytest.raises(ValueError, match="selection.module_name"):
        run_analysis_module(mod, hub, store, {}, selection=sel)

    assert mod.select_calls == 0
    assert not any(tmp_path.iterdir())


@pytest.mark.unit
def test_orchestrator_deterministic_provenance_id(tmp_path) -> None:
    hub = MagicMock(spec=AnalysisHub)
    store = FileAnalysisResultStore(base_dir=tmp_path)
    mod = _FakeModule()
    request: dict[str, Any] = {"key": 1}

    a = run_analysis_module(mod, hub, store, request, selection=None)
    b = run_analysis_module(mod, hub, store, request, selection=None)

    assert a.provenance_id == b.provenance_id
    assert a.data_hash == b.data_hash


@pytest.mark.unit
def test_orchestrator_propagates_run_errors(tmp_path) -> None:
    hub = MagicMock(spec=AnalysisHub)
    store = FileAnalysisResultStore(base_dir=tmp_path)

    class Boom(_FakeModule):
        def run(
            self,
            hub: AnalysisHub,
            request: dict[str, Any],
            selection: SelectionResult | None = None,
        ) -> AnalysisRunResult:
            raise RuntimeError("run failed")

    mod = Boom()

    with pytest.raises(RuntimeError, match="run failed"):
        run_analysis_module(mod, hub, store, {}, selection=None)

    assert not any(tmp_path.iterdir())


@pytest.mark.unit
def test_orchestrator_rejects_mismatched_input_lengths(tmp_path) -> None:
    hub = MagicMock(spec=AnalysisHub)
    store = FileAnalysisResultStore(base_dir=tmp_path)

    class BadRun(_FakeModule):
        def run(
            self,
            hub: AnalysisHub,
            request: dict[str, Any],
            selection: SelectionResult | None = None,
        ) -> AnalysisRunResult:
            return AnalysisRunResult(
                module_name=self.module_name,
                module_version=self.module_version,
                result_type="t",
                input_provenance_ids=["a", "b"],
                input_data_hashes=["x"],
                parameters_hash="p" * 64,
                schema={},
                payload={},
            )

    mod = BadRun()

    with pytest.raises(ValueError, match="same length"):
        run_analysis_module(mod, hub, store, {}, selection=None)

    assert not any(tmp_path.iterdir())


@pytest.mark.unit
def test_orchestrator_rejects_module_name_mismatch(tmp_path) -> None:
    hub = MagicMock(spec=AnalysisHub)
    store = FileAnalysisResultStore(base_dir=tmp_path)

    class WrongName(_FakeModule):
        def run(
            self,
            hub: AnalysisHub,
            request: dict[str, Any],
            selection: SelectionResult | None = None,
        ) -> AnalysisRunResult:
            base = super().run(hub, request, selection)
            return AnalysisRunResult(
                module_name="other",
                module_version=base.module_version,
                result_type=base.result_type,
                input_provenance_ids=base.input_provenance_ids,
                input_data_hashes=base.input_data_hashes,
                parameters_hash=base.parameters_hash,
                schema=base.schema,
                payload=base.payload,
            )

    with pytest.raises(ValueError, match="run_result.module_name"):
        run_analysis_module(WrongName(), hub, store, {}, selection=None)

    assert not any(tmp_path.iterdir())

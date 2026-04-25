"""Tests for the analysis module registry."""

from __future__ import annotations

import importlib
from typing import Any

import pytest

from neurolab.analysis_hub.interfaces import AnalysisHub
from neurolab.analysis_modules.models import AnalysisModuleDescription, AnalysisRunResult, SelectionResult
from neurolab.analysis_modules.registry import (
    clear_registry,
    get_analysis_module,
    list_analysis_modules,
    register_analysis_module,
)


@pytest.fixture(autouse=True)
def _reset_registry() -> Any:
    clear_registry()
    yield
    clear_registry()


class _StubModule:
    def __init__(self, name: str, version: str) -> None:
        self.module_name = name
        self.module_version = version

    def describe(self) -> AnalysisModuleDescription:
        return AnalysisModuleDescription(module_name=self.module_name, module_version=self.module_version, summary="stub")

    def select(self, hub: AnalysisHub, request: Any) -> SelectionResult:
        return SelectionResult(module_name=self.module_name, selected_provenance_ids=(), total_candidates_seen=0)

    def run(
        self,
        hub: AnalysisHub,
        request: Any,
        selection: SelectionResult | None = None,
    ) -> AnalysisRunResult:
        return AnalysisRunResult(
            module_name=self.module_name,
            module_version=self.module_version,
            result_type="stub",
            input_provenance_ids=[],
            input_data_hashes=[],
            parameters_hash="0" * 64,
            schema={},
            payload={},
        )


@pytest.mark.unit
def test_register_and_retrieve() -> None:
    m = _StubModule("alpha_mod", "1.0.0")
    register_analysis_module(m)
    got = get_analysis_module("alpha_mod")
    assert got is m


@pytest.mark.unit
def test_duplicate_registration_same_version_allowed() -> None:
    m = _StubModule("dup_same", "1.0.0")
    register_analysis_module(m)
    register_analysis_module(m)
    assert len(list_analysis_modules()) == 1
    assert get_analysis_module("dup_same") is m


@pytest.mark.unit
def test_duplicate_registration_different_version_raises() -> None:
    register_analysis_module(_StubModule("dup_ver", "1.0.0"))
    with pytest.raises(ValueError, match="already registered"):
        register_analysis_module(_StubModule("dup_ver", "2.0.0"))


@pytest.mark.unit
def test_list_analysis_modules_sorted_by_name() -> None:
    register_analysis_module(_StubModule("zebra", "1.0.0"))
    register_analysis_module(_StubModule("apple", "1.0.0"))
    register_analysis_module(_StubModule("middle", "1.0.0"))
    names = [m.module_name for m in list_analysis_modules()]
    assert names == ["apple", "middle", "zebra"]


@pytest.mark.unit
def test_get_missing_raises_keyerror_with_available() -> None:
    register_analysis_module(_StubModule("only_one", "1.0.0"))
    with pytest.raises(KeyError) as excinfo:
        get_analysis_module("nope")
    msg = str(excinfo.value)
    assert "Unknown analysis module 'nope'" in msg
    assert "only_one" in msg


@pytest.mark.unit
def test_clear_registry() -> None:
    register_analysis_module(_StubModule("a", "1"))
    register_analysis_module(_StubModule("b", "1"))
    clear_registry()
    assert list_analysis_modules() == []
    with pytest.raises(KeyError):
        get_analysis_module("a")


@pytest.mark.unit
def test_payload_top_level_count_registered_when_implementations_imported() -> None:
    import neurolab.analysis_modules.implementations as impl_mod

    importlib.reload(impl_mod)

    from neurolab.analysis_modules.implementations.payload_top_level_count import PayloadTopLevelCountModule

    mod = get_analysis_module("payload_top_level_count")
    assert isinstance(mod, PayloadTopLevelCountModule)

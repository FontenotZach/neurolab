"""Tests for analysis module dataclasses."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from neurolab.analysis_hub.interfaces import AnalysisHub
from neurolab.analysis_modules.base import AnalysisModule
from neurolab.analysis_modules.models import AnalysisModuleDescription, AnalysisRunResult, SelectionResult


def test_analysis_run_result_fields() -> None:
    r = AnalysisRunResult(
        module_name="mod_a",
        module_version="1.0.0",
        result_type="summary",
        input_provenance_ids=["p1"],
        input_data_hashes=["d1"],
        parameters_hash="a" * 64,
        schema={"k": 1},
        payload={"out": 2},
    )
    assert r.module_name == "mod_a"
    assert r.module_version == "1.0.0"
    assert r.result_type == "summary"
    assert r.input_provenance_ids == ["p1"]
    assert r.input_data_hashes == ["d1"]
    assert r.parameters_hash == "a" * 64
    assert r.schema == {"k": 1}
    assert r.payload == {"out": 2}
    assert r.warnings == []


def test_analysis_run_result_warnings_default_isolated() -> None:
    a = AnalysisRunResult(
        module_name="m",
        module_version="1",
        result_type="t",
        input_provenance_ids=[],
        input_data_hashes=[],
        parameters_hash="b" * 64,
        schema={},
        payload=None,
    )
    b = AnalysisRunResult(
        module_name="m",
        module_version="1",
        result_type="t",
        input_provenance_ids=[],
        input_data_hashes=[],
        parameters_hash="b" * 64,
        schema={},
        payload=None,
    )
    assert a.warnings is not b.warnings
    a.warnings.append("only a")
    assert b.warnings == []


def test_analysis_module_protocol_assignable() -> None:
    """Structural implementor with updated ``run`` signature is accepted."""

    class _MinimalModule:
        module_name = "stub"
        module_version = "0.0.0"

        def describe(self) -> AnalysisModuleDescription:
            return AnalysisModuleDescription(
                module_name=self.module_name,
                module_version=self.module_version,
                summary="stub",
            )

        def select(self, hub: AnalysisHub, request: dict[str, Any]) -> SelectionResult:
            return SelectionResult(
                module_name=self.module_name,
                selected_provenance_ids=(),
                total_candidates_seen=0,
            )

        def run(
            self,
            hub: AnalysisHub,
            request: dict[str, Any],
            selection: SelectionResult | None = None,
        ) -> AnalysisRunResult:
            return AnalysisRunResult(
                module_name=self.module_name,
                module_version=self.module_version,
                result_type="stub",
                input_provenance_ids=[],
                input_data_hashes=[],
                parameters_hash="c" * 64,
                schema={},
                payload={},
            )

    hub = MagicMock(spec=AnalysisHub)
    mod: AnalysisModule[dict[str, Any]] = _MinimalModule()
    assert mod.describe().summary == "stub"
    assert isinstance(mod.run(hub, {}, selection=None), AnalysisRunResult)

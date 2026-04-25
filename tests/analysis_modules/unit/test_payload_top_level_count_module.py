"""Unit tests for PayloadTopLevelCountModule."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from neurolab.analysis_hub.interfaces import AnalysisHub
from neurolab.analysis_modules.implementations.payload_top_level_count import (
    PayloadTopLevelCountModule,
    PayloadTopLevelCountRequest,
)
from neurolab.analysis_modules.models import SelectionResult


@pytest.mark.unit
def test_run_rejects_selection_with_wrong_module_name() -> None:
    hub = MagicMock(spec=AnalysisHub)
    mod = PayloadTopLevelCountModule()
    bad = SelectionResult(
        module_name="other_module",
        selected_provenance_ids=("p1",),
        total_candidates_seen=1,
    )

    with pytest.raises(ValueError, match="selection.module_name"):
        mod.run(hub, PayloadTopLevelCountRequest(), selection=bad)

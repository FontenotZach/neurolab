"""Integration test: process manifest from test_data through adapter pipeline."""

from __future__ import annotations

import pytest

from neurolab.adapters.pipeline.adapter_pipeline import AdapterPipeline
from neurolab.data_interface.models import DataSourceSpec
from neurolab.data_interface.orchestrator import collect_source

pytestmark = [pytest.mark.adapters, pytest.mark.integration]


@pytest.mark.integration
def test_pipeline_process_manifest_from_test_data(project_test_data_dir):
    """Collect from test_data/session1, run pipeline; at least one CSV yields tabular output."""
    session_dir = project_test_data_dir / "session1"
    if not session_dir.exists():
        pytest.skip("test_data/session1 not found")

    source = DataSourceSpec(uri=str(session_dir))
    manifest = collect_source(source)
    if not manifest.artifacts:
        pytest.skip("no artifacts in test_data/session1")

    pipeline = AdapterPipeline()
    result = pipeline.process_manifest(manifest)

    # At least one artifact (e.g. data.csv) should be handled by CSVAdapter
    tabular_outputs = [o for o in result.outputs if o.dataset_type == "tabular"]
    assert len(tabular_outputs) >= 1, "expected at least one tabular output from session1 CSV"

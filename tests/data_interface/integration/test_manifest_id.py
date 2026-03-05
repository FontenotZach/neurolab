"""
Integration tests for manifest_id consistency using project test_data.
Verifies that collect_source produces deterministic manifest_ids and that
re-collecting the same content yields the same id.
"""

import pytest

from neurolab.data_interface.models import DataSourceSpec
from neurolab.data_interface.orchestrator import collect_source

pytestmark = [pytest.mark.data_interface]


@pytest.mark.integration
def test_manifest_id_stable_across_collects(project_test_data_dir):
    """Collecting the same directory twice yields the same manifest_id."""
    if not project_test_data_dir.exists():
        pytest.skip("test_data directory not found")

    source = DataSourceSpec(uri=str(project_test_data_dir), recursive=True)
    manifest1 = collect_source(source)
    manifest2 = collect_source(source)

    assert manifest1.manifest_id == manifest2.manifest_id
    assert len(manifest1.artifacts) == len(manifest2.artifacts)


@pytest.mark.integration
def test_manifest_id_deterministic_for_session(project_test_data_dir):
    """Collecting a subdirectory (e.g. session1) gives a stable manifest_id."""
    session_dir = project_test_data_dir / "session1"
    if not session_dir.exists():
        pytest.skip("test_data/session1 not found")

    source = DataSourceSpec(uri=str(session_dir), recursive=True)
    manifest1 = collect_source(source)
    manifest2 = collect_source(source)

    assert manifest1.manifest_id == manifest2.manifest_id


@pytest.mark.integration
def test_manifest_id_different_for_different_content(project_test_data_dir):
    """Different directories (different content) produce different manifest_ids."""
    session1 = project_test_data_dir / "session1"
    session2 = project_test_data_dir / "session2"
    if not session1.exists() or not session2.exists():
        pytest.skip("test_data/session1 or session2 not found")

    source1 = DataSourceSpec(uri=str(session1), recursive=True)
    source2 = DataSourceSpec(uri=str(session2), recursive=True)
    manifest1 = collect_source(source1)
    manifest2 = collect_source(source2)

    assert manifest1.manifest_id != manifest2.manifest_id

"""
Tests for the Neurolab CLI commands using Typer's CliRunner.
Covers collect, history, show, info, diff, delete, clear, and parse.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from neurolab.adapters.core.output import AdapterOutput
from neurolab.adapters.pipeline.adapter_pipeline import AdapterPipelineResult
from neurolab.data_interface.models import DataSourceSpec, Manifest
from neurolab.interfaces.cli import app
from neurolab.storage.adapter_results.file_store import FileAdapterResultStore
from neurolab.storage.manifest_store import FileManifestStore
from neurolab.storage.roster_store import RosterStore

pytestmark = [pytest.mark.interfaces]

runner = CliRunner()


@pytest.fixture()
def cli_env(tmp_path, monkeypatch):
    """Redirect manifest store and roster to tmp_path so tests are isolated."""
    manifest_dir = tmp_path / "manifests"
    roster_path = tmp_path / "roster.json"
    adapter_dir = tmp_path / "adapter_outputs"

    def _patched_manifest_store_init(self, base_dir=None):
        self.base_dir = manifest_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _patched_roster_store_init(self, path=None):
        self.path = roster_path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _patched_adapter_result_store_init(self, base_dir=None):
        self.base_dir = adapter_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(FileManifestStore, "__init__", _patched_manifest_store_init)
    monkeypatch.setattr(RosterStore, "__init__", _patched_roster_store_init)
    monkeypatch.setattr(FileAdapterResultStore, "__init__", _patched_adapter_result_store_init)

    return tmp_path


def _save_child_record(tmp_path, manifest_id: str, payload):
    store = FileAdapterResultStore(base_dir=tmp_path / "adapter_outputs")
    m = Manifest(
        manifest_id=manifest_id,
        source=DataSourceSpec(uri="file:///x", compute_hash=True),
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        artifacts=[],
        warnings=[],
    )
    out = AdapterOutput(
        artifact_id="art-1",
        adapter_name="t",
        adapter_version="1.0",
        dataset_type="tabular",
        schema={"k": 1},
        payload=payload,
    )
    saved = store.save_pipeline_result(m, AdapterPipelineResult(outputs=[out], skipped_artifacts=[]))
    return saved[0].stored_output_id


@pytest.fixture()
def sample_source(tmp_path):
    """Create a small directory to collect from."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "a.txt").write_text("hello")
    (data_dir / "b.csv").write_text("x,y\n1,2")
    return data_dir


# --- collect ---


@pytest.mark.unit
def test_collect_success(cli_env, sample_source):
    result = runner.invoke(app, ["collect", str(sample_source)])
    assert result.exit_code == 0
    assert "Collection Summary" in result.output
    assert "2" in result.output  # 2 artifacts


@pytest.mark.unit
def test_collect_nonexistent_path(cli_env, tmp_path):
    result = runner.invoke(app, ["collect", str(tmp_path / "nope")])
    assert result.exit_code == 0
    assert "0" in result.output  # 0 artifacts


# --- history ---


@pytest.mark.unit
def test_history_empty(cli_env):
    result = runner.invoke(app, ["history"])
    assert result.exit_code == 0
    assert "No stored manifests found" in result.output


@pytest.mark.unit
def test_history_after_collect(cli_env, sample_source):
    runner.invoke(app, ["collect", str(sample_source)])
    result = runner.invoke(app, ["history"])
    assert result.exit_code == 0
    assert "Stored Manifests" in result.output


# --- info ---


@pytest.mark.unit
def test_info_empty(cli_env):
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "No stored manifests found" in result.output


@pytest.mark.unit
def test_info_after_collect(cli_env, sample_source):
    runner.invoke(app, ["collect", str(sample_source)])
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "Manifest Store Info" in result.output
    assert "1" in result.output  # 1 manifest


# --- show ---


@pytest.mark.unit
def test_show_missing(cli_env):
    result = runner.invoke(app, ["show", "nonexistent"])
    assert result.exit_code == 1
    assert "not found" in result.output


@pytest.mark.unit
def test_show_after_collect(cli_env, sample_source):
    runner.invoke(app, ["collect", str(sample_source)])
    store = FileManifestStore()
    mid = store.list()[0]
    result = runner.invoke(app, ["show", mid])
    assert result.exit_code == 0
    assert mid in result.output


# --- parse ---


@pytest.mark.unit
def test_parse_missing_manifest(cli_env):
    result = runner.invoke(app, ["parse", "nonexistent"])
    assert result.exit_code == 1
    assert "not found" in result.output


@pytest.mark.unit
def test_parse_after_collect(cli_env, sample_source):
    """Parse runs pipeline and prints Manifest, Artifacts processed, Adapters used, Outputs, Skipped."""
    runner.invoke(app, ["collect", str(sample_source)])
    store = FileManifestStore()
    mid = store.list()[0]
    result = runner.invoke(app, ["parse", mid])
    assert result.exit_code == 0
    assert "Manifest:" in result.output
    assert "Artifacts processed: 2" in result.output
    assert "Adapters used:" in result.output
    assert "csv_adapter:" in result.output
    assert "Outputs generated:" in result.output
    assert "Skipped artifacts:" in result.output


# --- children / child ---


@pytest.mark.unit
def test_children_empty(cli_env):
    result = runner.invoke(app, ["children", "mid-1"])
    assert result.exit_code == 0
    assert "No persisted child records found" in result.output


@pytest.mark.unit
def test_children_lists_records(cli_env, tmp_path):
    sid = _save_child_record(tmp_path, "mid-1", payload=[{"a": 1}])
    result = runner.invoke(app, ["children", "mid-1"])
    assert result.exit_code == 0
    assert "Children of manifest mid-1" in result.output
    assert sid[:12] in result.output
    assert "art-1" in result.output
    assert "t" in result.output


@pytest.mark.unit
def test_children_long(cli_env, tmp_path):
    _save_child_record(tmp_path, "mid-1", payload=[{"a": 1}])
    result = runner.invoke(app, ["children", "mid-1", "--long"])
    assert result.exit_code == 0
    # Column headers may truncate in Rich tables; check for the payload_format value prefix.
    assert "neur" in result.output


@pytest.mark.unit
def test_child_show(cli_env, tmp_path):
    sid = _save_child_record(tmp_path, "mid-1", payload={"x": 1})
    result = runner.invoke(app, ["child", "show", "mid-1", sid])
    assert result.exit_code == 0
    assert "stored_output_id" in result.output
    assert "schema" in result.output
    assert '"k": 1' in result.output


@pytest.mark.unit
def test_child_payload_json(cli_env, tmp_path):
    sid = _save_child_record(tmp_path, "mid-1", payload={"x": 1})
    result = runner.invoke(app, ["child", "payload", "mid-1", sid])
    assert result.exit_code == 0
    assert '"x": 1' in result.output


@pytest.mark.unit
def test_child_payload_ndarray_summarized_and_full(cli_env, tmp_path):
    np = pytest.importorskip("numpy")
    sid = _save_child_record(tmp_path, "mid-1", payload={"signal": np.asarray([1.0, 2.0], dtype=np.float32)})

    result = runner.invoke(app, ["child", "payload", "mid-1", sid])
    assert result.exit_code == 0
    assert "__ndarray__" in result.output
    assert "shape" in result.output

    result_full = runner.invoke(app, ["child", "payload", "mid-1", sid, "--full"])
    assert result_full.exit_code == 0
    assert "__ndarray__" not in result_full.output
    assert "1.0" in result_full.output


@pytest.mark.unit
def test_children_delete_confirm_and_abort(cli_env, tmp_path):
    _save_child_record(tmp_path, "mid-1", payload={"x": 1})

    abort = runner.invoke(app, ["children", "delete", "mid-1"], input="n\n")
    assert abort.exit_code == 0
    assert "Aborting" in abort.output

    ok = runner.invoke(app, ["children", "delete", "mid-1"], input="y\n")
    assert ok.exit_code == 0
    assert "Deleted" in ok.output

    after = runner.invoke(app, ["children", "mid-1"])
    assert after.exit_code == 0
    assert "No persisted child records found" in after.output


@pytest.mark.unit
def test_children_delete_yes(cli_env, tmp_path):
    _save_child_record(tmp_path, "mid-1", payload={"x": 1})
    result = runner.invoke(app, ["children", "delete", "mid-1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


# --- hub ---


@pytest.mark.unit
def test_hub_list_lists_records(cli_env, tmp_path):
    sid = _save_child_record(tmp_path, "mid-1", payload=[{"a": 1}])
    hub_dir = tmp_path / "adapter_outputs"
    result = runner.invoke(app, ["hub", "list", "--hub-dir", str(hub_dir)])
    assert result.exit_code == 0
    assert "Analysis Hub Records" in result.output
    assert sid[:12] in result.output
    assert "mid-1" in result.output
    assert "art-1" in result.output
    assert "t" in result.output


@pytest.mark.unit
def test_hub_list_honors_filters_and_limit(cli_env, tmp_path):
    _save_child_record(tmp_path, "mid-1", payload=[{"a": 1}])
    _save_child_record(tmp_path, "mid-2", payload=[{"a": 2}])
    hub_dir = tmp_path / "adapter_outputs"

    filtered = runner.invoke(app, ["hub", "list", "--hub-dir", str(hub_dir), "--manifest-id", "mid-2"])
    assert filtered.exit_code == 0
    assert "mid-2" in filtered.output
    assert "mid-1" not in filtered.output

    limited = runner.invoke(app, ["hub", "list", "--hub-dir", str(hub_dir), "--limit", "1"])
    assert limited.exit_code == 0
    # Header appears; only one record row should include one of the manifest ids.
    assert ("mid-1" in limited.output) ^ ("mid-2" in limited.output)


@pytest.mark.unit
def test_hub_list_long_includes_extra_fields(cli_env, tmp_path):
    _save_child_record(tmp_path, "mid-1", payload=[{"a": 1}])
    hub_dir = tmp_path / "adapter_outputs"
    short = runner.invoke(app, ["hub", "list", "--hub-dir", str(hub_dir)])
    assert short.exit_code == 0

    long = runner.invoke(app, ["hub", "list", "--hub-dir", str(hub_dir), "--long"])
    assert long.exit_code == 0

    def _top_border_sep_count(s: str) -> int:
        for line in s.splitlines():
            if line.startswith("┏"):
                return line.count("┳")
        return 0

    # --long adds columns; Rich's top border should have more separators.
    assert _top_border_sep_count(long.output) > _top_border_sep_count(short.output)


@pytest.mark.unit
def test_hub_show_valid_and_invalid(cli_env, tmp_path):
    sid = _save_child_record(tmp_path, "mid-1", payload={"x": 1})
    hub_dir = tmp_path / "adapter_outputs"
    ok = runner.invoke(app, ["hub", "show", "--hub-dir", str(hub_dir), sid])
    assert ok.exit_code == 0
    assert "stored_output_id" in ok.output
    assert "schema" in ok.output
    assert '"k": 1' in ok.output
    assert "schema_fingerprint" in ok.output

    bad = runner.invoke(app, ["hub", "show", "--hub-dir", str(hub_dir), "0" * 64])
    assert bad.exit_code == 1
    assert "Stored output not found" in bad.output


@pytest.mark.unit
def test_hub_count_summarizes(cli_env, tmp_path):
    _save_child_record(tmp_path, "mid-1", payload=[{"a": 1}])
    _save_child_record(tmp_path, "mid-1", payload=[{"a": 2}])
    _save_child_record(tmp_path, "mid-2", payload=[{"a": 3}])

    hub_dir = tmp_path / "adapter_outputs"
    result = runner.invoke(app, ["hub", "count", "--hub-dir", str(hub_dir)])
    assert result.exit_code == 0
    assert "Total records" in result.output
    assert "Counts by adapter_name" in result.output
    assert "Counts by dataset_type" in result.output


@pytest.mark.unit
def test_hub_load_summary_and_json(cli_env, tmp_path):
    sid = _save_child_record(tmp_path, "mid-1", payload={"x": 1})
    hub_dir = tmp_path / "adapter_outputs"
    result = runner.invoke(app, ["hub", "load", "--hub-dir", str(hub_dir), sid])
    assert result.exit_code == 0
    assert "Loaded payload" in result.output
    assert "python_type" in result.output

    result_json = runner.invoke(app, ["hub", "load", "--hub-dir", str(hub_dir), sid, "--json"])
    assert result_json.exit_code == 0
    assert '"x": 1' in result_json.output

    bad = runner.invoke(app, ["hub", "load", "--hub-dir", str(hub_dir), "0" * 64])
    assert bad.exit_code == 1
    assert "Stored output not found" in bad.output


@pytest.mark.unit
def test_hub_schemas_groups(cli_env, tmp_path):
    _save_child_record(tmp_path, "mid-1", payload=[{"a": 1}])
    _save_child_record(tmp_path, "mid-1", payload=[{"a": 2}])
    hub_dir = tmp_path / "adapter_outputs"
    result = runner.invoke(app, ["hub", "schemas", "--hub-dir", str(hub_dir)])
    assert result.exit_code == 0
    assert "Schemas in Analysis Hub" in result.output
    assert "schema_fingerprint" in result.output

    result_long = runner.invoke(app, ["hub", "schemas", "--hub-dir", str(hub_dir), "--long"])
    assert result_long.exit_code == 0
    assert "schema_preview" in result_long.output or "schema" in result_long.output

# --- diff ---


@pytest.mark.unit
def test_diff_missing_manifests(cli_env):
    result = runner.invoke(app, ["diff", "a", "b"])
    assert result.exit_code == 1
    assert "not found" in result.output


@pytest.mark.unit
def test_diff_identical(cli_env, sample_source):
    runner.invoke(app, ["collect", str(sample_source)])
    store = FileManifestStore()
    mid = store.list()[0]
    result = runner.invoke(app, ["diff", mid, mid])
    assert result.exit_code == 0
    assert "0" in result.output  # 0 added/removed/modified


# --- delete ---


@pytest.mark.unit
def test_delete_with_confirm(cli_env, sample_source):
    runner.invoke(app, ["collect", str(sample_source)])
    store = FileManifestStore()
    mid = store.list()[0]
    result = runner.invoke(app, ["delete", mid], input="y\n")
    assert result.exit_code == 0
    assert "Deleted" in result.output
    assert store.list() == []


@pytest.mark.unit
def test_delete_abort(cli_env, sample_source):
    runner.invoke(app, ["collect", str(sample_source)])
    store = FileManifestStore()
    mid = store.list()[0]
    result = runner.invoke(app, ["delete", mid], input="n\n")
    assert result.exit_code == 0
    assert "Aborting" in result.output
    assert len(store.list()) == 1


# --- clear ---


@pytest.mark.unit
def test_clear_empty(cli_env):
    result = runner.invoke(app, ["clear"])
    assert result.exit_code == 0
    assert "No stored manifests to delete" in result.output


@pytest.mark.unit
def test_clear_with_confirm(cli_env, sample_source):
    runner.invoke(app, ["collect", str(sample_source)])
    store = FileManifestStore()
    assert len(store.list()) == 1
    result = runner.invoke(app, ["clear"], input="y\n")
    assert result.exit_code == 0
    assert "Deleted" in result.output
    assert store.list() == []

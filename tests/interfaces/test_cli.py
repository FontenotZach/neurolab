"""
Tests for the Neurolab CLI commands using Typer's CliRunner.
Covers collect, history, show, info, diff, delete, and clear.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from neurolab.interfaces.cli import app
from neurolab.storage.manifest_store import FileManifestStore
from neurolab.storage.roster_store import RosterStore

pytestmark = [pytest.mark.interfaces]

runner = CliRunner()


@pytest.fixture()
def cli_env(tmp_path, monkeypatch):
    """Redirect manifest store and roster to tmp_path so tests are isolated."""
    manifest_dir = tmp_path / "manifests"
    roster_path = tmp_path / "roster.json"

    def _patched_manifest_store_init(self, base_dir=None):
        self.base_dir = manifest_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _patched_roster_store_init(self, path=None):
        self.path = roster_path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(FileManifestStore, "__init__", _patched_manifest_store_init)
    monkeypatch.setattr(RosterStore, "__init__", _patched_roster_store_init)

    return tmp_path


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

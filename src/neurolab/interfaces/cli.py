import typer
from rich import print
from rich.table import Table

from neurolab.data_interface.models import DataSourceSpec
from neurolab.data_interface.orchestrator import collect_source
from neurolab.storage.manifest_store import FileManifestStore

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main():
    """
    Neurolab CLI.
    """
    pass


@app.command()
def collect(path: str):
    source = DataSourceSpec(uri=path)
    manifest = collect_source(source)

    table = Table(title="Collection Summary")
    table.add_column("Metric")
    table.add_column("Value")

    table.add_row("Source", path)
    table.add_row("Artifacts Found", str(len(manifest.artifacts)))
    table.add_row("Warnings", str(len(manifest.warnings)))

    manifest_store = FileManifestStore()
    manifest_store.save(manifest)
    table.add_row("Manifest ID", manifest.manifest_id)

    print(table)


@app.command()
def history():
    """
    List stored manifest IDs.
    """
    store = FileManifestStore()
    manifests = store.list()

    if not manifests:
        print("[yellow]No stored manifests found.[/yellow]")
        return

    table = Table(title="Stored Manifests")
    table.add_column("Manifest ID", style="cyan")

    for mid in sorted(manifests):
        table.add_row(mid)

    print(table)


@app.command()
def show(manifest_id: str):
    """
    Show summary information for a stored manifest.
    """
    store = FileManifestStore()

    try:
        manifest = store.load(manifest_id)
    except FileNotFoundError as err:
        print(f"[red]Manifest {manifest_id} not found.[/red]")
        raise typer.Exit(code=1) from err

    table = Table(title=f"Manifest {manifest_id}")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Source", manifest.source.uri)
    table.add_row("Created At", manifest.created_at.isoformat())
    table.add_row("Artifacts", str(len(manifest.artifacts)))
    table.add_row("Warnings", str(len(manifest.warnings)))

    print(table)

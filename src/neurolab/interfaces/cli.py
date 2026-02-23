import typer
from rich import print
from rich.table import Table

from neurolab.data_interface.models import DataSourceSpec
from neurolab.data_interface.orchestrator import collect_source
from neurolab.storage.manifest_store import FileManifestStore

app = typer.Typer(no_args_is_help=True)

"""Neurolab CLI.
- Provides commands for collecting artifacts from data sources, managing stored manifests, and comparing manifests.
- Designed for ease of use and extensibility, allowing for future addition of new commands and options as needed.
- Uses rich for enhanced terminal output and typer for command-line interface management.
- Commands include:
  - collect: Collect artifacts from a specified data source and save the resulting manifest.
  - history: List stored manifests with summary information.
  - delete: Delete a stored manifest by ID.
  - clear: Delete all stored manifests.
  - info: Show summary information about the manifest store.
  - diff: Compare two stored manifests and show differences.
  - show: Show summary information for a specific stored manifest.
- Each command includes options for customizing behavior and output, with sensible defaults for ease of use."""


@app.callback()
def main():
    """
    Neurolab CLI.
    """
    pass


"""
Collect artifacts from a specified data source.
- Currently supports filesystem sources, but designed for easy extension to other types (e.g., databases
or APIs) in the future.
- Displays a summary of the collection results, including the number of artifacts found and any warnings.
- Saves the resulting manifest to the manifest store for later retrieval and comparison.
- Could be extended in the future to support additional options, such as computing content hashes during
collection or specifying custom manifest metadata.
"""


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


"""
List stored manifests (newest first).
- By default, shows only the most recent 10 manifests for brevity.
- Optionally, can show all stored manifests with --all.
- Displays key information about each manifest, including creation time, source URI, artifact count, and
warning count.

Options:
--head N: Show only the most recent N manifests (default: 10).
--all: Show all stored manifests.
"""


@app.command()
def history(
    head: int = typer.Option(
        10,
        "--head",
        "-n",
        help="Show only the most recent N manifests (default: 10).",
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        help="Show all stored manifests.",
    ),
):
    """
    List stored manifests (newest first).
    """
    store = FileManifestStore()
    manifest_ids = store.list()

    if not manifest_ids:
        print("[yellow]No stored manifests found.[/yellow]")
        return

    # Load manifests
    manifests = []
    for mid in manifest_ids:
        try:
            m = store.load(mid)
            manifests.append(m)
        except Exception:
            continue

    # Sort newest first
    manifests.sort(key=lambda m: m.created_at, reverse=True)

    total = len(manifests)

    if not show_all:
        manifests = manifests[:head]

    table = Table(title="Stored Manifests - Created At, descending")
    table.add_column("Created At", style="bold cyan")
    table.add_column("Manifest ID", style="cyan")
    table.add_column("Source", style="green")
    table.add_column("Artifacts", justify="right")
    table.add_column("Warnings", justify="right")

    for m in manifests:
        table.add_row(
            m.created_at.isoformat(),
            m.manifest_id,
            m.source.uri,
            str(len(m.artifacts)),
            str(len(m.warnings)),
        )

    if not show_all and total > head:
        table.add_row(
            "...",
            "...",
            f"{total - head} other manifests",
            "",
            "",
        )

    print(table)


"""
Delete a stored manifest by ID.
- Prompts for confirmation before deleting to prevent accidental data loss.
"""


@app.command()
def delete(manifest_id: str):
    """
    Delete a stored manifest by ID.
    """
    store = FileManifestStore()

    try:
        confirm = typer.confirm(
            f"This action will delete {manifest_id} from stored manifests. Continue?",
            default=False,
        )
        if not confirm:
            print("[yellow]Aborting delete operation.[/yellow]")
            return
        store.delete(manifest_id)
        print(f"[green]Deleted manifest {manifest_id}.[/green]")
    except FileNotFoundError as err:
        print(f"[red]Manifest {manifest_id} not found.[/red]")
        raise typer.Exit(code=1) from err


"""
Delete all stored manifests.
- Prompts for confirmation before deleting to prevent accidental data loss.
- Could be extended in the future to support selective deletion based on criteria (e.g., age, source).
"""


@app.command()
def clear():
    """
    Delete all stored manifests.
    """
    store = FileManifestStore()
    manifest_ids = store.list()

    if not manifest_ids:
        print("[yellow]No stored manifests to delete.[/yellow]")
        return

    confirm = typer.confirm(
        f"This action will delete {len(manifest_ids)} stored manifest(s). Continue?",
        default=False,
    )
    if not confirm:
        print("[yellow]Aborting clear operation.[/yellow]")
        return

    for mid in manifest_ids:
        store._path(mid).unlink()

    print(f"[green]Deleted {len(manifest_ids)} manifests.[/green]")


"""
Show summary information about the manifest store.
- Total number of stored manifests.
- Oldest and newest manifest creation timestamps.
- Optionally, could include aggregate artifact counts or common sources in future iterations.
"""


@app.command()
def info():
    """
    Show summary information about the manifest store.
    """
    store = FileManifestStore()
    manifest_ids = store.list()

    table = Table(title="Manifest Store Info")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Total Manifests", str(len(manifest_ids)))

    manifests = [store.load(mid) for mid in manifest_ids]
    manifests.sort(key=lambda m: m.created_at)

    oldest = manifests[0].created_at.isoformat()
    newest = manifests[-1].created_at.isoformat()

    table.add_row("Oldest Manifest", oldest)
    table.add_row("Newest Manifest", newest)

    print(table)


"""
Diff two stored manifests by ID.
- Compares artifacts based on relative_path (for filesystem sources).
- Uses content_hash for comparison if available, otherwise falls back to size and mtime.
- Provides both summary and detailed views of differences.

Options:
--long: Show detailed file-level differences instead of just counts.
"""


@app.command()
def diff(
    id1: str,
    id2: str,
    long: bool = typer.Option(
        False,
        "--long",
        help="Show detailed file-level differences.",
    ),
):
    """
    Compare two manifests.
    """
    store = FileManifestStore()

    try:
        m1 = store.load(id1)
        m2 = store.load(id2)
    except FileNotFoundError:
        print("[red]One or both manifest IDs not found.[/red]")
        raise typer.Exit(code=1) from None

    # Index artifacts by relative_path
    a1 = {a.relative_path: a for a in m1.artifacts if a.relative_path is not None}
    a2 = {a.relative_path: a for a in m2.artifacts if a.relative_path is not None}

    paths1 = set(a1.keys())
    paths2 = set(a2.keys())

    added = sorted(paths2 - paths1)
    removed = sorted(paths1 - paths2)

    modified = []

    for path in sorted(paths1 & paths2):
        art1 = a1[path]
        art2 = a2[path]

        # Prefer hash comparison if available
        # Is content_hash always expected to be present for filesystem artifacts?
        # If not, this fallback is necessary.
        if art1.content_hash and art2.content_hash:
            if art1.content_hash != art2.content_hash:
                modified.append(path)
        else:
            # Fallback comparison
            if art1.size_bytes != art2.size_bytes or art1.mtime != art2.mtime:
                modified.append(path)

    # Summary view
    if not long:
        table = Table(title="Manifest Diff Summary")
        table.add_column("Metric", style="bold cyan")
        table.add_column("Count", justify="right")

        table.add_row("Added", str(len(added)))
        table.add_row("Removed", str(len(removed)))
        table.add_row("Modified", str(len(modified)))

        print(table)
        return

    # Detailed view
    if not added and not removed and not modified:
        print("[green]No differences detected between manifests.[/green]")
        return

    table = Table(title="Manifest Diff (Detailed)")
    table.add_column("Change Type", style="bold cyan")
    table.add_column("Path", style="green")

    for path in added:
        table.add_row("Added", path)

    for path in removed:
        table.add_row("Removed", path)

    for path in modified:
        table.add_row("Modified", path)

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

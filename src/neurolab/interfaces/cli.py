from __future__ import annotations

import typer
from rich import print
from rich.table import Table

from neurolab.data_interface.models import DataSourceSpec
from neurolab.data_interface.orchestrator import collect_source
from neurolab.storage.manifest_store import FileManifestStore
from neurolab.storage.roster_store import RosterStore

app = typer.Typer(no_args_is_help=True)
roster_app = typer.Typer(help="Manage a short list of manifest aliases (e.g. r1, r2) for quick reference.")
app.add_typer(roster_app, name="roster")


@app.callback()
def main():
    """Neurolab CLI."""
    pass


def _resolve_manifest_id(
    id_or_alias: str,
    roster_store: RosterStore,
) -> str:
    """Resolve a roster alias to manifest_id, or return as-is if not an alias."""
    resolved = roster_store.get(id_or_alias)
    if resolved is not None:
        return resolved
    return id_or_alias


@app.command()
def collect(path: str):
    """Collect artifacts from a data source and save the resulting manifest."""
    source = DataSourceSpec(uri=path)
    manifest = collect_source(source)

    table = Table(title="Collection Summary")
    table.add_column("Metric", no_wrap=True)
    table.add_column("Value", no_wrap=True)

    table.add_row("Source", path)
    table.add_row("Artifacts Found", str(len(manifest.artifacts)))
    table.add_row("Warnings", str(len(manifest.warnings)))

    manifest_store = FileManifestStore()
    manifest_store.save(manifest)
    table.add_row("Manifest ID", manifest.manifest_id)

    print(table)


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
    table.add_column("Manifest ID", style="cyan", no_wrap=True)
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


@app.command()
def delete(manifest_id: str):
    """
    Delete a stored manifest by ID (or roster alias, e.g. r1). Removes the alias from the roster if present.
    """
    store = FileManifestStore()
    roster_store = RosterStore()
    resolved_id = _resolve_manifest_id(manifest_id, roster_store)

    try:
        confirm = typer.confirm(
            f"This action will delete {resolved_id} from stored manifests. Continue?",
            default=False,
        )
        if not confirm:
            print("[yellow]Aborting delete operation.[/yellow]")
            return
        store.delete(resolved_id)
        if manifest_id != resolved_id:
            roster_store.remove(manifest_id)
        else:
            for alias, mid in list(roster_store.load().items()):
                if mid == resolved_id:
                    roster_store.remove(alias)
                    break
        print(f"[green]Deleted manifest {resolved_id}.[/green]")
    except FileNotFoundError as err:
        print(f"[red]Manifest {manifest_id} not found.[/red]")
        raise typer.Exit(code=1) from err


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
        store.delete(mid)

    print(f"[green]Deleted {len(manifest_ids)} manifests.[/green]")


@roster_app.command("add")
def roster_add(
    manifest_id: str,
    as_alias: str | None = typer.Option(
        None,
        "--as",
        help="Alias for this manifest (e.g. r1, baseline). If omitted, next r1, r2, ... is used.",
    ),
):
    """
    Add a manifest to the roster by ID. Use the manifest in other commands by alias (e.g. diff r1 r2).
    """
    manifest_store = FileManifestStore()
    roster_store = RosterStore()
    try:
        manifest_store.load(manifest_id)
    except FileNotFoundError:
        print(f"[red]Manifest {manifest_id} not found in store.[/red]")
        raise typer.Exit(code=1) from None
    alias = as_alias if as_alias is not None else roster_store.next_slot()
    roster_store.add(alias, manifest_id)
    print(f"[green]Added {manifest_id} as {alias}.[/green]")


@roster_app.command("list")
def roster_list():
    """
    List roster entries (alias -> manifest ID). Optionally shows manifest details.
    """
    roster_store = RosterStore()
    manifest_store = FileManifestStore()
    entries = roster_store.load()
    if not entries:
        print("[yellow]Roster is empty.[/yellow]")
        return
    table = Table(title="Roster")
    table.add_column("Alias", style="bold cyan")
    table.add_column("Manifest ID", style="cyan", no_wrap=True)
    table.add_column("Source", style="green")
    table.add_column("Created At", style="dim")
    for alias, mid in sorted(entries.items(), key=lambda p: (len(p[0]), p[0])):
        try:
            m = manifest_store.load(mid)
            table.add_row(alias, mid, m.source.uri, m.created_at.isoformat())
        except FileNotFoundError:
            table.add_row(alias, mid, "[red](manifest missing)[/red]", "")
    print(table)


@roster_app.command("remove")
def roster_remove(alias: str):
    """
    Remove an alias from the roster.
    """
    roster_store = RosterStore()
    entries = roster_store.load()
    if alias not in entries:
        print(f"[red]Alias {alias} not in roster.[/red]")
        raise typer.Exit(code=1) from None
    roster_store.remove(alias)
    print(f"[green]Removed {alias} from roster.[/green]")


@roster_app.command("clear")
def roster_clear():
    """
    Remove all entries from the roster.
    """
    roster_store = RosterStore()
    entries = roster_store.load()
    if not entries:
        print("[yellow]Roster is already empty.[/yellow]")
        return
    confirm = typer.confirm(
        f"This will remove {len(entries)} alias(es) from the roster. Continue?",
        default=False,
    )
    if not confirm:
        print("[yellow]Aborting.[/yellow]")
        return
    roster_store.save({})
    print("[green]Roster cleared.[/green]")


@app.command()
def info():
    """
    Show summary information about the manifest store.
    """
    store = FileManifestStore()
    manifest_ids = store.list()

    if not manifest_ids:
        print("[yellow]No stored manifests found.[/yellow]")
        return

    table = Table(title="Manifest Store Info")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Total Manifests", str(len(manifest_ids)))

    manifests = [store.load(mid) for mid in manifest_ids]
    manifests.sort(key=lambda m: m.created_at)

    table.add_row("Oldest Manifest", manifests[0].created_at.isoformat())
    table.add_row("Newest Manifest", manifests[-1].created_at.isoformat())

    print(table)


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
    roster_store = RosterStore()
    resolved_id1 = _resolve_manifest_id(id1, roster_store)
    resolved_id2 = _resolve_manifest_id(id2, roster_store)

    try:
        m1 = store.load(resolved_id1)
        m2 = store.load(resolved_id2)
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
    roster_store = RosterStore()
    resolved_id = _resolve_manifest_id(manifest_id, roster_store)

    try:
        manifest = store.load(resolved_id)
    except FileNotFoundError as err:
        print(f"[red]Manifest {manifest_id} not found.[/red]")
        raise typer.Exit(code=1) from err

    table = Table(title=f"Manifest {resolved_id}")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold green", no_wrap=True)

    table.add_row("Source", manifest.source.uri)
    table.add_row("Created At", manifest.created_at.isoformat())
    table.add_row("Artifacts", str(len(manifest.artifacts)))
    table.add_row("Warnings", str(len(manifest.warnings)))

    print(table)

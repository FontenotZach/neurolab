from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich import print
from rich.table import Table

from neurolab.adapters.pipeline.adapter_pipeline import AdapterPipeline
from neurolab.analysis_hub import FileSystemAnalysisHub, MetadataLoadError, MetadataRecordNotFoundError, PayloadNotFoundError
from neurolab.data_interface.models import DataSourceSpec
from neurolab.data_interface.orchestrator import collect_source
from neurolab.storage.adapter_results import FileAdapterResultStore
from neurolab.storage.adapter_results.errors import StoredOutputNotFound
from neurolab.storage.adapter_results.ids import canonical_json, schema_fingerprint
from neurolab.storage.manifest_store import FileManifestStore
from neurolab.storage.roster_store import RosterStore

app = typer.Typer(no_args_is_help=True)
roster_app = typer.Typer(help="Manage a short list of manifest aliases (e.g. r1, r2) for quick reference.")
app.add_typer(roster_app, name="roster")

child_app = typer.Typer(help="Inspect persisted parsed child records derived from a manifest.")
app.add_typer(child_app, name="child")

hub_app = typer.Typer(help="Browse Analysis Hub registry of persisted parsed outputs.")
app.add_typer(hub_app, name="hub")


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


def _canonical_manifest_id(manifest_id_or_prefix: str) -> str:
    """
    Resolve a full manifest_id from an id or unique prefix using the manifest store.
    If the manifest is not found, return the input unchanged.
    """
    store = FileManifestStore()
    try:
        m = store.load(manifest_id_or_prefix)
        return m.manifest_id
    except FileNotFoundError:
        return manifest_id_or_prefix


def _short_id(s: str, n: int = 12) -> str:
    return s if len(s) <= n else f"{s[:n]}..."


def _render_payload_for_display(obj: Any, *, full: bool) -> Any:
    """
    Convert payload to a JSON-serializable display structure.
    Default behavior summarizes ndarray leaves; --full expands arrays via tolist().
    """
    try:
        import numpy as np  # type: ignore
    except Exception:
        np = None  # type: ignore

    if np is not None and isinstance(obj, np.ndarray):
        if full:
            return obj.tolist()
        return {"__ndarray__": {"dtype": str(obj.dtype), "shape": [int(x) for x in obj.shape]}}

    if isinstance(obj, dict):
        return {str(k): _render_payload_for_display(v, full=full) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_render_payload_for_display(v, full=full) for v in obj]
    return obj


def _build_analysis_hub(*, hub_dir: Path | None, adapter_store_dir: Path | None) -> FileSystemAnalysisHub:
    """
    Construct the Analysis Hub.

    `hub_dir` and `adapter_store_dir` are aliases for the same base directory:
    ~/.neurolab/data/adapter_outputs by default.
    """

    if hub_dir is not None and adapter_store_dir is not None and hub_dir != adapter_store_dir:
        print("[red]Conflicting hub directory options: --hub-dir and --adapter-store-dir differ.[/red]")
        raise typer.Exit(code=2)

    base_dir = hub_dir if hub_dir is not None else adapter_store_dir
    try:
        return FileSystemAnalysisHub(base_dir=base_dir)
    except MetadataLoadError as err:
        print(f"[red]{err}[/red]")
        raise typer.Exit(code=1) from err


def _hub_filter_records(
    hub: FileSystemAnalysisHub,
    *,
    manifest_id: str | None,
    artifact_id: str | None,
    adapter_name: str | None,
    dataset_type: str | None,
):
    return hub.find_records(
        manifest_id=manifest_id,
        artifact_id=artifact_id,
        adapter_name=adapter_name,
        dataset_type=dataset_type,
    )


@app.command()
def children(
    manifest_id_or_action: Annotated[str, typer.Argument(help="Manifest ID (or roster alias), or the action 'delete'.")],
    manifest_id: Annotated[str | None, typer.Argument(help="Manifest ID (or roster alias) when using the 'delete' action.")] = None,
    long: Annotated[
        bool,
        typer.Option("--long", help="Include additional metadata columns (adapter_version, payload_format, row_count)."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Skip confirmation prompt (only applies to delete)."),
    ] = False,
    adapter_store_dir: Annotated[
        Path | None,
        typer.Option(
            "--adapter-store-dir",
            help="Base directory for adapter results (default: ~/.neurolab/data/adapter_outputs).",
            path_type=Path,
        ),
    ] = None,
):
    """
    List persisted parsed child records derived from a manifest.
    """
    roster_store = RosterStore()
    store = FileAdapterResultStore(base_dir=adapter_store_dir)

    # Support both:
    # - neurolab children <manifest_id>
    # - neurolab children delete <manifest_id>
    if manifest_id_or_action == "delete":
        if manifest_id is None:
            print("[red]Missing manifest_id for delete.[/red]")
            raise typer.Exit(code=2)
        resolved_id = _resolve_manifest_id(manifest_id, roster_store)
        canonical_id = _canonical_manifest_id(resolved_id)
        existing = store.list_outputs(canonical_id)
        if not existing:
            print(f"[yellow]No persisted child records found for manifest {canonical_id}.[/yellow]")
            return
        if not yes:
            confirm = typer.confirm(
                f"This action will delete {len(existing)} persisted child record(s) derived from manifest {canonical_id}. Continue?",
                default=False,
            )
            if not confirm:
                print("[yellow]Aborting.[/yellow]")
                return
        store.delete_manifest_outputs(canonical_id)
        print(f"[green]Deleted {len(existing)} persisted child record(s) for manifest {canonical_id}.[/green]")
        return

    if manifest_id is not None:
        print("[red]Unexpected extra argument.[/red]")
        raise typer.Exit(code=2)

    resolved_id = _resolve_manifest_id(manifest_id_or_action, roster_store)
    canonical_id = _canonical_manifest_id(resolved_id)
    children_meta = store.list_outputs(canonical_id)
    if not children_meta:
        print(f"[yellow]No persisted child records found for manifest {canonical_id}.[/yellow]")
        return

    table = Table(title=f"Children of manifest {canonical_id}")
    table.add_column("Ordinal", justify="right", style="bold cyan")
    table.add_column("Stored Output ID", style="cyan", no_wrap=True)
    table.add_column("Artifact ID", style="green", no_wrap=True)
    table.add_column("Adapter", style="bold")
    table.add_column("Dataset Type")
    if long:
        table.add_column("Adapter Ver", style="dim")
        table.add_column("Payload Format", style="dim")
        table.add_column("Row Count", justify="right", style="dim")

    for meta in children_meta:
        row = [
            str(meta.pipeline_ordinal),
            _short_id(meta.stored_output_id, 12),
            meta.artifact_id,
            meta.adapter_name,
            meta.dataset_type,
        ]
        if long:
            row.extend(
                [
                    meta.adapter_version,
                    meta.payload_format,
                    "" if meta.row_count is None else str(meta.row_count),
                ]
            )
        table.add_row(*row)
    print(table)


@child_app.command("show")
def child_show(
    manifest_id: str,
    stored_output_id: str,
    adapter_store_dir: Annotated[
        Path | None,
        typer.Option(
            "--adapter-store-dir",
            help="Base directory for adapter results (default: ~/.neurolab/data/adapter_outputs).",
            path_type=Path,
        ),
    ] = None,
):
    """
    Show metadata for one persisted parsed child record derived from a manifest.
    """
    roster_store = RosterStore()
    resolved_id = _resolve_manifest_id(manifest_id, roster_store)
    canonical_id = _canonical_manifest_id(resolved_id)
    store = FileAdapterResultStore(base_dir=adapter_store_dir)
    try:
        meta = store.load_metadata(canonical_id, stored_output_id)
    except StoredOutputNotFound as err:
        print(f"[red]{err}[/red]")
        raise typer.Exit(code=1) from err

    table = Table(title=f"Child record {_short_id(meta.stored_output_id, 12)} (manifest {resolved_id})")
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="bold green")
    table.add_row("stored_output_id", meta.stored_output_id)
    table.add_row("manifest_id", meta.manifest_id)
    table.add_row("artifact_id", meta.artifact_id)
    table.add_row("adapter_name", meta.adapter_name)
    table.add_row("adapter_version", meta.adapter_version)
    table.add_row("dataset_type", meta.dataset_type)
    table.add_row("pipeline_ordinal", str(meta.pipeline_ordinal))
    table.add_row("payload_format", meta.payload_format)
    table.add_row("payload_path", meta.payload_path)
    table.add_row("row_count", "" if meta.row_count is None else str(meta.row_count))
    table.add_row("shape_summary", "" if meta.shape_summary is None else json.dumps(meta.shape_summary, sort_keys=True))
    print(table)
    print("[bold]schema[/bold]")
    print(json.dumps(meta.schema, indent=2, sort_keys=True, ensure_ascii=False))


@child_app.command("payload")
def child_payload(
    manifest_id: str,
    stored_output_id: str,
    full: Annotated[
        bool,
        typer.Option("--full", help="Print full payload (arrays expanded)."),
    ] = False,
    head: Annotated[
        int | None,
        typer.Option("--head", help="When payload is a list, show only the first N elements."),
    ] = None,
    adapter_store_dir: Annotated[
        Path | None,
        typer.Option(
            "--adapter-store-dir",
            help="Base directory for adapter results (default: ~/.neurolab/data/adapter_outputs).",
            path_type=Path,
        ),
    ] = None,
):
    """
    Display the reconstructed payload for one persisted parsed child record derived from a manifest.
    """
    roster_store = RosterStore()
    resolved_id = _resolve_manifest_id(manifest_id, roster_store)
    canonical_id = _canonical_manifest_id(resolved_id)
    store = FileAdapterResultStore(base_dir=adapter_store_dir)
    try:
        payload = store.load_payload(canonical_id, stored_output_id)
    except StoredOutputNotFound as err:
        print(f"[red]{err}[/red]")
        raise typer.Exit(code=1) from err

    if head is not None and isinstance(payload, list):
        payload = payload[: max(0, int(head))]

    rendered = _render_payload_for_display(payload, full=full)
    print(json.dumps(rendered, indent=2, sort_keys=True, ensure_ascii=False))


@hub_app.command("list")
def hub_list(
    manifest_id: Annotated[str | None, typer.Option("--manifest-id", help="Filter by manifest_id.")] = None,
    artifact_id: Annotated[str | None, typer.Option("--artifact-id", help="Filter by artifact_id.")] = None,
    adapter_name: Annotated[str | None, typer.Option("--adapter-name", help="Filter by adapter_name.")] = None,
    dataset_type: Annotated[str | None, typer.Option("--dataset-type", help="Filter by dataset_type.")] = None,
    limit: Annotated[int | None, typer.Option("--limit", help="Show only the first N records after filtering.")] = None,
    long: Annotated[bool, typer.Option("--long", help="Include additional metadata columns.")] = False,
    hub_dir: Annotated[
        Path | None,
        typer.Option("--hub-dir", help="Base directory for hub records (default: ~/.neurolab/data/adapter_outputs).", path_type=Path),
    ] = None,
    adapter_store_dir: Annotated[
        Path | None,
        typer.Option(
            "--adapter-store-dir",
            help="Alias for --hub-dir (default: ~/.neurolab/data/adapter_outputs).",
            path_type=Path,
        ),
    ] = None,
):
    hub = _build_analysis_hub(hub_dir=hub_dir, adapter_store_dir=adapter_store_dir)
    records = _hub_filter_records(hub, manifest_id=manifest_id, artifact_id=artifact_id, adapter_name=adapter_name, dataset_type=dataset_type)
    if limit is not None:
        records = records[: max(0, int(limit))]

    table = Table(title="Analysis Hub Records")
    table.add_column("Stored Output ID", style="cyan", no_wrap=True)
    table.add_column("Manifest ID", style="green", no_wrap=True)
    table.add_column("Artifact ID", style="green", no_wrap=True)
    table.add_column("Adapter", style="bold")
    table.add_column("Dataset Type")
    table.add_column("Row Count", justify="right", style="dim")
    table.add_column("Shape Summary", style="dim")
    if long:
        table.add_column("Adapter Ver", style="dim")
        table.add_column("Ordinal", justify="right", style="dim")
        table.add_column("Payload Format", style="dim")
        table.add_column("Payload Path", style="dim")

    for r in records:
        row = [
            _short_id(r.stored_output_id, 12),
            _short_id(r.manifest_id, 12),
            r.artifact_id,
            r.adapter_name,
            r.dataset_type,
            "" if r.row_count is None else str(r.row_count),
            "" if r.shape_summary is None else json.dumps(r.shape_summary, sort_keys=True, ensure_ascii=False),
        ]
        if long:
            row.extend([r.adapter_version, str(r.pipeline_ordinal), r.payload_format, r.payload_path])
        table.add_row(*row)
    print(table)


@hub_app.command("show")
def hub_show(
    stored_output_id: Annotated[str, typer.Argument(help="stored_output_id of the record to display.")],
    hub_dir: Annotated[
        Path | None,
        typer.Option("--hub-dir", help="Base directory for hub records (default: ~/.neurolab/data/adapter_outputs).", path_type=Path),
    ] = None,
    adapter_store_dir: Annotated[
        Path | None,
        typer.Option("--adapter-store-dir", help="Alias for --hub-dir.", path_type=Path),
    ] = None,
):
    hub = _build_analysis_hub(hub_dir=hub_dir, adapter_store_dir=adapter_store_dir)
    try:
        r = hub.get_record(stored_output_id)
    except MetadataRecordNotFoundError as err:
        print(f"[red]Stored output not found: {stored_output_id}[/red]")
        raise typer.Exit(code=1) from err

    fp = schema_fingerprint(r.schema)

    table = Table(title=f"Hub record {_short_id(r.stored_output_id, 12)}")
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="bold green")

    table.add_row("stored_output_id", r.stored_output_id)
    table.add_row("manifest_id", r.manifest_id)
    table.add_row("artifact_id", r.artifact_id)
    table.add_row("adapter_name", r.adapter_name)
    table.add_row("adapter_version", r.adapter_version)
    table.add_row("dataset_type", r.dataset_type)
    table.add_row("pipeline_ordinal", str(r.pipeline_ordinal))
    table.add_row("payload_format", r.payload_format)
    table.add_row("payload_path", r.payload_path)
    table.add_row("row_count", "" if r.row_count is None else str(r.row_count))
    table.add_row("shape_summary", "" if r.shape_summary is None else json.dumps(r.shape_summary, sort_keys=True, ensure_ascii=False))
    table.add_row("schema_fingerprint", fp)
    print(table)

    print("[bold]schema[/bold]")
    print(json.dumps(r.schema, indent=2, sort_keys=True, ensure_ascii=False))


@hub_app.command("count")
def hub_count(
    manifest_id: Annotated[str | None, typer.Option("--manifest-id", help="Filter by manifest_id.")] = None,
    artifact_id: Annotated[str | None, typer.Option("--artifact-id", help="Filter by artifact_id.")] = None,
    adapter_name: Annotated[str | None, typer.Option("--adapter-name", help="Filter by adapter_name.")] = None,
    dataset_type: Annotated[str | None, typer.Option("--dataset-type", help="Filter by dataset_type.")] = None,
    hub_dir: Annotated[
        Path | None,
        typer.Option("--hub-dir", help="Base directory for hub records (default: ~/.neurolab/data/adapter_outputs).", path_type=Path),
    ] = None,
    adapter_store_dir: Annotated[
        Path | None,
        typer.Option("--adapter-store-dir", help="Alias for --hub-dir.", path_type=Path),
    ] = None,
):
    hub = _build_analysis_hub(hub_dir=hub_dir, adapter_store_dir=adapter_store_dir)
    records = _hub_filter_records(hub, manifest_id=manifest_id, artifact_id=artifact_id, adapter_name=adapter_name, dataset_type=dataset_type)

    adapter_counts: dict[str, int] = {}
    dataset_counts: dict[str, int] = {}
    manifests: set[str] = set()
    artifacts: set[str] = set()
    with_row_count = 0
    with_shape_summary = 0

    for r in records:
        adapter_counts[r.adapter_name] = adapter_counts.get(r.adapter_name, 0) + 1
        dataset_counts[r.dataset_type] = dataset_counts.get(r.dataset_type, 0) + 1
        manifests.add(r.manifest_id)
        artifacts.add(r.artifact_id)
        if r.row_count is not None:
            with_row_count += 1
        if r.shape_summary is not None:
            with_shape_summary += 1

    summary = Table(title="Analysis Hub Count Summary")
    summary.add_column("Metric", style="bold cyan")
    summary.add_column("Value", style="bold green", justify="right")
    summary.add_row("Total records", str(len(records)))
    summary.add_row("Distinct manifests", str(len(manifests)))
    summary.add_row("Distinct artifacts", str(len(artifacts)))
    summary.add_row("With row_count", str(with_row_count))
    summary.add_row("With shape_summary", str(with_shape_summary))
    print(summary)

    if adapter_counts:
        t = Table(title="Counts by adapter_name")
        t.add_column("adapter_name", style="bold")
        t.add_column("count", justify="right")
        for k in sorted(adapter_counts):
            t.add_row(k, str(adapter_counts[k]))
        print(t)

    if dataset_counts:
        t = Table(title="Counts by dataset_type")
        t.add_column("dataset_type", style="bold")
        t.add_column("count", justify="right")
        for k in sorted(dataset_counts):
            t.add_row(k, str(dataset_counts[k]))
        print(t)


@hub_app.command("load")
def hub_load(
    stored_output_id: Annotated[str, typer.Argument(help="stored_output_id of the record to load.")],
    json_out: Annotated[bool, typer.Option("--json", help="Print decoded payload as JSON (may be large).")] = False,
    summary_only: Annotated[bool, typer.Option("--summary-only", help="Print only a summary (default behavior).")] = True,
    hub_dir: Annotated[
        Path | None,
        typer.Option("--hub-dir", help="Base directory for hub records (default: ~/.neurolab/data/adapter_outputs).", path_type=Path),
    ] = None,
    adapter_store_dir: Annotated[
        Path | None,
        typer.Option("--adapter-store-dir", help="Alias for --hub-dir.", path_type=Path),
    ] = None,
):
    hub = _build_analysis_hub(hub_dir=hub_dir, adapter_store_dir=adapter_store_dir)
    try:
        h = hub.open_handle(stored_output_id)
    except MetadataRecordNotFoundError as err:
        print(f"[red]Stored output not found: {stored_output_id}[/red]")
        raise typer.Exit(code=1) from err

    try:
        payload = h.load()
    except PayloadNotFoundError as err:
        print(f"[red]{err}[/red]")
        raise typer.Exit(code=1) from err

    r = h.metadata
    payload_type = type(payload).__name__
    keys = list(payload.keys()) if isinstance(payload, dict) else None
    n_items = len(payload) if isinstance(payload, list) else None

    table = Table(title=f"Loaded payload for {_short_id(r.stored_output_id, 12)}")
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="bold green")
    table.add_row("stored_output_id", r.stored_output_id)
    table.add_row("python_type", payload_type)
    if keys is not None:
        table.add_row("top_level_keys", ", ".join([str(k) for k in keys[:20]]) + ("" if len(keys) <= 20 else ", ..."))
    if n_items is not None:
        table.add_row("list_length", str(n_items))
    table.add_row("row_count", "" if r.row_count is None else str(r.row_count))
    table.add_row("shape_summary", "" if r.shape_summary is None else json.dumps(r.shape_summary, sort_keys=True, ensure_ascii=False))
    print(table)

    if summary_only and not json_out:
        return

    if json_out:
        rendered = _render_payload_for_display(payload, full=True)
        print(json.dumps(rendered, indent=2, sort_keys=True, ensure_ascii=False))


@hub_app.command("schemas")
def hub_schemas(
    manifest_id: Annotated[str | None, typer.Option("--manifest-id", help="Filter by manifest_id.")] = None,
    artifact_id: Annotated[str | None, typer.Option("--artifact-id", help="Filter by artifact_id.")] = None,
    adapter_name: Annotated[str | None, typer.Option("--adapter-name", help="Filter by adapter_name.")] = None,
    dataset_type: Annotated[str | None, typer.Option("--dataset-type", help="Filter by dataset_type.")] = None,
    long: Annotated[bool, typer.Option("--long", help="Include an example id and schema preview.")] = False,
    hub_dir: Annotated[
        Path | None,
        typer.Option("--hub-dir", help="Base directory for hub records (default: ~/.neurolab/data/adapter_outputs).", path_type=Path),
    ] = None,
    adapter_store_dir: Annotated[
        Path | None,
        typer.Option("--adapter-store-dir", help="Alias for --hub-dir.", path_type=Path),
    ] = None,
):
    hub = _build_analysis_hub(hub_dir=hub_dir, adapter_store_dir=adapter_store_dir)
    records = _hub_filter_records(hub, manifest_id=manifest_id, artifact_id=artifact_id, adapter_name=adapter_name, dataset_type=dataset_type)

    groups: dict[tuple[str, str, str], list] = {}
    for r in records:
        fp = schema_fingerprint(r.schema)
        key = (r.adapter_name, r.dataset_type, fp)
        groups.setdefault(key, []).append(r)

    table = Table(title="Schemas in Analysis Hub")
    table.add_column("adapter_name", style="bold")
    table.add_column("dataset_type")
    table.add_column("schema_fingerprint", style="cyan", no_wrap=True)
    table.add_column("record_count", justify="right")
    if long:
        table.add_column("example_id", style="dim", no_wrap=True)
        table.add_column("schema_preview", style="dim")

    for (an, dt, fp) in sorted(groups.keys()):
        rs = groups[(an, dt, fp)]
        row = [an, dt, fp, str(len(rs))]
        if long:
            example = rs[0]
            preview = canonical_json(example.schema)
            if len(preview) > 200:
                preview = preview[:200] + "..."
            row.extend([_short_id(example.stored_output_id, 12), preview])
        table.add_row(*row)

    print(table)


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
def show(
    manifest_id: str,
    long: Annotated[
        bool,
        typer.Option("--long", help="Show artifact details."),
    ] = False,
):
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

    if not long:
        return

    # Artifact detail table
    art_table = Table(title="Artifacts")
    art_table.add_column("Path", style="cyan")
    art_table.add_column("Size", justify="right")
    art_table.add_column("Media Type", style="green")
    art_table.add_column("Hash", style="dim")

    for artifact in manifest.artifacts:
        art_table.add_row(
            artifact.relative_path,
            str(artifact.size_bytes),
            artifact.media_type or "-",
            artifact.content_hash[:12] + "...",
        )

    print()
    print(art_table)


@app.command()
def parse(
    manifest_id: str,
    store_outputs: Annotated[
        bool,
        typer.Option("--store-outputs", help="Persist adapter outputs to the adapter result store."),
    ] = False,
    adapter_store_dir: Annotated[
        Path | None,
        typer.Option(
            "--adapter-store-dir",
            help="Base directory for adapter results (default: ~/.neurolab/data/adapter_outputs).",
            path_type=Path,
        ),
    ] = None,
):
    """
    Run the adapter pipeline on a stored manifest and show a summary of outputs and skips.
    """
    store = FileManifestStore()
    roster_store = RosterStore()
    resolved_id = _resolve_manifest_id(manifest_id, roster_store)

    try:
        manifest = store.load(resolved_id)
    except FileNotFoundError as err:
        print(f"[red]Manifest {manifest_id} not found.[/red]")
        raise typer.Exit(code=1) from err

    pipeline = AdapterPipeline()
    result = pipeline.process_manifest(manifest)

    # Adapter usage counts (outputs per adapter_name)
    adapter_counts: dict[str, int] = {}
    for out in result.outputs:
        adapter_counts[out.adapter_name] = adapter_counts.get(out.adapter_name, 0) + 1

    manifest_display = resolved_id if len(resolved_id) <= 12 else f"{resolved_id[:8]}..."
    print(f"Manifest: {manifest_display}")
    print(f"Artifacts processed: {len(manifest.artifacts)}")
    print("Adapters used:")
    for name, count in sorted(adapter_counts.items()):
        print(f"  {name}: {count}")
    print(f"Outputs generated: {len(result.outputs)} datasets")
    print(f"Skipped artifacts: {len(result.skipped_artifacts)}")
    if store_outputs:
        ar_store = FileAdapterResultStore(base_dir=adapter_store_dir)
        saved = ar_store.save_pipeline_result(manifest, result)
        print(f"Stored {len(saved)} adapter output record(s) under manifest {resolved_id}.")

import typer
from rich import print
from rich.table import Table

from neurolab.data_interface.models import DataSourceSpec
from neurolab.data_interface.orchestrator import collect_source

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

    print(table)

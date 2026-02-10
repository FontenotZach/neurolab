import typer
from rich import print

app = typer.Typer(no_args_is_help=True)


@app.command()
def hello(name: str = "world"):
    print(f"[bold green]Hello[/bold green], {name}!")


def main():
    app()


if __name__ == "__main__":
    main()

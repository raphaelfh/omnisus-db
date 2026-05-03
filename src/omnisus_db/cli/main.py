"""omnisus-db CLI entry point (Typer + Rich)."""

from __future__ import annotations

import typer
from rich.console import Console

from omnisus_db.lake import Lake

app = typer.Typer(
    name="omnisus-db",
    help="Brazilian public health database ingestion lib.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

DEFAULT_TARGET = "ducklake:./omnisus.ducklake"


@app.command()
def init(
    target: str = typer.Option(
        DEFAULT_TARGET,
        "--target",
        "-t",
        help="DuckLake target (e.g. ducklake:./omnisus.ducklake)",
    ),
) -> None:
    """Initialize a new lake and load auxiliary tables."""
    console.print(f"[bold]Initializing[/bold] lake at {target}")
    with Lake.local(target) as lake:
        lake.bootstrap_auxiliares()
        tables = lake.tables()
    console.print(f"[green]:heavy_check_mark:[/green] {len(tables)} table(s): {', '.join(tables)}")


@app.command(name="import")
def import_cmd(
    dataset: str = typer.Argument(..., help="Dataset name (sim, sinasc, ...)"),
) -> None:
    """Import a dataset (stub — implemented in Phase 2+)."""
    console.print(f"[yellow]TODO[/yellow] import {dataset}")
    raise typer.Exit(code=2)


@app.command()
def query(sql: str = typer.Argument(...)) -> None:
    """Run an ad-hoc SQL query against the lake (stub)."""
    console.print(f"[yellow]TODO[/yellow] query: {sql}")
    raise typer.Exit(code=2)


lake_app = typer.Typer(name="lake", help="Lake operations.")
app.add_typer(lake_app)


@lake_app.command(name="tables")
def lake_tables_cmd() -> None:
    """List tables in the lake (stub)."""
    raise typer.Exit(code=2)


@app.command()
def doctor() -> None:
    """Run diagnostics on the environment (stub)."""
    raise typer.Exit(code=2)


if __name__ == "__main__":
    app()

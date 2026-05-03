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
    dataset: str = typer.Argument(..., help="sim | sinasc | sih | ibge-pop | cnes-st"),
    year: list[int] | None = typer.Option(
        None, "--year", "-y", help="Repeatable; e.g. -y 2023 -y 2024"
    ),
    years_range: str | None = typer.Option(None, "--years", help="e.g. 2020-2024"),
    ufs: str | None = typer.Option(None, "--ufs", help="Comma list: SP,RJ,MG"),
    months: str | None = typer.Option(None, "--months", help="Comma list, monthly only"),
    target: str = typer.Option(DEFAULT_TARGET, "--target", "-t"),
) -> None:
    """Import a dataset into the lake."""
    import omnisus_db as odb

    # Resolve years
    if years_range:
        a, b = years_range.split("-")
        yrs: list[int] = list(range(int(a), int(b) + 1))
    elif year:
        yrs = list(year)
    else:
        raise typer.BadParameter("provide --year/-y or --years RANGE")

    uf_list = [u.strip().upper() for u in ufs.split(",")] if ufs else None

    if dataset == "sim":
        results = odb.import_sim(years=yrs, ufs=uf_list, target=target)
    elif dataset == "sinasc":
        results = odb.import_sinasc(years=yrs, ufs=uf_list, target=target)
    elif dataset == "ibge-pop":
        results = odb.import_ibge_pop(years=yrs, target=target)
    elif dataset == "sih":
        m = [int(x) for x in months.split(",")] if months else range(1, 13)
        results = odb.import_sih(years=yrs, ufs=uf_list, months=m, target=target)
    elif dataset == "cnes-st":
        m = [int(x) for x in months.split(",")] if months else range(1, 13)
        results = odb.import_cnes_st(years=yrs, ufs=uf_list, months=m, target=target)
    else:
        raise typer.BadParameter(f"unknown dataset: {dataset}")

    total_rows = sum(r.rows for r in results)
    console.print(
        f"[green]:heavy_check_mark:[/green] imported [bold]{total_rows:,}[/bold] rows "
        f"({len(results)} scope(s))"
    )


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

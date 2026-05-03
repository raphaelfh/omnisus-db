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
def query(
    sql: str = typer.Argument(..., help="SQL to run against the lake"),
    target: str = typer.Option(DEFAULT_TARGET, "--target", "-t"),
) -> None:
    """Run an ad-hoc SQL query."""
    from rich.table import Table

    with Lake.local(target) as lake:
        rel = lake.connect().sql(sql)
        cols = list(rel.columns)
        rows = rel.fetchall()

    table = Table(*cols)
    for row in rows[:200]:
        table.add_row(*[str(v) for v in row])
    console.print(table)
    if len(rows) > 200:
        console.print(f"... ({len(rows)} rows total, showing first 200)")


lake_app = typer.Typer(name="lake", help="Lake operations.")
app.add_typer(lake_app)


@lake_app.command(name="tables")
def lake_tables_cmd(
    target: str = typer.Option(DEFAULT_TARGET, "--target", "-t"),
) -> None:
    """List user tables in the lake."""
    with Lake.local(target) as lake:
        for t in lake.tables():
            console.print(f"  {t}")


@lake_app.command(name="describe")
def lake_describe_cmd(
    table: str,
    target: str = typer.Option(DEFAULT_TARGET, "--target", "-t"),
) -> None:
    """Describe a lake table (columns + types)."""
    from rich.table import Table as RichTable

    with Lake.local(target) as lake:
        cols = lake.connect().execute(f"DESCRIBE lake.{table}").fetchall()
    rt = RichTable("Column", "Type")
    for c in cols:
        rt.add_row(str(c[0]), str(c[1]))
    console.print(rt)


@lake_app.command(name="snapshots")
def lake_snapshots_cmd(
    table: str,
    target: str = typer.Option(DEFAULT_TARGET, "--target", "-t"),
) -> None:
    """List snapshot history for a table."""
    with Lake.local(target) as lake:
        for snap in lake.snapshots(table):
            console.print(snap)


@lake_app.command(name="optimize")
def lake_optimize_cmd(
    table: str,
    target: str = typer.Option(DEFAULT_TARGET, "--target", "-t"),
) -> None:
    """Compact small Parquet files for a table."""
    with Lake.local(target) as lake:
        try:
            lake.optimize(table)
        except Exception as exc:
            # ducklake_compact_files can be a no-op or noisy on tiny tables;
            # surface the message but do not fail the CLI.
            console.print(f"[yellow]optimize note:[/yellow] {exc}")
            return
    console.print(f"[green]:heavy_check_mark:[/green] optimized {table}")


@lake_app.command(name="vacuum")
def lake_vacuum_cmd(
    older_than: str = typer.Option("30 days", "--older-than"),
    target: str = typer.Option(DEFAULT_TARGET, "--target", "-t"),
) -> None:
    """Drop snapshots older than the given interval."""
    with Lake.local(target) as lake:
        lake.vacuum(older_than=older_than)
    console.print(f"[green]:heavy_check_mark:[/green] vacuumed snapshots older than {older_than}")


@lake_app.command(name="update-auxiliares")
def lake_update_aux_cmd(
    target: str = typer.Option(DEFAULT_TARGET, "--target", "-t"),
) -> None:
    """Refresh aux_* tables from the bundled bootstrap.zip."""
    with Lake.local(target) as lake:
        lake.bootstrap_auxiliares()
    console.print("[green]:heavy_check_mark:[/green] aux tables refreshed")


@app.command()
def doctor() -> None:
    """Print diagnostic info (versions, env)."""
    import duckdb
    import polars as pl
    import pyarrow as pa

    from omnisus_db._version import __version__ as v

    console.print(f"omnisus-db: {v}")
    console.print(f"DuckDB:     {duckdb.__version__}")
    console.print(f"Polars:     {pl.__version__}")
    console.print(f"PyArrow:    {pa.__version__}")

    try:
        con = duckdb.connect()
        con.execute("INSTALL ducklake; LOAD ducklake;")
        console.print("[green]:heavy_check_mark:[/green] ducklake extension OK")
    except Exception as exc:
        console.print(f"[red]x[/red] ducklake load failed: {exc}")


if __name__ == "__main__":
    app()

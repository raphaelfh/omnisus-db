"""omnisus-db CLI entry point (Typer + Rich)."""

from __future__ import annotations

from collections.abc import Callable

import typer
from rich.console import Console

from omnisus_db.lake import DEFAULT_TARGET, Lake
from omnisus_db.sources.datasus_ftp.datasets import ALIASES, REGISTRY, resolve

app = typer.Typer(
    name="omnisus-db",
    help="Brazilian public health database ingestion lib.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

_NON_FTP: dict[str, str] = {"ibge-pop": "ibge_pop", "ibge_pop": "ibge_pop"}
"""CLI names of datasets that are not DATASUS-FTP rows (spec §3.4), mapped to
their dataset name. Dispatch (in ``import_cmd``) looks up the importer for
that dataset name in a second, importer-keyed mapping built inside the
command body — a mapping entry with no importer raises ``KeyError`` loudly
rather than silently importing the wrong dataset."""


def dataset_choices() -> list[str]:
    """Every name ``omnisus-db import`` accepts — derived, never listed by hand."""
    return sorted({*REGISTRY, *ALIASES, *_NON_FTP})


def ftp_dataset_choices() -> list[str]:
    """Every name ``omnisus-db inventory`` accepts.

    A subset of :func:`dataset_choices`: the inventory reads the DATASUS FTP
    server, so datasets that do not come from it (``_NON_FTP``) have nothing
    to list. Offering a name the command then rejects is a declaration that
    lies (spec I5).
    """
    return sorted({*REGISTRY, *ALIASES})


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
    dataset: str = typer.Argument(..., help=f"One of: {', '.join(dataset_choices())}"),
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

    non_ftp_importers: dict[str, Callable[..., list[odb.ImportResult]]] = {
        "ibge_pop": lambda **kw: odb.import_ibge_pop(**kw),
    }

    # Resolve years
    if years_range:
        a, b = years_range.split("-")
        yrs: list[int] = list(range(int(a), int(b) + 1))
    elif year:
        yrs = list(year)
    else:
        raise typer.BadParameter("provide --year/-y or --years RANGE")

    uf_list = [u.strip().upper() for u in ufs.split(",")] if ufs else None
    month_list = [int(x) for x in months.split(",")] if months else None

    if dataset in _NON_FTP:
        name = _NON_FTP[dataset]
        importer = non_ftp_importers[name]
        results = importer(years=yrs, target=target)
    else:
        try:
            d = resolve(dataset)
        except ValueError as exc:
            raise typer.BadParameter(
                f"{exc}. Choose from: {', '.join(dataset_choices())}"
            ) from exc
        if d.name == "cnes_st":
            # Named importer: refreshes aux_cnes after the load (spec §3.4, I2).
            results = odb.import_cnes_st(
                years=yrs, ufs=uf_list, months=month_list or range(1, 13), target=target
            )
        else:
            results = odb.import_dataset(
                d,
                scopes=odb.scopes_for(d, years=yrs, ufs=uf_list, months=month_list),
                target=target,
            )

    total_rows = sum(r.rows for r in results)
    console.print(
        f"[green]:heavy_check_mark:[/green] imported [bold]{total_rows:,}[/bold] rows "
        f"({len(results)} scope(s))"
    )


@app.command()
def inventory(
    dataset: str | None = typer.Argument(
        None, help=f"One of: {', '.join(ftp_dataset_choices())}. Omit when using --path."
    ),
    path: str | None = typer.Option(
        None, "--path", "-p", help="Browse any FTP path instead (e.g. /dissemin/publicos/SINAN)"
    ),
    depth: int = typer.Option(1, "--depth", "-d", help="Recursion depth for --path (1-4)"),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass the 24h listing cache"),
) -> None:
    """Show what DATASUS actually publishes, from a cached FTP listing."""
    from rich.table import Table as RichTable

    import omnisus_db as odb
    from omnisus_db.sources.datasus_ftp.datasets import resolve
    from omnisus_db.sources.datasus_ftp.inventory import FtpPathNotFound, FtpUnavailable

    if (dataset is None) == (path is None):
        raise typer.BadParameter("provide exactly one of DATASET or --path")
    if path is not None and not 1 <= depth <= 4:
        raise typer.BadParameter("--depth must be between 1 and 4")

    try:
        if path is not None:
            entries = odb.browse(path, depth=depth, refresh=refresh)
            table = RichTable("Name", "Type", "Size", "Modified")
            for e in entries:
                table.add_row(
                    e.name,
                    "dir" if e.is_dir else "file",
                    "" if e.is_dir else f"{e.size_bytes:,}",
                    e.modified.strftime("%Y-%m-%d %H:%M"),
                )
            console.print(table)
            console.print(f"[dim]{len(entries)} entry(ies) under {path}[/dim]")
            return
        assert dataset is not None, "the XOR check above guarantees this"
        try:
            d = resolve(dataset)
        except ValueError as exc:
            raise typer.BadParameter(
                f"{exc}. Choose from: {', '.join(ftp_dataset_choices())}"
            ) from exc
        scopes = odb.available(d, refresh=refresh)
        table = RichTable("UF", "Ano", "Mês")
        for s in scopes:
            table.add_row(s.uf, str(s.ano), "" if s.mes is None else f"{s.mes:02d}")
        console.print(table)
        console.print(f"[dim]{len(scopes)} scope(s) available for {d.name}[/dim]")
    except FtpPathNotFound as exc:
        console.print(f"[red]x[/red] not found on the server: {exc}")
        raise typer.Exit(code=1) from exc
    except FtpUnavailable as exc:
        console.print(f"[red]x[/red] DATASUS FTP unreachable: {exc}")
        raise typer.Exit(code=1) from exc


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

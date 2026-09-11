"""DuckDB connection factory with ducklake extension loaded."""

from __future__ import annotations

import contextlib
from pathlib import Path

import duckdb

from omnisus_db.lake.sql import quote_identifier, quote_literal

SUPPORTED_CATALOG_SCHEMES = ("sqlite", "postgresql", "postgres", "duckdb")


class CatalogAttachError(RuntimeError):
    """The DuckLake catalog could not be opened, so there is no lake to use.

    ``stage`` names the statement that failed: ``"install"`` (the ducklake
    extension), ``"attach"`` (the catalog itself) or ``"set_option"``; the
    message adds the DuckDB error class. For a remote catalog the DuckDB error
    is not chained — its text can echo the connection string — so stage and
    class are the whole diagnostic. For a local catalog it is chained, so the
    file-level reason stays visible.
    """

    def __init__(self, stage: str, duckdb_error: str) -> None:
        self.stage = stage
        super().__init__(f"could not open DuckLake catalog: {duckdb_error} during {stage}")


def make_connection(
    *,
    catalog_uri: str,
    storage_root: str,
    alias: str = "lake",
) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection with ducklake attached.

    Args:
        catalog_uri: ``sqlite:/path/to/catalog.sqlite`` or ``postgresql://...``.
        storage_root: filesystem path or s3:// URI for Parquet storage.
        alias: schema alias for the attached ducklake (default ``lake``).

    Returns:
        Connected ``DuckDBPyConnection`` with ducklake loaded and attached.

    Raises:
        CatalogAttachError: any of the three setup statements failed; the
            connection is closed before raising.
    """
    scheme = catalog_uri.split(":", 1)[0].lower()
    if scheme not in SUPPORTED_CATALOG_SCHEMES:
        raise ValueError(f"unsupported catalog scheme: {scheme!r}")

    if not storage_root.startswith(("s3://", "gs://", "az://", "azure://")):
        Path(storage_root).mkdir(parents=True, exist_ok=True)

    # DuckLake requires an explicit backend selector before a PostgreSQL URI.
    remote = scheme in ("postgres", "postgresql")
    metadata_path = "postgres:" + catalog_uri if remote else catalog_uri
    quoted_alias = quote_identifier(alias)
    statements = (
        ("install", "INSTALL ducklake; LOAD ducklake;"),
        (
            "attach",
            f"ATTACH {quote_literal('ducklake:' + metadata_path)} AS {quoted_alias} "
            f"(DATA_PATH {quote_literal(storage_root)})",
        ),
        ("set_option", f"CALL {quoted_alias}.set_option('parquet_compression', 'zstd')"),
    )
    con = duckdb.connect(":memory:")
    for stage, sql in statements:
        try:
            con.execute(sql)
        except BaseException as exc:
            con.close()
            if not isinstance(exc, Exception):
                raise
            cause = None if remote else exc  # a remote error can echo the connection string
            raise CatalogAttachError(stage, type(exc).__name__) from cause
    return con


def close_connection(con: duckdb.DuckDBPyConnection, alias: str = "lake") -> None:
    """Detach + close cleanly."""
    with contextlib.suppress(duckdb.Error):
        con.execute(f"DETACH {quote_identifier(alias)}")
    con.close()

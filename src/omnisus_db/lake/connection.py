"""DuckDB connection factory with ducklake extension loaded."""

from __future__ import annotations

import contextlib
from pathlib import Path

import duckdb

from omnisus_db.lake.sql import quote_identifier, quote_literal

SUPPORTED_CATALOG_SCHEMES = ("sqlite", "postgresql", "postgres", "duckdb")


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
    """
    scheme = catalog_uri.split(":", 1)[0].lower()
    if scheme not in SUPPORTED_CATALOG_SCHEMES:
        raise ValueError(f"unsupported catalog scheme: {scheme!r}")

    if not storage_root.startswith(("s3://", "gs://", "az://", "azure://")):
        Path(storage_root).mkdir(parents=True, exist_ok=True)

    # DuckLake requires an explicit backend selector before a PostgreSQL URI.
    metadata_path = (
        "postgres:" + catalog_uri if scheme in ("postgres", "postgresql") else catalog_uri
    )
    quoted_alias = quote_identifier(alias)
    con = duckdb.connect(":memory:")
    try:
        con.execute("INSTALL ducklake; LOAD ducklake;")
        con.execute(
            f"ATTACH {quote_literal('ducklake:' + metadata_path)} AS {quoted_alias} (DATA_PATH {quote_literal(storage_root)})"
        )
        con.execute(f"CALL {quoted_alias}.set_option('parquet_compression', 'zstd')")
    except BaseException as exc:
        con.close()
        if scheme in ("postgres", "postgresql") and isinstance(exc, Exception):
            raise duckdb.ConnectionException(
                "could not attach remote DuckLake catalog; check connection settings"
            ) from None
        raise
    return con


def close_connection(con: duckdb.DuckDBPyConnection, alias: str = "lake") -> None:
    """Detach + close cleanly."""
    with contextlib.suppress(duckdb.Error):
        con.execute(f"DETACH {quote_identifier(alias)}")
    con.close()

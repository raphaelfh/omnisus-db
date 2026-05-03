"""DuckDB connection factory with ducklake extension loaded."""

from __future__ import annotations

import contextlib
from pathlib import Path

import duckdb

SUPPORTED_CATALOG_SCHEMES = ("sqlite", "postgresql", "duckdb")


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

    con = duckdb.connect(":memory:")
    con.execute("INSTALL ducklake; LOAD ducklake;")
    con.execute(f"ATTACH 'ducklake:{catalog_uri}' AS {alias} (DATA_PATH '{storage_root}')")
    return con


def close_connection(con: duckdb.DuckDBPyConnection) -> None:
    """Detach + close cleanly."""
    with contextlib.suppress(duckdb.Error):
        con.execute("DETACH lake")
    con.close()

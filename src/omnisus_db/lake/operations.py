"""High-level Lake API."""

from __future__ import annotations

from typing import Self

import duckdb

from omnisus_db.lake.catalog import CatalogURI, parse_target
from omnisus_db.lake.connection import close_connection, make_connection


class Lake:
    """Handle on a DuckLake.

    Use :meth:`local` for SQLite-backed dev/researcher use, :meth:`cloud`
    for Postgres-backed multi-writer deployments.
    """

    def __init__(self, *, target: CatalogURI, alias: str = "lake") -> None:
        self._target = target
        self._alias = alias
        self._con = make_connection(
            catalog_uri=target.catalog_uri,
            storage_root=target.storage_root,
            alias=alias,
        )

    @classmethod
    def local(cls, target: str) -> Self:
        """Open or create a local SQLite-backed DuckLake."""
        return cls(target=parse_target(target))

    @classmethod
    def cloud(cls, *, catalog: str, storage: str) -> Self:
        """Open a Postgres-backed cloud DuckLake."""
        if not catalog.startswith(("postgresql://", "postgres://")):
            raise ValueError("cloud catalog must be postgresql://")
        target_str = f"ducklake:{catalog}?storage={storage}"
        return cls(target=parse_target(target_str))

    @property
    def alias(self) -> str:
        return self._alias

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Return the underlying DuckDB connection (raw, per spec §11.4)."""
        return self._con

    def tables(self) -> list[str]:
        """List user tables in the lake (excludes ducklake internals)."""
        rows = self._con.execute(
            f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_catalog = '{self._alias}'
            ORDER BY table_name
            """
        ).fetchall()
        return [name for (name,) in rows]

    def snapshots(self, table: str) -> list[dict[str, object]]:
        """Return snapshot history for a table."""
        rows = self._con.execute(
            f"SELECT * FROM ducklake_snapshots('{self._alias}.{table}')"
        ).fetchall()
        cols = [d[0] for d in self._con.description]
        return [dict(zip(cols, row, strict=True)) for row in rows]

    def optimize(self, table: str) -> None:
        """Compact small files (``ducklake_compact_files``)."""
        self._con.execute(f"CALL ducklake_compact_files('{self._alias}', '{table}')")

    def vacuum(self, *, older_than: str = "30 days") -> None:
        """Remove snapshots older than the given interval."""
        self._con.execute(
            f"CALL ducklake_cleanup_old_files('{self._alias}', "
            f"older_than => INTERVAL '{older_than}')"
        )

    def close(self) -> None:
        """Detach and close the connection."""
        close_connection(self._con)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

"""Sessions on a DuckLake catalog: the shared read surface and the read-only reader."""

from __future__ import annotations

from typing import Self

import duckdb

from omnisus_db.lake.catalog import parse_target
from omnisus_db.lake.connection import close_connection, make_reader_connection
from omnisus_db.lake.sql import quote_literal


class Session:
    """What every handle on a catalog can do: query, list, and close.

    Subclasses own how the connection is opened — :class:`Lake` for writing,
    under the writer lock; :class:`LakeReader` read-only — and hand it here.
    Raw SQL transaction control is outside this contract on either.
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, alias: str) -> None:
        self._con = con
        self._alias = alias
        self._closed = False
        self._unusable = False

    @property
    def alias(self) -> str:
        return self._alias

    @property
    def is_usable(self) -> bool:
        return not self._closed and not self._unusable

    def connect(self) -> duckdb.DuckDBPyConnection:
        if self._closed:
            raise RuntimeError("handle is closed")
        if self._unusable:
            raise RuntimeError("Lake handle is unusable; close it and inspect the catalog")
        return self._con

    def tables(self) -> list[str]:
        """List user tables in the lake (excludes ducklake internals)."""
        self.connect()
        rows = self._con.execute(
            f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_catalog = {quote_literal(self._alias)}
            ORDER BY table_name
            """
        ).fetchall()
        return [name for (name,) in rows]

    def snapshots(self) -> list[dict[str, object]]:
        """Return the catalog's snapshot history, oldest first.

        DuckLake snapshots are catalog-wide, not per-table: ``changes`` names
        which tables each one touched. The previous signature took a table and
        queried ``ducklake_snapshots('lake.<table>')``, which does not bind —
        so this method always raised, and ``ingest`` made the same call inside
        a bare ``except`` that turned it into ``snapshot_id=None`` on every
        import ever run.

        Timestamps come back as strings: DuckDB renders its own TIMESTAMPTZ
        through ``pytz``, which is not a dependency of this package.
        """
        self.connect()
        rows = self._con.execute(
            f"""
            SELECT snapshot_id, snapshot_time::VARCHAR, changes::VARCHAR
            FROM ducklake_snapshots({quote_literal(self._alias)})
            ORDER BY snapshot_id
            """
        ).fetchall()
        return [
            {"snapshot_id": int(sid), "snapshot_time": when, "changes": changes}
            for sid, when, changes in rows
        ]

    def publications(self, *, run_id: str | None = None) -> list[dict]:
        """Read durable publication IDs, including after an unknown commit outcome."""
        from omnisus_db.lake.publication import publications

        return publications(self, run_id=run_id)

    def attempts(self, *, run_id: str | None = None) -> list[dict]:
        """Read failed attempts recorded after known data rollbacks."""
        from omnisus_db.lake.publication import attempts

        return attempts(self, run_id=run_id)

    def close(self) -> None:
        if self._closed:
            return
        try:
            close_connection(self._con, self._alias)
        finally:
            self._closed = True

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


class LakeReader(Session):
    """Read-only session on an existing lake.

    ``target`` uses the same grammar as :meth:`Lake.local` —
    ``ducklake:./omnisus.ducklake`` or ``ducklake:postgresql://…?storage=…`` —
    and the storage part is ignored: the catalog records its own data path.
    Nothing is created and no option is set, so a reader never takes the
    writer lock and never blocks a writer; DuckLake refuses writes on the
    connection itself. ``snapshot_id`` pins the session to one snapshot
    (``snapshots()[-1]["snapshot_id"]`` is the latest); without it every
    statement reads the latest committed snapshot.

    Raises :class:`~omnisus_db.lake.CatalogAttachError` when the catalog does
    not exist or the pinned snapshot is unknown.
    """

    snapshot_id: int | None
    """The pinned snapshot, or ``None`` for a session that reads the latest one."""

    def __init__(
        self, target: str, *, snapshot_id: int | None = None, alias: str = "lake"
    ) -> None:
        if snapshot_id is not None and (type(snapshot_id) is not int or snapshot_id < 0):
            raise ValueError("snapshot_id must be a non-negative integer")
        self.snapshot_id = snapshot_id
        catalog = parse_target(target)
        con = make_reader_connection(
            catalog_uri=catalog.catalog_uri, alias=alias, snapshot_id=snapshot_id
        )
        super().__init__(con, alias)

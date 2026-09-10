"""High-level Lake API."""

from __future__ import annotations

import contextlib
import re
from typing import TYPE_CHECKING, Self

import duckdb
import structlog

from omnisus_db.lake._transactions import (
    CommitOutcomeUnknown,
    TransactionReceipt,
    TransactionStateError,
)
from omnisus_db.lake.catalog import CatalogURI, parse_target
from omnisus_db.lake.connection import close_connection, make_connection

if TYPE_CHECKING:
    from collections.abc import Iterator

    import polars as pl

    from omnisus_db.sources._base import ImportResult

logger = structlog.get_logger(__name__)

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class Lake:
    """Handle on a DuckLake.

    Use :meth:`local` for SQLite-backed dev/researcher use, :meth:`cloud`
    for Postgres-backed multi-writer deployments.
    """

    def __init__(self, *, target: CatalogURI, alias: str = "lake") -> None:
        self._target = target
        self._alias = alias
        self._in_transaction = False
        self._unusable = False
        self._closed = False
        self._pending_results: list[ImportResult] = []
        self._ensured: set[str] = set()
        """Tables this handle has already created and partitioned. Ensuring a
        table costs a schema read of the staging file; once per run is enough."""
        self._columns: dict[str, set[str]] = {}
        """Known column names per table, so schema reconciliation does not
        re-query the catalog for every scope."""
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

    @property
    def in_transaction(self) -> bool:
        return self._in_transaction

    @property
    def is_usable(self) -> bool:
        return not self._closed and not self._unusable

    def connect(self) -> duckdb.DuckDBPyConnection:
        if not self.is_usable:
            raise RuntimeError("Lake handle is unusable; close it and inspect the catalog")
        return self._con

    def _read_snapshot(self) -> int | None:
        row = self._con.execute(
            "SELECT id FROM ducklake_last_committed_snapshot(?)", [self._alias]
        ).fetchone()
        return None if row is None or row[0] is None else int(row[0])

    def tables(self) -> list[str]:
        """List user tables in the lake (excludes ducklake internals)."""
        self.connect()
        rows = self._con.execute(
            f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_catalog = '{self._alias}'
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
            FROM ducklake_snapshots('{self._alias}')
            ORDER BY snapshot_id
            """
        ).fetchall()
        return [
            {"snapshot_id": int(sid), "snapshot_time": when, "changes": changes}
            for sid, when, changes in rows
        ]

    @contextlib.contextmanager
    def transaction(self) -> Iterator[TransactionReceipt]:
        self.connect()  # Reject closed or invalidated handles.
        if self._in_transaction:
            raise RuntimeError("nested Lake.transaction is not supported")
        self._columns.clear()
        self._ensured.clear()
        try:
            before = self._read_snapshot()
            self._con.execute("BEGIN TRANSACTION")
        except BaseException as exc:
            self._unusable = True
            if not isinstance(exc, Exception):
                raise
            raise TransactionStateError("could not begin managed transaction") from exc

        receipt = TransactionReceipt()
        self._in_transaction = True
        self._pending_results = []
        try:
            try:
                yield receipt
            except BaseException as original:
                try:
                    self._con.execute("ROLLBACK")
                except BaseException as rollback_error:
                    self._unusable = True
                    original.add_note(f"rollback also failed: {rollback_error}")
                    if isinstance(original, Exception):
                        raise TransactionStateError(
                            "rollback failed; handle unusable"
                        ) from original
                raise
            else:
                try:
                    self._con.execute("COMMIT")
                except BaseException as original:
                    self._unusable = True
                    try:
                        self._con.execute("ROLLBACK")
                    except BaseException as rollback_error:
                        original.add_note(f"rollback cleanup also failed: {rollback_error}")
                    if not isinstance(original, Exception):
                        raise
                    raise CommitOutcomeUnknown(
                        "commit outcome unknown; inspect before retry"
                    ) from original

                receipt.committed = True
                try:
                    after = self._read_snapshot()
                except Exception:
                    logger.warning("lake.snapshot_unavailable_after_commit")
                else:
                    receipt.snapshot_id = after if after != before else None
                for result in self._pending_results:
                    result.snapshot_id = receipt.snapshot_id
        finally:
            self._in_transaction = False
            self._pending_results = []
            self._columns.clear()
            self._ensured.clear()

    def optimize(self, table: str) -> None:
        """Compact small files (``ducklake_compact_files``)."""
        self.connect()
        self._con.execute(f"CALL ducklake_compact_files('{self._alias}', '{table}')")

    def vacuum(self, *, older_than: str = "30 days") -> None:
        """Remove snapshots older than the given interval."""
        self.connect()
        self._con.execute(
            f"CALL ducklake_cleanup_old_files('{self._alias}', "
            f"older_than => INTERVAL '{older_than}')"
        )

    def bootstrap_auxiliares(self) -> None:
        """Load aux_* tables from the packaged bootstrap.zip.

        Idempotent: re-running replaces the table contents.
        """
        self.connect()

        import io
        import os
        import tempfile
        import zipfile
        from importlib.resources import files

        zip_bytes = (files("omnisus_db.data") / "auxiliares-bootstrap.zip").read_bytes()
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for name in zf.namelist():
                if not name.endswith(".parquet"):
                    continue
                table = name.removesuffix(".parquet")
                with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
                    tmp.write(zf.read(name))
                    tmp_path = tmp.name
                try:
                    self._con.execute(
                        f"CREATE OR REPLACE TABLE {self._alias}.{table} AS "
                        f"SELECT * FROM read_parquet('{tmp_path}')"
                    )
                finally:
                    os.unlink(tmp_path)

    def ensure_aux_cnes_view(self) -> bool:
        """Create or refresh ``aux_cnes`` — one row per CNES, joining
        ``cnes_st`` (operational, monthly snapshots) with ``cnes_master``
        (names from the API).

        Output columns:
            cnes        : 7-digit code
            nome        : establishment name (NULL if cnes_master not loaded)
            tp_unid     : unit type, latest snapshot
            codufmun    : município IBGE, latest snapshot
            yyyymm_max  : ``ano*100+mes`` of the latest cnes_st snapshot

        Behaviour:
            - ``cnes_st`` missing → no-op, returns ``False``.
            - ``cnes_master`` missing → view still works, but ``nome`` is NULL.
              Run ``import_cnes_master()`` to populate names.
        """
        self.connect()
        tables = set(self.tables())
        if "cnes_st" not in tables:
            return False

        if "cnes_master" in tables:
            nome_select = "m.nome"
            join_clause = f"LEFT JOIN {self._alias}.cnes_master m USING (cnes)"
        else:
            nome_select = "CAST(NULL AS VARCHAR) AS nome"
            join_clause = ""

        self._con.execute(
            f"""
            CREATE OR REPLACE VIEW {self._alias}.aux_cnes AS
            WITH latest AS (
                SELECT
                    cnes,
                    ARG_MAX(tp_unid,  ano * 100 + mes) AS tp_unid,
                    ARG_MAX(codufmun, ano * 100 + mes) AS codufmun,
                    MAX(ano * 100 + mes) AS yyyymm_max
                FROM {self._alias}.cnes_st
                WHERE cnes IS NOT NULL
                GROUP BY cnes
            )
            SELECT
                latest.cnes,
                {nome_select},
                latest.tp_unid,
                latest.codufmun,
                latest.yyyymm_max
            FROM latest
            {join_clause}
            """
        )
        return True

    def _staging_columns(self, staging: str) -> list[tuple[str, str]]:
        """(name, type) of the staging file, read from the Parquet footer."""
        return [
            (str(name), str(dtype))
            for name, dtype, *_ in self._con.execute(
                f"DESCRIBE SELECT * FROM read_parquet('{staging}')"
            ).fetchall()
        ]

    def _table_columns(self, table: str) -> set[str]:
        if table not in self._columns:
            rows = self._con.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_catalog = ? AND table_name = ?
                """,
                [self._alias, table],
            ).fetchall()
            self._columns[table] = {str(name) for (name,) in rows}
        return self._columns[table]

    def _ensure_table(self, table: str, staging: str, partition_by: tuple[str, ...]) -> None:
        """Create the table and set its partitioning, then keep its schema wide
        enough for what is being inserted.

        DATASUS changes its layouts between eras: SIM-DO goes 42 columns in
        1996, 45 in 2005, 61 in 2010, 90 in 2015 and 89 in 2020, adding *and*
        removing columns. A table created from whichever scope landed first
        therefore rejects most of the others, which is why a multi-year import
        could not build a lake at all. New columns are added as they appear;
        columns a given era lacks are left NULL by ``INSERT ... BY NAME``.
        """
        if table not in set(self.tables()):
            self._con.execute(
                f"CREATE TABLE {self._alias}.{table} AS "
                f"SELECT * FROM read_parquet('{staging}') WHERE 1=0"
            )
            if partition_by:
                bad = [c for c in partition_by if not _IDENTIFIER.match(c)]
                if bad:
                    raise ValueError(f"partition_by must be plain identifiers; got {bad}")
                cols = ", ".join(partition_by)
                self._con.execute(f"ALTER TABLE {self._alias}.{table} SET PARTITIONED BY ({cols})")
            self._columns.pop(table, None)
            self._ensured.add(table)
            return

        known = self._table_columns(table)
        missing = [(n, t) for n, t in self._staging_columns(staging) if n not in known]
        for name, dtype in missing:
            if not _IDENTIFIER.match(name):
                raise ValueError(f"refusing to add a non-identifier column: {name!r}")
            self._con.execute(f"ALTER TABLE {self._alias}.{table} ADD COLUMN {name} {dtype}")
            known.add(name)
        if missing:
            logger.info(
                "lake.schema_widened",
                table=table,
                added=[n for n, _ in missing],
            )
        self._ensured.add(table)

    def ingest(
        self,
        table: str,
        lazyframe: pl.LazyFrame,
        *,
        partition_by: tuple[str, ...] = (),
    ) -> ImportResult:
        """Append data in a managed transaction. Direct calls commit before returning.
        Inside Lake.transaction(), snapshot_id remains None until that context commits.
        Raw SQL BEGIN/COMMIT is outside this managed-transaction contract.

        Args:
            table: destination table name (e.g. "sim_do")
            lazyframe: pl.LazyFrame to materialize and insert
            partition_by: columns to partition the table by, applied once when
                the table is created. Previously accepted and discarded, which
                made every registry row's declared ``partition_by`` a lie
                (spec I5).

        """
        import tempfile
        import time
        from pathlib import Path

        from omnisus_db.sources._base import ImportResult

        self.connect()
        if not self.in_transaction:
            with self.transaction():
                return self.ingest(table, lazyframe, partition_by=partition_by)

        t0 = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="omnisus-staging-") as tmp:
            staging = Path(tmp) / f"{table}.parquet"
            lazyframe.sink_parquet(
                staging,
                row_group_size=1_000_000,
                compression="zstd",
            )
            bytes_written = staging.stat().st_size

            self._ensure_table(table, str(staging), partition_by)
            # BY NAME, not positional: eras differ in both column count and
            # order, and a column this era lacks must land as NULL rather than
            # shifting every value one place to the left.
            # INSERT reports its own row count, so the separate
            # SELECT count(*) over the same staging file is pure waste.
            inserted = self._con.execute(
                f"INSERT INTO {self._alias}.{table} BY NAME "
                f"SELECT * FROM read_parquet('{staging}')"
            ).fetchone()
            rows = 0 if inserted is None else int(inserted[0])

        duration = time.monotonic() - t0

        result = ImportResult(
            rows=int(rows),
            bytes_written=int(bytes_written),
            duration_seconds=duration,
            snapshot_id=None,
        )
        self._pending_results.append(result)
        return result

    def close(self) -> None:
        if self._closed:
            return
        try:
            close_connection(self._con)
        finally:
            self._closed = True
            self._columns.clear()
            self._ensured.clear()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

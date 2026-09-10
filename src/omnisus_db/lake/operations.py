"""High-level Lake API."""

from __future__ import annotations

import contextlib
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
from omnisus_db.lake.sql import qualified, quote_identifier, quote_literal

if TYPE_CHECKING:
    from collections.abc import Iterator

    import polars as pl

    from omnisus_db.sources._base import ImportResult

logger = structlog.get_logger(__name__)


class Lake:
    """Handle on a DuckLake.

    Use :meth:`local` with a ``ducklake:`` target or :meth:`cloud` for a
    Postgres-backed catalog. Managed ingestion requires one writer per lake,
    including when the catalog is hosted in Postgres.
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
        from omnisus_db.lake.locking import WriterLock

        self._writer_lock = WriterLock(target.catalog_uri)
        try:
            self._con = make_connection(
                catalog_uri=target.catalog_uri,
                storage_root=target.storage_root,
                alias=alias,
            )
        except BaseException:
            self._writer_lock.close()
            raise

    @classmethod
    def local(cls, target: str) -> Self:
        """Open or create a local SQLite-backed DuckLake."""
        return cls(target=parse_target(target))

    @classmethod
    def cloud(cls, *, catalog: str, storage: str) -> Self:
        """Open a Postgres-backed cloud DuckLake."""
        if not catalog.startswith(("postgresql://", "postgres://")):
            raise ValueError("cloud catalog must be postgresql://")
        return cls(target=CatalogURI(catalog_uri=catalog, storage_root=storage))

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
                        if not isinstance(rollback_error, Exception):
                            raise rollback_error from original
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
                        if isinstance(original, Exception) and not isinstance(
                            rollback_error, Exception
                        ):
                            raise rollback_error from original
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

    def optimize(self, table: str) -> list[dict]:
        """Compact table files, retaining historical snapshots."""
        from omnisus_db.lake.maintenance import run_maintenance

        return run_maintenance(self.connect(), alias=self._alias, operation="compact", table=table)

    def expire_snapshots(self, *, older_than, dry_run: bool = True) -> list[dict]:
        """Expire history before a timezone-aware datetime; simulate by default."""
        from omnisus_db.lake.maintenance import run_maintenance

        return run_maintenance(
            self.connect(),
            alias=self._alias,
            operation="expire",
            older_than=older_than,
            dry_run=dry_run,
        )

    def cleanup_files(self, *, older_than, dry_run: bool = True) -> list[dict]:
        """Clean obsolete files before a timezone-aware cutoff; simulate by default."""
        from omnisus_db.lake.maintenance import run_maintenance

        return run_maintenance(
            self.connect(),
            alias=self._alias,
            operation="cleanup",
            older_than=older_than,
            dry_run=dry_run,
        )

    def vacuum(self, *, older_than: str = "30 days") -> list[dict]:
        """Deprecated cleanup wrapper. This operation does not expire history."""
        import warnings

        from omnisus_db.lake.maintenance import interval_cutoff

        warnings.warn(
            "vacuum is deprecated; use cleanup_files with an explicit cutoff",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.cleanup_files(older_than=interval_cutoff(older_than), dry_run=False)

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
                        f"CREATE OR REPLACE TABLE {qualified(self._alias, table)} AS "
                        f"SELECT * FROM read_parquet({quote_literal(tmp_path)})"
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

        operational = qualified(self._alias, "cnes_st")
        view = qualified(self._alias, "aux_cnes")
        if "cnes_master" in tables:
            nome_select = "m.nome"
            join_clause = f"LEFT JOIN {qualified(self._alias, 'cnes_master')} m USING (cnes)"
        else:
            nome_select = "CAST(NULL AS VARCHAR) AS nome"
            join_clause = ""

        # Select all rows at the latest competence. Identical repeated imports
        # can collapse in this view; conflicting rows must never be picked by
        # incidental load order. The guard remains in the view for later inserts.
        latest_cte = f"""
            WITH ranked AS (
                SELECT cnes, tp_unid, codufmun, CAST(ano AS INTEGER) * 100 + CAST(mes AS INTEGER) AS yyyymm_max,
                       DENSE_RANK() OVER (PARTITION BY cnes ORDER BY ano DESC NULLS LAST, mes DESC NULLS LAST) AS rank
                FROM {operational} WHERE cnes IS NOT NULL
            ), latest AS (
                SELECT DISTINCT cnes, tp_unid, codufmun, yyyymm_max FROM ranked WHERE rank=1
            ), checked AS (
                SELECT *, COUNT(*) OVER (PARTITION BY cnes) AS variants FROM latest
            )
        """
        conflict = self._con.execute(
            latest_cte
            + "SELECT cnes FROM checked WHERE variants > 1 OR yyyymm_max IS NULL LIMIT 1"
        ).fetchone()
        if conflict:
            raise ValueError(
                "ambiguous or conflicting latest CNES rows; reconcile source versions before refreshing"
            )
        self._con.execute(f"""
            CREATE OR REPLACE VIEW {view} AS
            {latest_cte}
            SELECT CASE WHEN variants != 1 OR yyyymm_max IS NULL
                        THEN error('conflicting latest CNES rows') ELSE checked.cnes END AS cnes,
                   {nome_select}, checked.tp_unid, checked.codufmun, checked.yyyymm_max
            FROM checked {join_clause}
            WHERE CASE WHEN variants != 1 OR yyyymm_max IS NULL THEN error('conflicting latest CNES rows') ELSE true END
        """)
        return True

    def _staging_columns(self, staging: str) -> list[tuple[str, str]]:
        """(name, type) of the staging file, read from the Parquet footer."""
        return [
            (str(name), str(dtype))
            for name, dtype, *_ in self._con.execute(
                f"DESCRIBE SELECT * FROM read_parquet({quote_literal(str(staging))})"
            ).fetchall()
        ]

    def _table_columns(self, table: str) -> set[str]:
        if table not in self._columns:
            rows = self._con.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_catalog = ? AND table_schema = 'main' AND table_name = ?
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
                f"CREATE TABLE {qualified(self._alias, table)} AS "
                f"SELECT * FROM read_parquet({quote_literal(str(staging))}) WHERE 1=0"
            )
            if partition_by:
                cols = ", ".join(quote_identifier(c) for c in partition_by)
                self._con.execute(
                    f"ALTER TABLE {qualified(self._alias, table)} SET PARTITIONED BY ({cols})"
                )
            self._columns.pop(table, None)
            self._ensured.add(table)
            return

        import pyarrow as pa
        import pyarrow.parquet as pq

        from omnisus_db.lake.schema import compatible_type

        known = self._table_columns(table)
        existing_types = dict(
            self._con.execute(
                "SELECT column_name, data_type FROM information_schema.columns WHERE table_catalog = ? AND table_schema = 'main' AND table_name = ?",
                [self._alias, table],
            ).fetchall()
        )
        incoming = self._staging_columns(staging)
        null_fields = {f.name for f in pq.read_schema(staging) if pa.types.is_null(f.type)}
        promotions = []
        # Validate ALL shared columns before altering any of them.
        for name, dtype in incoming:
            if name in existing_types and name not in null_fields:
                target_type = compatible_type(existing_types[name], dtype)
                if target_type != existing_types[name]:
                    promotions.append((name, target_type))
        for name, dtype in promotions:
            self._con.execute(
                f"ALTER TABLE {qualified(self._alias, table)} ALTER COLUMN {quote_identifier(name)} SET TYPE {dtype}"
            )
        missing = [(n, t) for n, t in incoming if n not in known]
        for name, dtype in missing:
            self._con.execute(
                f"ALTER TABLE {qualified(self._alias, table)} ADD COLUMN {quote_identifier(name)} {dtype}"
            )
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

        self.connect()
        if not self.in_transaction:
            with self.transaction():
                return self.ingest(table, lazyframe, partition_by=partition_by)
        start = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="omnisus-staging-") as tmp:
            staging = Path(tmp) / "data.parquet"
            lazyframe.sink_parquet(staging, row_group_size=1_000_000, compression="zstd")
            result = self.ingest_parquet(table, staging, partition_by=partition_by)
        result.duration_seconds = time.monotonic() - start
        return result

    def ingest_parquet(
        self, table: str, staging, *, partition_by: tuple[str, ...] = ()
    ) -> ImportResult:
        """Append an existing validated staging file without rewriting it."""
        import time
        from pathlib import Path

        from omnisus_db.sources._base import ImportResult

        self.connect()
        staging = Path(staging)
        if not self.in_transaction:
            with self.transaction():
                return self.ingest_parquet(table, staging, partition_by=partition_by)
        start = time.monotonic()
        self._ensure_table(table, str(staging), partition_by)
        inserted = self._con.execute(
            f"INSERT INTO {qualified(self._alias, table)} BY NAME SELECT * FROM read_parquet({quote_literal(str(staging))})"
        ).fetchone()
        result = ImportResult(
            rows=0 if inserted is None else int(inserted[0]),
            bytes_written=staging.stat().st_size,
            duration_seconds=time.monotonic() - start,
        )
        self._pending_results.append(result)
        return result

    def publish_scope(self, table: str, staging, **kwargs) -> ImportResult | None:
        """Publish a validated source scope with an explicit replay policy."""
        from omnisus_db.lake.publication import publish_scope

        return publish_scope(self, table, staging, **kwargs)

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
            self._writer_lock.close()
            self._closed = True
            self._columns.clear()
            self._ensured.clear()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

"""Transactional source publications; ordinary Lake.ingest remains append."""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from omnisus_db.lake.sql import qualified, quote_identifier, quote_literal
from omnisus_db.sources._base import ScopeKey

if TYPE_CHECKING:
    from omnisus_db.lake import Lake
    from omnisus_db.lake.session import Session
    from omnisus_db.sources._base import ImportResult

ImportPolicy = Literal["append", "skip_same", "error_if_exists", "replace"]
POLICIES = ("append", "skip_same", "error_if_exists", "replace")
MANIFEST = "_omnisus_publications"


def validate_policy(policy: str) -> None:
    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {POLICIES}")


@dataclass(frozen=True)
class DeletionResult:
    """What :func:`delete_scope` removed: data rows, and the manifest rows retired with them."""

    rows_deleted: int
    publications_retired: int


def _validate_scope(scope: ScopeKey) -> None:
    if (
        (scope.uf is not None and not re.fullmatch("[A-Z]{2}", scope.uf))
        or not 1900 <= scope.ano <= 2200
        or (scope.mes is not None and not 1 <= scope.mes <= 12)
        or (scope.uf is None and scope.mes is not None)
    ):
        raise ValueError("invalid source scope")


def _ensure_manifest(lake: "Lake") -> str:
    manifest = qualified(lake.alias, MANIFEST)
    lake.connect().execute(f"""CREATE TABLE IF NOT EXISTS {manifest} (
        publication_id VARCHAR, dataset VARCHAR, scope_json VARCHAR,
        source_sha256 VARCHAR, parser_version VARCHAR, run_id VARCHAR,
        batch_id VARCHAR, published_at VARCHAR, rows BIGINT,
        active BOOLEAN, managed BOOLEAN, source_uri VARCHAR
    )""")
    # Use live schema here: Lake's column cache is for data-table ingestion,
    # and an ALTER within a multi-scope transaction must be visible immediately.
    columns = {
        row[0] for row in lake.connect().execute(f"DESCRIBE SELECT * FROM {manifest}").fetchall()
    }
    if "source_uri" not in columns:
        lake.connect().execute(f"ALTER TABLE {manifest} ADD COLUMN source_uri VARCHAR")
    return manifest


def publications(session: "Session", *, run_id: str | None = None) -> list[dict]:
    if MANIFEST not in session.tables():
        return []
    sql = f"SELECT * FROM {qualified(session.alias, MANIFEST)}"
    args = []
    if run_id is not None:
        sql += " WHERE run_id = ?"
        args.append(run_id)
    rows = (
        session.connect()
        .execute(sql + " ORDER BY published_at, publication_id", args)
        .to_arrow_table()
        .to_pylist()
    )
    for row in rows:
        dimensions = json.loads(row["scope_json"])
        row["scope"] = scope_from_fields(dimensions) if isinstance(dimensions, dict) else None
    return rows


def scope_fields(scope: ScopeKey) -> dict[str, object]:
    """The columns that identify ``scope``'s rows: the manifest's scope_json shape."""
    fields: dict[str, object] = (
        {"_source_ano": scope.ano} if scope.uf is None else {"ano": scope.ano, "uf": scope.uf}
    )
    if scope.mes is not None:
        fields["mes"] = scope.mes
    return fields


def scope_from_fields(fields: Mapping[str, object]) -> ScopeKey | None:
    """Inverse of :func:`scope_fields`; ``None`` for a shape this version never writes."""
    uf, mes = fields.get("uf"), fields.get("mes")
    national = fields.get("_source_ano")
    if set(fields) == {"_source_ano"} and isinstance(national, int):
        return ScopeKey(uf=None, ano=national)
    ano = fields.get("ano")
    if (
        set(fields) - {"mes"} == {"ano", "uf"}
        and isinstance(ano, int)
        and isinstance(uf, str)
        and (mes is None or isinstance(mes, int))
    ):
        return ScopeKey(uf=uf, ano=ano, mes=mes)
    return None


def _predicate(fields: Mapping[str, object]) -> tuple[str, list[object]]:
    sql = " AND ".join(f"{quote_identifier(k)} IS NOT DISTINCT FROM ?" for k in fields)
    return sql, list(fields.values())


def publish_scope(
    lake: "Lake",
    table: str,
    staging: Path,
    *,
    scope: ScopeKey,
    source_sha256: str,
    parser_version: str,
    policy: ImportPolicy = "append",
    run_id: str | None = None,
    batch_id: str | None = None,
    partition_by: tuple[str, ...] = (),
    source_uri: str | None = None,
) -> "ImportResult | None":
    validate_policy(policy)
    if not re.fullmatch("[0-9a-f]{64}", source_sha256) or not parser_version:
        raise ValueError("publication requires source SHA-256 and parser version")
    _validate_scope(scope)
    if table.startswith("_omnisus_"):
        raise ValueError("reserved publication table name")
    staging = Path(staging)
    run_id, batch_id = run_id or str(uuid4()), batch_id or str(uuid4())
    if not lake.in_transaction:
        with lake.transaction():
            return publish_scope(
                lake,
                table,
                staging,
                scope=scope,
                source_sha256=source_sha256,
                parser_version=parser_version,
                policy=policy,
                run_id=run_id,
                batch_id=batch_id,
                partition_by=partition_by,
                source_uri=source_uri,
            )
    con = lake.connect()
    fields = scope_fields(scope)
    columns = dict(lake._staging_columns(str(staging)))
    if not fields.keys() <= columns.keys():
        raise ValueError("staging is missing source scope columns")
    predicate, args = _predicate(fields)
    counts = con.execute(
        f"SELECT count(*), count(*) FILTER (WHERE {predicate}) FROM read_parquet({quote_literal(str(staging))})",
        args,
    ).fetchone()
    assert counts is not None
    total, matching = counts
    if total == 0 or matching != total:
        raise ValueError("empty or inconsistent source scope; previous data preserved")
    scope_json = json.dumps(fields, sort_keys=True, separators=(",", ":"))
    existing = 0
    if table in lake.tables():
        # Never let a wider national scope replace state publications or vice versa.
        national_table = "_source_ano" in lake._table_columns(table)
        if national_table != (scope.uf is None):
            raise ValueError("incompatible national/state publication scope")
        existing_row = con.execute(
            f"SELECT count(*) FROM {qualified(lake.alias, table)} WHERE {predicate}", args
        ).fetchone()
        assert existing_row is not None
        existing = existing_row[0]
    manifest = _ensure_manifest(lake)
    previous = con.execute(
        f"SELECT source_sha256, parser_version, rows, managed FROM {manifest} WHERE dataset=? AND scope_json=? AND active",
        [table, scope_json],
    ).fetchall()
    managed = sum(r[2] for r in previous) == existing and all(r[3] for r in previous)
    if policy != "append" and not managed:
        raise ValueError("legacy or unmanaged rows in scope; inventory/rebuild required")
    if existing and policy == "error_if_exists":
        raise ValueError("source scope already exists")
    if previous and policy == "skip_same":
        if all(r[0] == source_sha256 and r[1] == parser_version for r in previous):
            return None
        raise ValueError("different source/parser version exists; request replace explicitly")
    # Schema compatibility is checked before deleting. All mutations and the
    # durable publication ID then share the caller's managed transaction.
    lake._ensure_table(table, str(staging), partition_by)
    if policy == "replace":
        con.execute(f"DELETE FROM {qualified(lake.alias, table)} WHERE {predicate}", args)
        con.execute(
            f"UPDATE {manifest} SET active=false WHERE dataset=? AND scope_json=? AND active",
            [table, scope_json],
        )
    result = lake.ingest_parquet(table, staging, partition_by=partition_by)
    publication_id = str(uuid4())
    con.execute(
        f"INSERT INTO {manifest} (publication_id, dataset, scope_json, source_sha256, "
        "parser_version, run_id, batch_id, published_at, rows, active, managed, source_uri) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            publication_id,
            table,
            scope_json,
            source_sha256,
            parser_version,
            run_id,
            batch_id,
            datetime.now(UTC).isoformat(),
            result.rows,
            True,
            managed,
            source_uri,
        ],
    )
    result.run_id, result.batch_id, result.publication_id = run_id, batch_id, publication_id
    return result


def delete_scope(lake: "Lake", table: str, scope: ScopeKey) -> DeletionResult:
    """Delete one source scope and retire every publication within it, atomically.

    Rows are matched by the predicate :func:`publish_scope` uses, so a yearly
    scope on a monthly table removes all its months, and each month's manifest
    row is retired (``active = false``). Rows that never had a manifest are
    deleted as well; ``rows_deleted`` above the retired publications' row sum
    is the caller's signal that unmanaged rows were present. Runs inside the
    caller's managed transaction when one is active, else opens one.
    """
    _validate_scope(scope)
    if table.startswith("_omnisus_"):
        raise ValueError("reserved publication table name")
    if not lake.in_transaction:
        with lake.transaction():
            return delete_scope(lake, table, scope)
    if table not in lake.tables():
        raise ValueError(f"unknown table: {table!r}")
    national_table = "_source_ano" in lake._table_columns(table)
    if national_table != (scope.uf is None):
        raise ValueError("incompatible national/state publication scope")
    con = lake.connect()
    fields = scope_fields(scope)
    predicate, args = _predicate(fields)
    data = qualified(lake.alias, table)
    counted = con.execute(f"SELECT count(*) FROM {data} WHERE {predicate}", args).fetchone()
    assert counted is not None
    con.execute(f"DELETE FROM {data} WHERE {predicate}", args)
    retired = 0
    if MANIFEST in lake.tables():
        manifest = qualified(lake.alias, MANIFEST)
        active = con.execute(
            f"SELECT publication_id, scope_json FROM {manifest} WHERE dataset = ? AND active",
            [table],
        ).fetchall()
        within = [
            publication_id
            for publication_id, scope_json in active
            if _contains(json.loads(scope_json), fields)
        ]
        for publication_id in within:
            con.execute(
                f"UPDATE {manifest} SET active = false WHERE publication_id = ?", [publication_id]
            )
        retired = len(within)
    return DeletionResult(rows_deleted=int(counted[0]), publications_retired=retired)


def _contains(dimensions: object, fields: Mapping[str, object]) -> bool:
    """Whether a manifest row's scope lies within the requested fields."""
    return isinstance(dimensions, dict) and all(dimensions.get(k) == v for k, v in fields.items())


def record_failed_attempts(lake: "Lake", report) -> None:
    """Persist determined failures after data batches have rolled back."""
    if not report.failed:
        return
    table = qualified(lake.alias, "_omnisus_attempts")
    with lake.transaction():
        lake.connect().execute(f"""CREATE TABLE IF NOT EXISTS {table} (
            run_id VARCHAR, input_index BIGINT, scope VARCHAR, status VARCHAR,
            reason VARCHAR, recorded_at VARCHAR
        )""")
        rows = [
            (
                report.run_id,
                index,
                str(outcome.scope),
                outcome.status,
                outcome.reason,
                datetime.now(UTC).isoformat(),
            )
            for index, outcome in enumerate(report.outcomes)
            if outcome.status == "failed"
        ]
        lake.connect().executemany(f"INSERT INTO {table} VALUES (?, ?, ?, ?, ?, ?)", rows)


def attempts(session: "Session", *, run_id: str | None = None) -> list[dict]:
    if "_omnisus_attempts" not in session.tables():
        return []
    sql = f"SELECT * FROM {qualified(session.alias, '_omnisus_attempts')}"
    params = []
    if run_id is not None:
        sql += " WHERE run_id=?"
        params.append(run_id)
    return (
        session.connect()
        .execute(sql + " ORDER BY recorded_at, input_index", params)
        .to_arrow_table()
        .to_pylist()
    )

# Scoped Removal and Publication Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the lake a scoped delete that keeps data rows and the publication manifest coherent, and make `publications()` rows carry a decoded `ScopeKey` so callers reconcile without decoding the manifest's private encoding.

**Architecture:** Everything lives in `src/omnisus_db/lake/publication.py`, next to `publish_scope`, which already owns the scope encoding, the row predicate and the manifest. The scope-field builder, its predicate and the scope validation are extracted into helpers shared by `publish_scope` and the new `delete_scope`; a decoder is the inverse of the builder. `Lake` gets a thin `delete_scope` wrapper like `publish_scope`; `Session.publications()` (shared with `LakeReader`) adds the decoded key.

**Tech Stack:** Python 3.12, DuckDB 1.5.5 + DuckLake, Polars, pytest (`uv run pytest`), ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-09-11-scope-deletion-and-reconciliation-design.md`

## Global Constraints

- Python floor `>=3.12`; ruff `line-length = 99`; `uv run mypy src` must stay clean.
- CI gate: `uv run pytest -m "not e2e and not perf" --cov=omnisus_db --cov-fail-under=85`; `uv run ruff check .`; `uv run ruff format --check .`.
- Public-API changes need a `CHANGELOG.md` entry under `## Unreleased`.
- No adoption of legacy rows, no CLI command, no new manifest column (spec, "Decisions").
- Every commit message ends with the line `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Pre-commit hooks run ruff, ruff format and mypy on commit; a failing hook aborts the commit — fix and retry, never `--no-verify`.

---

### Task 1: Shared scope helpers and the decoded `scope` on publications

**Files:**
- Modify: `src/omnisus_db/lake/publication.py` (imports; new helpers above `publish_scope`; `publications()`; the `fields`/`predicate` lines inside `publish_scope`)
- Test: `tests/unit/lake/test_publication.py`

**Interfaces:**
- Consumes: `ScopeKey(uf: str | None, ano: int, mes: int | None = None)` from `omnisus_db.sources._base`; `Session.publications()` in `src/omnisus_db/lake/session.py` delegating to `publication.publications(session, run_id=...)`.
- Produces (used by Task 2):
  - `scope_fields(scope: ScopeKey) -> dict[str, object]` — `{"_source_ano": ano}` for a national scope, else `{"ano": ano, "uf": uf}` plus `"mes"` when set.
  - `_predicate(fields: Mapping[str, object]) -> tuple[str, list[object]]` — `"ano" IS NOT DISTINCT FROM ? AND ...` and its arguments.
  - `scope_from_fields(fields: Mapping[str, object]) -> ScopeKey | None`.
  - `publications()` rows carry `row["scope"]: ScopeKey | None`.

- [ ] **Step 1: Write the failing tests**

Add a national publishing helper next to `_publish` and two tests at the end of `tests/unit/lake/test_publication.py`:

```python
def _publish_national(lake, tmp_path, ano=2023, value=1):
    path = tmp_path / f"BR-{ano}.parquet"
    pl.DataFrame({"_source_ano": [ano], "v": [value]}).write_parquet(path)
    return lake.publish_scope(
        "n",
        path,
        scope=ScopeKey(uf=None, ano=ano),
        source_sha256=hashlib.sha256(f"BR{ano}".encode()).hexdigest(),
        parser_version="parser-v1",
        run_id="national",
        partition_by=("_source_ano",),
    )


def test_publications_carry_a_decoded_scope(tmp_path):
    """The app decoded scope_json itself, including our private _source_ano
    encoding. The package now hands back the ScopeKey it wrote."""
    with Lake.local(f"ducklake:{tmp_path}/s.ducklake") as lake:
        _publish(lake, tmp_path)
        _publish_national(lake, tmp_path)
        scopes = {r["dataset"]: r["scope"] for r in lake.publications()}
        assert scopes == {
            "t": ScopeKey(uf="SP", ano=2024, mes=1),
            "n": ScopeKey(uf=None, ano=2023),
        }


def test_scope_from_fields_rejects_shapes_this_version_never_writes():
    from omnisus_db.lake.publication import scope_from_fields

    assert scope_from_fields({"ano": 2024, "uf": "SP"}) == ScopeKey(uf="SP", ano=2024)
    assert scope_from_fields({"_source_ano": 2023}) == ScopeKey(uf=None, ano=2023)
    assert scope_from_fields({"product": "estimate", "ano": 2024}) is None
    assert scope_from_fields({"ano": "2024", "uf": "SP"}) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/lake/test_publication.py -q -k "decoded_scope or scope_from_fields"`
Expected: FAIL — `KeyError: 'scope'` in the first, `ImportError: cannot import name 'scope_from_fields'` in the second.

- [ ] **Step 3: Add the helpers and the decoded key**

In `src/omnisus_db/lake/publication.py`, add `from collections.abc import Mapping` to the stdlib import block (ruff's isort places it first, before `import json`); the existing `from typing import TYPE_CHECKING, Literal` stays as is. Insert above `def publish_scope(`:

```python
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
    if set(fields) - {"mes"} == {"ano", "uf"} and isinstance(ano, int) and isinstance(uf, str):
        if mes is None or isinstance(mes, int):
            return ScopeKey(uf=uf, ano=ano, mes=mes)
    return None


def _predicate(fields: Mapping[str, object]) -> tuple[str, list[object]]:
    sql = " AND ".join(f"{quote_identifier(k)} IS NOT DISTINCT FROM ?" for k in fields)
    return sql, list(fields.values())
```

Inside `publish_scope`, replace

```python
    fields = {"_source_ano": scope.ano} if scope.uf is None else {"ano": scope.ano, "uf": scope.uf}
    if scope.mes is not None:
        fields["mes"] = scope.mes
    columns = dict(lake._staging_columns(str(staging)))
    if not fields.keys() <= columns.keys():
        raise ValueError("staging is missing source scope columns")
    predicate = " AND ".join(f"{quote_identifier(k)} IS NOT DISTINCT FROM ?" for k in fields)
    args = list(fields.values())
```

with

```python
    fields = scope_fields(scope)
    columns = dict(lake._staging_columns(str(staging)))
    if not fields.keys() <= columns.keys():
        raise ValueError("staging is missing source scope columns")
    predicate, args = _predicate(fields)
```

Replace the body of `publications` so every row carries the decoded key:

```python
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
```

- [ ] **Step 4: Run the lake tests to verify they pass**

Run: `uv run pytest tests/unit/lake -q`
Expected: all pass (the two new tests plus every existing publication/reader/transaction test — `publish_scope` behaviour is unchanged by the extraction).

- [ ] **Step 5: Lint, type-check, commit**

Run: `uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src`
Expected: clean. Then:

```bash
git add src/omnisus_db/lake/publication.py tests/unit/lake/test_publication.py
git commit -m "Carry a decoded ScopeKey on every publication row

The Omnisus app decoded scope_json itself, including a bridge over the
private _source_ano encoding of national scopes. The encoder lives in
publication.py; scope_from_fields is its inverse and publications() now
hands back the ScopeKey it wrote. scope_fields and the row predicate are
extracted so the coming delete_scope shares one definition with
publish_scope.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: `delete_scope` and `DeletionResult`

**Files:**
- Modify: `src/omnisus_db/lake/publication.py` (new dataclass; `_validate_scope` extracted from `publish_scope`; new `delete_scope`)
- Modify: `src/omnisus_db/lake/operations.py` (`Lake.delete_scope` wrapper after `publish_scope`; `TYPE_CHECKING` import)
- Modify: `src/omnisus_db/__init__.py` (import and `__all__`)
- Test: `tests/unit/lake/test_publication.py`, `tests/unit/test_public_api.py`

**Interfaces:**
- Consumes (Task 1): `scope_fields`, `_predicate`; existing `Lake.in_transaction`, `Lake.transaction()`, `Lake.tables()`, `Lake._table_columns(table) -> set[str]`, `Lake.alias`, `Lake.connect()`, `MANIFEST`, `qualified(alias, name)`.
- Produces (used by Tasks 3 and 4):
  - `DeletionResult(rows_deleted: int, publications_retired: int)` — frozen dataclass, exported as `omnisus_db.DeletionResult`.
  - `Lake.delete_scope(table: str, scope: ScopeKey) -> DeletionResult`.

- [ ] **Step 1: Write the failing tests**

Change the `_publish` helper's signature so a month can be chosen (default unchanged):

```python
def _publish(
    lake, tmp_path, uf="SP", value=1, policy="append", digest=None, run_id="run-1", mes=1
):
    path = tmp_path / f"{uf}-{value}-{mes}.parquet"
    pl.DataFrame({"ano": [2024], "mes": [mes], "uf": [uf], "v": [value]}).write_parquet(path)
    return lake.publish_scope(
        "t",
        path,
        scope=ScopeKey(uf=uf, ano=2024, mes=mes),
        source_sha256=digest or hashlib.sha256(str(value).encode()).hexdigest(),
        parser_version="parser-v1",
        policy=policy,
        run_id=run_id,
        partition_by=("ano", "mes"),
    )
```

(`test_parser_version_change_is_not_skip_same` references `tmp_path / "SP-1.parquet"`; update it to `tmp_path / "SP-1-1.parquet"`.)

Append these tests:

```python
def test_delete_scope_removes_every_month_and_retires_their_publications(tmp_path):
    """A yearly scope on a monthly table covers all its months; the neighbouring
    UF and its publication are untouched."""
    from omnisus_db import DeletionResult

    with Lake.local(f"ducklake:{tmp_path}/d.ducklake") as lake:
        _publish(lake, tmp_path)
        _publish(lake, tmp_path, value=2, mes=2)
        _publish(lake, tmp_path, uf="RJ", value=3)

        result = lake.delete_scope("t", ScopeKey(uf="SP", ano=2024))

        assert result == DeletionResult(rows_deleted=2, publications_retired=2)
        assert lake.connect().execute("SELECT uf, v FROM lake.t").fetchall() == [("RJ", 3)]
        assert {r["scope"]: r["active"] for r in lake.publications()} == {
            ScopeKey(uf="SP", ano=2024, mes=1): False,
            ScopeKey(uf="SP", ano=2024, mes=2): False,
            ScopeKey(uf="RJ", ano=2024, mes=1): True,
        }


def test_delete_scope_deletes_unmanaged_rows_without_retirements(tmp_path):
    from omnisus_db import DeletionResult

    with Lake.local(f"ducklake:{tmp_path}/d.ducklake") as lake:
        lake.ingest("t", pl.DataFrame({"ano": [2024], "mes": [1], "uf": ["SP"], "v": [9]}).lazy())

        result = lake.delete_scope("t", ScopeKey(uf="SP", ano=2024, mes=1))

        assert result == DeletionResult(rows_deleted=1, publications_retired=0)
        assert lake.connect().execute("SELECT count(*) FROM lake.t").fetchone() == (0,)


def test_delete_scope_rejects_unknown_table_and_wrong_geography(tmp_path):
    with Lake.local(f"ducklake:{tmp_path}/d.ducklake") as lake:
        _publish(lake, tmp_path)
        with pytest.raises(ValueError, match="unknown table"):
            lake.delete_scope("nope", ScopeKey(uf="SP", ano=2024))
        with pytest.raises(ValueError, match="national/state"):
            lake.delete_scope("t", ScopeKey(uf=None, ano=2024))
        with pytest.raises(ValueError, match="reserved"):
            lake.delete_scope("_omnisus_publications", ScopeKey(uf="SP", ano=2024))
        assert lake.connect().execute("SELECT count(*) FROM lake.t").fetchone() == (1,)


def test_delete_scope_rolls_back_with_the_callers_transaction(tmp_path):
    with Lake.local(f"ducklake:{tmp_path}/d.ducklake") as lake:
        _publish(lake, tmp_path)
        with pytest.raises(RuntimeError), lake.transaction():
            lake.delete_scope("t", ScopeKey(uf="SP", ano=2024, mes=1))
            raise RuntimeError("abort")
        assert lake.connect().execute("SELECT v FROM lake.t").fetchall() == [(1,)]
        assert [r["active"] for r in lake.publications()] == [True]


def test_delete_scope_on_a_national_table(tmp_path):
    from omnisus_db import DeletionResult

    with Lake.local(f"ducklake:{tmp_path}/d.ducklake") as lake:
        _publish_national(lake, tmp_path, ano=2023)
        _publish_national(lake, tmp_path, ano=2024, value=2)

        result = lake.delete_scope("n", ScopeKey(uf=None, ano=2023))

        assert result == DeletionResult(rows_deleted=1, publications_retired=1)
        assert lake.connect().execute("SELECT _source_ano FROM lake.n").fetchall() == [(2024,)]


def _publish_yearly(lake, tmp_path, uf="SP", value=1):
    path = tmp_path / f"y-{uf}-{value}.parquet"
    pl.DataFrame({"ano": [2023], "uf": [uf], "v": [value]}).write_parquet(path)
    return lake.publish_scope(
        "y",
        path,
        scope=ScopeKey(uf=uf, ano=2023),
        source_sha256=hashlib.sha256(f"y{uf}{value}".encode()).hexdigest(),
        parser_version="parser-v1",
        run_id="yearly",
        partition_by=("ano", "uf"),
    )


def test_delete_scope_on_a_yearly_table(tmp_path):
    from omnisus_db import DeletionResult

    with Lake.local(f"ducklake:{tmp_path}/d.ducklake") as lake:
        _publish_yearly(lake, tmp_path)
        _publish_yearly(lake, tmp_path, uf="RJ", value=2)

        result = lake.delete_scope("y", ScopeKey(uf="SP", ano=2023))

        assert result == DeletionResult(rows_deleted=1, publications_retired=1)
        assert lake.connect().execute("SELECT uf FROM lake.y").fetchall() == [("RJ",)]
        assert {r["scope"]: r["active"] for r in lake.publications(run_id="yearly")} == {
            ScopeKey(uf="SP", ano=2023): False,
            ScopeKey(uf="RJ", ano=2023): True,
        }
```

And in `tests/unit/test_public_api.py`, after `test_lake_reader_is_exported`:

```python
def test_deletion_result_is_exported() -> None:
    from omnisus_db.lake.publication import DeletionResult

    assert "DeletionResult" in odb.__all__
    assert odb.DeletionResult is DeletionResult
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/lake/test_publication.py tests/unit/test_public_api.py -q -k "delete_scope or deletion_result"`
Expected: FAIL — `ImportError: cannot import name 'DeletionResult'` / `AttributeError: 'Lake' object has no attribute 'delete_scope'`.

- [ ] **Step 3: Implement the dataclass, the validation helper and `delete_scope`**

In `src/omnisus_db/lake/publication.py`, add `from dataclasses import dataclass` to the imports. Below `validate_policy`, add:

```python
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
```

In `publish_scope`, replace the inline `if ( (scope.uf is not None and not re.fullmatch(...)) ... raise ValueError("invalid source scope")` block with `_validate_scope(scope)`.

After `publish_scope` (before `record_failed_attempts`), add:

```python
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
```

In `src/omnisus_db/lake/operations.py`, add `from omnisus_db.lake.publication import DeletionResult` inside the `if TYPE_CHECKING:` block (below the `polars` import, sorted), and after the `publish_scope` method add:

```python
    def delete_scope(self, table: str, scope: ScopeKey) -> DeletionResult:
        """Delete one source scope and retire its publications in one transaction."""
        from omnisus_db.lake.publication import delete_scope

        return delete_scope(self, table, scope)
```

`ScopeKey` must be importable in `operations.py` for the annotation: add `from omnisus_db.sources._base import ImportResult, ScopeKey` to the existing `TYPE_CHECKING` import of `ImportResult` (the module already has `from __future__ import annotations`).

In `src/omnisus_db/__init__.py`, change `from omnisus_db.lake.publication import ImportPolicy` to `from omnisus_db.lake.publication import DeletionResult, ImportPolicy`, and add `"DeletionResult",` to `__all__` right after `"Dataset",`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/lake tests/unit/test_public_api.py -q`
Expected: all pass.

- [ ] **Step 5: Lint, type-check, commit**

Run: `uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src`
Expected: clean (if ruff's `RUF022` complains about `__all__` order, move `"DeletionResult"` to where it asks). Then:

```bash
git add src/omnisus_db/lake/publication.py src/omnisus_db/lake/operations.py src/omnisus_db/__init__.py tests/unit/lake/test_publication.py tests/unit/test_public_api.py
git commit -m "Add Lake.delete_scope, removal coherent with the publication manifest

The Omnisus app answered 501 on scoped deletion because the package had
no removal that kept data and manifest in agreement. delete_scope deletes
rows by the predicate publish_scope uses and retires, in the same managed
transaction, every active manifest row within the scope — a yearly scope
on a monthly table covers all its months. Unmanaged rows are deleted too;
the DeletionResult counts show the caller when they were present.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: PostgreSQL integration case

**Files:**
- Modify: `tests/integration/test_postgres_lake.py` (imports; end of `test_cloud_managed_publication`)

**Interfaces:**
- Consumes: `Lake.delete_scope`, `DeletionResult` (Task 2); `LakeReader(target)`, `publications()` rows with `"scope"` (Task 1).

- [ ] **Step 1: Extend the test**

Change the import line to `from omnisus_db import DeletionResult, Lake, LakeReader, ScopeKey`. At the end of `test_cloud_managed_publication`, after the pinned-reader block, append:

```python
    # Removal keeps data and manifest coherent, and a reader observes both sides.
    with Lake.cloud(catalog=catalog, storage=storage) as lake:
        deletion = lake.delete_scope("synthetic", ScopeKey(uf="SP", ano=2024))
        assert deletion == DeletionResult(rows_deleted=2, publications_retired=1)
    with LakeReader(target) as reader:
        assert reader.connect().execute("SELECT count(*) FROM lake.synthetic").fetchone() == (0,)
        (record,) = reader.publications(run_id="selector-gate")
        assert record["active"] is False
        assert record["scope"] == ScopeKey(uf="SP", ano=2024)
```

- [ ] **Step 2: Run it against a disposable PostgreSQL**

Docker must be running and the `postgres:17` image present locally. Run this as one shell script (macOS has no `timeout`; the loop polls readiness with `docker exec`):

```bash
set -e
docker run --rm -d --name odb-pg-gate -e POSTGRES_HOST_AUTH_METHOD=trust -p 127.0.0.1:54329:5432 postgres:17 >/dev/null
trap 'docker rm -f odb-pg-gate >/dev/null 2>&1 || true' EXIT
for i in $(seq 1 120); do docker exec odb-pg-gate pg_isready -h 127.0.0.1 -U postgres -q 2>/dev/null && break; done
OMNISUS_TEST_POSTGRES_URL="postgresql://postgres@127.0.0.1:54329/postgres" uv run pytest tests/integration/test_postgres_lake.py -q --tb=short
```

Expected: `2 passed`. Without the environment variable the two cases are skipped; that is the CI behaviour and is acceptable, but this step must be run at least once with the container.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_postgres_lake.py
git commit -m "Cover scoped deletion on a PostgreSQL catalog

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: Declared limitations, documentation and CHANGELOG

**Files:**
- Modify: `src/omnisus_db/__init__.py` (docstrings of `import_ibge_pop` and `import_cnes_master`)
- Modify: `docs/api.md` (Results and The lake sections)
- Modify: `docs/guides/reprocessing-and-maintenance.md` (three sections)
- Modify: `CHANGELOG.md` (`## Unreleased` → `### Added` and `### Changed`)

**Interfaces:**
- Consumes: names from Tasks 1–2 exactly as written: `Lake.delete_scope`, `DeletionResult`, `publications()` rows' `scope`.

- [ ] **Step 1: Declare the limitations in the docstrings**

In `src/omnisus_db/__init__.py`, append to the docstring of `import_ibge_pop` (after "...canonical data and source manifest."):

```
    Accepts neither ``run_id`` nor ``policy`` and never appears in
    ``Lake.publications()``: each edition is its own publication, identified by
    the returned ``publication_id`` in ``ibge_population_manifest``. Reconcile
    an interrupted run through that manifest, not by run ID.
```

Append to the docstring of `import_cnes_master` (after "...(e.g. from the backend admin UI)."):

```
    This is an idempotent upsert, not a publication: it accepts neither
    ``run_id`` nor ``policy``, records no manifest row and returns only a
    count. To reconcile an interrupted run, run it again — ``only_missing``
    fetches only what is still absent.
```

- [ ] **Step 2: Document the API**

In `docs/api.md`, under `## Results`, after the line `::: omnisus_db.sources._base.ScopeKey` add:

```
::: omnisus_db.DeletionResult
```

Under `## The lake`, replace the paragraph starting "`Lake.publications(run_id=...)` reads the durable source-publication manifest;" with:

```
`Lake.publications(run_id=...)` reads the durable source-publication manifest;
each row carries `scope`, the `ScopeKey` the package wrote (`None` for a shape
this version does not write), alongside the raw `scope_json`.
`Lake.attempts(run_id=...)` reads separately recorded known failures.
`Lake.ingest_parquet` appends a staging file directly. `Lake.publish_scope` adds
scope validation, source identity and replay policy to that write.
`Lake.delete_scope(table, scope)` removes one source scope and retires every
publication within it in the same transaction; a yearly scope on a monthly
table covers all its months. `import_ibge_pop` and `import_cnes_master` do not
take part in this manifest — see their docstrings for how each reconciles.
```

- [ ] **Step 3: Update the reprocessing guide**

In `docs/guides/reprocessing-and-maintenance.md`, replace the Python block under "## Inspect an interrupted run" (the one opening `with odb.Lake.local(odb.DEFAULT_TARGET) as lake:`) with:

```python
with odb.LakeReader(odb.DEFAULT_TARGET) as reader:
    published = {p["scope"] for p in reader.publications(run_id="sim-rr-2023-review-01")}
    failed_attempts = reader.attempts(run_id="sim-rr-2023-review-01")
```

and change the sentence that follows, "Publications include publication, run and batch IDs, source scope/hash, parser version, row count and active status." to "Publications include publication, run and batch IDs, the decoded `scope`, source hash, parser version, row count and active status. A scope absent from `published` did not commit under that run ID, because data and manifest commit in one transaction; choose run IDs you never reuse, or that inference is void."

Insert before "## Coordinate writers and bound downloads":

```
## Remove a scope

`Lake.delete_scope(table, scope)` deletes the rows of one source scope and
retires every publication within it (`active = false`) in one managed
transaction, so data and manifest never disagree. A yearly scope on a monthly
table removes all twelve months and retires each month's publication. Rows that
never had a publication are removed as well; when `rows_deleted` exceeds the
retired publications' row sum, unmanaged rows were present.

```python
with odb.Lake.local(odb.DEFAULT_TARGET) as lake:
    result = lake.delete_scope("sih_rd", odb.ScopeKey(uf="RR", ano=2023))
    print(result.rows_deleted, result.publications_retired)
```

Retired publications stay in the manifest for inspection; they are not
distinguished from ones superseded by `replace`.

## Migrate a legacy lake

Rows written before publications existed have no manifest and are never
certified in place. Migrate by rebuilding, so provenance exists from the first
import:

1. Choose a new target. Do not point it at the old catalog or storage.
2. Import each dataset with `available()` as the plan and an explicit `run_id`;
   `policy="skip_same"` makes reruns idempotent.
3. Verify `publications()` covers every scope you expect, and compare row counts
   with the old lake where that matters to you.
4. Switch consumers to the new target string. Keep the old lake read-only
   until nothing reads it, then delete it.

The old lake is not modified at any step.
```

- [ ] **Step 4: CHANGELOG**

In `CHANGELOG.md`, under `### Added` after the `LakeReader` entry, add:

```
- **`Lake.delete_scope(table, scope)` — removal coherent with the manifest.**
  Deletes one source scope by the predicate `publish_scope` uses and retires
  every publication within it in the same transaction; a yearly scope on a
  monthly table covers all its months. Returns a `DeletionResult` with the
  rows deleted and publications retired, so unmanaged rows are visible when
  the two disagree. The Omnisus app answered 501 on scoped deletion for lack
  of exactly this.
```

Under `### Changed`, after the `Session` entry, add:

```
- `publications()` rows carry `scope`, the `ScopeKey` the package wrote
  (`None` for a shape this version does not write). Consumers were decoding
  `scope_json` themselves, including the private `_source_ano` encoding of
  national scopes.
- `import_ibge_pop` and `import_cnes_master` now state that they take neither
  `run_id` nor `policy` and do not appear in `Lake.publications()`; each names
  its own reconciliation key. Legacy lakes migrate by rebuild, never by
  in-place adoption — see the reprocessing guide.
```

- [ ] **Step 5: Run the full gate and commit**

Run:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src && git diff --check && uv run python scripts/gen_datasets_doc.py --check && uv run pytest -m "not e2e and not perf" --cov=omnisus_db --cov-fail-under=85 -q
```

Expected: everything clean; coverage ≥ 85%. Then:

```bash
git add src/omnisus_db/__init__.py docs/api.md docs/guides/reprocessing-and-maintenance.md CHANGELOG.md
git commit -m "Document scoped removal, decoded scopes and the rebuild migration

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

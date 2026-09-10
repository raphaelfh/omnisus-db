# API reference

The public import, discovery and lake interfaces below are rendered from the
current checkout. Their availability and return types differ from the historical
`v0.1.0` tag; follow the [installation guide](guides/getting-started.md).

## Discovery

Ask the server what exists before deciding what to import.

::: omnisus_db.available
::: omnisus_db.browse
::: omnisus_db.FtpEntry

## Planning

Planning is composition: build a list of scopes any way you like and hand it
to `import_dataset`. There is no planner flag on the Python API.

::: omnisus_db.scopes_for
::: omnisus_db.ALL_UFS

## Importing

The FTP importers return `ImportReport`; inspect `report.failed`, `report.skipped`
and `report.ok`. `import_ibge_pop` returns `list[ImportResult]`, while
`import_cnes_master` returns the number of records written.

`ImportAbortedError` interrupts an FTP run when it cannot safely continue.
Inspect its `report` for determined outcomes and `unresolved` for
`(input_index, ScopeKey)` pairs before retrying. Imports append data unless an
importer explicitly implements replacement, as CNES master does.

::: omnisus_db.import_dataset
::: omnisus_db.import_sim
::: omnisus_db.import_sinasc
::: omnisus_db.import_sih
::: omnisus_db.import_cnes_st
::: omnisus_db.import_ibge_pop
::: omnisus_db.import_cnes_master

## Results

`ImportResult.bytes_written` measures the temporary staging Parquet file, not
final lake storage growth. `snapshot_id=None` can mean an uncommitted result or
an unavailable snapshot ID; it does not alone establish whether a write committed.

::: omnisus_db.sources._base.ImportReport
::: omnisus_db.sources._base.ScopeOutcome
::: omnisus_db.sources._base.ImportResult
::: omnisus_db.sources._base.ScopeKey

## The lake

Use a target URI such as `ducklake:./omnisus.ducklake` with `Lake.local`.
Use one writer per lake and `Lake.transaction()` for managed writes; raw SQL
transaction control is outside this contract. Managed transactions cannot nest.

```python
import omnisus_db as odb
import polars as pl

with odb.Lake.local(odb.DEFAULT_TARGET) as lake:
    with lake.transaction() as receipt:
        result = lake.ingest("example", pl.DataFrame({"id": [1]}).lazy())
        assert result.snapshot_id is None
    assert receipt.committed
    print(receipt.snapshot_id, result.rows)
```

The receipt's `snapshot_id` may remain `None` after a successful commit when no new snapshot was created or the lookup was unavailable.
See [Architecture](architecture.md) for rollback and recovery boundaries.

::: omnisus_db.Lake
::: omnisus_db.DEFAULT_TARGET

## Registry

::: omnisus_db.Dataset
::: omnisus_db.resolve

## Errors

Lake transaction errors are imported from `omnisus_db.lake`. A
`CommitOutcomeUnknown` means the COMMIT raised and the handle is unusable;
inspect the catalog before retrying. The FTP runner wraps transaction state
failures in the top-level `ImportAbortedError` with partial progress.

::: omnisus_db.ImportAbortedError
::: omnisus_db.lake.TransactionStateError
::: omnisus_db.lake.CommitOutcomeUnknown
::: omnisus_db.FtpPathNotFound
::: omnisus_db.FtpUnavailable

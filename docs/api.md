# API reference

The public import, discovery and lake interfaces below are rendered from the
current checkout. Their availability and return types differ from the historical
`v0.1.0` tag; follow the [installation guide](guides/getting-started.md).

## Discovery

Ask the server what exists before deciding what to import.

::: omnisus_db.available
::: omnisus_db.available_releases
::: omnisus_db.browse
::: omnisus_db.FtpEntry

## Releases

Some datasets publish final and preliminary files under the same names in two
directories (a row's `prelim_dir`). `available_releases` reports which
directory each scope came from; `outdated` compares that against what a lake
has published and returns the scopes whose release moved, to be re-imported
with `import_dataset(..., policy="replace")`. See
[reprocessing and maintenance](guides/reprocessing-and-maintenance.md).

::: omnisus_db.outdated

## Planning

Planning is composition: build a list of scopes any way you like and hand it
to `import_dataset`. There is no planner flag on the Python API.

::: omnisus_db.scopes_for
::: omnisus_db.ALL_UFS

## Importing

The FTP importers return `ImportReport`; inspect `report.failed`, `report.skipped`
and `report.ok`. `import_ibge_populacao` returns `list[ImportResult]`, while
`import_cnes_master` returns the number of records written.

`import_research` is the researcher door: it requires `run_id` and defaults to
`policy="skip_same"`. It refuses `append`. `import_dataset` remains the operator
API and still appends unless a policy is set.

`ImportAbortedError` interrupts an FTP run when it cannot safely continue.
Inspect its `report` for determined outcomes and `unresolved` for
`(input_index, ScopeKey)` pairs before retrying. Imports append data unless an
explicit replay `policy` is selected. FTP imports accept `append` (default),
`skip_same`, `error_if_exists` and `replace`. See
[reprocessing and maintenance](guides/reprocessing-and-maintenance.md) for legacy
scope restrictions, run IDs and byte budgets.

::: omnisus_db.import_dataset
::: omnisus_db.import_research
::: omnisus_db.import_cnes_estabelecimentos
::: omnisus_db.import_ibge_populacao
::: omnisus_db.import_cnes_master

## Results

`ImportResult.bytes_written` measures the temporary staging Parquet file, not
final lake storage growth. `snapshot_id=None` can mean an uncommitted result or
an unavailable snapshot ID; it does not alone establish whether a write committed.
Managed FTP results also carry `run_id`, `batch_id` and `publication_id`; IBGE
results carry their canonical `publication_id`.

::: omnisus_db.sources._base.ImportReport
::: omnisus_db.sources._base.ScopeOutcome
::: omnisus_db.sources._base.ImportResult
::: omnisus_db.sources._base.ScopeKey
::: omnisus_db.DeletionResult

## The lake

Use a target URI such as `ducklake:./omnisus.ducklake` with `Lake.local`.
Local handles enforce a cooperative writer lock for their lifetime.
Use `Lake.transaction()` for managed writes; raw SQL
transaction control is outside this contract. Managed transactions cannot nest.

To read, open a `LakeReader` on the same target: it attaches the catalog
read-only, takes no lock, creates nothing and sets no option, so it runs
alongside an import. Pass `snapshot_id` to pin the session; without it every
statement reads the latest committed snapshot.

```python
import omnisus_db as odb

with odb.LakeReader(odb.DEFAULT_TARGET) as reader:
    latest = reader.snapshots()[-1]["snapshot_id"]
    rows = reader.connect().execute("SELECT count(*) FROM lake.sim_obitos").fetchone()

with odb.LakeReader(odb.DEFAULT_TARGET, snapshot_id=latest) as reader:
    ...  # every statement here sees exactly that snapshot
```

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

`Lake.publications(run_id=...)` reads the durable source-publication manifest;
each row carries `scope`, the `ScopeKey` the package wrote (`None` for a shape
this version does not write), alongside the raw `scope_json`.
`Lake.attempts(run_id=...)` reads separately recorded known failures.
`Lake.ingest_parquet` appends a staging file directly. `Lake.publish_scope` adds
scope validation, source identity and replay policy to that write.
`Lake.delete_scope(table, scope)` removes one source scope and retires every
publication within it in the same transaction; a yearly scope on a monthly
table covers all its months. `import_ibge_populacao` and `import_cnes_master` do not
take part in this manifest — see their docstrings for how each reconciles.

`Lake.optimize(table)` merges adjacent files. `Lake.expire_snapshots` and
`Lake.cleanup_files` take `older_than` as a timezone-aware datetime and default
to `dry_run=True`. Each returns a list of result dictionaries. `Lake.vacuum` is
a deprecated physical cleanup alias; it does not expire snapshots.

::: omnisus_db.Lake
::: omnisus_db.LakeReader
::: omnisus_db.DEFAULT_TARGET

## Research citations and joins

`import_research` is above. `cite` reads the publication manifest (or
`ibge_population_manifest`) and returns Portuguese text matching the
[reproducibility guide](pesquisa/reprodutibilidade.md). `latest_snapshot_id`
is the newest catalog snapshot. Municipality helpers take the leftmost 6 or 7
digits; they do not pad and they do not rewrite stored columns.

::: omnisus_db.Citation
::: omnisus_db.cite
::: omnisus_db.citation_from_publications
::: omnisus_db.latest_snapshot_id
::: omnisus_db.municipality_join_key
::: omnisus_db.municipality_join_key_sql

## Registry

`datasets()` lists every curated FTP dataset; `products()` adds the two
importer families outside the registry (`ibge_populacao`, `cnes_master`) and states,
per family, the scope fields, accepted policies, how an interrupted run is
reconciled and whether `available()` applies. Year rules for IBGE remain in
`omnisus_db.sources.ibge.products` (`CENSUS_YEARS`, `ESTIMATE_UNAVAILABLE_YEARS`);
an estimate is importable only as its latest edition, so there is no floor year.

::: omnisus_db.Dataset
::: omnisus_db.resolve
::: omnisus_db.datasets
::: omnisus_db.products
::: omnisus_db.Product

## Errors

Lake transaction errors are imported from `omnisus_db.lake`. A
`CommitOutcomeUnknown` means the COMMIT raised and the handle is unusable;
inspect the catalog before retrying. The FTP runner wraps transaction state
failures in the top-level `ImportAbortedError` with partial progress.
`CatalogAttachError` means the catalog could not be opened at all: `.stage`
says which statement failed, and for a remote catalog the message never
carries the connection string.

::: omnisus_db.ImportAbortedError
::: omnisus_db.CatalogAttachError
::: omnisus_db.lake.TransactionStateError
::: omnisus_db.lake.CommitOutcomeUnknown
::: omnisus_db.FtpPathNotFound
::: omnisus_db.FtpUnavailable

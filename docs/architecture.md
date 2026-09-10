# Architecture

The current implementation combines a DATASUS FTP registry, source-specific
importers, and a shared DuckLake writer. Historical design rationale lives in
`docs/superpowers/specs/2026-09-09-repo-structure-design.md` and
`docs/superpowers/specs/2026-09-09-transactional-ingestion-design.md` in the
repository; these working documents are not published to this site.

## Registry and importers

- **`Dataset`** is an immutable, keyword-only DATASUS FTP registry row. It holds
  identity, FTP location, cadence, partitioning, coverage and a dictionary path.
  The registry includes SIM-DO, SINASC-NV, SIH-RD, SIA/APAC and CNES-ST. Callers
  can also construct a `Dataset` with their own dictionary.
- **Importers** orchestrate fetching, parsing and writing. IBGE population and
  CNES master data use dedicated HTTP importers; they are not FTP registry rows.
  CNES-ST's named importer additionally refreshes the `aux_cnes` view.

## DATASUS data flow

```text
bounded concurrent FTP fetches -> one parse/write consumer
  -> datasus_dbc.decompress_bytes -> complete DBF bytes
  -> dbfread2 records -> Polars batches -> concatenated DataFrame
  -> LazyFrame -> temporary zstd Parquet
  -> managed transaction: create/widen table + INSERT BY NAME -> COMMIT
```

The parser checks DBF payload length and parsed record counts against the DBF
header. It builds frames in batches of 100,000 records, but retains all frames
for a scope before concatenating them. This is not a constant-memory pipeline:
DBC and DBF payloads and parsed scope data must fit in memory. Fetch concurrency
and the bounded queue limit how many fetched payloads await the consumer.

New columns widen the lake table; columns absent from an incoming scope become
NULL through `INSERT BY NAME`. `Lake.ingest` appends rows, so importing an already
committed scope again can duplicate data. It does not replace a partition or
provide deduplication.

## Transaction boundaries and recovery

`Lake.ingest` opens a managed transaction when called directly and returns after
commit. Inside `with lake.transaction() as receipt:`, multiple ingests share the
transaction. Their `ImportResult.snapshot_id` values stay `None` until the
context commits. The receipt then records `committed=True` and, when available,
the committed snapshot ID. A successful commit can still have no snapshot ID
if the transaction made no snapshot change or the follow-up lookup failed.

The FTP runner defaults to six concurrent fetches and batches of 24 consumed
scopes per transaction. Set `batch_size=1` on `import_dataset` for per-scope
transactions. Fetch failures are reported independently. An ordinary parse or
write failure rolls back the current batch, marks its attempted writes failed,
and allows later scopes to continue. Previously committed batches remain.
Results preserve input order, including repeated scope values; batching follows
fetch completion order.

A transaction state failure stops the runner with `ImportAbortedError`.
`error.report` contains determined outcomes; `error.unresolved` contains
`(input_index, ScopeKey)` pairs requiring inspection. A failed COMMIT raises
`CommitOutcomeUnknown` in the lake API and invalidates the handle. Inspect the
catalog before retrying unresolved writes: a raised COMMIT does not prove that
nothing was committed.

Use one writer per lake for this managed ingestion workflow. Managed transactions
cannot nest, and the FTP runner rejects an already active transaction. Raw SQL
`BEGIN`/`COMMIT` through `Lake.connect()` is outside this contract. SQLite and
Postgres catalog targets are accepted; the presence of a Postgres target does
not establish concurrent-writer recovery guarantees for these importers.

IBGE population commits each year through `Lake.ingest` and returns a list of
`ImportResult`; it does not use the FTP report/recovery loop. CNES master data is
fetched and validated before its table upsert and `aux_cnes` refresh commit in
one transaction, and the importer returns a row count. The CNES-ST wrapper
refreshes its view after the FTP import, in a separate operation. Auxiliary
bootstrap tables are replaced individually unless the caller supplies an outer
managed transaction.

## Runtime and layout

Python 3.12 or newer is required. The DuckDB connection factory installs and
loads the `ducklake` extension when opening a lake; an environment without the
extension cached needs access to the extension repository. Dependency versions
are declared in `pyproject.toml`.

```text
src/omnisus_db/
| lake/         - catalog targets, connections, managed transactions, writes
| sources/      - per-family fetch and parse
| | datasus_ftp/ - registry, inventory, bounded import runner
| | ibge/       - population HTTP importer
| | cnes/       - CNES-specific importers
| transforms/   - Polars helpers and Frictionless dictionary loader
| data/         - YAML schemas and auxiliares-bootstrap.zip
| cli/          - Typer entry point
```

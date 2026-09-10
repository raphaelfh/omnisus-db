# Knowing what exists

DATASUS publishes different date ranges for different datasets and states, and
the ranges move. Guessing produces two failure modes: asking for files that were
never published, and silently missing files that were.

Two functions answer the question, at two levels of interpretation.

## `available` — what can I import?

Closed-world. Reads one directory listing and decodes each filename through the
registry, so you get back exactly the scopes this package can import.

```python
import omnisus_db as odb

odb.available("sim_do")                      # matching scopes in the cached/fresh listing
odb.available("sim_do", years=range(2020, 2025))
```

Names belonging to other datasets in the same directory are skipped, not raised
on — `SIASUS/200801_/Dados` holds seven of our eleven datasets side by side.

## `browse` — what is actually there?

Open-world. No decoding, so it reaches families this package does not model at
all (SINAN, CIHA, PCE), and any path you like.

```python
odb.browse("/dissemin/publicos/SINAN", depth=2)
```

Recursion is bounded by `depth`, and the walk is sequential. A subdirectory that
cannot be listed is logged and skipped rather than truncating the walk.

## From the command line

```bash
omnisus-db inventory sim_do
omnisus-db inventory --path /dissemin/publicos/SINAN --depth 2
```

## Building the lake from what exists

The point of all this. `--plan inventory` asks the server first and imports only
what it lists:

```bash
omnisus-db import sim --plan inventory --years 1996-2024 --ufs RR,AC
```

In Python the same thing is composition — no flag, just a different function
filling `scopes`:

```python
odb.import_dataset("sim_do", scopes=odb.available("sim_do", years=range(1996, 2025)))
```

The alternative is to plan blindly and let tolerance absorb the gaps:

```python
odb.import_dataset(
    "sim_do", scopes=odb.scopes_for("sim_do", years=range(2020, 2025), ufs=["RR"])
)
```

Both work. Inventory planning costs one directory listing and avoids opening a
connection per nonexistent file; blind planning costs nothing up front and
reports the gaps as `skipped`.

## Caching

Listings are cached for 24 hours under `OMNISUS_CACHE_DIR` (or the XDG cache
directory). The cache is never authoritative: a miss, a stale entry or an
unreadable file all fall through to the network, and a cache that cannot be
written never discards a listing that already succeeded.

`--plan inventory` always refreshes. A 23-hour-old listing would silently omit a
month DATASUS published this morning, and the run is about to use the network
anyway. Pass `--refresh` to force it for browsing too.

## Reading the report

A normally completed DATASUS-FTP import returns an `ImportReport`.
`import_ibge_pop` instead returns `list[ImportResult]`, and `import_cnes_master`
returns an integer count:

```python
report = odb.import_dataset("sim_do", scopes=odb.available("sim_do"))

report.rows          # rows ingested
report.ok            # scopes imported
report.skipped       # outside declared coverage or missing upstream
report.failed        # download, parsing or write failures; inspect each reason
```

Inspect `report.failed`; never the report's truthiness. `omnisus-db import`
exits 1 for a completed FTP report with failures or for `ImportAbortedError`.
Skipped scopes alone do not fail the run. Invalid arguments and other exceptions
can also produce a non-zero exit status.

## Transactions and interrupted imports

Use one writer per lake. Serialize write handles, processes and external SQL
clients that target the same catalog. This release does not provide a
cross-process writer lock or distributed retry coordination.

A completed import returns one outcome for every requested input position.
Repeated input scopes remain repeated append operations. `ok` means committed;
`failed` means an unsuccessful scope; `skipped` means a documented absence.

If transaction initialization, commit acknowledgement or rollback fails, or a
producer stops unexpectedly, the FTP runner raises
`ImportAbortedError`. Its `report` contains determined outcomes and its
`unresolved` contains `(input_index, scope)` pairs that need inspection or were
not processed. Do not retry the whole import automatically: an unacknowledged
commit may already have written data.

```python
import omnisus_db as odb

try:
    report = odb.import_dataset(
        "sim_do", scopes=[odb.ScopeKey(uf="RR", ano=2023)]
    )
except odb.ImportAbortedError as exc:
    print(exc.report.rows, exc.unresolved)
    raise
```

For lower-level writes, use `Lake.transaction()`. An `ImportResult` created
inside that context has `snapshot_id=None` until commit. Direct `Lake.ingest`
commits before returning. If snapshot metadata cannot be read after a successful
commit, the write remains successful and its snapshot stays `None`.

Managed transactions cannot be nested. The FTP runner also rejects an existing
managed transaction before starting producers. Cancellation rolls back the active
batch and preserves prior commits; control-flow interruptions propagate, including
when they first occur during cleanup.

Do not combine managed transactions with raw SQL `BEGIN` or `COMMIT` on
`Lake.connect()`. After a transaction-state failure, close the handle and inspect
the catalog before starting a new write.

CNES Master refresh validates records before changing stored values and commits
the table update and view refresh together. Repeated explicit CNES codes are
fetched once; progress counts unique codes.

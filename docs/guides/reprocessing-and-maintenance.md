# Reprocessing and maintenance

## Choose a replay policy

FTP imports retain `append` as their default. Choose another policy explicitly
when a scope has already been published through the managed importer:

| Policy | Existing managed scope | Absent scope |
|---|---|---|
| `append` | Append another publication; duplicates remain possible | Publish |
| `skip_same` | Skip only when all active publications have the same source SHA-256 and parser version; otherwise fail | Publish |
| `error_if_exists` | Fail without changing data | Publish |
| `replace` | Validate staging, delete the exact source scope, insert and replace its active manifest in one transaction | Publish |

```python
import omnisus_db as odb

report = odb.import_dataset(
    "sim_do",
    scopes=[odb.ScopeKey(uf="RR", ano=2023)],
    policy="skip_same",
    run_id="sim-rr-2023-review-01",
)
print(report.run_id, report.rows, report.failed)
```

```bash
omnisus-db import sim --year 2023 --ufs RR --policy skip_same --run-id sim-rr-2023-review-01
```

Source identity combines the compressed DBC SHA-256 with an explicit staging
parser version and the dictionary file's SHA-256. A parser algorithm change must
bump that version. `skip_same` still fetches and validates the source to establish
this identity. It does not remove duplicates already created by `append`.
`replace` requires nonempty staging with every row belonging to the exact scope.
For monthly data this includes UF, year and month, even when the physical table
partition omits UF. Event rows are never deduplicated with `DISTINCT`.

Rows created by older importers or direct SQL have no trustworthy source
manifest. Policies other than `append` reject such scopes. Inventory or rebuild
them explicitly in a separate target before switching; a later append cannot
retroactively certify the old rows. Manifest row counts detect some external
changes but do not audit arbitrary edits that preserve counts. External SQL
writes remain outside the managed contract. IBGE has a separate publication
model described in its [source documentation](../sources/ibge_pop.md).

## Inspect an interrupted run

Choose and retain `run_id` before starting an import. A failed COMMIT can have
succeeded in the catalog despite the missing acknowledgement. After closing the
unusable handle, reopen the lake and inspect the durable manifest:

```python
with odb.Lake.local(odb.DEFAULT_TARGET) as lake:
    publications = lake.publications(run_id="sim-rr-2023-review-01")
    failed_attempts = lake.attempts(run_id="sim-rr-2023-review-01")
```

Publications include publication, run and batch IDs, source scope/hash, parser
version, row count and active status. Superseded manifests remain for inspection.
The failure table records known failures separately after data rollback at the
end of a completed run; a crash or unknown transaction outcome can prevent that
log from being written. Its absence is not evidence of success.

`ImportAbortedError.report` contains determined outcomes and `unresolved` lists
input positions needing inspection. Repeated input positions are preserved.
A skip that depends on an uncommitted publication shares that batch's outcome;
it cannot remain successful after rollback. Reconcile publications before
retrying an unknown commit, rather than appending the entire run again.

## Coordinate writers and bound downloads

A local `Lake` handle acquires a cooperative lock on the canonical catalog path
before opening DuckDB and holds it until close. Concurrent handles fail with
`WriterBusyError` from `omnisus_db.lake.locking`. The sidecar `.writer.lock` file
remains after close; its presence alone does not mean a writer is active. Do not
delete it while handles may be running. This protocol also covers maintenance.
External SQL clients, network filesystems and cloud catalogs require external
coordination; distributed recovery has not been validated.

`import_dataset` and `import_cnes_st` accept `max_payload_bytes` (default 512 MiB)
and `max_inflight_bytes` (default 1 GiB). CLI equivalents are
`--max-payload-bytes` and `--max-inflight-bytes`, in bytes. The total must cover
at least one per-file reservation. Space is reserved before downloading and
held while the payload is queued and consumed. The default allows two reserved
payloads even with the default six fetch workers. A file exceeding the cap fails
during receipt. Cancellation closes sockets and waits for the worker before
releasing the reservation; a DNS/connect phase without a socket can still take
until its timeout.

These limits cover compressed payloads, not total process memory. Decompression
still materializes the whole DBF. Parsing spools bounded batches to temporary
disk and writes reconciled Parquet in a second pass. Provide enough temporary
disk for DBF, Arrow spool and Parquet.

The reproducible benchmark is `scripts/benchmark_resources.py`. On the measured
132,440-row amplified fixture with 100,000-row batches, peak RSS changed from
1328.5 to 758.0 MiB, elapsed time from 3.705 to 6.571 seconds, and sampled peak
temporary disk from 61.9 to 112.5 MiB. Row order/hash and schema matched. This is
one run per mode on repeated fixture records; it does not establish national
throughput or a universal memory bound. Disk sampling every 5 ms is a lower bound.
The amplified case feeds repeated DBF records directly and bypasses DBC
decompression; its elapsed times do not measure the complete DBC pipeline. A
separate 3,311-row real DBC case exercises decompression in the same benchmark.
The repository's `reports/benchmark-d6-default.json` records the environment,
corpus hashes and full results.

## Compact, expire history and clean files

These are separate operations:

1. `lake.optimize(table)` merges adjacent files while retaining snapshots.
2. `lake.expire_snapshots(older_than=cutoff)` simulates removing older history.
3. `lake.cleanup_files(older_than=cutoff)` simulates deletion of obsolete files
   eligible under DuckLake's retention rules. It does not expire snapshots.

```python
from datetime import UTC, datetime

cutoff = datetime(2026, 8, 1, tzinfo=UTC)
with odb.Lake.local(odb.DEFAULT_TARGET) as lake:
    compacted = lake.optimize("sim_do")
    history_preview = lake.expire_snapshots(older_than=cutoff)
    files_preview = lake.cleanup_files(older_than=cutoff)
```

The new expiration and cleanup APIs default to `dry_run=True`. Pass
`dry_run=False` to execute after selecting a retention cutoff suitable for the
history you need. Cutoffs must include a timezone. Returned dictionaries expose
DuckLake's operation results.

```bash
omnisus-db lake optimize sim_do
omnisus-db lake expire-snapshots --before 2026-08-01T00:00:00+00:00 --dry-run
omnisus-db lake cleanup-files --before 2026-08-01T00:00:00+00:00 --dry-run
```

Use `--execute` instead of `--dry-run` to apply expiration or cleanup. Failures
exit nonzero. The legacy `vacuum(older_than="30 days")` wrapper is deprecated:
it converts the interval to a timestamp and executes physical cleanup. It does
not expire snapshots and does not default to simulation.

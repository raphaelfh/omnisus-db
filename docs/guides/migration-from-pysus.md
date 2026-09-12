# Migration from PySUS

The examples below use the current repository version; install it as described
in [Getting Started](getting-started.md). Older tags can expose different APIs.

## Import SIM

```python
import omnisus_db as odb

report = odb.import_sim(years=[2023], ufs=["SP"])
print(report.rows, report.failed)
```

The FTP import functions return `ImportReport`, rather than a downloaded file
handle or a list of results. Access successful `ImportResult` values through
`outcome.result` in `report.ok`. Use `available()` and `import_dataset()` when
the list of published scopes should drive the import.

## Read into a DataFrame

```python
with odb.Lake.local(odb.DEFAULT_TARGET) as lake:
    df = lake.connect().sql(
        "SELECT * FROM lake.sim_obitos WHERE ano=2023 AND uf='SP'"
    ).pl()
```

The target includes the `ducklake:` prefix, and the context closes the connection
after the query is materialized.

## Operational differences

- Data is appended to tables managed by a DuckLake catalog; repeated imports of
  the same scope are not deduplicated by default. Managed source publications
  support explicit replay policies; legacy scopes require inventory or rebuild.
- Local handles acquire a cooperative writer lock. External SQL and cloud
  writers require external coordination. Downloads may be concurrent,
  while parsing and writing use one consumer and one connection.
- Managed transactions group schema and data changes and provide committed
  snapshots. `ImportAbortedError` carries determined results and unresolved input
  positions; inspect the catalog before retrying an unknown commit.
- YAML dictionaries and auxiliary tables support normalization and joins; their
  presence does not imply every incoming record has been validated by Frictionless.

See [import results and transactions](inventory.md) for failure handling and
[cloud targets](getting-started.md#cloud-target) for target configuration limits.

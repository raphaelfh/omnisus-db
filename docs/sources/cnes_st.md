# cnes_st

CNES establishment data uses the DATASUS-FTP pipeline. The generated
[registry catalog](../datasets.md) defines its cadence, coverage and partitions.
`import_cnes_st()` returns `ImportReport` and refreshes `aux_cnes` after the load.

```python
import omnisus_db as odb

report = odb.import_cnes_st(years=[2023], ufs=["RR"], months=[1])
print(report.rows, report.failed)
```

## Establishment names

Names are fetched separately by `import_cnes_master()` from the public CNES API.
Its return value is the number of useful records fetched, not `ImportReport`.

```python
updated = odb.import_cnes_master()  # missing codes discovered from cnes_st
```

The master refresh validates records before mutation and commits table creation,
row replacement and view refresh together. Repeated explicit codes are fetched
once. Individual HTTP failures and responses without a useful name are omitted;
the integer count does not identify which codes failed, and their old rows remain.
`only_missing=True` filters codes discovered from the lake when `codes=None`;
explicit codes request those records even when already present.

CNES-ST ingestion is append-only. `aux_cnes` currently uses per-field `arg_max`
aggregation; it does not promise that every returned field comes from the same
latest record. Temporal-view changes are a separate planned delivery.

Fields and decoding metadata are in
`src/omnisus_db/data/dicionarios/cnes_st.yaml`. See
[the transaction contract](../guides/inventory.md#transactions-and-interrupted-imports)
for the one-writer requirement and failure handling.

# cnes_estabelecimentos

CNES establishment data uses the DATASUS-FTP pipeline. The generated
[registry catalog](../datasets.md) defines its cadence, coverage and partitions.
`import_cnes_estabelecimentos()` returns `ImportReport` and refreshes `aux_cnes` after the load.

```python
import omnisus_db as odb

report = odb.import_cnes_estabelecimentos(years=[2023], ufs=["RR"], months=[1])
print(report.rows, report.failed)
```

## Establishment names

Names are fetched separately by `import_cnes_master()` from the public CNES API.
Its return value is the number of useful records fetched, not `ImportReport`.

```python
updated = odb.import_cnes_master()  # missing codes discovered from cnes_estabelecimentos
```

The master refresh validates records before mutation and commits table creation,
row replacement and view refresh together. Repeated explicit codes are fetched
once. Individual HTTP failures and responses without a useful name are omitted;
the integer count does not identify which codes failed, and their old rows remain.
`only_missing=True` filters codes discovered from the lake when `codes=None`;
explicit codes request those records even when already present.

CNES-ST ingestion appends by default and accepts the explicit replay policies
described in [reprocessing](../guides/reprocessing-and-maintenance.md). Replacement
always matches UF, year and month, even though UF is not a physical partition.

`aux_cnes` selects all CNES-ST attributes from the complete row at the latest
`ano`/`mes` for each CNES code. NULLs in that row stay NULL; an older value is not
carried forward. Identical latest rows collapse in the view; conflicting latest
rows cause an error until the source scope is reconciled. The underlying table
retains its history. The separately collected master name is current enrichment
and does not establish a historical name for the selected competence.

The wrapper refreshes the view after the FTP load in a separate operation.
A conflicting tie can therefore fail view refresh after source batches committed;
inspect the data and publication manifest before retrying.

Fields and decoding metadata are in
`src/omnisus_db/data/dicionarios/cnes_estabelecimentos.yaml`. See
[the transaction contract](../guides/inventory.md#transactions-and-interrupted-imports)
for the one-writer requirement and failure handling.

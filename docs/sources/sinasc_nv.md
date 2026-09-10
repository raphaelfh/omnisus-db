# sinasc_nv

SINASC — Live births. This dataset uses the shared DATASUS-FTP ingestion pipeline.
See the generated [registry catalog](../datasets.md) for its aliases, cadence,
coverage, partitions and FTP directory.

```bash
omnisus-db inventory sinasc_nv --refresh
omnisus-db import sinasc_nv --plan inventory --years 2020-2024 --ufs RR
```

Imports append to `lake.sinasc_nv`. Completion returns `ImportReport`; interrupted
transaction state is exposed through `ImportAbortedError`. See
[results and transactions](../guides/inventory.md#transactions-and-interrupted-imports).

The field definitions, foreign-key metadata and decoding rules live in
`src/omnisus_db/data/dicionarios/sinasc_nv.yaml`. The parser applies the dictionary
and preserves unlisted fields; physical table columns can therefore exceed the
dictionary. Dictionary validation alone does not certify all incoming records.

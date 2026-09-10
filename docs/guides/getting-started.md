# Getting Started

Install the current checkout, initialize a lake, import a listed scope and query it.
These pages describe the repository version; the historical `v0.1.0` tag predates
`ImportReport`, inventory and the transactional fixes.

## 1. Install

Python 3.12 or newer is required. Python 3.12 and 3.13 are tested.
From the repository root:

```bash
python -m pip install .
```

For development and documentation, use the committed dependency lock:

```bash
uv sync --locked --all-extras
```

## 2. Initialize a lake

```bash
omnisus-db init
```

This creates `./omnisus.ducklake/` (Parquet storage) and `./omnisus-catalog.sqlite`
(DuckLake catalog) and seeds auxiliary tables (UF, municipios, CID-10).

## 3. Import some data

```bash
omnisus-db inventory sim --refresh
omnisus-db import sim --plan inventory --year 2023 --ufs RR
```

If the listing has no matching scope, choose one it actually lists. Imports
append data: repeating a scope inserts it again. Use one writer per lake.
See [inventory and import results](inventory.md) for skipped scopes, failures
and interrupted imports.

## 4. Query

After the scope has imported successfully:

```bash
omnisus-db query "SELECT count(*) FROM lake.sim_do WHERE ano=2023 AND uf='RR'"
```

Or in Python:

```python
import omnisus_db as odb

with odb.Lake.local(odb.DEFAULT_TARGET) as lake:
    df = lake.connect().sql(
        "SELECT count(*) AS obitos FROM lake.sim_do WHERE ano=2023 AND uf='RR'"
    ).pl()
```

Every explicit lake target must start with `ducklake:`, for example
`ducklake:./omnisus.ducklake`. Keep the `Lake` context open while using its
connection or lazy relations.

## 5. Bigger imports

```bash
omnisus-db import sim --plan inventory --years 2020-2024 --ufs SP,RJ,MG
omnisus-db import sinasc --plan inventory --years 2020-2024
```

A completed FTP import reports every requested position. The CLI exits 1 for
failed scopes or interrupted imports. Inspect an unknown commit before retrying;
see [the transaction contract](inventory.md#transactions-and-interrupted-imports).
The separate [IBGE population importer](../sources/ibge_pop.md) has an unresolved
source-selection limitation and a different return type.

## Cloud target

Commands that operate on a lake accept `--target/-t`; inventory does not use a
lake. PostgreSQL catalog targets use this form:

```bash
omnisus-db import sim --year 2023 --ufs RR \
  --target "ducklake:postgresql://user:pwd@host/db?storage=s3://bucket/lake"
```

The DuckDB connection needs the appropriate catalog and object-storage
credentials. The current target parser extracts `storage` and drops other
PostgreSQL query parameters; do not rely on such parameters being forwarded.
The D1 acceptance tests validate local catalogs, not concurrent cloud writers.

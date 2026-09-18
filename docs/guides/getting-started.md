# Getting Started

Install the current checkout, initialize a lake, import a listed scope and query it.
These pages describe the repository version; the historical `v0.1.0` tag predates
`ImportReport`, inventory and the transactional fixes.

## 1. Install

Python 3.12 or newer is required. Python 3.12, 3.13 and 3.14 are tested.

```bash
python -m pip install omnisus-db
```

From the repository root, the same checkout:

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
omnisus-db inventory sim_obitos --refresh
omnisus-db import sim_obitos --plan inventory --year 2023 --ufs RR
```

If the listing has no matching scope, choose one it actually lists. Imports
append data by default: repeating a scope inserts it again. Use `--policy skip_same`
to skip a previously managed publication with the same source and parser version.
Local handles enforce a cooperative single-writer lock.
See [inventory and import results](inventory.md) for skipped scopes, failures
and interrupted imports.

## 4. Query

After the scope has imported successfully:

```bash
omnisus-db query "SELECT count(*) FROM lake.sim_obitos WHERE ano=2023 AND uf='RR'"
```

Or in Python:

```python
import omnisus_db as odb

report = odb.import_research(
    "sim_obitos",
    scopes=odb.available("sim_obitos", years=[2023], ufs=["RR"]),
    target=odb.DEFAULT_TARGET,
    run_id="sim-rr-2023-01",
)
with odb.LakeReader(odb.DEFAULT_TARGET) as reader:
    snapshot_id = odb.latest_snapshot_id(reader)
    citacao = odb.cite(reader, dataset="sim_obitos", snapshot_id=snapshot_id, run_id="sim-rr-2023-01")
    df = reader.connect().sql(
        "SELECT count(*) AS obitos FROM lake.sim_obitos WHERE ano=2023 AND uf='RR'"
    ).pl()
print(citacao.text)
```

`import_research` skips a scope that is already published with the same source
and parser (`skip_same`). Repeating `import_dataset` without a policy appends
again. Pin `snapshot_id` on a second `LakeReader` if another import may run
after you print the count. Every explicit lake target must start with
`ducklake:`, for example `ducklake:./omnisus.ducklake`. A `LakeReader` takes no
writer lock; open `Lake.local` only to write.

## 5. Bigger imports

```bash
omnisus-db import sim_obitos --plan inventory --years 2020-2024 --ufs SP,RJ,MG
omnisus-db import sinasc_nascidos_vivos --plan inventory --years 2020-2024
```

A completed FTP import reports every requested position. The CLI exits 1 for
failed scopes or interrupted imports. Inspect an unknown commit before retrying;
see [the transaction contract](inventory.md#transactions-and-interrupted-imports).
The separate [IBGE population importer](../sources/ibge_populacao.md) requires an explicit
product and edition and returns a list of results. For example:

```bash
omnisus-db import ibge_populacao --year 2022 --population-product census
```

Historical estimates without a verified territorial universe are unavailable.

## Cloud target

Commands that operate on a lake accept `--target/-t`; inventory does not use a
lake. PostgreSQL catalog targets use this form:

```bash
omnisus-db import sim_obitos --year 2023 --ufs RR \
  --target "ducklake:postgresql://user:pwd@host/db?storage=s3://bucket/lake"
```

The DuckDB connection needs the appropriate catalog and object-storage
credentials. The parser extracts exactly one `storage` parameter and preserves
other PostgreSQL query parameters, including `sslmode`. Percent-encode embedded
query characters in the storage value, or use `Lake.cloud(catalog=...,
storage=...)` in Python to pass the values separately. When the catalog cannot
be opened, `Lake.cloud`/`Lake.local` raise `CatalogAttachError`: `.stage` tells
whether the ducklake extension (`install`), the catalog (`attach`) or the
compression option (`set_option`) failed, and a remote catalog's error never
includes the connection string.
Acceptance tests validate local catalogs; cloud concurrency still requires
external writer coordination. See [reprocessing and maintenance](reprocessing-and-maintenance.md).

# omnisus-db

A Python library for ingesting Brazilian public health databases (DATASUS, IBGE, CNES)
into a [DuckLake](https://ducklake.select)-backed lakehouse.

## What it does

- **Fetches** DBC files from DATASUS FTP, JSON from IBGE SIDRA.
- **Decompresses** DBC -> DBF -> Polars, streaming records in 100k batches.
- **Persists** as Parquet under a DuckLake catalog (SQLite or Postgres).
- **Queries** via DuckDB with the `ducklake` extension.
- **Inventories** the FTP server, so an import can plan from what is really published.

## Install

```bash
pip install git+https://github.com/raphaelfh/omnisus-db@v0.1.0
```

## Hello, mortality

```python
import omnisus_db as odb

odb.import_sim(years=[2024], ufs=["SP"])
df = odb.Lake.local("./omnisus.ducklake").connect().sql(
    "SELECT count(*) AS obitos FROM lake.sim_do WHERE ano = 2024"
).pl()
print(df)
```

See [Getting Started](guides/getting-started.md).

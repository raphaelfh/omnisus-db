# omnisus-db

A Python library for ingesting Brazilian public health databases (DATASUS, IBGE, CNES)
into a [DuckLake](https://ducklake.select)-backed lakehouse.

## What it does

- **Fetches** DBC files from DATASUS FTP, JSON from IBGE SIDRA and the CNES API.
- **Decompresses** DBC to DBF and builds Polars frames in 100,000-record batches;
  the complete parsed scope is retained in memory.
- **Persists** data as Parquet under a DuckLake catalog (SQLite or Postgres),
  with managed transactions for ingestion.
- **Queries** via DuckDB with the `ducklake` extension.
- **Inventories** the FTP server, so an import can plan from what is published.

## Install

For field descriptions, code mappings, official evidence and review coverage,
see the [data dictionary design and source catalog](dicionario/index.md).
The proposed metadata API is documented separately from the current runtime.

These pages describe the current checkout. The historical `v0.1.0` tag predates
the discovery, reporting and managed transaction APIs documented here.
Python 3.12 or newer is required.

```bash
git clone https://github.com/raphaelfh/omnisus-db.git
cd omnisus-db
python -m pip install .
```

Opening a lake installs and loads the DuckDB `ducklake` extension. If it is not
cached, the environment needs access to DuckDB's extension repository.

## Hello, mortality

```python
import omnisus_db as odb

report = odb.import_dataset(
    "sim_obitos",
    scopes=odb.available("sim_obitos", years=[2024], ufs=["SP"]),
    target=odb.DEFAULT_TARGET,
)
print(f"Rows imported: {report.rows}; failed: {len(report.failed)}; skipped: {len(report.skipped)}")

if report.ok:
    with odb.Lake.local(odb.DEFAULT_TARGET) as lake:
        df = lake.connect().sql(
            "SELECT count(*) AS obitos FROM lake.sim_obitos WHERE ano = 2024"
        ).pl()
        print(df)
```

FTP imports report ordinary scope failures and missing files. Transaction state
failures raise `ImportAbortedError` with partial progress. Imports append rows;
retrying a committed scope can duplicate data. Use one writer per lake and see
[Getting Started](guides/getting-started.md) for report handling and recovery.

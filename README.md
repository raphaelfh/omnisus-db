# omnisus-db

Python library for ingesting Brazilian public health databases (DATASUS, IBGE, CNES)
into a DuckLake-backed lakehouse.

**Status:** Pre-1.0. API may change between minor versions.

## Install

```bash
# From the current checkout (Python >=3.12)
pip install .
```

## Quick start

```python
import omnisus_db as odb

# Import only what DATASUS actually publishes
odb.import_dataset("sim_do", scopes=odb.available("sim_do", years=range(2020, 2025)))

with odb.Lake.local(odb.DEFAULT_TARGET) as lake:
    df = lake.connect().sql(
        "SELECT count(*) AS obitos FROM lake.sim_do WHERE ano = 2024"
    ).pl()
```

Ask the server what exists before importing:

```python
odb.available("sim_do")                      # scopes you can import
odb.browse("/dissemin/publicos/SINAN")       # any FTP path, decoded or not
```

See [docs](https://raphaelfh.github.io/omnisus-db) for details.

## Interactive API notebook

For analysis using complete SIM/Roraima files (2022 and 2023), with a reusable local
lake, quality checks, filters, aggregations and transactions:

```bash
uv run --locked --extra notebooks marimo edit notebooks/api_dados_reais.py
```

For a complete real-data flow, open the [DATASUS inventory notebook](notebooks/inventario_dados_reais.py):
query the live file listing, select files by state/year, download into DuckLake,
inspect records, and export CSV/Parquet. See [execution instructions](notebooks/README.md).

```bash
uv run --locked --extra notebooks marimo edit notebooks/inventario_dados_reais.py
```

The [marimo walkthrough](notebooks/README.md) covers planning, synthetic ingestion,
SQL/Polars, transactions, rollback, results and optional real imports:

```bash
uv sync --locked --extra notebooks
uv run --locked --extra notebooks marimo edit notebooks/api_cenarios.py
```

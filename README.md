# omnisus-db

Python library for ingesting Brazilian public health databases (DATASUS, IBGE, CNES)
into a DuckLake-backed lakehouse.

**Status:** Pre-1.0. API may change between minor versions.

## Install

```bash
pip install git+https://github.com/raphaelfh/omnisus-db@v0.1.0
```

## Quick start

```python
import omnisus_db as odb

# Import only what DATASUS actually publishes
odb.import_dataset("sim_do", scopes=odb.available("sim_do", years=range(2020, 2025)))

df = odb.Lake.local("./omnisus.ducklake").connect().sql(
    "SELECT count(*) AS obitos FROM lake.sim_do WHERE ano = 2024"
).pl()
```

Ask the server what exists before importing:

```python
odb.available("sim_do")                      # scopes you can import
odb.browse("/dissemin/publicos/SINAN")       # any FTP path, decoded or not
```

See [docs](https://raphaelfh.github.io/omnisus-db) for details.

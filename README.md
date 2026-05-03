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
odb.import_sim(years=range(2020, 2025), ufs=["SP"])
odb.query("SELECT count(*) FROM sim_do WHERE ano = 2024").pl()
```

See [docs](https://raphaelfh.github.io/omnisus-db) for details.

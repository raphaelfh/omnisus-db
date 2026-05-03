# Migration from PySUS

If you currently use [PySUS](https://github.com/AlertaDengue/PySUS), here's
how to translate common patterns to omnisus-db.

## Download SIM

| PySUS | omnisus-db |
|-------|------------|
| `from pysus import SIM; SIM().download(['SP'], [2024])` | `odb.import_sim(years=[2024], ufs=['SP'])` |

## Read into DataFrame

| PySUS | omnisus-db |
|-------|------------|
| `df = parquet.to_dataframe()` | `odb.Lake.local('./omnisus.ducklake').connect().sql("SELECT * FROM lake.sim_do WHERE ano=2024 AND uf='SP'").pl()` |

## Why switch

- Single canonical Parquet dataset (vs. one file per scope on disk)
- Time-travel + ACID via DuckLake snapshots
- Cloud-native (S3/GCS) without code changes
- Pre-computed Frictionless schemas + auxiliary tables (UF, municipios, CID-10)

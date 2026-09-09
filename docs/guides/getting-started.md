# Getting Started

5-minute path: install + bootstrap + first import + first query.

## 1. Install

```bash
pip install git+https://github.com/raphaelfh/omnisus-db@v0.1.0
```

## 2. Initialize a lake

```bash
omnisus-db init
```

This creates `./omnisus.ducklake/` (Parquet storage) and `./omnisus-catalog.sqlite`
(DuckLake catalog) and seeds auxiliary tables (UF, municipios, CID-10).

## 3. Import some data

```bash
# Just one UF + one year for a quick test
omnisus-db import sim --year 2024 --ufs RR
```

## 4. Query

```bash
omnisus-db query "SELECT count(*) FROM lake.sim_do WHERE ano=2024 AND uf='RR'"
```

Or in Python:

```python
import omnisus_db as odb

con = odb.Lake.local("./omnisus.ducklake").connect()
df = con.sql("SELECT count(*) AS obitos FROM lake.sim_do WHERE ano=2024").pl()
```

## 5. Bigger imports

```bash
omnisus-db import sim --years 2020-2024 --ufs SP,RJ,MG
omnisus-db import sinasc --years 2023-2024
omnisus-db import ibge-pop --years 2010-2024
```

## Cloud target

Every command takes `--target/-t`; there is no environment variable for it.

```bash
omnisus-db import sim --year 2024 \
  --target "ducklake:postgresql://user:pwd@host/db?storage=s3://bucket/lake"
```

# omnisus-db

Python library for ingesting Brazilian public health databases (DATASUS, IBGE, CNES)
into a DuckLake-backed lakehouse.

**Status:** Pre-1.0. API may change between minor versions.

## Optional Rust DBF reader

DBF decoding defaults to `auto`: Rust when installed and supported, otherwise Python.
An optional native reader lives in
[`native/omnisus-db-dbf`](native/omnisus-db-dbf/README.md) and shares the same Arrow
staging and integrity checks. Install its locally built wheel to enable it automatically:

```bash
pip install --only-binary=:all: path/to/omnisus_db_dbf-<version>-<platform>.whl
```

Set `OMNISUS_DBF_BACKEND=rust` to require Rust or `OMNISUS_DBF_BACKEND=python`
to force dbfread2. The default `auto` falls back for an absent extension
or unsupported DBF metadata. Corrupt files and errors during parsing always fail.
No published native package version is required by the base installation.

## Install

```bash
# From the current checkout (Python >=3.12)
pip install .
```

## Quick start

```python
import omnisus_db as odb

# Import only what DATASUS actually publishes
odb.import_dataset("sim_obitos", scopes=odb.available("sim_obitos", years=range(2020, 2025)))

with odb.LakeReader(odb.DEFAULT_TARGET) as reader:
    df = reader.connect().sql(
        "SELECT count(*) AS obitos FROM lake.sim_obitos WHERE ano = 2024"
    ).pl()
```

Ask the server what exists before importing:

```python
odb.available("sim_obitos")                      # scopes you can import
odb.browse("/dissemin/publicos/SINAN")       # any FTP path, decoded or not
```

National Chagas and Hanseníase SINAN notifications are available as
`sinan_chagas` and `sinan_hanseniase`, both final and preliminary: DATASUS
publishes some datasets in two directories under the same filenames, and
`available_releases()`/`outdated()` tell you which release each scope is in
and which ones moved. Use `available()` and `policy="skip_same"` for
repeatable imports; filter record geography after acquisition. The
[Marimo walkthrough](notebooks/sinan_chagas.py) covers discovery, a saved plan,
publication, recovery and aggregate analysis.

The [medication walkthrough](notebooks/medicamentos.py) uses SIA-AM/APAC and a
separate bounded BNAFAR/Hórus stock query. Stock observations are partial and
are not dispensing events or managed lake publications. See the
[source contract](docs/sources/medicamentos.md) for access and coverage limits.

See [docs](https://raphaelfh.github.io/omnisus-db) for details.

## Notebooks: learning path

Start with the [notebook guide](notebooks/README.md):

| Order | Notebook | Purpose |
| --- | --- | --- |
| 1 | [DATASUS panorama](notebooks/panorama_datasus.py) | Real samples from all 18 portal categories; explore tables, fields and provenance |
| 2 | [Inventory and selection](notebooks/inventario_dados_reais.py) | Discover files and import a selected scope into DuckLake |
| 3 | [SIM analysis](notebooks/api_dados_reais.py) | Query complete SIM/Roraima files, check quality and create aggregates |
| 4 | [API scenarios](notebooks/api_cenarios.py) | Learn transactions, rollback and library behavior |

```bash
uv sync --locked --extra notebooks
uv run --locked --extra notebooks marimo edit notebooks/panorama_datasus.py
```

The panorama reuses the latest local archive and downloads a new one on request.
See the [data map and full column inventory](reports/2026-09-10-mapa-datasus/README.md).
One sample per portal category does not cover every subtype, year or state.

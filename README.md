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

See the [documentation site](https://raphaelfh.github.io/omnisus-db/) for guides,
the dataset catalogue and the API reference. To build it locally:

```bash
uv sync --locked --extra docs && uv run mkdocs serve
```

## Para pesquisadores

O [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/) mostra qual
base responde a cada pergunta, o que um registro representa e como citar o resultado.
Cada base tem um notebook com as mesmas seis etapas em
[`notebooks/bases/`](notebooks/bases/): SIM, SINASC, SIH, SIA, CNES, população IBGE,
SINAN (Chagas aguda e hanseníase) e medicamentos.

```bash
uv sync --locked --extra notebooks
uv run --locked --extra notebooks marimo edit notebooks/bases/sim_obitos.py
```

Abrir um notebook não baixa nada. Outros notebooks, para explorar o DATASUS e
para quem desenvolve a biblioteca, estão no [índice](notebooks/README.md).

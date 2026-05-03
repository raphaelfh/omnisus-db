# Architecture

For the full design rationale, see the
[design spec](https://github.com/raphaelfh/omnisus/blob/main/docs/superpowers/specs/2026-05-02-omnisus-db-design.md).

## Three core abstractions

- **`Source`** — a family (DATASUS-FTP, IBGE, CNES). Knows how to *discover* and *fetch bytes*.
- **`Dataset`** — an immutable product (SIM-DO, SINASC-NV, IBGE-pop). Declares schema + partitions.
- **`Importer`** — a function that orchestrates fetch + parse + sink for one `(dataset, scope)`.

## Data flow

```text
fetch (anonymous FTP) -> datasus_dbc.decompress_bytes (Rust)
  -> dbfread2 streaming -> Polars batches -> sink_parquet (Rust)
  -> DuckLake INSERT (atomic snapshot)
```

## Layout

```text
src/omnisus_db/
| lake/         - DuckLake bindings
| sources/      - per-family fetch+parse
| | datasus_ftp/
| | ibge/
| | cnes/
| transforms/   - Polars helpers + Frictionless loader
| data/         - YAML schemas + bootstrap.zip
| cli/          - Typer entry point
```

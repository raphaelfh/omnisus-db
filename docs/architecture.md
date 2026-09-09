# Architecture

For the full design rationale, see the structural design spec at
`docs/superpowers/specs/2026-09-09-repo-structure-design.md` in the repository.
It is deliberately not published to this site.

## Two core abstractions

- **`Dataset`** — an immutable registry row (SIM-DO, SINASC-NV, IBGE-pop). Holds
  identity and location only: prefix, FTP directory, cadence, partitioning,
  coverage. Anything behavioural becomes an importer module, never a flag on the
  row.
- **`Importer`** — a function that orchestrates fetch + parse + sink for one
  `(dataset, scope)`.

A third abstraction, `Source`, was removed: it was a protocol no class ever
implemented, so its declaration was an unmet promise.

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

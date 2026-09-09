# Changelog

## Unreleased

### Changed

- **Lake Parquet files are now zstd-compressed.** DuckLake rewrites ingested
  files with its own writer settings and was discarding the staging file's
  zstd, producing lake files ~3.3× larger than necessary. The connection now
  sets `parquet_compression=zstd`. Existing files keep their size until
  compacted (`omnisus-db lake optimize`).

## v0.1.0 — 2026-05-02

Initial release. Greenfield Python library replacing the old
`omnisus/backend/etl/`, `omnisus/backend/storage/`, and
`omnisus/backend/app/*_dicionario.py` code paths.

### Added

- **DuckLake 1.0** catalog (SQLite default; Postgres via `Lake.cloud()`)
- **Source families:** DATASUS-FTP (anonymous FTP transport), IBGE (SIDRA REST), CNES (DATASUS-FTP)
- **Datasets:** SIM-DO, SINASC-NV, SIH-RD (monthly), IBGE-pop, CNES-ST (monthly)
- **Auxiliary tables:** `aux_uf` (27 rows), `aux_municipios` (5571 rows), `aux_cid10` (16 seed rows) — bundled in `auxiliares-bootstrap.zip`
- **8 Frictionless Table Schema YAMLs** (validated in CI via `frictionless validate`)
- **CLI** (`omnisus-db`): `init`, `import`, `query`, `lake {tables, describe, snapshots, optimize, vacuum, update-auxiliares}`, `doctor`
- **Top-level Python API:** `import_sim`, `import_sinasc`, `import_sih`, `import_ibge_pop`, `import_cnes_st`, `Lake`, `ImportResult`, `ScopeKey`, `ALL_UFS`
- **DBC pipeline:** `datasus-dbc` (Rust) → `dbfread2` streaming → Polars batches (100k rows) → `sink_parquet` (zstd, 1M row groups) → DuckLake `INSERT` (atomic snapshot)
- **DBF terminator patch** for CNES-ST and similar DBC files with malformed headers
- **mkdocs-material** site (Home, Getting Started, Architecture, Migration from PySUS, per-source pages); GitHub Pages workflow
- **Pre-commit hooks:** ruff (check + format), frictionless validate, basic file hygiene
- **CI workflow:** ruff + lint + unit + integration tests on Ubuntu + macOS / Python 3.13
- **Performance benchmarks** with `pytest-benchmark` (DBF parse + full pipeline)
- **ADR 0001:** Rust DBF crate decision — `dbfread2` is 84% of parse pipeline; Rust crate (Option B) justified but deferred to v0.2.0

### Tests

- 84 unit tests (lake, sources, transforms, CLI, base protocols, frictionless interop)
- 6 integration tests (real FTP smoke + 5 fixture-driven e2e: SIM, SINASC, SIH, IBGE-pop, CNES-ST)
- 2 perf benchmarks (DBF parse, full pipeline)

### Notes

- Pre-1.0: minor bumps may break per SemVer §0.x. CHANGELOG and deprecation
  warnings used aggressively.
- **Distribution:** GitHub Releases only (PyPI namespace deferred to v1.0
  per spec §11.6).
- **Real DATASUS data:** served via anonymous FTP (`ftp.datasus.gov.br`).
  HTTP mirror at `datasus.saude.gov.br/dissemin/publicos` is currently 404
  for every dataset — code uses FTP transport.
- **DuckLake:** ATTACHes as a *catalog* (not a schema). User tables live at
  `lake.<table>`, internally `lake.main.<table>`.

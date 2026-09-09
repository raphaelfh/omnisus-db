# Changelog

## Unreleased

### Added

- **Every registered dataset is now reachable.** `import_dataset(name, scopes=...)`
  imports any DATASUS-FTP dataset — including the whole SIA/APAC family
  (`sia_bi`, `sia_am`, `sia_aq`, `sia_atd`, `sia_ad`, `sia_abo`, `sia_ps`),
  which had been registered but had no public door.
- `scopes_for(name, years=..., ufs=..., months=...)` — the product planner.
  Planning is composition: pass its result, or any `list[ScopeKey]`, to
  `import_dataset`.
- `Dataset` is public. A caller can construct one for a dataset the package
  does not curate, point `dictionary=` at their own Frictionless YAML, and
  ingest it through the same code path.
- `DEFAULT_TARGET` exported from `omnisus_db` and `omnisus_db.lake`.
- **A real FTP inventory.** `available(dataset)` lists the scopes DATASUS
  actually publishes (registry-decoded); `browse(path, depth=)` lists any FTP
  path, reaching subsystems this package does not model (SINAN, CIHA, PCE).
  Both come from one listing primitive and need no lake. Listings cache to
  Parquet under `${XDG_CACHE_HOME:-~/.cache}/omnisus-db/inventory/`
  (override with `OMNISUS_CACHE_DIR`), 24h TTL, `refresh=True` to bypass.
  DuckDB reads those files directly.
- **CLI:** `omnisus-db inventory <dataset>` and
  `omnisus-db inventory --path <ftp-path> [--depth N]`.
- **Tier 3 ground-truth probe** (`tests/integration/test_registry_probe.py`,
  weekly `probe.yml`): validates every registry row's `ftp_dir`, `prefix` and
  `coverage` against the live server — the only tier that catches a wrong row
  or a DATASUS reorganisation.

### Changed

- **Lake Parquet files are now zstd-compressed.** DuckLake rewrites ingested
  files with its own writer settings and was discarding the staging file's
  zstd, producing lake files ~3.3× larger than necessary. The connection now
  sets `parquet_compression=zstd`. Files already in a lake keep their current
  (uncompressed) size — recompressing them requires rewriting the table, and
  a later release will provide a command for that.
- `sources.datasus_ftp.inventory` was a filename codec; it is now the actual
  inventory. The codec moved to `sources.datasus_ftp.filenames` with
  identical signatures, plus a non-raising `decode()`.

### Removed

- `omnisus_db.sources.datasus_ftp.datasets.DatasetConfig` — replaced by
  `Dataset`.
- `omnisus_db.sources.datasus_ftp.inventory.DATASET_PREFIX` — derive the
  prefix map from `REGISTRY` / `PREFIX_TO_DATASET` instead.
- `omnisus_db.sources._base.Dataset` (unused) — replaced by
  `omnisus_db.Dataset`.
- `omnisus_db.sources._base.Source` — a protocol no class ever implemented.
  Discovery ships as `inventory.available()` / `inventory.crawl()` instead of
  a `Source` method, so the declaration was an unmet promise (spec I5).

### Fixed

- **Registry `coverage` for three APAC subtypes.** `sia_atd`, `sia_abo` and
  `sia_ps` declared `coverage` starting `(2008, 1)`, inherited from the rest
  of the SIA/APAC family without per-subtype verification. The Tier 3
  ground-truth probe found the server's earliest published file for each is
  later: `sia_atd` starts `(2014, 8)`, `sia_abo` starts `(2014, 1)`, `sia_ps`
  starts `(2012, 11)`. `sia_ad`, `sia_am`, `sia_aq` and `sia_bi` were checked
  and are correct at `(2008, 1)`. Anyone relying on these three datasets'
  declared coverage window should note it changed.
- **A cache write failure no longer discards a successful FTP listing.**
  `available()`/`browse()` could raise `PermissionError` (or any other
  write-side error) even though the network answer was already in hand —
  an unwritable `OMNISUS_CACHE_DIR`, a read-only `$HOME`, or a full disk
  now only logs a warning and returns the listing (spec I8: the cache is
  never authoritative).
- **`omnisus-db inventory` no longer lists a rejected dataset name in its
  own error message.** The command's help and its "unknown dataset" error
  now enumerate only the FTP-backed names it actually accepts, not the
  full `import`-command set (which includes `ibge-pop`/`ibge_pop`, which
  `inventory` has always rejected).
- **Only a 550 FTP response means "path not found."** A login failure
  (530) or a `TYPE`/`CWD` error other than 550 was previously reported as
  `FtpPathNotFound` with zero retries — the same code path the Tier 3
  probe treats as ground truth, so a busy or refusing server could look
  like a wrong registry row. Those errors are now retried to the normal
  budget and reported as `FtpUnavailable` if they persist; 550 behaviour
  is unchanged (terminal, never retried).
- **`Listing.path` is canonical on a cache hit, not just a miss.**
  `list_dir_cached("/x/")` returned `.path == "/x/"` on a cache hit and
  `"/x"` on a miss; a hit now reads the canonical path recorded at write
  time, matching what `list_dir` itself always promised.
- **`omnisus-db inventory --path ... --depth N` bounds `--depth` to 1-4.**
  `--depth 0` previously surfaced a raw traceback; an unbounded depth could
  sequentially LIST an entire DATASUS subtree against the shared public
  server (spec I7).

`get_config` is kept as a compatibility wrapper over `resolve`.

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

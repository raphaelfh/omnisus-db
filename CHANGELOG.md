# Changelog

## v0.2.0 — 2026-09-12

A minor bump, not a patch: every dataset and import function was renamed
and the short-name aliases are gone, so 0.1.0 callers break.

### Removed

- `import_sim`, `import_sinasc` and `import_sih`. They were one-line aliases
  over `import_dataset` + `scopes_for` and hid the two things a repeatable
  import needs: `available()` and `policy`. Write
  `import_dataset("sim_obitos", scopes=available("sim_obitos", years=...))`.
- `import_ibge_pop` is now `import_ibge_populacao`, matching the dataset name.
  `import_cnes_estabelecimentos` and `import_cnes_master` are unchanged: both
  carry behaviour of their own, so they stay named functions.

### Fixed

- Failed DBC scopes are included in import reports. Rolled-back batches no longer
  leave missing outcomes, and unknown commits abort with inspectable partial progress.
- Schema caches are cleared at transaction boundaries. Ingestion snapshots are
  finalized after commit; direct ingestion groups schema and data changes atomically.
- CNES Master refresh commits records and the derived view together. Duplicate
  explicit codes are fetched once, and conflicting prepared records are rejected.

### Added

- `available()` and `available_releases()` take `ufs` and `months`, the same
  selectors as `scopes_for()`, so "what exists for SP in 2024" is one call.
  A national row raises on either selector instead of returning nothing. The
  CLI's `--plan inventory` now delegates to it rather than post-filtering.
- `sinan_hanseniase` (SINAN HANS, 2001–, final and preliminary).
- `scripts/gen_dicionario.py`: physical-inventory YAML from one DBC file.
- Optional `omnisus-db-dbf` Rust extension for C/N DBF decoding directly to Arrow
  batches, with exact integer/string semantics and a shared staging writer.
  `OMNISUS_DBF_BACKEND=python|rust|auto` selects the backend; Python remains the
  default. Unsupported metadata can fall back before parsing, while corrupt data
  and late failures remain errors. Native wheels have independent build/install
  checks, fixture parity tests and resource benchmarks.
- **`pip install omnisus-db` works without a Rust toolchain on Python 3.12.**
  `requires-python` was `>=3.13` for no recorded reason — there is no 3.13-only
  syntax in the package and the full suite passes on 3.12 — while `datasus-dbc`
  ships cp313 wheels only for manylinux aarch64/armv7l/ppc64le/s390x. So every
  mainstream install resolved to the sdist and needed cargo. The floor is now
  `>=3.12`, where wheels exist, and CI tests that floor rather than merely
  declaring it. Users already on 3.13 still need cargo until upstream ships
  cp313 wheels; CI runs that case non-blocking so the gap stays visible.
- **Multi-year imports work at all.** DATASUS changes its layouts between
  eras — SIM-DO is 42 columns in 1996, 45 in 2005, 61 in 2010, 90 in 2015 and
  89 in 2020, adding *and* removing columns. `Lake.ingest` created the table
  from the first scope it saw and inserted positionally, so every other era was
  rejected outright. It now widens the table as new columns appear and inserts
  `BY NAME`, so a column an era lacks lands as NULL instead of shifting every
  value one place left. Only real multi-year data surfaces this; every test
  fixture is a single year.
- **Import tolerance.** A wide import no longer dies on the first file DATASUS
  never published. `import_dataset` returns an `ImportReport` of per-scope
  outcomes — `ok`, `skipped` (not published upstream; normal), `failed`
  (exists but could not be ingested; retryable). Previously the first gap
  raised and discarded every result already collected, including scopes whose
  rows were already committed, so `import_sim(years=range(2000, 2026))` fired
  702 blind fetches and died on scope 3 with no partial results and no resume.
  Inspect `report.failed`; never the report's truthiness.
- **`--plan inventory`.** `omnisus-db import <ds> --plan inventory` asks the
  server what it publishes and imports only that, instead of the blind
  cartesian product. Implies a cache refresh, because a 23-hour-old listing
  would silently omit a month published this morning. In Python this needs no
  flag — pass `available(...)` instead of `scopes_for(...)` as `scopes`.
- `omnisus-db import` exits non-zero **if and only if** a scope failed. A
  skipped scope exits zero, so an orchestrator can tell "nothing to do" from
  "something broke".
- `concurrency` (default 6) and `batch_size` (default 24) on `import_dataset`.
- Generated `docs/datasets.md` (all 11 datasets, rendered from the registry and
  checked for staleness in CI), an API reference page, and a guide to the
  inventory — `available`, `browse` and `omnisus-db inventory` shipped
  undocumented.
- `release.yml`: PyPI Trusted Publishing (OIDC) with PEP 740 attestations,
  gated on a wheel-only install. `dependabot.yml` for actions and uv.

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
- **`sinan_chagas_prelim` — the first national dataset.** SINAN's preliminary
  acute Chagas files (`CHAGBRYY.dbc`, one file per year for the whole country)
  do not fit a `(uf, ano)` scope, so `Dataset` gained `geography="national"`,
  `ScopeKey.uf` may be `None` and the table is partitioned by `_source_ano`.
  `scopes_for` rejects UF/month filters for national datasets — filter records
  after import. The final 2000–2022 files live in another directory and are
  not part of this contract; see `docs/sources/sinan_chagas_prelim.md`.
- `sources.medicamentos.horus.fetch_stock_page`: one filtered page of the
  public BNAFAR/Hórus stock API, returned with its exact bytes and provenance.
  It is an observation, not a publication — no pagination, no lake write — and
  a page is never evidence of complete dispensing coverage.
  `docs/sources/medicamentos.md` maps which medicine questions each public
  source can and cannot answer.
- `sources.ibge.products.CENSUS_YEARS` and `ESTIMATE_UNAVAILABLE_YEARS`: the
  census editions the package accepts and the estimate editions it rejects,
  each stated once and used by `resolve_product`. Consumers were listing census
  years through a private mapping and copying the rejected years by hand.
- `ImportPolicy` and `resolve` are listed in `omnisus_db.__all__` (both were
  already importable from the top level).
- `CatalogAttachError`, raised by `Lake.local`/`Lake.cloud` when the catalog
  cannot be opened. `.stage` names the statement that failed — `install` (the
  ducklake extension), `attach` or `set_option` — and the message names the
  DuckDB error class. For a remote catalog the DuckDB error is not chained,
  because its text can echo the connection string; for a local one it is, so
  the file-level reason stays visible. Replaces the `duckdb.ConnectionException`
  the remote path raised and the raw DuckDB exception the local path leaked —
  two contracts, neither saying which statement failed. Exported from
  `omnisus_db` and `omnisus_db.lake`.
- **`LakeReader` — a read-only session.** `LakeReader(target, snapshot_id=None)`
  attaches an existing catalog `READ_ONLY` with no `DATA_PATH` (the catalog
  records its own and rejects a different one), never creates a catalog and
  never sets an option, so it takes no writer lock and never blocks a writer.
  It reads alongside an import — even mid-transaction — at the last committed
  snapshot, or pinned to `snapshot_id` for a reproducible session. It offers
  `connect()`, `tables()`, `snapshots()`, `publications()` and `attempts()`,
  and nothing that writes; DuckLake refuses writes on the connection itself.
  Until now the only way to query was `Lake.local()` — a writer that takes the
  lock — which is what the Omnisus app and the notebooks were doing. The
  reader accepts every target the writer accepts, SQLite or PostgreSQL; the
  package does not impose PostgreSQL for shared reading, by decision — a
  PostgreSQL-only read profile is an application's own policy.
- **`Lake.delete_scope(table, scope)` — removal coherent with the manifest.**
  Deletes one source scope by the predicate `publish_scope` uses and retires
  every publication within it in the same transaction; a yearly scope on a
  monthly table covers all its months. Returns a `DeletionResult` with the
  rows deleted and publications retired, so unmanaged rows are visible when
  the two disagree. The Omnisus app answered 501 on scoped deletion for lack
  of exactly this.
- **`datasets()` and `products()` — the catalog, stated once.** `datasets()`
  is the public face of the registry; `products()` returns one frozen `Product`
  per importer family — the FTP datasets, `ibge_pop` and `cnes_master` — with
  its scope fields, accepted policies, reconciliation key (`run_id`,
  `publication_id` or rerun) and whether `available()` applies. Consumers were
  reaching `REGISTRY` through an internal path and hard-coding the two
  special cases, including a "first estimate year" the package never declared:
  an IBGE estimate is importable only as its latest edition.

### Changed

- **Every dataset is renamed to its readable DATASUS name** (`sim_do` → `sim_obitos`,
  `sinasc_nv` → `sinasc_nascidos_vivos`, `sih_rd` → `sih_aih_reduzida`,
  `sia_bi` → `sia_bpa_individualizado`, `sia_am` → `sia_apac_medicamentos`,
  `sia_aq` → `sia_apac_quimioterapia`, `sia_atd` → `sia_apac_tratamento_dialitico`,
  `sia_ad` → `sia_apac_laudos_diversos`, `sia_abo` → `sia_apac_cirurgia_bariatrica`,
  `sia_ps` → `sia_psicossocial`, `cnes_st` → `cnes_estabelecimentos`,
  `sinan_chagas_prelim` → `sinan_chagas`, `ibge_pop` → `ibge_populacao`;
  `import_cnes_st` → `import_cnes_estabelecimentos`). No aliases are kept.
  Lake tables carry the new names: rebuild existing lakes into a new target.
- Final and preliminary DATASUS directories are one dataset: rows declare
  `prelim_dir`, `available_releases()` shows where each scope is, every row
  carries `_source_release`, `publications()` exposes `release`, and
  `outdated()` lists the scopes whose year moved to final (re-import with
  `policy="replace"`). SIM and SINASC 2025–2026 preliminary files are now
  discoverable.
- Source identity is declared in the dictionary (`x-identity`) and checked
  by one rule for every row; the Chagas-specific validator is gone.
- Staging now types an all-blank column from its own DBF field descriptor — the
  type a sibling file stages when the column is populated — so a year where a
  DATE column is empty no longer pins the lake column to INTEGER and rejects
  the next year (found by the hanseníase pilot, `HANSBR23` `dt_transrm`). The
  curated dictionary is not used for this: it states semantics, and where the
  two disagree (`sih_aih_reduzida.rubrica`, an `N` field declared `string`) the
  declared type would reject the next month instead. A file with no records at
  all is typed from the same descriptors.
- `Lake` shares its read surface (`connect`, `tables`, `snapshots`,
  `publications`, `attempts`, `close`) with `LakeReader` through
  `omnisus_db.lake.session.Session`. Behaviour is unchanged, except that
  `connect()` on a closed handle now says so instead of "unusable".
- `publications()` rows carry `scope`, the `ScopeKey` the package wrote
  (`None` for a shape this version does not write). Consumers were decoding
  `scope_json` themselves, including the private `_source_ano` encoding of
  national scopes.
- `import_ibge_pop` and `import_cnes_master` now state that they take neither
  `run_id` nor `policy` and do not appear in `Lake.publications()`; each names
  its own reconciliation key. Legacy lakes migrate by rebuild, never by
  in-place adoption — see the reprocessing guide.

- Updated runtime, development and documentation dependency floors and the uv
  lockfile to the compatible stable releases checked on 2026-09-09, including
  DuckDB 1.5.5, Polars 1.44.2 and PyArrow 25.0.1. Python 3.12 remains the floor.
  Ruff now targets that floor and the pre-commit hook uses Ruff 0.16.6, matching
  the lockfile. The documentation stack stays on MkDocs 1.x.
- **Imports overlap fetch with parse.** Six fetches now run in flight behind a
  bounded queue while a single consumer parses and sinks; fetch and parse were
  fully serialized, so wall clock was `sum(fetch) + sum(parse+sink)`. Measured
  on 12 scopes at a simulated 300 ms fetch: 5.62 s → 2.01 s (2.8×). One
  consumer is a correctness requirement, not tuning — the lake holds one DuckDB
  connection and Polars already saturates cores inside a parse. DATASUS FTP is
  a shared public resource; the bound is deliberate.
- **Scopes commit in batches of 24**, not one DuckLake snapshot each. A wide
  SIH import left 648 snapshots and 648 small files behind. A scope is marked
  `ok` only once its batch commits, so a rolled-back batch reports its scopes
  failed and safe to retry. `batch_size=1` restores per-scope atomicity.
- **Declared `partition_by` is now applied.** `Lake.ingest` accepted the
  argument and ran `del partition_by`, so every registry row's declared
  partitioning was a promise nothing kept. Files now land under `ano=…/uf=…/`.
  Existing lakes need a one-time `ALTER TABLE … SET PARTITIONED BY`.
- The staging Parquet is read once per scope instead of three times (a
  schema-only `CREATE`, the `INSERT`, and a separate `SELECT count(*)`).
- **Lake Parquet files are now zstd-compressed.** DuckLake rewrites ingested
  files with its own writer settings and was discarding the staging file's
  zstd, producing lake files ~3.3× larger than necessary. The connection now
  sets `parquet_compression=zstd`. Files already in a lake keep their current
  (uncompressed) size — recompressing them requires rewriting the table, and
  a later release will provide a command for that.
- `sources.datasus_ftp.inventory` was a filename codec; it is now the actual
  inventory. The codec moved to `sources.datasus_ftp.filenames` with
  identical signatures, plus a non-raising `decode()`.
- `ScopeKey.uf` is `str | None`. `None` is a national source, and `str(scope)`
  renders it as `national_<ano>`. Code that assumed a two-letter UF on every
  scope must handle the national case.

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

- **A busy DATASUS was reported as a missing dataset.** `fetch.py` treated every
  `ftplib.error_perm` as permanent, but `error_perm` is *any* 5xx, and DATASUS
  answers `530 maximum number of allowed clients` when its anonymous-connection
  pool is full. Only a 550 is terminal now, as `inventory.py` already had it.
  The two modules had diverged because `FTP_HOST` and the transient-error tuple
  were each stated twice; both now live in one module.
- **`omnisus-db lake snapshots` never worked.** It asked
  `ducklake_snapshots('lake.<table>')`, which does not bind. Snapshots are
  catalog-wide in DuckLake, and the command now lists them (it no longer takes
  a table argument).
- **`ImportResult.snapshot_id` was `None` on every import ever run** — `ingest`
  made that same failing call inside a bare `except Exception`.
- `tests/integration/test_fetch_ftp_real.py` was marked `integration` only, so
  CI's `-m "not e2e and not perf"` did not deselect it and **every pull request
  opened a real FTP connection to DATASUS**. Its docstring claimed the
  opposite.
- README's quick start called `odb.query(...)`, which does not exist, and
  queried an unqualified `sim_do` rather than `lake.sim_do`. The getting-started
  guide documented `OMNISUS_DB_TARGET`, which nothing reads. `architecture.md`
  still listed the deleted `Source` protocol. `docs/index.md` claimed "no temp
  files for the heavy steps" while the parser writes one per scope.
- `mkdocs` published `docs/superpowers/` — internal specs, plans and ledgers —
  to the public site.
- `scripts/build_fixtures.py` hand-copied an FTP path map covering 5 of the 11
  datasets, so `conftest`'s "run scripts/build_fixtures.py" was a dead end for
  the other 6. It derives from the registry and covers all 11.
- The version was stated in both `pyproject.toml` and `_version.py`; it now has
  one home, which removes the two-file `sed` dance from `RELEASE.md`.

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
- **PostgreSQL catalogs could not be attached.** DuckLake needs the `postgres:`
  backend selector before the URI (`ducklake:postgres:postgresql://…`); without
  it every `Lake.cloud()` and every `ducklake:postgresql://…` target failed —
  and the failure was reported as "check connection settings", pointing at
  credentials for a bug that involved none. The selector is added for the
  `postgres`/`postgresql` schemes only; local catalogs are unchanged. Verified
  against PostgreSQL 17 with DuckDB 1.5.5
  (`reports/evidence/2026-09-10/postgres-selector/`).
- **A `postgresql:///?host=…` target lost its `//`.** `parse_target` rebuilt
  the DSN with `urlunsplit`, which restores an empty authority only for schemes
  it knows, so every parameter-only libpq URI came back as `postgresql:/?host=…`
  and the attach failed. The DSN is now rebuilt by hand; only the `storage`
  parameter is removed.

`get_config` was a compatibility wrapper over `resolve`; it was removed together
with `ALIASES` when every dataset was renamed to its readable DATASUS name (see
`### Changed` above) — there is no compatibility surface.

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

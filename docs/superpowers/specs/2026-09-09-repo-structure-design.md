# omnisus-db — Structural Design Spec

**Date:** 2026-09-09
**Status:** Proposed
**Supersedes:** nothing. Complements the v0.1.0 design spec in the parent
`omnisus` repository (`docs/superpowers/specs/2026-05-02-omnisus-db-design.md`).
**Scope:** how this repository is structured so it grows to ~40 datasets
without accumulating locks, duplicated facts, or dead configuration.

---

## 1. Why

Four defects motivated this spec. All were verified against the codebase or
the live DATASUS server, not inferred.

### 1.1 Seven of eleven datasets are unreachable

The whole SIA/APAC family (`sia_bi`, `sia_am`, `sia_aq`, `sia_atd`, `sia_ad`,
`sia_abo`, `sia_ps`) is registered, path-mapped, prefix-mapped, and has a
dictionary each — but appears **zero times** in the public API and the CLI.
Commit `3c58244` shipped internals with no user-facing door.

This is not an oversight to patch with an `elif`. It is the predictable
outcome of a dataset being defined in seven places, none of which is
authoritative.

### 1.2 A wide import aborts on the first missing file

`_import_dataset_ftp` loops `years x ufs` with no error handling, and
`fetch_dbc_bytes` re-raises `ftplib.error_perm` (550) without retry. So
`import_sim(years=range(2000, 2026))` fires 702 blind fetches and dies on the
first `(uf, year)` DATASUS never published. No partial results, no resume.

### 1.3 `ftp_dir: str` cannot express DATASUS reality

Live listing of the server (2026-09-09):

```
/dissemin/publicos/SIM      -> CID10, CID9, PRELIM, 1996_, 1997_1995
/dissemin/publicos/SIASUS   -> 199407_200712, 200801_, Anteriores_a_1994, APAC
/dissemin/publicos/SIHSUS   -> 199201_200712, 200801_, 2008..2014, DBF, CSV, XML
/dissemin/publicos/CNES     -> 200508_
```

Our rows point at `SIM/CID10/DORES`, `SIASUS/200801_`, `SIHSUS/200801_`.
Three of four families have era directories a single-string field cannot
reach. SIM before 1996, SIA before 2008, SIH before 2008 and SIM `PRELIM`
are unreachable **by construction**.

### 1.4 There is no inventory

`sources/datasus_ftp/inventory.py` is a filename codec. There is no directory
listing anywhere in the codebase — no `NLST`, no `MLSD`, no `dir()`.
`Source.list_available()` is declared in `_base.py` and implemented by nobody.
Section 4 implements it for DATASUS-FTP via `available()`; if a source family
still has no implementation once that lands, the method is removed from the
protocol rather than left as an unmet promise (I5).

---

## 2. Invariants

The charter. Everything below is an application of these.

| # | Invariant | Enforced by |
|---|---|---|
| I1 | **One row + one YAML = one dataset.** Reachability, filename codec, FTP path, CLI and docs derive from the row. | Tier 2 test |
| I2 | **The row holds identity and location only.** Anything behavioural becomes an importer module, never a flag on `Dataset`. | Review rule |
| I3 | **The registry is a catalog, not a gate.** The pipeline takes `Dataset` *values*; uncurated datasets flow through the same path. | `import_scope` signature |
| I4 | **No fact is stated twice.** If two modules need it, one derives it. | Tier 2 test |
| I5 | **A row must not lie.** Declared `partition_by` means partitioning happens; declared `ftp_dir` exists upstream. | Tier 3 probe |
| I6 | **Empty is not failed.** No falsy sentinel ever stands in for an error. | Error-contract tests |
| I7 | **Everything is bounded** — retries, concurrency, recursion depth. | Review rule |
| I8 | **The cache is never authoritative.** Corrupt or missing means refetch, never raise. | Cache tests |

I2 and I7 decide whether this ages well. The rest are mechanically checkable.

**Operational contract.** Adding a dataset is: one registry row, one
`data/dicionarios/<name>.yaml`, one test fixture. CLI, API, docs and inventory
follow automatically. Editing a fifth file means an invariant broke.

---

## 3. The kernel

One frozen row per dataset in `sources/datasus_ftp/datasets.py`, absorbing
facts currently spread across three modules.

```python
YM = tuple[int, int]   # (year, month), e.g. (2008, 1)

@dataclass(frozen=True)
class Dataset:
    name: str                       # registry key = table = YAML stem = CLI name
    prefix: str                     # DATASUS filename prefix: DO, DN, RD, BI, ATD
    ftp_dir: str                    # /dissemin/publicos/...
    partition_by: tuple[str, ...]   # ("ano","uf") | ("ano","uf","mes")
    coverage: tuple[YM, YM | None]  # (first, last|None) published
    aliases: tuple[str, ...] = ()   # CLI back-compat: "sim" -> sim_do

    @property
    def monthly(self) -> bool:      return "mes" in self.partition_by
    @property
    def dictionary(self) -> Path:   return DICIONARIOS / f"{self.name}.yaml"
```

`monthly` becomes derived, removing the duplicated fact between
`datasets.py` and `inventory.py`. `coverage` lets the planner reject
impossible scopes offline, before a socket opens.

### 3.1 What stops being hand-maintained

| Removed | Replaced by |
|---|---|
| `fetch._PATH` (11 lines) | `dataset.ftp_dir` |
| `inventory.DATASET_PREFIX` (11 lines) | comprehension over `REGISTRY` |
| `inventory.PREFIX_TO_DATASET` | same comprehension |
| 6 `import_*` facades (~90 lines) | `import_dataset(...)` + 3 one-line aliases |
| CLI `elif` ladder (~15 lines) | choices from `REGISTRY` keys + aliases |
| `mkdocs.yml` sources nav | generated `docs/datasets.md` |

Net: fewer lines than today.

### 3.2 Eras are rows, not fields

CID9 and CID10 have genuinely different columns. A single row spanning both
would claim a schema it does not have (violating I5). So era variants are
**separate rows with their own dictionaries** — `sim_do` (CID10, 1996+),
`sim_do_cid9` (1979-1995).

Cost: "all SIM 1979-2024" means importing two datasets and unioning
deliberately. That friction is correct — it surfaces a real schema break
rather than hiding it behind a silent column mismatch.

**Scope note.** This spec makes era variants *expressible*; it does not add
them. Creating `sim_do_cid9`, the pre-2008 SIA/SIH rows and `sim_do_prelim`
(each needing its own dictionary derived from that era's real layout) is
follow-up work, one row at a time, under the section 2 contract.

### 3.3 Registry as catalog, not gate

The pipeline signature takes a value:

```python
async def import_scope(*, dataset: Dataset, scope: ScopeKey, lake: Lake) -> ImportResult
```

`REGISTRY` is a dict of pre-built values, nothing more. A user can construct
`Dataset(...)` for a family we never curated and ingest it through the same
code path — no second, untyped mode. This is what keeps the registry from
becoming a lock (I3).

### 3.3.1 Names at the edge, values inside

To avoid ambiguity in every signature below: **public helpers accept dataset
*names* (`str`), resolved through `REGISTRY`; internal functions take
`Dataset` *values*.** So `odb.available("sim_do")` and
`omnisus-db inventory sim_do` are the ergonomic surface, while
`import_scope(dataset=Dataset(...), ...)` is the open door of I3. Public
helpers also accept a `Dataset` value in place of a name, which is how an
uncurated dataset reaches the same path.

### 3.4 Scope boundary

`REGISTRY` is the **DATASUS-FTP** kernel: eleven homogeneous rows.
`ibge_pop` and `cnes_master` stay their own named functions — they take
different parameters (no `ufs`, no `months`, no prefix, no FTP dir), and
forcing them into the row would make it polymorphic and half-null.
Two honest special cases beat one wide row that lies.

---

## 4. Inventory

`inventory.py` today is the filename codec; it is renamed `filenames.py`
(a pure move — only `fetch.py` imports it). `inventory.py` becomes what the
name promised.

### 4.1 Three layers

```python
list_dir(path, *, timeout=60, retries=3) -> list[FtpEntry]   # one LIST. The primitive.
crawl(path, *, depth=1) -> Iterator[FtpEntry]                # bounded recursion, sequential
available(dataset, *, years=None, refresh=False) -> list[ScopeKey]
```

`available` is closed-world (registry-decoded); `crawl` is open-world (any
path, reaching SINAN/CIHA/PCE). Same primitive underneath — the difference is
only whether filenames get decoded. One mechanism, two levels of
interpretation, no competing untyped subsystem.

Because the registry names the eleven directories that matter, the oracle
path **never recurses**. No queue, no thread pool, no locks.

```python
@dataclass(frozen=True)
class FtpEntry:
    name: str          # spaces preserved
    path: str
    parent: str
    is_dir: bool
    size_bytes: int
    modified: datetime # detects DATASUS republishing a file already ingested
```

### 4.2 Protocol facts (verified against the live server)

- DATASUS emits **MS-DOS LIST** format, not Unix: position 2 is `<DIR>` or the
  byte size; the name is `" ".join(parts[3:])` because names contain spaces.
- `ftp.encoding = "latin-1"` is **required** — `ftplib` defaults to UTF-8 and
  raises `UnicodeDecodeError` on real listings.
- `voidcmd("TYPE I")` before listing.
- Sizes exceed 32 bits in the wild (`base_aih1.duck`, 12 GB).

### 4.3 Error contract

| Condition | Behaviour |
|---|---|
| Directory exists, no entries | `[]` — a legitimate answer |
| `550` (missing or denied) | raise `FtpPathNotFound` — terminal, never retried |
| Transient (timeout, dropped socket) | bounded retry, capped backoff, fresh connection per attempt, then `FtpUnavailable` |
| Malformed LIST line | skip it, count it, surface the count — never drop the listing |

No bare `except Exception`. Empty and failed are never the same value (I6).
This matters doubly because the inventory is also the Tier 3 test oracle: a
silently short listing would report a valid registry path as missing.

### 4.4 Cache

- **Location:** `${XDG_CACHE_HOME:-~/.cache}/omnisus-db/inventory/`, overridable
  by `OMNISUS_CACHE_DIR`. No new dependency.
- **Format:** one Parquet per listed directory, named from the slugified path,
  so `ls` is debuggable.
- **Staleness:** a `fetched_at` column *inside* the file. Default TTL 24h;
  `refresh=True` forces. No sidecar metadata to desynchronise.
- **Atomicity:** temp file plus `os.replace`.
- **Never authoritative:** unreadable means miss, never error (I8).

Parquet earns its place beyond taste: DuckDB reads it directly, so the
inventory is queryable through the SQL already shipped, with no ingestion.

### 4.5 Surface

```python
odb.available("sim_do", years=range(2020, 2025))
odb.browse("/dissemin/publicos/SINAN", depth=2)
```
```bash
omnisus-db inventory sim_do [--refresh]
omnisus-db inventory --path /dissemin/publicos/SINAN --depth 2
```

---

## 5. Import and performance

### 5.1 Tolerance and planning

```python
# public, synchronous: opens and closes the lake itself (replaces the 6 facades)
def import_dataset(
    dataset: str | Dataset,
    *,
    scopes: Sequence[ScopeKey],
    target: str = DEFAULT_TARGET,
    concurrency: int = 6,
) -> ImportReport

# internal, async: caller owns the lake
async def _run(dataset: Dataset, *, scopes, lake: Lake, concurrency: int) -> ImportReport
```

The public function keeps the `target: str` ergonomics the six facades had,
so `import_sim(...)` remains a one-line alias. The loop iterates a
`list[ScopeKey]` and never asks where it came from.

```python
@dataclass(frozen=True)
class ScopeOutcome:
    scope: ScopeKey
    status: Literal["ok", "skipped", "failed"]
    result: ImportResult | None      # set when ok
    reason: str | None               # set when skipped or failed

@dataclass(frozen=True)
class ImportReport:
    outcomes: tuple[ScopeOutcome, ...]
    @property
    def rows(self) -> int: ...
    @property
    def failed(self) -> tuple[ScopeOutcome, ...]: ...
```

`ImportReport` is truthy-agnostic: callers inspect `failed`, never a bool.

- **Python:** planning is composition. `scopes=product(years, ufs)` (dumb) or
  `scopes=odb.available("sim_do", years=...)` (inventory-planned). No flag in
  the library.
- **CLI:** `--plan` is sugar selecting which planner fills `scopes`. One line
  of branching, in `main.py` only.
- **Tolerance is unconditional.** A 550 is a `Skipped` outcome, never an
  exception. `ImportReport` carries `ok / skipped / failed`, so a 702-scope run
  reports what happened instead of dying on scope 3. `coverage` rejects
  impossible scopes before any socket opens.

### 5.2 Performance, ordered by measured impact

| # | Defect (live today) | Fix | Expected |
|---|---|---|---|
| 1 | Fetch and parse fully serialized — connect, RETR, parse, insert, one at a time | Bounded producer/consumer: N fetches in flight, parse+sink consuming as bytes land | Wall clock from `sum(fetch)+sum(parse)` to about `max(sum(fetch)/N, sum(parse))` |
| 2 | One DuckLake snapshot per scope — 702 commits for a wide SIM import | Accumulate M scopes per commit (default M=24) | 702 -> ~30 commits |
| 3 | Staging Parquet read three times (`CREATE...WHERE 1=0`, `INSERT...SELECT`, `SELECT count(*)`) | Row count from the Parquet footer; create the table once per run | ~1/3 of the sink stage, free |
| 4 | `partition_by` accepted then discarded (`del partition_by`) | Actually partition | Query pruning, and the row stops lying (I5) |

**Batching and failure semantics.** Batching trades atomicity granularity for
commit count: a failure mid-batch loses that batch's uncommitted scopes, not
the run. Those scopes are reported `failed` in `ImportReport` and are safe to
retry, because a scope is only marked `ok` after its batch commits. M is
tunable; M=1 restores per-scope atomicity for callers that want it.

**Politeness constraint.** DATASUS FTP is a shared public resource.
Concurrency is bounded and politely defaulted (6). This is deliberately not
"as fast as the network allows".

**Staging stays.** `sink_parquet` streams, bounding memory on national-scale
scopes. Materializing to Arrow to skip the disk hop would trade bounded memory
for a modest saving — the wrong trade for a 30 M-record import.

### 5.3 Rust DBF: right call, wrong time

ADR 0001 measured `dbfread2` at **84.2%** of the parse pipeline (229.5 ms of
272.6 ms) and estimated 5-10x from a PyO3 + `dbase` reader. It is still not
what to do first, for the reason the ADR itself gives: real wall clock is
dominated by FTP fetch.

Item 1 above changes that. Once fetch is overlapped, parse becomes the
ceiling — and only then is the 84% the thing standing between us and
national-scale imports.

**Sequencing: concurrency first, re-run `bench_full_pipeline`, then Rust.**
The ADR's plug-in shape (try-import `omnisus_db_dbf`, fall back to `dbfread2`)
needs no change.

---

## 6. Test contract

Approach A centralizes facts, which centralizes blast radius. Internal
agreement is necessary and insufficient: if a row is wrong, everything derives
consistently wrong. So one tier must check the row against DATASUS itself.

| Tier | Proves | Cost | Runs |
|---|---|---|---|
| **1. Golden filenames** | `(dataset, scope) -> filename` exact for all rows: 2-vs-3-letter prefix ambiguity (`ATDRR2401` is `ATD`+`RR`, never `AT`+`DR`), `yy<80` century rollover, month zero-padding, `mes=None` rejection. Plus a `hypothesis` round-trip property: `parse_filename(scope_to_filename(d, s)) == (s, d)`. | offline, ms | every PR |
| **2. Registry consistency** | Precisely: (a) every `REGISTRY` key has a `dicionarios/<key>.yaml`; (b) `cli_dataset_choices() == set(REGISTRY) \| aliases`; (c) `available()` accepts exactly `set(REGISTRY)`; (d) prefixes are unique; (e) `("mes" in partition_by) == monthly`; (f) every non-`aux_*` YAML is owned by exactly one dataset, where the owner set is `REGISTRY` **plus the declared non-FTP datasets** (`ibge_pop`). `aux_*.yaml` are bootstrap tables and exempt. This is the test that makes the SIA gap impossible. | offline, ms | every PR |
| **3. Ground-truth probe** | The row matches reality: `ftp_dir` exists, at least one file carries `prefix`, `coverage` matches the earliest file actually published. The only tier that catches a wrong path or a DATASUS reorganisation. | network, flaky upstream | scheduled |

The inventory is the Tier 3 oracle. The feature and its own test harness are
the same code — which is why this stays simple instead of doubling.

Parsing fixtures come from real captured listings (`<DIR>` entries, a 12 GB
file, two-digit years spanning 2010 to 2026), tested offline. Cache behaviour
uses `pyfakefs`, already a dev dependency and currently unused.

---

## 7. Repository infrastructure

### 7.1 CI — turning dead configuration live

| Change | Why |
|---|---|
| `uv sync --frozen` | The lockfile is committed and never enforced; green CI is not reproducible |
| `mypy` in pre-commit and CI | We ship `py.typed` and verify it nowhere |
| `--cov-fail-under=85` replacing the orphan `coverage.xml` | The XML is written and consumed by nothing; 85 is at or below current measured coverage, so it ratchets rather than blocks |
| New `probe.yml`: Tier 3 on a weekly cron plus `workflow_dispatch` | Catches DATASUS reorganisations before users do; off the PR path because upstream is flaky |
| `concurrency:` groups on both workflows | Stacked pushes race the Pages deploy |
| `windows-latest` in the matrix | Our users are epidemiologists on Windows; we have FTP and path code and test neither there |
| `dependabot.yml` (actions + uv) | |

### 7.2 Release — delete the runbook

`release.yml` on tag `v*`: `uv build`, then **PyPI Trusted Publishing (OIDC)**
with PEP 740 build attestations. No long-lived token — simpler *and* stronger.

Version has one home: `_version.py`, with hatch `dynamic = ["version"]`.
This removes the two-file `sed` dance and its macOS-only `sed -i ''`.
`RELEASE.md` shrinks to "tag and push".

### 7.3 Docs — stop maintaining what the registry knows

- One **generated `docs/datasets.md`** rendering the registry as a table
  (name, prefix, coverage, partitioning, dictionary link). Generated by
  `scripts/gen_datasets_doc.py`, run as a pre-commit hook and re-checked in CI
  with `--check` (fails if the committed file is stale) — the same pattern as
  `ruff format --check`. The file is committed, so the docs build stays a plain
  `mkdocs build` with no new plugin. Replaces the per-dataset nav treadmill
  with a page that cannot drift.
- Hand-written source pages only where real prose exists, not one per dataset
  by obligation.
- An **API reference page**, which finally makes the already-configured
  `mkdocstrings` do something.
- **CHANGELOG:** add `Unreleased`, backfill the six commits since v0.1.0, and
  correct stale counts (8 -> 15 YAMLs, 84 -> 140 tests, 5 -> 11 datasets).
  Discipline, not a bot gate.

---

## 8. Deliberately rejected

| Rejected | Why |
|---|---|
| Layered packages (`discovery/`, `ingestion/`, `catalog/`) | Adds indirection to a 2,300-line codebase. The real coupling problem is duplicated *facts*, not tangled *layers* — layering would not have caught the SIA gap; a registry test does. |
| Plugin/entry-point dataset registry | One author, eleven datasets. Ceremony bought against a hypothetical. |
| `eras` as a field on `Dataset` | One row implies one dictionary, but CID9 and CID10 differ in columns. The row would lie (I5). |
| Free-threaded Python (PEP 703) | Available on 3.13, but the Polars/DuckDB/PyArrow wheel ecosystem is immature under it — and unnecessary: `ftplib` in `to_thread` releases the GIL on I/O, and Polars/DuckDB parallelize in native threads. Revisit in a year. |
| Process pool for parsing | Pickling Arrow batches across processes eats the gain. |
| Replacing `ftplib` with an async FTP client | `to_thread` plus bounded concurrency gives the same overlap without depending on a thinner-maintained library. |
| A generic untyped ingestion path | `crawl` provides reach; ingestion stays typed through `Dataset` values (I3). Two ingestion modes would blur the product. |
| qds's thread pool + queue + lock crawler | Exists to survive a full recursive crawl. The registry means our common case lists eleven known directories. |

### 8.1 Anti-patterns observed in `drandreq/quadrosdesaude`

Studied because they have run this against the real server. Their protocol
knowledge (section 4.2) is validated and adopted. These are not:

1. **Crawl terminates early and silently.** `while not queue.empty(): sleep(2)`
   — the queue empties while workers are mid-directory and about to enqueue
   children. `task_done()` is called but `join()` never is. Produces a partial
   inventory that looks complete. Fatal for an oracle.
2. **Unbounded retry.** `while not sucesso_leitura` with no max attempts and a
   reconnect wrapped in `except Exception: pass` — spins forever on a
   persistent error. See I7.
3. **`INSERT OR IGNORE` on a path primary key.** The inventory never updates;
   a file whose size changed keeps its stale row permanently. See I8.
4. **One global lock around every single-row INSERT.** All workers serialize on
   the write path; most of the parallelism is theatre.
5. **`except Exception -> return []`.** Empty is indistinguishable from failed.
   See I6.

---

## 9. Sequencing

| Step | Delivers | Depends on |
|---|---|---|
| 1 | Unified `Dataset` row; derive `_PATH`, prefix maps; `monthly` derived | — |
| 2 | `import_dataset` + registry-driven CLI; three aliases kept | 1 |
| 3 | Tier 1 + Tier 2 tests | 1, 2 |
| 4 | `filenames.py` rename; `inventory.py` with `list_dir` / `crawl` / `available` | 1 |
| 5 | Tier 3 probe + `probe.yml` | 4 |
| 6 | Import tolerance, `ImportReport`, `coverage` pre-filtering | 2 |
| 7 | Bounded concurrency; snapshot batching; staging triple-read; `partition_by` | 6 |
| 8 | CI hardening, `release.yml`, generated docs, CHANGELOG | — |
| 9 | Re-run benchmarks; re-evaluate ADR 0001 Rust gate with fetch overlapped | 7 |

Steps 1-3 are one coherent change and close the defect in section 1.1.
Step 8 is independent and can land at any time.

## 10. Non-goals

- Ingesting SINAN, CIHA or PCE. `crawl` reaches them; curating dictionaries is
  a separate decision per family.
- A Streamlit or web UI. That belongs to the Explorer application, not to an
  ingestion library.
- Vendoring a C decompressor. `datasus-dbc` (Rust) is 6% of the parse pipeline.
- Multi-writer coordination beyond what DuckLake's Postgres catalog provides.

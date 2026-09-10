# Kernel Registry & Public API Implementation Plan

> Historical design/plan, reviewed on 2026-09-10. This records the original
> proposal, not current execution instructions. The registry and inventory now
> exist in code; Python requires >=3.12, and FTP imports return ImportReport.
> Transaction behavior is governed by the transactional-ingestion design and
> the public API/transaction guide. Historical checkbox state does not certify
> what has run. Live-network tests must carry e2e as well as integration: the
> normal CI selection does not exclude integration by itself.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every registered dataset reachable through one registry-derived Python API and CLI, with the registry as a catalog (not a gate), guarded by Tier 1 + Tier 2 tests — plus the one-line zstd fix that ships first.

**Architecture:** One frozen `Dataset` row per dataset in `datasets.py` becomes the single source of truth; the FTP path map, filename prefix map, public `import_*` facades and CLI `elif` ladder are replaced by derivations from it. The pipeline (`import_scope`) takes `Dataset` *values*, so an ad-hoc dataset with its own YAML flows through the same path as a registered one. A new `import_dataset(dataset, scopes=...)` plus a `scopes_for(...)` planner replace six bespoke facades; three one-line aliases keep back-compat.

**Tech Stack:** Python 3.13, uv, pytest + pytest-asyncio (`asyncio_mode = auto`), hypothesis (already a dev dep, first use here), Polars, DuckDB 1.5 + DuckLake, Typer + Rich, structlog.

**Spec:** `docs/superpowers/specs/2026-09-09-repo-structure-design.md` — this plan implements §9 steps 0–3 (kernel). Inventory (steps 4–5), import tolerance + performance (6–7) and infra (8) are separate plans.

## Global Constraints

- `requires-python = ">=3.13"` — do not lower it (spec §7.1.1 decision: keep 3.13).
- No new runtime or dev dependencies. `hypothesis` is already in `[project.optional-dependencies].dev`.
- Ruff: `line-length = 99`; rules `E, F, I, N, W, UP, B, SIM, RUF, ASYNC`; format with `ruff format` (double quotes). `from hypothesis import strategies as st` must be its own import line (ruff isort does not combine `as` imports).
- All tests run with `uv run pytest`. CI command is `uv run pytest -m "not e2e and not perf"`. Unit tests never touch `ftp.datasus.gov.br` — monkeypatch `omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes` and feed bytes from `tests/fixtures/dbc/*.dbc` via the `dbc_fixture` fixture in `tests/conftest.py`.
- Async tests: decorate with `@pytest.mark.asyncio` (existing convention, even though auto mode is on).
- Existing public names that tests import and that MUST keep working unchanged: `datasets.get_config`, `fetch.ftp_path_for`, `inventory.parse_filename`, `inventory.scope_to_filename`, `parse.dbc_bytes_to_lazyframe(bytes, *, dataset: str, ano=None, uf=None)`, `_runner.import_scope(*, dataset, scope, lake)`, `odb.import_sim/import_sinasc/import_sih/import_cnes_st/import_ibge_pop` returning `list[ImportResult]` (the `ImportReport` change is a later plan; `tests/integration/test_sim_e2e.py` does `results[0].rows`).
- The spec's invariants apply throughout: I2 (row holds identity + location only — no behavioural flags on `Dataset`), I4 (no fact stated twice), I6 (empty is not failed).
- Commit messages: `type(scope): summary` (see `git log`), ending with the trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Pre-commit hooks run automatically on commit (ruff, ruff-format, file hygiene).
- Work happens on the current branch in this worktree. Do not `cd` out of it.

---

## File Structure

| File | Responsibility after this plan |
|---|---|
| `src/omnisus_db/lake/connection.py` | **Modify.** Sets DuckLake `parquet_compression=zstd` after ATTACH (spec §5.2 item 5). |
| `src/omnisus_db/lake/catalog.py` | **Modify.** Gains `DEFAULT_TARGET` — the single home for the default lake target string (replaces five duplicated literals). |
| `src/omnisus_db/lake/__init__.py` | **Modify.** Re-exports `DEFAULT_TARGET`. |
| `src/omnisus_db/sources/datasus_ftp/datasets.py` | **Rewrite.** The kernel: `Dataset` row, `REGISTRY`, `ALIASES`, `resolve()`, `get_config()` (compat). Identity and location only. |
| `src/omnisus_db/sources/datasus_ftp/inventory.py` | **Modify.** `PREFIX_TO_DATASET` derived from `REGISTRY`; `DATASET_PREFIX` deleted; `scope_to_filename` accepts `str \| Dataset`. (The rename to `filenames.py` is the inventory plan's job — not here.) |
| `src/omnisus_db/sources/datasus_ftp/fetch.py` | **Modify.** `_PATH` deleted; `ftp_path_for` / `fetch_dbc_bytes` derive the directory from the row and accept `str \| Dataset`. |
| `src/omnisus_db/sources/datasus_ftp/parse.py` | **Modify.** `dbc_bytes_to_lazyframe` gains `dictionary: Path \| None = None`. |
| `src/omnisus_db/transforms/dictionaries.py` | **Modify.** `load_dicionario` accepts `str \| Path`. |
| `src/omnisus_db/sources/datasus_ftp/_runner.py` | **Modify.** `import_scope` resolves `str \| Dataset` and passes `dictionary` through — the I3 door. |
| `src/omnisus_db/sources/_base.py` | **Modify.** Delete the unused `Dataset` dataclass (name collision with the kernel row; consumed only by its own test). `Source` protocol stays — the inventory plan decides its fate (spec §1.4). |
| `src/omnisus_db/__init__.py` | **Rewrite.** `scopes_for`, `import_dataset`, three aliases, `import_cnes_st` (named: it refreshes `aux_cnes`), `import_ibge_pop` / `import_cnes_master` unchanged. |
| `src/omnisus_db/cli/main.py` | **Modify.** `import` command derives its choices from `REGISTRY` + `ALIASES`; two honest special cases (`ibge-pop`, `cnes-st`). |
| `CHANGELOG.md` | **Modify.** `## Unreleased` section. |
| `tests/unit/lake/test_connection.py` | **Modify.** zstd test. |
| `tests/unit/sources/datasus_ftp/test_datasets.py` | **Create.** Row semantics, `resolve`, ad-hoc dataset through codec + path. |
| `tests/unit/sources/test_base.py` | **Modify.** Drop the dead `Dataset` test. |
| `tests/unit/transforms/test_dictionaries.py` | **Modify.** `Path` loading tests. |
| `tests/unit/sources/datasus_ftp/test_parse.py` | **Modify.** `dictionary=` test. |
| `tests/unit/sources/datasus_ftp/test_runner.py` | **Modify.** Ad-hoc `Dataset` value through `import_scope`; fail-fast without YAML. |
| `tests/unit/test_public_api.py` | **Create.** `scopes_for`, `import_dataset`, SIA reachability. |
| `tests/unit/cli/test_main.py` | **Modify.** Registry-driven CLI tests. |
| `tests/unit/sources/datasus_ftp/test_filenames_golden.py` | **Create.** Tier 1. |
| `tests/unit/test_registry_consistency.py` | **Create.** Tier 2 (a, b, d, e, f). |

---

### Task 1: DuckLake writes zstd (spec §9 step 0)

**Files:**
- Modify: `src/omnisus_db/lake/connection.py:38-40`
- Modify: `CHANGELOG.md:1-3`
- Test: `tests/unit/lake/test_connection.py`

**Interfaces:**
- Consumes: `Lake.local(target)`, `Lake.ingest(table, lazyframe)` from `omnisus_db.lake.operations` (unchanged).
- Produces: nothing new — a behavioural fix. Every later task's lake files are zstd.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/lake/test_connection.py`:

```python
def test_lake_files_are_zstd_not_3x_larger_than_staging(tmp_path: Path) -> None:
    """DuckLake rewrites every ingested Parquet with its own writer settings
    and does not inherit the staging file's compression. Probed on DuckLake
    415a9ebd: 801,067 B without the option vs 241,497 B with it, for a
    241,491 B zstd reference (spec §5.2 item 5). The connection must set
    parquet_compression=zstd so lake files match a zstd reference written by
    the same engine."""
    import polars as pl

    from omnisus_db.lake import Lake

    with Lake.local(f"ducklake:{tmp_path}/z.ducklake") as lake:
        con = lake.connect()
        ref = tmp_path / "ref.parquet"
        con.execute(
            "COPY (SELECT 2022 AS ano, 'BA' AS uf, i AS v FROM range(200000) t(i)) "
            f"TO '{ref}' (FORMAT PARQUET, COMPRESSION zstd)"
        )
        lake.ingest("t", pl.scan_parquet(ref))
        (lake_bytes,) = con.execute(
            "SELECT sum(file_size_bytes) FROM __ducklake_metadata_lake.ducklake_data_file"
        ).fetchone()

    assert lake_bytes <= 1.2 * ref.stat().st_size, (
        f"lake wrote {lake_bytes:,} B for a {ref.stat().st_size:,} B zstd reference"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/lake/test_connection.py::test_lake_files_are_zstd_not_3x_larger_than_staging -v`
Expected: FAIL — `assert 801067 <= 289789.2` (numbers approximate; the lake file is ~3.3× the reference).

- [ ] **Step 3: Set the option after ATTACH**

In `src/omnisus_db/lake/connection.py`, replace:

```python
    con = duckdb.connect(":memory:")
    con.execute("INSTALL ducklake; LOAD ducklake;")
    con.execute(f"ATTACH 'ducklake:{catalog_uri}' AS {alias} (DATA_PATH '{storage_root}')")
    return con
```

with:

```python
    con = duckdb.connect(":memory:")
    con.execute("INSTALL ducklake; LOAD ducklake;")
    con.execute(f"ATTACH 'ducklake:{catalog_uri}' AS {alias} (DATA_PATH '{storage_root}')")
    # DuckLake rewrites every ingested Parquet with its own writer settings and
    # does not inherit the staging file's compression. Without this, lake files
    # come out ~3.3x larger than the zstd staging (spec §5.2 item 5). Files
    # already in a lake keep their size until compacted.
    con.execute(f"CALL {alias}.set_option('parquet_compression', 'zstd')")
    return con
```

- [ ] **Step 4: Run the lake tests**

Run: `uv run pytest tests/unit/lake -q`
Expected: all pass, including the new test.

- [ ] **Step 5: Start the `Unreleased` CHANGELOG section**

In `CHANGELOG.md`, insert after the `# Changelog` heading (line 1) and its blank line:

```markdown
## Unreleased

### Changed

- **Lake Parquet files are now zstd-compressed.** DuckLake rewrites ingested
  files with its own writer settings and was discarding the staging file's
  zstd, producing lake files ~3.3× larger than necessary. The connection now
  sets `parquet_compression=zstd`. Existing files keep their size until
  compacted (`omnisus-db lake optimize`).

```

- [ ] **Step 6: Commit**

```bash
git add src/omnisus_db/lake/connection.py tests/unit/lake/test_connection.py CHANGELOG.md
git commit -m "perf(lake): set DuckLake parquet_compression=zstd at connection

DuckLake rewrites every ingested Parquet with its own defaults and does not
inherit the staging file's compression; lake files were ~3.3x larger than
staging (801,067 B vs 241,497 B on the probe). Spec §5.2 item 5, step 0.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: The `Dataset` row and derived maps (spec §3, §3.1)

**Files:**
- Rewrite: `src/omnisus_db/sources/datasus_ftp/datasets.py`
- Modify: `src/omnisus_db/sources/datasus_ftp/inventory.py:6-24, 58-84`
- Modify: `src/omnisus_db/sources/datasus_ftp/fetch.py:12-39, 53-68`
- Modify: `src/omnisus_db/sources/_base.py:5-9, 30-39`
- Modify: `tests/unit/sources/test_base.py`
- Create: `tests/unit/sources/datasus_ftp/test_datasets.py`

**Interfaces:**
- Consumes: `ScopeKey` from `omnisus_db.sources._base`.
- Produces (used by every later task):
  - `datasets.Dataset` — frozen dataclass, fields `name: str, prefix: str, ftp_dir: str, cadence: Literal["yearly","monthly"], partition_by: tuple[str, ...], coverage: tuple[YM, YM | None], aliases: tuple[str, ...] = (), dictionary: Path | None = None`; property `monthly: bool`.
  - `datasets.REGISTRY: dict[str, Dataset]` — the 11 rows.
  - `datasets.ALIASES: dict[str, str]` — alias → key.
  - `datasets.resolve(dataset: str | Dataset) -> Dataset` — key, alias, or value; raises `ValueError("unknown dataset: ...")`.
  - `datasets.get_config(dataset: str) -> Dataset` — compat wrapper over `resolve`.
  - `inventory.PREFIX_TO_DATASET: dict[str, str]`; `inventory.scope_to_filename(dataset: str | Dataset, scope) -> str`; `inventory.parse_filename(name) -> tuple[ScopeKey, str]` (unchanged signature).
  - `fetch.ftp_path_for(dataset: str | Dataset, scope) -> tuple[str, str]`; `fetch.fetch_dbc_bytes(*, dataset: str | Dataset, scope, ...)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/sources/datasus_ftp/test_datasets.py`:

```python
"""Tests for the dataset registry — the kernel (spec §3)."""

from __future__ import annotations

from typing import Any

import pytest

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import ALIASES, REGISTRY, Dataset, resolve

ELEVEN = {
    "sim_do",
    "sinasc_nv",
    "sih_rd",
    "sia_bi",
    "sia_am",
    "sia_aq",
    "sia_atd",
    "sia_ad",
    "sia_abo",
    "sia_ps",
    "cnes_st",
}


def _adhoc(**over: Any) -> Dataset:
    base: dict[str, Any] = {
        "name": "custom",
        "prefix": "DO",
        "ftp_dir": "/dissemin/publicos/X",
        "cadence": "yearly",
        "partition_by": ("ano", "uf"),
        "coverage": ((2000, 1), None),
    }
    return Dataset(**{**base, **over})


def test_registry_has_exactly_the_eleven_ftp_datasets() -> None:
    assert set(REGISTRY) == ELEVEN


def test_registry_keys_equal_row_names() -> None:
    for key, d in REGISTRY.items():
        assert key == d.name


def test_monthly_is_derived_from_cadence_not_partition_by() -> None:
    # spec §3: cadence (upstream fact) and partition_by (our layout) are distinct
    assert _adhoc(cadence="monthly", partition_by=("ano",)).monthly is True
    assert _adhoc(cadence="yearly", partition_by=("ano", "uf", "mes")).monthly is False


def test_row_is_frozen() -> None:
    d = _adhoc()
    with pytest.raises((AttributeError, TypeError)):
        d.name = "other"  # type: ignore[misc]


def test_dictionary_defaults_to_none_meaning_packaged_yaml() -> None:
    assert REGISTRY["sim_do"].dictionary is None


def test_resolve_by_key_returns_the_registry_object() -> None:
    assert resolve("sim_do") is REGISTRY["sim_do"]


@pytest.mark.parametrize(
    ("alias", "key"),
    [("sim", "sim_do"), ("sinasc", "sinasc_nv"), ("sih", "sih_rd"), ("cnes-st", "cnes_st")],
)
def test_resolve_by_alias(alias: str, key: str) -> None:
    assert resolve(alias) is REGISTRY[key]
    assert ALIASES[alias] == key


def test_resolve_passes_a_value_through_untouched() -> None:
    d = _adhoc()
    assert resolve(d) is d


def test_resolve_unknown_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown dataset"):
        resolve("bogus")


def test_aliases_do_not_collide_with_registry_keys() -> None:
    assert not set(ALIASES) & set(REGISTRY)


def test_adhoc_dataset_flows_through_codec_and_ftp_path() -> None:
    """I3: a Dataset value not in REGISTRY works through the same functions."""
    from omnisus_db.sources.datasus_ftp.fetch import ftp_path_for
    from omnisus_db.sources.datasus_ftp.inventory import scope_to_filename

    d = _adhoc(name="sim_cid9", prefix="DO", ftp_dir="/dissemin/publicos/SIM/CID9/DORES")
    scope = ScopeKey(uf="SP", ano=1995)
    assert scope_to_filename(d, scope) == "DOSP1995.dbc"
    assert ftp_path_for(d, scope) == ("/dissemin/publicos/SIM/CID9/DORES", "DOSP1995.dbc")


def test_adhoc_monthly_dataset_builds_monthly_filename() -> None:
    from omnisus_db.sources.datasus_ftp.inventory import scope_to_filename

    d = _adhoc(name="sia_pa", prefix="PA", cadence="monthly", partition_by=("ano", "uf", "mes"))
    assert scope_to_filename(d, ScopeKey(uf="RR", ano=2024, mes=3)) == "PARR2403.dbc"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_datasets.py -v`
Expected: FAIL at import — `ImportError: cannot import name 'ALIASES'` (and `Dataset`, `resolve`).

- [ ] **Step 3: Rewrite `datasets.py`**

Replace the entire content of `src/omnisus_db/sources/datasus_ftp/datasets.py` with:

```python
"""The DATASUS-FTP dataset registry — single source of truth (spec §3).

One frozen row per dataset. The FTP path map, filename prefix map, CLI
choices and docs all derive from these rows. Adding a dataset is one row
here plus one ``data/dicionarios/<name>.yaml`` (spec §2, operational
contract).

The registry is a catalog, not a gate (spec §3.3, ADR 0002): the pipeline
takes ``Dataset`` *values*, so a ``Dataset`` built by a caller flows through
the same path as a registered one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

YM = tuple[int, int]
"""``(year, month)``, e.g. ``(2008, 1)``."""

Cadence = Literal["yearly", "monthly"]


@dataclass(frozen=True)
class Dataset:
    """Identity and location of one DATASUS-FTP dataset.

    Holds *only* identity and location (spec I2). Anything behavioural
    belongs in an importer module, never as a flag here.
    """

    name: str
    """Registry key = lake table = YAML stem = CLI name (``sim_do``)."""

    prefix: str
    """DATASUS filename prefix: ``DO``, ``DN``, ``RD``, ``BI``, ``ATD``…"""

    ftp_dir: str
    """Directory on ``ftp.datasus.gov.br`` holding this dataset's files."""

    cadence: Cadence
    """How DATASUS publishes files. Decides filename shape (upstream fact)."""

    partition_by: tuple[str, ...]
    """How the lake table is laid out (our storage policy, spec §5.2 item 4)."""

    coverage: tuple[YM, YM | None]
    """``(first, last)`` published; ``last=None`` means ongoing.

    Provisional until the Tier 3 probe validates it against the server.
    """

    aliases: tuple[str, ...] = ()
    """Extra CLI names kept for back-compat (``"sim"`` -> ``sim_do``)."""

    dictionary: Path | None = None
    """Frictionless YAML. ``None`` -> packaged ``dicionarios/<name>.yaml``."""

    @property
    def monthly(self) -> bool:
        return self.cadence == "monthly"


_SIM = "/dissemin/publicos/SIM/CID10/DORES"
_SINASC = "/dissemin/publicos/SINASC/NOV/DNRES"
_SIH = "/dissemin/publicos/SIHSUS/200801_/Dados"
_SIA = "/dissemin/publicos/SIASUS/200801_/Dados"
_CNES_ST = "/dissemin/publicos/CNES/200508_/Dados/ST"

_YEARLY = ("ano", "uf")
_MONTHLY = ("ano", "uf", "mes")

# fmt: off
_ROWS: tuple[Dataset, ...] = (
    Dataset(name="sim_do",    prefix="DO",  ftp_dir=_SIM,     cadence="yearly",  partition_by=_YEARLY,       coverage=((1996, 1), None), aliases=("sim",)),
    Dataset(name="sinasc_nv", prefix="DN",  ftp_dir=_SINASC,  cadence="yearly",  partition_by=_YEARLY,       coverage=((1996, 1), None), aliases=("sinasc",)),
    Dataset(name="sih_rd",    prefix="RD",  ftp_dir=_SIH,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2008, 1), None), aliases=("sih",)),
    Dataset(name="sia_bi",    prefix="BI",  ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2008, 1), None)),
    Dataset(name="sia_am",    prefix="AM",  ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2008, 1), None)),
    Dataset(name="sia_aq",    prefix="AQ",  ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2008, 1), None)),
    Dataset(name="sia_atd",   prefix="ATD", ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2008, 1), None)),
    Dataset(name="sia_ad",    prefix="AD",  ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2008, 1), None)),
    Dataset(name="sia_abo",   prefix="ABO", ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2008, 1), None)),
    Dataset(name="sia_ps",    prefix="PS",  ftp_dir=_SIA,     cadence="monthly", partition_by=_MONTHLY,      coverage=((2008, 1), None)),
    Dataset(name="cnes_st",   prefix="ST",  ftp_dir=_CNES_ST, cadence="monthly", partition_by=("ano", "mes"), coverage=((2005, 8), None), aliases=("cnes-st",)),
)
# fmt: on

REGISTRY: dict[str, Dataset] = {d.name: d for d in _ROWS}

ALIASES: dict[str, str] = {alias: d.name for d in _ROWS for alias in d.aliases}


def resolve(dataset: str | Dataset) -> Dataset:
    """Return the ``Dataset`` for a registry key, an alias, or a value.

    Names at the edge, values inside (spec §3.3.1): a ``Dataset`` value
    passes through untouched — that is how an uncurated dataset reaches the
    pipeline.
    """
    if isinstance(dataset, Dataset):
        return dataset
    key = ALIASES.get(dataset, dataset)
    try:
        return REGISTRY[key]
    except KeyError:
        raise ValueError(f"unknown dataset: {dataset!r}") from None


def get_config(dataset: str) -> Dataset:
    """Registry lookup by key. Kept for callers that predate :func:`resolve`."""
    return resolve(dataset)
```

Note: the `# fmt: off` / `# fmt: on` pair keeps the eleven rows column-aligned through `ruff format`; ruff honours these markers. Lines inside exceed 99 chars — `E501` is ignored in `pyproject.toml`, so `ruff check` passes.

- [ ] **Step 4: Derive the prefix map in `inventory.py`**

In `src/omnisus_db/sources/datasus_ftp/inventory.py`, replace lines 7–25 (from `from omnisus_db.sources._base import ScopeKey` through the `PREFIX_TO_DATASET` definition — the textual anchors are authoritative if line numbers have drifted) with:

```python
from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import REGISTRY, Dataset, resolve

# Derived from the registry (spec §3.1) — never hand-maintained here.
PREFIX_TO_DATASET: dict[str, str] = {d.prefix: d.name for d in REGISTRY.values()}
```

In `parse_filename`, replace:

```python
    dataset = PREFIX_TO_DATASET[prefix]
    _, is_monthly = DATASET_PREFIX[dataset]
    if is_monthly:
```

with:

```python
    dataset = PREFIX_TO_DATASET[prefix]
    if REGISTRY[dataset].monthly:
```

Replace the whole `scope_to_filename` function with:

```python
def scope_to_filename(dataset: str | Dataset, scope: ScopeKey) -> str:
    """Build the DATASUS DBC filename for a given (dataset, scope).

    Accepts a registry key, an alias, or a ``Dataset`` value (spec §3.3.1),
    so an ad-hoc dataset can name its files without being registered.
    """
    d = resolve(dataset)
    yy = scope.ano % 100
    if d.monthly:
        if scope.mes is None:
            raise ValueError(f"{d.name} requires mes; got: {scope}")
        return f"{d.prefix}{scope.uf}{yy:02d}{scope.mes:02d}.dbc"
    return f"{d.prefix}{scope.uf}{scope.ano:04d}.dbc"
```

- [ ] **Step 5: Derive the directory in `fetch.py`**

In `src/omnisus_db/sources/datasus_ftp/fetch.py`, replace the import of `ScopeKey` and everything through the end of `ftp_path_for` (lines 12–39) with:

```python
from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import Dataset, resolve
from omnisus_db.sources.datasus_ftp.inventory import scope_to_filename

logger = structlog.get_logger(__name__)

FTP_HOST = "ftp.datasus.gov.br"


def ftp_path_for(dataset: str | Dataset, scope: ScopeKey) -> tuple[str, str]:
    """Return (remote_dir, filename) for the given dataset/scope.

    Both values derive from the registry row (spec §3.1); there is no
    separate path map to keep in sync.
    """
    d = resolve(dataset)
    return d.ftp_dir, scope_to_filename(d, scope)
```

Then change the signature and first lines of `fetch_dbc_bytes`:

```python
async def fetch_dbc_bytes(
    *,
    dataset: str | Dataset,
    scope: ScopeKey,
    timeout_seconds: float = 120.0,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
) -> bytes:
    """Fetch DBC bytes for one scope from DATASUS FTP, with exponential retry."""
    d = resolve(dataset)
    remote_dir, filename = ftp_path_for(d, scope)
```

and in the success log call replace `dataset=dataset,` with `dataset=d.name,`.

- [ ] **Step 6: Delete the dead `Dataset` in `_base.py` and its test**

In `src/omnisus_db/sources/_base.py`:
- Delete the `from pathlib import Path` and `import pyarrow as pa` lines (only the deleted class used them).
- Delete the whole `@dataclass(frozen=True) class Dataset:` block (the one with `family`, `canonical_schema`, `dictionary_path`).

In `tests/unit/sources/test_base.py`:
- Change the imports to:

```python
from __future__ import annotations

from omnisus_db.sources._base import ImportResult, ScopeKey
```

  (drop `Path`, `pyarrow`, `pytest`, `Dataset` — none remain used).
- Delete `test_dataset_is_frozen` entirely.

- [ ] **Step 7: Run every test that touches the maps**

Run: `uv run pytest tests/unit/sources -q`
Expected: all pass — the new `test_datasets.py`, plus the untouched `test_fetch.py`, `test_inventory.py`, `test_runner.py` (`get_config` tests), `test_sia_bi.py`, `test_sia_apac.py`, `test_base.py`.

- [ ] **Step 8: Lint**

Run: `uv run ruff check src tests && uv run ruff format --check src tests`
Expected: clean. If `ruff format --check` flags `datasets.py`, run `uv run ruff format src/omnisus_db/sources/datasus_ftp/datasets.py` and confirm the `# fmt: off` block survived.

- [ ] **Step 9: Commit**

```bash
git add src/omnisus_db/sources/datasus_ftp/datasets.py src/omnisus_db/sources/datasus_ftp/inventory.py src/omnisus_db/sources/datasus_ftp/fetch.py src/omnisus_db/sources/_base.py tests/unit/sources/test_base.py tests/unit/sources/datasus_ftp/test_datasets.py
git commit -m "refactor(datasets): single-source Dataset row; derive prefix and path maps

One frozen row per dataset (identity + location only, spec I2). fetch._PATH
and inventory.DATASET_PREFIX are gone; monthly derives from cadence, not
partition_by. resolve() accepts keys, aliases and Dataset values (spec
§3.3.1). Deletes the unused _base.Dataset that collided on the name.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Dictionaries by `Path` (spec §3.3 — uncurated is not schemaless)

**Files:**
- Modify: `src/omnisus_db/transforms/dictionaries.py:29, 336-353`
- Modify: `src/omnisus_db/sources/datasus_ftp/parse.py:10-16, 130-150`
- Test: `tests/unit/transforms/test_dictionaries.py`, `tests/unit/sources/datasus_ftp/test_parse.py`

**Interfaces:**
- Consumes: nothing from Task 2 (independent of the row) — but sequenced after it so Task 4 can compose both.
- Produces:
  - `load_dicionario(name_or_path: str | Path) -> Dicionario` — `str` → packaged YAML; `Path` → that file. Raises `FileNotFoundError` either way when missing.
  - `dbc_bytes_to_lazyframe(dbc_bytes, *, dataset: str, ano=None, uf=None, dictionary: Path | None = None)`.

- [ ] **Step 1: Write the failing tests**

In `tests/unit/transforms/test_dictionaries.py`, add `from pathlib import Path` to the imports (keep existing ones), then append:

```python
def _copy_packaged(name: str, dest: Path) -> Path:
    from importlib.resources import files

    src = (files("omnisus_db.data.dicionarios") / f"{name}.yaml").read_text(encoding="utf-8")
    dest.write_text(src, encoding="utf-8")
    return dest


def test_load_dicionario_accepts_a_path(tmp_path: Path) -> None:
    """An ad-hoc dataset supplies its own YAML (spec §3.3)."""
    custom = _copy_packaged("sim_do", tmp_path / "custom.yaml")
    dic = load_dicionario(custom)
    packaged = load_dicionario("sim_do")
    assert dic.name == packaged.name
    assert dic.encoding == packaged.encoding
    assert [f["name"] for f in dic.fields] == [f["name"] for f in packaged.fields]


def test_load_dicionario_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="dicionario not found"):
        load_dicionario(tmp_path / "nope.yaml")
```

In `tests/unit/sources/datasus_ftp/test_parse.py`, add `from pathlib import Path` to the imports if not already present, then append:

```python
def test_parse_with_explicit_dictionary_path(dbc_fixture, tmp_path: Path) -> None:
    """The dictionary argument bypasses the packaged lookup entirely, so the
    dataset name need not be registered (spec §3.3)."""
    from importlib.resources import files

    custom = tmp_path / "mine.yaml"
    custom.write_text(
        (files("omnisus_db.data.dicionarios") / "sim_do.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    raw = dbc_fixture("sim_rr_2023_mini").read_bytes()
    lf = dbc_bytes_to_lazyframe(raw, dataset="not_in_registry", dictionary=custom)
    assert lf.collect().height > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/transforms/test_dictionaries.py tests/unit/sources/datasus_ftp/test_parse.py -q`
Expected: 3 failures — `load_dicionario(Path)` raises `FileNotFoundError: dicionario not found: /.../custom.yaml` for the first (it treats the Path as a name), the second passes by accident (note this — it must still pass after), and the parse test fails with `TypeError: ... unexpected keyword argument 'dictionary'`.

- [ ] **Step 3: Make `load_dicionario` accept a `Path`**

In `src/omnisus_db/transforms/dictionaries.py`, ensure `from pathlib import Path` is among the imports (add it after `from importlib.resources import files` if absent). Replace the `load_dicionario` function with:

```python
@cache
def load_dicionario(name_or_path: str | Path) -> Dicionario:
    """Load and cache a Dicionario.

    ``str`` is a dataset name resolved to the packaged
    ``dicionarios/<name>.yaml``. ``Path`` is an explicit YAML file — how an
    ad-hoc dataset supplies its own schema (spec §3.3).
    """
    if isinstance(name_or_path, Path):
        if not name_or_path.is_file():
            raise FileNotFoundError(f"dicionario not found: {name_or_path}")
        text = name_or_path.read_text(encoding="utf-8")
    else:
        yaml_path = files("omnisus_db.data.dicionarios") / f"{name_or_path}.yaml"
        if not yaml_path.is_file():
            raise FileNotFoundError(f"dicionario not found: {name_or_path}")
        text = yaml_path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
    schema = raw.get("schema", {})
    return Dicionario(
        name=raw["name"],
        title=raw.get("title", raw["name"]),
        encoding=raw.get("encoding", "utf-8"),
        fields=schema.get("fields", []),
        primary_key=schema.get("primaryKey", []),
        partitions=raw.get("x-partitions", []),
        source_format=raw.get("x-source-format", ""),
        version=raw.get("x-version", "0.0.0"),
        raw=raw,
    )
```

- [ ] **Step 4: Thread `dictionary` through `parse.py`**

In `src/omnisus_db/sources/datasus_ftp/parse.py`, add `from pathlib import Path` to the stdlib imports (after `import tempfile`). Change the signature and the first line of the body of `dbc_bytes_to_lazyframe`:

```python
def dbc_bytes_to_lazyframe(
    dbc_bytes: bytes,
    *,
    dataset: str,
    ano: int | None = None,
    uf: str | None = None,
    dictionary: Path | None = None,
) -> pl.LazyFrame:
    """Decode DBC bytes and return a Polars LazyFrame.

    Args:
        dbc_bytes: raw DBC payload from FTP.
        dataset: dataset name (e.g. "sim_do") — used for log/error messages
            and, when ``dictionary`` is None, to look up the packaged YAML.
        ano, uf: optionally injected as canonical partition columns.
        dictionary: explicit Frictionless YAML path. Bypasses the packaged
            lookup so an unregistered dataset can be parsed (spec §3.3).

    Raises:
        FileNotFoundError: if no dictionary can be loaded.
        DbfIntegrityError: if the decompressed DBF is truncated or the parsed
            record count diverges from the header's declared count.
        Exception: bubbles from datasus_dbc / dbfread2 on bad input.
    """
    dic = load_dicionario(dictionary if dictionary is not None else dataset)
```

(The remainder of the function is unchanged.)

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/unit/transforms tests/unit/sources/datasus_ftp/test_parse.py tests/unit/sources/datasus_ftp/test_integrity.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/omnisus_db/transforms/dictionaries.py src/omnisus_db/sources/datasus_ftp/parse.py tests/unit/transforms/test_dictionaries.py tests/unit/sources/datasus_ftp/test_parse.py
git commit -m "feat(dicionarios): load_dicionario accepts a Path; parse takes dictionary=

Uncurated is not schemaless (spec §3.3): an ad-hoc Dataset supplies its own
YAML. Until now load_dicionario read packaged resources only, which closed
the I3 door at the parse layer.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: `import_scope` takes `Dataset` values — the I3 door (spec §3.3)

**Files:**
- Modify: `src/omnisus_db/sources/datasus_ftp/_runner.py`
- Test: `tests/unit/sources/datasus_ftp/test_runner.py`

**Interfaces:**
- Consumes: `resolve`, `Dataset` (Task 2); `fetch_dbc_bytes(dataset=Dataset, ...)` (Task 2); `dbc_bytes_to_lazyframe(..., dictionary=)` (Task 3).
- Produces: `import_scope(*, dataset: str | Dataset, scope: ScopeKey, lake: Lake) -> ImportResult` — used by Task 5's `import_dataset` and by `cnes/importers/st.py` (unchanged, still passes `"cnes_st"`).

- [ ] **Step 1: Write the failing tests**

In `tests/unit/sources/datasus_ftp/test_runner.py`, add `from pathlib import Path` to the imports (after `from __future__ import annotations`, before `import pytest`), then append:

```python
def _custom_sim_yaml(tmp_path: Path) -> Path:
    from importlib.resources import files

    dest = tmp_path / "sim_custom.yaml"
    dest.write_text(
        (files("omnisus_db.data.dicionarios") / "sim_do.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return dest


@pytest.mark.asyncio
async def test_import_scope_accepts_an_adhoc_dataset_value(monkeypatch, tmp_path, dbc_fixture) -> None:
    """I3: a Dataset built by the caller, with its own YAML, ingests through the
    same path as a registered one — no second untyped mode (spec §3.3)."""
    from omnisus_db.sources.datasus_ftp.datasets import Dataset

    fixture_bytes = dbc_fixture("sim_rr_2023_mini").read_bytes()
    ds = Dataset(
        name="sim_custom",
        prefix="DO",
        ftp_dir="/dissemin/publicos/SIM/CID9/DORES",
        cadence="yearly",
        partition_by=("ano", "uf"),
        coverage=((1979, 1), (1995, 12)),
        dictionary=_custom_sim_yaml(tmp_path),
    )
    seen: dict[str, object] = {}

    async def fake_fetch(*, dataset, scope, **_kw: object) -> bytes:
        seen["dataset"] = dataset
        return fixture_bytes

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)

    with Lake.local(f"ducklake:{tmp_path}/x.ducklake") as lake:
        result = await import_scope(dataset=ds, scope=ScopeKey(uf="RR", ano=2023), lake=lake)
        assert result.rows > 0
        assert "sim_custom" in lake.tables()
    assert seen["dataset"] is ds


@pytest.mark.asyncio
async def test_import_scope_adhoc_without_yaml_fails_fast(monkeypatch, tmp_path) -> None:
    """Uncurated is not schemaless: no YAML -> FileNotFoundError before any
    bytes are decoded, never a silent all-strings fallback (spec §3.3)."""
    from omnisus_db.sources.datasus_ftp.datasets import Dataset

    ds = Dataset(
        name="no_such_yaml",
        prefix="ZZ",
        ftp_dir="/x",
        cadence="yearly",
        partition_by=("ano", "uf"),
        coverage=((2000, 1), None),
    )

    async def fake_fetch(*, dataset, scope, **_kw: object) -> bytes:
        return b"never decoded"

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)

    with Lake.local(f"ducklake:{tmp_path}/x.ducklake") as lake, pytest.raises(FileNotFoundError):
        await import_scope(dataset=ds, scope=ScopeKey(uf="RR", ano=2023), lake=lake)


@pytest.mark.asyncio
async def test_import_scope_accepts_an_alias(monkeypatch, tmp_path, dbc_fixture) -> None:
    fixture_bytes = dbc_fixture("sim_rr_2023_mini").read_bytes()

    async def fake_fetch(*, dataset, scope, **_kw: object) -> bytes:
        return fixture_bytes

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)

    with Lake.local(f"ducklake:{tmp_path}/x.ducklake") as lake:
        result = await import_scope(dataset="sim", scope=ScopeKey(uf="RR", ano=2023), lake=lake)
        assert result.rows > 0
        assert "sim_do" in lake.tables()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_runner.py -q`
Expected: `test_import_scope_accepts_an_adhoc_dataset_value` FAILS with `FileNotFoundError: dicionario not found: Dataset(...)` — the runner still passes the `Dataset` object to `dbc_bytes_to_lazyframe(dataset=...)`, which treats it as a packaged-YAML *name* and ignores `ds.dictionary`. The other two new tests already pass (`get_config` resolves values and aliases since Task 2, and the no-YAML case fails fast by accident); they pin behaviour that must survive the rewrite.

- [ ] **Step 3: Rewrite `_runner.py`**

Replace the entire content of `src/omnisus_db/sources/datasus_ftp/_runner.py` with:

```python
"""Generic DATASUS-FTP pipeline (per spec §11.1 hybrid pattern).

Per-dataset modules (e.g. cnes/importers/st.py) wrap this when they need
extra behaviour. For datasets with no special behaviour the generic runner
is the whole importer.
"""

from __future__ import annotations

import polars as pl
import structlog

from omnisus_db.lake import Lake
from omnisus_db.sources._base import ImportResult, ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import Dataset, resolve
from omnisus_db.sources.datasus_ftp.fetch import fetch_dbc_bytes
from omnisus_db.sources.datasus_ftp.parse import dbc_bytes_to_lazyframe

logger = structlog.get_logger(__name__)


async def import_scope(
    *,
    dataset: str | Dataset,
    scope: ScopeKey,
    lake: Lake,
) -> ImportResult:
    """Fetch + parse + sink one (dataset, scope) into the lake.

    ``dataset`` is a registry key, an alias, or a ``Dataset`` value. The
    value form is the open door of spec I3: an uncurated dataset with its
    own ``dictionary`` flows through exactly this path.
    """
    d = resolve(dataset)
    if d.monthly and scope.mes is None:
        raise ValueError(f"{d.name} is monthly; ScopeKey.mes is required")

    logger.info("import_scope.start", dataset=d.name, scope=str(scope))
    raw = await fetch_dbc_bytes(dataset=d, scope=scope)
    lf = dbc_bytes_to_lazyframe(
        raw, dataset=d.name, ano=scope.ano, uf=scope.uf, dictionary=d.dictionary
    )
    if d.monthly:
        lf = lf.with_columns(pl.lit(scope.mes).cast(pl.UInt8).alias("mes"))
    result = lake.ingest(d.name, lf, partition_by=d.partition_by)
    logger.info(
        "import_scope.done",
        dataset=d.name,
        scope=str(scope),
        rows=result.rows,
        snapshot_id=result.snapshot_id,
    )
    return result
```

- [ ] **Step 4: Run the runner tests and the e2e fixture tests**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_runner.py tests/integration -q -m "not integration"`
Expected: all pass (`test_fetch_ftp_real` is deselected by the marker; the fixture-driven e2e tests run and pass).

- [ ] **Step 5: Commit**

```bash
git add src/omnisus_db/sources/datasus_ftp/_runner.py tests/unit/sources/datasus_ftp/test_runner.py
git commit -m "feat(runner): import_scope accepts Dataset values — the I3 door

The pipeline takes values, not keys (spec §3.3, ADR 0002). An ad-hoc
Dataset with its own dictionary ingests through the same code path as a
registered one; without a dictionary it fails fast.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: `scopes_for` + `import_dataset` + aliases (spec §5.1, §9 step 2)

**Files:**
- Modify: `src/omnisus_db/lake/catalog.py` (append `DEFAULT_TARGET`)
- Modify: `src/omnisus_db/lake/__init__.py`
- Rewrite: `src/omnisus_db/__init__.py`
- Modify: `CHANGELOG.md` (Unreleased → Added)
- Create: `tests/unit/test_public_api.py`

**Interfaces:**
- Consumes: `import_scope(dataset=Dataset, ...)` (Task 4); `resolve`, `Dataset` (Task 2).
- Produces (used by Task 6 and Task 8):
  - `omnisus_db.lake.DEFAULT_TARGET: str == "ducklake:./omnisus.ducklake"`.
  - `odb.scopes_for(dataset: str | Dataset, *, years: Iterable[int], ufs: Sequence[str] | None = None, months: Iterable[int] | None = None) -> list[ScopeKey]` — order year → uf → month; `months` ignored for yearly, defaults to 1..12 for monthly; `ufs=None` → `ALL_UFS`.
  - `odb.import_dataset(dataset: str | Dataset, *, scopes: Sequence[ScopeKey], target: str = DEFAULT_TARGET) -> list[ImportResult]`.
  - `odb.import_sim / import_sinasc / import_sih / import_cnes_st` — same signatures and return type as today.
  - `odb.Dataset` re-exported.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_public_api.py`:

```python
"""Tests for the top-level API: scopes_for, import_dataset, aliases (spec §5.1)."""

from __future__ import annotations

from pathlib import Path

import omnisus_db as odb
from omnisus_db.lake import Lake
from omnisus_db.sources._base import ScopeKey


def test_scopes_for_yearly_ignores_months() -> None:
    assert odb.scopes_for("sim_do", years=[2023], ufs=["RR"], months=[1, 2]) == [
        ScopeKey(uf="RR", ano=2023)
    ]


def test_scopes_for_monthly_defaults_to_twelve_months() -> None:
    scopes = odb.scopes_for("sih_rd", years=[2024], ufs=["RR"])
    assert len(scopes) == 12
    assert scopes[0] == ScopeKey(uf="RR", ano=2024, mes=1)
    assert scopes[-1] == ScopeKey(uf="RR", ano=2024, mes=12)


def test_scopes_for_all_ufs_when_none() -> None:
    assert len(odb.scopes_for("sim_do", years=[2023])) == len(odb.ALL_UFS) == 27


def test_scopes_for_order_is_year_then_uf_then_month() -> None:
    scopes = odb.scopes_for("sih_rd", years=[2023, 2024], ufs=["AC", "RR"], months=[1, 2])
    assert [(s.ano, s.uf, s.mes) for s in scopes] == [
        (2023, "AC", 1),
        (2023, "AC", 2),
        (2023, "RR", 1),
        (2023, "RR", 2),
        (2024, "AC", 1),
        (2024, "AC", 2),
        (2024, "RR", 1),
        (2024, "RR", 2),
    ]


def test_scopes_for_accepts_alias_and_value() -> None:
    from omnisus_db.sources.datasus_ftp.datasets import REGISTRY

    by_alias = odb.scopes_for("sim", years=[2023], ufs=["RR"])
    by_value = odb.scopes_for(REGISTRY["sim_do"], years=[2023], ufs=["RR"])
    assert by_alias == by_value == [ScopeKey(uf="RR", ano=2023)]


def _fake_fetch_from(monkeypatch, payload: bytes) -> None:
    async def fake_fetch(*, dataset, scope, **_kw: object) -> bytes:
        return payload

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)


def test_import_dataset_reaches_the_sia_family(monkeypatch, tmp_path: Path, dbc_fixture) -> None:
    """Seven SIA datasets had no public door (spec §1.1). Now every row has one."""
    _fake_fetch_from(monkeypatch, dbc_fixture("sia_atd_rr_2024_01_mini").read_bytes())
    target = f"ducklake:{tmp_path}/api.ducklake"

    results = odb.import_dataset(
        "sia_atd",
        scopes=odb.scopes_for("sia_atd", years=[2024], ufs=["RR"], months=[1]),
        target=target,
    )

    assert len(results) == 1
    assert results[0].rows > 0
    with Lake.local(target) as lake:
        assert "sia_atd" in lake.tables()


def test_import_dataset_accepts_alias_and_hand_built_scopes(
    monkeypatch, tmp_path: Path, dbc_fixture
) -> None:
    """Planning is composition: any list[ScopeKey] works (spec §5.1)."""
    _fake_fetch_from(monkeypatch, dbc_fixture("sim_rr_2023_mini").read_bytes())
    target = f"ducklake:{tmp_path}/alias.ducklake"

    results = odb.import_dataset("sim", scopes=[ScopeKey(uf="RR", ano=2023)], target=target)

    assert results[0].rows > 0
    with Lake.local(target) as lake:
        assert "sim_do" in lake.tables()


def test_import_sim_alias_still_returns_a_list(monkeypatch, tmp_path: Path, dbc_fixture) -> None:
    """Back-compat for this plan: aliases keep list[ImportResult] until the
    tolerance plan introduces ImportReport (spec §5.1 compatibility note)."""
    _fake_fetch_from(monkeypatch, dbc_fixture("sim_rr_2023_mini").read_bytes())
    results = odb.import_sim(years=[2023], ufs=["RR"], target=f"ducklake:{tmp_path}/s.ducklake")
    assert isinstance(results, list)
    assert results[0].rows > 0


def test_default_target_is_exported_from_lake() -> None:
    from omnisus_db.lake import DEFAULT_TARGET

    assert DEFAULT_TARGET == "ducklake:./omnisus.ducklake"
    assert odb.DEFAULT_TARGET is DEFAULT_TARGET
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_public_api.py -q`
Expected: FAIL — `AttributeError: module 'omnisus_db' has no attribute 'scopes_for'` (and the `DEFAULT_TARGET` import error).

- [ ] **Step 3: Give `DEFAULT_TARGET` one home**

Append to `src/omnisus_db/lake/catalog.py`:

```python


DEFAULT_TARGET = "ducklake:./omnisus.ducklake"
"""Default lake target for the Python API and the CLI — its single home (spec I4)."""
```

Replace `src/omnisus_db/lake/__init__.py` with:

```python
"""Lake — DuckLake bindings."""

from omnisus_db.lake.catalog import DEFAULT_TARGET
from omnisus_db.lake.operations import Lake

__all__ = ["DEFAULT_TARGET", "Lake"]
```

- [ ] **Step 4: Rewrite `src/omnisus_db/__init__.py`**

Replace the entire file with:

```python
"""omnisus-db — Brazilian public health database ingestion lib."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable, Sequence

from omnisus_db._version import __version__
from omnisus_db.lake import DEFAULT_TARGET, Lake
from omnisus_db.sources._base import ImportResult, ScopeKey
from omnisus_db.sources.datasus_ftp._runner import import_scope as _import_scope_ftp
from omnisus_db.sources.datasus_ftp.datasets import Dataset, resolve

ALL_UFS: tuple[str, ...] = (
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
)


def scopes_for(
    dataset: str | Dataset,
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None = None,
    months: Iterable[int] | None = None,
) -> list[ScopeKey]:
    """The product planner: every (uf, year[, month]) for a dataset.

    ``months`` is ignored for yearly datasets and defaults to 1..12 for
    monthly ones. Order is year -> uf -> month. Planning is composition
    (spec §5.1): pass the result — or any other ``list[ScopeKey]`` — to
    :func:`import_dataset`.
    """
    d = resolve(dataset)
    uf_list = tuple(ufs) if ufs is not None else ALL_UFS
    month_list = tuple(months) if months is not None else tuple(range(1, 13))
    scopes: list[ScopeKey] = []
    for year in years:
        for uf in uf_list:
            if d.monthly:
                scopes.extend(ScopeKey(uf=uf, ano=year, mes=m) for m in month_list)
            else:
                scopes.append(ScopeKey(uf=uf, ano=year))
    return scopes


def import_dataset(
    dataset: str | Dataset,
    *,
    scopes: Sequence[ScopeKey],
    target: str = DEFAULT_TARGET,
) -> list[ImportResult]:
    """Import the given scopes of any DATASUS-FTP dataset into the lake.

    ``dataset`` is a registry key (``"sia_bi"``), an alias (``"sim"``) or a
    ``Dataset`` value. The loop iterates ``scopes`` and never asks where they
    came from — build them with :func:`scopes_for` or by hand.

    Per-scope tolerance and ``ImportReport`` arrive in a later plan (spec
    §5.1); until then a missing file raises, as it always has.
    """
    d = resolve(dataset)

    async def run() -> list[ImportResult]:
        results: list[ImportResult] = []
        with Lake.local(target) as lake:
            for scope in scopes:
                results.append(await _import_scope_ftp(dataset=d, scope=scope, lake=lake))
        return results

    return asyncio.run(run())


def import_sim(
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None = None,
    target: str = DEFAULT_TARGET,
) -> list[ImportResult]:
    """Import SIM-DO (declarações de óbito). Alias for ``import_dataset("sim_do", ...)``."""
    return import_dataset("sim_do", scopes=scopes_for("sim_do", years=years, ufs=ufs), target=target)


def import_sinasc(
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None = None,
    target: str = DEFAULT_TARGET,
) -> list[ImportResult]:
    """Import SINASC-NV (nascidos vivos). Alias for ``import_dataset("sinasc_nv", ...)``."""
    return import_dataset(
        "sinasc_nv", scopes=scopes_for("sinasc_nv", years=years, ufs=ufs), target=target
    )


def import_sih(
    *,
    years: Iterable[int],
    ufs: Sequence[str] | None = None,
    months: Iterable[int] = range(1, 13),
    target: str = DEFAULT_TARGET,
) -> list[ImportResult]:
    """Import SIH-RD (AIH reduzida), monthly. Alias for ``import_dataset("sih_rd", ...)``."""
    return import_dataset(
        "sih_rd",
        scopes=scopes_for("sih_rd", years=years, ufs=ufs, months=months),
        target=target,
    )


def import_ibge_pop(
    *,
    years: Iterable[int] | None = None,
    target: str = DEFAULT_TARGET,
) -> list[ImportResult]:
    """Import IBGE population estimates for the given years."""
    from omnisus_db.sources.ibge.importers.pop import import_pop_year

    if years is None:
        years = range(2010, 2026)

    async def run() -> list[ImportResult]:
        results: list[ImportResult] = []
        with Lake.local(target) as lake:
            for y in years:
                results.append(await import_pop_year(year=y, lake=lake))
        return results

    return asyncio.run(run())


def import_cnes_st(
    *,
    years: Iterable[int],
    months: Iterable[int] = range(1, 13),
    ufs: Sequence[str] | None = None,
    target: str = DEFAULT_TARGET,
) -> list[ImportResult]:
    """Import CNES-ST (estabelecimentos), monthly, then refresh ``aux_cnes``.

    This stays a named function rather than a bare alias because the view
    refresh is *behaviour*, and behaviour lives in importers, not in the
    registry row (spec I2). ``import_dataset("cnes_st", ...)`` loads the
    table but does not refresh the view; call
    ``Lake.ensure_aux_cnes_view()`` afterwards if you use that path.
    """
    results = import_dataset(
        "cnes_st",
        scopes=scopes_for("cnes_st", years=years, ufs=ufs, months=months),
        target=target,
    )
    with Lake.local(target) as lake:
        lake.ensure_aux_cnes_view()
    return results


def import_cnes_master(
    *,
    codes: Sequence[str] | None = None,
    target: str = DEFAULT_TARGET,
    concurrency: int = 5,
    only_missing: bool = True,
    progress: Callable[[int, int], None] | None = None,
) -> int:
    """Fetch CNES establishment names from the public API → ``lake.cnes_master``.

    The DATASUS public CNES-ST DBF doesn't carry establishment names; this
    pulls them from ``apidadosabertos.saude.gov.br`` and joins them into
    ``aux_cnes`` so downstream tools (e.g. the Explorer) can resolve a CNES
    code to a human-readable name.

    With ``codes=None`` and ``only_missing=True`` (defaults), runs are
    incremental — only CNES codes present in ``cnes_st`` but absent from
    ``cnes_master`` are fetched. Pass ``progress=(done, total) -> None`` to
    stream job progress (e.g. from the backend admin UI).
    """
    from omnisus_db.sources.cnes.importers.master import (
        import_cnes_master as _impl,
    )

    return _impl(
        codes=codes,
        target=target,
        concurrency=concurrency,
        only_missing=only_missing,
        progress=progress,
    )


__all__ = [
    "ALL_UFS",
    "DEFAULT_TARGET",
    "Dataset",
    "ImportResult",
    "Lake",
    "ScopeKey",
    "__version__",
    "import_cnes_master",
    "import_cnes_st",
    "import_dataset",
    "import_ibge_pop",
    "import_sih",
    "import_sim",
    "import_sinasc",
    "scopes_for",
]
```

- [ ] **Step 5: Run the API tests and the fixture e2e tests**

Run: `uv run pytest tests/unit/test_public_api.py tests/integration -q -m "not integration"`
Expected: all pass. `test_sim_e2e` still does `results[0].rows` on a list.

- [ ] **Step 6: Record the additions in the CHANGELOG**

In `CHANGELOG.md`, under `## Unreleased`, add an `### Added` block **above** `### Changed`:

```markdown
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

```

- [ ] **Step 7: Commit**

```bash
git add src/omnisus_db/__init__.py src/omnisus_db/lake/catalog.py src/omnisus_db/lake/__init__.py tests/unit/test_public_api.py CHANGELOG.md
git commit -m "feat(api): import_dataset + scopes_for — every registered dataset reachable

Replaces six bespoke facades with one registry-driven entry point and a
product planner; keeps import_sim/sinasc/sih as one-line aliases and
import_cnes_st as a named importer (it refreshes aux_cnes: behaviour, not
a row flag). Closes spec §1.1 — the SIA family now has a public door.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: Registry-driven CLI (spec §3.1, §9 step 2)

**Files:**
- Modify: `src/omnisus_db/cli/main.py:1-83`
- Test: `tests/unit/cli/test_main.py`

**Interfaces:**
- Consumes: `odb.scopes_for`, `odb.import_dataset`, `odb.import_cnes_st`, `odb.import_ibge_pop`, `DEFAULT_TARGET` (Task 5); `REGISTRY`, `ALIASES`, `resolve` (Task 2).
- Produces: `cli.main.dataset_choices() -> list[str]` — every name `omnisus-db import` accepts (used by Task 8's Tier 2 (b)).

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/cli/test_main.py`:

```python
def test_import_sia_bi_via_cli(monkeypatch, tmp_path: Path, dbc_fixture) -> None:
    """The CLI must reach every registry row, not a hand-maintained subset."""
    fixture_bytes = dbc_fixture("sia_bi_rr_2024_01_mini").read_bytes()

    async def fake_fetch(*, dataset, scope, **_kw: object) -> bytes:
        return fixture_bytes

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)

    target = f"ducklake:{tmp_path}/sia.ducklake"
    result = runner.invoke(
        app,
        ["import", "sia_bi", "--year", "2024", "--months", "1", "--ufs", "RR", "--target", target],
    )
    assert result.exit_code == 0, result.output

    from omnisus_db.lake import Lake

    with Lake.local(target) as lake:
        assert "sia_bi" in lake.tables()


def test_import_unknown_dataset_lists_the_choices() -> None:
    result = runner.invoke(app, ["import", "bogus", "--year", "2024"])
    assert result.exit_code != 0
    assert "unknown dataset" in result.output
    assert "sia_bi" in result.output


def test_import_help_lists_registry_names_and_aliases() -> None:
    result = runner.invoke(app, ["import", "--help"])
    assert result.exit_code == 0
    for name in ("sim", "sia_atd", "cnes-st", "ibge-pop"):
        assert name in result.output


def test_dataset_choices_cover_registry_aliases_and_non_ftp() -> None:
    from omnisus_db.cli.main import dataset_choices
    from omnisus_db.sources.datasus_ftp.datasets import ALIASES, REGISTRY

    choices = set(dataset_choices())
    assert set(REGISTRY) | set(ALIASES) <= choices
    assert "ibge-pop" in choices


def test_cli_default_target_is_the_lake_default() -> None:
    from omnisus_db.cli.main import DEFAULT_TARGET as cli_default
    from omnisus_db.lake import DEFAULT_TARGET

    assert cli_default is DEFAULT_TARGET
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/cli/test_main.py -q`
Expected: the five new tests fail (`sia_bi` → `BadParameter: unknown dataset`; `dataset_choices` import error; help text lacks `sia_atd`; the identity test fails because the CLI defines its own string literal).

- [ ] **Step 3: Rewrite the top of `cli/main.py` and the `import` command**

In `src/omnisus_db/cli/main.py`, replace everything from the first line through the end of `import_cmd` (line 83, the `console.print(... imported ...)` call) with:

```python
"""omnisus-db CLI entry point (Typer + Rich)."""

from __future__ import annotations

import typer
from rich.console import Console

from omnisus_db.lake import DEFAULT_TARGET, Lake
from omnisus_db.sources.datasus_ftp.datasets import ALIASES, REGISTRY, resolve

app = typer.Typer(
    name="omnisus-db",
    help="Brazilian public health database ingestion lib.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

_NON_FTP: dict[str, str] = {"ibge-pop": "ibge_pop"}
"""CLI names of datasets that are not DATASUS-FTP rows (spec §3.4). Each has
its own named importer."""


def dataset_choices() -> list[str]:
    """Every name ``omnisus-db import`` accepts — derived, never listed by hand."""
    return sorted({*REGISTRY, *ALIASES, *_NON_FTP})


@app.command()
def init(
    target: str = typer.Option(
        DEFAULT_TARGET,
        "--target",
        "-t",
        help="DuckLake target (e.g. ducklake:./omnisus.ducklake)",
    ),
) -> None:
    """Initialize a new lake and load auxiliary tables."""
    console.print(f"[bold]Initializing[/bold] lake at {target}")
    with Lake.local(target) as lake:
        lake.bootstrap_auxiliares()
        tables = lake.tables()
    console.print(f"[green]:heavy_check_mark:[/green] {len(tables)} table(s): {', '.join(tables)}")


@app.command(name="import")
def import_cmd(
    dataset: str = typer.Argument(..., help=f"One of: {', '.join(dataset_choices())}"),
    year: list[int] | None = typer.Option(
        None, "--year", "-y", help="Repeatable; e.g. -y 2023 -y 2024"
    ),
    years_range: str | None = typer.Option(None, "--years", help="e.g. 2020-2024"),
    ufs: str | None = typer.Option(None, "--ufs", help="Comma list: SP,RJ,MG"),
    months: str | None = typer.Option(None, "--months", help="Comma list, monthly only"),
    target: str = typer.Option(DEFAULT_TARGET, "--target", "-t"),
) -> None:
    """Import a dataset into the lake."""
    import omnisus_db as odb

    # Resolve years
    if years_range:
        a, b = years_range.split("-")
        yrs: list[int] = list(range(int(a), int(b) + 1))
    elif year:
        yrs = list(year)
    else:
        raise typer.BadParameter("provide --year/-y or --years RANGE")

    uf_list = [u.strip().upper() for u in ufs.split(",")] if ufs else None
    month_list = [int(x) for x in months.split(",")] if months else None

    if dataset in _NON_FTP:
        results = odb.import_ibge_pop(years=yrs, target=target)
    else:
        try:
            d = resolve(dataset)
        except ValueError as exc:
            raise typer.BadParameter(f"{exc}. Choose from: {', '.join(dataset_choices())}") from exc
        if d.name == "cnes_st":
            # Named importer: refreshes aux_cnes after the load (spec §3.4, I2).
            results = odb.import_cnes_st(
                years=yrs, ufs=uf_list, months=month_list or range(1, 13), target=target
            )
        else:
            results = odb.import_dataset(
                d,
                scopes=odb.scopes_for(d, years=yrs, ufs=uf_list, months=month_list),
                target=target,
            )

    total_rows = sum(r.rows for r in results)
    console.print(
        f"[green]:heavy_check_mark:[/green] imported [bold]{total_rows:,}[/bold] rows "
        f"({len(results)} scope(s))"
    )
```

Everything from `@app.command()\ndef query(` onward is unchanged. Confirm the old `DEFAULT_TARGET = "ducklake:./omnisus.ducklake"` line is gone.

- [ ] **Step 4: Run the CLI tests**

Run: `uv run pytest tests/unit/cli -q`
Expected: all pass, including the pre-existing `test_import_sim_via_cli` (alias `sim`) and `test_import_requires_year_or_years`.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src tests && uv run ruff format --check src tests`
Expected: clean. If `ruff format` wants to rewrap any line, apply it with `uv run ruff format src/omnisus_db/cli/main.py`.

- [ ] **Step 6: Commit**

```bash
git add src/omnisus_db/cli/main.py tests/unit/cli/test_main.py
git commit -m "refactor(cli): dataset choices derive from the registry

The elif ladder is gone; import accepts every registry key and alias, with
two honest special cases (ibge-pop, cnes-st) instead of eleven. Unknown
names list the valid choices. DEFAULT_TARGET has one home.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: Tier 1 — golden filename table + round-trip property (spec §6)

**Files:**
- Create: `tests/unit/sources/datasus_ftp/test_filenames_golden.py`

**Interfaces:**
- Consumes: `REGISTRY` (Task 2), `scope_to_filename`, `parse_filename`, `odb.ALL_UFS`.
- Produces: nothing — a guard.

- [ ] **Step 1: Write the tests**

Create `tests/unit/sources/datasus_ftp/test_filenames_golden.py`:

```python
"""Tier 1 (spec §6): the (dataset, scope) -> filename codec is exactly right
for every registry row, plus a round-trip property over the whole space.

Centralizing facts centralizes blast radius: if a row's prefix were wrong,
every derived surface would be consistently wrong. This table is the
independent statement of what the filenames must be.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from omnisus_db import ALL_UFS
from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import REGISTRY
from omnisus_db.sources.datasus_ftp.inventory import parse_filename, scope_to_filename

# fmt: off
GOLDEN: list[tuple[str, ScopeKey, str]] = [
    ("sim_do",    ScopeKey(uf="SP", ano=2024),         "DOSP2024.dbc"),
    ("sim_do",    ScopeKey(uf="RR", ano=1996),         "DORR1996.dbc"),
    ("sinasc_nv", ScopeKey(uf="MG", ano=2022),         "DNMG2022.dbc"),
    ("sih_rd",    ScopeKey(uf="SP", ano=2024, mes=1),  "RDSP2401.dbc"),
    ("sih_rd",    ScopeKey(uf="AC", ano=2008, mes=12), "RDAC0812.dbc"),
    ("sia_bi",    ScopeKey(uf="RR", ano=2024, mes=1),  "BIRR2401.dbc"),
    ("sia_am",    ScopeKey(uf="RR", ano=2024, mes=1),  "AMRR2401.dbc"),
    ("sia_aq",    ScopeKey(uf="RR", ano=2024, mes=1),  "AQRR2401.dbc"),
    ("sia_atd",   ScopeKey(uf="RR", ano=2024, mes=1),  "ATDRR2401.dbc"),  # 3-letter: ATD+RR, never AT+DR
    ("sia_ad",    ScopeKey(uf="AC", ano=2024, mes=1),  "ADAC2401.dbc"),   # AD+AC, never ADA+C
    ("sia_abo",   ScopeKey(uf="SP", ano=2024, mes=1),  "ABOSP2401.dbc"),  # ABO+SP, never AB+OS
    ("sia_ps",    ScopeKey(uf="RR", ano=2024, mes=1),  "PSRR2401.dbc"),
    ("cnes_st",   ScopeKey(uf="RR", ano=2024, mes=1),  "STRR2401.dbc"),
    # two-digit-year pivot: yy < 80 -> 20yy, else 19yy
    ("sih_rd",    ScopeKey(uf="SP", ano=1999, mes=6),  "RDSP9906.dbc"),
    ("sih_rd",    ScopeKey(uf="SP", ano=1980, mes=6),  "RDSP8006.dbc"),
    ("sih_rd",    ScopeKey(uf="SP", ano=2079, mes=6),  "RDSP7906.dbc"),
]
# fmt: on

_IDS = [g[2] for g in GOLDEN]


@pytest.mark.parametrize(("dataset", "scope", "filename"), GOLDEN, ids=_IDS)
def test_scope_to_filename_golden(dataset: str, scope: ScopeKey, filename: str) -> None:
    assert scope_to_filename(dataset, scope) == filename


@pytest.mark.parametrize(("dataset", "scope", "filename"), GOLDEN, ids=_IDS)
def test_parse_filename_golden(dataset: str, scope: ScopeKey, filename: str) -> None:
    assert parse_filename(filename) == (scope, dataset)


def test_every_registry_row_has_a_golden_case() -> None:
    assert {g[0] for g in GOLDEN} == set(REGISTRY)


def test_monthly_dataset_rejects_scope_without_mes() -> None:
    with pytest.raises(ValueError, match="requires mes"):
        scope_to_filename("sih_rd", ScopeKey(uf="SP", ano=2024))


def test_parse_rejects_unknown_prefix() -> None:
    with pytest.raises(ValueError, match="unknown dataset prefix"):
        parse_filename("ZZSP2024.dbc")


# --- round-trip property over the whole space ------------------------------
# ano in [1980, 2079] is the range the two-digit-year pivot can round-trip.

_YEARLY = sorted(n for n, d in REGISTRY.items() if not d.monthly)
_MONTHLY = sorted(n for n, d in REGISTRY.items() if d.monthly)


@settings(max_examples=300, deadline=None)
@given(
    dataset=st.sampled_from(_YEARLY),
    uf=st.sampled_from(ALL_UFS),
    ano=st.integers(1980, 2079),
)
def test_roundtrip_yearly(dataset: str, uf: str, ano: int) -> None:
    scope = ScopeKey(uf=uf, ano=ano)
    assert parse_filename(scope_to_filename(dataset, scope)) == (scope, dataset)


@settings(max_examples=300, deadline=None)
@given(
    dataset=st.sampled_from(_MONTHLY),
    uf=st.sampled_from(ALL_UFS),
    ano=st.integers(1980, 2079),
    mes=st.integers(1, 12),
)
def test_roundtrip_monthly(dataset: str, uf: str, ano: int, mes: int) -> None:
    scope = ScopeKey(uf=uf, ano=ano, mes=mes)
    assert parse_filename(scope_to_filename(dataset, scope)) == (scope, dataset)
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_filenames_golden.py -v`
Expected: all pass on the first run — this task adds guards, not behaviour. If a golden case fails, the codec (or the row) is wrong, not the table: stop and report.

- [ ] **Step 3: Lint**

Run: `uv run ruff check tests && uv run ruff format --check tests`
Expected: clean (the `# fmt: off` block keeps the table aligned; `E501` is ignored).

- [ ] **Step 4: Commit**

```bash
git add tests/unit/sources/datasus_ftp/test_filenames_golden.py
git commit -m "test(tier1): golden filename table + hypothesis round-trip

Independent statement of every registry row's filename, incl. the 2-vs-3
letter prefix ambiguity and the two-digit-year pivot. First use of
hypothesis in the repo (spec §6).

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: Tier 2 — registry consistency (spec §6, I1/I4)

**Files:**
- Create: `tests/unit/test_registry_consistency.py`

**Interfaces:**
- Consumes: `REGISTRY`, `ALIASES` (Task 2); `odb.scopes_for` (Task 5); `cli.main.dataset_choices` (Task 6).
- Produces: nothing — the guard that makes spec §1.1 unrepeatable.

- [ ] **Step 1: Write the tests**

Create `tests/unit/test_registry_consistency.py`:

```python
"""Tier 2 (spec §6): the registry is internally consistent and every row is
reachable. This is the test that makes the SIA gap (spec §1.1) impossible.

Tier 2 (c) — ``available()`` accepts exactly the registry — lives with the
inventory plan, because ``available()`` does not exist yet.
"""

from __future__ import annotations

from importlib.resources import files

import omnisus_db as odb
from omnisus_db.cli.main import dataset_choices
from omnisus_db.sources.datasus_ftp.datasets import ALIASES, REGISTRY

NON_FTP_DATASETS = {"ibge_pop"}
"""Datasets with their own importer and YAML but no registry row (spec §3.4)."""


def _packaged_yaml_stems() -> set[str]:
    root = files("omnisus_db.data.dicionarios")
    return {p.name.removesuffix(".yaml") for p in root.iterdir() if p.name.endswith(".yaml")}


def test_a_every_row_has_a_packaged_dictionary() -> None:
    missing = {name for name in REGISTRY if name not in _packaged_yaml_stems()}
    assert not missing, f"registry rows without dicionarios/<name>.yaml: {sorted(missing)}"


def test_b_cli_accepts_every_row_and_alias() -> None:
    assert set(REGISTRY) | set(ALIASES) <= set(dataset_choices())


def test_b_python_api_accepts_every_row() -> None:
    for name in REGISTRY:
        scopes = odb.scopes_for(name, years=[2024], ufs=["RR"], months=[1])
        assert scopes, name


def test_d_prefixes_are_unique() -> None:
    prefixes = [d.prefix for d in REGISTRY.values()]
    assert len(prefixes) == len(set(prefixes)), sorted(prefixes)


def test_e_cadence_agrees_with_partition_layout() -> None:
    """Agreement between two distinct facts — never derivation (spec §3)."""
    for d in REGISTRY.values():
        assert d.monthly == ("mes" in d.partition_by), d.name


def test_f_every_non_aux_yaml_has_exactly_one_owner() -> None:
    owners = set(REGISTRY) | NON_FTP_DATASETS
    yamls = {s for s in _packaged_yaml_stems() if not s.startswith("aux_")}
    assert yamls == owners, (
        f"unowned yaml: {sorted(yamls - owners)}; owner without yaml: {sorted(owners - yamls)}"
    )


def test_keys_equal_names_and_aliases_point_at_keys() -> None:
    for key, d in REGISTRY.items():
        assert key == d.name
    for alias, key in ALIASES.items():
        assert key in REGISTRY, alias
        assert alias not in REGISTRY, alias
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/unit/test_registry_consistency.py -v`
Expected: all 7 pass. If `test_f` fails, a YAML exists that no dataset owns (or vice versa) — that is a real inconsistency in the repo; report it rather than loosening the test.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_registry_consistency.py
git commit -m "test(tier2): registry consistency — the SIA gap is now impossible

Every row has a YAML, is reachable from the CLI and the API, has a unique
prefix, and its cadence agrees with its partition layout; every non-aux
YAML has exactly one owner (spec §6, I1, I4).

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: Verification pass (the CI command, exactly)

**Files:**
- No new files. Fixes only if the checks below find something.

**Interfaces:**
- Consumes: everything above.
- Produces: a green tree at the tip of the branch.

- [ ] **Step 1: Run the CI lint gates**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: both clean. Fix anything reported, re-run.

- [ ] **Step 2: Run the CI test command**

Run: `uv run pytest -m "not e2e and not perf" -q`
Expected: 0 failures. Test count is ≥ 174 + the ~45 added by this plan.

- [ ] **Step 3: Advisory type check**

Run: `uv run mypy src`
Expected: this is *not* a gate yet (it becomes one in the infra plan, spec §7.1). Fix any error whose file was touched by this plan (`datasets.py`, `inventory.py`, `fetch.py`, `_runner.py`, `parse.py`, `dictionaries.py`, `__init__.py`, `cli/main.py`, `lake/catalog.py`, `lake/connection.py`); leave pre-existing errors elsewhere alone and list them in the commit body if any.

- [ ] **Step 4: Confirm the spec's operational contract holds**

Run: `git diff --stat v0.1.0..HEAD -- src/omnisus_db/sources/datasus_ftp/fetch.py src/omnisus_db/sources/datasus_ftp/inventory.py`
Expected: net negative line counts in both — the hand-maintained maps are gone (spec §3.1).

- [ ] **Step 5: Commit any fixes**

Only if Steps 1–3 changed files:

```bash
git add -A src tests
git commit -m "chore: lint/type fixes from the kernel plan verification pass

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Out of scope for this plan (next plans)

| Spec item | Plan |
|---|---|
| `inventory.py` → `filenames.py` rename; `list_dir` / `crawl` / `available`; cache; Tier 2 (c); Tier 3 probe + `probe.yml`; `Source.list_available` fate | Inventory plan (§9 steps 4–5) |
| `ImportReport` / `ScopeOutcome`; per-scope tolerance; `coverage` pre-filter; CLI exit status; `--plan`; bounded concurrency; `BEGIN…COMMIT` batching; staging triple-read; `SET PARTITIONED BY` | Import & performance plan (§9 steps 6–7) |
| `uv sync --frozen`; mypy gate; `--cov-fail-under=80`; wheel-only install gate; `release.yml`; generated `docs/datasets.md`; API reference page; CHANGELOG backfill of the six pre-existing commits; upstream `datasus-dbc` PR | Infra plan (§9 step 8) |
| Benchmarks re-run; tune M; ADR 0001 re-evaluation | After steps 6–7 (§9 step 9) |

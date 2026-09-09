# Inventory & Ground-Truth Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give omnisus-db a real FTP inventory — one listing primitive, an open-world browser, and a registry-decoded availability oracle — cached to plain Parquet, and use it as the oracle for a scheduled probe that validates every registry row against the live DATASUS server.

**Architecture:** `inventory.py` today is a filename codec, so it is first renamed `filenames.py` (pure move). The new `inventory.py` holds three layers over one primitive: `list_dir` (one FTP `LIST`, MS-DOS parsing, strict error contract), `crawl` (bounded recursion, open-world), and `available` (registry-decoded, closed-world). A separate `_cache.py` owns persistence: one Parquet per listed directory under a cache dir, TTL inside the file, atomic writes, never authoritative. Nothing here depends on `Lake`.

**Tech Stack:** Python 3.13, uv, stdlib `ftplib` (sync — this is not a hot path), Polars (Parquet cache), pytest + pyfakefs (both already dev deps), Typer + Rich, structlog.

**Spec:** `docs/superpowers/specs/2026-09-09-repo-structure-design.md` — this plan implements §4 in full, §6 Tier 2 (c) and Tier 3, and §9 steps 4–5. The kernel plan (§9 steps 0–3) is merged; import tolerance/performance (6–7) and infra (8) are separate plans.

## Global Constraints

- `requires-python = ">=3.13"`. **No new runtime or dev dependencies.** `pyfakefs` is already in `[project.optional-dependencies].dev` and currently unused — this plan is its first use.
- Ruff: `line-length = 99`; rules `E, F, I, N, W, UP, B, SIM, RUF, ASYNC`; `ruff format` with double quotes. `E501` is ignored, so `# fmt: off` fixture tables may exceed 99 chars.
- All tests run with `uv run pytest`. CI runs `uv run pytest -m "not e2e and not perf"`. **Unit tests never touch the network** — patch `_blocking_list` (the sync seam, mirroring `fetch.py::_blocking_fetch`), never `ftplib.FTP` itself.
- Only tests marked `@pytest.mark.integration` may reach `ftp.datasus.gov.br`. That marker is deselected by the CI command.
- Spec invariants that bind this plan: **I5** (a declaration must not lie), **I6** (empty is never a falsy stand-in for failure — an empty directory returns an empty `Listing`, a missing one raises), **I7** (retries, concurrency and recursion depth are all bounded), **I8** (the cache is never authoritative — unreadable means miss, never raise).
- Verified protocol facts, non-negotiable (probed 2026-09-09 against the live server):
  - **MLSD is not supported** — `500 Command not understood`. Use `LIST` via `ftp.dir()`.
  - `ftp.encoding = "latin-1"` is **required**; the default UTF-8 raises `UnicodeDecodeError` on real listings.
  - `ftp.voidcmd("TYPE I")` before listing.
  - MS-DOS LIST format: `MM-DD-YY  HH:MMAM/PM<pad>{SIZE|<DIR>}<pad>NAME`; position 2 is `<DIR>` or the byte size; the name is `" ".join(parts[3:])`.
  - A missing directory raises `ftplib.error_perm` — `550 The system cannot find the file specified.`
- Commit messages: `type(scope): summary`, ending with the trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. Pre-commit hooks run ruff automatically.
- Work on the current branch in this worktree. Do not `cd` out of it.

---

## File Structure

| File | Responsibility after this plan |
|---|---|
| `src/omnisus_db/sources/datasus_ftp/filenames.py` | **Create (git mv from `inventory.py`).** The filename codec only: `PREFIX_TO_DATASET`, `parse_filename`, `scope_to_filename`, plus a new non-raising `decode`. |
| `src/omnisus_db/sources/datasus_ftp/inventory.py` | **Rewrite.** `FtpEntry`, `Listing`, `FtpPathNotFound`, `FtpUnavailable`, `_parse_msdos_line`, `_blocking_list`, `list_dir`, `list_dir_cached`, `crawl`, `available`. |
| `src/omnisus_db/sources/datasus_ftp/_cache.py` | **Create.** Persistence only: `cache_dir`, `cache_path`, `read_cached`, `write_cache`. Knows nothing about FTP. |
| `src/omnisus_db/sources/datasus_ftp/fetch.py` | **Modify.** Import `scope_to_filename` from `filenames`. |
| `src/omnisus_db/sources/_base.py` | **Modify.** Delete the never-implemented `Source` protocol (I5). |
| `src/omnisus_db/__init__.py` | **Modify.** Export `available`, `browse`, `FtpEntry`, `FtpPathNotFound`, `FtpUnavailable`. |
| `src/omnisus_db/cli/main.py` | **Modify.** Add the `inventory` command. |
| `scripts/build_fixtures.py` | **Modify.** Import from `filenames`. |
| `.github/workflows/probe.yml` | **Create.** Weekly Tier 3 + `workflow_dispatch`. |
| `CHANGELOG.md` | **Modify.** `Unreleased` → Added / Changed / Removed. |
| `tests/unit/sources/datasus_ftp/test_filenames.py` | **Rename** from `test_inventory.py`; add `decode` tests. |
| `tests/unit/sources/datasus_ftp/test_msdos_parsing.py` | **Create.** Golden LIST lines from the real server. |
| `tests/unit/sources/datasus_ftp/test_list_dir.py` | **Create.** Error contract, patched at `_blocking_list`. |
| `tests/unit/sources/datasus_ftp/test_inventory_cache.py` | **Create.** TTL, atomicity, corrupt→miss (pyfakefs/tmp_path). |
| `tests/unit/sources/datasus_ftp/test_available.py` | **Create.** Decoding, filtering, `crawl` depth. |
| `tests/unit/cli/test_inventory_cmd.py` | **Create.** CLI surface. |
| `tests/integration/test_registry_probe.py` | **Create.** Tier 3, `@pytest.mark.integration`. |
| `tests/unit/test_registry_consistency.py` | **Modify.** Add Tier 2 (c). |

---

### Task 1: Rename the codec to `filenames.py` (spec §4 opening)

Pure move plus import updates. No behaviour changes.

**Files:**
- Rename: `src/omnisus_db/sources/datasus_ftp/inventory.py` → `filenames.py`
- Rename: `tests/unit/sources/datasus_ftp/test_inventory.py` → `test_filenames.py`
- Modify: `src/omnisus_db/sources/datasus_ftp/fetch.py:14`
- Modify: `scripts/build_fixtures.py:19`
- Modify: `tests/unit/sources/datasus_ftp/test_sia_apac.py:22`, `test_sia_bi.py:19`, `test_filenames_golden.py:18`, `test_datasets.py:94,103`

**Interfaces:**
- Consumes: nothing new.
- Produces: `omnisus_db.sources.datasus_ftp.filenames` exporting `PREFIX_TO_DATASET`, `parse_filename`, `scope_to_filename` — identical signatures. Every later task imports the codec from here.

- [ ] **Step 1: Move both files with git**

```bash
git mv src/omnisus_db/sources/datasus_ftp/inventory.py src/omnisus_db/sources/datasus_ftp/filenames.py
git mv tests/unit/sources/datasus_ftp/test_inventory.py tests/unit/sources/datasus_ftp/test_filenames.py
```

- [ ] **Step 2: Update the module docstring**

In `src/omnisus_db/sources/datasus_ftp/filenames.py`, replace line 1:

```python
"""DATASUS DBC filename codec: (dataset, ScopeKey) <-> filename.

Split out of the old ``inventory.py`` so that name could be used for the
actual inventory (spec §4). This module is pure — no network, no cache.
"""
```

- [ ] **Step 3: Update every importer**

Replace `datasus_ftp.inventory` with `datasus_ftp.filenames` in exactly these seven places:

```bash
sed -i '' 's/datasus_ftp\.inventory/datasus_ftp.filenames/' \
  src/omnisus_db/sources/datasus_ftp/fetch.py \
  scripts/build_fixtures.py \
  tests/unit/sources/datasus_ftp/test_sia_apac.py \
  tests/unit/sources/datasus_ftp/test_sia_bi.py \
  tests/unit/sources/datasus_ftp/test_filenames_golden.py \
  tests/unit/sources/datasus_ftp/test_datasets.py
```

Then verify nothing references the old path:

```bash
grep -rn "datasus_ftp.inventory" src tests scripts || echo "clean"
```

Expected: `clean`.

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -m "not e2e and not perf" -q`
Expected: `275 passed, 2 deselected` — identical to before the move.

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check src tests scripts && uv run ruff format --check src tests scripts
git add -A src tests scripts
git commit -m "refactor(datasus_ftp): rename inventory.py to filenames.py

The module was a filename codec, not an inventory. Frees the name for the
real inventory (spec §4). Pure move: no behaviour change, 275 tests
unchanged.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: `decode` — a non-raising codec entry point

`available()` lists directories holding files from many datasets (SIASUS/200801_/Dados carries BI, AM, AQ, ATD, AD, ABO, PS **and** PA, SAD and others we do not model). It must skip what it cannot decode rather than raise. `parse_filename` keeps raising — existing tests depend on that.

**Files:**
- Modify: `src/omnisus_db/sources/datasus_ftp/filenames.py`
- Test: `tests/unit/sources/datasus_ftp/test_filenames.py`

**Interfaces:**
- Consumes: `parse_filename` (Task 1).
- Produces: `filenames.decode(name: str) -> tuple[ScopeKey, str] | None` — `None` for any name this package cannot decode. Used by `available` (Task 6) and the Tier 3 probe (Task 8).

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/sources/datasus_ftp/test_filenames.py`:

```python
def test_decode_returns_scope_and_dataset_for_known_names() -> None:
    from omnisus_db.sources.datasus_ftp.filenames import decode

    assert decode("DOSP2024.dbc") == (ScopeKey(uf="SP", ano=2024), "sim_do")
    assert decode("ATDRR2401.dbc") == (ScopeKey(uf="RR", ano=2024, mes=1), "sia_atd")


def test_decode_returns_none_for_unmodelled_prefixes() -> None:
    """SIASUS/200801_/Dados also holds PA*, SAD* and others we do not model —
    available() must skip them, not raise (spec §4.1)."""
    from omnisus_db.sources.datasus_ftp.filenames import decode

    assert decode("PARR2401.dbc") is None
    assert decode("SADRR2401.dbc") is None


def test_decode_returns_none_for_non_dbc_and_junk() -> None:
    from omnisus_db.sources.datasus_ftp.filenames import decode

    for name in ("readme.txt", "base_aih1.duck", "", "DO.dbc", "199407_200712"):
        assert decode(name) is None, name


def test_decode_agrees_with_parse_filename_where_both_succeed() -> None:
    from omnisus_db.sources.datasus_ftp.filenames import decode, parse_filename

    assert decode("RDSP2401.dbc") == parse_filename("RDSP2401.dbc")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_filenames.py -q`
Expected: FAIL — `ImportError: cannot import name 'decode'`.

- [ ] **Step 3: Implement `decode`**

Append to `src/omnisus_db/sources/datasus_ftp/filenames.py`:

```python
def decode(name: str) -> tuple[ScopeKey, str] | None:
    """Best-effort :func:`parse_filename`: ``None`` instead of raising.

    A DATASUS directory holds files from many datasets, most of which this
    package does not model (SIASUS/200801_/Dados carries ``PA*`` and ``SAD*``
    alongside the APAC family). Callers that scan a directory need to skip
    those, not fail on them.
    """
    try:
        return parse_filename(name)
    except ValueError:
        return None
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_filenames.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/omnisus_db/sources/datasus_ftp/filenames.py tests/unit/sources/datasus_ftp/test_filenames.py
git commit -m "feat(filenames): decode() — non-raising codec for directory scans

available() scans directories holding many datasets' files; unmodelled
prefixes must be skipped, not raised on (spec §4.1).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: MS-DOS LIST parsing — `FtpEntry`, `Listing`, `_parse_msdos_line`

Offline and pure. The golden lines are verbatim from the live server.

**Files:**
- Create: `src/omnisus_db/sources/datasus_ftp/inventory.py`
- Test: `tests/unit/sources/datasus_ftp/test_msdos_parsing.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `inventory.FtpEntry` — frozen: `name: str, path: str, parent: str, is_dir: bool, size_bytes: int, modified: datetime`.
  - `inventory.Listing` — frozen: `entries: tuple[FtpEntry, ...], skipped: int, path: str`; property `files -> tuple[FtpEntry, ...]`; property `dirs -> tuple[FtpEntry, ...]`.
  - `inventory._parse_msdos_line(line: str, parent: str) -> FtpEntry | None`.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/sources/datasus_ftp/test_msdos_parsing.py`:

```python
"""MS-DOS LIST parsing (spec §4.2).

Every GOLDEN line is verbatim output from ftp.datasus.gov.br captured
2026-09-09. DATASUS answers `500 Command not understood` to MLSD, so LIST
plus this parser is the only way in.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from omnisus_db.sources.datasus_ftp.inventory import FtpEntry, Listing, _parse_msdos_line

PARENT = "/dissemin/publicos/SIM/CID10/DORES"

# fmt: off
GOLDEN: list[tuple[str, str, bool, int, datetime]] = [
    # line,                                                              name,               is_dir, size,        modified
    ("01-31-20  02:48PM                76107 DOAC1996.dbc",              "DOAC1996.dbc",     False,  76107,       datetime(2020, 1, 31, 14, 48)),
    ("12-23-25  03:48PM               874197 DOTO2024.dbc",              "DOTO2024.dbc",     False,  874197,      datetime(2025, 12, 23, 15, 48)),
    ("12-19-24  11:56AM               817587 DOTO2023.dbc",              "DOTO2023.dbc",     False,  817587,      datetime(2024, 12, 19, 11, 56)),
    ("02-24-18  07:38AM       <DIR>          199407_200712",             "199407_200712",    True,   0,           datetime(2018, 2, 24, 7, 38)),
    ("08-18-10  01:24PM       <DIR>          Anteriores_a_1994",         "Anteriores_a_1994", True,  0,           datetime(2010, 8, 18, 13, 24)),
    # 12 GB — exceeds 32 bits (spec §4.2)
    ("06-07-26  01:54PM          12000440320 base_aih1.duck",            "base_aih1.duck",   False,  12000440320, datetime(2026, 6, 7, 13, 54)),
]
# fmt: on


@pytest.mark.parametrize(("line", "name", "is_dir", "size", "modified"), GOLDEN, ids=[g[1] for g in GOLDEN])
def test_parse_golden_lines(line: str, name: str, is_dir: bool, size: int, modified: datetime) -> None:
    entry = _parse_msdos_line(line, PARENT)
    assert entry is not None
    assert entry.name == name
    assert entry.is_dir is is_dir
    assert entry.size_bytes == size
    assert entry.modified == modified
    assert entry.parent == PARENT
    assert entry.path == f"{PARENT}/{name}"


def test_names_with_spaces_are_preserved() -> None:
    """DATASUS directory names contain spaces; naive split()[3] truncates."""
    entry = _parse_msdos_line("02-24-18  07:38AM       <DIR>          Dados Antigos 1994", PARENT)
    assert entry is not None
    assert entry.name == "Dados Antigos 1994"


def test_size_exceeds_32_bits() -> None:
    entry = _parse_msdos_line(GOLDEN[-1][0], PARENT)
    assert entry is not None
    assert entry.size_bytes > 2**32


def test_mtime_two_digit_year_uses_the_posix_pivot_not_the_filename_pivot() -> None:
    """strptime %y maps 00-68 -> 2000s, 69-99 -> 1900s. That is NOT the
    filename codec's pivot (80), and the two must not be conflated."""
    entry = _parse_msdos_line("01-02-98  10:00AM                  123 OLD.dbc", PARENT)
    assert entry is not None
    assert entry.modified.year == 1998


@pytest.mark.parametrize(
    "line",
    [
        "",
        "   ",
        "garbage",
        "01-31-20  02:48PM",                      # too few fields
        "01-31-20  02:48PM   NOTANUMBER file.dbc",  # size neither int nor <DIR>
        "99-99-99  02:48PM                123 x.dbc",  # impossible date
    ],
)
def test_malformed_lines_return_none(line: str) -> None:
    assert _parse_msdos_line(line, PARENT) is None


def test_parent_with_trailing_slash_does_not_double_it() -> None:
    entry = _parse_msdos_line(GOLDEN[0][0], "/dissemin/publicos/")
    assert entry is not None
    assert entry.path == "/dissemin/publicos/DOAC1996.dbc"


def test_listing_splits_files_and_dirs_and_is_frozen() -> None:
    entries = tuple(
        e for e in (_parse_msdos_line(g[0], PARENT) for g in GOLDEN) if e is not None
    )
    listing = Listing(entries=entries, skipped=2, path=PARENT)
    assert len(listing.files) == 4
    assert len(listing.dirs) == 2
    assert listing.skipped == 2
    with pytest.raises((AttributeError, TypeError)):
        listing.skipped = 0  # type: ignore[misc]


def test_ftp_entry_is_frozen() -> None:
    entry = _parse_msdos_line(GOLDEN[0][0], PARENT)
    assert entry is not None
    with pytest.raises((AttributeError, TypeError)):
        entry.name = "other"  # type: ignore[misc]
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_msdos_parsing.py -q`
Expected: FAIL — `ModuleNotFoundError` / `ImportError` (the new `inventory.py` does not exist yet; Task 1 renamed the old one away).

- [ ] **Step 3: Create `inventory.py` with the data types and parser**

Create `src/omnisus_db/sources/datasus_ftp/inventory.py`:

```python
"""DATASUS FTP inventory: list, crawl, and decode what the server actually has.

Three layers over one primitive (spec §4.1):

    list_dir(path)      -> Listing          one LIST. The primitive.
    crawl(path, depth=) -> Iterator[FtpEntry]  bounded recursion, open-world.
    available(dataset)  -> list[ScopeKey]   registry-decoded, closed-world.

``available`` and ``crawl`` are the same mechanism at two levels of
interpretation — the only difference is whether filenames get decoded. The
registry names the eleven directories that matter, so the oracle path never
recurses: no queue, no thread pool, no locks.

This module has no dependency on ``Lake``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

_DIR_MARKER = "<DIR>"


class FtpPathNotFound(Exception):
    """The remote directory does not exist, or access was denied (550).

    Terminal — never retried. Distinct from an existing but empty directory,
    which returns an empty :class:`Listing` (spec I6).
    """


class FtpUnavailable(Exception):
    """The server could not be reached within the retry budget."""


@dataclass(frozen=True)
class FtpEntry:
    """One line of a DATASUS FTP directory listing."""

    name: str
    """File or directory name, spaces preserved."""

    path: str
    """Absolute remote path."""

    parent: str
    """Absolute path of the containing directory."""

    is_dir: bool

    size_bytes: int
    """0 for directories. Exceeds 32 bits in the wild (spec §4.2)."""

    modified: datetime
    """Server-reported mtime. Detects DATASUS republishing a file we ingested."""


@dataclass(frozen=True)
class Listing:
    """The result of one LIST, including what could not be parsed.

    ``skipped`` is structural, not a log line: the Tier 3 probe asserts it is
    zero for registry directories, and an empty ``entries`` with a missing
    directory is impossible — that raises :class:`FtpPathNotFound` (spec I6).
    """

    entries: tuple[FtpEntry, ...]
    skipped: int
    path: str

    @property
    def files(self) -> tuple[FtpEntry, ...]:
        return tuple(e for e in self.entries if not e.is_dir)

    @property
    def dirs(self) -> tuple[FtpEntry, ...]:
        return tuple(e for e in self.entries if e.is_dir)


def _parse_msdos_line(line: str, parent: str) -> FtpEntry | None:
    """Parse one MS-DOS-format LIST line, or ``None`` if it is malformed.

    DATASUS answers ``500 Command not understood`` to MLSD, so LIST is the
    only option and its format is MS-DOS, not Unix::

        01-31-20  02:48PM                76107 DOAC1996.dbc
        02-24-18  07:38AM       <DIR>          199407_200712

    Field 2 is the byte size or ``<DIR>``; the name is everything after it,
    rejoined, because DATASUS names contain spaces.

    Note the two-digit year here goes through ``strptime`` (``%y``: 00-68 ->
    2000s), which is deliberately NOT the filename codec's pivot of 80. These
    are different clocks and must not be conflated.
    """
    parts = line.split()
    if len(parts) < 4:
        return None
    marker = parts[2]
    is_dir = marker == _DIR_MARKER
    if not is_dir:
        try:
            size = int(marker)
        except ValueError:
            return None
    else:
        size = 0
    try:
        modified = datetime.strptime(f"{parts[0]} {parts[1]}", "%m-%d-%y %I:%M%p")
    except ValueError:
        return None
    name = " ".join(parts[3:])
    if not name:
        return None
    base = parent.rstrip("/")
    return FtpEntry(
        name=name,
        path=f"{base}/{name}",
        parent=parent,
        is_dir=is_dir,
        size_bytes=size,
        modified=modified,
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_msdos_parsing.py -v`
Expected: all pass (6 golden cases + 9 others).

- [ ] **Step 5: Commit**

```bash
git add src/omnisus_db/sources/datasus_ftp/inventory.py tests/unit/sources/datasus_ftp/test_msdos_parsing.py
git commit -m "feat(inventory): FtpEntry, Listing and MS-DOS LIST parsing

DATASUS answers 500 to MLSD, so LIST + MS-DOS parsing is the only way in
(spec §4.2). Golden lines are verbatim from the live server, including a
12 GB size that exceeds 32 bits and a <DIR> entry.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: `list_dir` — the network primitive and its error contract

**Files:**
- Modify: `src/omnisus_db/sources/datasus_ftp/inventory.py`
- Test: `tests/unit/sources/datasus_ftp/test_list_dir.py`

**Interfaces:**
- Consumes: `FtpEntry`, `Listing`, `_parse_msdos_line`, `FtpPathNotFound`, `FtpUnavailable` (Task 3).
- Produces:
  - `inventory._blocking_list(path: str, timeout_seconds: float) -> list[str]` — the patch seam for tests.
  - `inventory.list_dir(path: str, *, timeout_seconds: float = 60.0, max_retries: int = 3, backoff_seconds: float = 1.0) -> Listing` — sync. Raises `FtpPathNotFound` on 550, `FtpUnavailable` after the budget.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/sources/datasus_ftp/test_list_dir.py`:

```python
"""list_dir error contract (spec §4.3).

Empty and failed are never the same value (I6); retries are bounded (I7).
Patched at _blocking_list — the same seam fetch.py uses. No network.
"""

from __future__ import annotations

import ftplib
from unittest.mock import patch

import pytest

from omnisus_db.sources.datasus_ftp.inventory import (
    FtpPathNotFound,
    FtpUnavailable,
    list_dir,
)

PATH = "/dissemin/publicos/SIM/CID10/DORES"
LINE = "01-31-20  02:48PM                76107 DOAC1996.dbc"


def test_returns_parsed_entries() -> None:
    with patch(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list", return_value=[LINE]
    ):
        listing = list_dir(PATH)
    assert listing.path == PATH
    assert len(listing.entries) == 1
    assert listing.entries[0].name == "DOAC1996.dbc"
    assert listing.skipped == 0


def test_existing_but_empty_directory_returns_empty_listing_not_an_error() -> None:
    """An empty directory is a legitimate answer (spec I6)."""
    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", return_value=[]):
        listing = list_dir(PATH)
    assert listing.entries == ()
    assert listing.skipped == 0


def test_malformed_lines_are_counted_not_dropped_silently() -> None:
    with patch(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list",
        return_value=[LINE, "garbage", "also garbage"],
    ):
        listing = list_dir(PATH)
    assert len(listing.entries) == 1
    assert listing.skipped == 2


def test_550_raises_path_not_found_and_is_never_retried() -> None:
    calls = 0

    def boom(*_a: object, **_k: object) -> list[str]:
        nonlocal calls
        calls += 1
        raise ftplib.error_perm("550 The system cannot find the file specified.")

    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", side_effect=boom):
        with pytest.raises(FtpPathNotFound, match="/dissemin"):
            list_dir(PATH)
    assert calls == 1, "550 is terminal — it must not be retried"


def test_transient_error_retries_then_raises_unavailable_within_budget() -> None:
    calls = 0

    def flaky(*_a: object, **_k: object) -> list[str]:
        nonlocal calls
        calls += 1
        raise TimeoutError("dropped")

    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", side_effect=flaky):
        with pytest.raises(FtpUnavailable):
            list_dir(PATH, max_retries=3, backoff_seconds=0)
    assert calls == 3, "retries must be bounded by max_retries (I7)"


def test_transient_error_then_success_returns_the_listing() -> None:
    calls = 0

    def flaky_once(*_a: object, **_k: object) -> list[str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("dropped")
        return [LINE]

    with patch(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list", side_effect=flaky_once
    ):
        listing = list_dir(PATH, backoff_seconds=0)
    assert len(listing.entries) == 1
    assert calls == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_list_dir.py -q`
Expected: FAIL — `ImportError: cannot import name 'list_dir'`.

- [ ] **Step 3: Implement the primitive**

Add to the imports at the top of `src/omnisus_db/sources/datasus_ftp/inventory.py`:

```python
import contextlib
import ftplib
import time

import structlog
```

and after the existing imports:

```python
logger = structlog.get_logger(__name__)

FTP_HOST = "ftp.datasus.gov.br"
```

Then append to the module:

```python
def _blocking_list(path: str, timeout_seconds: float) -> list[str]:
    """One anonymous-FTP LIST of ``path``. The patch seam for tests.

    ``encoding = "latin-1"`` is required: ftplib defaults to UTF-8 and raises
    UnicodeDecodeError on real DATASUS listings (spec §4.2).
    """
    lines: list[str] = []
    with contextlib.closing(ftplib.FTP(FTP_HOST, timeout=timeout_seconds)) as ftp:
        ftp.encoding = "latin-1"
        ftp.login()  # anonymous
        ftp.voidcmd("TYPE I")
        ftp.cwd(path)
        ftp.dir(lines.append)
    return lines


def list_dir(
    path: str,
    *,
    timeout_seconds: float = 60.0,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
) -> Listing:
    """List one remote directory. The primitive every other layer builds on.

    Raises:
        FtpPathNotFound: the directory is missing or access was denied (550).
            Terminal — never retried.
        FtpUnavailable: transient failures exhausted ``max_retries``.

    An existing but empty directory returns an empty :class:`Listing`; empty
    and failed are never the same value (spec I6). Every connection attempt is
    fresh, because a long-lived FTP control connection to DATASUS does not
    survive a transient error.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            raw = _blocking_list(path, timeout_seconds)
        except ftplib.error_perm as exc:
            raise FtpPathNotFound(f"{path}: {exc}") from exc
        except (*ftplib.all_errors, OSError, TimeoutError) as exc:
            last_exc = exc
            if attempt + 1 < max_retries:
                time.sleep(backoff_seconds * (2**attempt))
            continue
        entries: list[FtpEntry] = []
        skipped = 0
        for line in raw:
            entry = _parse_msdos_line(line, path)
            if entry is None:
                skipped += 1
            else:
                entries.append(entry)
        if skipped:
            logger.warning("inventory.skipped_lines", path=path, skipped=skipped)
        logger.info("inventory.listed", path=path, entries=len(entries), skipped=skipped)
        return Listing(entries=tuple(entries), skipped=skipped, path=path)
    raise FtpUnavailable(f"{path}: {max_retries} attempts failed") from last_exc
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_list_dir.py -v`
Expected: all 6 pass.

- [ ] **Step 5: Commit**

```bash
git add src/omnisus_db/sources/datasus_ftp/inventory.py tests/unit/sources/datasus_ftp/test_list_dir.py
git commit -m "feat(inventory): list_dir with a strict error contract

550 is terminal and never retried; transient errors retry on a bounded
budget with a fresh connection each attempt; malformed lines are counted in
Listing.skipped, never silently dropped. Empty and failed are never the same
value (spec §4.3, I6, I7).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: The Parquet cache

**Files:**
- Create: `src/omnisus_db/sources/datasus_ftp/_cache.py`
- Test: `tests/unit/sources/datasus_ftp/test_inventory_cache.py`

**Interfaces:**
- Consumes: `FtpEntry`, `Listing` (Task 3).
- Produces:
  - `_cache.cache_dir() -> Path` — honours `OMNISUS_CACHE_DIR`, else `${XDG_CACHE_HOME:-~/.cache}/omnisus-db/inventory`.
  - `_cache.cache_path(remote_path: str) -> Path` — slugified, `.parquet`.
  - `_cache.read_cached(remote_path: str, *, ttl_hours: float = 24.0) -> Listing | None` — `None` on miss, stale, or unreadable. Never raises.
  - `_cache.write_cache(listing: Listing) -> Path` — atomic.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/sources/datasus_ftp/test_inventory_cache.py`:

```python
"""Inventory cache (spec §4.4). Never authoritative: unreadable means miss,
never an error (I8). Staleness lives in the file, not a sidecar."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from omnisus_db.sources.datasus_ftp._cache import (
    cache_dir,
    cache_path,
    read_cached,
    write_cache,
)
from omnisus_db.sources.datasus_ftp.inventory import FtpEntry, Listing

PATH = "/dissemin/publicos/SIM/CID10/DORES"


def _listing(path: str = PATH, n: int = 2) -> Listing:
    entries = tuple(
        FtpEntry(
            name=f"DOAC{1996 + i}.dbc",
            path=f"{path}/DOAC{1996 + i}.dbc",
            parent=path,
            is_dir=False,
            size_bytes=76107 + i,
            modified=datetime(2020, 1, 31, 14, 48),
        )
        for i in range(n)
    )
    return Listing(entries=entries, skipped=1, path=path)


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMNISUS_CACHE_DIR", str(tmp_path / "cache"))


def test_cache_dir_honours_the_env_override(tmp_path: Path) -> None:
    assert cache_dir() == tmp_path / "cache"


def test_cache_dir_falls_back_to_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OMNISUS_CACHE_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert cache_dir() == tmp_path / "xdg" / "omnisus-db" / "inventory"


def test_cache_path_is_a_readable_slug_not_a_hash() -> None:
    p = cache_path(PATH)
    assert p.name == "dissemin_publicos_SIM_CID10_DORES.parquet"
    assert p.parent == cache_dir()


def test_distinct_remote_paths_get_distinct_files() -> None:
    assert cache_path("/a/b") != cache_path("/a/c")


def test_write_then_read_roundtrips_entries_and_skipped() -> None:
    original = _listing()
    write_cache(original)
    got = read_cached(PATH)
    assert got is not None
    assert got.path == original.path
    assert got.skipped == original.skipped
    assert [e.name for e in got.entries] == [e.name for e in original.entries]
    assert got.entries[0].size_bytes == original.entries[0].size_bytes
    assert got.entries[0].modified == original.entries[0].modified
    assert got.entries[0].is_dir is False


def test_miss_returns_none() -> None:
    assert read_cached("/never/listed") is None


def test_entry_older_than_the_ttl_is_a_miss() -> None:
    write_cache(_listing())
    assert read_cached(PATH, ttl_hours=0) is None


def test_entry_within_the_ttl_is_a_hit() -> None:
    write_cache(_listing())
    assert read_cached(PATH, ttl_hours=24) is not None


def test_corrupt_file_is_a_miss_never_an_error() -> None:
    """The cache is never authoritative (spec I8)."""
    write_cache(_listing())
    cache_path(PATH).write_bytes(b"not a parquet file")
    assert read_cached(PATH) is None


def test_write_is_atomic_and_leaves_no_temp_files() -> None:
    write_cache(_listing())
    leftovers = [p.name for p in cache_dir().iterdir() if not p.name.endswith(".parquet")]
    assert leftovers == []


def test_rewrite_replaces_rather_than_appends() -> None:
    write_cache(_listing(n=2))
    write_cache(_listing(n=5))
    got = read_cached(PATH)
    assert got is not None
    assert len(got.entries) == 5


def test_large_sizes_survive_the_roundtrip() -> None:
    big = Listing(
        entries=(
            FtpEntry(
                name="base_aih1.duck",
                path=f"{PATH}/base_aih1.duck",
                parent=PATH,
                is_dir=False,
                size_bytes=12_000_440_320,
                modified=datetime(2026, 6, 7, 13, 54),
            ),
        ),
        skipped=0,
        path=PATH,
    )
    write_cache(big)
    got = read_cached(PATH)
    assert got is not None
    assert got.entries[0].size_bytes == 12_000_440_320


def test_empty_listing_roundtrips_as_empty_not_as_a_miss() -> None:
    """An empty directory is a real answer and must cache as one (I6)."""
    write_cache(Listing(entries=(), skipped=0, path=PATH))
    got = read_cached(PATH)
    assert got is not None
    assert got.entries == ()


def test_empty_listing_still_expires_with_the_ttl() -> None:
    """A zero-row frame has no fetched_at value; staleness must fall back to
    the file mtime, or an empty cached directory would never expire."""
    write_cache(Listing(entries=(), skipped=0, path=PATH))
    assert read_cached(PATH, ttl_hours=0) is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_inventory_cache.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'omnisus_db.sources.datasus_ftp._cache'`.

- [ ] **Step 3: Implement the cache**

Create `src/omnisus_db/sources/datasus_ftp/_cache.py`:

```python
"""Persistence for the FTP inventory (spec §4.4).

One Parquet per listed directory, named from the slugified remote path so
``ls`` is debuggable. Staleness lives in a ``fetched_at`` column inside the
file — there is no sidecar metadata to desynchronise.

The cache is never authoritative (spec I8): anything unreadable is a miss,
never an error. It knows nothing about FTP.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import structlog

from omnisus_db.sources.datasus_ftp.inventory import FtpEntry, Listing

logger = structlog.get_logger(__name__)

_SLUG_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def cache_dir() -> Path:
    """Directory holding cached listings.

    ``OMNISUS_CACHE_DIR`` wins; otherwise ``${XDG_CACHE_HOME:-~/.cache}``.
    """
    override = os.environ.get("OMNISUS_CACHE_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "omnisus-db" / "inventory"


def cache_path(remote_path: str) -> Path:
    """Cache file for one remote directory, named from a readable slug."""
    slug = _SLUG_UNSAFE.sub("_", remote_path.strip("/")) or "root"
    return cache_dir() / f"{slug}.parquet"


def write_cache(listing: Listing) -> Path:
    """Persist a listing atomically. Returns the file written."""
    target = cache_path(listing.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).replace(tzinfo=None)
    frame = pl.DataFrame(
        {
            "name": [e.name for e in listing.entries],
            "path": [e.path for e in listing.entries],
            "parent": [e.parent for e in listing.entries],
            "is_dir": [e.is_dir for e in listing.entries],
            "size_bytes": [e.size_bytes for e in listing.entries],
            "modified": [e.modified for e in listing.entries],
        },
        schema={
            "name": pl.Utf8,
            "path": pl.Utf8,
            "parent": pl.Utf8,
            "is_dir": pl.Boolean,
            "size_bytes": pl.Int64,
            "modified": pl.Datetime("us"),
        },
    ).with_columns(
        pl.lit(listing.path).alias("listing_path"),
        pl.lit(listing.skipped).cast(pl.Int64).alias("skipped"),
        pl.lit(now).cast(pl.Datetime("us")).alias("fetched_at"),
    )
    tmp = target.with_suffix(".parquet.tmp")
    frame.write_parquet(tmp, compression="zstd")
    os.replace(tmp, target)
    return target


def read_cached(remote_path: str, *, ttl_hours: float = 24.0) -> Listing | None:
    """Return the cached listing, or ``None`` on miss, stale or unreadable.

    Never raises: a corrupt cache is a miss (spec I8).
    """
    target = cache_path(remote_path)
    try:
        frame = pl.read_parquet(target)
    except Exception as exc:  # noqa: BLE001 — any failure is a cache miss (I8)
        if target.exists():
            logger.warning("inventory.cache_unreadable", path=str(target), error=str(exc))
        return None
    try:
        # A zero-row frame carries no fetched_at value, so an empty directory's
        # staleness comes from the file's mtime. Without this an empty cached
        # listing would never expire.
        fetched_at = frame.get_column("fetched_at").max() if frame.height else None
        if fetched_at is None:
            fetched_at = datetime.fromtimestamp(target.stat().st_mtime)  # noqa: DTZ006
        if datetime.now(UTC).replace(tzinfo=None) - fetched_at > timedelta(hours=ttl_hours):
            return None
        skipped = int(frame.get_column("skipped").max() or 0) if frame.height else 0
        entries = tuple(
            FtpEntry(
                name=row["name"],
                path=row["path"],
                parent=row["parent"],
                is_dir=row["is_dir"],
                size_bytes=int(row["size_bytes"]),
                modified=row["modified"],
            )
            for row in frame.iter_rows(named=True)
        )
    except Exception as exc:  # noqa: BLE001 — malformed cache is a miss (I8)
        logger.warning("inventory.cache_malformed", path=str(target), error=str(exc))
        return None
    return Listing(entries=entries, skipped=skipped, path=remote_path)
```

Note on the empty-listing case: an empty directory is a real answer (I6), so
it must cache as a hit with `entries=()` — but a zero-row frame carries no
`fetched_at` value, so its staleness falls back to the file's mtime. Without
that fallback an empty cached listing would never expire. `write_cache` also
keeps `listing_path` for debuggability, even though `read_cached` takes the
path from its argument.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_inventory_cache.py -v`
Expected: all 14 pass. If either empty-listing test fails because a zero-row frame loses its columns, adjust `write_cache` to always emit the declared schema — do not change the test.

- [ ] **Step 5: Commit**

```bash
git add src/omnisus_db/sources/datasus_ftp/_cache.py tests/unit/sources/datasus_ftp/test_inventory_cache.py
git commit -m "feat(inventory): Parquet listing cache, never authoritative

One Parquet per directory under \${XDG_CACHE_HOME:-~/.cache}/omnisus-db,
slug-named so ls is debuggable, TTL in a fetched_at column inside the file,
atomic temp+replace. Corrupt or missing is a miss, never an error (spec
§4.4, I8). DuckDB can read these directly.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: `list_dir_cached`, `crawl`, `available`

**Files:**
- Modify: `src/omnisus_db/sources/datasus_ftp/inventory.py`
- Test: `tests/unit/sources/datasus_ftp/test_available.py`

**Interfaces:**
- Consumes: `list_dir` (Task 4), `_cache.read_cached`/`write_cache` (Task 5), `filenames.decode` (Task 2), `datasets.resolve` (merged).
- Produces:
  - `inventory.list_dir_cached(path, *, refresh=False, ttl_hours=24.0, **list_kwargs) -> Listing`
  - `inventory.crawl(path, *, depth=1, refresh=False) -> Iterator[FtpEntry]`
  - `inventory.available(dataset: str | Dataset, *, years=None, refresh=False) -> list[ScopeKey]`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/sources/datasus_ftp/test_available.py`:

```python
"""crawl (open-world) and available (registry-decoded) — spec §4.1.

Same primitive underneath; the only difference is whether filenames get
decoded. Patched at _blocking_list. No network.
"""

from __future__ import annotations

import ftplib
from pathlib import Path
from unittest.mock import patch

import pytest

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import REGISTRY
from omnisus_db.sources.datasus_ftp.inventory import available, crawl, list_dir_cached

SIM_DIR = REGISTRY["sim_do"].ftp_dir
SIA_DIR = REGISTRY["sia_bi"].ftp_dir


def _file(name: str, when: str = "01-31-20  02:48PM", size: int = 76107) -> str:
    return f"{when}         {size:>12} {name}"


def _dir(name: str, when: str = "02-24-18  07:38AM") -> str:
    return f"{when}       <DIR>          {name}"


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMNISUS_CACHE_DIR", str(tmp_path / "cache"))


# --- available -------------------------------------------------------------


def test_available_decodes_scopes_for_the_requested_dataset() -> None:
    lines = [_file("DOAC1996.dbc"), _file("DOAC1997.dbc"), _file("DOSP2024.dbc")]
    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", return_value=lines):
        scopes = available("sim_do")
    assert ScopeKey(uf="AC", ano=1996) in scopes
    assert ScopeKey(uf="SP", ano=2024) in scopes
    assert len(scopes) == 3


def test_available_filters_out_other_datasets_sharing_the_directory() -> None:
    """SIASUS/200801_/Dados holds BI, AM, AQ, ATD... available('sia_bi') must
    return only BI scopes."""
    lines = [
        _file("BIRR2401.dbc"),
        _file("AMRR2401.dbc"),
        _file("ATDRR2401.dbc"),
        _file("BIRR2402.dbc"),
    ]
    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", return_value=lines):
        scopes = available("sia_bi")
    assert scopes == [
        ScopeKey(uf="RR", ano=2024, mes=1),
        ScopeKey(uf="RR", ano=2024, mes=2),
    ]


def test_available_skips_undecodable_names_without_raising() -> None:
    lines = [_file("DOAC1996.dbc"), _file("readme.txt"), _file("PARR2401.dbc"), _dir("OLD")]
    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", return_value=lines):
        scopes = available("sim_do")
    assert scopes == [ScopeKey(uf="AC", ano=1996)]


def test_available_filters_by_years() -> None:
    lines = [_file("DOAC1996.dbc"), _file("DOAC2020.dbc"), _file("DOAC2024.dbc")]
    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", return_value=lines):
        scopes = available("sim_do", years=range(2020, 2025))
    assert [s.ano for s in scopes] == [2020, 2024]


def test_available_returns_sorted_scopes() -> None:
    lines = [_file("DOSP2024.dbc"), _file("DOAC1996.dbc"), _file("DOAC2020.dbc")]
    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", return_value=lines):
        scopes = available("sim_do")
    assert scopes == sorted(scopes, key=lambda s: (s.ano, s.uf, s.mes or 0))


def test_available_accepts_an_alias() -> None:
    with patch(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list",
        return_value=[_file("DOAC1996.dbc")],
    ):
        assert available("sim") == [ScopeKey(uf="AC", ano=1996)]


def test_available_empty_directory_returns_empty_list() -> None:
    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", return_value=[]):
        assert available("sim_do") == []


# --- caching ---------------------------------------------------------------


def test_second_call_is_served_from_cache_without_hitting_the_network() -> None:
    with patch(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list",
        return_value=[_file("DOAC1996.dbc")],
    ) as spy:
        available("sim_do")
        available("sim_do")
    assert spy.call_count == 1


def test_refresh_bypasses_the_cache() -> None:
    with patch(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list",
        return_value=[_file("DOAC1996.dbc")],
    ) as spy:
        available("sim_do")
        available("sim_do", refresh=True)
    assert spy.call_count == 2


def test_list_dir_cached_writes_the_cache_file() -> None:
    from omnisus_db.sources.datasus_ftp._cache import cache_path

    with patch(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list",
        return_value=[_file("DOAC1996.dbc")],
    ):
        list_dir_cached(SIM_DIR)
    assert cache_path(SIM_DIR).exists()


# --- crawl -----------------------------------------------------------------


def test_crawl_depth_one_does_not_recurse() -> None:
    lines = [_file("DOAC1996.dbc"), _dir("SUBDIR")]
    with patch(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list", return_value=lines
    ) as spy:
        entries = list(crawl(SIM_DIR, depth=1))
    assert spy.call_count == 1
    assert {e.name for e in entries} == {"DOAC1996.dbc", "SUBDIR"}


def test_crawl_depth_two_descends_once() -> None:
    def by_path(path: str, _timeout: float) -> list[str]:
        if path == SIM_DIR:
            return [_dir("SUB")]
        if path == f"{SIM_DIR}/SUB":
            return [_file("DOAC1996.dbc"), _dir("DEEPER")]
        raise AssertionError(f"crawl went too deep: {path}")

    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", side_effect=by_path):
        names = {e.name for e in crawl(SIM_DIR, depth=2)}
    assert names == {"SUB", "DOAC1996.dbc", "DEEPER"}


def test_crawl_is_lazy() -> None:
    """A generator, so a huge tree can be interrupted (I7)."""
    with patch(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list",
        return_value=[_file("DOAC1996.dbc")],
    ) as spy:
        it = crawl(SIM_DIR, depth=1)
        assert spy.call_count == 0
        next(it)
        assert spy.call_count == 1


def test_crawl_rejects_non_positive_depth() -> None:
    with pytest.raises(ValueError, match="depth"):
        list(crawl(SIM_DIR, depth=0))


def test_crawl_skips_unreadable_subdirectories_but_yields_the_rest() -> None:
    """A denied subtree must not truncate the walk: the directory entry is
    still yielded and its siblings are still listed."""

    def by_path(path: str, _timeout: float) -> list[str]:
        if path == SIA_DIR:
            return [_dir("OK"), _dir("DENIED")]
        if path == f"{SIA_DIR}/OK":
            return [_file("BIRR2401.dbc")]
        raise ftplib.error_perm("550 denied")

    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", side_effect=by_path):
        names = {e.name for e in crawl(SIA_DIR, depth=2)}
    assert names == {"OK", "DENIED", "BIRR2401.dbc"}


def test_crawl_raises_when_the_root_itself_is_missing() -> None:
    def boom(*_a: object, **_k: object) -> list[str]:
        raise ftplib.error_perm("550 nope")

    from omnisus_db.sources.datasus_ftp.inventory import FtpPathNotFound

    with patch("omnisus_db.sources.datasus_ftp.inventory._blocking_list", side_effect=boom):
        with pytest.raises(FtpPathNotFound):
            list(crawl("/nope", depth=1))
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_available.py -q`
Expected: FAIL — `ImportError: cannot import name 'available'`.

- [ ] **Step 3: Implement the three layers**

Add to `inventory.py`'s imports:

```python
from collections.abc import Iterable, Iterator

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import Dataset, resolve
from omnisus_db.sources.datasus_ftp.filenames import decode
```

Import the cache lazily inside the functions to avoid a circular import
(`_cache` imports `FtpEntry`/`Listing` from this module).

Append:

```python
def list_dir_cached(
    path: str,
    *,
    refresh: bool = False,
    ttl_hours: float = 24.0,
    timeout_seconds: float = 60.0,
    max_retries: int = 3,
) -> Listing:
    """:func:`list_dir` with the Parquet cache in front of it.

    The cache is never authoritative (spec I8): a miss, a stale entry or an
    unreadable file all fall through to the network.
    """
    from omnisus_db.sources.datasus_ftp import _cache

    if not refresh:
        cached = _cache.read_cached(path, ttl_hours=ttl_hours)
        if cached is not None:
            logger.debug("inventory.cache_hit", path=path, entries=len(cached.entries))
            return cached
    listing = list_dir(path, timeout_seconds=timeout_seconds, max_retries=max_retries)
    _cache.write_cache(listing)
    return listing


def crawl(path: str, *, depth: int = 1, refresh: bool = False) -> Iterator[FtpEntry]:
    """Walk a remote subtree, yielding entries as they are found.

    Open-world: any path, no decoding, so it reaches families this package
    does not model (SINAN, CIHA, PCE). ``depth=1`` lists ``path`` only.
    Recursion is bounded by ``depth`` and the walk is sequential — no queue,
    no pool (spec §4.1, I7).

    A subdirectory that cannot be listed is logged and skipped; the entry for
    the directory itself is still yielded, so a denied subtree never silently
    truncates the walk.
    """
    if depth < 1:
        raise ValueError(f"depth must be >= 1; got {depth}")
    frontier: list[tuple[str, int]] = [(path, depth)]
    while frontier:
        current, remaining = frontier.pop(0)
        try:
            listing = list_dir_cached(current, refresh=refresh)
        except (FtpPathNotFound, FtpUnavailable) as exc:
            if current == path:
                raise
            logger.warning("inventory.crawl_skipped", path=current, error=str(exc))
            continue
        for entry in listing.entries:
            yield entry
            if entry.is_dir and remaining > 1:
                frontier.append((entry.path, remaining - 1))


def available(
    dataset: str | Dataset,
    *,
    years: Iterable[int] | None = None,
    refresh: bool = False,
) -> list[ScopeKey]:
    """Scopes DATASUS actually publishes for ``dataset``, newest last.

    Closed-world counterpart to :func:`crawl`: the same listing, with each
    filename decoded through the registry. Names belonging to other datasets
    in the same directory — SIASUS/200801_/Dados holds ``PA*`` and ``SAD*``
    alongside the APAC family — are skipped, not raised on.

    This is the planner's input (spec §5.1) and the Tier 3 oracle (spec §6).
    """
    d = resolve(dataset)
    wanted = set(years) if years is not None else None
    listing = list_dir_cached(d.ftp_dir, refresh=refresh)
    scopes: list[ScopeKey] = []
    for entry in listing.files:
        decoded = decode(entry.name)
        if decoded is None:
            continue
        scope, name = decoded
        if name != d.name:
            continue
        if wanted is not None and scope.ano not in wanted:
            continue
        scopes.append(scope)
    scopes.sort(key=lambda s: (s.ano, s.uf, s.mes or 0))
    logger.info("inventory.available", dataset=d.name, scopes=len(scopes))
    return scopes
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_available.py -v`
Expected: all 16 pass.

- [ ] **Step 5: Run the whole datasus_ftp suite**

Run: `uv run pytest tests/unit/sources/datasus_ftp -q`
Expected: all pass, no import cycles.

- [ ] **Step 6: Commit**

```bash
git add src/omnisus_db/sources/datasus_ftp/inventory.py tests/unit/sources/datasus_ftp/test_available.py
git commit -m "feat(inventory): list_dir_cached, crawl and available

One mechanism, two levels of interpretation: crawl is open-world (any path,
reaching SINAN/CIHA/PCE), available decodes through the registry and filters
to one dataset. The oracle path never recurses — the registry names the
eleven directories that matter (spec §4.1).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Public surface — `odb.available`, `odb.browse`, `omnisus-db inventory`

**Files:**
- Modify: `src/omnisus_db/__init__.py`
- Modify: `src/omnisus_db/cli/main.py`
- Create: `tests/unit/cli/test_inventory_cmd.py`
- Modify: `tests/unit/test_public_api.py`

**Interfaces:**
- Consumes: `available`, `crawl`, `FtpEntry`, `FtpPathNotFound`, `FtpUnavailable` (Tasks 3–6).
- Produces: `odb.available`, `odb.browse`, `odb.FtpEntry`, `odb.FtpPathNotFound`, `odb.FtpUnavailable`; CLI `omnisus-db inventory`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_public_api.py`:

```python
def test_available_and_browse_are_exported() -> None:
    import omnisus_db as odb

    for name in ("available", "browse", "FtpEntry", "FtpPathNotFound", "FtpUnavailable"):
        assert name in odb.__all__, name
        assert hasattr(odb, name), name


def test_available_needs_no_lake(monkeypatch, tmp_path: Path) -> None:
    """Discovery is decoupled from the lake — it works before `init` (spec §4.4)."""
    import omnisus_db as odb

    monkeypatch.setenv("OMNISUS_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list",
        lambda _p, _t: ["01-31-20  02:48PM                76107 DOAC1996.dbc"],
    )
    assert odb.available("sim_do") == [ScopeKey(uf="AC", ano=1996)]
    assert not list(tmp_path.glob("*.ducklake"))
```

Create `tests/unit/cli/test_inventory_cmd.py`:

```python
"""omnisus-db inventory (spec §4.5)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from omnisus_db.cli.main import app

runner = CliRunner()

LINES = [
    "01-31-20  02:48PM                76107 DOAC1996.dbc",
    "12-23-25  03:48PM               874197 DOTO2024.dbc",
    "02-24-18  07:38AM       <DIR>          OLD",
]


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMNISUS_CACHE_DIR", str(tmp_path / "cache"))


def _patch(monkeypatch: pytest.MonkeyPatch, lines: list[str] | None = None) -> None:
    monkeypatch.setattr(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list",
        lambda _p, _t: LINES if lines is None else lines,
    )


def test_inventory_dataset_lists_available_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    result = runner.invoke(app, ["inventory", "sim_do"])
    assert result.exit_code == 0, result.output
    assert "AC" in result.output
    assert "1996" in result.output


def test_inventory_accepts_an_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    assert runner.invoke(app, ["inventory", "sim"]).exit_code == 0


def test_inventory_path_browses_any_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Open-world: a path we have no dictionary for still lists."""
    _patch(monkeypatch)
    result = runner.invoke(app, ["inventory", "--path", "/dissemin/publicos/SINAN"])
    assert result.exit_code == 0, result.output
    assert "DOAC1996.dbc" in result.output
    assert "OLD" in result.output


def test_inventory_requires_exactly_one_of_dataset_or_path() -> None:
    both = runner.invoke(app, ["inventory", "sim_do", "--path", "/x"])
    assert both.exit_code != 0
    neither = runner.invoke(app, ["inventory"])
    assert neither.exit_code != 0


def test_inventory_unknown_dataset_lists_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    result = runner.invoke(app, ["inventory", "bogus"])
    assert result.exit_code != 0
    assert "unknown dataset" in result.output


def test_inventory_reports_a_missing_path_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    import ftplib

    def boom(_p: str, _t: float) -> list[str]:
        raise ftplib.error_perm("550 The system cannot find the file specified.")

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp.inventory._blocking_list", boom)
    result = runner.invoke(app, ["inventory", "--path", "/nope"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_inventory_appears_in_top_level_help() -> None:
    assert "inventory" in runner.invoke(app, ["--help"]).output
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/cli/test_inventory_cmd.py tests/unit/test_public_api.py -q`
Expected: FAIL — no `inventory` command; `available` not in `odb.__all__`.

- [ ] **Step 3: Export from the package**

In `src/omnisus_db/__init__.py`, add to the imports:

```python
from omnisus_db.sources.datasus_ftp.inventory import (
    FtpEntry,
    FtpPathNotFound,
    FtpUnavailable,
    available,
)
from omnisus_db.sources.datasus_ftp.inventory import crawl as _crawl
```

and define, next to `scopes_for`:

```python
def browse(path: str, *, depth: int = 1, refresh: bool = False) -> list[FtpEntry]:
    """List any DATASUS FTP path — the open-world counterpart to :func:`available`.

    Reaches subsystems this package does not model (SINAN, CIHA, PCE).
    ``depth=1`` lists ``path`` only; recursion is bounded (spec §4.1).
    """
    return list(_crawl(path, depth=depth, refresh=refresh))
```

Add `"FtpEntry", "FtpPathNotFound", "FtpUnavailable", "available", "browse"` to `__all__`, keeping it sorted.

- [ ] **Step 4: Add the CLI command**

In `src/omnisus_db/cli/main.py`, after the `import` command, add:

```python
@app.command()
def inventory(
    dataset: str | None = typer.Argument(
        None, help=f"One of: {', '.join(dataset_choices())}. Omit when using --path."
    ),
    path: str | None = typer.Option(
        None, "--path", "-p", help="Browse any FTP path instead (e.g. /dissemin/publicos/SINAN)"
    ),
    depth: int = typer.Option(1, "--depth", "-d", help="Recursion depth for --path"),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass the 24h listing cache"),
) -> None:
    """Show what DATASUS actually publishes, from a cached FTP listing."""
    from rich.table import Table as RichTable

    import omnisus_db as odb
    from omnisus_db.sources.datasus_ftp.datasets import resolve
    from omnisus_db.sources.datasus_ftp.inventory import FtpPathNotFound, FtpUnavailable

    if (dataset is None) == (path is None):
        raise typer.BadParameter("provide exactly one of DATASET or --path")

    try:
        if path is not None:
            entries = odb.browse(path, depth=depth, refresh=refresh)
            table = RichTable("Name", "Type", "Size", "Modified")
            for e in entries:
                table.add_row(
                    e.name,
                    "dir" if e.is_dir else "file",
                    "" if e.is_dir else f"{e.size_bytes:,}",
                    e.modified.strftime("%Y-%m-%d %H:%M"),
                )
            console.print(table)
            console.print(f"[dim]{len(entries)} entry(ies) under {path}[/dim]")
            return
        try:
            d = resolve(dataset)
        except ValueError as exc:
            raise typer.BadParameter(f"{exc}. Choose from: {', '.join(dataset_choices())}") from exc
        scopes = odb.available(d, refresh=refresh)
        table = RichTable("UF", "Ano", "Mês")
        for s in scopes:
            table.add_row(s.uf, str(s.ano), "" if s.mes is None else f"{s.mes:02d}")
        console.print(table)
        console.print(f"[dim]{len(scopes)} scope(s) available for {d.name}[/dim]")
    except FtpPathNotFound as exc:
        console.print(f"[red]x[/red] not found on the server: {exc}")
        raise typer.Exit(code=1) from exc
    except FtpUnavailable as exc:
        console.print(f"[red]x[/red] DATASUS FTP unreachable: {exc}")
        raise typer.Exit(code=1) from exc
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/unit/cli tests/unit/test_public_api.py -q`
Expected: all pass.

Note: `omnisus-db inventory` for a dataset with many UFs prints a long table;
that is acceptable — `query` already prints up to 200 rows.

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check src tests && uv run ruff format --check src tests
git add src/omnisus_db/__init__.py src/omnisus_db/cli/main.py tests/unit/cli/test_inventory_cmd.py tests/unit/test_public_api.py
git commit -m "feat(cli): omnisus-db inventory; export available and browse

available() is registry-decoded, browse() is open-world; both come from one
listing primitive and need no lake (spec §4.5).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Tier 2 (c), the Tier 3 probe, and `probe.yml`

**Files:**
- Modify: `tests/unit/test_registry_consistency.py`
- Create: `tests/integration/test_registry_probe.py`
- Create: `.github/workflows/probe.yml`

**Interfaces:**
- Consumes: `available` (Task 6), `REGISTRY` (merged).
- Produces: nothing importable — guards.

- [ ] **Step 1: Add Tier 2 (c)**

Append to `tests/unit/test_registry_consistency.py`:

```python
def test_c_available_accepts_exactly_the_registry(monkeypatch, tmp_path) -> None:
    """Tier 2 (c), spec §6: available() accepts every registry key and alias,
    and rejects everything else. Offline — the listing is stubbed."""
    from omnisus_db.sources.datasus_ftp.datasets import ALIASES, REGISTRY
    from omnisus_db.sources.datasus_ftp.inventory import available

    monkeypatch.setenv("OMNISUS_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list", lambda _p, _t: []
    )
    for name in (*REGISTRY, *ALIASES):
        assert available(name) == [], name
    with pytest.raises(ValueError, match="unknown dataset"):
        available("definitely_not_a_dataset")
```

Add `import pytest` at the top if absent.

- [ ] **Step 2: Write the Tier 3 probe**

Create `tests/integration/test_registry_probe.py`:

```python
"""Tier 3 (spec §6): every registry row, checked against the live server.

Internal agreement is necessary and insufficient — if a row's ftp_dir or
prefix is wrong, every derived surface is consistently wrong. Only this tier
can catch that, and only it detects a DATASUS reorganisation.

Network-bound and upstream-flaky, so it runs on a schedule, never on a PR.

Marked BOTH ``integration`` and ``e2e`` deliberately. CI runs
``-m "not e2e and not perf"``, which does *not* deselect ``integration`` — so
``integration`` alone would put eleven live FTP listings on every pull
request. ``e2e`` is described in pyproject as "slow, manual/cron", which is
exactly this, and it is already deselected. ``probe.yml`` selects with
``-m integration``, which matches regardless of the second marker.

    uv run pytest tests/integration/test_registry_probe.py -m integration

A failure here is a finding about the registry or the server — never a
reason to loosen an assertion.
"""

from __future__ import annotations

import pytest

from omnisus_db.sources.datasus_ftp.datasets import REGISTRY, Dataset
from omnisus_db.sources.datasus_ftp.filenames import decode
from omnisus_db.sources.datasus_ftp.inventory import Listing, list_dir

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

ROWS = [pytest.param(d, id=name) for name, d in sorted(REGISTRY.items())]


@pytest.fixture(scope="module")
def listings() -> dict[str, Listing]:
    """One live LIST per distinct ftp_dir — the SIA rows share a directory."""
    cache: dict[str, Listing] = {}
    for d in REGISTRY.values():
        if d.ftp_dir not in cache:
            cache[d.ftp_dir] = list_dir(d.ftp_dir, timeout_seconds=120.0)
    return cache


@pytest.mark.parametrize("d", ROWS)
def test_ftp_dir_exists_and_parses_cleanly(d: Dataset, listings: dict[str, Listing]) -> None:
    listing = listings[d.ftp_dir]
    assert listing.entries, f"{d.name}: {d.ftp_dir} listed empty"
    assert listing.skipped == 0, (
        f"{d.name}: {listing.skipped} unparseable LIST lines in {d.ftp_dir} — "
        "the MS-DOS parser or the server format changed"
    )


@pytest.mark.parametrize("d", ROWS)
def test_directory_holds_files_with_this_prefix(
    d: Dataset, listings: dict[str, Listing]
) -> None:
    listing = listings[d.ftp_dir]
    mine = [
        e
        for e in listing.files
        if (decoded := decode(e.name)) is not None and decoded[1] == d.name
    ]
    assert mine, (
        f"{d.name}: no file in {d.ftp_dir} decodes to this dataset — "
        f"prefix {d.prefix!r} or ftp_dir is wrong"
    )


@pytest.mark.parametrize("d", ROWS)
def test_coverage_matches_the_earliest_published_file(
    d: Dataset, listings: dict[str, Listing]
) -> None:
    """coverage[0] must be what the server actually publishes first.

    If this fails, fix the row (or investigate a DATASUS reorganisation) —
    do not widen the assertion.
    """
    listing = listings[d.ftp_dir]
    scopes = [
        decoded[0]
        for e in listing.files
        if (decoded := decode(e.name)) is not None and decoded[1] == d.name
    ]
    assert scopes, f"{d.name}: nothing decoded"
    earliest = min((s.ano, s.mes or 1) for s in scopes)
    assert earliest == d.coverage[0], (
        f"{d.name}: registry says coverage starts {d.coverage[0]}, "
        f"server's earliest file is {earliest}"
    )
```

- [ ] **Step 3: Run the probe once, manually**

Run: `uv run pytest tests/integration/test_registry_probe.py -m integration -v`
Expected: 33 tests (11 rows × 3). `sim_do` is known-good — the earliest `DO*` file on the server is 1996, matching `coverage=((1996, 1), None)`.

If a row fails: **stop and report it.** That is the probe doing its job — the registry row or the server changed. Record the actual value in your report; do not edit the assertion or the row without the controller ruling on it.

- [ ] **Step 4: Add the scheduled workflow**

Create `.github/workflows/probe.yml`:

```yaml
name: probe

# Tier 3 (spec §6): validate every registry row against the live DATASUS
# server. Off the PR path — upstream is flaky and this is network-bound.
on:
  schedule:
    - cron: "17 6 * * 1"  # Mondays 06:17 UTC
  workflow_dispatch:

concurrency:
  group: probe
  cancel-in-progress: false

permissions:
  contents: read

jobs:
  probe:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - name: Setup Python
        run: uv python install 3.13
      - name: Sync deps
        run: uv sync --extra dev
      - name: Ground-truth probe against ftp.datasus.gov.br
        run: uv run pytest tests/integration/test_registry_probe.py -m integration -v
```

- [ ] **Step 5: Confirm the probe stays out of CI**

The CI command selects `integration` tests (it only deselects `e2e` and `perf`), which is why the probe carries the `e2e` marker too. Verify that mechanically:

```bash
uv run pytest -m "not e2e and not perf" --collect-only -q 2>&1 | grep -c "test_registry_probe" | tr -d ' '
```

Expected: `0` — the probe is not collected by the CI command.

```bash
uv run pytest tests/integration/test_registry_probe.py -m integration --collect-only -q 2>&1 | tail -2
```

Expected: 33 tests collected — `probe.yml`'s selection does reach them.

If the first command returns anything but `0`, stop and report: CI would hit DATASUS on every pull request.

- [ ] **Step 6: Commit**

```bash
git add tests/unit/test_registry_consistency.py tests/integration/test_registry_probe.py .github/workflows/probe.yml
git commit -m "test(tier3): ground-truth probe against the live DATASUS server

Validates every registry row's ftp_dir, prefix and coverage against
ftp.datasus.gov.br, plus Tier 2 (c). Weekly cron + workflow_dispatch, off
the PR path. The inventory is its own test harness (spec §6).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Delete the `Source` protocol; CHANGELOG; verification

Spec §1.4: *"if a source family still has no implementation once that lands, the method is removed from the protocol rather than left as an unmet promise (I5)."* `available()` is a module-level function, not a `Source` method, and no class in the codebase implements `Source`. It has never been implemented and this plan does not implement it — so it goes.

**Files:**
- Modify: `src/omnisus_db/sources/_base.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: everything above.
- Produces: a green tree.

- [ ] **Step 1: Confirm nothing implements or imports `Source`**

```bash
grep -rn "\bSource\b" src tests scripts
```

Expected: only the definition in `src/omnisus_db/sources/_base.py`. If anything else appears, stop and report.

- [ ] **Step 2: Delete it**

In `src/omnisus_db/sources/_base.py`, delete the `Source` class and the now-unused `from typing import Protocol` import. Update the module docstring's first line to:

```python
"""Shared value types for source families: ScopeKey and ImportResult."""
```

- [ ] **Step 3: Run the full suite**

Run: `uv run pytest -m "not e2e and not perf" -q`
Expected: all pass (275 from the kernel plan + roughly 60 added here).

- [ ] **Step 4: Update the CHANGELOG**

Under `## Unreleased`, add to `### Added`:

```markdown
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
```

to `### Changed`:

```markdown
- `sources.datasus_ftp.inventory` was a filename codec; it is now the actual
  inventory. The codec moved to `sources.datasus_ftp.filenames` with
  identical signatures, plus a non-raising `decode()`.
```

and to `### Removed`:

```markdown
- `sources._base.Source` — a protocol no class ever implemented. Discovery
  ships as `inventory.available()` / `inventory.crawl()` instead of a
  `Source` method, so the declaration was an unmet promise (spec I5).
```

- [ ] **Step 5: Lint, type-check, verify**

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy src   # advisory: expect the 3 known pre-existing errors, none new
uv run pytest -m "not e2e and not perf" -q
```

Report the mypy output. Fix only errors introduced by this plan's files; leave the three pre-existing ones (`dictionaries.py:34`, `fetch.py:64`, `operations.py:208`).

- [ ] **Step 6: Commit**

```bash
git add src/omnisus_db/sources/_base.py CHANGELOG.md
git commit -m "refactor(sources): delete the never-implemented Source protocol

Discovery ships as inventory.available()/crawl(), not as a Source method; no
class ever implemented the protocol, so the declaration was an unmet promise
(spec §1.4, I5). CHANGELOG records the inventory, the codec rename and this
removal.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Out of scope for this plan (next plans)

| Spec item | Plan |
|---|---|
| `ImportReport`/`ScopeOutcome`, per-scope tolerance, `coverage` pre-filtering, CLI exit status, `--plan` (which implies `refresh=True`), bounded fetch concurrency, `BEGIN…COMMIT` batching, the staging triple-read, `SET PARTITIONED BY` | Import & performance (§9 steps 6–7) |
| `uv sync --frozen`, mypy gate, `--cov-fail-under=80`, the wheel-only install gate and the `datasus-dbc` cp313 upstream fix, `release.yml`, generated `docs/datasets.md`, API reference page, CHANGELOG backfill | Infra (§9 step 8) |
| `Lake.optimize` calls `ducklake_compact_files`, which does not exist in the pinned DuckLake, and the CLI swallows the failure and exits 0 (an I6 violation) | Import & performance |
| `scripts/build_fixtures.py` hand-maintains an FTP path map covering 5 of 11 datasets — it should derive from `REGISTRY` | Infra |
| `load_dicionario(str)` joins into the package dir unguarded | Infra |
| Benchmarks re-run, tune M, ADR 0001 Rust gate re-evaluation | After steps 6–7 |

# DBC decompression inside omnisus-db — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `datasus-dbc` dependency with DBC decompression we own: a pure-Python decoder by default and the same decoder in the optional native package `omnisus-db-dbf`, so `omnisus-db` installs from wheels on Python 3.12, 3.13 and 3.14.

**Architecture:** Both decoders are altered ports of zlib's `contrib/blast/blast.c`. `datasus_ftp/dbc.py` selects the backend like the DBF reader does (`OMNISUS_DBC_BACKEND=python|rust|auto`) through one shared loader, `datasus_ftp/native.py`. The native crate gains `decompress_dbc`, `API_VERSION` 2 and `abi3` wheels. `omnisus-db` gains no dependency.

**Tech Stack:** Python 3.12+, structlog, Hypothesis, pytest; Rust 1.98.1, PyO3 0.29 (`abi3-py312`), Maturin 1.12.6, proptest; GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-13-dbc-nativo-design.md` — read §9 "Revisions after the spike"; it overrides §4.1, §4.2 and §5.

## Global Constraints

- No new third-party dependency, Python or Rust. `datasus-dbc` leaves `pyproject.toml` and `uv.lock`.
- `omnisus-db` does **not** depend on `omnisus-db-dbf`. The native package stays optional.
- Error messages, identical in both backends: `missing DBC header`, `DBC header size exceeds file size`, `corrupt DBC stream at byte N`, `truncated DBC stream at byte N` (N is the absolute offset in the DBC payload).
- Environment variable: `OMNISUS_DBC_BACKEND`; values `python`, `rust`, `auto` (default `auto`).
- Native `API_VERSION` becomes `2` in Task 3, in the crate and in every Python check at once.
- Speed hint threshold: `HINT_BYTES = 16 * 1024**2` of compressed input, only when the request was `auto` and Python decoded.
- No dead code: every removed name or import has zero remaining references (`grep` checks are part of the tasks).
- Historical records are never edited: `docs/superpowers/specs/*` and `plans/*` other than this plan's own spec, `docs/decisions/*`, `reports/*`.
- Ruff line length 99; `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src` pass after every task.
- Rust commands need `export PATH="/opt/homebrew/opt/rustup/bin:$PATH"` on this machine.
- Commit messages end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Gate hooks with `uv run pre-commit run --from-ref origin/main --to-ref HEAD`, never `--all-files`.
- Nothing contacts the DATASUS FTP.

## File map

| File | Responsibility |
|---|---|
| `src/omnisus_db/sources/datasus_ftp/native.py` (new) | Backend request validation and optional native module lookup, shared by DBF and DBC |
| `src/omnisus_db/sources/datasus_ftp/dbc.py` (new) | Pure-Python blast port, DBC framing, backend selection, `InvalidDbcError` |
| `src/omnisus_db/sources/datasus_ftp/dbf_batches.py` | Uses `native.py` instead of its own lookup |
| `src/omnisus_db/sources/datasus_ftp/parse.py`, `staging.py` | Decompression seam `parse.dbc.decompress_bytes` |
| `tests/fixtures/dbc/golden.json` (new) | Length and SHA-256 of `datasus-dbc` output for the 13 fixtures |
| `tests/fixtures/blast/` (new) | zlib's `test.pk`/`test.txt` vector and its notice |
| `tests/unit/sources/datasus_ftp/test_dbc.py`, `test_native.py` (new) | Decoder and loader tests |
| `native/omnisus-db-dbf/src/dbc.rs` (new) | Rust blast port and DBC framing |
| `native/omnisus-db-dbf/tests/dbc.rs` (new) | Rust vector, error and property tests |
| `native/omnisus-db-dbf/fuzz/fuzz_targets/dbc.rs` (new) | Fuzz target |
| `.github/workflows/{native,test,release}.yml` | abi3 wheel matrix; required install gates on 3.12–3.14 |

---

### Task 1: Python decoder, shared native loader and golden fixtures

**Files:**
- Create: `src/omnisus_db/sources/datasus_ftp/native.py`
- Create: `src/omnisus_db/sources/datasus_ftp/dbc.py`
- Modify: `src/omnisus_db/sources/datasus_ftp/dbf_batches.py` (the `Backend` alias and the lookup block in `open_dbf_batches`)
- Create: `tests/fixtures/dbc/golden.json`, `tests/fixtures/blast/test.pk`, `tests/fixtures/blast/test.txt`, `tests/fixtures/blast/README.md`
- Create: `tests/unit/sources/datasus_ftp/test_dbc.py`, `tests/unit/sources/datasus_ftp/test_native.py`
- Modify: `tests/unit/sources/datasus_ftp/test_dbf_backends.py`

**Interfaces:**
- Produces: `native.Backend = Literal["python", "rust", "auto"]`; `native.API_VERSION: int` (= 1 in this task); `native.requested_backend(backend: Backend | None, *, variable: str, label: str) -> str`; `native.load_native(requested: str) -> ModuleType | None`; `dbc.InvalidDbcError(ValueError)`; `dbc.decompress_bytes(raw: bytes, backend: Backend | None = None) -> bytes`; `dbc.HINT_BYTES: int`.

- [ ] **Step 1: Add the fixtures**

```bash
SCRATCH=/private/tmp/claude-501/-Users-raphael-PycharmProjects-omnisus-db/5f79a43d-72e8-4694-9cbc-77e949ec2350/scratchpad/blast
mkdir -p tests/fixtures/blast
cp "$SCRATCH/golden.json" tests/fixtures/dbc/golden.json
cp "$SCRATCH/test.pk" "$SCRATCH/test.txt" tests/fixtures/blast/
```

`golden.json` was produced with `datasus_dbc.decompress_bytes` 0.1.3 on the 13 `tests/fixtures/dbc/*.dbc` files before this plan. `test.pk` is 8 bytes (`00 04 82 24 25 8f 80 7f`); `test.txt` is the 13 bytes `AIAIAIAIAIAIA` with no newline. Check both with `xxd`.

Create `tests/fixtures/blast/README.md`:

```markdown
# blast test vector

`test.pk` and `test.txt` are copied unchanged from zlib `contrib/blast/test/`
(https://github.com/madler/zlib/tree/develop/contrib/blast). `test.pk` is a
PKWare DCL imploded stream that decompresses to `test.txt`. The DBC decoders
in `src/omnisus_db/sources/datasus_ftp/dbc.py` and
`native/omnisus-db-dbf/src/dbc.rs` are altered ports of `blast.c`, distributed
under this notice:

    Copyright (C) 2003, 2012, 2013 Mark Adler

    This software is provided 'as-is', without any express or implied
    warranty.  In no event will the author be held liable for any damages
    arising from the use of this software.

    Permission is granted to anyone to use this software for any purpose,
    including commercial applications, and to alter it and redistribute it
    freely, subject to the following restrictions:

    1. The origin of this software must not be misrepresented; you must not
       claim that you wrote the original software. If you use this software
       in a product, an acknowledgment in the product documentation would be
       appreciated but is not required.
    2. Altered source versions must be plainly marked as such, and must not be
       misrepresented as being the original software.
    3. This notice may not be removed or altered from any source distribution.
```

`tests/fixtures/dbf/manifest.json` pre-commit exclusions: run `uv run pre-commit run --files tests/fixtures/blast/test.pk tests/fixtures/blast/test.txt` and confirm neither file was rewritten (`xxd` again). If a hook changes them, add `tests/fixtures/blast/` to that hook's `exclude` in `.pre-commit-config.yaml`.

- [ ] **Step 2: Write the failing loader tests** — `tests/unit/sources/datasus_ftp/test_native.py`

```python
"""The optional native package is found, rejected or skipped, never silently misused."""

from types import SimpleNamespace

import pytest

from omnisus_db.sources.datasus_ftp import native


def missing(name):
    raise ModuleNotFoundError("module absent", name=name)


@pytest.mark.parametrize("value", ["python", "rust", "auto"])
def test_explicit_backend_wins_over_environment(monkeypatch, value):
    monkeypatch.setenv("OMNISUS_X_BACKEND", "typo")
    assert native.requested_backend(value, variable="OMNISUS_X_BACKEND", label="X") == value


def test_environment_then_auto(monkeypatch):
    monkeypatch.delenv("OMNISUS_X_BACKEND", raising=False)
    assert native.requested_backend(None, variable="OMNISUS_X_BACKEND", label="X") == "auto"
    monkeypatch.setenv("OMNISUS_X_BACKEND", "python")
    assert native.requested_backend(None, variable="OMNISUS_X_BACKEND", label="X") == "python"


def test_unknown_backend_names_the_capability(monkeypatch):
    monkeypatch.setenv("OMNISUS_X_BACKEND", "typo")
    with pytest.raises(ValueError, match="^X backend must be python, rust or auto$"):
        native.requested_backend(None, variable="OMNISUS_X_BACKEND", label="X")


def test_python_never_imports(monkeypatch):
    monkeypatch.setattr(native, "import_module", lambda _: pytest.fail("imported"))
    assert native.load_native("python") is None


def test_auto_without_package_is_none(monkeypatch):
    monkeypatch.setattr(native, "import_module", lambda _: missing("omnisus_db_dbf"))
    assert native.load_native("auto") is None


def test_rust_without_package_raises(monkeypatch):
    monkeypatch.setattr(native, "import_module", lambda _: missing("omnisus_db_dbf"))
    with pytest.raises(ImportError, match="omnisus-db-dbf"):
        native.load_native("rust")


def test_missing_transitive_dependency_is_not_hidden(monkeypatch):
    monkeypatch.setattr(native, "import_module", lambda _: missing("pyarrow"))
    with pytest.raises(ModuleNotFoundError):
        native.load_native("auto")


def test_incompatible_api_is_an_error_even_for_auto(monkeypatch):
    monkeypatch.setattr(native, "import_module", lambda _: SimpleNamespace(API_VERSION=99))
    with pytest.raises(ImportError, match=f"API_VERSION={native.API_VERSION}"):
        native.load_native("auto")


def test_compatible_module_is_returned(monkeypatch):
    module = SimpleNamespace(API_VERSION=native.API_VERSION)
    monkeypatch.setattr(native, "import_module", lambda _: module)
    assert native.load_native("rust") is module
```

- [ ] **Step 3: Run it to see it fail**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_native.py -q`
Expected: collection error, `cannot import name 'native'`.

- [ ] **Step 4: Implement** — `src/omnisus_db/sources/datasus_ftp/native.py`

```python
"""Optional ``omnisus-db-dbf`` lookup shared by the DBF reader and DBC decompressor."""

from __future__ import annotations

import os
from importlib import import_module
from types import ModuleType
from typing import Literal

Backend = Literal["python", "rust", "auto"]
API_VERSION = 1


def requested_backend(backend: Backend | None, *, variable: str, label: str) -> str:
    """The explicit backend, else the environment variable, else ``auto``."""
    requested = backend if backend is not None else os.environ.get(variable, "auto")
    if requested not in ("python", "rust", "auto"):
        raise ValueError(f"{label} backend must be python, rust or auto")
    return requested


def load_native(requested: str) -> ModuleType | None:
    """The native module, or None when Python decodes.

    Only ``auto`` tolerates an absent package. A missing transitive dependency or
    an incompatible API is always an error, never a silent fallback.
    """
    if requested == "python":
        return None
    try:
        native = import_module("omnisus_db_dbf")
    except ModuleNotFoundError as exc:
        if exc.name != "omnisus_db_dbf":
            raise
        if requested == "rust":
            raise ImportError("Rust backend requires the optional omnisus-db-dbf package") from exc
        return None
    if getattr(native, "API_VERSION", None) != API_VERSION:
        raise ImportError(f"Incompatible omnisus-db-dbf API; expected API_VERSION={API_VERSION}")
    return native
```

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_native.py -q` — Expected: 11 passed.

- [ ] **Step 5: Move `open_dbf_batches` onto the loader**

In `dbf_batches.py`: delete `import os`, `from importlib import import_module` and the `Backend = Literal[...]` line (drop `Literal` from the `typing` import if nothing else uses it); add `from omnisus_db.sources.datasus_ftp.native import Backend, load_native, requested_backend`. Replace everything from `requested = backend if ...` down to the end of the `if native is not None:` block (just before `actual = ...`) with:

```python
    requested = requested_backend(backend, variable="OMNISUS_DBF_BACKEND", label="DBF")
    native = load_native(requested)
    reader = None
    reason = "extension_not_installed" if native is None and requested == "auto" else None
    if native is not None:
        from omnisus_db.sources.datasus_ftp import parse

        try:
            reader = native.open_reader(
                parse._ensure_dbf_terminator(dbf_bytes),
                encoding=encoding,
                batch_rows=batch_rows,
            )
        except native.UnsupportedDbfError:
            if requested == "rust":
                raise
            reason = "unsupported_metadata"
        except native.InvalidDbfError as exc:
            raise DbfIntegrityError(str(exc)) from exc
```

In `test_dbf_backends.py`, patch the loader's import instead of the reader's: add `from omnisus_db.sources.datasus_ftp import native as native_loader`, change every `monkeypatch.setattr(module, "import_module", ...)` to `monkeypatch.setattr(native_loader, "import_module", ...)`, and in `fake_native` use `API_VERSION=native_loader.API_VERSION`. Delete `test_missing_transitive_dependency_does_not_fallback` and `test_incompatible_api_does_not_fallback` from this file: `test_native.py` now owns those cases.

Run: `uv run pytest tests/unit/sources/datasus_ftp -q -m "not e2e and not perf"` — Expected: all pass.

- [ ] **Step 6: Write the failing decoder tests** — `tests/unit/sources/datasus_ftp/test_dbc.py`

```python
"""DBC decompression: byte-exact with datasus-dbc output, never silent on bad input."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from omnisus_db.sources.datasus_ftp import dbc, native

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
GOLDEN = json.loads((FIXTURES / "dbc" / "golden.json").read_text(encoding="utf-8"))
VECTOR = (FIXTURES / "blast" / "test.pk").read_bytes()
BACKENDS = ["python"]


def framed(body: bytes) -> bytes:
    """A minimal DBC: a 10-byte pre-header declaring header_size=10, a CRC32, the body."""
    return bytes(8) + (10).to_bytes(2, "little") + bytes(4) + body


def outcome(raw: bytes, backend: str) -> bytes | str:
    try:
        return dbc.decompress_bytes(raw, backend=backend)
    except dbc.InvalidDbcError as exc:
        return str(exc)


def test_golden_covers_every_fixture():
    assert sorted(GOLDEN) == sorted(path.name for path in (FIXTURES / "dbc").glob("*.dbc"))


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_matches_datasus_dbc_output(backend, name):
    out = dbc.decompress_bytes((FIXTURES / "dbc" / name).read_bytes(), backend=backend)
    assert len(out) == GOLDEN[name]["length"]
    assert hashlib.sha256(out).hexdigest() == GOLDEN[name]["sha256"]


@pytest.mark.parametrize("backend", BACKENDS)
def test_zlib_blast_vector(backend):
    expected = (FIXTURES / "blast" / "test.txt").read_bytes()
    assert dbc.decompress_bytes(framed(VECTOR), backend=backend) == framed(b"")[:10] + expected


@pytest.mark.parametrize("backend", BACKENDS)
@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"", "missing DBC header"),
        (bytes(9), "missing DBC header"),
        (bytes(8) + (100).to_bytes(2, "little"), "DBC header size exceeds file size"),
        (framed(b"\x02\x04"), "corrupt DBC stream at byte 15"),
        (framed(b"\x00\x07"), "corrupt DBC stream at byte 16"),
    ],
)
def test_malformed_input_names_the_problem(backend, raw, message):
    assert outcome(raw, backend) == message


@pytest.mark.parametrize("backend", BACKENDS)
def test_every_truncation_is_reported_where_input_ends(backend):
    raw = framed(VECTOR)
    for end in range(14, len(raw)):
        assert outcome(raw[:end], backend) == f"truncated DBC stream at byte {end}"


@settings(max_examples=300, deadline=None)
@given(body=st.binary(max_size=2048), frame=st.booleans())
def test_arbitrary_bytes_decode_or_raise_invalid(body, frame):
    raw = framed(body) if frame else body
    assert isinstance(outcome(raw, "python"), bytes | str)


class Recorder:
    def __init__(self):
        self.events = []

    def debug(self, event, **fields):
        self.events.append(("debug", event, fields))

    def info(self, event, **fields):
        self.events.append(("info", event, fields))


class FakeInvalidDbcError(ValueError):
    pass


def fake_native(decompress):
    return SimpleNamespace(
        API_VERSION=native.API_VERSION,
        __version__="9.9.9",
        decompress_dbc=decompress,
        InvalidDbcError=FakeInvalidDbcError,
    )


def missing(_):
    raise ModuleNotFoundError("module absent", name="omnisus_db_dbf")


def test_unknown_backend_is_rejected(monkeypatch):
    monkeypatch.setenv("OMNISUS_DBC_BACKEND", "typo")
    with pytest.raises(ValueError, match="^DBC backend must be python, rust or auto$"):
        dbc.decompress_bytes(framed(VECTOR))


def test_auto_prefers_native_and_logs_it(monkeypatch):
    monkeypatch.delenv("OMNISUS_DBC_BACKEND", raising=False)
    monkeypatch.setattr(native, "import_module", lambda _: fake_native(lambda raw: b"native"))
    log = Recorder()
    monkeypatch.setattr(dbc, "logger", log)
    assert dbc.decompress_bytes(framed(VECTOR)) == b"native"
    assert log.events == [
        (
            "debug",
            "datasus_ftp.dbc_backend",
            {"backend": "rust", "requested": "auto", "version": "9.9.9", "fallback": None},
        )
    ]


def test_native_error_is_raised_as_invalid_dbc_error_without_python_retry(monkeypatch):
    def broken(raw):
        raise FakeInvalidDbcError("corrupt DBC stream at byte 3")

    monkeypatch.setattr(native, "import_module", lambda _: fake_native(broken))
    with pytest.raises(dbc.InvalidDbcError, match="^corrupt DBC stream at byte 3$"):
        dbc.decompress_bytes(b"", backend="rust")


def test_auto_without_package_decodes_in_python_and_says_why(monkeypatch):
    monkeypatch.setattr(native, "import_module", missing)
    log = Recorder()
    monkeypatch.setattr(dbc, "logger", log)
    assert dbc.decompress_bytes(framed(VECTOR), backend="auto").endswith(b"AIAIAIAIAIAIA")
    assert log.events == [
        (
            "debug",
            "datasus_ftp.dbc_backend",
            {
                "backend": "python",
                "requested": "auto",
                "version": None,
                "fallback": "extension_not_installed",
            },
        )
    ]


@pytest.mark.parametrize(("backend", "hinted"), [("auto", True), ("python", False)])
def test_speed_hint_only_when_python_was_not_chosen(monkeypatch, backend, hinted):
    monkeypatch.setattr(native, "import_module", missing)
    monkeypatch.setattr(dbc, "HINT_BYTES", 10)
    log = Recorder()
    monkeypatch.setattr(dbc, "logger", log)
    raw = framed(VECTOR)
    dbc.decompress_bytes(raw, backend=backend)
    hints = [fields for level, event, fields in log.events if level == "info"]
    assert hints == ([{"compressed_bytes": len(raw)}] if hinted else [])
```

- [ ] **Step 7: Run them to see them fail**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_dbc.py -q`
Expected: collection error, `cannot import name 'dbc'`.

- [ ] **Step 8: Implement** — `src/omnisus_db/sources/datasus_ftp/dbc.py`

```python
"""DATASUS DBC: a DBF header, a CRC32, then a PKWare DCL imploded body.

The decoder below is an altered port of Mark Adler's blast.c (zlib
contrib/blast, version 1.3). Altered: it reads an in-memory buffer, appends to a
growing output instead of a 4 KiB window, and raises InvalidDbcError instead of
returning codes. ``native/omnisus-db-dbf/src/dbc.rs`` carries the same port.
Original notice, from blast.h:

    Copyright (C) 2003, 2012, 2013 Mark Adler

    This software is provided 'as-is', without any express or implied
    warranty.  In no event will the author be held liable for any damages
    arising from the use of this software.

    Permission is granted to anyone to use this software for any purpose,
    including commercial applications, and to alter it and redistribute it
    freely, subject to the following restrictions:

    1. The origin of this software must not be misrepresented; you must not
       claim that you wrote the original software. If you use this software
       in a product, an acknowledgment in the product documentation would be
       appreciated but is not required.
    2. Altered source versions must be plainly marked as such, and must not be
       misrepresented as being the original software.
    3. This notice may not be removed or altered from any source distribution.
"""

from __future__ import annotations

import structlog

from omnisus_db.sources.datasus_ftp.native import Backend, load_native, requested_backend

logger = structlog.get_logger(__name__)

HINT_BYTES = 16 * 1024**2
"""Compressed size above which pure Python (about 10 MB of output per second) earns a hint."""

_MAXBITS = 13


class InvalidDbcError(ValueError):
    """The DBC payload is malformed or truncated."""


def _huffman(compact: bytes) -> tuple[list[int], list[int]]:
    """Canonical decoding tables (codes per length, symbols by length) from compact lengths.

    Each compact byte is a code length (low four bits) repeated (high four bits + 1) times.
    """
    lengths: list[int] = []
    for byte in compact:
        lengths += [byte & 15] * ((byte >> 4) + 1)
    count = [0] * (_MAXBITS + 1)
    for length in lengths:
        count[length] += 1
    offsets = [0] * (_MAXBITS + 1)
    for length in range(1, _MAXBITS):
        offsets[length + 1] = offsets[length] + count[length]
    symbols = [0] * len(lengths)
    for symbol, length in enumerate(lengths):
        if length:
            symbols[offsets[length]] = symbol
            offsets[length] += 1
    return count, symbols


_LITERAL = _huffman(
    bytes(
        [
            11, 124, 8, 7, 28, 7, 188, 13, 76, 4, 10, 8, 12, 10, 12, 10, 8, 23, 8,
            9, 7, 6, 7, 8, 7, 6, 55, 8, 23, 24, 12, 11, 7, 9, 11, 12, 6, 7, 22, 5,
            7, 24, 6, 11, 9, 6, 7, 22, 7, 11, 38, 7, 9, 8, 25, 11, 8, 11, 9, 12,
            8, 12, 5, 38, 5, 38, 5, 11, 7, 5, 6, 21, 6, 10, 53, 8, 7, 24, 10, 27,
            44, 253, 253, 253, 252, 252, 252, 13, 12, 45, 12, 45, 12, 61, 12, 45,
            44, 173,
        ]
    )
)  # fmt: skip
_LENGTH = _huffman(bytes([2, 35, 36, 53, 38, 23]))
_DISTANCE = _huffman(bytes([2, 20, 53, 230, 247, 151, 248]))
_LENGTH_BASE = (3, 2, 4, 5, 6, 7, 8, 9, 10, 12, 16, 24, 40, 72, 136, 264)
_LENGTH_EXTRA = (0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8)
_END = 519


def _explode(data: bytes, start: int) -> bytes:
    """Decode the imploded stream at ``data[start:]``; errors cite absolute offsets."""
    position = start
    buffer = 0
    available = 0

    def bits(need: int) -> int:
        # Bits are packed least significant first.
        nonlocal position, buffer, available
        while available < need:
            if position == len(data):
                raise InvalidDbcError(f"truncated DBC stream at byte {position}")
            buffer |= data[position] << available
            position += 1
            available += 8
        value = buffer & ((1 << need) - 1)
        buffer >>= need
        available -= need
        return value

    def decode(table: tuple[list[int], list[int]]) -> int:
        # Codes are stored bit-reversed and inverted relative to canonical order.
        count, symbols = table
        code = first = index = 0
        for length in range(1, _MAXBITS + 1):
            code |= bits(1) ^ 1
            if code < first + count[length]:
                return symbols[index + code - first]
            index += count[length]
            first = (first + count[length]) << 1
            code <<= 1
        raise InvalidDbcError(f"corrupt DBC stream at byte {position}")

    literals_coded = bits(8)
    if literals_coded > 1:
        raise InvalidDbcError(f"corrupt DBC stream at byte {position}")
    dictionary_bits = bits(8)
    if dictionary_bits not in (4, 5, 6):
        raise InvalidDbcError(f"corrupt DBC stream at byte {position}")
    out = bytearray()
    while True:
        if not bits(1):
            out.append(decode(_LITERAL) if literals_coded else bits(8))
            continue
        symbol = decode(_LENGTH)
        length = _LENGTH_BASE[symbol] + bits(_LENGTH_EXTRA[symbol])
        if length == _END:
            return bytes(out)
        shift = 2 if length == 2 else dictionary_bits
        distance = (decode(_DISTANCE) << shift) + bits(shift) + 1
        if distance > len(out):
            raise InvalidDbcError(f"corrupt DBC stream at byte {position}")
        source = len(out) - distance
        if distance >= length:
            out += out[source : source + length]
        else:
            # Overlapping copy: each new byte may be one this copy just wrote.
            for index in range(source, source + length):
                out.append(out[index])


def _python_decompress(raw: bytes) -> bytes:
    if len(raw) < 10:
        raise InvalidDbcError("missing DBC header")
    header_size = int.from_bytes(raw[8:10], "little")
    if header_size + 4 > len(raw):
        raise InvalidDbcError("DBC header size exceeds file size")
    # The 4 bytes after the header are a CRC32 that DATASUS readers ignore.
    return raw[:header_size] + _explode(raw, header_size + 4)


def decompress_bytes(raw: bytes, backend: Backend | None = None) -> bytes:
    """DBF bytes from a DBC payload.

    ``backend``, else ``OMNISUS_DBC_BACKEND``, is ``python``, ``rust`` or ``auto``
    (the native package when installed). Both produce identical bytes.

    Raises:
        InvalidDbcError: the payload is malformed or truncated.
    """
    requested = requested_backend(backend, variable="OMNISUS_DBC_BACKEND", label="DBC")
    native = load_native(requested)
    logger.debug(
        "datasus_ftp.dbc_backend",
        backend="python" if native is None else "rust",
        requested=requested,
        version=None if native is None else native.__version__,
        fallback="extension_not_installed" if native is None and requested == "auto" else None,
    )
    if native is not None:
        try:
            return native.decompress_dbc(raw)
        except native.InvalidDbcError as exc:
            raise InvalidDbcError(str(exc)) from exc
    if requested == "auto" and len(raw) > HINT_BYTES:
        logger.info("datasus_ftp.dbc_python_backend_slow", compressed_bytes=len(raw))
    return _python_decompress(raw)
```

If ruff format rewrites the `_LITERAL` table despite `# fmt: skip`, move the list into a module-level tuple on one logical statement per original row and keep `# fmt: skip` on that statement; do not let it become one number per line.

- [ ] **Step 9: Run the tests**

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_dbc.py tests/unit/sources/datasus_ftp/test_native.py -q`
Expected: all pass (13 golden cases, vector, 5 malformed, truncation, Hypothesis, 5 selector tests, 11 loader tests).

- [ ] **Step 10: Break it and watch it fail**

One at a time, revert each after seeing the failure:
1. In `_explode`, change `shift = 2 if length == 2 else dictionary_bits` to `shift = dictionary_bits` → golden tests fail.
2. In `_python_decompress`, change `header_size + 4` to `header_size` → golden and vector tests fail.
3. In `decompress_bytes`, drop the `requested == "auto"` condition of the hint → `test_speed_hint_only_when_python_was_not_chosen[python-False]` fails.
4. In `native.load_native`, remove the `exc.name != "omnisus_db_dbf"` check → `test_missing_transitive_dependency_is_not_hidden` fails.

- [ ] **Step 11: Lint, type check, commit**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src
uv run pytest -m "not e2e and not perf" -q
git add src/omnisus_db/sources/datasus_ftp/native.py src/omnisus_db/sources/datasus_ftp/dbc.py \
  src/omnisus_db/sources/datasus_ftp/dbf_batches.py tests/fixtures/dbc/golden.json tests/fixtures/blast \
  tests/unit/sources/datasus_ftp/test_dbc.py tests/unit/sources/datasus_ftp/test_native.py \
  tests/unit/sources/datasus_ftp/test_dbf_backends.py
git commit -m "Decompress DBC in Python, byte-exact with datasus-dbc

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Route every caller through `dbc` and drop `datasus-dbc`

**Files:**
- Modify: `src/omnisus_db/sources/datasus_ftp/parse.py`, `src/omnisus_db/sources/datasus_ftp/staging.py`
- Modify: `tests/unit/sources/datasus_ftp/{test_staging,test_sinan_chagas,test_dbf_parity,test_integrity,test_parse}.py`, `tests/integration/test_rust_dbf_pipeline.py`, `tests/unit/scripts/test_gen_dicionario.py`, `tests/perf/bench_dbf_parse.py`
- Modify: `scripts/gen_dicionario.py`, `scripts/benchmark_resources.py`, `notebooks/_acervo/tabelas.py`
- Modify: `pyproject.toml`, `uv.lock`, `docs/architecture.md`

**Interfaces:**
- Consumes: `dbc.decompress_bytes(raw, backend=None) -> bytes`, `dbc.InvalidDbcError` (Task 1).
- Produces: the seam `omnisus_db.sources.datasus_ftp.parse.dbc` (the `dbc` module object); tests patch `parse.dbc.decompress_bytes`.

- [ ] **Step 1: Make the empty-payload test demand the real error**

In `tests/unit/sources/datasus_ftp/test_parse.py`, replace `test_parse_empty_bytes_returns_empty_lazyframe` (its name contradicts its body) with:

```python
def test_parse_empty_bytes_raises_invalid_dbc() -> None:
    with pytest.raises(InvalidDbcError, match="missing DBC header"):
        dbc_bytes_to_lazyframe(b"", dataset="sim_obitos")
```

and import it: `from omnisus_db.sources.datasus_ftp.dbc import InvalidDbcError`.

Run: `uv run pytest tests/unit/sources/datasus_ftp/test_parse.py -q`
Expected: FAIL — `datasus_dbc` raises its own error type, not `InvalidDbcError`.

- [ ] **Step 2: Switch the seam**

`parse.py`: replace `import datasus_dbc as datasus_dbc  # Retain the public decompression monkeypatch seam.` with `from omnisus_db.sources.datasus_ftp import dbc as dbc  # Decompression monkeypatch seam.` (keep import sorting: run `uv run ruff check --fix`). In the `dbc_bytes_to_lazyframe` docstring replace `Exception: bubbles from datasus_dbc / dbfread2 on bad input.` with:

```
        InvalidDbcError: if the DBC payload is malformed or truncated.
        Exception: bubbles from dbfread2 on a malformed DBF.
```

`staging.py`: `dbf_bytes = parse.datasus_dbc.decompress_bytes(raw)` → `dbf_bytes = parse.dbc.decompress_bytes(raw)`.

- [ ] **Step 3: Move every patch and direct caller**

Exact edits:
- `parse.datasus_dbc` → `parse.dbc` in `tests/unit/sources/datasus_ftp/test_staging.py` (7 lines), `test_sinan_chagas.py` (2), `test_dbf_parity.py` (2), `tests/integration/test_rust_dbf_pipeline.py` (1).
- `test_integrity.py`: the string `"omnisus_db.sources.datasus_ftp.parse.datasus_dbc.decompress_bytes"` → `"omnisus_db.sources.datasus_ftp.parse.dbc.decompress_bytes"`.
- `scripts/gen_dicionario.py`: `import datasus_dbc` → `from omnisus_db.sources.datasus_ftp import dbc`; `datasus_dbc.decompress_bytes(` → `dbc.decompress_bytes(`. `tests/unit/scripts/test_gen_dicionario.py`: both `module.datasus_dbc` → `module.dbc`.
- `tests/perf/bench_dbf_parse.py`: `import datasus_dbc` → `from omnisus_db.sources.datasus_ftp import dbc`; `datasus_dbc.decompress_bytes(` → `dbc.decompress_bytes(`.
- `scripts/benchmark_resources.py`: `import datasus_dbc` → delete (the module already imports `parse`); `datasus_dbc.decompress_bytes(` → `parse.dbc.decompress_bytes(` (two call sites); `parse.datasus_dbc.decompress_bytes = lambda _: raw` → `parse.dbc.decompress_bytes = lambda _: raw`; remove `"datasus-dbc",` from the recorded package list.
- `notebooks/_acervo/tabelas.py`: `import datasus_dbc` → `from omnisus_db.sources.datasus_ftp.dbc import decompress_bytes`; `datasus_dbc.decompress_bytes(payload)` → `decompress_bytes(payload)`.
- `docs/architecture.md`: `-> datasus_dbc.decompress_bytes -> complete DBF bytes` → `-> dbc.decompress_bytes (Python, or optional Rust) -> complete DBF bytes`.

- [ ] **Step 4: Remove the dependency**

Delete the line `"datasus-dbc>=0.1.3,<1.0",` from `[project] dependencies` in `pyproject.toml`, then:

```bash
uv lock
uv sync --extra dev
```

Expected: `uv lock` reports `Removed datasus-dbc v0.1.3`; `uv.lock` has no `datasus-dbc` entry.

- [ ] **Step 5: Prove nothing still names it**

```bash
grep -rn "datasus_dbc\|datasus-dbc" src tests scripts notebooks pyproject.toml uv.lock docs/architecture.md
```

Expected: exactly one hit, `scripts/smoke_native_wheel.py` (`find_spec("datasus_dbc") is None`), which Task 3 keeps on purpose. `.venv/bin/python -c "import datasus_dbc"` → `ModuleNotFoundError`.

- [ ] **Step 6: Run everything**

```bash
uv run pytest -m "not e2e and not perf" -q
uv run pytest tests/perf/bench_dbf_parse.py -m perf -q --benchmark-disable
uv run ruff check . && uv run ruff format --check . && uv run mypy src
uv run marimo check --strict --ignore-scripts notebooks
```

Expected: all pass (native tests skip: no wheel installed).

- [ ] **Step 7: Commit**

```bash
git add -A src tests scripts notebooks pyproject.toml uv.lock docs/architecture.md
git commit -m "Decompress DBC through omnisus-db, not datasus-dbc

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: The same decoder in the native package (API 2, abi3)

**Files:**
- Create: `native/omnisus-db-dbf/src/dbc.rs`, `native/omnisus-db-dbf/tests/dbc.rs`, `native/omnisus-db-dbf/fuzz/fuzz_targets/dbc.rs`
- Modify: `native/omnisus-db-dbf/src/lib.rs`, `src/bindings.rs`, `Cargo.toml`, `Cargo.lock`, `pyproject.toml`, `python/omnisus_db_dbf/__init__.py`, `python/omnisus_db_dbf/_native.pyi`, `fuzz/Cargo.toml`, `fuzz/Cargo.lock`, `fuzz/README.md`, `README.md`, `tests/test_bindings.py`
- Modify: `src/omnisus_db/sources/datasus_ftp/native.py` (`API_VERSION = 2`), `tests/conftest.py`, `scripts/smoke_native_wheel.py`, `scripts/benchmark_resources.py`, `tests/unit/sources/datasus_ftp/test_dbc.py`

**Interfaces:**
- Consumes: Task 1 error messages and `test_dbc.py` helpers `framed`, `outcome`, `BACKENDS`.
- Produces: Rust `_native::dbc::{decompress, explode, DbcError}`; Python `omnisus_db_dbf.decompress_dbc(data: bytes) -> bytes`, `omnisus_db_dbf.InvalidDbcError(ValueError)`, `API_VERSION == 2`.

- [ ] **Step 1: Write the failing Rust tests** — `native/omnisus-db-dbf/tests/dbc.rs`

```rust
use _native::dbc::{DbcError, decompress, explode};
use proptest::prelude::*;

// zlib contrib/blast/test: test.pk decompresses to test.txt.
const VECTOR: [u8; 8] = [0x00, 0x04, 0x82, 0x24, 0x25, 0x8f, 0x80, 0x7f];
const TEXT: &[u8] = b"AIAIAIAIAIAIA";

fn framed(body: &[u8]) -> Vec<u8> {
    let mut raw = vec![0; 8];
    raw.extend_from_slice(&10u16.to_le_bytes());
    raw.extend_from_slice(&[0; 4]);
    raw.extend_from_slice(body);
    raw
}

#[test]
fn zlib_blast_vector() {
    assert_eq!(explode(&VECTOR, 0).unwrap(), TEXT);
    let mut expected = framed(&[])[..10].to_vec();
    expected.extend_from_slice(TEXT);
    assert_eq!(decompress(&framed(&VECTOR)).unwrap(), expected);
}

#[test]
fn malformed_input_names_the_problem() {
    let too_big = [&[0u8; 8][..], &100u16.to_le_bytes()].concat();
    let cases: [(&[u8], &str); 5] = [
        (b"", "missing DBC header"),
        (&[0; 9], "missing DBC header"),
        (&too_big, "DBC header size exceeds file size"),
        (&framed(&[2, 4]), "corrupt DBC stream at byte 15"),
        (&framed(&[0, 7]), "corrupt DBC stream at byte 16"),
    ];
    for (raw, message) in cases {
        assert_eq!(decompress(raw).unwrap_err().to_string(), message);
    }
}

#[test]
fn every_truncation_is_reported_where_input_ends() {
    let raw = framed(&VECTOR);
    for end in 14..raw.len() {
        assert_eq!(decompress(&raw[..end]), Err(DbcError::Truncated(end)));
    }
}

proptest! {
    #[test]
    fn arbitrary_bytes_never_panic(body in proptest::collection::vec(any::<u8>(), 0..2048)) {
        let _ = decompress(&body);
        let _ = decompress(&framed(&body));
    }
}
```

`let cases` borrows temporaries from `framed(...)`; if the compiler rejects it, bind each `framed(...)` to a `let` first.

- [ ] **Step 2: Run it to see it fail**

```bash
export PATH="/opt/homebrew/opt/rustup/bin:$PATH"
cargo test --locked --manifest-path native/omnisus-db-dbf/Cargo.toml --test dbc
```

Expected: FAIL, `unresolved import _native::dbc`.

- [ ] **Step 3: Implement** — `native/omnisus-db-dbf/src/dbc.rs`

```rust
//! DATASUS DBC: a DBF header, a CRC32, then a PKWare DCL imploded body.
//!
//! The decoder is an altered port of Mark Adler's blast.c (zlib contrib/blast,
//! version 1.3). Altered: it reads a slice, appends to a growing `Vec` instead
//! of a 4 KiB window, and returns `DbcError` instead of integer codes.
//! `src/omnisus_db/sources/datasus_ftp/dbc.py` carries the same port; both must
//! produce identical bytes and messages. Original notice, from blast.h:
//!
//!   Copyright (C) 2003, 2012, 2013 Mark Adler
//!
//!   This software is provided 'as-is', without any express or implied
//!   warranty.  In no event will the author be held liable for any damages
//!   arising from the use of this software.
//!
//!   Permission is granted to anyone to use this software for any purpose,
//!   including commercial applications, and to alter it and redistribute it
//!   freely, subject to the following restrictions:
//!
//!   1. The origin of this software must not be misrepresented; you must not
//!      claim that you wrote the original software. If you use this software
//!      in a product, an acknowledgment in the product documentation would be
//!      appreciated but is not required.
//!   2. Altered source versions must be plainly marked as such, and must not be
//!      misrepresented as being the original software.
//!   3. This notice may not be removed or altered from any source distribution.

use std::{fmt, sync::LazyLock};

#[derive(Debug, PartialEq, Eq)]
pub enum DbcError {
    MissingHeader,
    HeaderSize,
    Corrupt(usize),
    Truncated(usize),
}

impl fmt::Display for DbcError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingHeader => f.write_str("missing DBC header"),
            Self::HeaderSize => f.write_str("DBC header size exceeds file size"),
            Self::Corrupt(at) => write!(f, "corrupt DBC stream at byte {at}"),
            Self::Truncated(at) => write!(f, "truncated DBC stream at byte {at}"),
        }
    }
}

const MAXBITS: usize = 13;
const END: usize = 519;
const LENGTH_BASE: [usize; 16] = [3, 2, 4, 5, 6, 7, 8, 9, 10, 12, 16, 24, 40, 72, 136, 264];
const LENGTH_EXTRA: [u32; 16] = [0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8];

/// Canonical decoding tables: codes per length, and symbols ordered by length.
struct Huffman {
    count: [usize; MAXBITS + 1],
    symbols: Vec<usize>,
}

impl Huffman {
    /// Each compact byte is a code length (low four bits) repeated (high four bits + 1) times.
    fn new(compact: &[u8]) -> Self {
        let lengths: Vec<usize> = compact
            .iter()
            .flat_map(|&byte| std::iter::repeat_n(usize::from(byte & 15), usize::from(byte >> 4) + 1))
            .collect();
        let mut count = [0; MAXBITS + 1];
        for &length in &lengths {
            count[length] += 1;
        }
        let mut offsets = [0; MAXBITS + 1];
        for length in 1..MAXBITS {
            offsets[length + 1] = offsets[length] + count[length];
        }
        let mut symbols = vec![0; lengths.len()];
        for (symbol, &length) in lengths.iter().enumerate() {
            if length != 0 {
                symbols[offsets[length]] = symbol;
                offsets[length] += 1;
            }
        }
        Self { count, symbols }
    }
}

static LITERAL: LazyLock<Huffman> = LazyLock::new(|| {
    Huffman::new(&[
        11, 124, 8, 7, 28, 7, 188, 13, 76, 4, 10, 8, 12, 10, 12, 10, 8, 23, 8, 9, 7, 6, 7, 8, 7,
        6, 55, 8, 23, 24, 12, 11, 7, 9, 11, 12, 6, 7, 22, 5, 7, 24, 6, 11, 9, 6, 7, 22, 7, 11, 38,
        7, 9, 8, 25, 11, 8, 11, 9, 12, 8, 12, 5, 38, 5, 38, 5, 11, 7, 5, 6, 21, 6, 10, 53, 8, 7,
        24, 10, 27, 44, 253, 253, 253, 252, 252, 252, 13, 12, 45, 12, 45, 12, 61, 12, 45, 44, 173,
    ])
});
static LENGTH: LazyLock<Huffman> = LazyLock::new(|| Huffman::new(&[2, 35, 36, 53, 38, 23]));
static DISTANCE: LazyLock<Huffman> =
    LazyLock::new(|| Huffman::new(&[2, 20, 53, 230, 247, 151, 248]));

/// Least-significant-bit-first reader over a slice; offsets are absolute.
struct Bits<'a> {
    data: &'a [u8],
    position: usize,
    buffer: u32,
    available: u32,
}

impl Bits<'_> {
    fn take(&mut self, need: u32) -> Result<usize, DbcError> {
        while self.available < need {
            let byte = *self
                .data
                .get(self.position)
                .ok_or(DbcError::Truncated(self.position))?;
            self.buffer |= u32::from(byte) << self.available;
            self.position += 1;
            self.available += 8;
        }
        let value = self.buffer & ((1 << need) - 1);
        self.buffer >>= need;
        self.available -= need;
        Ok(value as usize)
    }

    /// Codes are stored bit-reversed and inverted relative to canonical order.
    fn decode(&mut self, table: &Huffman) -> Result<usize, DbcError> {
        let (mut code, mut first, mut index) = (0, 0, 0);
        for length in 1..=MAXBITS {
            code |= self.take(1)? ^ 1;
            let count = table.count[length];
            if code < first + count {
                return Ok(table.symbols[index + code - first]);
            }
            index += count;
            first = (first + count) << 1;
            code <<= 1;
        }
        Err(DbcError::Corrupt(self.position))
    }
}

/// Decode the imploded stream at `data[start..]`.
pub fn explode(data: &[u8], start: usize) -> Result<Vec<u8>, DbcError> {
    let mut bits = Bits { data, position: start, buffer: 0, available: 0 };
    let literals_coded = bits.take(8)?;
    if literals_coded > 1 {
        return Err(DbcError::Corrupt(bits.position));
    }
    let dictionary_bits = bits.take(8)?;
    if !(4..=6).contains(&dictionary_bits) {
        return Err(DbcError::Corrupt(bits.position));
    }
    let mut out = Vec::new();
    loop {
        if bits.take(1)? == 0 {
            let literal = if literals_coded == 1 { bits.decode(&LITERAL)? } else { bits.take(8)? };
            out.push(literal as u8);
            continue;
        }
        let symbol = bits.decode(&LENGTH)?;
        let length = LENGTH_BASE[symbol] + bits.take(LENGTH_EXTRA[symbol])?;
        if length == END {
            return Ok(out);
        }
        let shift = if length == 2 { 2 } else { dictionary_bits as u32 };
        let distance = (bits.decode(&DISTANCE)? << shift) + bits.take(shift)? + 1;
        if distance > out.len() {
            return Err(DbcError::Corrupt(bits.position));
        }
        let source = out.len() - distance;
        if distance >= length {
            out.extend_from_within(source..source + length);
        } else {
            // Overlapping copy: each new byte may be one this copy just wrote.
            for _ in 0..length {
                out.push(out[out.len() - distance]);
            }
        }
    }
}

/// DBF bytes from a DBC payload: the header is kept, the CRC32 after it is ignored.
pub fn decompress(raw: &[u8]) -> Result<Vec<u8>, DbcError> {
    let size = raw.get(8..10).ok_or(DbcError::MissingHeader)?;
    let header_size = usize::from(u16::from_le_bytes([size[0], size[1]]));
    if header_size + 4 > raw.len() {
        return Err(DbcError::HeaderSize);
    }
    let mut out = raw[..header_size].to_vec();
    out.extend(explode(raw, header_size + 4)?);
    Ok(out)
}
```

`src/lib.rs`: add `pub mod dbc;` (alphabetical, after `mod arrow;`). Run `cargo fmt --manifest-path native/omnisus-db-dbf/Cargo.toml --all` and accept its layout.

Run: `cargo test --locked --manifest-path native/omnisus-db-dbf/Cargo.toml --test dbc` — Expected: 4 passed.

- [ ] **Step 4: Expose it to Python**

`src/bindings.rs`: add `crate::dbc` to the `use crate::{...}` list, then:

```rust
create_exception!(
    omnisus_db_dbf,
    InvalidDbcError,
    PyValueError,
    "DBC is malformed or truncated."
);

#[pyfunction]
fn decompress_dbc<'py>(py: Python<'py>, data: &Bound<'py, PyBytes>) -> PyResult<Bound<'py, PyBytes>> {
    // Never hold a borrowed Python buffer across detach().
    let owned = data.as_bytes().to_vec();
    let out = py
        .detach(move || dbc::decompress(&owned))
        .map_err(|e| InvalidDbcError::new_err(e.to_string()))?;
    Ok(PyBytes::new(py, &out))
}
```

In `register`: `module.add("API_VERSION", 2)?;`, `module.add("InvalidDbcError", module.py().get_type::<InvalidDbcError>())?;`, `module.add_function(wrap_pyfunction!(decompress_dbc, module)?)?;`.

`python/omnisus_db_dbf/__init__.py`: docstring `"""Optional native DBF to Arrow reader and DBC decompressor."""`; import and list `InvalidDbcError` and `decompress_dbc` in alphabetical order in both the import and `__all__`.

`python/omnisus_db_dbf/_native.pyi`: add `class InvalidDbcError(ValueError): ...` and `def decompress_dbc(data: bytes) -> bytes: ...`.

`Cargo.toml`: `version = "0.2.0"`; `description = "Optional DBF to Arrow reader and DBC decompressor for omnisus-db"`; `pyo3 = { version = "=0.29.0", optional = true, features = ["abi3-py312"] }`. `pyproject.toml` (native): same description; classifiers add `"Programming Language :: Python :: 3.14"`.

Update both lockfiles for the version bump only:

```bash
cargo update --manifest-path native/omnisus-db-dbf/Cargo.toml --workspace
cargo update --manifest-path native/omnisus-db-dbf/fuzz/Cargo.toml -p omnisus-db-dbf
git diff native/omnisus-db-dbf/Cargo.lock native/omnisus-db-dbf/fuzz/Cargo.lock
```

Expected diff: only the `omnisus-db-dbf` version line changes in each. If other crates moved, `git checkout` the lockfiles and bump the `version` line by hand.

- [ ] **Step 5: Bump every Python-side API check to 2**

- `src/omnisus_db/sources/datasus_ftp/native.py`: `API_VERSION = 2`.
- `tests/conftest.py` `_native_available`: `if omnisus_db_dbf.API_VERSION != 2:`; message `"Incompatible native API"`. Help text of `--require-rust-dbf`: `"Require the real native extension and all committed DBF/DBC fixtures."` stays.
- `scripts/benchmark_resources.py`: `if native.API_VERSION != 2:` / `"Expected native API_VERSION=2"`.
- `native/omnisus-db-dbf/tests/test_bindings.py`: `assert native.API_VERSION == 2`, and add:

```python
def test_decompress_dbc_contract():
    import omnisus_db_dbf as native

    blast = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "blast"
    raw = bytes(8) + (10).to_bytes(2, "little") + bytes(4) + (blast / "test.pk").read_bytes()
    assert native.decompress_dbc(raw) == raw[:10] + (blast / "test.txt").read_bytes()
    with pytest.raises(native.InvalidDbcError, match="^missing DBC header$"):
        native.decompress_dbc(b"")
    assert issubclass(native.InvalidDbcError, ValueError)
    with pytest.raises(TypeError):
        native.decompress_dbc(bytearray(raw))
```

- `scripts/smoke_native_wheel.py`: `assert dbf.API_VERSION == 2`; replace the two `python_tag` lines with `assert "Tag: cp312-abi3-" in wheel_metadata`; update the module docstring's first paragraph to say to copy `tests/fixtures/dbf` **and** `tests/fixtures/blast` beside it; add:

```python
def test_decompress_dbc_vector() -> None:
    blast = Path(__file__).parent / "blast"
    raw = bytes(8) + (10).to_bytes(2, "little") + bytes(4) + (blast / "test.pk").read_bytes()
    assert dbf.decompress_dbc(raw) == raw[:10] + (blast / "test.txt").read_bytes()
    with pytest.raises(dbf.InvalidDbcError):
        dbf.decompress_dbc(raw[:-1])
```

- `tests/unit/sources/datasus_ftp/test_dbc.py`: `BACKENDS = ["python", pytest.param("rust", marks=pytest.mark.rust_dbf)]`, and add:

```python
@pytest.mark.rust_dbf
@settings(max_examples=500, deadline=None)
@given(body=st.binary(max_size=2048), frame=st.booleans())
def test_backends_agree_on_bytes_and_messages(body, frame):
    raw = framed(body) if frame else body
    assert outcome(raw, "rust") == outcome(raw, "python")
```

- [ ] **Step 6: Build the wheel and run the native suites**

```bash
export PATH="/opt/homebrew/opt/rustup/bin:$PATH"
cargo fmt --manifest-path native/omnisus-db-dbf/Cargo.toml --all --check
cargo clippy --locked --all-targets --manifest-path native/omnisus-db-dbf/Cargo.toml -- -D warnings
cargo test --locked --manifest-path native/omnisus-db-dbf/Cargo.toml
cargo test --locked --no-default-features --manifest-path native/omnisus-db-dbf/Cargo.toml
rm -rf dist/native
uvx --python 3.12 maturin==1.12.6 build --manifest-path native/omnisus-db-dbf/Cargo.toml --release --locked --out dist/native
uv pip install --python .venv dist/native/*.whl
uv run --no-sync pytest --require-rust-dbf -m "not e2e and not perf" -q \
  tests/unit/sources/datasus_ftp tests/integration/test_rust_dbf_pipeline.py native/omnisus-db-dbf/tests/test_bindings.py
```

Expected: wheel name contains `cp312-abi3`; every command passes; no `rust_dbf` skips. Then the clean-environment smoke on two interpreters:

```bash
for py in 3.12 3.14; do
  gate=$(mktemp -d); smoke=$(mktemp -d)
  uv venv -q --python $py "$gate/venv"
  uv pip install -q --python "$gate/venv" --only-binary=:all: dist/native/*.whl 'pyarrow==25.0.1' 'pytest==9.1.1'
  cp scripts/smoke_native_wheel.py "$smoke/"; cp -R tests/fixtures/dbf tests/fixtures/blast "$smoke/"; touch "$smoke/pytest.ini"
  (cd "$smoke" && OMNISUS_NATIVE_SOURCE_ROOT="$PWD" uv run --no-project --no-sync --python "$gate/venv" python -I -m pytest -q -c pytest.ini smoke_native_wheel.py)
done
```

`OMNISUS_NATIVE_SOURCE_ROOT` must be the checkout root: run the loop from the worktree root with `OMNISUS_NATIVE_SOURCE_ROOT="$(git rev-parse --show-toplevel)"` captured before `cd`. Expected: 10 passed per interpreter. Remove `dist/native` afterwards (`dist/` is git-ignored; confirm with `git status`).

- [ ] **Step 7: Fuzz target**

`native/omnisus-db-dbf/fuzz/fuzz_targets/dbc.rs`:

```rust
#![no_main]

use _native::dbc::decompress;
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    if data.len() > 64 * 1024 {
        return;
    }
    let _ = decompress(data);
});
```

`fuzz/Cargo.toml`: add a second `[[bin]]` block identical to `dbf` with `name = "dbc"`, `path = "fuzz_targets/dbc.rs"`. `fuzz/README.md`: rename the heading to `# Native robustness targets`, state that `dbc` exercises header checks and the imploded-stream decoder, and add a run command using the DBC fixtures as corpus:

```sh
mkdir -p /tmp/omnisus-dbc-fuzz-corpus
cp ../../tests/fixtures/dbc/sia_aq_rr_2024_01_mini.dbc ../../tests/fixtures/blast/test.pk /tmp/omnisus-dbc-fuzz-corpus/
cargo +nightly-2026-09-10 fuzz run dbc /tmp/omnisus-dbc-fuzz-corpus -- \
  -max_total_time=30 -max_len=65536 -timeout=5 -rss_limit_mb=2048
```

Check it compiles on stable without running libFuzzer: `cargo check --locked --manifest-path native/omnisus-db-dbf/fuzz/Cargo.toml --bins`. If stable refuses to build `libfuzzer-sys`, install `nightly-2026-09-10` (`rustup toolchain install nightly-2026-09-10 --profile minimal`) and use `cargo +nightly-2026-09-10 check`. Run the 30-second campaign if cargo-fuzz is available and record the executions count in `fuzz/README.md` beside the DBF campaign; otherwise leave only the command.

- [ ] **Step 8: Native README**

In `native/omnisus-db-dbf/README.md`: first line `Optional DBF → Arrow reader and DBC decompressor for \`omnisus-db\`.`; after the reader example add

````markdown
```python
from omnisus_db_dbf import decompress_dbc

dbf_bytes = decompress_dbc(dbc_bytes)  # raises InvalidDbcError on bad input
```

`decompress_dbc` releases the GIL and returns the same bytes as the pure-Python
decoder in `omnisus_db.sources.datasus_ftp.dbc`.
````

Change `API version 1 supports` to `API version 2 supports` and add the sentence `API version 2 adds \`decompress_dbc\`.`; replace the targets paragraph lines `Supported distribution targets are normal CPython 3.12/3.13 ...` and `The initial package does not use abi3 ...` with `Wheels use the stable ABI (abi3, CPython 3.12 and later) on Linux x86_64, Windows x86_64 and macOS arm64/x86_64. Free-threaded CPython is not supported.`; delete the sentence `The existing datasus-dbc CPython 3.13 wheel limitation is independent.`

- [ ] **Step 9: Break it and watch it fail**

One at a time, rebuild the wheel where needed, revert after:
1. Rust `explode`: `let shift = dictionary_bits as u32;` → `test_matches_datasus_dbc_output[...-rust]` and `test_backends_agree...` fail.
2. Rust `Bits::take`: `.ok_or(DbcError::Truncated(self.position + 1))` → `every_truncation_is_reported_where_input_ends` fails.
3. `bindings.rs`: `module.add("API_VERSION", 1)` → the Python run errors with `Incompatible native API`.

- [ ] **Step 10: Commit**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src
git add native src/omnisus_db/sources/datasus_ftp/native.py tests/conftest.py scripts tests/unit/sources/datasus_ftp/test_dbc.py
git status --short   # no target/, dist/ or wheel files staged
git commit -m "Decompress DBC natively in omnisus-db-dbf (API 2, abi3)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: CI, release notes and changelog

**Files:**
- Modify: `.github/workflows/native.yml`, `.github/workflows/test.yml`, `.github/workflows/release.yml`
- Modify: `RELEASE.md`, `CHANGELOG.md`, `README.md` and `docs/**` only where they mention `datasus-dbc`, cargo/Rust for installing, or the 3.13 install gap

**Interfaces:**
- Consumes: abi3 wheel (`cp312-abi3`), `scripts/smoke_native_wheel.py` expecting `dbf/` and `blast/` beside it (Task 3).

- [ ] **Step 1: `native.yml`**

- `name: native package`.
- `wheels` job: name `wheel (${{ matrix.platform.target }})`; delete the `python:` matrix axis; `actions/setup-python` pins `python-version: "3.12"`; maturin `--interpreter ${{ runner.os == 'Linux' && 'python3.12' || 'python' }}`.
- Replace the step `Native wheel only, binary dependencies only` with:

```yaml
      - name: Native wheel only, binary dependencies only, on every supported Python
        # One abi3 wheel serves 3.12 and later. No cache, so a source build cannot mask a gap.
        run: |
          smoke="$RUNNER_TEMP/native-smoke"
          mkdir -p "$smoke"
          cp scripts/smoke_native_wheel.py "$smoke/"
          cp -R tests/fixtures/dbf tests/fixtures/blast "$smoke/"
          touch "$smoke/pytest.ini"
          for python in 3.12 3.13 3.14; do
            gate="$RUNNER_TEMP/native-gate-$python"
            uv venv --python "$python" "$gate"
            uv pip install --python "$gate" --no-cache --only-binary=:all: \
              dist/native/*.whl 'pyarrow==25.0.1' 'pytest==9.1.1'
            (cd "$smoke" && uv run --no-project --no-sync --python "$gate" \
              python -I -m pytest -q -c pytest.ini smoke_native_wheel.py)
          done
```

- Replace the two steps `Install the full stack from wheels on Python 3.12` and `Install the development stack on Python 3.13` with one step (no `if:`):

```yaml
      - name: Install the full stack from wheels
        env:
          STACK_GATE: ${{ runner.temp }}/native-stack-gate
        run: |
          uv venv --python '${{ steps.python.outputs.python-path }}' "$STACK_GATE"
          main_wheels=(main-dist/*.whl)
          uv pip install --python "$STACK_GATE" --no-cache --only-binary=:all: \
            "${main_wheels[0]}[dev]" dist/native/*.whl
```

- Upload artifact name: `native-wheel-${{ matrix.platform.target }}`.
- `sdist` job's smoke step: `cp -R tests/fixtures/dbf tests/fixtures/blast "$NATIVE_SMOKE/"` instead of copying only `dbf`.
- No remaining `datasus` or `matrix.python` string in the file: `grep -n "datasus\|matrix.python" .github/workflows/native.yml` → empty.

- [ ] **Step 2: `test.yml` install gate**

Replace the job comment and matrix so every row is required:

```yaml
  install-gate:
    # The real "does it install for a user": build the wheel, then install it
    # where NOTHING may be built from source. Everything else in CI is green
    # only because the runners ship a Rust toolchain that users do not have.
    # Every supported Python must pass; DBC decompression is pure Python unless
    # the optional native wheel is installed.
    name: wheel-only install (${{ matrix.os }}, py${{ matrix.python }})
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - { os: ubuntu-latest, python: "3.12" }
          - { os: macos-latest, python: "3.12" }
          - { os: windows-latest, python: "3.12" }
          - { os: ubuntu-latest, python: "3.13" }
          - { os: ubuntu-latest, python: "3.14" }
```

Delete `continue-on-error: ${{ !matrix.required }}`. Steps stay as they are.

- [ ] **Step 3: `release.yml` gate**

Gate job: name `wheel-only install (${{ matrix.os }}, py${{ matrix.python }})`; matrix `os: [ubuntu-latest, macos-latest, windows-latest]` and `python: ["3.12", "3.13", "3.14"]`; replace the three hard-coded `3.12` uses with `${{ matrix.python }}`; comment:

```yaml
    # Publishing is gated on the wheel-only install (spec §7.1.1 and §7.2):
    # we must not ship a package users cannot install without a Rust toolchain.
    # Every supported Python, every OS. No continue-on-error; this is the gate.
```

Validate all three files: `uvx --from check-jsonschema check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/native.yml .github/workflows/test.yml .github/workflows/release.yml` (if offline, `uv run python -c "import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]" .github/workflows/*.yml`).

- [ ] **Step 4: `RELEASE.md`**

- Section `## Optional native DBF package` → `## Optional native package`. Rewrite its paragraphs to say: it provides the Rust DBF reader and DBC decompressor; one abi3 wheel per platform (Linux x86_64, Windows x86_64, macOS arm64/x86_64) serves CPython 3.12 and later, smoke-tested on 3.12, 3.13 and 3.14; `omnisus-db` does not depend on it and decodes DBF and DBC in pure Python without it; `dbf-v*` tags and the Trusted Publisher paragraph stay; replace "should the main package add a `rust` extra" wording only if it now names the wrong capability (it should say a `native` extra).
- Delete the whole `## The wheel gap, and why the floor is 3.12` section, including the "real fix" paragraph. Add in its place:

```markdown
## Supported Python

`requires-python` is `>=3.12`. The wheel-only install gate in `test.yml` and
`release.yml` installs the built wheel with `--only-binary=:all:` on 3.12, 3.13
and 3.14 and must pass; no dependency needs a Rust toolchain.
```

- [ ] **Step 5: `CHANGELOG.md`**

Under `## Unreleased`, before `### Fixed`, add:

```markdown
### Changed

- **Installs from wheels on Python 3.13 and 3.14.** DBC decompression no
  longer uses `datasus-dbc`, which has no 3.13 wheels for macOS, Windows or
  Linux x86_64 and made `pip install` need Rust there. `omnisus-db` now ports
  zlib's `blast.c` to pure Python, byte-exact with `datasus-dbc` on every test
  fixture. The optional `omnisus-db-dbf` wheel carries the same decoder in Rust
  (API version 2, one abi3 wheel for 3.12+) and is used automatically when
  installed; `OMNISUS_DBC_BACKEND=python|rust|auto` chooses explicitly.
  Malformed payloads raise `InvalidDbcError`, a `ValueError`.
```

- [ ] **Step 6: Remaining mentions**

```bash
grep -rn "datasus-dbc\|datasus_dbc\|cargo\|3\.13" README.md docs --include='*.md' | grep -v "docs/superpowers\|docs/decisions"
```

Fix each hit that states an install requirement or the old gap; leave hits that are unrelated (e.g. a changelog entry about a past release). Then:

```bash
uv run mkdocs build --strict
grep -rn "datasus_dbc\|datasus-dbc" --exclude-dir=.git --exclude-dir=.venv --exclude-dir=reports --exclude-dir=superpowers --exclude-dir=decisions . | grep -v "^./CHANGELOG.md"
```

Expected: the build passes; the grep lists only `scripts/smoke_native_wheel.py` and `tests/unit/sources/datasus_ftp/test_dbc.py` / `tests/fixtures/dbc/golden.json`-related docstrings that describe the golden source.

- [ ] **Step 7: Commit**

```bash
uv run pre-commit run --from-ref origin/main --to-ref HEAD
git add .github RELEASE.md CHANGELOG.md README.md docs
git commit -m "Require wheel-only installs on 3.12-3.14; build one abi3 native wheel

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

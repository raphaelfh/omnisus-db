# DBC decompression inside omnisus-db — design

Date: 2026-09-13 · Branch: `dbc-nativo` (off `main`, independent of PR #10)

## 1. Problem

`omnisus-db` depends on `datasus-dbc` 0.1.3 to decompress DATASUS `.dbc` files.
That package publishes no cp313 wheels for macOS, Windows or manylinux x86_64,
so on Python 3.13+ `pip install omnisus-db` builds it from source and fails
without a Rust toolchain. Upstream has been idle since July 2024.

Alternatives rejected:

- `pyreaddbc` 2.0.4 is maintained and has cp313 wheels, but is AGPL-3.0;
  `omnisus-db` is MIT.
- The Rust crate `explode` 0.1.2 (used by `datasus-dbc`) had its last release in
  August 2020; it fails the "well maintained" requirement.
- Pure Python only: works everywhere but gives up native speed.

## 2. Decision

Decompress DBC in code we own, with two backends that must agree byte for byte:

1. **Native (default where available):** a Rust port of Mark Adler's `blast.c`
   (zlib `contrib/blast`, zlib license, maintained) in the existing crate
   `native/omnisus-db-dbf`, built as `abi3` wheels and published to PyPI.
2. **Pure Python (fallback):** a Python port of the same algorithm, used on
   platforms without a native wheel.

No new third-party dependency is added. `datasus-dbc` is removed.

## 3. DBC format

Bytes 0–9 are a DBF pre-header; bytes 8–9 hold `header_size` (little-endian
u16). Bytes 10..`header_size` are the rest of the DBF header, followed by a
4-byte CRC32 that is read and ignored. The remainder is a PKWare DCL "imploded"
stream. Output = `raw[:header_size]` + exploded stream.

## 4. Components

### 4.1 Rust — `native/omnisus-db-dbf/src/dbc.rs`

- `blast` port: literal (coded/uncoded) and distance-dictionary modes (4, 5 or
  6 bits), Huffman tables built from the compact length tables in `blast.c`,
  end-of-stream length code 519. Bounds-checked: no `unsafe`, no panic on any
  input.
- `decompress_dbc(raw: &[u8]) -> Result<Vec<u8>, DbcError>` handles the framing
  in §3.
- Binding (`bindings.rs`): `decompress_dbc(data: bytes) -> bytes`, exception
  `InvalidDbcError` (subclass of `ValueError`), GIL released while decoding.
- `API_VERSION` becomes `2`; `omnisus_db_dbf/__init__.py` and `_native.pyi`
  export the new names. The Python side requires exactly `2` for both the DBF
  and the DBC selector, so a stale wheel is reported as
  `reason="api_version_mismatch"` and the Python backends are used.

### 4.2 Python — `src/omnisus_db/sources/datasus_ftp/dbc.py`

- `_explode(stream: bytes) -> bytes`: pure-Python port of the same algorithm.
- `InvalidDbcError(ValueError)`: the error callers catch. The native
  `omnisus_db_dbf.InvalidDbcError` is re-raised as this type.
- `decompress_bytes(raw: bytes, backend: Backend | None = None) -> bytes`,
  selection copied from `dbf_batches.open_dbf_batches`:
  `requested = backend or os.environ.get("OMNISUS_DBC_BACKEND", "auto")`,
  validated against `python|rust|auto`; `rust` raises `RuntimeError` if the
  native module is missing or on the wrong API version; `auto` falls back to
  Python. Logs `datasus_ftp.dbc_backend` once per call with `backend`,
  `requested`, `version` and the `fallback` reason.
- Speed hint: when the Python backend decodes an input larger than 5 MiB, log
  one INFO line saying no native wheel is installed for this platform and
  decompression is slower.

### 4.3 Seam

`parse.py` replaces `import datasus_dbc as datasus_dbc` with
`from omnisus_db.sources.datasus_ftp import dbc as dbc`; `staging.py` calls
`parse.dbc.decompress_bytes(raw)`. Every monkeypatch of
`parse.datasus_dbc.decompress_bytes` (unit, integration and perf tests,
`scripts/benchmark_resources.py`, `scripts/gen_dicionario.py`) moves to
`parse.dbc.decompress_bytes`. `scripts/smoke_native_wheel.py` keeps asserting
that `datasus_dbc` is not importable and also smoke-tests `decompress_dbc` on
one fixture.

## 5. Packaging and release

- **abi3:** `pyo3` gains the `abi3-py312` feature; the wheel matrix in
  `native.yml` drops its `python` axis. Targets: Linux x86_64 and aarch64
  (manylinux 2_28 and musllinux 1_2), macOS arm64 and x86_64, Windows x86_64.
  The wheel-only smoke runs the same wheel on 3.12, 3.13 and 3.14.
- **Crate metadata:** description becomes "Native DBF reader and DBC
  decompressor for omnisus-db"; classifiers list 3.12–3.14.
- **Dependency in `omnisus-db`:** `datasus-dbc` is removed. `omnisus-db-dbf` is
  added pinned `==` to the crate version released with it, restricted by
  markers to platforms with a wheel:
  `(sys_platform == 'linux' and platform_machine in 'x86_64 aarch64') or
  (sys_platform == 'darwin' and platform_machine in 'arm64 x86_64') or
  (sys_platform == 'win32' and platform_machine == 'AMD64')`.
  Elsewhere pip never tries to build it and the Python backend is used. Musl
  Linux cannot be excluded by a marker, which is why musllinux wheels are in
  the matrix.
- **`release.yml`:** one `v*` tag releases both packages. Build the crate
  wheels and sdist, run the gate, publish `omnisus-db-dbf`, then `omnisus-db`.
  The wheel-only install gate runs on ubuntu/macos/windows × 3.12/3.13/3.14
  with `--only-binary=:all:` and must pass. The `dbf-v*` tag trigger in
  `native.yml` is removed.
- **`test.yml`:** the `install-gate` 3.13 row becomes required and a required
  3.14 row is added. The gate builds the crate wheel and installs the main
  wheel with `--find-links` pointing at it, so it does not need PyPI.
- **Manual step (repository owner):** configure PyPI Trusted Publishing for
  both project names before the first tag.

## 6. Errors

Both backends raise `InvalidDbcError` with one of four messages. Offsets are
included where applicable; file contents never are.

| Case | Message |
|---|---|
| input shorter than 10 bytes | `missing DBC header` |
| `header_size + 4 > len(raw)` | `DBC header size exceeds file size` |
| invalid code, distance before output start, bad table | `corrupt DBC stream at byte N` |
| input ends before the end-of-stream code | `truncated DBC stream at byte N` |

The existing bad-input test in `tests/unit/sources/datasus_ftp/test_parse.py`
keeps passing.

## 7. Tests

- **Golden outputs first:** before `datasus-dbc` is removed, one commit records
  the SHA-256 and length of `datasus_dbc.decompress_bytes` output for the 14
  `.dbc` files in `tests/fixtures/dbc/` in `tests/fixtures/dbc/golden.json`.
  Both backends must match every entry.
- **zlib vector:** `test.pk` → `test.txt` from zlib `contrib/blast/test/`,
  copied with its license notice into `tests/fixtures/blast/`, checked in both
  backends (`cargo test` and pytest).
- **Bad input:** every truncated prefix of one small fixture, single-byte
  corruptions, and proptest/Hypothesis random bytes must end in
  `InvalidDbcError`: never a panic, `IndexError` or hang (Python tests carry a
  timeout). A `cargo fuzz` target `dbc` is added next to `dbf`.
- **Selector:** env var validation, explicit `rust` without the module raises,
  `auto` fallback logs its reason, API version mismatch falls back, the 5 MiB
  hint appears only with the Python backend.
- **Falsification:** each new test is broken once on purpose (flip one output
  byte, skip the CRC offset) and seen to fail before it is trusted.
- **Benchmark (informative, not a gate):** Python vs Rust on
  `sinasc_rr_2022_mini.dbc` in `tests/perf/`.

## 8. Risks

- **abi3 with `arrow-pyarrow` 59.2.0 and `pyo3` 0.29:** may not compile under
  the limited API. The plan's first task is a spike building an abi3 wheel. If
  it fails, the matrix keeps per-version wheels for 3.12, 3.13 and 3.14 and
  this spec records why.
- **Python backend speed:** unknown on full-size SIH/SIA files. It only affects
  platforms without a wheel; the benchmark measures it and the docs state it.
- **First PyPI publication:** neither name is published yet; nothing is
  uploaded unless the release gate is green.

## 9. Revisions after the spike (2026-09-13, before planning)

These rulings override the sections above where they disagree.

- **Measured:** a throwaway pure-Python port matched all 13 golden outputs
  (there are 13 `.dbc` fixtures, not 14) and zlib's vector, decoding the
  largest fixture (2.9 MB out) in 0.34 s. An `abi3-py312` build of the current
  crate succeeded (`cp312-abi3` wheel), so the §8 abi3 risk is closed.
- **The native package stays optional (overrides §5 "Dependency" and
  "`release.yml`").** `RELEASE.md` records that nothing is published to PyPI by
  decision; the distribution channel is the wheel file built from the tag. A
  required `omnisus-db-dbf` dependency would make that wheel uninstallable.
  So `omnisus-db` gains no dependency, pure Python is the default decoder,
  `release.yml` publishes nothing new, and the musllinux/aarch64 targets are
  dropped (YAGNI while the package is optional). The wheel-only install gates
  on 3.12, 3.13 and 3.14 become required, because removing `datasus-dbc`
  makes them pass.
- **Stale native API is an error, not a fallback (overrides §4.1).** This is
  what the DBF selector already does; both selectors now share one loader,
  `datasus_ftp/native.py`, requiring `API_VERSION == 2`.
- **Speed hint threshold (overrides §4.2):** 16 MiB of compressed input, which
  is roughly 10 s in pure Python; 5 MiB would fire on every ordinary file.
- **No output-size limit is added;** DBC sources are the DATASUS FTP, as
  before.
- **zlib license:** both ports are altered versions of `blast.c`, so each
  source file carries the `blast.h` notice and says it was altered.

## 10. Out of scope

- Changing the DBF reader itself.
- Compressing DBC files.
- PR #10 (researcher guide) and its CI.

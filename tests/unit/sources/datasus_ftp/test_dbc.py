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
from tests.support.native import missing_module

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
GOLDEN = json.loads((FIXTURES / "dbc" / "golden.json").read_text(encoding="utf-8"))
MUTATION_SEED = (FIXTURES / "dbc" / "sia_aq_rr_2024_01_mini.dbc").read_bytes()
VECTOR = (FIXTURES / "blast" / "test.pk").read_bytes()
BACKENDS = ["python", pytest.param("rust", marks=pytest.mark.rust_dbf)]


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


@pytest.mark.rust_dbf
@settings(max_examples=500, deadline=None)
@given(
    body=st.one_of(
        st.binary(max_size=2048),
        st.tuples(st.integers(0, 1), st.integers(4, 6), st.binary(max_size=2048)).map(
            lambda t: bytes([t[0], t[1]]) + t[2]
        ),
    ),
    frame=st.booleans(),
)
def test_backends_agree_on_bytes_and_messages(body, frame):
    raw = framed(body) if frame else body
    assert outcome(raw, "rust") == outcome(raw, "python")


@pytest.mark.rust_dbf
@settings(max_examples=200, deadline=None)
@given(index=st.integers(0, len(MUTATION_SEED) - 1), value=st.integers(0, 255))
def test_backends_agree_on_mutated_fixture(index, value):
    mutated = bytearray(MUTATION_SEED)
    mutated[index] = value
    assert outcome(bytes(mutated), "rust") == outcome(bytes(mutated), "python")


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


def test_unknown_backend_is_rejected(monkeypatch):
    monkeypatch.setenv("OMNISUS_DBC_BACKEND", "typo")
    with pytest.raises(ValueError, match=r"^DBC backend must be python, rust or auto$"):
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
    with pytest.raises(dbc.InvalidDbcError, match=r"^corrupt DBC stream at byte 3$"):
        dbc.decompress_bytes(b"", backend="rust")


def test_auto_without_package_decodes_in_python_and_says_why(monkeypatch):
    monkeypatch.setattr(native, "import_module", lambda _: missing_module("omnisus_db_dbf"))
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
    monkeypatch.setattr(native, "import_module", lambda _: missing_module("omnisus_db_dbf"))
    monkeypatch.setattr(dbc, "HINT_BYTES", 10)
    log = Recorder()
    monkeypatch.setattr(dbc, "logger", log)
    raw = framed(VECTOR)
    dbc.decompress_bytes(raw, backend=backend)
    hints = [fields for level, event, fields in log.events if level == "info"]
    assert hints == ([{"compressed_bytes": len(raw)}] if hinted else [])

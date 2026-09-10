"""Closable DBF → Arrow adapters; staging owns all publication and schema policy."""

from __future__ import annotations

import datetime as dt
import os
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from decimal import Decimal
from importlib import import_module
from typing import Any, Literal

import pyarrow as pa
import structlog

from omnisus_db.sources.datasus_ftp.dbf_contract import DbfIntegrityError

Backend = Literal["python", "rust", "auto"]
logger = structlog.get_logger(__name__)


def _family(value: Any) -> type:
    # bool is an int subclass; datetime is a date subclass.
    for cls in (bool, int, float, str, bytes, Decimal, dt.datetime, dt.date, dt.time):
        if isinstance(value, cls):
            return cls
    raise TypeError(f"Unsupported DBF value type: {type(value).__name__}")


def _table(records: list[dict[str, Any]]) -> pa.Table:
    names = dict.fromkeys(name for record in records for name in record)
    columns = {}
    for name in names:
        values = [record.get(name) for record in records]
        families = {_family(value) for value in values if value is not None}
        if len(families) > 1:
            raise TypeError(f"Incompatible value families in DBF column {name}")
        columns[name] = pa.array(values, safe=True)
    return pa.table(columns)


def _python_batches(
    data: bytes, encoding: str, batch_rows: int
) -> Generator[pa.RecordBatch, None, None]:
    from omnisus_db.sources.datasus_ftp import parse

    records = parse._stream_records(data, encoding=encoding)
    buffer = []
    try:
        for record in records:
            buffer.append(record)
            if len(buffer) >= batch_rows:
                yield from _table(buffer).to_batches()
                buffer.clear()
        if buffer:
            yield from _table(buffer).to_batches()
    finally:
        close = getattr(records, "close", None)
        if close is not None:
            close()


@contextmanager
def open_dbf_batches(
    dbf_bytes: bytes, *, encoding: str, batch_rows: int, backend: Backend | None = None
) -> Iterator[Iterator[pa.RecordBatch]]:
    """Resolve once, then consume without retrying errors through a different parser.

    Both readers own their resources until context exit. Native preflight may
    reject unsupported metadata before iteration, the only capability fallback.
    """
    if batch_rows <= 0:
        raise ValueError("batch_rows must be positive")
    requested = backend if backend is not None else os.environ.get("OMNISUS_DBF_BACKEND", "python")
    if requested not in ("python", "rust", "auto"):
        raise ValueError("DBF backend must be python, rust or auto")
    native = None
    reader = None
    reason = None
    if requested != "python":
        try:
            native = import_module("omnisus_db_dbf")
        except ModuleNotFoundError as exc:
            if exc.name != "omnisus_db_dbf":
                raise
            if requested == "rust":
                raise ImportError(
                    "Rust backend requires the optional omnisus-db-dbf package"
                ) from exc
            reason = "extension_not_installed"
        if native is not None:
            if getattr(native, "API_VERSION", None) != 1:
                raise ImportError("Incompatible omnisus-db-dbf API; expected API_VERSION=1")
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
    actual = "rust" if reader is not None else "python"
    logger.debug(
        "datasus_ftp.dbf_backend",
        backend=actual,
        requested=requested,
        version=getattr(native, "__version__", None) if actual == "rust" else None,
        fallback=reason,
    )
    if reader is None:
        reader = _python_batches(dbf_bytes, encoding, batch_rows)

    def batches():
        try:
            yield from reader
        except Exception as exc:
            if actual == "rust" and isinstance(exc, native.InvalidDbfError):
                raise DbfIntegrityError(str(exc)) from exc
            raise

    stream = batches()
    try:
        yield stream
    finally:
        stream.close()
        reader.close()

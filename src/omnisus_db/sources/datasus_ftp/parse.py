"""DBC bytes → Polars LazyFrame pipeline.

Pipeline (in-memory, no disk writes for DBC; small temp DBF for dbfread2):
    DBC bytes -> datasus_dbc.decompress_bytes() -> DBF bytes
    DBF bytes -> dbfread2.DBF (streaming) -> batches of records
    batches -> polars.DataFrame -> concat -> LazyFrame
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import datasus_dbc
import polars as pl
import structlog
from dbfread2 import DBF

from omnisus_db.transforms.dictionaries import load_dicionario

logger = structlog.get_logger(__name__)

BATCH_ROWS = 100_000

_DELETED_FLAG = 0x2A  # b"*"


class DbfIntegrityError(Exception):
    """Decompressed DBF is inconsistent with its own header record count.

    DATASUS truncation is *silent*: a partial download or partial decompress
    yields a structurally valid DBF that simply stops early — dbfread2 raises
    nothing and 1-2% of records vanish. This error turns that into a hard
    failure. Field-measured on PAAC2401 (-1.0%) and RDAC2401 (-1.8%).
    """


def _read_dbf_geometry(dbf_bytes: bytes) -> tuple[int, int, int] | None:
    """Return (nrec, hdr_len, rec_len) from the DBF header, or None if the
    header is too malformed to interpret (let dbfread2 surface its own error).
    """
    if len(dbf_bytes) < 32:
        return None
    nrec = int.from_bytes(dbf_bytes[4:8], "little")
    hdr_len = int.from_bytes(dbf_bytes[8:10], "little")
    rec_len = int.from_bytes(dbf_bytes[10:12], "little")
    if hdr_len <= 32 or rec_len <= 0:
        return None
    return nrec, hdr_len, rec_len


def _check_dbf_length(dbf_bytes: bytes, *, dataset: str) -> None:
    """Pre-parse gate: the byte payload must hold all declared records."""
    geometry = _read_dbf_geometry(dbf_bytes)
    if geometry is None:
        return
    nrec, hdr_len, rec_len = geometry
    expected = hdr_len + nrec * rec_len
    if len(dbf_bytes) < expected:
        present = max(0, (len(dbf_bytes) - hdr_len) // rec_len)
        raise DbfIntegrityError(
            f"{dataset}: DBF truncated — header declares {nrec} records "
            f"but payload holds only {present} "
            f"({len(dbf_bytes)} bytes < {expected} expected)"
        )


def _check_record_count(dbf_bytes: bytes, parsed: int, *, dataset: str) -> None:
    """Post-parse gate: parsed + deleted must equal the declared count.

    Catches parser early-stops (e.g. an embedded 0x1A EOF marker) that the
    length check cannot see. Deleted rows (flag ``*``) are skipped by
    dbfread2 but occupy slots, so they count toward nrec.
    """
    geometry = _read_dbf_geometry(dbf_bytes)
    if geometry is None:
        return
    nrec, hdr_len, rec_len = geometry
    flags = dbf_bytes[hdr_len : hdr_len + nrec * rec_len : rec_len]
    deleted = flags.count(_DELETED_FLAG)
    if deleted:
        logger.warning(
            "datasus_ftp.deleted_records",
            dataset=dataset,
            deleted=deleted,
        )
    if parsed + deleted != nrec:
        raise DbfIntegrityError(
            f"{dataset}: record count mismatch — header declares {nrec} "
            f"records, parsed {parsed} + {deleted} deleted = {parsed + deleted}"
        )


def _ensure_dbf_terminator(dbf_bytes: bytes) -> bytes:
    """Ensure the DBF field-descriptor area ends with 0x0D.

    Some DATASUS DBC payloads (notably CNES) decompress to a DBF whose
    declared header length leaves a 0x00 in place of the required 0x0D
    field-descriptor terminator. Patch the byte at ``hdr_size - 1`` when
    needed so dbfread2 can parse the file.
    """
    if len(dbf_bytes) < 12:
        return dbf_bytes
    hdr_size = int.from_bytes(dbf_bytes[8:10], "little")
    if hdr_size <= 32 or hdr_size > len(dbf_bytes):
        return dbf_bytes
    if dbf_bytes[hdr_size - 1] == 0x0D:
        return dbf_bytes
    patched = bytearray(dbf_bytes)
    patched[hdr_size - 1] = 0x0D
    return bytes(patched)


def _stream_records(dbf_bytes: bytes, encoding: str) -> Iterator[dict[str, Any]]:
    """Stream records from DBF bytes via a temp file (dbfread2 needs a path)."""
    dbf_bytes = _ensure_dbf_terminator(dbf_bytes)
    with tempfile.NamedTemporaryFile(suffix=".dbf", delete=False) as tmp:
        tmp.write(dbf_bytes)
        tmp_path = tmp.name
    try:
        for record in DBF(tmp_path, encoding=encoding, preload=False):
            yield dict(record)
    finally:
        os.unlink(tmp_path)


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
    dbf_bytes = datasus_dbc.decompress_bytes(dbc_bytes)
    _check_dbf_length(dbf_bytes, dataset=dataset)

    parsed = 0
    batches: list[pl.DataFrame] = []
    buffer: list[dict[str, Any]] = []
    for rec in _stream_records(dbf_bytes, encoding=dic.encoding):
        parsed += 1
        buffer.append(rec)
        if len(buffer) >= BATCH_ROWS:
            batches.append(pl.DataFrame(buffer, infer_schema_length=None))
            buffer.clear()
    if buffer:
        batches.append(pl.DataFrame(buffer, infer_schema_length=None))

    _check_record_count(dbf_bytes, parsed, dataset=dataset)

    if not batches:
        # Empty DBF — return an empty LazyFrame using the dictionary schema names
        df = pl.DataFrame(
            {f["name"]: [] for f in dic.fields},
            schema={f["name"]: pl.Utf8 for f in dic.fields},
        )
    else:
        df = pl.concat(batches, how="diagonal_relaxed")

    # Lowercase column names (DATASUS uses uppercase; canonical is lowercase)
    df = df.rename({c: c.lower() for c in df.columns})

    if ano is not None:
        df = df.with_columns(pl.lit(ano).cast(pl.UInt16).alias("ano"))
    if uf is not None:
        df = df.with_columns(pl.lit(uf).cast(pl.Utf8).alias("uf"))

    logger.info(
        "datasus_ftp.parsed",
        dataset=dataset,
        rows=df.height,
        batches=len(batches),
    )
    return df.lazy()

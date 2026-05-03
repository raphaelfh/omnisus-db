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
from typing import Any

import datasus_dbc
import polars as pl
import structlog
from dbfread2 import DBF

from omnisus_db.transforms.dictionaries import load_dicionario

logger = structlog.get_logger(__name__)

BATCH_ROWS = 100_000


def _stream_records(dbf_bytes: bytes, encoding: str) -> Iterator[dict[str, Any]]:
    """Stream records from DBF bytes via a temp file (dbfread2 needs a path)."""
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
) -> pl.LazyFrame:
    """Decode DBC bytes and return a Polars LazyFrame.

    Args:
        dbc_bytes: raw DBC payload from FTP.
        dataset: dataset name (e.g. "sim_do") — used to look up encoding from
            the Frictionless YAML.
        ano, uf: optionally injected as canonical partition columns.

    Raises:
        FileNotFoundError: if the dataset has no Frictionless YAML.
        Exception: bubbles from datasus_dbc / dbfread2 on bad input.
    """
    dic = load_dicionario(dataset)  # raises FileNotFoundError if unknown
    dbf_bytes = datasus_dbc.decompress_bytes(dbc_bytes)

    batches: list[pl.DataFrame] = []
    buffer: list[dict[str, Any]] = []
    for rec in _stream_records(dbf_bytes, encoding=dic.encoding):
        buffer.append(rec)
        if len(buffer) >= BATCH_ROWS:
            batches.append(pl.DataFrame(buffer, infer_schema_length=None))
            buffer.clear()
    if buffer:
        batches.append(pl.DataFrame(buffer, infer_schema_length=None))

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

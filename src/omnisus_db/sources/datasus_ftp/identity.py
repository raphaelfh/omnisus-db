"""Source identity, declared in the dictionary and checked once per file.

A DATASUS file is identified by the *mode* of its year column (and, when the
layout has one, of its agravo code): the whole file is rejected when the
mode is wrong, while the few off-year or mis-typed records real files carry
(tuberculosis, zika) stay in the lake untouched. Which columns and which code
is a per-dataset fact, so it lives in the YAML's ``x-identity`` block, and
changing it changes ``parser_version`` for free.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from omnisus_db.sources._base import ScopeKey
from omnisus_db.transforms.dictionaries import Dicionario


def _mode(frame: pl.LazyFrame, column: str) -> str | None:
    """Most frequent trimmed text value; ties break on the value, so the answer is deterministic."""
    top = (
        frame.select(pl.col(column).cast(pl.String).str.strip_chars().alias("v"))
        .group_by("v")
        .len()
        .sort(["len", "v"], descending=[True, False])
        .limit(1)
        .collect()
    )
    return top["v"][0] if top.height else None


def validate_identity(staging: Path, dicionario: Dicionario, scope: ScopeKey) -> None:
    spec = dicionario.raw.get("x-identity")
    if not spec:
        return
    frame = pl.scan_parquet(staging)
    columns = set(frame.collect_schema().names())
    year_column = spec["year_column"]
    if year_column not in columns:
        raise ValueError(f"{dicionario.name}: identity column {year_column!r} is missing")
    year = _mode(frame, year_column)
    if year is None:
        raise ValueError(f"{dicionario.name}: empty source file")
    if year != str(scope.ano):
        raise ValueError(
            f"{dicionario.name}: most frequent {year_column} is {year}, not the scope year {scope.ano}"
        )
    code_column = spec.get("code_column")
    if code_column and code_column in columns:
        code = _mode(frame, code_column)
        if code != spec["code"]:
            raise ValueError(
                f"{dicionario.name}: most frequent {code_column} is {code!r}, not {spec['code']!r}"
            )

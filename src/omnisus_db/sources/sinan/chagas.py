"""Validate the identity of a complete preliminary acute Chagas source.

This validates the acquisition contract, not clinical completeness or case
confirmation. Original codes and geography remain unchanged in the lake.
"""

from pathlib import Path

import polars as pl

from omnisus_db.sources._base import ScopeKey


def validate_staging(path: Path, scope: ScopeKey) -> None:
    if scope.uf is not None or scope.mes is not None:
        raise ValueError("Chagas preliminary source requires a national annual scope")
    frame = pl.scan_parquet(path)
    required = {"id_agravo", "nu_ano", "sg_uf_not"}
    if not required <= set(frame.collect_schema().names()):
        raise ValueError("Chagas source is missing identity columns")
    valid = (
        (pl.col("id_agravo").cast(pl.String).str.strip_chars() == "B571")
        & (pl.col("nu_ano").cast(pl.String).str.strip_chars() == str(scope.ano))
    ).fill_null(False)
    count, invalid = frame.select(pl.len(), (~valid).sum().alias("invalid")).collect().row(0)
    if count == 0 or invalid:
        raise ValueError("Chagas source has empty, wrong-year or wrong-agravo records")

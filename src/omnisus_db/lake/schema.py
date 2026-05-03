"""Canonical column types shared across datasets."""

from __future__ import annotations

import pyarrow as pa

CANONICAL_TYPES: dict[str, pa.DataType] = {
    "ano": pa.uint16(),
    "mes": pa.uint8(),
    "uf": pa.dictionary(pa.int8(), pa.string()),
    "competencia": pa.string(),
    "codmunres": pa.string(),
    "codigo_ibge": pa.string(),
}

CANONICAL_DDL: dict[str, str] = {
    "ano": "USMALLINT",
    "mes": "UTINYINT",
    "uf": "VARCHAR",
    "competencia": "VARCHAR",
    "codmunres": "VARCHAR",
    "codigo_ibge": "VARCHAR",
}


def canonical_type(column: str) -> pa.DataType:
    """Return the canonical Arrow type for a well-known column."""
    return CANONICAL_TYPES[column]


def ddl_for_field(column: str) -> str:
    """Return the DuckDB DDL type for a well-known column."""
    return CANONICAL_DDL[column]

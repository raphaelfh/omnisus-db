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


class UnsafeSchemaError(ValueError):
    """A schema change has no verified lossless conversion."""


def compatible_type(existing: str, incoming: str) -> str:
    """Return a common lossless SQL type, or reject before implicit SQL casts.

    Families are deliberately narrow. Decimal scale changes, signed/unsigned
    mixing and numeric/string conversions require a domain migration.
    """
    if existing == incoming:
        return existing
    families = (
        ("TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT"),
        ("UTINYINT", "USMALLINT", "UINTEGER", "UBIGINT", "UHUGEINT"),
        ("FLOAT", "DOUBLE"),
    )
    for family in families:
        if existing in family and incoming in family:
            return family[max(family.index(existing), family.index(incoming))]
    raise UnsafeSchemaError(
        f"unsafe schema type change: {existing} versus {incoming}; explicit migration required"
    )

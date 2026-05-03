"""Reusable Polars expressions for code normalization."""

from __future__ import annotations

import polars as pl


def lpad_6(expr: pl.Expr) -> pl.Expr:
    """Left-pad a string column to 6 chars with '0' (IBGE municipio short form)."""
    return expr.cast(pl.Utf8).str.zfill(6)


def normalize_uf(expr: pl.Expr) -> pl.Expr:
    """Trim + uppercase a UF column."""
    return expr.cast(pl.Utf8).str.strip_chars().str.to_uppercase()


def parse_ddmmyyyy(expr: pl.Expr) -> pl.Expr:
    """Parse a DDMMYYYY date string into pl.Date."""
    return expr.cast(pl.Utf8).str.strptime(pl.Date, format="%d%m%Y", strict=False)

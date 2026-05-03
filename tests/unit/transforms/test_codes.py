"""Tests for transforms.codes — Polars utility expressions."""

from __future__ import annotations

import polars as pl

from omnisus_db.transforms.codes import lpad_6, normalize_uf, parse_ddmmyyyy


def test_lpad_6_pads_5_digit_codes() -> None:
    df = pl.DataFrame({"code": ["12345", "123456", None]})
    out = df.with_columns(lpad_6(pl.col("code")).alias("padded"))
    assert out["padded"].to_list() == ["012345", "123456", None]


def test_normalize_uf_uppercases_and_strips() -> None:
    df = pl.DataFrame({"uf": [" sp ", "rj", "MG", None]})
    out = df.with_columns(normalize_uf(pl.col("uf")).alias("uf_n"))
    assert out["uf_n"].to_list() == ["SP", "RJ", "MG", None]


def test_parse_ddmmyyyy_handles_zero_padded() -> None:
    df = pl.DataFrame({"d": ["01012024", "31122023", None]})
    out = df.with_columns(parse_ddmmyyyy(pl.col("d")).alias("dt"))
    parsed = out["dt"].to_list()
    assert parsed[0].isoformat() == "2024-01-01"
    assert parsed[1].isoformat() == "2023-12-31"
    assert parsed[2] is None

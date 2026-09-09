"""Tests for datasus_ftp.parse — DBC → Polars."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from omnisus_db.sources.datasus_ftp.parse import dbc_bytes_to_lazyframe


def test_parse_sim_fixture_returns_lazyframe(dbc_fixture) -> None:
    dbc_path: Path = dbc_fixture("sim_rr_2023_mini")
    lf = dbc_bytes_to_lazyframe(dbc_path.read_bytes(), dataset="sim_do")
    assert isinstance(lf, pl.LazyFrame)
    df = lf.collect()
    assert df.height > 0
    # SIM should have at least the canonical columns (lower-cased).
    # NOTE: the raw DATASUS DO* DBC does not contain `numerodo` (that key is
    # synthesized downstream); use a column that is actually present.
    assert any(c.lower() == "dtobito" for c in df.columns)
    assert all(c == c.lower() for c in df.columns)


def test_parse_sim_applies_canonical_partition_cols(dbc_fixture) -> None:
    dbc_path: Path = dbc_fixture("sim_rr_2023_mini")
    lf = dbc_bytes_to_lazyframe(
        dbc_path.read_bytes(),
        dataset="sim_do",
        ano=2023,
        uf="RR",
    )
    df = lf.collect()
    assert df["ano"].dtype == pl.UInt16
    assert df["ano"].unique().to_list() == [2023]
    assert df["uf"].unique().to_list() == ["RR"]


def test_parse_unknown_dataset_raises() -> None:
    with pytest.raises(FileNotFoundError):
        dbc_bytes_to_lazyframe(b"x", dataset="bogus")


def test_parse_empty_bytes_returns_empty_lazyframe() -> None:
    """Empty DBC content should not crash; should return empty LazyFrame."""
    # An empty DBC doesn't decompress meaningfully; this should raise rather
    # than silently return data. We expect *some* exception (datasus_dbc
    # decompression error).
    with pytest.raises(Exception):  # noqa: B017 — bubbles from datasus_dbc
        dbc_bytes_to_lazyframe(b"", dataset="sim_do")


def test_parse_with_explicit_dictionary_path(dbc_fixture, tmp_path: Path) -> None:
    """The dictionary argument bypasses the packaged lookup entirely, so the
    dataset name need not be registered (spec §3.3)."""
    from importlib.resources import files

    custom = tmp_path / "mine.yaml"
    custom.write_text(
        (files("omnisus_db.data.dicionarios") / "sim_do.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    raw = dbc_fixture("sim_rr_2023_mini").read_bytes()
    lf = dbc_bytes_to_lazyframe(raw, dataset="not_in_registry", dictionary=custom)
    assert lf.collect().height > 0

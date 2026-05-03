"""Tests for Lake.bootstrap_auxiliares."""

from __future__ import annotations

from pathlib import Path

from omnisus_db.lake import Lake


def test_bootstrap_auxiliares_loads_3_tables(tmp_path: Path) -> None:
    lake = Lake.local(f"ducklake:{tmp_path}/x.ducklake")

    lake.bootstrap_auxiliares()

    tables = set(lake.tables())
    assert {"aux_uf", "aux_municipios", "aux_cid10"} <= tables

    n = lake.connect().execute("SELECT count(*) FROM lake.aux_uf").fetchone()[0]
    assert n == 27

    lake.close()


def test_bootstrap_idempotent(tmp_path: Path) -> None:
    lake = Lake.local(f"ducklake:{tmp_path}/x.ducklake")
    lake.bootstrap_auxiliares()
    lake.bootstrap_auxiliares()
    n = lake.connect().execute("SELECT count(*) FROM lake.aux_uf").fetchone()[0]
    assert n == 27
    lake.close()

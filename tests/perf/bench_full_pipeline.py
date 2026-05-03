"""Benchmark the full DBC->lake pipeline (sim_do)."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from omnisus_db.lake import Lake
from omnisus_db.sources.datasus_ftp.parse import dbc_bytes_to_lazyframe


@pytest.mark.perf
def test_bench_full_pipeline_sim(benchmark, dbc_fixture, tmp_path) -> None:
    fixture: Path = dbc_fixture("sim_rr_2023_mini")
    raw = fixture.read_bytes()

    def run() -> int:
        lake = Lake.local(f"ducklake:{tmp_path}/bench-{benchmark.name}.ducklake")
        try:
            lf: pl.LazyFrame = dbc_bytes_to_lazyframe(raw, dataset="sim_do", ano=2023, uf="RR")
            result = lake.ingest("sim_do", lf, partition_by=("ano", "uf"))
            return result.rows
        finally:
            lake.close()

    rows = benchmark.pedantic(run, rounds=3, iterations=1)
    assert rows > 0

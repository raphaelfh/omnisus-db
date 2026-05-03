"""Benchmark DBC->DBF->Polars parse step in isolation."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnisus_db.sources.datasus_ftp.parse import dbc_bytes_to_lazyframe


@pytest.mark.perf
def test_bench_dbf_parse_sim(benchmark, dbc_fixture) -> None:
    fixture: Path = dbc_fixture("sim_rr_2023_mini")
    raw = fixture.read_bytes()

    def run() -> int:
        lf = dbc_bytes_to_lazyframe(raw, dataset="sim_do", ano=2023, uf="RR")
        return lf.collect().height

    rows = benchmark(run)
    assert rows > 0

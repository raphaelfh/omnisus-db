"""End-to-end: fixture DBC -> import_sim() -> lake -> query."""

from __future__ import annotations

from pathlib import Path

import pytest

import omnisus_db as odb
from omnisus_db.lake import Lake


@pytest.mark.integration
def test_import_sim_e2e_with_fixture(monkeypatch, tmp_path: Path, dbc_fixture) -> None:
    fixture = dbc_fixture("sim_rr_2023_mini")
    fixture_bytes = fixture.read_bytes()

    async def fake_fetch(*, dataset, scope, **_kw):
        return fixture_bytes

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp.fetch.fetch_dbc_bytes", fake_fetch)
    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)

    target = f"ducklake:{tmp_path}/test.ducklake"
    report = odb.import_sim(years=[2023], ufs=["RR"], target=target)
    assert not report.failed, report.failed
    assert report.rows > 0

    lake = Lake.local(target)
    n = (
        lake.connect()
        .execute("SELECT count(*) FROM lake.sim_obitos WHERE ano=2023 AND uf='RR'")
        .fetchone()[0]
    )
    assert n > 0
    lake.close()

"""End-to-end: CNES fixture -> import_cnes_estabelecimentos() -> lake -> query."""

from __future__ import annotations

from pathlib import Path

import pytest

import omnisus_db as odb
from omnisus_db.lake import Lake


@pytest.mark.integration
def test_import_cnes_estabelecimentos_e2e(monkeypatch, tmp_path: Path, dbc_fixture) -> None:
    fixture_bytes = dbc_fixture("cnes_rr_2024_01_mini").read_bytes()

    async def fake_fetch(*, dataset, scope, **_kw):
        return fixture_bytes

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp.fetch.fetch_dbc_bytes", fake_fetch)
    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)

    target = f"ducklake:{tmp_path}/test.ducklake"
    odb.import_cnes_estabelecimentos(years=[2024], months=[1], ufs=["RR"], target=target)

    lake = Lake.local(target)
    n = (
        lake.connect()
        .execute("SELECT count(*) FROM lake.cnes_estabelecimentos WHERE ano=2024 AND mes=1")
        .fetchone()[0]
    )
    assert n > 0
    lake.close()

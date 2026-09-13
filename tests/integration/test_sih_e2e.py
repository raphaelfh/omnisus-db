"""End-to-end: SIH monthly fixture -> import_dataset("sih_aih_reduzida") -> lake -> query."""

from __future__ import annotations

from pathlib import Path

import pytest

import omnisus_db as odb
from omnisus_db.lake import Lake


@pytest.mark.integration
def test_import_sih_monthly(monkeypatch, tmp_path: Path, dbc_fixture) -> None:
    fixture_bytes = dbc_fixture("sih_rr_2024_01_mini").read_bytes()

    async def fake_fetch(*, dataset, scope, **_kw):
        return fixture_bytes

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp.fetch.fetch_dbc_bytes", fake_fetch)
    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)

    target = f"ducklake:{tmp_path}/test.ducklake"
    odb.import_dataset(
        "sih_aih_reduzida",
        scopes=odb.scopes_for("sih_aih_reduzida", years=[2024], ufs=["RR"], months=[1]),
        target=target,
    )

    lake = Lake.local(target)
    rows = (
        lake.connect()
        .execute("SELECT count(*) FROM lake.sih_aih_reduzida WHERE ano=2024 AND uf='RR' AND mes=1")
        .fetchone()[0]
    )
    assert rows > 0
    lake.close()

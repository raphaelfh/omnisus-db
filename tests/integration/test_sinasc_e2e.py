"""End-to-end: SINASC fixture -> import_dataset("sinasc_nascidos_vivos") -> lake -> query."""

from __future__ import annotations

from pathlib import Path

import pytest

import omnisus_db as odb
from omnisus_db.lake import Lake


@pytest.mark.integration
def test_import_sinasc_with_fixture(monkeypatch, tmp_path: Path, dbc_fixture) -> None:
    fixture_bytes = dbc_fixture("sinasc_rr_2022_mini").read_bytes()

    async def fake_fetch(*, dataset, scope, **_kw):
        return fixture_bytes

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp.fetch.fetch_dbc_bytes", fake_fetch)
    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)
    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.release_map", lambda d: {})

    target = f"ducklake:{tmp_path}/test.ducklake"
    odb.import_dataset(
        "sinasc_nascidos_vivos",
        scopes=odb.scopes_for("sinasc_nascidos_vivos", years=[2022], ufs=["RR"]),
        target=target,
    )

    lake = Lake.local(target)
    n = (
        lake.connect()
        .execute("SELECT count(*) FROM lake.sinasc_nascidos_vivos WHERE ano=2022 AND uf='RR'")
        .fetchone()[0]
    )
    assert n > 0
    lake.close()

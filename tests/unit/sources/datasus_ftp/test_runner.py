"""Tests for the generic DATASUS-FTP runner."""

from __future__ import annotations

import pytest

from omnisus_db.lake import Lake
from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp._runner import import_scope


@pytest.mark.asyncio
async def test_import_scope_sim_uses_fixture(monkeypatch, tmp_path, dbc_fixture) -> None:
    fixture = dbc_fixture("sim_rr_2023_mini")
    fixture_bytes = fixture.read_bytes()

    async def fake_fetch(*, dataset: str, scope: ScopeKey, **_kw: object) -> bytes:
        return fixture_bytes

    monkeypatch.setattr(
        "omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes",
        fake_fetch,
    )

    lake = Lake.local(f"ducklake:{tmp_path}/x.ducklake")
    result = await import_scope(
        dataset="sim_do",
        scope=ScopeKey(uf="RR", ano=2023),
        lake=lake,
    )
    assert result.rows > 0
    assert "sim_do" in lake.tables()
    lake.close()


@pytest.mark.asyncio
async def test_import_scope_sih_requires_mes(tmp_path) -> None:
    lake = Lake.local(f"ducklake:{tmp_path}/x.ducklake")
    with pytest.raises(ValueError, match="monthly"):
        await import_scope(
            dataset="sih_rd",
            scope=ScopeKey(uf="SP", ano=2024, mes=None),
            lake=lake,
        )
    lake.close()


def test_get_config_returns_partition_by() -> None:
    from omnisus_db.sources.datasus_ftp.datasets import get_config

    cfg = get_config("sim_do")
    assert cfg.partition_by == ("ano", "uf")
    assert cfg.monthly is False

    sih = get_config("sih_rd")
    assert sih.partition_by == ("ano", "uf", "mes")
    assert sih.monthly is True


def test_get_config_unknown_raises() -> None:
    import pytest as _pt

    from omnisus_db.sources.datasus_ftp.datasets import get_config

    with _pt.raises(ValueError):
        get_config("bogus")

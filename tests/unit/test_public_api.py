"""Tests for the top-level API: scopes_for, import_dataset, aliases (spec §5.1)."""

from __future__ import annotations

from pathlib import Path

import omnisus_db as odb
from omnisus_db.lake import Lake
from omnisus_db.sources._base import ScopeKey


def test_scopes_for_yearly_ignores_months() -> None:
    assert odb.scopes_for("sim_do", years=[2023], ufs=["RR"], months=[1, 2]) == [
        ScopeKey(uf="RR", ano=2023)
    ]


def test_scopes_for_monthly_defaults_to_twelve_months() -> None:
    scopes = odb.scopes_for("sih_rd", years=[2024], ufs=["RR"])
    assert len(scopes) == 12
    assert scopes[0] == ScopeKey(uf="RR", ano=2024, mes=1)
    assert scopes[-1] == ScopeKey(uf="RR", ano=2024, mes=12)


def test_scopes_for_all_ufs_when_none() -> None:
    assert len(odb.scopes_for("sim_do", years=[2023])) == len(odb.ALL_UFS) == 27


def test_scopes_for_order_is_year_then_uf_then_month() -> None:
    scopes = odb.scopes_for("sih_rd", years=[2023, 2024], ufs=["AC", "RR"], months=[1, 2])
    assert [(s.ano, s.uf, s.mes) for s in scopes] == [
        (2023, "AC", 1),
        (2023, "AC", 2),
        (2023, "RR", 1),
        (2023, "RR", 2),
        (2024, "AC", 1),
        (2024, "AC", 2),
        (2024, "RR", 1),
        (2024, "RR", 2),
    ]


def test_scopes_for_accepts_alias_and_value() -> None:
    from omnisus_db.sources.datasus_ftp.datasets import REGISTRY

    by_alias = odb.scopes_for("sim", years=[2023], ufs=["RR"])
    by_value = odb.scopes_for(REGISTRY["sim_do"], years=[2023], ufs=["RR"])
    assert by_alias == by_value == [ScopeKey(uf="RR", ano=2023)]


def _fake_fetch_from(monkeypatch, payload: bytes) -> None:
    async def fake_fetch(*, dataset, scope, **_kw: object) -> bytes:
        return payload

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)


def test_import_dataset_reaches_the_sia_family(monkeypatch, tmp_path: Path, dbc_fixture) -> None:
    """Seven SIA datasets had no public door (spec §1.1). Now every row has one."""
    _fake_fetch_from(monkeypatch, dbc_fixture("sia_atd_rr_2024_01_mini").read_bytes())
    target = f"ducklake:{tmp_path}/api.ducklake"

    results = odb.import_dataset(
        "sia_atd",
        scopes=odb.scopes_for("sia_atd", years=[2024], ufs=["RR"], months=[1]),
        target=target,
    )

    assert len(results) == 1
    assert results[0].rows > 0
    with Lake.local(target) as lake:
        assert "sia_atd" in lake.tables()


def test_import_dataset_accepts_alias_and_hand_built_scopes(
    monkeypatch, tmp_path: Path, dbc_fixture
) -> None:
    """Planning is composition: any list[ScopeKey] works (spec §5.1)."""
    _fake_fetch_from(monkeypatch, dbc_fixture("sim_rr_2023_mini").read_bytes())
    target = f"ducklake:{tmp_path}/alias.ducklake"

    results = odb.import_dataset("sim", scopes=[ScopeKey(uf="RR", ano=2023)], target=target)

    assert results[0].rows > 0
    with Lake.local(target) as lake:
        assert "sim_do" in lake.tables()


def test_import_sim_alias_still_returns_a_list(monkeypatch, tmp_path: Path, dbc_fixture) -> None:
    """Back-compat for this plan: aliases keep list[ImportResult] until the
    tolerance plan introduces ImportReport (spec §5.1 compatibility note)."""
    _fake_fetch_from(monkeypatch, dbc_fixture("sim_rr_2023_mini").read_bytes())
    results = odb.import_sim(years=[2023], ufs=["RR"], target=f"ducklake:{tmp_path}/s.ducklake")
    assert isinstance(results, list)
    assert results[0].rows > 0


def test_default_target_is_exported_from_lake() -> None:
    from omnisus_db.lake import DEFAULT_TARGET

    assert DEFAULT_TARGET == "ducklake:./omnisus.ducklake"
    assert odb.DEFAULT_TARGET is DEFAULT_TARGET

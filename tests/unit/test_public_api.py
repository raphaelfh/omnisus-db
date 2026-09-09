"""Tests for the top-level API: scopes_for, import_dataset, aliases (spec §5.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

import omnisus_db as odb
from omnisus_db.lake import Lake
from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import REGISTRY


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


_FIXTURE_FOR: dict[str, tuple[str, ScopeKey]] = {
    "sim_do": ("sim_rr_2023_mini", ScopeKey(uf="RR", ano=2023)),
    "sinasc_nv": ("sinasc_rr_2022_mini", ScopeKey(uf="RR", ano=2022)),
    "sih_rd": ("sih_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
    "sia_bi": ("sia_bi_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
    "sia_am": ("sia_am_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
    "sia_aq": ("sia_aq_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
    "sia_atd": ("sia_atd_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
    "sia_ad": ("sia_ad_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
    "sia_ps": ("sia_ps_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
    "sia_abo": ("sia_abo_sp_2024_01_mini", ScopeKey(uf="SP", ano=2024, mes=1)),
    "cnes_st": ("cnes_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
}


def test_fixture_map_covers_every_registry_row() -> None:
    """A new registry row without a fixture here would silently skip Tier 2
    coverage — assert the map is complete instead."""
    assert set(_FIXTURE_FOR) == set(REGISTRY)


@pytest.mark.parametrize("dataset_name", sorted(REGISTRY))
def test_import_dataset_reaches_every_registry_row(
    dataset_name: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, dbc_fixture
) -> None:
    """Tier 2: every registry row is proven end to end, not just sia_atd and
    sia_bi (spec §6) — this is what makes the SIA gap impossible."""
    fixture_name, scope = _FIXTURE_FOR[dataset_name]
    _fake_fetch_from(monkeypatch, dbc_fixture(fixture_name).read_bytes())
    target = f"ducklake:{tmp_path}/{dataset_name}.ducklake"

    results = odb.import_dataset(dataset_name, scopes=[scope], target=target)

    assert results[0].rows > 0
    with Lake.local(target) as lake:
        assert dataset_name in lake.tables()


def test_available_and_browse_are_exported() -> None:
    import omnisus_db as odb

    for name in ("available", "browse", "FtpEntry", "FtpPathNotFound", "FtpUnavailable"):
        assert name in odb.__all__, name
        assert hasattr(odb, name), name


def test_available_needs_no_lake(monkeypatch, tmp_path: Path) -> None:
    """Discovery is decoupled from the lake — it works before `init` (spec §4.4)."""
    import omnisus_db as odb

    monkeypatch.setenv("OMNISUS_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list",
        lambda _p, _t: ["01-31-20  02:48PM                76107 DOAC1996.dbc"],
    )
    assert odb.available("sim_do") == [ScopeKey(uf="AC", ano=1996)]
    assert not list(tmp_path.glob("*.ducklake"))

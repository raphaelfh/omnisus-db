"""Tests for the top-level API: scopes_for, import_dataset (spec §5.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

import omnisus_db as odb
from omnisus_db.lake import Lake
from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import REGISTRY


def test_scopes_for_yearly_ignores_months() -> None:
    assert odb.scopes_for("sim_obitos", years=[2023], ufs=["RR"], months=[1, 2]) == [
        ScopeKey(uf="RR", ano=2023)
    ]


def test_scopes_for_monthly_defaults_to_twelve_months() -> None:
    scopes = odb.scopes_for("sih_aih_reduzida", years=[2024], ufs=["RR"])
    assert len(scopes) == 12
    assert scopes[0] == ScopeKey(uf="RR", ano=2024, mes=1)
    assert scopes[-1] == ScopeKey(uf="RR", ano=2024, mes=12)


def test_scopes_for_all_ufs_when_none() -> None:
    assert len(odb.scopes_for("sim_obitos", years=[2023])) == len(odb.ALL_UFS) == 27


def test_scopes_for_order_is_year_then_uf_then_month() -> None:
    scopes = odb.scopes_for(
        "sih_aih_reduzida", years=[2023, 2024], ufs=["AC", "RR"], months=[1, 2]
    )
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


def test_scopes_for_accepts_a_dataset_value() -> None:
    by_key = odb.scopes_for("sim_obitos", years=[2023], ufs=["RR"])
    by_value = odb.scopes_for(REGISTRY["sim_obitos"], years=[2023], ufs=["RR"])
    assert by_key == by_value == [ScopeKey(uf="RR", ano=2023)]


def _fake_fetch_from(monkeypatch, payload: bytes) -> None:
    async def fake_fetch(*, dataset, scope, **_kw: object) -> bytes:
        return payload

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)


def test_import_dataset_reaches_the_sia_family(monkeypatch, tmp_path: Path, dbc_fixture) -> None:
    """Seven SIA datasets had no public door (spec §1.1). Now every row has one."""
    _fake_fetch_from(monkeypatch, dbc_fixture("sia_atd_rr_2024_01_mini").read_bytes())
    target = f"ducklake:{tmp_path}/api.ducklake"

    report = odb.import_dataset(
        "sia_apac_tratamento_dialitico",
        scopes=odb.scopes_for(
            "sia_apac_tratamento_dialitico", years=[2024], ufs=["RR"], months=[1]
        ),
        target=target,
    )

    assert len(report.outcomes) == 1
    assert report.ok[0].result is not None
    assert report.rows > 0
    with Lake.local(target) as lake:
        assert "sia_apac_tratamento_dialitico" in lake.tables()


def test_import_dataset_accepts_hand_built_scopes(
    monkeypatch, tmp_path: Path, dbc_fixture
) -> None:
    """Planning is composition: any list[ScopeKey] works (spec §5.1)."""
    _fake_fetch_from(monkeypatch, dbc_fixture("sim_rr_2023_mini").read_bytes())
    target = f"ducklake:{tmp_path}/handbuilt.ducklake"

    report = odb.import_dataset("sim_obitos", scopes=[ScopeKey(uf="RR", ano=2023)], target=target)

    assert report.rows > 0
    with Lake.local(target) as lake:
        assert "sim_obitos" in lake.tables()


def test_import_sim_alias_returns_a_report(monkeypatch, tmp_path: Path, dbc_fixture) -> None:
    """Back-compat for this plan: aliases keep list[ImportResult] until the
    tolerance plan introduces ImportReport (spec §5.1 compatibility note)."""
    _fake_fetch_from(monkeypatch, dbc_fixture("sim_rr_2023_mini").read_bytes())
    report = odb.import_sim(years=[2023], ufs=["RR"], target=f"ducklake:{tmp_path}/s.ducklake")
    assert isinstance(report, odb.ImportReport)
    assert not report.failed
    assert report.rows > 0


def test_default_target_is_exported_from_lake() -> None:
    from omnisus_db.lake import DEFAULT_TARGET

    assert DEFAULT_TARGET == "ducklake:./omnisus.ducklake"
    assert odb.DEFAULT_TARGET is DEFAULT_TARGET


def test_import_aborted_error_is_public_and_retains_progress_payload() -> None:
    report = odb.ImportReport(outcomes=())
    unresolved = ((0, ScopeKey(uf="RR", ano=2023)),)

    error = odb.ImportAbortedError(report, unresolved)

    assert isinstance(error, RuntimeError)
    assert error.report is report
    assert error.unresolved == unresolved


_FIXTURE_FOR: dict[str, tuple[str, ScopeKey]] = {
    "sinan_chagas": ("sinan_chagas_br_2023", ScopeKey(uf=None, ano=2023)),
    "sim_obitos": ("sim_rr_2023_mini", ScopeKey(uf="RR", ano=2023)),
    "sinasc_nascidos_vivos": ("sinasc_rr_2022_mini", ScopeKey(uf="RR", ano=2022)),
    "sih_aih_reduzida": ("sih_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
    "sia_bpa_individualizado": ("sia_bi_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
    "sia_apac_medicamentos": ("sia_am_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
    "sia_apac_quimioterapia": ("sia_aq_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
    "sia_apac_tratamento_dialitico": (
        "sia_atd_rr_2024_01_mini",
        ScopeKey(uf="RR", ano=2024, mes=1),
    ),
    "sia_apac_laudos_diversos": ("sia_ad_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
    "sia_psicossocial": ("sia_ps_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
    "sia_apac_cirurgia_bariatrica": (
        "sia_abo_sp_2024_01_mini",
        ScopeKey(uf="SP", ano=2024, mes=1),
    ),
    "cnes_estabelecimentos": ("cnes_rr_2024_01_mini", ScopeKey(uf="RR", ano=2024, mes=1)),
}


def test_fixture_map_covers_every_registry_row() -> None:
    """A new registry row without a fixture here would silently skip Tier 2
    coverage — assert the map is complete instead."""
    assert set(_FIXTURE_FOR) == set(REGISTRY)


def test_the_fixture_builder_can_rebuild_every_fixture_this_map_names() -> None:
    """conftest tells a developer with a missing fixture to run
    scripts/build_fixtures.py. That was a dead end for 6 of the 11 datasets,
    because the script carried its own hand-copied path map covering 5. Assert
    the two agree, so the instruction stays true."""
    import importlib.util

    script = Path(__file__).resolve().parents[2] / "scripts" / "build_fixtures.py"
    spec = importlib.util.spec_from_file_location("build_fixtures", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    built = {
        dataset: (fname.removesuffix(".dbc"), scope) for dataset, scope, fname in module.TARGETS
    }
    assert built == _FIXTURE_FOR


@pytest.mark.parametrize("dataset_name", sorted(REGISTRY))
def test_import_dataset_reaches_every_registry_row(
    dataset_name: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, dbc_fixture
) -> None:
    """Tier 2: every registry row is proven end to end, not just sia_apac_tratamento_dialitico and
    sia_bpa_individualizado (spec §6) — this is what makes the SIA gap impossible."""
    fixture_name, scope = _FIXTURE_FOR[dataset_name]
    _fake_fetch_from(monkeypatch, dbc_fixture(fixture_name).read_bytes())
    target = f"ducklake:{tmp_path}/{dataset_name}.ducklake"

    report = odb.import_dataset(dataset_name, scopes=[scope], target=target)

    assert not report.failed, report.failed
    assert report.rows > 0
    with Lake.local(target) as lake:
        assert dataset_name in lake.tables()


def test_available_and_browse_are_exported() -> None:
    import omnisus_db as odb

    for name in ("available", "browse", "FtpEntry", "FtpPathNotFound", "FtpUnavailable"):
        assert name in odb.__all__, name
        assert hasattr(odb, name), name


def test_policy_type_and_dataset_resolver_are_exported() -> None:
    from typing import get_args

    assert {"ImportPolicy", "resolve"} <= set(odb.__all__)
    assert get_args(odb.ImportPolicy) == ("append", "skip_same", "error_if_exists", "replace")
    assert odb.resolve("sim_obitos").name == "sim_obitos"


def test_catalog_attach_error_is_exported() -> None:
    from omnisus_db.lake import CatalogAttachError

    assert "CatalogAttachError" in odb.__all__
    assert odb.CatalogAttachError is CatalogAttachError
    assert issubclass(CatalogAttachError, RuntimeError)


def test_lake_reader_is_exported() -> None:
    from omnisus_db.lake import LakeReader

    assert "LakeReader" in odb.__all__
    assert odb.LakeReader is LakeReader


def test_products_state_what_each_importer_family_supports() -> None:
    """The Omnisus app rebuilt this catalog by hand, treating ibge_populacao and
    cnes_master as special cases. One frozen record per family says it here."""
    from dataclasses import FrozenInstanceError
    from typing import get_args

    products = {p.name: p for p in odb.products()}
    assert set(products) == set(REGISTRY) | {"ibge_populacao", "cnes_master"}
    assert [d.name for d in odb.datasets()] == list(REGISTRY)
    for dataset in odb.datasets():
        product = products[dataset.name]
        assert product.dataset is dataset
        if dataset.geography == "national":
            assert product.scope_fields == ("ano",)
        else:
            assert product.scope_fields == (
                ("uf", "ano", "mes") if dataset.monthly else ("uf", "ano")
            )
        assert product.policies == get_args(odb.ImportPolicy)
        assert (product.reconcile_by, product.inventory) == ("run_id", True)
    assert products["ibge_populacao"] == odb.Product(
        "ibge_populacao", None, ("product", "ano"), ("append",), "publication_id", False
    )
    assert products["cnes_master"] == odb.Product(
        "cnes_master", None, (), ("append",), "rerun", False
    )
    with pytest.raises(FrozenInstanceError):
        products["ibge_populacao"].inventory = True  # type: ignore[misc]
    assert {"Product", "datasets", "products"} <= set(odb.__all__)


def test_deletion_result_is_exported() -> None:
    from omnisus_db.lake.publication import DeletionResult

    assert "DeletionResult" in odb.__all__
    assert odb.DeletionResult is DeletionResult


def test_available_needs_no_lake(monkeypatch, tmp_path: Path) -> None:
    """Discovery is decoupled from the lake — it works before `init` (spec §4.4)."""
    import omnisus_db as odb

    monkeypatch.setenv("OMNISUS_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list",
        lambda _p, _t: ["01-31-20  02:48PM                76107 DOAC1996.dbc"],
    )
    assert odb.available("sim_obitos") == [ScopeKey(uf="AC", ano=1996)]
    assert not list(tmp_path.glob("*.ducklake"))

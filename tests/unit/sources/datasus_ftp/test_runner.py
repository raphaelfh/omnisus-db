"""Tests for the generic DATASUS-FTP runner."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from omnisus_db.lake import Lake
from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp._runner import import_scope
from omnisus_db.sources.datasus_ftp.datasets import REGISTRY
from omnisus_db.sources.datasus_ftp.fetch import FtpFileNotFound


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
    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.release_map", lambda d: {})

    lake = Lake.local(f"ducklake:{tmp_path}/x.ducklake")
    result = await import_scope(
        dataset="sim_obitos",
        scope=ScopeKey(uf="RR", ano=2023),
        lake=lake,
    )
    assert result.rows > 0
    assert "sim_obitos" in lake.tables()
    lake.close()


@pytest.mark.asyncio
async def test_import_scope_sih_requires_mes(tmp_path) -> None:
    lake = Lake.local(f"ducklake:{tmp_path}/x.ducklake")
    with pytest.raises(ValueError, match="monthly"):
        await import_scope(
            dataset="sih_aih_reduzida",
            scope=ScopeKey(uf="SP", ano=2024, mes=None),
            lake=lake,
        )
    lake.close()


def test_resolve_returns_partition_by() -> None:
    from omnisus_db.sources.datasus_ftp.datasets import resolve

    cfg = resolve("sim_obitos")
    assert cfg.partition_by == ("ano", "uf")
    assert cfg.monthly is False

    sih = resolve("sih_aih_reduzida")
    assert sih.partition_by == ("ano", "uf", "mes")
    assert sih.monthly is True


def test_resolve_unknown_raises() -> None:
    import pytest as _pt

    from omnisus_db.sources.datasus_ftp.datasets import resolve

    with _pt.raises(ValueError):
        resolve("bogus")


def _custom_sim_yaml(tmp_path: Path) -> Path:
    from importlib.resources import files

    dest = tmp_path / "sim_custom.yaml"
    dest.write_text(
        (files("omnisus_db.data.dicionarios") / "sim_obitos.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return dest


@pytest.mark.asyncio
async def test_import_scope_accepts_an_adhoc_dataset_value(
    monkeypatch, tmp_path, dbc_fixture
) -> None:
    """I3: a Dataset built by the caller, with its own YAML, ingests through the
    same path as a registered one — no second untyped mode (spec §3.3)."""
    from omnisus_db.sources.datasus_ftp.datasets import Dataset

    fixture_bytes = dbc_fixture("sim_rr_2023_mini").read_bytes()
    ds = Dataset(
        name="sim_custom",
        prefix="DO",
        ftp_dir="/dissemin/publicos/SIM/CID9/DORES",
        cadence="yearly",
        partition_by=("ano", "uf"),
        coverage=((1979, 1), (1995, 12)),
        dictionary=_custom_sim_yaml(tmp_path),
    )
    seen: dict[str, object] = {}

    async def fake_fetch(*, dataset, scope, **_kw: object) -> bytes:
        seen["dataset"] = dataset
        return fixture_bytes

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)

    with Lake.local(f"ducklake:{tmp_path}/x.ducklake") as lake:
        result = await import_scope(dataset=ds, scope=ScopeKey(uf="RR", ano=2023), lake=lake)
        assert result.rows > 0
        assert "sim_custom" in lake.tables()
    assert seen["dataset"] is ds


@pytest.mark.asyncio
async def test_import_scope_adhoc_without_yaml_fails_fast(monkeypatch, tmp_path) -> None:
    """Uncurated is not schemaless: no YAML -> FileNotFoundError before any
    bytes are decoded, never a silent all-strings fallback (spec §3.3)."""
    from omnisus_db.sources.datasus_ftp.datasets import Dataset

    ds = Dataset(
        name="no_such_yaml",
        prefix="ZZ",
        ftp_dir="/x",
        cadence="yearly",
        partition_by=("ano", "uf"),
        coverage=((2000, 1), None),
    )

    async def fake_fetch(*, dataset, scope, **_kw: object) -> bytes:
        return b"never decoded"

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)

    with Lake.local(f"ducklake:{tmp_path}/x.ducklake") as lake, pytest.raises(FileNotFoundError):
        await import_scope(dataset=ds, scope=ScopeKey(uf="RR", ano=2023), lake=lake)


def test_run_scopes_fetches_from_the_listed_release(monkeypatch, tmp_path) -> None:
    from omnisus_db.sources.datasus_ftp import _runner

    seen: list[tuple[ScopeKey, str]] = []

    async def fake_fetch(*, dataset, scope, release="final", **_):
        seen.append((scope, release))
        raise FtpFileNotFound("stop here")  # skipped: the release choice is what we test

    monkeypatch.setattr(_runner, "release_map", lambda d: {ScopeKey(uf="AC", ano=2025): "prelim"})
    monkeypatch.setattr(_runner, "fetch_dbc_bytes", fake_fetch)
    with Lake.local(f"ducklake:{tmp_path}/l.ducklake") as lake:
        asyncio.run(
            _runner.run_scopes(
                "sim_obitos",
                scopes=[ScopeKey(uf="AC", ano=2024), ScopeKey(uf="AC", ano=2025)],
                lake=lake,
            )
        )
    assert seen == [
        (ScopeKey(uf="AC", ano=2024), "final"),
        (ScopeKey(uf="AC", ano=2025), "prelim"),
    ]


def test_release_map_lists_nothing_for_rows_without_prelim_dir(monkeypatch) -> None:
    from omnisus_db.sources.datasus_ftp import _runner

    monkeypatch.setattr(
        _runner,
        "available_releases",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not list")),
    )
    assert _runner.release_map(REGISTRY["sia_bpa_individualizado"]) == {}

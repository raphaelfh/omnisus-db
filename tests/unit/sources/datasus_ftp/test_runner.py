"""Tests for the generic DATASUS-FTP runner."""

from __future__ import annotations

from pathlib import Path

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


def _custom_sim_yaml(tmp_path: Path) -> Path:
    from importlib.resources import files

    dest = tmp_path / "sim_custom.yaml"
    dest.write_text(
        (files("omnisus_db.data.dicionarios") / "sim_do.yaml").read_text(encoding="utf-8"),
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


@pytest.mark.asyncio
async def test_import_scope_accepts_an_alias(monkeypatch, tmp_path, dbc_fixture) -> None:
    fixture_bytes = dbc_fixture("sim_rr_2023_mini").read_bytes()

    async def fake_fetch(*, dataset, scope, **_kw: object) -> bytes:
        return fixture_bytes

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)

    with Lake.local(f"ducklake:{tmp_path}/x.ducklake") as lake:
        result = await import_scope(dataset="sim", scope=ScopeKey(uf="RR", ano=2023), lake=lake)
        assert result.rows > 0
        assert "sim_do" in lake.tables()

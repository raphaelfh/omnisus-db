"""omnisus-db inventory (spec §4.5)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from omnisus_db.cli.main import app

runner = CliRunner()

LINES = [
    "01-31-20  02:48PM                76107 DOAC1996.dbc",
    "12-23-25  03:48PM               874197 DOTO2024.dbc",
    "02-24-18  07:38AM       <DIR>          OLD",
]


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMNISUS_CACHE_DIR", str(tmp_path / "cache"))


def _patch(monkeypatch: pytest.MonkeyPatch, lines: list[str] | None = None) -> None:
    monkeypatch.setattr(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list",
        lambda _p, _t: LINES if lines is None else lines,
    )


def test_inventory_dataset_lists_available_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    result = runner.invoke(app, ["inventory", "sim_do"])
    assert result.exit_code == 0, result.output
    assert "AC" in result.output
    assert "1996" in result.output


def test_inventory_accepts_an_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    assert runner.invoke(app, ["inventory", "sim"]).exit_code == 0


def test_inventory_path_browses_any_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Open-world: a path we have no dictionary for still lists."""
    _patch(monkeypatch)
    result = runner.invoke(app, ["inventory", "--path", "/dissemin/publicos/SINAN"])
    assert result.exit_code == 0, result.output
    assert "DOAC1996.dbc" in result.output
    assert "OLD" in result.output


def test_inventory_requires_exactly_one_of_dataset_or_path() -> None:
    both = runner.invoke(app, ["inventory", "sim_do", "--path", "/x"])
    assert both.exit_code != 0
    neither = runner.invoke(app, ["inventory"])
    assert neither.exit_code != 0


def test_inventory_rejects_out_of_range_depth(monkeypatch: pytest.MonkeyPatch) -> None:
    """--depth is unguarded in both directions (spec I7: everything bounded).
    depth=0 would previously reach `crawl`'s ValueError as a raw traceback;
    an unbounded depth could LIST the whole DATASUS tree."""
    _patch(monkeypatch)
    result = runner.invoke(
        app, ["inventory", "--path", "/dissemin/publicos/SINAN", "--depth", "0"]
    )
    assert result.exit_code != 0
    assert "depth" in result.output.lower()
    assert "Traceback" not in result.output


def test_inventory_unknown_dataset_lists_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    result = runner.invoke(app, ["inventory", "bogus"])
    assert result.exit_code != 0
    assert "unknown dataset" in result.output


def test_inventory_reports_a_missing_path_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    import ftplib

    def boom(_p: str, _t: float) -> list[str]:
        raise ftplib.error_perm("550 The system cannot find the file specified.")

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp.inventory._blocking_list", boom)
    result = runner.invoke(app, ["inventory", "--path", "/nope"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_inventory_reports_ftp_unavailable_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_p: str, _t: float) -> list[str]:
        raise TimeoutError("dropped")

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp.inventory._blocking_list", boom)
    monkeypatch.setattr("omnisus_db.sources.datasus_ftp.inventory.time.sleep", lambda _s: None)
    result = runner.invoke(app, ["inventory", "--path", "/nope"])
    assert result.exit_code != 0
    assert "unreachable" in result.output.lower()
    assert "Traceback" not in result.output


def test_inventory_appears_in_top_level_help() -> None:
    assert "inventory" in runner.invoke(app, ["--help"]).output

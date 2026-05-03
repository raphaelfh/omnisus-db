"""Tests for the omnisus-db CLI entry point."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from omnisus_db.cli.main import app

runner = CliRunner()


def test_app_help_lists_top_level_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for verb in ("init", "import", "query", "lake", "doctor"):
        assert verb in result.stdout


def test_init_creates_lake_and_loads_auxiliares(tmp_path: Path) -> None:
    target = f"ducklake:{tmp_path}/omnisus.ducklake"
    result = runner.invoke(app, ["init", "--target", target])

    assert result.exit_code == 0, result.stdout

    from omnisus_db.lake import Lake

    lake = Lake.local(target)
    tables = set(lake.tables())
    assert {"aux_uf", "aux_municipios", "aux_cid10"} <= tables
    lake.close()


def test_init_default_target_is_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / "omnisus.ducklake").exists()

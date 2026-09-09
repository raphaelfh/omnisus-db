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


def test_import_sim_via_cli(monkeypatch, tmp_path, dbc_fixture) -> None:
    fixture_bytes = dbc_fixture("sim_rr_2023_mini").read_bytes()

    async def fake_fetch(*, dataset, scope, **_kw):
        return fixture_bytes

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp.fetch.fetch_dbc_bytes", fake_fetch)
    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)

    target = f"ducklake:{tmp_path}/cli.ducklake"
    result = runner.invoke(
        app,
        ["import", "sim", "--year", "2023", "--ufs", "RR", "--target", target],
    )
    assert result.exit_code == 0, result.stdout

    from omnisus_db.lake import Lake

    lake = Lake.local(target)
    n = lake.connect().execute("SELECT count(*) FROM lake.sim_do").fetchone()[0]
    assert n > 0
    lake.close()


def test_import_requires_year_or_years() -> None:
    """Missing --year/--years should fail with a clear error."""
    result = runner.invoke(app, ["import", "sim"])
    assert result.exit_code != 0
    assert "year" in result.output.lower()


def test_query_runs_sql(tmp_path: Path) -> None:
    target = f"ducklake:{tmp_path}/q.ducklake"
    runner.invoke(app, ["init", "--target", target])
    result = runner.invoke(
        app,
        ["query", "SELECT count(*) FROM lake.aux_uf", "--target", target],
    )
    assert result.exit_code == 0, result.stdout
    assert "27" in result.stdout


def test_lake_tables_lists_aux(tmp_path: Path) -> None:
    target = f"ducklake:{tmp_path}/t.ducklake"
    runner.invoke(app, ["init", "--target", target])
    result = runner.invoke(app, ["lake", "tables", "--target", target])
    assert result.exit_code == 0
    assert "aux_uf" in result.stdout


def test_doctor_reports_environment() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "DuckDB" in result.stdout
    assert "Polars" in result.stdout


def test_lake_describe_shows_columns(tmp_path: Path) -> None:
    target = f"ducklake:{tmp_path}/d.ducklake"
    runner.invoke(app, ["init", "--target", target])
    result = runner.invoke(
        app,
        ["lake", "describe", "aux_uf", "--target", target],
    )
    assert result.exit_code == 0
    assert "codigo_ibge" in result.stdout


def test_lake_optimize_runs(tmp_path: Path) -> None:
    target = f"ducklake:{tmp_path}/o.ducklake"
    runner.invoke(app, ["init", "--target", target])
    result = runner.invoke(
        app,
        ["lake", "optimize", "aux_uf", "--target", target],
    )
    # Optimize may print output; just confirm no crash
    assert result.exit_code == 0


def test_lake_update_auxiliares(tmp_path: Path) -> None:
    target = f"ducklake:{tmp_path}/u.ducklake"
    runner.invoke(app, ["init", "--target", target])
    result = runner.invoke(
        app,
        ["lake", "update-auxiliares", "--target", target],
    )
    assert result.exit_code == 0


def test_import_sia_bi_via_cli(monkeypatch, tmp_path: Path, dbc_fixture) -> None:
    """The CLI must reach every registry row, not a hand-maintained subset."""
    fixture_bytes = dbc_fixture("sia_bi_rr_2024_01_mini").read_bytes()

    async def fake_fetch(*, dataset, scope, **_kw: object) -> bytes:
        return fixture_bytes

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fake_fetch)

    target = f"ducklake:{tmp_path}/sia.ducklake"
    result = runner.invoke(
        app,
        ["import", "sia_bi", "--year", "2024", "--months", "1", "--ufs", "RR", "--target", target],
    )
    assert result.exit_code == 0, result.output

    from omnisus_db.lake import Lake

    with Lake.local(target) as lake:
        assert "sia_bi" in lake.tables()


def test_import_unknown_dataset_lists_the_choices() -> None:
    result = runner.invoke(app, ["import", "bogus", "--year", "2024"])
    assert result.exit_code != 0
    assert "unknown dataset" in result.output
    assert "sia_bi" in result.output


def test_import_help_lists_registry_names_and_aliases() -> None:
    result = runner.invoke(app, ["import", "--help"])
    assert result.exit_code == 0
    for name in ("sim", "sia_atd", "cnes-st", "ibge-pop"):
        assert name in result.output


def test_dataset_choices_cover_registry_aliases_and_non_ftp() -> None:
    import omnisus_db.cli.main as cli_main
    from omnisus_db.cli.main import dataset_choices
    from omnisus_db.sources.datasus_ftp.datasets import ALIASES, REGISTRY

    choices = set(dataset_choices())
    assert choices == set(REGISTRY) | set(ALIASES) | set(cli_main._NON_FTP)
    assert "ibge-pop" in choices


def test_import_dispatch_fails_loudly_on_non_ftp_entry_without_importer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ``_NON_FTP`` entry with no matching importer must raise, never
    silently mis-route to another dataset's importer."""
    import omnisus_db.cli.main as cli_main

    monkeypatch.setitem(cli_main._NON_FTP, "bogus-nonftp", "bogus")

    result = runner.invoke(app, ["import", "bogus-nonftp", "--year", "2024"])
    assert result.exit_code != 0
    assert "imported" not in result.output


def test_cli_default_target_is_the_lake_default() -> None:
    from omnisus_db.cli.main import DEFAULT_TARGET as CLI_DEFAULT_TARGET
    from omnisus_db.lake import DEFAULT_TARGET

    assert CLI_DEFAULT_TARGET is DEFAULT_TARGET


# --- import: planning and exit status (spec §5.1) --------------------------


def _serve_fixture_except(monkeypatch, fixture_bytes: bytes, missing: set[str]) -> None:
    """Patch the synchronous FTP seam, never ftplib itself."""
    import ftplib

    def _blocking(_remote_dir: str, filename: str, _timeout: float) -> bytes:
        if filename in missing:
            raise ftplib.error_perm("550 The system cannot find the file specified.")
        return fixture_bytes

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp.fetch._blocking_fetch", _blocking)


def test_a_skipped_scope_exits_zero(monkeypatch, tmp_path: Path, dbc_fixture) -> None:
    """Asking for a range DATASUS only partly published is normal, not an error.
    An orchestrator must be able to tell 'nothing to do' from 'something broke'."""
    _serve_fixture_except(
        monkeypatch, dbc_fixture("sim_rr_2023_mini").read_bytes(), {"DORR2022.dbc"}
    )
    result = runner.invoke(
        app,
        [
            "import",
            "sim",
            "--years",
            "2022-2023",
            "--ufs",
            "RR",
            "--target",
            f"ducklake:{tmp_path}/s.ducklake",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "1 skipped" in result.output


def test_a_failed_scope_exits_one(monkeypatch, tmp_path: Path) -> None:
    """A 530 exhausting its retries is a real failure and must be visible to
    the caller's exit status, not buried in a summary line."""
    import ftplib

    def _throttled(*_a: object) -> bytes:
        raise ftplib.error_perm("530 maximum number of allowed clients")

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp.fetch._blocking_fetch", _throttled)
    result = runner.invoke(
        app,
        [
            "import",
            "sim",
            "--year",
            "2023",
            "--ufs",
            "RR",
            "--target",
            f"ducklake:{tmp_path}/f.ducklake",
        ],
    )
    assert result.exit_code == 1, result.output
    assert "1 failed" in result.output


def test_plan_inventory_imports_only_what_the_server_lists(
    monkeypatch, tmp_path: Path, dbc_fixture
) -> None:
    """The goal: build the lake from what is actually published. The server
    lists 2023 only, so 2022 is never even attempted."""
    monkeypatch.setenv("OMNISUS_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list",
        lambda _p, _t: ["01-31-20  02:48PM                76107 DORR2023.dbc"],
    )
    fetched: list[str] = []

    def _blocking(_remote_dir: str, filename: str, _timeout: float) -> bytes:
        fetched.append(filename)
        return dbc_fixture("sim_rr_2023_mini").read_bytes()

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp.fetch._blocking_fetch", _blocking)

    result = runner.invoke(
        app,
        [
            "import",
            "sim",
            "--years",
            "2022-2023",
            "--ufs",
            "RR",
            "--plan",
            "inventory",
            "--target",
            f"ducklake:{tmp_path}/p.ducklake",
        ],
    )
    assert result.exit_code == 0, result.output
    assert fetched == ["DORR2023.dbc"], "2022 was not listed, so it must not be fetched"


def test_plan_inventory_bypasses_a_stale_listing_cache(
    monkeypatch, tmp_path: Path, dbc_fixture
) -> None:
    """--plan implies refresh=True. A 23-hour-old cache would silently omit a
    month published this morning, and the run is about to use the network anyway."""
    monkeypatch.setenv("OMNISUS_CACHE_DIR", str(tmp_path / "cache"))
    listings = 0

    def _list(_p: str, _t: float) -> list[str]:
        nonlocal listings
        listings += 1
        return ["01-31-20  02:48PM                76107 DORR2023.dbc"]

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp.inventory._blocking_list", _list)
    monkeypatch.setattr(
        "omnisus_db.sources.datasus_ftp.fetch._blocking_fetch",
        lambda *_a: dbc_fixture("sim_rr_2023_mini").read_bytes(),
    )
    argv = [
        "import",
        "sim",
        "--year",
        "2023",
        "--ufs",
        "RR",
        "--plan",
        "inventory",
        "--target",
        f"ducklake:{tmp_path}/r.ducklake",
    ]

    assert runner.invoke(app, argv).exit_code == 0
    assert runner.invoke(app, argv).exit_code == 0
    assert listings == 2, "the second run must re-list, not trust the 24h cache"


def test_an_unknown_plan_is_rejected() -> None:
    result = runner.invoke(app, ["import", "sim", "--year", "2023", "--plan", "bogus"])
    assert result.exit_code != 0
    assert "inventory" in result.output and "product" in result.output

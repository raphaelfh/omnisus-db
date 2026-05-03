"""Tests for the Lake class."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from omnisus_db.lake import Lake


def test_lake_local_creates_catalog_and_storage(tmp_path: Path) -> None:
    target = f"ducklake:{tmp_path}/omnisus.ducklake"
    lake = Lake.local(target)

    catalog_file = tmp_path / "omnisus-catalog.sqlite"
    assert catalog_file.exists()
    assert (tmp_path / "omnisus.ducklake").is_dir()

    lake.close()


def test_lake_tables_returns_empty_initially(tmp_path: Path) -> None:
    lake = Lake.local(f"ducklake:{tmp_path}/x.ducklake")
    assert lake.tables() == []
    lake.close()


def test_lake_connect_returns_duckdb_connection(tmp_path: Path) -> None:
    lake = Lake.local(f"ducklake:{tmp_path}/x.ducklake")
    con = lake.connect()
    assert isinstance(con, duckdb.DuckDBPyConnection)
    lake.close()


def test_lake_query_runs_sql(tmp_path: Path) -> None:
    lake = Lake.local(f"ducklake:{tmp_path}/x.ducklake")
    con = lake.connect()
    rows = con.execute("SELECT 1 AS x").fetchall()
    assert rows == [(1,)]
    lake.close()


def test_lake_cloud_requires_postgres_extras(tmp_path: Path) -> None:
    """Smoke: cloud factory builds the right target string format.

    We don't actually connect to PG here; just check that the URI
    assembly path is exercised. The connection attempt to an invalid
    PG host should fail.
    """
    with pytest.raises(duckdb.Error):
        Lake.cloud(
            catalog="postgresql://invalid:invalid@127.0.0.1:1/none",
            storage=str(tmp_path),
        )


def test_lake_context_manager(tmp_path: Path) -> None:
    target = f"ducklake:{tmp_path}/cm.ducklake"
    with Lake.local(target) as lake:
        assert lake.tables() == []

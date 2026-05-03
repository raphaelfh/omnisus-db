"""Tests for lake.connection."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnisus_db.lake.connection import make_connection


def test_make_connection_returns_duckdb_with_ducklake_loaded(tmp_path: Path) -> None:
    catalog = f"sqlite:{tmp_path / 'cat.sqlite'}"
    storage = str(tmp_path / "data")

    con = make_connection(catalog_uri=catalog, storage_root=storage, alias="lake")

    extensions = con.execute(
        "SELECT extension_name FROM duckdb_extensions() WHERE loaded"
    ).fetchall()
    assert any(name == "ducklake" for (name,) in extensions)

    # DuckLake attaches as a catalog (database) named after the alias;
    # its default schema is "main".
    catalogs = con.execute(
        "SELECT DISTINCT catalog_name FROM information_schema.schemata"
    ).fetchall()
    assert any(name == "lake" for (name,) in catalogs)


def test_make_connection_creates_storage_dir_if_missing(tmp_path: Path) -> None:
    storage = tmp_path / "lake-data"
    assert not storage.exists()

    make_connection(
        catalog_uri=f"sqlite:{tmp_path / 'cat.sqlite'}",
        storage_root=str(storage),
        alias="lake",
    )

    assert storage.is_dir()


def test_make_connection_rejects_unsupported_catalog_scheme(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported catalog scheme"):
        make_connection(
            catalog_uri="mongodb://nope",
            storage_root=str(tmp_path),
            alias="lake",
        )

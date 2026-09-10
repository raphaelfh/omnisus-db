"""Tests for lake.connection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from omnisus_db.lake.connection import make_connection


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "sqlite", "duckdb"])
def test_catalog_backend_selector(scheme, tmp_path, monkeypatch):
    con = Mock()
    monkeypatch.setattr("omnisus_db.lake.connection.duckdb.connect", lambda _: con)
    uri = (
        f"{scheme}://user:p'ass@localhost/test"
        if scheme in ("postgres", "postgresql")
        else f"{scheme}:{tmp_path}/cat"
    )
    make_connection(catalog_uri=uri, storage_root=str(tmp_path), alias='a"b')
    backend = "postgres:" if scheme in ("postgres", "postgresql") else ""
    escaped_uri = uri.replace("'", "''")
    con.execute.assert_any_call(
        f'ATTACH \'ducklake:{backend}{escaped_uri}\' AS "a""b" '
        f"(DATA_PATH '{str(tmp_path).replace(chr(39), chr(39) * 2)}')"
    )


@pytest.mark.parametrize("scheme", ["postgres", "postgresql"])
def test_remote_attach_failure_hides_credentials_and_closes(scheme, tmp_path, monkeypatch):
    import traceback

    import duckdb

    con = Mock()
    secret = "synthetic-secret"
    con.execute.side_effect = [None, duckdb.Error(f"connection failed: {secret}")]
    monkeypatch.setattr("omnisus_db.lake.connection.duckdb.connect", lambda _: con)
    with pytest.raises(duckdb.ConnectionException) as caught:
        make_connection(
            catalog_uri=f"{scheme}://user:{secret}@localhost/test",
            storage_root=str(tmp_path),
        )
    assert secret not in "".join(traceback.format_exception(caught.value))
    assert caught.value.__suppress_context__
    con.close.assert_called_once()


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


def test_lake_files_are_zstd_not_3x_larger_than_staging(tmp_path: Path) -> None:
    """DuckLake rewrites every ingested Parquet with its own writer settings
    and does not inherit the staging file's compression. Probed on DuckLake
    415a9ebd: 801,067 B without the option vs 241,497 B with it, for a
    241,491 B zstd reference (spec §5.2 item 5). The connection must set
    parquet_compression=zstd so lake files match a zstd reference written by
    the same engine."""
    import polars as pl

    from omnisus_db.lake import Lake

    with Lake.local(f"ducklake:{tmp_path}/z.ducklake") as lake:
        con = lake.connect()
        ref = tmp_path / "ref.parquet"
        con.execute(
            "COPY (SELECT 2022 AS ano, 'BA' AS uf, i AS v FROM range(200000) t(i)) "
            f"TO '{ref}' (FORMAT PARQUET, COMPRESSION zstd)"
        )
        lake.ingest("t", pl.scan_parquet(ref))
        (lake_bytes,) = con.execute(
            "SELECT sum(file_size_bytes) FROM __ducklake_metadata_lake.ducklake_data_file"
        ).fetchone()

    assert lake_bytes <= 1.2 * ref.stat().st_size, (
        f"lake wrote {lake_bytes:,} B for a {ref.stat().st_size:,} B zstd reference"
    )

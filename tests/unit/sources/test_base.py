"""Tests for sources base protocols."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pytest

from omnisus_db.sources._base import Dataset, ImportResult, ScopeKey


def test_scope_key_is_hashable_and_immutable() -> None:
    s1 = ScopeKey(uf="SP", ano=2024, mes=None)
    s2 = ScopeKey(uf="SP", ano=2024, mes=None)
    assert s1 == s2
    assert hash(s1) == hash(s2)
    s = {s1, s2}  # works in sets
    assert len(s) == 1


def test_scope_key_str_excludes_none_fields() -> None:
    assert str(ScopeKey(uf="SP", ano=2024, mes=None)) == "SP_2024"
    assert str(ScopeKey(uf="MG", ano=2024, mes=1)) == "MG_2024_01"


def test_dataset_is_frozen() -> None:
    d = Dataset(
        family="datasus_ftp",
        name="sim_do",
        canonical_schema=pa.schema([("numerodo", pa.string())]),
        partition_by=("ano", "uf"),
        dictionary_path=Path("/tmp/sim_do.yaml"),
    )
    with pytest.raises((AttributeError, TypeError)):
        d.name = "other"  # type: ignore[misc]


def test_import_result_defaults() -> None:
    r = ImportResult(rows=100, bytes_written=1024, duration_seconds=1.5, snapshot_id=42)
    assert r.rows == 100
    assert r.snapshot_id == 42

from pathlib import Path

import polars as pl
import pytest

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.identity import validate_identity
from omnisus_db.transforms.dictionaries import Dicionario


def _dic(**identity) -> Dicionario:
    raw = {"name": "t", "schema": {"fields": []}}
    if identity:
        raw["x-identity"] = identity
    return Dicionario(
        name="t",
        title="t",
        encoding="latin-1",
        fields=[],
        primary_key=[],
        partitions=[],
        source_format="dbc",
        version="1",
        raw=raw,
    )


def _staging(tmp_path: Path, **columns) -> Path:
    p = tmp_path / "s.parquet"
    pl.DataFrame(columns).write_parquet(p)
    return p


SCOPE = ScopeKey(uf=None, ano=2025)


def test_no_block_means_no_check(tmp_path) -> None:
    validate_identity(_staging(tmp_path, nu_ano=["1999"]), _dic(), SCOPE)


def test_mode_of_year_must_equal_the_scope_year(tmp_path) -> None:
    ok = _staging(
        tmp_path, nu_ano=["2025", "2025", "2026"]
    )  # a few off-year records are normal (TB)
    validate_identity(ok, _dic(year_column="nu_ano"), SCOPE)
    bad = _staging(tmp_path, nu_ano=["2024", "2024", "2025"])
    with pytest.raises(ValueError, match="year"):
        validate_identity(bad, _dic(year_column="nu_ano"), SCOPE)


def test_missing_year_column_and_empty_file_are_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="nu_ano"):
        validate_identity(_staging(tmp_path, other=["x"]), _dic(year_column="nu_ano"), SCOPE)
    with pytest.raises(ValueError, match="empty"):
        validate_identity(
            _staging(tmp_path, nu_ano=pl.Series([], dtype=pl.String)),
            _dic(year_column="nu_ano"),
            SCOPE,
        )


def test_code_mode_must_match_when_the_column_exists(tmp_path) -> None:
    dic = _dic(year_column="nu_ano", code_column="id_agravo", code="A309")
    validate_identity(
        _staging(tmp_path, nu_ano=["2025"] * 3, id_agravo=["A309", "A309", "A30."]), dic, SCOPE
    )
    with pytest.raises(ValueError, match="A309"):
        validate_identity(
            _staging(tmp_path, nu_ano=["2025"] * 3, id_agravo=["", "", "A309"]), dic, SCOPE
        )  # AIDABR24 shape
    validate_identity(
        _staging(tmp_path, nu_ano=["2025"]), dic, SCOPE
    )  # pre-2007 layout: no code column


def test_values_are_trimmed_and_compared_as_text(tmp_path) -> None:
    validate_identity(
        _staging(tmp_path, nu_ano=[" 2025 "], id_agravo=[" A309"]),
        _dic(year_column="nu_ano", code_column="id_agravo", code="A309"),
        SCOPE,
    )

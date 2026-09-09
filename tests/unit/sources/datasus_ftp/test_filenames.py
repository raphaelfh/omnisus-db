"""Tests for DATASUS FTP filename / ScopeKey conversion."""

from __future__ import annotations

import pytest

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.filenames import (
    parse_filename,
    scope_to_filename,
)


def test_parse_filename_sim_do() -> None:
    scope, dataset = parse_filename("DOSP2024.dbc")
    assert dataset == "sim_do"
    assert scope == ScopeKey(uf="SP", ano=2024)


def test_parse_filename_sih_rd_monthly() -> None:
    scope, dataset = parse_filename("RDSP2401.dbc")
    assert dataset == "sih_rd"
    assert scope == ScopeKey(uf="SP", ano=2024, mes=1)


def test_scope_to_filename_sim() -> None:
    name = scope_to_filename("sim_do", ScopeKey(uf="SP", ano=2024))
    assert name == "DOSP2024.dbc"


def test_scope_to_filename_sih_monthly() -> None:
    name = scope_to_filename("sih_rd", ScopeKey(uf="SP", ano=2024, mes=1))
    assert name == "RDSP2401.dbc"


def test_parse_filename_unknown_returns_error() -> None:
    with pytest.raises(ValueError):
        parse_filename("UNKNOWN.dbc")


def test_scope_to_filename_monthly_requires_mes() -> None:
    with pytest.raises(ValueError):
        scope_to_filename("sih_rd", ScopeKey(uf="SP", ano=2024, mes=None))


def test_decode_returns_scope_and_dataset_for_known_names() -> None:
    from omnisus_db.sources.datasus_ftp.filenames import decode

    assert decode("DOSP2024.dbc") == (ScopeKey(uf="SP", ano=2024), "sim_do")
    assert decode("ATDRR2401.dbc") == (ScopeKey(uf="RR", ano=2024, mes=1), "sia_atd")


def test_decode_returns_none_for_unmodelled_prefixes() -> None:
    """SIASUS/200801_/Dados also holds PA*, SAD* and others we do not model —
    available() must skip them, not raise (spec §4.1)."""
    from omnisus_db.sources.datasus_ftp.filenames import decode

    assert decode("PARR2401.dbc") is None
    assert decode("SADRR2401.dbc") is None


def test_decode_returns_none_for_non_dbc_and_junk() -> None:
    from omnisus_db.sources.datasus_ftp.filenames import decode

    for name in ("readme.txt", "base_aih1.duck", "", "DO.dbc", "199407_200712"):
        assert decode(name) is None, name


def test_decode_agrees_with_parse_filename_where_both_succeed() -> None:
    from omnisus_db.sources.datasus_ftp.filenames import decode, parse_filename

    assert decode("RDSP2401.dbc") == parse_filename("RDSP2401.dbc")

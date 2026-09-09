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

"""Tests for DATASUS FTP filename / ScopeKey conversion."""

from __future__ import annotations

import pytest

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import REGISTRY
from omnisus_db.sources.datasus_ftp.filenames import (
    decode_for,
    scope_to_filename,
)


def test_decode_for_sim_obitos() -> None:
    scope = decode_for(REGISTRY["sim_obitos"], "DOSP2024.dbc")
    assert scope == ScopeKey(uf="SP", ano=2024)


def test_decode_for_sih_aih_reduzida_monthly() -> None:
    scope = decode_for(REGISTRY["sih_aih_reduzida"], "RDSP2401.dbc")
    assert scope == ScopeKey(uf="SP", ano=2024, mes=1)


def test_scope_to_filename_sim() -> None:
    name = scope_to_filename("sim_obitos", ScopeKey(uf="SP", ano=2024))
    assert name == "DOSP2024.dbc"


def test_scope_to_filename_sih_monthly() -> None:
    name = scope_to_filename("sih_aih_reduzida", ScopeKey(uf="SP", ano=2024, mes=1))
    assert name == "RDSP2401.dbc"


def test_scope_to_filename_monthly_requires_mes() -> None:
    with pytest.raises(ValueError):
        scope_to_filename("sih_aih_reduzida", ScopeKey(uf="SP", ano=2024, mes=None))


def test_decode_for_returns_scope_for_known_names() -> None:
    assert decode_for(REGISTRY["sim_obitos"], "DOSP2024.dbc") == ScopeKey(uf="SP", ano=2024)
    assert decode_for(REGISTRY["sia_apac_tratamento_dialitico"], "ATDRR2401.dbc") == ScopeKey(
        uf="RR", ano=2024, mes=1
    )


def test_decode_for_returns_none_for_unmodelled_prefixes() -> None:
    """SIASUS/200801_/Dados also holds PA*, SAD* and others we do not model —
    available() must skip them, not raise (spec §4.1)."""
    assert decode_for(REGISTRY["sia_apac_medicamentos"], "PARR2401.dbc") is None
    assert decode_for(REGISTRY["sia_apac_medicamentos"], "SADRR2401.dbc") is None


def test_decode_for_returns_none_for_non_dbc_and_junk() -> None:
    d = REGISTRY["sim_obitos"]
    for name in ("readme.txt", "base_aih1.duck", "", "DO.dbc", "199407_200712"):
        assert decode_for(d, name) is None, name


def test_decode_for_agrees_with_scope_to_filename_round_trip() -> None:
    d = REGISTRY["sih_aih_reduzida"]
    scope = ScopeKey(uf="SP", ano=2024, mes=1)
    assert decode_for(d, scope_to_filename(d, scope)) == scope

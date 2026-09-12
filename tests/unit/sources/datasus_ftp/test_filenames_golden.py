"""Tier 1 (spec §6): the (dataset, scope) -> filename codec is exactly right
for every registry row, plus a round-trip property over the whole space.

Centralizing facts centralizes blast radius: if a row's prefix were wrong,
every derived surface would be consistently wrong. This table is the
independent statement of what the filenames must be.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from omnisus_db import ALL_UFS
from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import REGISTRY
from omnisus_db.sources.datasus_ftp.filenames import parse_filename, scope_to_filename

# fmt: off
GOLDEN: list[tuple[str, ScopeKey, str]] = [
    ("sinan_chagas", ScopeKey(uf=None, ano=2023), "CHAGBR23.dbc"),
    ("sim_obitos",    ScopeKey(uf="SP", ano=2024),         "DOSP2024.dbc"),
    ("sim_obitos",    ScopeKey(uf="RR", ano=1996),         "DORR1996.dbc"),
    ("sinasc_nascidos_vivos", ScopeKey(uf="MG", ano=2022),         "DNMG2022.dbc"),
    ("sih_aih_reduzida",    ScopeKey(uf="SP", ano=2024, mes=1),  "RDSP2401.dbc"),
    ("sih_aih_reduzida",    ScopeKey(uf="AC", ano=2008, mes=12), "RDAC0812.dbc"),
    ("sia_bpa_individualizado",    ScopeKey(uf="RR", ano=2024, mes=1),  "BIRR2401.dbc"),
    ("sia_apac_medicamentos",    ScopeKey(uf="RR", ano=2024, mes=1),  "AMRR2401.dbc"),
    ("sia_apac_quimioterapia",    ScopeKey(uf="RR", ano=2024, mes=1),  "AQRR2401.dbc"),
    ("sia_apac_tratamento_dialitico",   ScopeKey(uf="RR", ano=2024, mes=1),  "ATDRR2401.dbc"),  # 3-letter: ATD+RR, never AT+DR
    ("sia_apac_laudos_diversos",    ScopeKey(uf="AC", ano=2024, mes=1),  "ADAC2401.dbc"),   # AD+AC, never ADA+C
    ("sia_apac_cirurgia_bariatrica",   ScopeKey(uf="SP", ano=2024, mes=1),  "ABOSP2401.dbc"),  # ABO+SP, never AB+OS
    ("sia_psicossocial",    ScopeKey(uf="RR", ano=2024, mes=1),  "PSRR2401.dbc"),
    ("cnes_estabelecimentos",   ScopeKey(uf="RR", ano=2024, mes=1),  "STRR2401.dbc"),
    # two-digit-year pivot: yy < 80 -> 20yy, else 19yy
    ("sih_aih_reduzida",    ScopeKey(uf="SP", ano=1999, mes=6),  "RDSP9906.dbc"),
    ("sih_aih_reduzida",    ScopeKey(uf="SP", ano=1980, mes=6),  "RDSP8006.dbc"),
    ("sih_aih_reduzida",    ScopeKey(uf="SP", ano=2079, mes=6),  "RDSP7906.dbc"),
]
# fmt: on

_IDS = [g[2] for g in GOLDEN]


@pytest.mark.parametrize(("dataset", "scope", "filename"), GOLDEN, ids=_IDS)
def test_scope_to_filename_golden(dataset: str, scope: ScopeKey, filename: str) -> None:
    assert scope_to_filename(dataset, scope) == filename


@pytest.mark.parametrize(("dataset", "scope", "filename"), GOLDEN, ids=_IDS)
def test_parse_filename_golden(dataset: str, scope: ScopeKey, filename: str) -> None:
    assert parse_filename(filename) == (scope, dataset)


def test_every_registry_row_has_a_golden_case() -> None:
    assert {g[0] for g in GOLDEN} == set(REGISTRY)


def test_monthly_dataset_rejects_scope_without_mes() -> None:
    with pytest.raises(ValueError, match="requires mes"):
        scope_to_filename("sih_aih_reduzida", ScopeKey(uf="SP", ano=2024))


def test_parse_rejects_unknown_prefix() -> None:
    with pytest.raises(ValueError, match="unknown dataset prefix"):
        parse_filename("ZZSP2024.dbc")


# --- round-trip property over the whole space ------------------------------
# ano in [1980, 2079] is the range the two-digit-year pivot can round-trip.

_YEARLY = sorted(n for n, d in REGISTRY.items() if not d.monthly and d.geography == "state")
_MONTHLY = sorted(n for n, d in REGISTRY.items() if d.monthly)


@settings(max_examples=300, deadline=None)
@given(
    dataset=st.sampled_from(_YEARLY),
    uf=st.sampled_from(ALL_UFS),
    ano=st.integers(1980, 2079),
)
def test_roundtrip_yearly(dataset: str, uf: str, ano: int) -> None:
    scope = ScopeKey(uf=uf, ano=ano)
    assert parse_filename(scope_to_filename(dataset, scope)) == (scope, dataset)


@settings(max_examples=300, deadline=None)
@given(
    dataset=st.sampled_from(_MONTHLY),
    uf=st.sampled_from(ALL_UFS),
    ano=st.integers(1980, 2079),
    mes=st.integers(1, 12),
)
def test_roundtrip_monthly(dataset: str, uf: str, ano: int, mes: int) -> None:
    scope = ScopeKey(uf=uf, ano=ano, mes=mes)
    assert parse_filename(scope_to_filename(dataset, scope)) == (scope, dataset)

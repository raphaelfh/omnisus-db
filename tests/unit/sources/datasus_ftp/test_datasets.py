"""Tests for the dataset registry — the kernel (spec §3)."""

from __future__ import annotations

from typing import Any

import pytest

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import ALIASES, REGISTRY, Dataset, resolve

ELEVEN = {
    "sim_do",
    "sinasc_nv",
    "sih_rd",
    "sia_bi",
    "sia_am",
    "sia_aq",
    "sia_atd",
    "sia_ad",
    "sia_abo",
    "sia_ps",
    "cnes_st",
}


def _adhoc(**over: Any) -> Dataset:
    base: dict[str, Any] = {
        "name": "custom",
        "prefix": "DO",
        "ftp_dir": "/dissemin/publicos/X",
        "cadence": "yearly",
        "partition_by": ("ano", "uf"),
        "coverage": ((2000, 1), None),
    }
    return Dataset(**{**base, **over})


def test_registry_has_exactly_the_eleven_ftp_datasets() -> None:
    assert set(REGISTRY) == ELEVEN


def test_registry_keys_equal_row_names() -> None:
    for key, d in REGISTRY.items():
        assert key == d.name


def test_monthly_is_derived_from_cadence_not_partition_by() -> None:
    # spec §3: cadence (upstream fact) and partition_by (our layout) are distinct
    assert _adhoc(cadence="monthly", partition_by=("ano",)).monthly is True
    assert _adhoc(cadence="yearly", partition_by=("ano", "uf", "mes")).monthly is False


def test_row_is_frozen() -> None:
    d = _adhoc()
    with pytest.raises((AttributeError, TypeError)):
        d.name = "other"  # type: ignore[misc]


def test_dictionary_defaults_to_none_meaning_packaged_yaml() -> None:
    assert REGISTRY["sim_do"].dictionary is None


def test_resolve_by_key_returns_the_registry_object() -> None:
    assert resolve("sim_do") is REGISTRY["sim_do"]


@pytest.mark.parametrize(
    ("alias", "key"),
    [("sim", "sim_do"), ("sinasc", "sinasc_nv"), ("sih", "sih_rd"), ("cnes-st", "cnes_st")],
)
def test_resolve_by_alias(alias: str, key: str) -> None:
    assert resolve(alias) is REGISTRY[key]
    assert ALIASES[alias] == key


def test_resolve_passes_a_value_through_untouched() -> None:
    d = _adhoc()
    assert resolve(d) is d


def test_resolve_unknown_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown dataset"):
        resolve("bogus")


def test_aliases_do_not_collide_with_registry_keys() -> None:
    assert not set(ALIASES) & set(REGISTRY)


def test_adhoc_dataset_flows_through_codec_and_ftp_path() -> None:
    """I3: a Dataset value not in REGISTRY works through the same functions."""
    from omnisus_db.sources.datasus_ftp.fetch import ftp_path_for
    from omnisus_db.sources.datasus_ftp.filenames import scope_to_filename

    d = _adhoc(name="sim_cid9", prefix="DO", ftp_dir="/dissemin/publicos/SIM/CID9/DORES")
    scope = ScopeKey(uf="SP", ano=1995)
    assert scope_to_filename(d, scope) == "DOSP1995.dbc"
    assert ftp_path_for(d, scope) == ("/dissemin/publicos/SIM/CID9/DORES", "DOSP1995.dbc")


def test_adhoc_monthly_dataset_builds_monthly_filename() -> None:
    from omnisus_db.sources.datasus_ftp.filenames import scope_to_filename

    d = _adhoc(name="sia_pa", prefix="PA", cadence="monthly", partition_by=("ano", "uf", "mes"))
    assert scope_to_filename(d, ScopeKey(uf="RR", ano=2024, mes=3)) == "PARR2403.dbc"


def test_dataset_is_keyword_only() -> None:
    """ADR 0002: ``Dataset`` is constructible only by keyword, never
    positionally — a positional call must raise ``TypeError``."""
    with pytest.raises(TypeError):
        Dataset(  # type: ignore[misc]
            "custom",
            "DO",
            "/dissemin/publicos/X",
            "yearly",
            ("ano", "uf"),
            ((2000, 1), None),
        )

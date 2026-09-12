"""Tests for the dataset registry — the kernel (spec §3)."""

from __future__ import annotations

from typing import Any

import pytest

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import REGISTRY, Dataset, resolve

ROWS = {
    "sim_obitos",
    "sinasc_nascidos_vivos",
    "sih_aih_reduzida",
    "sia_bpa_individualizado",
    "sia_apac_medicamentos",
    "sia_apac_quimioterapia",
    "sia_apac_tratamento_dialitico",
    "sia_apac_laudos_diversos",
    "sia_apac_cirurgia_bariatrica",
    "sia_psicossocial",
    "cnes_estabelecimentos",
    "sinan_chagas",
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


def test_registry_has_exactly_the_supported_ftp_datasets() -> None:
    assert set(REGISTRY) == ROWS


def test_names_are_full_readable_words() -> None:
    """Spec §3.7: <sistema>_<conteúdo>, never a two-letter file prefix or a release."""
    for name, d in REGISTRY.items():
        _system, _, content = name.partition("_")
        assert content, name
        assert content.lower() != d.prefix.lower(), name
        assert not name.endswith(("_prelim", "_final")), name


def test_module_has_no_alias_surface() -> None:
    import omnisus_db.sources.datasus_ftp.datasets as m

    assert not hasattr(m, "ALIASES")
    assert not hasattr(m, "get_config")
    assert "aliases" not in Dataset.__dataclass_fields__


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
    assert REGISTRY["sim_obitos"].dictionary is None


def test_resolve_by_key_returns_the_registry_object() -> None:
    assert resolve("sim_obitos") is REGISTRY["sim_obitos"]


def test_resolve_passes_a_value_through_untouched() -> None:
    d = _adhoc()
    assert resolve(d) is d


def test_resolve_unknown_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown dataset"):
        resolve("bogus")


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

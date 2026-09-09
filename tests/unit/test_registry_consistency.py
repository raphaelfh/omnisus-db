"""Tier 2 (spec §6): the registry is internally consistent and every row is
reachable. This is the test that makes the SIA gap (spec §1.1) impossible.

Tier 2 (c) — ``available()`` accepts exactly the registry — lives with the
inventory plan, because ``available()`` does not exist yet.
"""

from __future__ import annotations

from importlib.resources import files

import pytest

import omnisus_db as odb
import omnisus_db.cli.main as cli_main
from omnisus_db.cli.main import dataset_choices
from omnisus_db.sources.datasus_ftp.datasets import ALIASES, REGISTRY

NON_FTP_DATASETS = set(cli_main._NON_FTP.values())
"""Datasets with their own importer and YAML but no registry row (spec §3.4).
Derived from the CLI's own dispatch table — one fact source (I4)."""


def _packaged_yaml_stems() -> set[str]:
    root = files("omnisus_db.data.dicionarios")
    return {p.name.removesuffix(".yaml") for p in root.iterdir() if p.name.endswith(".yaml")}


def test_a_every_row_has_a_packaged_dictionary() -> None:
    missing = {name for name in REGISTRY if name not in _packaged_yaml_stems()}
    assert not missing, f"registry rows without dicionarios/<name>.yaml: {sorted(missing)}"


def test_b_cli_accepts_every_row_and_alias() -> None:
    assert set(dataset_choices()) == set(REGISTRY) | set(ALIASES) | set(cli_main._NON_FTP)


def test_b_python_api_accepts_every_row() -> None:
    for name in REGISTRY:
        scopes = odb.scopes_for(name, years=[2024], ufs=["RR"], months=[1])
        assert scopes, name


def test_d_prefixes_are_unique() -> None:
    prefixes = [d.prefix for d in REGISTRY.values()]
    assert len(prefixes) == len(set(prefixes)), sorted(prefixes)


def test_e_cadence_agrees_with_partition_layout() -> None:
    """Agreement between two distinct facts — never derivation (spec §3)."""
    for d in REGISTRY.values():
        assert d.monthly == ("mes" in d.partition_by), d.name


def test_f_every_non_aux_yaml_has_exactly_one_owner() -> None:
    owners = set(REGISTRY) | NON_FTP_DATASETS
    yamls = {s for s in _packaged_yaml_stems() if not s.startswith("aux_")}
    assert yamls == owners, (
        f"unowned yaml: {sorted(yamls - owners)}; owner without yaml: {sorted(owners - yamls)}"
    )


def test_keys_equal_names_and_aliases_point_at_keys() -> None:
    for key, d in REGISTRY.items():
        assert key == d.name
    for alias, key in ALIASES.items():
        assert key in REGISTRY, alias
        assert alias not in REGISTRY, alias


def test_coverage_is_well_formed() -> None:
    """``coverage`` is written but never checked elsewhere — validate the
    shape here so a bad ``(year, month)`` pair can't silently sit in the
    registry (spec I5: a row must not lie)."""
    for d in REGISTRY.values():
        first, last = d.coverage
        assert 1 <= first[1] <= 12, d.name
        assert first[0] >= 1979, d.name
        if last is not None:
            assert 1 <= last[1] <= 12, d.name
            assert last >= first, d.name


def test_d_inventory_advertises_exactly_what_available_accepts() -> None:
    """The CLI's advertised set and the function's accepted set are the same
    set. A name offered in help that `available` rejects is I5 in the UI."""
    from omnisus_db.cli.main import ftp_dataset_choices

    assert set(ftp_dataset_choices()) == {*REGISTRY, *ALIASES}


def _file(name: str, when: str = "01-31-20  02:48PM", size: int = 76107) -> str:
    return f"{when}         {size:>12} {name}"


def test_c_available_accepts_exactly_the_registry(monkeypatch, tmp_path) -> None:
    """Tier 2 (c), spec §6: available() accepts every registry key and alias,
    and rejects everything else. Offline — the stubbed listing includes one
    real line, so this doesn't also pass against an available() that always
    returns []."""
    from omnisus_db.sources._base import ScopeKey
    from omnisus_db.sources.datasus_ftp.datasets import ALIASES, REGISTRY
    from omnisus_db.sources.datasus_ftp.inventory import available

    monkeypatch.setenv("OMNISUS_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(
        "omnisus_db.sources.datasus_ftp.inventory._blocking_list",
        lambda _p, _t: [_file("DOAC1996.dbc")],
    )
    for name in (*REGISTRY, *ALIASES):
        available(name)  # accepted: must not raise, for every key and alias
    assert available("sim_do") == [ScopeKey(uf="AC", ano=1996)], (
        "the row whose prefix matches the stubbed line must decode it"
    )
    with pytest.raises(ValueError, match="unknown dataset"):
        available("definitely_not_a_dataset")

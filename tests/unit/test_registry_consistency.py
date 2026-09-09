"""Tier 2 (spec §6): the registry is internally consistent and every row is
reachable. This is the test that makes the SIA gap (spec §1.1) impossible.

Tier 2 (c) — ``available()`` accepts exactly the registry — lives with the
inventory plan, because ``available()`` does not exist yet.
"""

from __future__ import annotations

from importlib.resources import files

import omnisus_db as odb
from omnisus_db.cli.main import dataset_choices
from omnisus_db.sources.datasus_ftp.datasets import ALIASES, REGISTRY

NON_FTP_DATASETS = {"ibge_pop"}
"""Datasets with their own importer and YAML but no registry row (spec §3.4)."""


def _packaged_yaml_stems() -> set[str]:
    root = files("omnisus_db.data.dicionarios")
    return {p.name.removesuffix(".yaml") for p in root.iterdir() if p.name.endswith(".yaml")}


def test_a_every_row_has_a_packaged_dictionary() -> None:
    missing = {name for name in REGISTRY if name not in _packaged_yaml_stems()}
    assert not missing, f"registry rows without dicionarios/<name>.yaml: {sorted(missing)}"


def test_b_cli_accepts_every_row_and_alias() -> None:
    assert set(REGISTRY) | set(ALIASES) <= set(dataset_choices())


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

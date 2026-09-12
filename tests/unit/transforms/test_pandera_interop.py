"""Validate every Frictionless YAML loads cleanly + smoke pandera interop.

The bundled YAMLs are Frictionless ``tabular-data-resource`` descriptors with
the table schema nested under ``schema``. We pull that subdocument out and
hand it to :class:`frictionless.Schema.from_descriptor` so the test exercises
real Frictionless validation rather than just a YAML round-trip.
"""

from __future__ import annotations

from importlib.resources import files

import polars as pl
import pytest
import yaml
from frictionless import Schema as FrictionlessSchema


def _load_schema(dataset: str) -> FrictionlessSchema:
    yaml_path = files("omnisus_db.data.dicionarios") / f"{dataset}.yaml"
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    return FrictionlessSchema.from_descriptor(raw["schema"])


@pytest.mark.parametrize(
    "dataset",
    [
        "aux_uf",
        "aux_municipios",
        "aux_cid10",
        "sim_obitos",
        "sinasc_nascidos_vivos",
        "sih_aih_reduzida",
        "ibge_populacao",
        "cnes_estabelecimentos",
    ],
)
def test_frictionless_loads_for_all_dicionarios(dataset: str) -> None:
    schema = _load_schema(dataset)
    assert schema.fields, f"{dataset} has no fields"


def test_frictionless_field_types_for_aux_uf() -> None:
    schema = _load_schema("aux_uf")
    field_names = {f.name for f in schema.fields}
    assert {"codigo_ibge", "sigla", "nome", "regiao"} <= field_names


def test_pandera_can_consume_frictionless_aux_uf_sample() -> None:
    """Smoke: a Polars DF matching the aux_uf schema doesn't blow up.

    pandera real validation is out of scope for v0.1.0; this just confirms
    Frictionless field iteration + a sample DataFrame agree on column names.
    """
    fr_schema = _load_schema("aux_uf")

    sample = pl.DataFrame(
        {
            "codigo_ibge": ["35"],
            "sigla": ["SP"],
            "nome": ["São Paulo"],
            "regiao": ["Sudeste"],
        }
    )
    # Smoke: schema iterates fields without crash
    assert {f.name for f in fr_schema.fields} >= {
        "codigo_ibge",
        "sigla",
        "nome",
        "regiao",
    }
    # DataFrame has the expected columns
    assert set(sample.columns) >= {f.name for f in fr_schema.fields}

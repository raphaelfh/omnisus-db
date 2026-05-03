"""Tests for transforms.dictionaries — Frictionless YAML loader."""

from __future__ import annotations

import pyarrow as pa
import pytest

from omnisus_db.transforms.dictionaries import Dicionario, load_dicionario


def test_load_aux_uf_returns_dicionario() -> None:
    dic = load_dicionario("aux_uf")
    assert isinstance(dic, Dicionario)
    assert dic.name == "aux_uf"
    assert dic.encoding == "utf-8"


def test_dicionario_arrow_schema_includes_required_fields() -> None:
    dic = load_dicionario("aux_uf")
    schema = dic.arrow_schema
    assert isinstance(schema, pa.Schema)
    names = schema.names
    assert "codigo_ibge" in names
    assert "sigla" in names


def test_load_dicionario_unknown_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_dicionario("does_not_exist")


def test_loader_caches_parsed_yaml() -> None:
    a = load_dicionario("aux_uf")
    b = load_dicionario("aux_uf")
    assert a is b  # lru_cache

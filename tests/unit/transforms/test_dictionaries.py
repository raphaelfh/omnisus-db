"""Tests for transforms.dictionaries — Frictionless YAML loader."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pytest

from omnisus_db.transforms.dictionaries import Dicionario, load_dicionario

# ---------------------------------------------------------------------------
# Loading + caching + Arrow schema
# ---------------------------------------------------------------------------


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


def test_load_sim_do_has_expected_extensions() -> None:
    dic = load_dicionario("sim_do")
    assert dic.encoding == "cp1252"
    assert dic.partitions == ["ano", "uf"]
    assert dic.source_format == "dbc"
    # Type-tolerant decode: int input + string keys in YAML
    assert dic.decode("sexo", 1) == "Masculino"
    assert dic.decode("sexo", 99) == 99


def test_load_sim_do_arrow_schema_round_trip() -> None:
    dic = load_dicionario("sim_do")
    schema = dic.arrow_schema
    # Required fields present
    assert "numerodo" in schema.names
    assert "ano" in schema.names
    # Date types mapped
    assert schema.field("dtobito").type == pa.date32()
    # Integer mapped
    assert schema.field("sexo").type == pa.int64()


# ---------------------------------------------------------------------------
# field_def — case-insensitive lookup
# ---------------------------------------------------------------------------


def test_field_def_lookup_is_case_insensitive() -> None:
    dic = load_dicionario("sim_do")
    assert dic.field_def("sexo") is dic.field_def("SEXO")
    assert dic.field_def("SEXO")["name"] == "sexo"
    assert dic.field_def("nonexistent") is None


# ---------------------------------------------------------------------------
# decode — type tolerance
# ---------------------------------------------------------------------------


def test_decode_accepts_string_input_for_string_keys() -> None:
    dic = load_dicionario("sim_do")
    # YAML keys are strings; lake stores VARCHAR — string input must work.
    assert dic.decode("tipobito", "1") == "Fetal"
    assert dic.decode("tipobito", "2") == "Não fetal"


def test_decode_accepts_int_input_for_string_keys() -> None:
    dic = load_dicionario("sim_do")
    # Same data, but value happens to be an int — must still match.
    assert dic.decode("tipobito", 1) == "Fetal"
    assert dic.decode("tipobito", 2) == "Não fetal"


def test_decode_strips_whitespace() -> None:
    dic = load_dicionario("sim_do")
    # DBF/DBC files frequently pad codes with spaces — must still decode.
    assert dic.decode("sexo", " 1 ") == "Masculino"


def test_decode_unknown_value_passes_through() -> None:
    dic = load_dicionario("sim_do")
    assert dic.decode("sexo", "Z") == "Z"
    assert dic.decode("sexo", 42) == 42


def test_decode_unknown_field_passes_through() -> None:
    dic = load_dicionario("sim_do")
    assert dic.decode("not_a_field", "anything") == "anything"


def test_decode_handles_padded_string_keys() -> None:
    """Codes like ``ESCFALAGR1`` use 2-digit padded keys ('00', '01')."""
    dic = load_dicionario("sim_do")
    assert dic.decode("escfalagr1", "00") == "Sem escolaridade"
    # Int 0 must also map to '00' via string normalization — but the YAML has
    # both '00' and '01'..'12', so int 0 should NOT match '00' (different key).
    # We accept that one as-is (no decode happens).
    assert dic.decode("escfalagr1", "01") == "Fundamental I incompleto"


# ---------------------------------------------------------------------------
# decode_row — full-row decoding with transforms + decode
# ---------------------------------------------------------------------------


def test_decode_row_translates_x_decode_fields() -> None:
    dic = load_dicionario("sim_do")
    row = {"sexo": "1", "racacor": "2", "tipobito": "2"}
    result = dic.decode_row(row)
    assert result["sexo"] == "Masculino"
    assert result["racacor"] == "Preta"
    assert result["tipobito"] == "Não fetal"


def test_decode_row_reformats_dates_via_x_format() -> None:
    dic = load_dicionario("sim_do")
    row = {"dtobito": "01012024", "dtnasc": "03011927"}
    result = dic.decode_row(row)
    assert result["dtobito"] == "01/01/2024"
    assert result["dtnasc"] == "03/01/1927"


def test_decode_row_reformats_yyyymmdd_dates() -> None:
    dic = load_dicionario("sih_rd")
    row = {"dt_inter": "20240115", "nasc": "19850320"}
    result = dic.decode_row(row)
    assert result["dt_inter"] == "15/01/2024"
    assert result["nasc"] == "20/03/1985"


def test_decode_row_applies_time_hhmm_display_transform() -> None:
    dic = load_dicionario("sim_do")
    result = dic.decode_row({"horaobito": "1040"})
    assert result["horaobito"] == "10:40"


def test_decode_row_applies_idade_sim_display_transform() -> None:
    dic = load_dicionario("sim_do")
    # SIM idade encoding: 1st digit = unit, 2nd-3rd = value.
    assert dic.decode_row({"idade": "469"})["idade"] == "69 anos"
    assert dic.decode_row({"idade": "115"})["idade"] == "15 minutos"
    assert dic.decode_row({"idade": "310"})["idade"] == "10 dias"
    assert dic.decode_row({"idade": "501"})["idade"] == "101 anos"
    assert dic.decode_row({"idade": "999"})["idade"] == "Ignorada"


def test_decode_row_applies_idade_sih_cross_field_transform() -> None:
    dic = load_dicionario("sih_rd")
    # COD_IDADE=4 + IDADE=35 → 35 anos
    result = dic.decode_row({"cod_idade": "4", "idade": "35"})
    assert result["idade"] == "35 anos"
    # COD_IDADE=3 + IDADE=6 → 6 meses
    result = dic.decode_row({"cod_idade": "3", "idade": "6"})
    assert result["idade"] == "6 meses"
    # COD_IDADE=5 + IDADE=2 → 102 anos
    result = dic.decode_row({"cod_idade": "5", "idade": "2"})
    assert result["idade"] == "102 anos"


def test_decode_row_passes_unknown_keys_through_unchanged() -> None:
    dic = load_dicionario("sim_do")
    row = {"sexo": "1", "made_up_field": "raw_value"}
    result = dic.decode_row(row)
    assert result["sexo"] == "Masculino"
    assert result["made_up_field"] == "raw_value"


def test_decode_row_handles_empty_and_none_values() -> None:
    dic = load_dicionario("sim_do")
    # None and empty strings must pass through unchanged.
    row = {"sexo": None, "horaobito": "", "tipobito": "  "}
    result = dic.decode_row(row)
    assert result["sexo"] is None
    assert result["horaobito"] == ""
    assert result["tipobito"] == "  "


def test_decode_row_accepts_uppercase_keys() -> None:
    """Legacy callers may pass uppercase DBF column names — must still decode."""
    dic = load_dicionario("sim_do")
    result = dic.decode_row({"SEXO": "1", "DTOBITO": "01012024"})
    assert result["SEXO"] == "Masculino"
    assert result["DTOBITO"] == "01/01/2024"


def test_decode_row_returns_new_dict() -> None:
    dic = load_dicionario("sim_do")
    row = {"sexo": "1"}
    result = dic.decode_row(row)
    assert result is not row
    assert row["sexo"] == "1"  # original untouched


def test_decode_row_handles_empty_input() -> None:
    dic = load_dicionario("sim_do")
    assert dic.decode_row({}) == {}


# ---------------------------------------------------------------------------
# Labels — used by the explorer for human-readable column headers
# ---------------------------------------------------------------------------


def test_sim_fields_have_labels() -> None:
    dic = load_dicionario("sim_do")
    assert dic.field_def("sexo")["label"] == "Sexo"
    assert dic.field_def("dtobito")["label"] == "Data do óbito"
    assert dic.field_def("horaobito")["label"] == "Hora do óbito"
    assert dic.field_def("idade")["label"] == "Idade"


def test_sinasc_fields_have_labels() -> None:
    dic = load_dicionario("sinasc_nv")
    assert dic.field_def("sexo")["label"] == "Sexo"
    assert dic.field_def("dtnasc")["label"] == "Data de nascimento"


def test_sih_fields_have_labels() -> None:
    dic = load_dicionario("sih_rd")
    assert dic.field_def("dt_inter")["label"] == "Data de internação"
    assert dic.field_def("morte")["label"] == "Óbito"


# ---------------------------------------------------------------------------
# Path-based loading (spec §3.3 — uncurated datasets)
# ---------------------------------------------------------------------------


def _copy_packaged(name: str, dest: Path) -> Path:
    from importlib.resources import files

    src = (files("omnisus_db.data.dicionarios") / f"{name}.yaml").read_text(encoding="utf-8")
    dest.write_text(src, encoding="utf-8")
    return dest


def test_load_dicionario_accepts_a_path(tmp_path: Path) -> None:
    """An ad-hoc dataset supplies its own YAML (spec §3.3)."""
    custom = _copy_packaged("sim_do", tmp_path / "custom.yaml")
    dic = load_dicionario(custom)
    packaged = load_dicionario("sim_do")
    assert dic.name == packaged.name
    assert dic.encoding == packaged.encoding
    assert [f["name"] for f in dic.fields] == [f["name"] for f in packaged.fields]


def test_load_dicionario_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="dicionario not found"):
        load_dicionario(tmp_path / "nope.yaml")

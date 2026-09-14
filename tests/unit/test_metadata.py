from copy import deepcopy

import pytest

import omnisus_db as odb


def test_metadata_is_detached_and_reproducible():
    first = odb.describe_dataset("sim_obitos")
    expected = deepcopy(first)
    first["schema"]["fields"].clear()
    first["fields"].clear()
    assert odb.describe_dataset("sim_obitos") == expected
    assert expected["schema_version"] == "1.0.0"
    assert len(expected["metadata_hash"]) == 64


def test_public_display_preserves_input_and_unknown_values():
    row = {"idade": "2", "cod_idade": "5", "unknown": "01"}
    assert odb.display_row("sih_aih_reduzida", row)["idade"] == "102 anos"
    assert row == {"idade": "2", "cod_idade": "5", "unknown": "01"}
    assert odb.display_row("sih_aih_reduzida", row)["unknown"] == "01"


def test_metadata_separates_source_from_observation():
    description = odb.describe_dataset("sim_obitos")
    field = next(x for x in description["fields"] if x["field"]["name"] == "sexo")
    assert field["field"]["logical_type"] == "string"
    assert "observed_type" not in field["field"]
    assert field["field"]["codes"]
    assert all(isinstance(c["value"], str) for c in field["field"]["codes"])


def test_unknown_dataset_has_no_fabricated_description():
    with pytest.raises(FileNotFoundError):
        odb.describe_dataset("no_such_dataset")


def test_all_legacy_fields_have_explicit_review_status():
    description = odb.describe_dataset("sih_aih_reduzida")
    assert len(description["fields"]) == len(description["schema"]["fields"])
    for field in description["fields"]:
        assert field["claims"]
        assert field["applicability"]["status"] in {"unknown", "confirmed"}


@pytest.mark.parametrize("rule", ["age", "sex"])
def test_analytical_evidence_must_resolve(monkeypatch, rule):
    from omnisus_db.transforms.dictionaries import load_dicionario

    evidence = load_dicionario("sim_obitos").raw["x-analytics"][rule]["evidence"][0]
    monkeypatch.setitem(evidence, "source_id", "nonexistent-evidence")
    with pytest.raises(ValueError, match="Unresolved analytical source"):
        odb.describe_dataset("sim_obitos")


def test_review_hash_rejects_changed_value(monkeypatch):
    from omnisus_db.transforms.dictionaries import load_dicionario

    field = load_dicionario("sim_obitos").field_def("sexo")
    monkeypatch.setitem(field["x-decode"], "1", "Changed without review")
    with pytest.raises(ValueError, match="Changed reviewed value"):
        odb.describe_dataset("sim_obitos")

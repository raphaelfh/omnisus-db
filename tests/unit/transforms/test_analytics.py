from dataclasses import replace

import duckdb
import pytest

import omnisus_db as odb


def contexts(dataset):
    rules = odb.describe_dataset(dataset)["analytics"]
    return [
        odb.SourceContext(
            odb.ScopeKey(uf=x["uf"], ano=x["ano"], mes=x.get("mes")),
            x["release"],
            x["source_sha256"],
        )
        for x in rules["validated_sources"]
    ]


def test_projection_requires_confirmed_source_context():
    projection = odb.analytical_projection(
        "sim_obitos", observed_schema={"idade": "VARCHAR"}, scopes=[]
    )
    assert not projection.columns
    assert projection.unavailable


def test_projection_rejects_unknown_version_and_schema_collision():
    with pytest.raises(ValueError, match="version"):
        odb.analytical_projection(
            "sim_obitos", observed_schema={}, scopes=[], rule_version="future"
        )
    with pytest.raises(ValueError, match="collision"):
        odb.analytical_projection(
            "sim_obitos",
            observed_schema={"idade": "VARCHAR", "idade_status": "VARCHAR"},
            scopes=contexts("sim_obitos"),
        )


def test_native_sql_age_sex_dates_and_invalid_dates():
    schema = {"idade": "VARCHAR", "sexo": "VARCHAR", "dtobito": "VARCHAR"}
    projection = odb.analytical_projection(
        "sim_obitos", observed_schema=schema, scopes=contexts("sim_obitos")
    )
    expressions = ", ".join(f'{c.expression} AS "{c.name}"' for c in projection.columns)
    with duckdb.connect() as con:
        rows = con.sql(f"""SELECT {expressions} FROM (VALUES
          ('469','2','01042023'), ('000','9','02012023'), ('310','Z','31022024'),
          (NULL,NULL,NULL)) t(idade,sexo,dtobito)""").fetchall()
        columns = [c.name for c in projection.columns]
    records = [dict(zip(columns, row, strict=True)) for row in rows]
    assert records[0]["idade_anos_completos"] == 69
    assert records[0]["sexo_categoria"] == "female"
    assert records[1]["idade_status"] == "ignored"
    assert records[2]["dtobito_data"] is None
    assert records[2]["dtobito_data_status"] == "invalid"
    assert records[3]["dtobito_data_status"] == "missing"


def test_context_hash_and_scope_must_both_match():
    valid = contexts("sim_obitos")[0]
    for bad in [
        replace(valid, source_sha256="0" * 64),
        replace(valid, scope=odb.ScopeKey("XX", 2024)),
    ]:
        p = odb.analytical_projection(
            "sim_obitos", observed_schema={"idade": "VARCHAR"}, scopes=[bad]
        )
        assert not p.columns
    p = odb.analytical_projection(
        "sim_obitos", observed_schema={"idade": "VARCHAR"}, scopes=[valid, bad]
    )
    assert not p.columns


def test_publication_context_uses_publication_identity():
    row = {
        "dataset": "sim_obitos",
        "scope_json": '{"uf":"RR","ano":2023}',
        "source_uri": "ftp://ftp.datasus.gov.br/dissemin/publicos/SIM/CID10/DORES/DORR2023.dbc",
        "source_sha256": "a" * 64,
    }
    context = odb.SourceContext.from_publication(row)
    assert context.scope == odb.ScopeKey("RR", 2023)
    assert context.release == "final"
    with pytest.raises(ValueError):
        odb.SourceContext.from_publication({})

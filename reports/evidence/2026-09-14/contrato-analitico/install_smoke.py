"""Reproduce the installed-wheel contract check outside a source checkout."""

import importlib.metadata
import json
import platform
import socket


def offline(*args, **kwargs):
    raise AssertionError("Public contract attempted a network connection")


def main():
    socket.create_connection = offline
    import duckdb

    import omnisus_db as odb

    assert odb.__version__ == importlib.metadata.version("omnisus-db") == "0.3.0"
    assert "site-packages" in odb.__file__
    meta = odb.describe_dataset("sim_obitos")
    assert meta["schema_version"] == "1.0.0"
    changed = odb.describe_dataset("sim_obitos")
    changed.clear()
    assert odb.describe_dataset("sim_obitos") == meta
    source = meta["analytics"]["validated_sources"][0]
    context = odb.SourceContext(
        odb.ScopeKey(source["uf"], source["ano"]), source["release"], source["source_sha256"]
    )
    projection = odb.analytical_projection(
        "sim_obitos",
        observed_schema={"idade": "VARCHAR", "sexo": "VARCHAR", "dtobito": "VARCHAR"},
        scopes=[context],
    )
    expressions = ", ".join(f'{c.expression} AS "{c.name}"' for c in projection.columns)
    with duckdb.connect() as con:
        row = con.sql(
            f"SELECT {expressions} FROM (VALUES ('469','2','02012023')) t(idade,sexo,dtobito)"
        ).fetchone()
    record = dict(zip((c.name for c in projection.columns), row, strict=True))
    assert record["idade_anos_completos"] == 69
    assert record["sexo_categoria"] == "female"
    assert str(record["dtobito_data"]) == "2023-01-02"
    assert odb.display_row("sim_obitos", {"idade": "469", "unknown": "01"}) == {
        "idade": "69 anos",
        "unknown": "01",
    }
    print(
        json.dumps(
            {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "version": odb.__version__,
                "module": odb.__file__,
                "metadata_hash": meta["metadata_hash"],
                "public_contract_offline": True,
                "native_sql": True,
            }
        )
    )


if __name__ == "__main__":
    main()

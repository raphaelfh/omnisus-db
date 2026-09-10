"""Read current behavior using synthetic inputs and disposable local catalogs.

Run from repository root: .venv/bin/python reports/evidence/2026-09-10/d2-d6-audit/probe.py
This is an audit probe, not a specification of the desired behavior.
"""

import asyncio
import json
import platform
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import duckdb
import polars as pl
from typer.testing import CliRunner

from omnisus_db.cli.main import app
from omnisus_db.lake import Lake
from omnisus_db.lake.catalog import parse_target
from omnisus_db.sources.ibge.importers.pop import import_pop_year
from omnisus_db.sources.ibge.parse import pop_json_to_lazyframe


def capture(fn):
    try:
        return {"returned": fn()}
    except Exception as exc:
        return {"error": type(exc).__name__, "message": str(exc)}


def main():
    observations = {"python": platform.python_version(), "duckdb": duckdb.__version__}
    observations["catalog_query"] = parse_target(
        "ducklake:postgresql://example.invalid/db?sslmode=require&storage=s3://bucket/lake"
    ).catalog_uri
    payload = [
        {"resultados": [{"series": [{"localidade": {"id": "3550308"}, "serie": {"2021": "100"}}]}]}
    ]
    observations["ibge_wrong_year"] = (
        pop_json_to_lazyframe(payload, year=2022).collect().to_dicts()
    )

    with tempfile.TemporaryDirectory(prefix="omnisus-d2-d6-audit-") as tmp:
        target = f"ducklake:{tmp}/audit.ducklake"
        with Lake.local(target) as lake:
            observations["ducklake"] = (
                lake.connect()
                .execute(
                    "SELECT extension_version FROM duckdb_extensions() WHERE extension_name='ducklake'"
                )
                .fetchone()[0]
            )
            with patch(
                "omnisus_db.sources.ibge.importers.pop.fetch_pop_by_year",
                new=AsyncMock(return_value=[]),
            ):
                result = asyncio.run(import_pop_year(year=2022, lake=lake))
            observations["ibge_empty_import"] = {
                "rows": result.rows,
                "table_created": "ibge_pop" in lake.tables(),
            }
            for table, values in [("int_first", [1, 1.5]), ("float_first", [1.5, 1])]:
                for value in values:
                    lake.ingest(table, pl.DataFrame({"v": [value]}).lazy())
                observations[table] = (
                    lake.connect()
                    .execute(f"SELECT v, typeof(v) FROM lake.{table} ORDER BY v")
                    .fetchall()
                )
            con = lake.connect()
            con.execute(
                "CREATE TABLE lake.cnes_st (cnes VARCHAR, tp_unid VARCHAR, codufmun VARCHAR, ano INTEGER, mes INTEGER)"
            )
            con.execute(
                "INSERT INTO lake.cnes_st VALUES ('1234567','05','355030',2024,1), ('1234567',NULL,'330455',2024,2)"
            )
            lake.ensure_aux_cnes_view()
            observations["cnes_latest_with_null"] = con.execute(
                "SELECT tp_unid,codufmun,yyyymm_max FROM lake.aux_cnes"
            ).fetchall()
            lf = pl.DataFrame({"ano": [2024], "uf": ["SP"], "v": [7]}).lazy()
            lake.ingest("repeated", lf)
            lake.ingest("repeated", lf)
            observations["append_twice_rows"] = con.execute(
                "SELECT count(*) FROM lake.repeated"
            ).fetchone()[0]
            observations["optimize"] = capture(lambda: lake.optimize("repeated"))
            observations["vacuum"] = capture(lake.vacuum)
            observations["maintenance_functions"] = con.execute(
                "SELECT function_name, parameters, parameter_types FROM duckdb_functions() "
                "WHERE function_name IN ('ducklake_merge_adjacent_files','ducklake_cleanup_old_files','ducklake_expire_snapshots')"
            ).fetchall()
        result = CliRunner().invoke(app, ["lake", "optimize", "repeated", "--target", target])
        observations["cli_optimize"] = {"exit_code": result.exit_code, "output": result.output}

        def quoted_path():
            with Lake.local(f"ducklake:{tmp}/D'Avila/lake.ducklake"):
                return "opened"

        observations["quoted_local_path"] = capture(quoted_path)

    output = Path(__file__).with_name("observations.json")
    output.write_text(json.dumps(observations, indent=2, ensure_ascii=False) + "\n")
    print(output)
    print(json.dumps(observations, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

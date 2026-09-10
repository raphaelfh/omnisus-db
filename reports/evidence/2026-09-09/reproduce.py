"""Read-only source audit; every lake is created under TemporaryDirectory."""

import contextlib
import json
import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import polars as pl
import structlog
from typer.testing import CliRunner

import omnisus_db as odb
from omnisus_db.cli.main import app
from omnisus_db.lake import Lake
from omnisus_db.lake.catalog import parse_target
from omnisus_db.sources.cnes.importers.master import _ensure_master_table, _upsert_master
from omnisus_db.sources.datasus_ftp.parse import dbc_bytes_to_lazyframe
from omnisus_db.sources.ibge.parse import pop_json_to_lazyframe
from omnisus_db.transforms.dictionaries import load_dicionario

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL))
REPO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
RAW = (REPO / "tests/fixtures/dbc/sim_rr_2023_mini.dbc").read_bytes()
observations = {}


def record(name, fn):
    try:
        with tempfile.TemporaryDirectory(prefix="omnisus-audit-") as tmp:
            observations[name] = fn(Path(tmp))
    except Exception as exc:
        observations[name] = {"unexpected_error": type(exc).__name__, "detail": str(exc)}


def failed_scope(tmp):
    with patch("omnisus_db.sources.datasus_ftp.fetch._blocking_fetch", return_value=b"bad DBC"):
        report = odb.import_dataset(
            "sim_do",
            scopes=[odb.ScopeKey("RR", 2023)],
            target=f"ducklake:{tmp}/lake",
            batch_size=1,
        )
        cli = CliRunner().invoke(
            app, ["import", "sim_do", "-y", "2023", "--ufs", "RR", "-t", f"ducklake:{tmp}/cli"]
        )
    return {
        "requested": 1,
        "outcomes": len(report.outcomes),
        "failed": len(report.failed),
        "cli_exit_code": cli.exit_code,
        "cli_output": cli.stdout.strip(),
    }


def repeat_and_snapshot(tmp):
    target = f"ducklake:{tmp}/lake"
    scope = odb.ScopeKey("RR", 2023)
    with patch("omnisus_db.sources.datasus_ftp.fetch._blocking_fetch", return_value=RAW):
        r1 = odb.import_dataset("sim_do", scopes=[scope], target=target)
        r2 = odb.import_dataset("sim_do", scopes=[scope], target=target)
    with Lake.local(target) as lake:
        rows = lake.connect().execute("SELECT count(*) FROM lake.sim_do").fetchone()[0]
        snaps = lake.snapshots()
    return {
        "first_rows": r1.rows,
        "second_rows": r2.rows,
        "stored_rows": rows,
        "reported_snapshot_first": r1.ok[0].result.snapshot_id,
        "reported_snapshot_second": r2.ok[0].result.snapshot_id,
        "committed_snapshots": snaps,
    }


def rollback_schema(tmp):
    with Lake.local(f"ducklake:{tmp}/lake") as lake:
        lake.ingest("t", pl.DataFrame({"a": [1]}).lazy())
        try:
            with lake.transaction():
                lake.ingest("t", pl.DataFrame({"a": [2], "newcol": ["x"]}).lazy())
                raise RuntimeError("injected abort after successful schema extension")
        except RuntimeError:
            pass
        cached = sorted(lake._columns["t"])
        actual = [r[0] for r in lake.connect().execute("DESCRIBE lake.t").fetchall()]
        try:
            lake.ingest("t", pl.DataFrame({"a": [3], "newcol": ["y"]}).lazy())
            retry = "success"
        except Exception as exc:
            retry = f"{type(exc).__name__}: {exc}"
        return {"cached_columns": cached, "actual_columns": actual, "retry": retry}


def narrowing(tmp):
    with Lake.local(f"ducklake:{tmp}/lake") as lake:
        lake.ingest("t", pl.DataFrame({"a": [1]}, schema={"a": pl.UInt8}).lazy())
        try:
            lake.ingest("t", pl.DataFrame({"a": [300]}, schema={"a": pl.UInt16}).lazy())
            result = "success"
        except Exception as exc:
            result = f"{type(exc).__name__}: {exc}"
        lake.ingest("amounts", pl.DataFrame({"amount": [1]}).lazy())
        lake.ingest("amounts", pl.DataFrame({"amount": [1.75]}).lazy())
        stored = lake.connect().execute("SELECT amount FROM lake.amounts").fetchall()
        return {"result": result, "fractional_input": 1.75, "stored_after_int_then_float": stored}


def upsert_failure(tmp):
    with Lake.local(f"ducklake:{tmp}/lake") as lake:
        _ensure_master_table(lake)
        rows = [
            {
                "cnes": "1234567",
                "nome": "Synthetic test",
                "nome_fantasia": None,
                "razao_social": None,
            }
        ]
        _upsert_master(lake, rows)
        con = lake.connect()

        class FailInsert:
            def execute(self, *args, **kw):
                return con.execute(*args, **kw)

            def executemany(self, *args, **kw):
                raise RuntimeError("injected insert failure")

        with (
            patch.object(lake, "connect", return_value=FailInsert()),
            contextlib.suppress(RuntimeError),
        ):
            _upsert_master(lake, rows)
        return {
            "rows_before": 1,
            "rows_after_insert_failure": con.execute(
                "SELECT count(*) FROM lake.cnes_master"
            ).fetchone()[0],
        }


def latest_null(tmp):
    with Lake.local(f"ducklake:{tmp}/lake") as lake:
        lake.connect().execute(
            "CREATE TABLE lake.cnes_st(cnes VARCHAR, tp_unid VARCHAR, codufmun VARCHAR, ano INT, mes INT)"
        )
        lake.connect().execute(
            "INSERT INTO lake.cnes_st VALUES ('1234567','05','355030',2024,1), ('1234567',NULL,'999999',2024,2)"
        )
        lake.ensure_aux_cnes_view()
        return {
            "latest_source_type": None,
            "view": lake.connect().execute("SELECT * FROM lake.aux_cnes").fetchall(),
        }


def maintenance(tmp):
    results = {}
    with Lake.local(f"ducklake:{tmp}/lake") as lake:
        lake.ingest("t", pl.DataFrame({"a": [1]}).lazy())
        results["versions"] = (
            lake.connect()
            .execute(
                "SELECT extension_name, extension_version FROM duckdb_extensions() WHERE loaded"
            )
            .fetchall()
        )
        for name, fn in [
            ("optimize", lambda: lake.optimize("t")),
            ("vacuum", lambda: lake.vacuum()),
        ]:
            try:
                fn()
                results[name] = "success"
            except Exception as exc:
                results[name] = f"{type(exc).__name__}: {exc}"
    result = CliRunner().invoke(app, ["lake", "optimize", "t", "-t", f"ducklake:{tmp}/lake"])
    results["optimize_cli_exit"] = result.exit_code
    results["optimize_cli_output"] = result.stdout.strip()
    return results


def path_and_uri(tmp):
    result = {}
    for name, target in [
        ("readme", str(tmp / "lake")),
        ("apostrophe", f"ducklake:{tmp}/D'Avila/lake"),
    ]:
        try:
            with Lake.local(target):
                pass
            result[name] = "success"
        except Exception as exc:
            result[name] = f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
    c = parse_target(
        "ducklake:postgresql://user:dummy@host/db?sslmode=require&connect_timeout=10&storage=s3://example/lake"
    )
    result["parsed_catalog"] = c.catalog_uri
    result["parsed_storage"] = c.storage_root
    try:
        with patch("omnisus_db.lake.operations.make_connection"):
            Lake.cloud(
                catalog="postgresql://user:dummy@host/db?sslmode=require",
                storage="s3://example/lake",
            )
        result["cloud_with_options"] = "success"
    except Exception as exc:
        result["cloud_with_options"] = f"{type(exc).__name__}: {exc}"
    return result


def dictionary(tmp):
    df = dbc_bytes_to_lazyframe(RAW, dataset="sim_do", ano=2023, uf="RR").collect()
    dic = load_dicionario("sim_do")
    declared = {f["name"]: f["type"] for f in dic.fields}
    return {
        name: {"declared": declared.get(name), "actual": str(df.schema[name])}
        for name in ("dtobito", "idade", "sexo")
        if name in df.schema
    }


def ibge_contract(tmp):
    data = [
        {
            "resultados": [
                {
                    "series": [
                        {"localidade": {"id": "3550308"}, "serie": {"2023": "10", "2024": "-"}}
                    ]
                },
                {"series": [{"localidade": {"id": "3304557"}, "serie": {"2023": "20"}}]},
            ]
        }
    ]
    return {
        "requested_year": 2022,
        "input_series": 2,
        "returned_rows": pop_json_to_lazyframe(data, year=2022).collect().to_dicts(),
        "empty_payload_rows": pop_json_to_lazyframe([], year=2022).collect().height,
    }


for name, fn in [
    ("failed_scope", failed_scope),
    ("repeat_and_snapshot", repeat_and_snapshot),
    ("rollback_schema", rollback_schema),
    ("type_drift", narrowing),
    ("upsert_failure", upsert_failure),
    ("latest_null", latest_null),
    ("maintenance", maintenance),
    ("path_and_uri", path_and_uri),
    ("dictionary", dictionary),
    ("ibge_contract", ibge_contract),
]:
    record(name, fn)

print(json.dumps(observations, indent=2, ensure_ascii=False, default=str))

"""The bases/ notebook helpers: where a run lives, what it records, how rows reconcile."""

import json
from pathlib import Path

import duckdb
import pytest

import omnisus_db as odb
from omnisus_db._notebooks import (
    data_root,
    default_target,
    reconcile,
    record_import,
    record_provenance,
    run_without_buttons,
    save_plan,
    scope_filter,
)
from omnisus_db.lake.publication import _predicate, scope_fields

ROOT = Path(__file__).resolve().parents[3]
RR_2022 = odb.ScopeKey(uf="RR", ano=2022)


def test_data_root_follows_cwd(monkeypatch, tmp_path):
    monkeypatch.delenv("OMNISUS_NOTEBOOK_DATA", raising=False)
    monkeypatch.chdir(tmp_path)
    assert data_root() == tmp_path / "data/lake/pesquisa"
    assert default_target() == f"ducklake:{tmp_path / 'data/lake/pesquisa' / 'dados.ducklake'}"


def test_data_root_from_the_repository_root_matches_the_guide(monkeypatch):
    monkeypatch.delenv("OMNISUS_NOTEBOOK_DATA", raising=False)
    monkeypatch.chdir(ROOT)
    assert data_root() == ROOT / "data/lake/pesquisa"


def test_environment_overrides_the_data_root(monkeypatch, tmp_path):
    monkeypatch.setenv("OMNISUS_NOTEBOOK_DATA", str(tmp_path))
    assert data_root() == tmp_path


@pytest.mark.parametrize(
    ("cli_args", "expected"),
    [
        ({}, False),
        ({"executar": "true"}, True),
        ({"executar": "True"}, True),
        ({"executar": True}, True),
        ({"executar": "false"}, False),
    ],
)
def test_unattended_flag(cli_args, expected):
    assert run_without_buttons(cli_args) is expected


def test_fixing_a_plan_writes_only_the_plan(monkeypatch, tmp_path):
    monkeypatch.setenv("OMNISUS_NOTEBOOK_DATA", str(tmp_path))
    plan, folder = save_plan(
        "ducklake:x", dataset="sim_obitos", scopes=[{"uf": "RR", "ano": 2022, "mes": None}]
    )
    assert folder == tmp_path / "execucoes" / plan["run_id"]
    assert [p.name for p in folder.iterdir()] == ["plano.json"]
    assert json.loads((folder / "plano.json").read_text(encoding="utf-8")) == plan
    assert plan["dataset"] == "sim_obitos"
    assert plan["target"] == "ducklake:x"
    assert plan["omnisus_db"] == odb.__version__
    assert plan["created_at_utc"]


def test_two_plans_never_share_a_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("OMNISUS_NOTEBOOK_DATA", str(tmp_path))
    assert save_plan("ducklake:x")[1] != save_plan("ducklake:x")[1]


def test_import_record_keeps_every_outcome_and_unresolved_scope(tmp_path):
    already = odb.ScopeKey(uf="RR", ano=2021)
    report = odb.ImportReport(
        outcomes=(
            odb.ScopeOutcome(
                scope=RR_2022,
                status="ok",
                result=odb.ImportResult(rows=7, bytes_written=0, duration_seconds=0.1),
            ),
            odb.ScopeOutcome(
                scope=already,
                status="skipped",
                reason="same source and parser version already published",
            ),
        ),
        run_id="r1",
    )
    missing = odb.ScopeKey(uf="RR", ano=2020)

    rows = record_import(tmp_path, report, [(2, missing)])

    assert rows == [
        {"scope": str(RR_2022), "status": "ok", "rows": 7, "reason": None},
        {
            "scope": str(already),
            "status": "skipped",
            "rows": None,
            "reason": "same source and parser version already published",
        },
    ]
    saved = json.loads((tmp_path / "resultado.json").read_text(encoding="utf-8"))
    assert saved == {
        "rows_imported": 7,
        "outcomes": rows,
        "unresolved": [{"index": 2, "scope": str(missing)}],
    }


@pytest.mark.parametrize(
    "scope",
    [
        RR_2022,
        odb.ScopeKey(uf="RR", ano=2024, mes=1),
        odb.ScopeKey(uf=None, ano=2022),
    ],
)
def test_scope_filter_uses_the_lake_identity_predicate(scope):
    assert scope_filter(scope) == _predicate(scope_fields(scope))


class _Reader:
    alias = "lake"

    def __init__(self, publications):
        self._con = duckdb.connect()
        self._con.execute("ATTACH ':memory:' AS lake")
        self._con.execute(
            "CREATE TABLE lake.sim_obitos AS SELECT * FROM "
            "(VALUES ('RR', 2022), ('RR', 2022), ('RR', 2021)) AS t(uf, ano)"
        )
        self._publications = publications

    def connect(self):
        return self._con

    def publications(self):
        return self._publications


def test_reconciliation_counts_only_active_publications_of_the_dataset():
    active = {"dataset": "sim_obitos", "active": True, "scope": RR_2022, "rows": 2}
    publications = [
        active,
        {"dataset": "sim_obitos", "active": False, "scope": RR_2022, "rows": 5},
        {"dataset": "sinasc_nascidos_vivos", "active": True, "scope": RR_2022, "rows": 9},
    ]
    missing = odb.ScopeKey(uf="RR", ano=2020)

    comparison, actives = reconcile(_Reader(publications), "sim_obitos", [RR_2022, missing])

    assert comparison == [
        {
            "scope": str(RR_2022),
            "lake_rows": 2,
            "published_rows": 2,
            "matches": True,
        },
        {
            "scope": str(missing),
            "lake_rows": 0,
            "published_rows": 0,
            "matches": True,
        },
    ]
    assert actives == [active]


def test_provenance_names_what_a_citation_needs(tmp_path):
    plan = {"run_id": "r1", "dataset": "sim_obitos"}
    publications = [{"publication_id": "p1", "scope": RR_2022, "source_sha256": "ab"}]
    queries = {"obitos_por_mes": {"sql": "SELECT 1 WHERE uf = ?", "parameters": ["RR"]}}

    record = record_provenance(
        tmp_path,
        plan=plan,
        publications=publications,
        snapshot_id=3,
        queries=queries,
    )

    saved = json.loads((tmp_path / "proveniencia.json").read_text(encoding="utf-8"))
    assert saved == json.loads(json.dumps(record, default=str))
    assert saved["plan"] == plan
    assert saved["publications"][0]["scope"] == str(RR_2022)
    assert saved["snapshot_id"] == 3
    assert "sim_obitos" in saved["citation"]
    assert "ab" in saved["citation"]
    assert "r1" in saved["citation"]
    assert saved["queries"] == {
        "obitos_por_mes": {"sql": "SELECT 1 WHERE uf = ?", "parameters": ["RR"]}
    }
    assert saved["omnisus_db"] == odb.__version__
    assert saved["generated_at_utc"]


def test_provenance_rejects_a_query_without_its_parameters(tmp_path):
    with pytest.raises((TypeError, ValueError, KeyError)):
        record_provenance(
            tmp_path,
            plan={"run_id": "r1", "dataset": "sim_obitos"},
            publications=[],
            snapshot_id=3,
            queries={"obitos_por_mes": "SELECT 1"},
        )


def test_helpers_are_not_on_the_public_import_surface():
    assert "notebooks" not in odb.__all__
    assert "_notebooks" not in odb.__all__

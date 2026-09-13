"""The bases/ notebook helpers: where a run lives, what it records, how rows reconcile."""

import importlib.util
import json
from pathlib import Path

import duckdb
import pytest

import omnisus_db as odb

_PATH = Path(__file__).resolve().parents[3] / "notebooks/bases/_comum.py"
_spec = importlib.util.spec_from_file_location("_comum_under_test", _PATH)
comum = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(comum)

RR_2022 = odb.ScopeKey(uf="RR", ano=2022)


def test_data_root_defaults_to_the_shared_research_lake(monkeypatch):
    monkeypatch.delenv("OMNISUS_NOTEBOOK_DATA", raising=False)
    raiz = _PATH.parents[2] / "data/lake/pesquisa"
    assert comum.raiz_dados() == raiz
    assert comum.target_padrao() == f"ducklake:{raiz / 'dados.ducklake'}"


def test_environment_overrides_the_data_root(monkeypatch, tmp_path):
    monkeypatch.setenv("OMNISUS_NOTEBOOK_DATA", str(tmp_path))
    assert comum.raiz_dados() == tmp_path


@pytest.mark.parametrize(
    ("cli_args", "esperado"),
    [
        ({}, False),
        ({"executar": "true"}, True),
        ({"executar": "True"}, True),
        ({"executar": True}, True),
        ({"executar": "false"}, False),
    ],
)
def test_executar_flag(cli_args, esperado):
    assert comum.executar_sem_botoes(cli_args) is esperado


def test_fixing_a_plan_writes_only_the_plan(monkeypatch, tmp_path):
    monkeypatch.setenv("OMNISUS_NOTEBOOK_DATA", str(tmp_path))
    plano, pasta = comum.fixar_plano(
        "ducklake:x", dataset="sim_obitos", escopos=[{"uf": "RR", "ano": 2022, "mes": None}]
    )
    assert pasta == tmp_path / "execucoes" / plano["run_id"]
    assert [p.name for p in pasta.iterdir()] == ["plano.json"]
    assert json.loads((pasta / "plano.json").read_text(encoding="utf-8")) == plano
    assert plano["dataset"] == "sim_obitos"
    assert plano["target"] == "ducklake:x"
    assert plano["omnisus_db"] == odb.__version__


def test_two_plans_never_share_a_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("OMNISUS_NOTEBOOK_DATA", str(tmp_path))
    assert comum.fixar_plano("ducklake:x")[1] != comum.fixar_plano("ducklake:x")[1]


def test_import_record_keeps_every_outcome_and_unresolved_scope(tmp_path):
    ja_publicado = odb.ScopeKey(uf="RR", ano=2021)
    relatorio = odb.ImportReport(
        outcomes=(
            odb.ScopeOutcome(
                scope=RR_2022,
                status="ok",
                result=odb.ImportResult(rows=7, bytes_written=0, duration_seconds=0.1),
            ),
            odb.ScopeOutcome(
                scope=ja_publicado,
                status="skipped",
                reason="same source and parser version already published",
            ),
        ),
        run_id="r1",
    )
    nao_resolvido = odb.ScopeKey(uf="RR", ano=2020)

    linhas = comum.registrar_importacao(tmp_path, relatorio, [(2, nao_resolvido)])

    assert linhas == [
        {"escopo": str(RR_2022), "status": "ok", "linhas": 7, "motivo": None},
        {
            "escopo": str(ja_publicado),
            "status": "skipped",
            "linhas": None,
            "motivo": "same source and parser version already published",
        },
    ]
    salvo = json.loads((tmp_path / "resultado.json").read_text(encoding="utf-8"))
    assert salvo == {
        "linhas_importadas": 7,
        "desfechos": linhas,
        "nao_resolvidos": [{"indice": 2, "escopo": str(nao_resolvido)}],
    }


@pytest.mark.parametrize(
    ("escopo", "esperado"),
    [
        (RR_2022, ('"ano" = ? AND "uf" = ?', [2022, "RR"])),
        (
            odb.ScopeKey(uf="RR", ano=2024, mes=1),
            ('"ano" = ? AND "uf" = ? AND "mes" = ?', [2024, "RR", 1]),
        ),
        (odb.ScopeKey(uf=None, ano=2022), ('"_source_ano" = ?', [2022])),
    ],
)
def test_scope_filter_uses_the_columns_the_library_writes(escopo, esperado):
    assert comum.filtro_escopo(escopo) == esperado


class _Leitor:
    alias = "lake"

    def __init__(self, publicacoes):
        self._con = duckdb.connect()
        self._con.execute("ATTACH ':memory:' AS lake")
        self._con.execute(
            "CREATE TABLE lake.sim_obitos AS SELECT * FROM "
            "(VALUES ('RR', 2022), ('RR', 2022), ('RR', 2021)) AS t(uf, ano)"
        )
        self._publicacoes = publicacoes

    def connect(self):
        return self._con

    def publications(self):
        return self._publicacoes


def test_reconciliation_counts_only_active_publications_of_the_dataset():
    ativa = {"dataset": "sim_obitos", "active": True, "scope": RR_2022, "rows": 2}
    publicacoes = [
        ativa,
        {"dataset": "sim_obitos", "active": False, "scope": RR_2022, "rows": 5},
        {"dataset": "sinasc_nascidos_vivos", "active": True, "scope": RR_2022, "rows": 9},
    ]
    ausente = odb.ScopeKey(uf="RR", ano=2020)

    conferencia, ativas = comum.conferir(_Leitor(publicacoes), "sim_obitos", [RR_2022, ausente])

    assert conferencia == [
        {"escopo": str(RR_2022), "linhas_no_lake": 2, "linhas_publicadas": 2, "confere": True},
        {"escopo": str(ausente), "linhas_no_lake": 0, "linhas_publicadas": 0, "confere": True},
    ]
    assert ativas == [ativa]


def test_provenance_names_what_a_citation_needs(tmp_path):
    plano = {"run_id": "r1", "dataset": "sim_obitos"}
    publicacoes = [{"publication_id": "p1", "scope": RR_2022, "source_sha256": "ab"}]
    consultas = {"obitos_por_mes": {"sql": "SELECT 1 WHERE uf = ?", "parametros": ["RR"]}}

    registro = comum.registrar_proveniencia(
        tmp_path,
        plano=plano,
        publicacoes=publicacoes,
        snapshot_id=3,
        consultas=consultas,
    )

    salvo = json.loads((tmp_path / "proveniencia.json").read_text(encoding="utf-8"))
    assert salvo == json.loads(json.dumps(registro, default=str))
    assert salvo["plano"] == plano
    assert salvo["publicacoes"][0]["scope"] == str(RR_2022)
    assert salvo["snapshot_id"] == 3
    assert salvo["consultas"] == {
        "obitos_por_mes": {"sql": "SELECT 1 WHERE uf = ?", "parametros": ["RR"]}
    }
    assert salvo["consultas"]["obitos_por_mes"]["parametros"] == ["RR"]
    assert salvo["omnisus_db"] == odb.__version__
    assert salvo["gerado_em_utc"]


def test_provenance_rejects_a_query_without_its_parameters(tmp_path):
    with pytest.raises((TypeError, ValueError, KeyError)):
        comum.registrar_proveniencia(
            tmp_path,
            plano={"run_id": "r1", "dataset": "sim_obitos"},
            publicacoes=[],
            snapshot_id=3,
            consultas={"obitos_por_mes": "SELECT 1"},
        )

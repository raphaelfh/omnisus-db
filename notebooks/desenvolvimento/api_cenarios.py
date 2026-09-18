# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.16,<0.25",
#     "omnisus-db",
#     "polars>=1.44.2,<2.0",
# ]
#
# [tool.uv.sources]
# omnisus-db = { git = "https://github.com/raphaelfh/omnisus-db.git", rev = "5bdb25a45bea2056316dcd03c6a2c62a23a759cb" }
# ///

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="omnisus-db · API na prática")


@app.cell
def _():
    import asyncio
    from dataclasses import asdict
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from uuid import uuid4

    import marimo as mo
    import polars as pl

    import omnisus_db as odb

    return Path, TemporaryDirectory, asdict, asyncio, mo, odb, pl, uuid4


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # omnisus-db · API na prática

    [![Open in molab](https://molab.marimo.io/molab-shield.svg)](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/desenvolvimento/api_cenarios.py)

    Um roteiro executável: **planejar → gravar → consultar → verificar → importar**.
    Os exemplos locais usam dados fictícios e um lake temporário que é removido
    ao terminar a célula. As tabelas exibidas ficam materializadas em memória.
    DuckDB pode baixar a extensão DuckLake na primeira execução.

    As chamadas ao DATASUS ficam na seção 6: ponha `EXECUTAR_LIVE = True`. Cada
    importação cria um destino próprio em `data/lake/marimo-runs/`. Use **um
    escritor por lake**. Execute pela raiz do checkout atual; a tag histórica
    `v0.1.0` tem outra API.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Como a documentação foi avaliada

    Em 10/09/2026, os **19 arquivos Markdown** foram comparados com assinaturas,
    implementações, docstrings e testes da entrega transacional D1. Uma revisão
    independente cobriu API, arquitetura, página inicial e ADRs; a consolidação
    também cobriu guias, fontes, catálogo gerado e planos históricos.

    - **Contrato:** nomes, argumentos, tipos de retorno, exceções, URI e transações.
    - **Exemplos:** 16 comandos analisados pelo parser CLI, 14 blocos Python com
      sintaxe verificada e três exemplos executados em DuckLake temporário.
    - **Consistência:** links locais, catálogo gerado, MkDocs strict e comparação
      de AST para confirmar que as mudanças nas docstrings não alteraram a lógica.
    - **Regressão após o merge:** 429 testes passaram, 47 foram excluídos por
      `not e2e and not perf`, cobertura de 91,97%, Python 3.13.12.

    São evidências daquela revisão, **não uma nova execução da suíte neste notebook**.
    Não houve validação de disponibilidade ao vivo dos serviços, desempenho ou CI
    remota. Cobertura mede código exercitado; não garante correção dos dados.
    Relatório: `reports/2026-09-10-avaliacao-documentacao.md`.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 1 · Planejar escopos sem consultar o servidor
    """)
    return


@app.cell
def _(asdict, odb):
    annual_scopes = [
        asdict(s) for s in odb.scopes_for("sim_obitos", years=[2022, 2023], ufs=["RR", "SP"])
    ]
    monthly_scopes = [
        asdict(s)
        for s in odb.scopes_for("sih_aih_reduzida", years=[2024], ufs=["RR"], months=[1, 2])
    ]
    {"sim_anual": annual_scopes, "sih_mensal": monthly_scopes}
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2 · Ingerir, evoluir o esquema e consultar

    `Lake.ingest` recebe um `LazyFrame` e acrescenta registros. Chamado sozinho,
    ele confirma sua própria transação. Dentro de `Lake.transaction()`, várias
    gravações compartilham o commit. Neste exemplo, o segundo lote adiciona uma
    coluna: os registros antigos ficam com `NULL` nessa coluna.

    A célula também executa os cenários 3 e 4 sequencialmente, na mesma conexão,
    para que a reatividade não provoque escritas concorrentes.
    """)
    return


@app.cell
def _(Path, TemporaryDirectory, asdict, odb, pl):
    # Todos os recursos são fechados antes de sair; nenhuma relação lazy escapa.
    with TemporaryDirectory(prefix="omnisus-marimo-") as _directory:
        _target = f"ducklake:{Path(_directory) / 'demo.ducklake'}"
        with odb.Lake.local(_target) as _lake:
            with _lake.transaction() as _receipt:
                _first = _lake.ingest(
                    "demo_atendimentos",
                    pl.DataFrame(
                        {
                            "id": [1, 2, 3],
                            "uf": ["RR", "RR", "SP"],
                            "ano": [2023, 2023, 2023],
                            "valor": [100.0, 250.0, 400.0],
                        }
                    ).lazy(),
                    partition_by=("ano", "uf"),
                )
                snapshot_before_commit = _first.snapshot_id
                _audit = _lake.ingest(
                    "demo_lotes", pl.DataFrame({"lote": [1], "linhas": [3]}).lazy()
                )
                assert snapshot_before_commit is None
                assert _audit.snapshot_id is None
            assert _receipt.committed
            assert _first.snapshot_id == _audit.snapshot_id == _receipt.snapshot_id
            commit_summary = {
                "committed": _receipt.committed,
                "tabelas_no_commit": ["demo_atendimentos", "demo_lotes"],
                **asdict(_first),
            }

            _lake.ingest(
                "demo_atendimentos",
                pl.DataFrame(
                    {
                        "id": [4],
                        "uf": ["SP"],
                        "ano": [2024],
                        "valor": [500.0],
                        "origem": ["lote_novo"],
                    }
                ).lazy(),
            )
            demo_data = (
                _lake.connect().sql("SELECT * FROM lake.demo_atendimentos ORDER BY id").pl()
            )
            assert demo_data.height == 4
            assert demo_data["origem"].null_count() == 3

            # Erro proposital: prova que a linha 999 não fica publicada.
            _history_before = _lake.snapshots()
            try:
                with _lake.transaction() as _rollback_receipt:
                    _lake.ingest(
                        "demo_atendimentos",
                        pl.DataFrame(
                            {
                                "id": [999],
                                "uf": ["RR"],
                                "ano": [2024],
                                "valor": [-1.0],
                            }
                        ).lazy(),
                    )
                    raise ValueError("Demonstração: valor inválido, desfazer o lote")
            except ValueError as _error:
                rollback_message = str(_error)
            _count = (
                _lake.connect()
                .sql("SELECT count(*) FROM lake.demo_atendimentos WHERE id = 999")
                .fetchone()[0]
            )
            assert _count == 0
            assert not _rollback_receipt.committed
            assert _lake.snapshots() == _history_before
            rollback_summary = {"linhas_999": _count, "committed": _rollback_receipt.committed}

            # Repetir uma ingestão acrescenta novamente o mesmo dado.
            _repeated = pl.DataFrame({"id": [1]})
            _lake.ingest("demo_repeticao", _repeated.lazy())
            _lake.ingest("demo_repeticao", _repeated.lazy())
            append_summary = (
                _lake.connect()
                .sql(
                    "SELECT count(*) AS linhas, count(DISTINCT id) AS ids_unicos "
                    "FROM lake.demo_repeticao"
                )
                .pl()
            )
            assert append_summary.row(0) == (2, 1)
            snapshot_history = _lake.snapshots()
            demo_tables = _lake.tables()
            # Bytes podem ser baixados mesmo depois que o lake temporário fecha.
            import io as _io

            _buffer = _io.BytesIO()
            demo_data.write_parquet(_buffer)
            demo_parquet = _buffer.getvalue()
    return (
        append_summary,
        commit_summary,
        demo_data,
        demo_parquet,
        demo_tables,
        rollback_message,
        rollback_summary,
        snapshot_before_commit,
        snapshot_history,
    )


@app.cell
def _(demo_data, demo_parquet, pl):
    QUERY_UF = "Todas"
    filtrado = demo_data if QUERY_UF == "Todas" else demo_data.filter(pl.col("uf") == QUERY_UF)
    resumo_consulta = (
        filtrado.group_by("uf", "ano")
        .agg(pl.len().alias("atendimentos"), pl.col("valor").sum().alias("valor_total"))
        .sort("uf", "ano")
    )
    {"registros": filtrado, "agregacao": resumo_consulta, "parquet_bytes": len(demo_parquet)}
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3 · Commit, rollback e histórico
    """)
    return


@app.cell
def _(
    commit_summary,
    demo_tables,
    rollback_message,
    rollback_summary,
    snapshot_before_commit,
    snapshot_history,
):
    {
        "snapshot_antes_do_commit": snapshot_before_commit,
        "tabelas": demo_tables,
        "commit": commit_summary,
        "erro_controlado": rollback_message,
        "rollback": rollback_summary,
        "historico": snapshot_history,
    }
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 4 · Reprocessamento: append pode duplicar

    Duas chamadas com o mesmo registro geram duas linhas. Antes de repetir um
    escopo real, inspecione os resultados e o catálogo.
    """)
    return


@app.cell
def _(append_summary):
    append_summary
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 5 · Interpretar sucesso, ausência, falha e aborto

    Os objetos abaixo são **simulados** para exercitar a leitura do contrato sem provocar falhas externas.
    """)
    return


@app.cell
def _(odb):
    def report_rows(report):
        return [
            {
                "escopo": str(outcome.scope),
                "status": outcome.status,
                "linhas": outcome.result.rows if outcome.result else None,
                "snapshot": outcome.result.snapshot_id if outcome.result else None,
                "motivo": outcome.reason,
            }
            for outcome in report.outcomes
        ]

    simulated_report = odb.ImportReport(
        outcomes=(
            odb.ScopeOutcome(odb.ScopeKey("RR", 2023), "ok", odb.ImportResult(10, 1024, 0.2, 1)),
            odb.ScopeOutcome(odb.ScopeKey("RR", 1900), "skipped", reason="Fora da cobertura"),
            odb.ScopeOutcome(
                odb.ScopeKey("SP", 2023), "failed", reason="Falha simulada de leitura"
            ),
        )
    )
    simulated_abort = odb.ImportAbortedError(
        report=simulated_report, unresolved=((3, odb.ScopeKey("RJ", 2023)),)
    )
    assert len(simulated_report.failed) == 1
    return report_rows, simulated_abort, simulated_report


@app.cell
def _(report_rows, simulated_abort, simulated_report):
    {
        "desfechos": report_rows(simulated_report),
        "ok": len(simulated_report.ok),
        "skipped": len(simulated_report.skipped),
        "failed": len(simulated_report.failed),
        "linhas": simulated_report.rows,
        "unresolved": simulated_abort.unresolved,
    }
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6 · Descobrir e importar dados reais — opcional

    Edite os parâmetros Python e ponha `EXECUTAR_LIVE = True`. A UF e os meses
    são filtrados em Python: `available()` aceita `years` e `refresh`.
    Limitamos a importação a até três escopos; um arquivo ainda pode ser grande.
    Interromper uma célula não garante encerrar o importador na thread.
    """)
    return


@app.cell
def _():
    DATASET_LIVE = "sim_obitos"
    ANO_LIVE = 2023
    UF_LIVE = "RR"
    MESES_LIVE = [1]
    LIMITE_LIVE = 1
    REFRESH_LIVE = False
    EXECUTAR_LIVE = False
    (
        DATASET_LIVE,
        ANO_LIVE,
        UF_LIVE,
        MESES_LIVE,
        LIMITE_LIVE,
        REFRESH_LIVE,
        EXECUTAR_LIVE,
    )
    return (
        ANO_LIVE,
        DATASET_LIVE,
        EXECUTAR_LIVE,
        LIMITE_LIVE,
        MESES_LIVE,
        REFRESH_LIVE,
        UF_LIVE,
    )


@app.cell
async def discover_live(
    ANO_LIVE,
    DATASET_LIVE,
    EXECUTAR_LIVE,
    LIMITE_LIVE,
    MESES_LIVE,
    REFRESH_LIVE,
    UF_LIVE,
    asdict,
    asyncio,
    mo,
    odb,
):
    mo.stop(not EXECUTAR_LIVE, mo.md("Defina `EXECUTAR_LIVE = True` para consultar o DATASUS."))
    selected_config = {
        "dataset": DATASET_LIVE,
        "year": ANO_LIVE,
        "uf": UF_LIVE,
        "months": MESES_LIVE,
        "limit": LIMITE_LIVE,
        "refresh": REFRESH_LIVE,
    }
    _dataset = odb.resolve(selected_config["dataset"])
    try:
        _available = await asyncio.to_thread(
            odb.available,
            _dataset,
            years=[int(selected_config["year"])],
            refresh=selected_config["refresh"],
        )
    except (odb.FtpUnavailable, odb.FtpPathNotFound) as _error:
        mo.stop(True, mo.md(f"Inventário indisponível: `{type(_error).__name__}: {_error}`"))
    selected_scopes = [
        scope
        for scope in _available
        if scope.uf == selected_config["uf"]
        and (not _dataset.monthly or scope.mes in selected_config["months"])
    ][: int(selected_config["limit"])]
    mo.stop(
        not selected_scopes,
        mo.md("Nenhum escopo encontrado. Altere os parâmetros e consulte novamente."),
    )
    [asdict(scope) for scope in selected_scopes]
    return selected_config, selected_scopes


@app.cell
async def execute_live_import(
    EXECUTAR_LIVE,
    Path,
    asyncio,
    mo,
    odb,
    report_rows,
    selected_config,
    selected_scopes,
    uuid4,
):
    mo.stop(not EXECUTAR_LIVE, mo.md("Defina `EXECUTAR_LIVE = True` para importar."))
    live_directory = (Path.cwd() / "data/lake/marimo-runs" / uuid4().hex).resolve()
    live_target = f"ducklake:{live_directory / 'dados.ducklake'}"

    def _import_live():
        if selected_config["dataset"] == "cnes_estabelecimentos":
            return odb.import_cnes_estabelecimentos(scopes=selected_scopes, target=live_target)
        return odb.import_dataset(
            selected_config["dataset"],
            scopes=selected_scopes,
            target=live_target,
            concurrency=2,
            batch_size=1,
        )

    _unresolved = ()
    _aborted = False
    try:
        _report = await asyncio.to_thread(_import_live)
    except odb.ImportAbortedError as _error:
        _report = _error.report
        _unresolved = _error.unresolved
        _aborted = True
    {
        "destino": live_target,
        "aborto": _aborted,
        "ok": len(_report.ok),
        "skipped": len(_report.skipped),
        "failed": len(_report.failed),
        "desfechos": report_rows(_report),
        "unresolved": _unresolved,
    }
    return (live_target,)


@app.cell
def _(live_target, odb):
    with odb.LakeReader(live_target) as _read_lake:
        {"tabelas": _read_lake.tables(), "snapshots": _read_lake.snapshots()}
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7 · Receitas para continuar no seu lake

    Os trechos abaixo são receitas para copiar; não executam chamadas adicionais.

    **Consultar dados importados:** mantenha a conexão aberta até materializar o resultado.

    ```python
    with odb.LakeReader(live_target) as lake:
        df = lake.connect().execute(
            "SELECT uf, ano, count(*) AS registros FROM lake.sim_obitos "
            "WHERE uf = ? GROUP BY uf, ano", ["RR"]
        ).pl()
    # Ajuste a tabela ao dataset importado.
    ```

    **CNES: nomes de até três estabelecimentos já importados.**
    `import_cnes_estabelecimentos` atualiza `aux_cnes`; `import_dataset("cnes_estabelecimentos", ...)` exige
    `lake.ensure_aux_cnes_view()` depois. A visão seleciona a linha completa da
    última competência, preserva seus NULLs e rejeita empates conflitantes.
    O nome do master é enriquecimento atual, sem garantia histórica.

    ```python
    with odb.LakeReader(live_target) as lake:
        codes = [row[0] for row in lake.connect().sql(
            "SELECT DISTINCT cnes FROM lake.cnes_estabelecimentos "
            "WHERE cnes IS NOT NULL ORDER BY cnes LIMIT 3"
        ).fetchall()]
    written = await asyncio.to_thread(
        odb.import_cnes_master, codes=codes, target=live_target, concurrency=2
    )
    # written é int. Falhas HTTP individuais podem ser omitidas: confira os códigos.
    ```

    **IBGE: produto e edição explícitos.** O censo municipal de 2022 usa
    agregado 4714/variável 93, com validação de metadados, cobertura e proveniência.
    Estimativas históricas sem universo territorial da edição são recusadas.
    Confira a referência populacional e territorial antes de calcular uma taxa.
    O retorno é `list[ImportResult]`, diferente do relatório FTP.

    ```python
    ibge_results = await asyncio.to_thread(
        odb.import_ibge_populacao, years=[2022], product="census", target=live_target
    )
    for result in ibge_results:
        print(result.rows, result.snapshot_id, result.publication_id)
    ```

    **Outros ambientes:** `Lake.cloud(catalog=..., storage=...)` recebe catálogo
    PostgreSQL e armazenamento remoto. Credenciais são configuradas no ambiente.
    O parser preserva os parâmetros PostgreSQL além de extrair `storage`.
    Catálogos locais usam lock cooperativo; cloud exige coordenação externa.
    Esta demonstração não valida cloud. Compactação, expiração de snapshots e
    limpeza física têm operações próprias, descritas no guia de manutenção.

    Referências: `docs/api.md`, `docs/guides/inventory.md`,
    `docs/sources/cnes_estabelecimentos.md`, `docs/sources/ibge_populacao.md`.
    A seção 6 só acessa a rede quando `EXECUTAR_LIVE = True`.
    """)
    return


if __name__ == "__main__":
    app.run()

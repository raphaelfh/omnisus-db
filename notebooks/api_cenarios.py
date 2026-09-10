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

    Um roteiro executável: **planejar → gravar → consultar → verificar → importar**.
    Os exemplos locais usam dados fictícios e um lake temporário que é removido
    ao terminar a célula. As tabelas exibidas ficam materializadas em memória.
    DuckDB pode baixar a extensão DuckLake na primeira execução.

    As chamadas ao DATASUS ficam na seção 6 e exigem um clique. Cada importação
    cria um destino próprio em `data/lake/marimo-runs/`, relativo ao diretório
    de execução, e mantém os arquivos para inspeção. Use **um escritor por lake**.
    Execute pela raiz do checkout atual; a tag histórica `v0.1.0` tem outra API.
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
def _(asdict, mo, odb):
    annual_scopes = odb.scopes_for("sim", years=[2022, 2023], ufs=["RR", "SP"])
    monthly_scopes = odb.scopes_for("sih", years=[2024], ufs=["RR"], months=[1, 2])
    mo.vstack(
        [
            mo.md("`scopes_for` monta combinações; a existência no FTP ainda não foi verificada."),
            mo.ui.table([asdict(s) for s in annual_scopes], label="SIM · anual"),
            mo.ui.table([asdict(s) for s in monthly_scopes], label="SIH · mensal"),
        ]
    )
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
def _(mo):
    query_uf = mo.ui.dropdown(["Todas", "RR", "SP"], value="Todas", label="UF da consulta")
    query_uf
    return (query_uf,)


@app.cell
def _(demo_data, demo_parquet, mo, pl, query_uf):
    _filtered = (
        demo_data
        if query_uf.value == "Todas"
        else demo_data.filter(pl.col("uf") == query_uf.value)
    )
    _summary = (
        _filtered.group_by("uf", "ano")
        .agg(pl.len().alias("atendimentos"), pl.col("valor").sum().alias("valor_total"))
        .sort("uf", "ano")
    )
    mo.vstack(
        [
            mo.ui.table(_filtered, label="Registros fictícios · SQL → Polars"),
            mo.ui.table(_summary, label="Agregação com Polars"),
            mo.download(
                demo_parquet,
                filename="demo_atendimentos.parquet",
                label="Baixar exemplo completo em Parquet",
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(
    commit_summary,
    demo_tables,
    mo,
    rollback_message,
    rollback_summary,
    snapshot_before_commit,
    snapshot_history,
):
    mo.vstack(
        [
            mo.md("## 3 · Commit, rollback e histórico"),
            mo.md(
                f"Snapshot dentro da transação: `{snapshot_before_commit}`. Tabelas: `{demo_tables}`."
            ),
            mo.json(commit_summary),
            mo.md(f"**Erro controlado:** {rollback_message}"),
            mo.json(rollback_summary),
            mo.ui.table(snapshot_history, label="Snapshots do catálogo, não apenas de uma tabela"),
            mo.md(
                "`bytes_written` mede o Parquet temporário. Um `snapshot_id=None` isolado não prova falha do commit; consulte o recibo. Transações gerenciadas não podem ser aninhadas."
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(append_summary, mo):
    mo.vstack(
        [
            mo.md("## 4 · Reprocessamento: append pode duplicar"),
            mo.ui.table(append_summary),
            mo.md(
                "Duas chamadas com o mesmo registro geram duas linhas. Antes de repetir um escopo real, inspecione os resultados e o catálogo. O notebook cria um lake novo por importação real para permitir comparar tentativas."
            ),
        ]
    )
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


@app.cell(hide_code=True)
def _(mo, report_rows, simulated_abort, simulated_report):
    mo.vstack(
        [
            mo.ui.table(report_rows(simulated_report)),
            mo.md(
                f"Confirmados: **{len(simulated_report.ok)}** · Ausentes: **{len(simulated_report.skipped)}** · Falhos: **{len(simulated_report.failed)}** · Linhas: **{simulated_report.rows}**"
            ),
            mo.md(f"Aborto simulado, posições não resolvidas: `{simulated_abort.unresolved}`."),
            mo.md(
                "Inspecione `report.failed`, não `bool(report)`. `skipped` significa ausência reconhecida, não falha de conexão. Em `ImportAbortedError`, `report` contém desfechos conhecidos e `unresolved` traz índices da entrada original. Um commit incerto exige inspeção antes de retry; não reimporte automaticamente."
            ),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6 · Descobrir e importar dados reais — opcional

    Escolha os parâmetros, confirme o formulário e consulte o inventário. A UF e
    os meses são filtrados em Python: `available()` aceita `years` e `refresh`.
    Limitamos a importação a até três escopos; um arquivo ainda pode ser grande.
    `concurrency` limita downloads; o parser pode manter um escopo inteiro em memória.
    `batch_size` define quantos escopos compartilham uma transação.
    Interromper uma célula não garante encerrar o importador na thread: aguarde
    sua conclusão e inspecione o destino exibido antes de iniciar outra tentativa.
    """)
    return


@app.cell
def _(mo, odb):
    live_config = mo.ui.dictionary(
        {
            "dataset": mo.ui.dropdown(
                ["sim_do", "sinasc_nv", "sih_rd", "cnes_st", "sia_bi"],
                value="sim_do",
                label="Dataset",
            ),
            "year": mo.ui.number(start=2008, stop=2100, value=2023, label="Ano"),
            "uf": mo.ui.dropdown(list(odb.ALL_UFS), value="RR", label="UF"),
            "months": mo.ui.multiselect(
                list(range(1, 13)), value=[1], label="Meses (ignorados para anual)"
            ),
            "limit": mo.ui.number(start=1, stop=3, value=1, label="Máximo de escopos"),
            "refresh": mo.ui.checkbox(value=False, label="Atualizar cache do inventário"),
        }
    ).form(submit_button_label="Confirmar parâmetros")
    live_config
    return (live_config,)


@app.cell
def _(mo):
    discover_button = mo.ui.run_button(label="Consultar inventário DATASUS")
    discover_button
    return (discover_button,)


@app.cell
async def discover_live(asdict, asyncio, discover_button, live_config, mo, odb):
    mo.stop(not discover_button.value, mo.md("Inventário aguardando clique."))
    mo.stop(live_config.value is None, mo.md("Confirme os parâmetros primeiro."))
    selected_config = dict(live_config.value)
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
    mo.ui.table([asdict(scope) for scope in selected_scopes], label="Escopos que serão importados")
    return selected_config, selected_scopes


@app.cell
def _(mo, selected_scopes):
    import_button = mo.ui.run_button(
        label=f"Importar {len(selected_scopes)} escopo(s) em um lake novo"
    )
    import_button
    return (import_button,)


@app.cell
async def execute_live_import(
    Path,
    asyncio,
    import_button,
    mo,
    odb,
    report_rows,
    selected_config,
    selected_scopes,
    uuid4,
):
    mo.stop(not import_button.value, mo.md("Importação aguardando clique."))
    live_directory = (Path.cwd() / "data/lake/marimo-runs" / uuid4().hex).resolve()
    live_target = f"ducklake:{live_directory / 'dados.ducklake'}"
    mo.output.append(mo.md(f"**Tentativa em andamento:** `{live_target}`"))

    def _import_live():
        # Os wrappers síncronos usam asyncio.run: execute fora do loop do notebook.
        if selected_config["dataset"] == "cnes_st":
            return odb.import_cnes_st(scopes=selected_scopes, target=live_target)
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
    mo.vstack(
        [
            mo.md(f"Destino desta tentativa: `{live_target}`"),
            mo.md(
                f"Aborto: **{_aborted}** · ok: **{len(_report.ok)}** · skipped: **{len(_report.skipped)}** · failed: **{len(_report.failed)}**"
            ),
            mo.ui.table(report_rows(_report)),
            mo.md(f"Entradas não resolvidas: `{_unresolved}`. Inspecione antes de repetir."),
        ]
    )
    return (live_target,)


@app.cell
def _(live_target, mo, odb):
    # A célula só recebe o destino depois que o escritor terminou e fechou o lake.
    with odb.Lake.local(live_target) as _read_lake:
        _tables = _read_lake.tables()
        _snapshots = _read_lake.snapshots()
    mo.vstack(
        [
            mo.md(f"Tabelas encontradas ao reabrir: `{_tables}`"),
            mo.ui.table(_snapshots, label="Histórico persistido"),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7 · Receitas para continuar no seu lake

    Os trechos abaixo são receitas para copiar; não executam chamadas adicionais.

    **Consultar dados importados:** mantenha a conexão aberta até materializar o resultado.

    ```python
    with odb.Lake.local(live_target) as lake:
        df = lake.connect().execute(
            "SELECT uf, ano, count(*) AS registros FROM lake.sim_do "
            "WHERE uf = ? GROUP BY uf, ano", ["RR"]
        ).pl()
    # Ajuste a tabela ao dataset importado.
    ```

    **CNES: nomes de até três estabelecimentos já importados.**
    `import_cnes_st` atualiza `aux_cnes`; `import_dataset("cnes_st", ...)` exige
    `lake.ensure_aux_cnes_view()` depois. A visão usa `arg_max` por campo e não
    garante que todos os campos representem a mesma competência.

    ```python
    with odb.Lake.local(live_target) as lake:
        codes = [row[0] for row in lake.connect().sql(
            "SELECT DISTINCT cnes FROM lake.cnes_st "
            "WHERE cnes IS NOT NULL ORDER BY cnes LIMIT 3"
        ).fetchall()]
    written = await asyncio.to_thread(
        odb.import_cnes_master, codes=codes, target=live_target, concurrency=2
    )
    # written é int. Falhas HTTP individuais podem ser omitidas: confira os códigos.
    ```

    **IBGE: diagnóstico, com limitação conhecida de origem.** O importador atual
    usa agregado 793/variável 93; a adequação da série ao ano pedido está pendente
    da entrega D2. Não trate a saída como denominador validado de uma taxa.
    O retorno é `list[ImportResult]`, diferente do relatório FTP.

    ```python
    ibge_results = await asyncio.to_thread(
        odb.import_ibge_pop, years=[2022], target=live_target
    )
    for result in ibge_results:
        print(result.rows, result.snapshot_id)
    ```

    **Outros ambientes:** `Lake.cloud(catalog=..., storage=...)` recebe catálogo
    PostgreSQL e armazenamento remoto. Credenciais são configuradas no ambiente.
    Continua valendo um escritor; parâmetros extras da query PostgreSQL são
    descartados pelo parser atual. Cloud, `optimize` e `vacuum` não estão
    certificados por esta demonstração local.

    Referências: `docs/api.md`, `docs/guides/inventory.md`,
    `docs/sources/cnes_st.md`, `docs/sources/ibge_pop.md`.
    O controle das operações externas segue o
    [run button do marimo](https://docs.marimo.io/api/inputs/run_button/).
    """)
    return


if __name__ == "__main__":
    app.run()

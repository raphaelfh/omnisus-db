"""CNES · estabelecimentos: do arquivo do DATASUS a uma tabela citável, em seis etapas."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="CNES · estabelecimentos")


@app.cell
def _():
    import asyncio
    from dataclasses import asdict

    import marimo as mo
    from _comum import (
        LIMITE_BYTES,
        conferir,
        executar_sem_botoes,
        fixar_plano,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )

    import omnisus_db as odb
    from omnisus_db.transforms.dictionaries import load_dicionario

    dataset = "cnes_estabelecimentos"
    executar = executar_sem_botoes(mo.cli_args())
    return (
        LIMITE_BYTES,
        asdict,
        asyncio,
        conferir,
        dataset,
        executar,
        fixar_plano,
        load_dicionario,
        mo,
        odb,
        registrar_importacao,
        registrar_proveniencia,
        target_padrao,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # CNES · estabelecimentos

    Arquivo de estabelecimentos (ST) do Cadastro Nacional de Estabelecimentos de
    Saúde (CNES), publicado pelo DATASUS por UF e competência. Este notebook percorre
    as seis etapas do [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/)
    com um recorte pequeno: **Roraima, janeiro de 2024**.

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão.

    O dicionário empacotado declara 12 colunas. Antes de interpretar números, leia o
    [perfil do CNES](https://raphaelfh.github.io/omnisus-db/sources/cnes_estabelecimentos/).
    """)
    return


@app.cell
def _(dataset, load_dicionario, mo):
    _dicionario = load_dicionario(dataset)
    mo.vstack(
        [
            mo.md(
                "## 1 · O que a base registra\n\n"
                "Campos do dicionário que a biblioteca aplica na importação; colunas do "
                "arquivo fora do dicionário também são preservadas."
            ),
            mo.ui.table(
                [
                    {"campo": f["name"], "tipo": f["type"], "rótulo": f.get("label", "")}
                    for f in _dicionario.fields
                ],
                selection=None,
                page_size=12,
            ),
        ]
    )
    return


@app.cell
def _(mo):
    descobrir = mo.ui.run_button(label="Consultar o que o DATASUS publica")
    mo.vstack(
        [
            mo.md("## 2 · Descobrir\n\nLista agora o FTP do DATASUS (`refresh=True`)."),
            descobrir,
        ]
    )
    return (descobrir,)


@app.cell
async def _(asyncio, dataset, descobrir, executar, mo, odb):
    mo.stop(not (executar or descobrir.value), mo.md("A consulta começa pelo botão acima."))
    _publicados = await asyncio.to_thread(odb.available, dataset, ufs=["RR"], refresh=True)
    mo.ui.table(
        [
            {"uf": e.uf, "ano": e.ano, "mes": e.mes}
            for e in sorted(_publicados, key=lambda e: (-e.ano, -(e.mes or 0)))
        ],
        selection=None,
        label="Competências publicadas para RR",
    )
    return


@app.cell
def _(mo, odb, target_padrao):
    uf = mo.ui.dropdown(list(odb.ALL_UFS), value="RR", label="UF do arquivo")
    ano = mo.ui.number(start=2005, stop=2100, step=1, value=2024, label="Ano")
    mes = mo.ui.number(start=1, stop=12, step=1, value=1, label="Mês")
    target = mo.ui.text(value=target_padrao(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## 3 · Planejar e importar\n\n"
                "Confira ano e mês na etapa 2. Fixar o plano grava `plano.json` com um "
                "`run_id` antes de qualquer download. Para também atualizar a visão "
                "`aux_cnes`, a biblioteca oferece `import_cnes_estabelecimentos`."
            ),
            mo.hstack([uf, ano, mes]),
            target,
            fixar,
        ]
    )
    return ano, fixar, mes, target, uf


@app.cell
def _(LIMITE_BYTES, ano, asdict, dataset, executar, fixar, fixar_plano, mes, mo, odb, target, uf):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    escopos = odb.scopes_for(
        dataset, years=[int(ano.value)], ufs=[uf.value], months=[int(mes.value)]
    )
    plano, pasta = fixar_plano(
        target.value,
        dataset=dataset,
        escopos=[asdict(e) for e in escopos],
        policy="skip_same",
        limite_bytes=LIMITE_BYTES,
    )
    importar = mo.ui.run_button(label="Baixar e publicar este plano")
    mo.vstack([mo.md(f"Plano gravado em `{pasta / 'plano.json'}`."), mo.json(plano), importar])
    return escopos, importar, pasta, plano


@app.cell
async def _(
    LIMITE_BYTES, asyncio, escopos, executar, importar, mo, odb, pasta, plano, registrar_importacao
):
    mo.stop(not (executar or importar.value), mo.md("O download só começa pelo botão acima."))
    mo.output.append(
        mo.md(
            "Importando. Interromper a célula não cancela a thread: espere terminar "
            "antes de outra escrita no mesmo lake."
        )
    )
    try:
        relatorio = await asyncio.to_thread(
            odb.import_dataset,
            plano["dataset"],
            scopes=escopos,
            target=plano["target"],
            policy="skip_same",
            run_id=plano["run_id"],
            concurrency=1,
            max_payload_bytes=LIMITE_BYTES,
            max_inflight_bytes=LIMITE_BYTES,
        )
        _nao_resolvidos = ()
    except odb.ImportAbortedError as _erro:
        relatorio, _nao_resolvidos = _erro.report, _erro.unresolved
    _linhas = registrar_importacao(pasta, relatorio, _nao_resolvidos)
    if executar and (relatorio.failed or _nao_resolvidos):
        raise RuntimeError(f"Importação incompleta; veja {pasta / 'resultado.json'}")
    mo.vstack(
        [
            mo.ui.table(_linhas, selection=None, label="Desfecho por escopo"),
            mo.md(
                "`skipped` com *same source and parser version already published* quer "
                "dizer que o mesmo arquivo já estava no lake: nada foi duplicado. "
                "Um arquivo que o DATASUS não publica também aparece como `skipped`."
            ),
        ]
    )
    return (relatorio,)


@app.cell
def _(conferir, dataset, escopos, mo, odb, plano, relatorio):
    with odb.LakeReader(plano["target"]) as _leitor:
        mo.stop(
            dataset not in _leitor.tables(),
            mo.md("Nenhuma tabela publicada; veja os desfechos acima."),
        )
        _desta_execucao = _leitor.publications(run_id=plano["run_id"])
        _conferencia, publicacoes = conferir(_leitor, dataset, escopos)
        snapshot_id = _leitor.snapshots()[-1]["snapshot_id"]
    mo.vstack(
        [
            mo.md(
                "## 4 · Conferir\n\n"
                f"O relatório informou **{relatorio.rows:,} linhas novas**. Abaixo, as "
                "publicações desta execução e a contagem no lake contra o manifesto. "
                "O CNES-ST é publicado num único diretório, então `outdated` não se aplica."
            ),
            mo.ui.table(_desta_execucao, selection=None, label="publications(run_id=...)"),
            mo.ui.table(_conferencia, selection=None, label="Linhas no lake x publicadas"),
            mo.md(f"Snapshot `{snapshot_id}`"),
        ]
    )
    return publicacoes, snapshot_id


@app.cell
def _(escopos, mo, odb, plano, snapshot_id):
    consultas = {
        "estabelecimentos_por_tipo": """
            SELECT trim(CAST(competen AS VARCHAR)) AS competencia,
                   trim(CAST(tp_unid AS VARCHAR)) AS tipo_de_unidade,
                   count(DISTINCT cnes) AS estabelecimentos,
                   count(*) AS linhas
            FROM lake.cnes_estabelecimentos WHERE uf = ? AND ano = ? AND mes = ?
            GROUP BY ALL ORDER BY estabelecimentos DESC
        """,
        "estabelecimentos_por_municipio": """
            SELECT trim(CAST(codufmun AS VARCHAR)) AS municipio,
                   count(DISTINCT cnes) AS estabelecimentos
            FROM lake.cnes_estabelecimentos WHERE uf = ? AND ano = ? AND mes = ?
            GROUP BY ALL ORDER BY estabelecimentos DESC
        """,
    }
    _parametros = [escopos[0].uf, escopos[0].ano, escopos[0].mes]
    with odb.LakeReader(plano["target"], snapshot_id=snapshot_id) as _leitor:
        resultados = {
            nome: _leitor.connect().execute(sql, _parametros).pl()
            for nome, sql in consultas.items()
        }
    mo.vstack(
        [
            mo.md(
                "## 5 · Analisar\n\n"
                f"Consultas sobre o snapshot `{snapshot_id}`. Compare `linhas` e "
                "`estabelecimentos` (códigos CNES distintos) antes de contar unidades. Os "
                "códigos de tipo aparecem como publicados; o perfil explica cada um."
            ),
            mo.ui.tabs(
                {
                    nome: mo.vstack(
                        [
                            mo.ui.table(tabela, selection=None),
                            mo.accordion({"SQL": mo.md(f"```sql\n{consultas[nome]}\n```")}),
                        ]
                    )
                    for nome, tabela in resultados.items()
                }
            ),
        ]
    )
    return consultas, resultados


@app.cell
def _(consultas, mo, pasta, plano, publicacoes, registrar_proveniencia, resultados, snapshot_id):
    registrar_proveniencia(
        pasta, plano=plano, publicacoes=publicacoes, snapshot_id=snapshot_id, consultas=consultas
    )
    for _nome, _tabela in resultados.items():
        _tabela.write_csv(pasta / f"{_nome}.csv")
    mo.vstack(
        [
            mo.md(
                "## 6 · Guardar\n\n"
                f"Resultados e `proveniencia.json` gravados em `{pasta}`. Veja "
                "[Reprodutibilidade](https://raphaelfh.github.io/omnisus-db/pesquisa/reprodutibilidade/)."
            ),
            mo.hstack(
                [
                    mo.download(
                        (pasta / f"{nome}.csv").read_bytes(),
                        filename=f"{plano['dataset']}-{nome}.csv",
                        label=f"CSV · {nome}",
                    )
                    for nome in resultados
                ],
                wrap=True,
            ),
            mo.download(
                (pasta / "proveniencia.json").read_bytes(),
                filename=f"{plano['dataset']}-proveniencia.json",
                label="proveniencia.json",
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()

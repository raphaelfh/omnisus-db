# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.16,<0.25",
#     "omnisus-db",
#     "polars>=1.44.2,<2.0",
# ]
#
# [tool.uv.sources]
# omnisus-db = { git = "https://github.com/raphaelfh/omnisus-db.git" }
# ///

"""SIA · produção ambulatorial: escolha uma das sete tabelas e siga as seis etapas."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="SIA · produção ambulatorial")


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

    tabelas = {
        "sia_bpa_individualizado": "BPA individualizado",
        "sia_apac_medicamentos": "APAC · medicamentos",
        "sia_apac_quimioterapia": "APAC · quimioterapia",
        "sia_apac_tratamento_dialitico": "APAC · tratamento dialítico",
        "sia_apac_laudos_diversos": "APAC · laudos diversos",
        "sia_apac_cirurgia_bariatrica": "APAC · cirurgia bariátrica",
        "sia_psicossocial": "RAAS · atenção psicossocial",
    }
    executar = executar_sem_botoes(mo.cli_args())
    return (
        LIMITE_BYTES,
        tabelas,
        asdict,
        asyncio,
        conferir,
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
    # SIA · produção ambulatorial

    O Sistema de Informações Ambulatoriais do SUS (SIA/SUS) é publicado pelo DATASUS
    em várias tabelas, por UF e mês; a biblioteca importa sete. Escolha uma e siga as
    seis etapas do [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/)
    com um recorte pequeno: **Roraima, janeiro de 2024**.

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão.

    Cada tabela registra uma coisa diferente. Antes de interpretar números, leia o
    [perfil do SIA](https://raphaelfh.github.io/omnisus-db/sources/sia/).
    """)
    return


@app.cell
def _(tabelas, mo):
    tabela = mo.ui.dropdown(
        {rotulo: nome for nome, rotulo in tabelas.items()},
        value="BPA individualizado",
        label="Tabela do SIA",
    )
    tabela
    return (tabela,)


@app.cell
def _(load_dicionario, mo, tabela):
    _dicionario = load_dicionario(tabela.value)
    mo.vstack(
        [
            mo.md(
                f"## 1 · O que a tabela `{tabela.value}` registra\n\n"
                "Campos do dicionário que a biblioteca aplica na importação. "
                "O significado dos códigos está no perfil e no documento oficial citado nele."
            ),
            mo.ui.table(
                [
                    {"campo": f["name"], "tipo": f["type"], "rótulo": f.get("label", "")}
                    for f in _dicionario.fields
                ],
                selection=None,
                page_size=10,
            ),
        ]
    )
    return


@app.cell
def _(mo):
    descobrir = mo.ui.run_button(label="Consultar o que o DATASUS publica")
    mo.vstack(
        [
            mo.md(
                "## 2 · Descobrir\n\n"
                "Lista agora o diretório do SIA no FTP (`refresh=True`) e filtra os "
                "arquivos da tabela escolhida."
            ),
            descobrir,
        ]
    )
    return (descobrir,)


@app.cell
async def _(asyncio, descobrir, executar, mo, odb, tabela):
    mo.stop(not (executar or descobrir.value), mo.md("A consulta começa pelo botão acima."))
    _publicados = await asyncio.to_thread(odb.available, tabela.value, ufs=["RR"], refresh=True)
    mo.ui.table(
        [
            {"uf": e.uf, "ano": e.ano, "mes": e.mes}
            for e in sorted(_publicados, key=lambda e: (-e.ano, -(e.mes or 0)))
        ],
        selection=None,
        label=f"Arquivos de {tabela.value} publicados para RR",
    )
    return


@app.cell
def _(mo, odb, target_padrao):
    uf = mo.ui.dropdown(list(odb.ALL_UFS), value="RR", label="UF do arquivo")
    ano = mo.ui.number(start=2008, stop=2100, step=1, value=2024, label="Ano")
    mes = mo.ui.number(start=1, stop=12, step=1, value=1, label="Mês")
    target = mo.ui.text(value=target_padrao(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## 3 · Planejar e importar\n\n"
                "Confira ano e mês na etapa 2. O plano guarda a tabela escolhida; mudar a "
                "tabela depois exige fixar um novo plano. O notebook limita cada download "
                "comprimido a 25 MiB (`LIMITE_BYTES` em `_comum.py`); um arquivo maior "
                "(por exemplo outra UF) termina como `failed`, e pode ser importado "
                "subindo esse limite ou com a chamada direta `odb.import_dataset` no "
                'perfil desta base ("Como usar").'
            ),
            mo.hstack([uf, ano, mes]),
            target,
            fixar,
        ]
    )
    return ano, fixar, mes, target, uf


@app.cell
def _(LIMITE_BYTES, ano, asdict, executar, fixar, fixar_plano, mes, mo, odb, tabela, target, uf):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    escopos = odb.scopes_for(
        tabela.value, years=[int(ano.value)], ufs=[uf.value], months=[int(mes.value)]
    )
    plano, pasta = fixar_plano(
        target.value,
        dataset=tabela.value,
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
                "Um arquivo que o DATASUS não publica também aparece como `skipped`: "
                "nem toda tabela existe para toda UF e mês."
            ),
        ]
    )
    return (relatorio,)


@app.cell
def _(conferir, escopos, mo, odb, plano, relatorio):
    with odb.LakeReader(plano["target"]) as _leitor:
        mo.stop(
            plano["dataset"] not in _leitor.tables(),
            mo.md("Nenhuma tabela publicada; veja os desfechos acima."),
        )
        _desta_execucao = _leitor.publications(run_id=plano["run_id"])
        _conferencia, publicacoes = conferir(_leitor, plano["dataset"], escopos)
        mo.stop(
            not publicacoes,
            mo.md(
                "Nenhuma publicação ativa para os escopos deste plano; veja os desfechos acima."
            ),
        )
        snapshot_id = _leitor.snapshots()[-1]["snapshot_id"]
    mo.vstack(
        [
            mo.md(
                "## 4 · Conferir\n\n"
                f"O relatório informou **{relatorio.rows:,} linhas novas**. Abaixo, as "
                "publicações desta execução e a contagem no lake contra o manifesto. "
                "O SIA é publicado num único diretório, então `outdated` não se aplica."
            ),
            mo.ui.table(_desta_execucao, selection=None, label="publications(run_id=...)"),
            mo.ui.table(_conferencia, selection=None, label="Linhas no lake x publicadas"),
            mo.md(f"Snapshot `{snapshot_id}`"),
        ]
    )
    return publicacoes, snapshot_id


@app.cell
def _(escopos, mo, odb, plano, snapshot_id):
    _tabela = plano["dataset"]
    _recorte = "WHERE uf = ? AND ano = ? AND mes = ?"
    _analises = {
        "sia_apac_medicamentos": {
            "apac_por_procedimento_principal": f"""
                SELECT trim(CAST(ap_pripal AS VARCHAR)) AS procedimento_principal,
                       count(*) AS apac,
                       round(sum(TRY_CAST(ap_vl_ap AS DOUBLE)), 2) AS valor_aprovado
                FROM lake.sia_apac_medicamentos {_recorte}
                GROUP BY ALL ORDER BY apac DESC
            """
        },
        "sia_bpa_individualizado": {
            "quantidade_por_procedimento": f"""
                SELECT trim(CAST(proc_id AS VARCHAR)) AS procedimento,
                       count(*) AS registros,
                       sum(TRY_CAST(qt_aprov AS BIGINT)) AS quantidade_aprovada
                FROM lake.sia_bpa_individualizado {_recorte}
                GROUP BY ALL ORDER BY quantidade_aprovada DESC NULLS LAST
            """
        },
        "sia_psicossocial": {
            "acoes_por_cid_principal": f"""
                SELECT trim(CAST(pa_proc_id AS VARCHAR)) AS acao_realizada,
                       upper(trim(CAST(cidpri AS VARCHAR))) AS cid10_principal,
                       count(*) AS registros
                FROM lake.sia_psicossocial {_recorte}
                GROUP BY ALL ORDER BY registros DESC
            """
        },
    }
    # _tabela vem do plano, que só aceita as sete chaves de tabelas.
    _sql_por_nome = _analises.get(
        _tabela,
        {"registros_no_recorte": f'SELECT count(*) AS registros FROM lake."{_tabela}" {_recorte}'},
    )
    _parametros = [escopos[0].uf, escopos[0].ano, escopos[0].mes]
    consultas = {
        nome: {"sql": sql, "parametros": _parametros} for nome, sql in _sql_por_nome.items()
    }
    with odb.LakeReader(plano["target"], snapshot_id=snapshot_id) as _leitor:
        resultados = {
            nome: _leitor.connect().execute(consulta["sql"], consulta["parametros"]).pl()
            for nome, consulta in consultas.items()
        }
    _aviso = (
        ""
        if _tabela in _analises
        else "\n\nPara esta tabela os campos de análise ainda não foram verificados; "
        "a etapa mostra só a contagem. Use o dicionário da etapa 1 e o perfil."
    )
    mo.vstack(
        [
            mo.md(f"## 5 · Analisar\n\nConsultas sobre o snapshot `{snapshot_id}`.{_aviso}"),
            mo.ui.tabs(
                {
                    nome: mo.vstack(
                        [
                            mo.ui.table(tabela_resultado, selection=None),
                            mo.accordion({"SQL": mo.md(f"```sql\n{consultas[nome]['sql']}\n```")}),
                        ]
                    )
                    for nome, tabela_resultado in resultados.items()
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
    for _nome, _resultado in resultados.items():
        _resultado.write_csv(pasta / f"{_nome}.csv")
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

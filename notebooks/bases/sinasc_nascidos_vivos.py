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

"""SINASC · nascidos vivos: do arquivo do DATASUS a uma tabela citável, em seis etapas."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="SINASC · nascidos vivos")


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

    dataset = "sinasc_nascidos_vivos"
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
    # SINASC · nascidos vivos

    Base do Sistema de Informações sobre Nascidos Vivos (SINASC), publicada pelo
    DATASUS. Este notebook percorre as seis etapas do
    [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/) com um
    recorte pequeno: **Roraima, 2022**.

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão. Os dados vão para o lake de pesquisa compartilhado
    (`data/lake/pesquisa/`), o mesmo dos outros notebooks de `bases/`.

    Antes de interpretar números, leia o
    [perfil do SINASC](https://raphaelfh.github.io/omnisus-db/sources/sinasc_nascidos_vivos/).
    """)
    return


@app.cell
def _(dataset, load_dicionario, mo):
    _dicionario = load_dicionario(dataset)
    mo.vstack(
        [
            mo.md(
                "## 1 · O que a base registra\n\n"
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
                "Lista agora o FTP do DATASUS (`refresh=True`). A coluna `diretorio` "
                "diz se cada ano está no diretório final ou no preliminar."
            ),
            descobrir,
        ]
    )
    return (descobrir,)


@app.cell
async def _(asyncio, dataset, descobrir, executar, mo, odb):
    mo.stop(not (executar or descobrir.value), mo.md("A consulta começa pelo botão acima."))
    _publicados = await asyncio.to_thread(
        odb.available_releases, dataset, ufs=["RR"], refresh=True
    )
    mo.ui.table(
        [
            {"uf": e.uf, "ano": e.ano, "diretorio": r}
            for e, r in sorted(_publicados.items(), key=lambda item: -item[0].ano)
        ],
        selection=None,
        label="Arquivos publicados para RR",
    )
    return


@app.cell
def _(mo, odb, target_padrao):
    uf = mo.ui.dropdown(list(odb.ALL_UFS), value="RR", label="UF do arquivo")
    ano = mo.ui.number(start=1994, stop=2100, step=1, value=2022, label="Ano")
    target = mo.ui.text(value=target_padrao(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## 3 · Planejar e importar\n\n"
                "Confira o ano na etapa 2. Fixar o plano grava `plano.json` com um "
                "`run_id` antes de qualquer download. O notebook limita cada download "
                "comprimido a 25 MiB (`LIMITE_BYTES` em `_comum.py`); um arquivo maior "
                "(por exemplo outra UF) termina como `failed`, e pode ser importado "
                "subindo esse limite ou com a chamada direta `odb.import_dataset` no "
                'perfil desta base ("Como usar").'
            ),
            mo.hstack([uf, ano]),
            target,
            fixar,
        ]
    )
    return ano, fixar, target, uf


@app.cell
def _(LIMITE_BYTES, ano, asdict, dataset, executar, fixar, fixar_plano, mo, odb, target, uf):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    escopos = odb.scopes_for(dataset, years=[int(ano.value)], ufs=[uf.value])
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
        mo.stop(
            not publicacoes,
            mo.md(
                "Nenhuma publicação ativa para os escopos deste plano; veja os desfechos acima."
            ),
        )
        snapshot_id = _leitor.snapshots()[-1]["snapshot_id"]
        # refresh=False usa a listagem em cache do FTP, preenchida pela etapa 2 ou
        # pela própria importação: não faz um novo crawl do servidor público.
        _desatualizados = odb.outdated(dataset, lake=_leitor)
    mo.vstack(
        [
            mo.md(
                "## 4 · Conferir\n\n"
                f"O relatório informou **{relatorio.rows:,} linhas novas**. Abaixo, as "
                "publicações desta execução, a contagem no lake contra o manifesto e os "
                "escopos que o DATASUS moveu de diretório desde a importação (`outdated`)."
            ),
            mo.ui.table(_desta_execucao, selection=None, label="publications(run_id=...)"),
            mo.ui.table(_conferencia, selection=None, label="Linhas no lake x publicadas"),
            mo.md(
                f"Desatualizados: `{[str(e) for e in _desatualizados]}` · snapshot `{snapshot_id}`"
            ),
        ]
    )
    return publicacoes, snapshot_id


@app.cell
def _(escopos, mo, odb, plano, snapshot_id):
    _parametros = [escopos[0].uf, escopos[0].ano]
    consultas = {
        "nascidos_por_municipio_de_residencia": {
            "sql": """
                SELECT trim(CAST(codmunres AS VARCHAR)) AS municipio_residencia,
                       count(*) AS nascidos_vivos
                FROM lake.sinasc_nascidos_vivos WHERE uf = ? AND ano = ?
                GROUP BY ALL ORDER BY nascidos_vivos DESC
            """,
            "parametros": _parametros,
        },
        "peso_ao_nascer": {
            "sql": """
                SELECT count(*) AS nascidos_vivos,
                       count(TRY_CAST(peso AS INTEGER)) AS com_peso_numerico,
                       count(*) FILTER (WHERE TRY_CAST(peso AS INTEGER) < 2500)
                           AS peso_abaixo_de_2500_g
                FROM lake.sinasc_nascidos_vivos WHERE uf = ? AND ano = ?
            """,
            "parametros": _parametros,
        },
        "consultas_pre_natal": {
            "sql": """
                SELECT trim(CAST(consultas AS VARCHAR)) AS consultas_codigo,
                       count(*) AS nascidos_vivos
                FROM lake.sinasc_nascidos_vivos WHERE uf = ? AND ano = ?
                GROUP BY ALL ORDER BY consultas_codigo
            """,
            "parametros": _parametros,
        },
        "tipo_de_parto": {
            "sql": """
                SELECT trim(CAST(parto AS VARCHAR)) AS parto_codigo, count(*) AS nascidos_vivos
                FROM lake.sinasc_nascidos_vivos WHERE uf = ? AND ano = ?
                GROUP BY ALL ORDER BY parto_codigo
            """,
            "parametros": _parametros,
        },
    }
    with odb.LakeReader(plano["target"], snapshot_id=snapshot_id) as _leitor:
        resultados = {
            nome: _leitor.connect().execute(consulta["sql"], consulta["parametros"]).pl()
            for nome, consulta in consultas.items()
        }
    mo.vstack(
        [
            mo.md(
                "## 5 · Analisar\n\n"
                f"Consultas sobre o snapshot `{snapshot_id}`. `com_peso_numerico` mostra "
                "quantos registros têm peso utilizável antes de qualquer proporção. Os "
                "códigos aparecem como publicados; o perfil explica cada um."
            ),
            mo.ui.tabs(
                {
                    nome: mo.vstack(
                        [
                            mo.ui.table(tabela, selection=None),
                            mo.accordion({"SQL": mo.md(f"```sql\n{consultas[nome]['sql']}\n```")}),
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

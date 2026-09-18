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

"""SIM · óbitos: do arquivo do DATASUS a uma tabela citável, em seis etapas."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="SIM · óbitos")


@app.cell
def _():
    import asyncio
    from dataclasses import asdict

    import marimo as mo

    import omnisus_db as odb
    from omnisus_db._notebooks import (
        default_target,
        reconcile,
        record_import,
        record_provenance,
        run_without_buttons,
        save_plan,
    )
    from omnisus_db.transforms.dictionaries import load_dicionario

    dataset = "sim_obitos"
    MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
    executar = run_without_buttons(mo.cli_args())
    return (
        MAX_DOWNLOAD_BYTES,
        asdict,
        asyncio,
        reconcile,
        dataset,
        executar,
        save_plan,
        load_dicionario,
        mo,
        odb,
        record_import,
        record_provenance,
        default_target,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # SIM · óbitos

    [![Open in molab](https://molab.marimo.io/molab-shield.svg)](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/bases/sim_obitos.py)

    Base de óbitos do Sistema de Informações sobre Mortalidade (SIM), publicada
    pelo DATASUS. Este notebook percorre as seis etapas do
    [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/) com um
    recorte pequeno: **Roraima, 2022**.

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão. Os dados vão para o lake de pesquisa compartilhado
    (`data/lake/pesquisa/`), o mesmo dos outros notebooks de `bases/`.

    Antes de interpretar números, leia o
    [perfil do SIM](https://raphaelfh.github.io/omnisus-db/sources/sim_obitos/):
    o que um registro representa, datas, geografia e armadilhas, com as fontes.
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
                "Lista agora o FTP do DATASUS (`refresh=True`). O SIM tem um diretório "
                "final e um preliminar; a coluna `diretorio` diz onde cada ano está."
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
def _(mo, odb, default_target):
    uf = mo.ui.dropdown(list(odb.ALL_UFS), value="RR", label="UF do arquivo")
    ano = mo.ui.number(start=1996, stop=2100, step=1, value=2022, label="Ano")
    target = mo.ui.text(value=default_target(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## 3 · Planejar e importar\n\n"
                "Confira o ano na etapa 2. Fixar o plano grava `plano.json` com um "
                "`run_id` antes de qualquer download: é o `run_id` que permite "
                "reconciliar uma importação interrompida. O notebook limita cada "
                "download comprimido a 25 MiB (`MAX_DOWNLOAD_BYTES` no próprio notebook); um "
                "arquivo maior (por exemplo outra UF) termina como `failed`, e pode "
                "ser importado subindo esse limite ou com a chamada direta "
                '`odb.import_dataset` no perfil desta base ("Como usar").'
            ),
            mo.hstack([uf, ano]),
            target,
            fixar,
        ]
    )
    return ano, fixar, target, uf


@app.cell
def _(MAX_DOWNLOAD_BYTES, ano, asdict, dataset, executar, fixar, save_plan, mo, odb, target, uf):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    escopos = odb.scopes_for(dataset, years=[int(ano.value)], ufs=[uf.value])
    plano, pasta = save_plan(
        target.value,
        dataset=dataset,
        scopes=[asdict(e) for e in escopos],
        policy="skip_same",
        max_download_bytes=MAX_DOWNLOAD_BYTES,
    )
    importar = mo.ui.run_button(label="Baixar e publicar este plano")
    mo.vstack([mo.md(f"Plano gravado em `{pasta / 'plano.json'}`."), mo.json(plano), importar])
    return escopos, importar, pasta, plano


@app.cell
async def _(
    MAX_DOWNLOAD_BYTES, asyncio, escopos, executar, importar, mo, odb, pasta, plano, record_import
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
            max_payload_bytes=MAX_DOWNLOAD_BYTES,
            max_inflight_bytes=MAX_DOWNLOAD_BYTES,
        )
        _nao_resolvidos = ()
    except odb.ImportAbortedError as _erro:
        relatorio, _nao_resolvidos = _erro.report, _erro.unresolved
    _linhas = record_import(pasta, relatorio, _nao_resolvidos)
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
def _(reconcile, dataset, escopos, mo, odb, plano, relatorio):
    with odb.LakeReader(plano["target"]) as _leitor:
        mo.stop(
            dataset not in _leitor.tables(),
            mo.md("Nenhuma tabela publicada; veja os desfechos acima."),
        )
        _desta_execucao = _leitor.publications(run_id=plano["run_id"])
        _conferencia, publicacoes = reconcile(_leitor, dataset, escopos)
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
        "obitos_por_mes": {
            "sql": """
                WITH obitos AS (
                    SELECT COALESCE(
                        TRY_CAST(dtobito AS DATE),
                        TRY_STRPTIME(trim(CAST(dtobito AS VARCHAR)), '%d%m%Y')::DATE
                    ) AS data_obito
                    FROM lake.sim_obitos WHERE uf = ? AND ano = ?
                )
                SELECT coalesce(strftime(data_obito, '%Y-%m'), 'sem data válida') AS mes,
                       count(*) AS obitos
                FROM obitos GROUP BY ALL ORDER BY mes
            """,
            "parameters": _parametros,
        },
        "obitos_por_sexo_e_causa": {
            "sql": """
                SELECT trim(CAST(sexo AS VARCHAR)) AS sexo_codigo,
                       left(upper(trim(CAST(causabas AS VARCHAR))), 3) AS causa_basica_cid10_3,
                       count(*) AS obitos
                FROM lake.sim_obitos WHERE uf = ? AND ano = ?
                GROUP BY ALL ORDER BY obitos DESC
            """,
            "parameters": _parametros,
        },
        "residencia_e_ocorrencia": {
            "sql": """
                SELECT left(trim(CAST(codmunres AS VARCHAR)), 2) AS uf_residencia_ibge,
                       left(trim(CAST(codmunocor AS VARCHAR)), 2) AS uf_ocorrencia_ibge,
                       count(*) AS obitos
                FROM lake.sim_obitos WHERE uf = ? AND ano = ?
                GROUP BY ALL ORDER BY obitos DESC
            """,
            "parameters": _parametros,
        },
    }
    with odb.LakeReader(plano["target"], snapshot_id=snapshot_id) as _leitor:
        resultados = {
            nome: _leitor.connect().execute(consulta["sql"], consulta["parameters"]).pl()
            for nome, consulta in consultas.items()
        }
    mo.vstack(
        [
            mo.md(
                "## 5 · Analisar\n\n"
                f"Consultas sobre o snapshot `{snapshot_id}`: com o mesmo número, a "
                "consulta devolve as mesmas linhas mesmo depois de novas importações. "
                "Os códigos aparecem como publicados; o perfil explica cada um, e a "
                "diferença entre residência e ocorrência."
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
def _(consultas, mo, pasta, plano, publicacoes, record_provenance, resultados, snapshot_id):
    record_provenance(
        pasta, plan=plano, publications=publicacoes, snapshot_id=snapshot_id, queries=consultas
    )
    for _nome, _tabela in resultados.items():
        _tabela.write_csv(pasta / f"{_nome}.csv")
    mo.vstack(
        [
            mo.md(
                "## 6 · Guardar\n\n"
                f"Resultados e `proveniencia.json` gravados em `{pasta}`. Para citar: "
                "arquivo e SHA-256 de cada publicação, `snapshot_id`, versão do "
                "omnisus-db e data de acesso — veja "
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

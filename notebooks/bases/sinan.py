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

"""SINAN · notificações nacionais de Chagas aguda e hanseníase, em seis etapas."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="SINAN · Chagas e hanseníase")


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

    agravos = {"sinan_chagas": "Doença de Chagas aguda", "sinan_hanseniase": "Hanseníase"}
    MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
    executar = run_without_buttons(mo.cli_args())
    return (
        MAX_DOWNLOAD_BYTES,
        agravos,
        asdict,
        asyncio,
        reconcile,
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
    # SINAN · Chagas aguda e hanseníase

    [![Open in molab](https://molab.marimo.io/molab-shield.svg)](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/bases/sinan.py)

    Notificações do Sistema de Informação de Agravos de Notificação (SINAN),
    publicadas pelo DATASUS em **um arquivo nacional por ano**, com diretório final e
    preliminar. Este notebook percorre as seis etapas do
    [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/) com
    **Chagas aguda, 2022** (troque para hanseníase no seletor).

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão.

    Uma notificação não é um caso confirmado nem uma pessoa única. Leia os perfis de
    [Chagas](https://raphaelfh.github.io/omnisus-db/sources/sinan_chagas/) e
    [hanseníase](https://raphaelfh.github.io/omnisus-db/sources/sinan_hanseniase/).
    """)
    return


@app.cell
def _(agravos, mo):
    agravo = mo.ui.dropdown(
        {rotulo: nome for nome, rotulo in agravos.items()},
        value="Doença de Chagas aguda",
        label="Agravo",
    )
    agravo
    return (agravo,)


@app.cell
def _(agravo, load_dicionario, mo):
    _dicionario = load_dicionario(agravo.value)
    mo.vstack(
        [
            mo.md(
                f"## 1 · O que `{agravo.value}` registra\n\n"
                "Campos do dicionário que a biblioteca aplica na importação. "
                "O significado dos códigos está no dicionário oficial citado no perfil."
            ),
            mo.ui.table(
                [{"campo": f["name"], "tipo": f["type"]} for f in _dicionario.fields],
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
                "Lista agora os diretórios final e preliminar (`refresh=True`). Um ano "
                "preliminar pode ser revisado e depois movido para o final com o mesmo nome."
            ),
            descobrir,
        ]
    )
    return (descobrir,)


@app.cell
async def _(agravo, asyncio, descobrir, executar, mo, odb):
    mo.stop(not (executar or descobrir.value), mo.md("A consulta começa pelo botão acima."))
    _publicados = await asyncio.to_thread(odb.available_releases, agravo.value, refresh=True)
    mo.ui.table(
        [
            {"ano": e.ano, "abrangencia": "nacional", "diretorio": r}
            for e, r in sorted(_publicados.items(), key=lambda item: -item[0].ano)
        ],
        selection=None,
        label=f"Arquivos de {agravo.value}",
    )
    return


@app.cell
def _(mo, default_target):
    ano = mo.ui.number(start=2000, stop=2100, step=1, value=2022, label="Ano do arquivo")
    target = mo.ui.text(value=default_target(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## 3 · Planejar e importar\n\n"
                "O arquivo é nacional: não há filtro de UF na importação. Filtre a "
                "geografia dos registros depois, na análise. O notebook limita cada "
                "download comprimido a 25 MiB (`MAX_DOWNLOAD_BYTES` no próprio notebook); um "
                "arquivo maior termina como `failed`, e pode ser importado subindo "
                "esse limite ou com a chamada direta `odb.import_dataset` no perfil "
                'desta base ("Como usar").'
            ),
            ano,
            target,
            fixar,
        ]
    )
    return ano, fixar, target


@app.cell
def _(MAX_DOWNLOAD_BYTES, agravo, ano, asdict, executar, fixar, save_plan, mo, odb, target):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    escopos = odb.scopes_for(agravo.value, years=[int(ano.value)])
    plano, pasta = save_plan(
        target.value,
        dataset=agravo.value,
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
                "dizer que o mesmo arquivo já estava no lake. Um `failed` pedindo "
                "`replace` quer dizer que o DATASUS publicou outra versão do arquivo."
            ),
        ]
    )
    return (relatorio,)


@app.cell
def _(reconcile, escopos, mo, odb, plano, relatorio):
    with odb.LakeReader(plano["target"]) as _leitor:
        mo.stop(
            plano["dataset"] not in _leitor.tables(),
            mo.md("Nenhuma tabela publicada; veja os desfechos acima."),
        )
        _desta_execucao = _leitor.publications(run_id=plano["run_id"])
        _conferencia, publicacoes = reconcile(_leitor, plano["dataset"], escopos)
        mo.stop(
            not publicacoes,
            mo.md(
                "Nenhuma publicação ativa para os escopos deste plano; veja os desfechos acima."
            ),
        )
        snapshot_id = _leitor.snapshots()[-1]["snapshot_id"]
        # refresh=False usa a listagem em cache do FTP, preenchida pela etapa 2 ou
        # pela própria importação: não faz um novo crawl do servidor público.
        _desatualizados = odb.outdated(plano["dataset"], lake=_leitor)
    mo.vstack(
        [
            mo.md(
                "## 4 · Conferir\n\n"
                f"O relatório informou **{relatorio.rows:,} linhas novas**. `outdated` "
                "lista os anos que o DATASUS moveu entre preliminar e final desde a "
                'importação; atualize-os com `policy="replace"` e um novo `run_id`.'
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
    _tabela = plano["dataset"]  # uma das duas chaves de agravos
    _recorte = f'FROM lake."{_tabela}" WHERE _source_ano = ?'
    _parametros = [escopos[0].ano]
    consultas = {
        "diretorio_de_origem": {
            "sql": f"""
                SELECT _source_release AS diretorio, count(*) AS notificacoes {_recorte}
                GROUP BY ALL
            """,
            "parameters": _parametros,
        },
        "notificacoes_por_uf_de_notificacao": {
            "sql": f"""
                SELECT trim(CAST(sg_uf_not AS VARCHAR)) AS uf_notificacao_ibge,
                       count(*) AS notificacoes {_recorte}
                GROUP BY ALL ORDER BY notificacoes DESC
            """,
            "parameters": _parametros,
        },
        "notificacoes_por_uf_de_residencia": {
            "sql": f"""
                SELECT left(trim(CAST(id_mn_resi AS VARCHAR)), 2) AS uf_residencia_ibge,
                       count(*) AS notificacoes {_recorte}
                GROUP BY ALL ORDER BY notificacoes DESC
            """,
            "parameters": _parametros,
        },
    }
    if _tabela == "sinan_chagas":
        consultas["classificacao_e_evolucao"] = {
            "sql": f"""
                SELECT trim(CAST(classi_fin AS VARCHAR)) AS classi_fin,
                       trim(CAST(evolucao AS VARCHAR)) AS evolucao,
                       count(*) AS notificacoes {_recorte}
                GROUP BY ALL ORDER BY classi_fin, evolucao
            """,
            "parameters": _parametros,
        }
    else:
        consultas["modo_de_entrada_e_alta"] = {
            "sql": f"""
                SELECT trim(CAST(modoentr AS VARCHAR)) AS modoentr,
                       trim(CAST(tpalta_n AS VARCHAR)) AS tpalta_n,
                       count(*) AS notificacoes {_recorte}
                GROUP BY ALL ORDER BY modoentr, tpalta_n
            """,
            "parameters": _parametros,
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
                f"Consultas sobre o snapshot `{snapshot_id}`. Os códigos aparecem como "
                "publicados; confira no dicionário oficial antes de selecionar casos "
                "confirmados ou calcular incidência."
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

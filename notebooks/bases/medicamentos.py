# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.16,<0.25",
#     "omnisusdb",
#     "polars>=1.44.2,<2.0",
# ]
#
# [tool.uv.sources]
# omnisusdb = { git = "https://github.com/raphaelfh/omnisus-db.git", rev = "5bdb25a45bea2056316dcd03c6a2c62a23a759cb" }
# ///

"""Medicamentos: APAC do SIA no lake, uma página de estoque do Hórus e o que não existe."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="Medicamentos · APAC e estoque")


@app.cell
def _():
    import asyncio
    from dataclasses import asdict
    from uuid import uuid4

    import marimo as mo

    import omnisus_db as odb
    from omnisus_db._notebooks import (
        data_root,
        default_target,
        reconcile,
        record_import,
        record_provenance,
        run_without_buttons,
        save_plan,
        write_json,
    )
    from omnisus_db.sources.medicamentos import fetch_stock_page
    from omnisus_db.transforms.dictionaries import load_dicionario

    dataset = "sia_apac_medicamentos"
    MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
    executar = run_without_buttons(mo.cli_args())
    return (
        MAX_DOWNLOAD_BYTES,
        asdict,
        asyncio,
        reconcile,
        dataset,
        executar,
        fetch_stock_page,
        save_plan,
        load_dicionario,
        mo,
        odb,
        data_root,
        record_import,
        record_provenance,
        write_json,
        default_target,
        uuid4,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Medicamentos: o que dá para estudar com dados abertos

    [![Open in molab](https://molab.marimo.io/molab-shield.svg)](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/bases/medicamentos.py)

    Três partes:

    - **A · APAC de medicamentos (SIA-AM)** — as seis etapas do
      [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/) com
      **Roraima, janeiro de 2024**, no lake de pesquisa compartilhado.
    - **B · Estoque BNAFAR/Hórus** — uma página da API pública de posição de estoque,
      guardada com proveniência, sem publicar no lake.
    - **C · O que não existe publicamente** — eventos de dispensação.

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão. Leia o
    [perfil de medicamentos](https://raphaelfh.github.io/omnisus-db/sources/medicamentos/)
    antes de interpretar números: um registro de APAC não é uma dose nem uma dispensação.
    """)
    return


@app.cell
def _(dataset, load_dicionario, mo):
    _dicionario = load_dicionario(dataset)
    mo.vstack(
        [
            mo.md("## A1 · O que a APAC de medicamentos registra"),
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
    mo.vstack([mo.md("## A2 · Descobrir"), descobrir])
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
        label="Arquivos SIA-AM publicados para RR",
    )
    return


@app.cell
def _(mo, odb, default_target):
    uf = mo.ui.dropdown(list(odb.ALL_UFS), value="RR", label="UF do arquivo")
    ano = mo.ui.number(start=2008, stop=2100, step=1, value=2024, label="Ano")
    mes = mo.ui.number(start=1, stop=12, step=1, value=1, label="Mês de processamento")
    target = mo.ui.text(value=default_target(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## A3 · Planejar e importar\n\n"
                "Fixar o plano grava `plano.json` com um `run_id` antes de qualquer "
                "download. O notebook limita cada download comprimido a 25 MiB "
                "(`MAX_DOWNLOAD_BYTES` no próprio notebook); um arquivo maior (por exemplo outra "
                "UF) termina como `failed`, e pode ser importado subindo esse limite "
                "ou com a chamada direta `odb.import_dataset` no perfil desta base "
                '("Como usar").'
            ),
            mo.hstack([uf, ano, mes]),
            target,
            fixar,
        ]
    )
    return ano, fixar, mes, target, uf


@app.cell
def _(
    MAX_DOWNLOAD_BYTES, ano, asdict, dataset, executar, fixar, save_plan, mes, mo, odb, target, uf
):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    escopos = odb.scopes_for(
        dataset, years=[int(ano.value)], ufs=[uf.value], months=[int(mes.value)]
    )
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
    mo.vstack(
        [
            mo.md(
                "## A4 · Conferir\n\n"
                f"O relatório informou **{relatorio.rows:,} linhas novas**. O SIA é "
                "publicado num único diretório, então `outdated` não se aplica."
            ),
            mo.ui.table(_desta_execucao, selection=None, label="publications(run_id=...)"),
            mo.ui.table(_conferencia, selection=None, label="Linhas no lake x publicadas"),
            mo.md(f"Snapshot `{snapshot_id}`"),
        ]
    )
    return publicacoes, snapshot_id


@app.cell
def _(escopos, mo, odb, plano, snapshot_id):
    _parametros = [escopos[0].uf, escopos[0].ano, escopos[0].mes]
    consultas = {
        "apac_por_procedimento_principal": {
            "sql": """
                SELECT trim(CAST(ap_pripal AS VARCHAR)) AS procedimento_principal,
                       count(*) AS apac,
                       round(sum(TRY_CAST(ap_vl_ap AS DOUBLE)), 2) AS valor_aprovado
                FROM lake.sia_apac_medicamentos WHERE uf = ? AND ano = ? AND mes = ?
                GROUP BY ALL ORDER BY apac DESC
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
                "## A5 · Analisar\n\n"
                f"Registros de APAC por procedimento principal e valor aprovado, sobre o "
                f"snapshot `{snapshot_id}`. Não são doses nem pacientes únicos."
            ),
            mo.ui.table(resultados["apac_por_procedimento_principal"], selection=None),
            mo.accordion(
                {
                    "SQL": mo.md(
                        f"```sql\n{consultas['apac_por_procedimento_principal']['sql']}\n```"
                    )
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
            mo.md(f"## A6 · Guardar\n\nResultados e `proveniencia.json` gravados em `{pasta}`."),
            mo.download(
                (pasta / "apac_por_procedimento_principal.csv").read_bytes(),
                filename="sia_apac_medicamentos-apac_por_procedimento_principal.csv",
                label="CSV",
            ),
            mo.download(
                (pasta / "proveniencia.json").read_bytes(),
                filename="sia_apac_medicamentos-proveniencia.json",
                label="proveniencia.json",
            ),
        ]
    )
    return


@app.cell
def _(mo):
    codigo_uf = mo.ui.text(value="14", label="Código IBGE da UF")
    data_estoque = mo.ui.text(value="", label="Data da posição AAAA-MM-DD (opcional)")
    consultar_estoque = mo.ui.run_button(label="Consultar uma página (até 20 registros)")
    mo.vstack(
        [
            mo.md(
                "## B · Estoque BNAFAR/Hórus\n\n"
                "Uma página da API pública de **posição de estoque**. Não publica no lake. "
                "Uma página vazia não demonstra ausência de estoque, e uma página curta "
                "não demonstra completude."
            ),
            mo.hstack([codigo_uf, data_estoque]),
            consultar_estoque,
        ]
    )
    return codigo_uf, consultar_estoque, data_estoque


@app.cell
async def _(
    asyncio,
    codigo_uf,
    consultar_estoque,
    data_estoque,
    executar,
    fetch_stock_page,
    mo,
    data_root,
    write_json,
    uuid4,
):
    mo.stop(
        not (executar or consultar_estoque.value), mo.md("A consulta começa pelo botão acima.")
    )
    _filtros = {"codigo_uf": codigo_uf.value.strip()}
    if data_estoque.value.strip():
        _filtros["data_posicao_estoque"] = data_estoque.value.strip()
    _pagina = await asyncio.to_thread(fetch_stock_page, filters=_filtros, limit=20)
    _pasta = data_root() / "estoque" / uuid4().hex
    _pasta.mkdir(parents=True)
    (_pasta / "resposta.json").write_bytes(_pagina.raw)
    write_json(_pasta / "proveniencia.json", _pagina.provenance())
    mo.vstack(
        [
            mo.md(f"Observação salva em `{_pasta}`. SHA-256 da resposta: `{_pagina.sha256}`."),
            mo.ui.table(_pagina.records, selection=None),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## C · O que não existe publicamente

    A investigação de 2026-09-12
    ([relatório](https://github.com/raphaelfh/omnisus-db/blob/main/reports/2026-09-12-sinan-e-dispensacao.md),
    Parte 2) não encontrou **nenhuma fonte pública de eventos de dispensação**: a
    dispensação enviada à BNAFAR e à RNDS tem envio ou acesso autenticado. Estoque,
    entrega a DSEI e indicadores agregados não substituem dispensação. Para pesquisar
    dispensação, o caminho é uma extração fornecida pelo gestor.
    """)
    return


if __name__ == "__main__":
    app.run()

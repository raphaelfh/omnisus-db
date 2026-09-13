"""IBGE · população: a edição que serve de denominador, com proveniência."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="IBGE · população")


@app.cell
def _():
    import asyncio
    from dataclasses import asdict

    import marimo as mo
    from _comum import (
        executar_sem_botoes,
        fixar_plano,
        registrar_proveniencia,
        salvar_json,
        target_padrao,
    )

    import omnisus_db as odb
    from omnisus_db.sources.ibge.products import CENSUS_YEARS, ESTIMATE_UNAVAILABLE_YEARS
    from omnisus_db.transforms.dictionaries import load_dicionario

    executar = executar_sem_botoes(mo.cli_args())
    return (
        CENSUS_YEARS,
        ESTIMATE_UNAVAILABLE_YEARS,
        asdict,
        asyncio,
        executar,
        fixar_plano,
        load_dicionario,
        mo,
        odb,
        registrar_proveniencia,
        salvar_json,
        target_padrao,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # IBGE · população

    População municipal publicada pelo IBGE, importada de uma **edição explícita**:
    censo ou estimativa, e um ano. Este notebook percorre as seis etapas do
    [guia do pesquisador](https://raphaelfh.github.io/omnisus-db/pesquisa/) com o
    **censo de 2022** e, se o SIM estiver no mesmo lake, calcula óbitos por 100 mil.

    **Abrir este notebook não baixa nem grava nada.** Cada etapa com rede ou escrita
    começa por um botão.

    Censo e estimativa têm datas de referência diferentes. Leia o
    [perfil da população IBGE](https://raphaelfh.github.io/omnisus-db/sources/ibge_populacao/)
    e a página [Indicadores](https://raphaelfh.github.io/omnisus-db/pesquisa/indicadores/).
    """)
    return


@app.cell
def _(load_dicionario, mo):
    _dicionario = load_dicionario("ibge_populacao")
    mo.vstack(
        [
            mo.md("## 1 · O que a base registra\n\nColunas da visão `ibge_populacao`."),
            mo.ui.table(
                [
                    {"campo": f["name"], "tipo": f["type"], "rótulo": f.get("label", "")}
                    for f in _dicionario.fields
                ],
                selection=None,
            ),
        ]
    )
    return


@app.cell
def _(CENSUS_YEARS, ESTIMATE_UNAVAILABLE_YEARS, mo):
    mo.vstack(
        [
            mo.md(
                "## 2 · Descobrir\n\n"
                "Não há inventário de arquivos: a biblioteca aceita edições conhecidas. "
                "Esta tabela vem do pacote, sem rede."
            ),
            mo.ui.table(
                [
                    {"produto": "census", "anos_aceitos": ", ".join(map(str, CENSUS_YEARS))},
                    {
                        "produto": "estimate",
                        "anos_recusados": ", ".join(map(str, ESTIMATE_UNAVAILABLE_YEARS)),
                    },
                ],
                selection=None,
            ),
            mo.md(
                "Uma estimativa só é aceita na edição mais recente do agregado; anos "
                "recusados não têm universo territorial verificado."
            ),
        ]
    )
    return


@app.cell
def _(mo, target_padrao):
    produto = mo.ui.dropdown(["census", "estimate"], value="census", label="Produto")
    ano = mo.ui.number(start=2000, stop=2100, step=1, value=2022, label="Ano da edição")
    codigo_uf = mo.ui.text(value="14", label="Código IBGE da UF para a análise (14 = RR)")
    target = mo.ui.text(value=target_padrao(), label="Lake", full_width=True)
    fixar = mo.ui.run_button(label="Fixar o plano")
    mo.vstack(
        [
            mo.md(
                "## 3 · Planejar e importar\n\n"
                "Use o mesmo lake do SIM para poder calcular taxas. Uma edição já "
                "importada não é importada de novo: a visão `ibge_populacao` falha "
                "quando um município e ano têm duas publicações. O código da UF "
                "também entra no plano: trocá-lo depois de fixado não sobrescreve a "
                "execução, é preciso fixar um novo plano."
            ),
            mo.hstack([produto, ano]),
            codigo_uf,
            target,
            fixar,
        ]
    )
    return ano, codigo_uf, fixar, produto, target


@app.cell
def _(ano, codigo_uf, executar, fixar, fixar_plano, mo, produto, target):
    mo.stop(not (executar or fixar.value), mo.md("Fixe o plano para continuar."))
    plano, pasta = fixar_plano(
        target.value,
        dataset="ibge_populacao",
        product=produto.value,
        ano=int(ano.value),
        codigo_uf=codigo_uf.value.strip(),
    )
    importar = mo.ui.run_button(label="Baixar e publicar esta edição")
    mo.vstack([mo.md(f"Plano gravado em `{pasta / 'plano.json'}`."), mo.json(plano), importar])
    return importar, pasta, plano


@app.cell
async def _(asdict, asyncio, executar, importar, mo, odb, pasta, plano, salvar_json):
    mo.stop(not (executar or importar.value), mo.md("O download só começa pelo botão acima."))
    _sql = (
        "SELECT publication_id, product, ano, sha256, url, collected_at "
        "FROM lake.ibge_population_manifest WHERE product = ? AND ano = ?"
    )
    try:
        with odb.LakeReader(plano["target"]) as _leitor:
            _existentes = (
                _leitor.connect().execute(_sql, [plano["product"], plano["ano"]]).pl().to_dicts()
                if "ibge_population_manifest" in _leitor.tables()
                else []
            )
    except odb.CatalogAttachError:
        _existentes = []  # o lake ainda não existe
    if _existentes:
        importadas = []
    else:
        importadas = await asyncio.to_thread(
            odb.import_ibge_populacao,
            years=[plano["ano"]],
            product=plano["product"],
            target=plano["target"],
        )
    salvar_json(
        pasta / "resultado.json",
        {"ja_publicadas": _existentes, "importadas": [asdict(r) for r in importadas]},
    )
    mo.vstack(
        [
            mo.md(
                "Edição já estava no lake; nada foi importado."
                if _existentes
                else f"Importadas **{sum(r.rows for r in importadas):,} linhas**."
            ),
            mo.ui.table(_existentes or [asdict(r) for r in importadas], selection=None),
        ]
    )
    return (importadas,)


@app.cell
def _(importadas, mo, odb, plano):
    with odb.LakeReader(plano["target"]) as _leitor:
        publicacoes = (
            _leitor.connect()
            .execute(
                "SELECT * EXCLUDE (evidence_json) FROM lake.ibge_population_manifest "
                "WHERE product = ? AND ano = ?",
                [plano["product"], plano["ano"]],
            )
            .pl()
            .to_dicts()
        )
        _resumo = (
            _leitor.connect()
            .execute(
                "SELECT count(*) AS municipios, sum(populacao) AS populacao_total "
                "FROM lake.ibge_populacao WHERE ano = ?",
                [plano["ano"]],
            )
            .pl()
        )
        snapshot_id = _leitor.snapshots()[-1]["snapshot_id"]
    mo.vstack(
        [
            mo.md(
                "## 4 · Conferir\n\n"
                f"Esta execução importou {len(importadas)} edição(ões). O manifesto guarda "
                "URL, SHA-256 e data de coleta de cada publicação; a contagem abaixo lê a "
                "visão, que falharia se houvesse publicações ambíguas."
            ),
            mo.ui.table(publicacoes, selection=None, label="ibge_population_manifest"),
            mo.ui.table(_resumo, selection=None),
            mo.md(f"Snapshot `{snapshot_id}`"),
        ]
    )
    return publicacoes, snapshot_id


@app.cell
def _(mo, odb, plano, snapshot_id):
    _ano, _uf = plano["ano"], plano["codigo_uf"]
    _consultas = {
        "populacao_por_municipio": (
            "SELECT codigo_ibge, populacao FROM lake.ibge_populacao "
            "WHERE ano = ? AND left(codigo_ibge, 2) = ? ORDER BY populacao DESC",
            [_ano, _uf],
        ),
        "digitos_codigo_ibge": (
            "SELECT length(codigo_ibge) AS digitos, count(*) AS municipios "
            "FROM lake.ibge_populacao WHERE ano = ? GROUP BY ALL",
            [_ano],
        ),
    }
    with odb.LakeReader(plano["target"], snapshot_id=snapshot_id) as _leitor:
        _tem_sim = "sim_obitos" in _leitor.tables()
        if _tem_sim:
            _consultas["digitos_codmunres_sim"] = (
                "SELECT length(trim(CAST(codmunres AS VARCHAR))) AS digitos, count(*) AS obitos "
                "FROM lake.sim_obitos WHERE ano = ? GROUP BY ALL",
                [_ano],
            )
            _consultas["obitos_por_100_mil"] = (
                """
                WITH obitos AS (
                    SELECT left(trim(CAST(codmunres AS VARCHAR)), 6) AS municipio,
                           count(*) AS obitos
                    FROM lake.sim_obitos WHERE ano = ? GROUP BY ALL
                ), populacao AS (
                    SELECT left(codigo_ibge, 6) AS municipio, populacao
                    FROM lake.ibge_populacao WHERE ano = ? AND left(codigo_ibge, 2) = ?
                )
                SELECT municipio, obitos, populacao,
                       round(100000.0 * obitos / populacao, 1) AS obitos_por_100_mil
                FROM populacao JOIN obitos USING (municipio)
                ORDER BY municipio
                """,
                [_ano, _ano, _uf],
            )
        resultados = {
            nome: _leitor.connect().execute(sql, parametros).pl()
            for nome, (sql, parametros) in _consultas.items()
        }
    consultas = {
        nome: {"sql": sql, "parametros": parametros}
        for nome, (sql, parametros) in _consultas.items()
    }
    _texto = (
        "A taxa junta os municípios pelos **6 primeiros dígitos**: confira nas tabelas de "
        "dígitos que os dois lados têm o formato esperado antes de usar o resultado. "
        "Óbitos entram pelo município de residência (`codmunres`) e só os arquivos do SIM "
        "presentes no lake são contados; veja o perfil do SIM sobre como os arquivos "
        "são organizados."
        if _tem_sim
        else f"`sim_obitos` não está neste lake. Importe SIM {_ano} no notebook "
        "`bases/sim_obitos.py`, com o mesmo lake, para calcular óbitos por 100 mil."
    )
    mo.vstack(
        [
            mo.md(f"## 5 · Analisar\n\nConsultas sobre o snapshot `{snapshot_id}`. {_texto}"),
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
                        filename=f"ibge_populacao-{nome}.csv",
                        label=f"CSV · {nome}",
                    )
                    for nome in resultados
                ],
                wrap=True,
            ),
            mo.download(
                (pasta / "proveniencia.json").read_bytes(),
                filename="ibge_populacao-proveniencia.json",
                label="proveniencia.json",
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()

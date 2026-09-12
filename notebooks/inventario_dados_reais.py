"""Inventário DATASUS → seleção de arquivos reais → DuckLake → SQL e exportação."""
# Expressões finais são saídas visuais; marimo injeta as classes importadas.
# ruff: noqa: B018, N803

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="full", app_title="DATASUS · inventário e dados reais")


@app.cell
def _():
    import asyncio
    import json
    from datetime import UTC, datetime
    from pathlib import Path
    from uuid import uuid4

    import marimo as mo
    import polars as pl

    import omnisus_db as odb
    from omnisus_db.sources.datasus_ftp.datasets import REGISTRY
    from omnisus_db.sources.datasus_ftp.filenames import decode

    return REGISTRY, UTC, Path, asyncio, datetime, decode, json, mo, odb, pl, uuid4


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Inventário e download real do DATASUS

    **1. Consulte o servidor → 2. filtre e escolha os arquivos → 3. baixe e explore.**

    Todos os registros vêm do FTP público do Ministério da Saúde. O catálogo abaixo
    descreve as bases suportadas pela biblioteca; a disponibilidade só é confirmada
    pela consulta ao servidor. O exemplo inicial é **SIM · Roraima · 2023**.
    A seleção permite até três arquivos, com limite total de 25 MiB comprimidos.
    Não há dados sintéticos nem substituição por exemplos quando a rede falha.
    """)
    return


@app.cell(hide_code=True)
def _(REGISTRY, mo):
    mo.accordion(
        {
            "Bases suportadas (catálogo local; não comprova disponibilidade)": mo.ui.table(
                [
                    {"base": d.name, "periodicidade": d.cadence, "diretorio_ftp": d.ftp_dir}
                    for d in REGISTRY.values()
                ],
                selection=None,
            )
        }
    )
    return


@app.cell
def _(mo):
    # Permite executar exatamente o mesmo fluxo real e exportar os resultados sem UI.
    executar = str(mo.cli_args().get("executar", "false")).lower() == "true"
    return (executar,)


@app.cell
def _(REGISTRY, mo):
    base = mo.ui.dropdown(list(REGISTRY), value="sim_obitos", label="Base DATASUS")
    base
    return (base,)


@app.cell
def _(base, mo):
    consultar = mo.ui.run_button(label=f"Consultar inventário atualizado · {base.value}")
    consultar
    return (consultar,)


@app.cell
async def _(REGISTRY, UTC, asyncio, base, consultar, datetime, decode, executar, mo, odb, pl):
    mo.stop(not (executar or consultar.value), mo.md("Clique em **Consultar inventário**."))
    dataset = REGISTRY[base.value]
    with mo.status.spinner(title="Consultando a listagem real do DATASUS…"):
        try:
            # browse retorna metadados reais; decode reconhece os arquivos da base.
            # refresh=True exige rede: uma listagem antiga nunca vira consulta atual.
            _entries = await asyncio.to_thread(odb.browse, dataset.ftp_dir, refresh=True)
        except (odb.FtpUnavailable, odb.FtpPathNotFound) as _error:
            if executar:
                raise
            mo.stop(True, mo.callout(f"Consulta falhou: {_error}", kind="danger"))
    consulta_utc = datetime.now(UTC).isoformat()
    _rows = []
    for _entry in _entries:
        _decoded = None if _entry.is_dir else decode(_entry.name)
        if _decoded is not None and _decoded[1] == dataset.name:
            _scope = _decoded[0]
            _rows.append(
                {
                    "arquivo": _entry.name,
                    "uf": _scope.uf,
                    "ano": _scope.ano,
                    "mes": _scope.mes,
                    "bytes": _entry.size_bytes,
                    "MiB": round(_entry.size_bytes / 1024**2, 3),
                    "modificado_servidor": _entry.modified.isoformat(),
                    "url": f"ftp://ftp.datasus.gov.br{_entry.path}",
                }
            )
    if executar and not _rows:
        raise RuntimeError("O servidor não listou arquivos reconhecidos para esta base.")
    mo.stop(not _rows, mo.callout("Nenhum arquivo reconhecido nesta listagem.", kind="warn"))
    inventario = pl.DataFrame(_rows, schema_overrides={"mes": pl.Int64}).sort(
        ["ano", "uf", "mes"], descending=[True, False, False]
    )
    mo.vstack(
        [
            mo.md(f"## 1 · Disponibilidade confirmada: {dataset.name}"),
            mo.md(
                f"**{inventario.height:,} arquivos** · **{inventario['uf'].n_unique()} códigos territoriais** · "
                f"**{inventario['ano'].min()} a {inventario['ano'].max()}** · consulta UTC: `{consulta_utc}`"
            ),
            mo.md(
                f"Diretório: `ftp://ftp.datasus.gov.br{dataset.ftp_dir}`. "
                "Datas de modificação são informadas pelo servidor sem fuso. "
                "BR identifica o arquivo nacional, quando presente. "
                "Arquivos listados podem ser revisados ou removidos posteriormente."
            ),
            mo.ui.table(
                inventario, selection=None, page_size=10, label="Inventário remoto completo"
            ),
        ]
    )
    return consulta_utc, dataset, inventario


@app.cell
def _(dataset, inventario, mo, odb):
    _ufs = (
        ["Nacional"]
        if dataset.geography == "national"
        else sorted(set(inventario["uf"].to_list()).intersection(odb.ALL_UFS))
    )
    mo.stop(not _ufs, mo.md("A listagem não contém arquivos estaduais para selecionar."))
    _anos = sorted(inventario["ano"].unique().to_list(), reverse=True)
    uf = mo.ui.dropdown(_ufs, value="RR" if "RR" in _ufs else _ufs[0], label="UF")
    ano = mo.ui.dropdown(_anos, value=2023 if 2023 in _anos else _anos[0], label="Ano")
    mo.vstack([mo.md("## 2 · Escolha uma seleção do inventário"), mo.hstack([uf, ano])])
    return ano, uf


@app.cell
def _(ano, dataset, inventario, mo, pl, uf):
    _territorio = (
        pl.col("uf").is_null() if dataset.geography == "national" else pl.col("uf") == uf.value
    )
    recorte = inventario.filter(_territorio & (pl.col("ano") == ano.value))
    mo.stop(
        recorte.is_empty(),
        mo.callout("Nenhum arquivo para esta combinação de UF e ano.", kind="warn"),
    )
    arquivos = mo.ui.multiselect(
        recorte["arquivo"].to_list(),
        value=recorte["arquivo"].head(1).to_list(),
        max_selections=3,
        label="Arquivos para baixar (até 3)",
    )
    mo.vstack([mo.ui.table(recorte, selection=None, page_size=12), arquivos])
    return arquivos, recorte


@app.cell
def _(arquivos, mo, pl, recorte):
    selecao = recorte.filter(pl.col("arquivo").is_in(arquivos.value))
    mo.stop(selecao.is_empty(), mo.md("Selecione ao menos um arquivo."))
    mo.stop(
        selecao.height > 3 or selecao["bytes"].sum() > 25 * 1024**2,
        mo.callout(
            "Selecione até 3 arquivos que somem no máximo 25 MiB comprimidos.", kind="warn"
        ),
    )
    baixar = mo.ui.run_button(label=f"Baixar {selecao.height} arquivo(s) e mostrar os dados")
    mo.vstack(
        [
            mo.md(
                f"**{selecao.height} arquivo(s)** · **{selecao['bytes'].sum() / 1024**2:.3f} MiB** "
                "comprimidos. A conversão para tabelas ocupa mais memória e disco."
            ),
            baixar,
        ]
    )
    return baixar, selecao


@app.cell
async def _(
    Path,
    UTC,
    asyncio,
    baixar,
    consulta_utc,
    dataset,
    datetime,
    executar,
    inventario,
    json,
    mo,
    odb,
    selecao,
    uuid4,
):
    mo.stop(not (executar or baixar.value), mo.md("O download começa ao clicar no botão acima."))
    # mo.notebook_location() funciona mesmo quando o processo parte de outro diretório.
    pasta = (
        Path(mo.notebook_location()).parent
        / "data/lake/inventario-real"
        / f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid4().hex[:8]}"
    ).resolve()
    pasta.mkdir(parents=True, exist_ok=False)
    target = f"ducklake:{pasta / 'dados.ducklake'}"
    inventario.write_csv(pasta / "inventario.csv")
    selecao.write_csv(pasta / "selecao.csv")
    _scopes = [
        odb.ScopeKey(uf=r["uf"], ano=r["ano"], mes=r["mes"]) for r in selecao.iter_rows(named=True)
    ]
    mo.output.append(mo.md(f"## 3 · Download e importação\n\nDestino: `{pasta}`"))
    _inicio = datetime.now(UTC).isoformat()
    abortado = False
    _unresolved = []
    with mo.status.spinner(title="Baixando DBC, convertendo e gravando no DuckLake…"):
        try:
            # O wrapper usa asyncio.run internamente; executá-lo em thread evita
            # conflito com o loop assíncrono do marimo. Um único escritor por lake.
            relatorio = await asyncio.to_thread(
                odb.import_dataset,
                dataset.name,
                scopes=_scopes,
                target=target,
                concurrency=1,
                batch_size=1,
            )
        except odb.ImportAbortedError as _error:
            relatorio = _error.report
            abortado = True
            _unresolved = [{"indice": i, "escopo": str(s)} for i, s in _error.unresolved]
    desfechos = [
        {
            "escopo": str(o.scope),
            "status": o.status,
            "linhas": o.result.rows if o.result else 0,
            "segundos": o.result.duration_seconds if o.result else None,
            "snapshot": o.result.snapshot_id if o.result else None,
            "motivo": o.reason,
        }
        for o in relatorio.outcomes
    ]
    manifesto = {
        "base": dataset.name,
        "consulta_utc": consulta_utc,
        "inicio_utc": _inicio,
        "fim_utc": datetime.now(UTC).isoformat(),
        "omnisus_db": odb.__version__,
        "target": target,
        "selecao": selecao.to_dicts(),
        "linhas": relatorio.rows,
        "abortado": abortado,
        "nao_resolvidos": _unresolved,
        "desfechos": desfechos,
    }
    (pasta / "execucao.json").write_text(json.dumps(manifesto, indent=2, ensure_ascii=False))
    mo.output.append(
        mo.vstack(
            [
                mo.md(
                    f"**{relatorio.rows:,} linhas confirmadas** · {len(relatorio.ok)} ok · "
                    f"{len(relatorio.skipped)} ausentes · {len(relatorio.failed)} falhas · aborto: {abortado}"
                ),
                mo.ui.table(desfechos, selection=None),
                mo.callout(
                    "Execução incompleta; confira os motivos e execucao.json antes de repetir."
                    if abortado or relatorio.failed or relatorio.skipped
                    else "Importação concluída.",
                    kind="warn"
                    if abortado or relatorio.failed or relatorio.skipped
                    else "success",
                ),
            ]
        )
    )
    # No modo de execução automática, falhas não geram uma exportação com aparência de sucesso.
    if executar and (abortado or relatorio.failed or relatorio.skipped):
        raise RuntimeError(f"Importação incompleta. Inspecione {pasta / 'execucao.json'}")
    return manifesto, pasta, relatorio, target


@app.cell
def _(dataset, mo, odb, pasta, relatorio, target):
    mo.stop(not relatorio.ok, mo.md("Nenhum escopo confirmado para consultar."))
    # O nome da tabela vem exclusivamente do registro de datasets da biblioteca.
    tabela_sql = f'lake."{dataset.name}"'
    with odb.Lake.local(target) as _lake:
        _conn = _lake.connect()
        total = _conn.sql(f"SELECT count(*) FROM {tabela_sql}").fetchone()[0]
        assert total == relatorio.rows, "A contagem persistida diverge do relatório de importação."
        amostra = _conn.sql(f"SELECT * FROM {tabela_sql} LIMIT 50").pl()
        esquema = _conn.sql(f"DESCRIBE {tabela_sql}").pl()
        _grupos = (
            "_source_ano"
            if dataset.geography == "national"
            else "uf, ano, mes"
            if dataset.monthly
            else "uf, ano"
        )
        resumo = _conn.sql(
            f"SELECT {_grupos}, count(*) AS registros FROM {tabela_sql} "
            f"GROUP BY {_grupos} ORDER BY {_grupos}"
        ).pl()
        for _ext, _opcoes in [("parquet", "FORMAT PARQUET"), ("csv", "FORMAT CSV, HEADER TRUE")]:
            _destino = str(pasta / f"{dataset.name}.{_ext}").replace("'", "''")
            _conn.execute(f"COPY {tabela_sql} TO '{_destino}' ({_opcoes})")
    mo.vstack(
        [
            mo.md(f"## 4 · Resultado real: {total:,} registros e {amostra.width} colunas"),
            mo.ui.table(
                resumo, selection=None, label="Contagem por escopo (SQL no lake reaberto)"
            ),
            mo.md(
                "### Primeiras 50 linhas\nAmostra de inspeção, sem ordenação ou representatividade estatística. "
                "As exportações abaixo contêm **todos** os registros importados."
            ),
            mo.ui.table(
                amostra, selection=None, page_size=10, max_columns=None, label="Registros reais"
            ),
            mo.accordion({"Esquema da tabela": mo.ui.table(esquema, selection=None)}),
            mo.hstack(
                [
                    mo.download(
                        data=lambda: (pasta / f"{dataset.name}.csv").read_bytes(),
                        filename=f"{dataset.name}.csv",
                        label="Baixar CSV completo",
                    ),
                    mo.download(
                        data=lambda: (pasta / f"{dataset.name}.parquet").read_bytes(),
                        filename=f"{dataset.name}.parquet",
                        label="Baixar Parquet completo",
                    ),
                ]
            ),
            mo.md(
                f"Arquivos salvos em `{pasta}`. O DBC é convertido pelo importador; "
                "o resultado durável fica no DuckLake e nas exportações."
            ),
        ]
    )
    return amostra, esquema, resumo, total


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    Cada clique cria um lake novo para evitar duplicação por append. Aguarde a
    importação terminar antes de repetir: interromper a célula pode deixar a thread
    trabalhando. Inventário vazio, arquivo ausente e erro de download são situações
    distintas e aparecem separadamente.

    Fonte: [FTP público DATASUS](https://datasus.saude.gov.br/transferencia-de-arquivos/).
    Interação: [botões de execução do marimo](https://docs.marimo.io/api/inputs/run_button/).
    Consulte também `docs/guides/inventory.md` para `odb.available()` (escopos
    importáveis) e `odb.browse()` (arquivos e metadados, usado neste notebook).
    """)
    return


if __name__ == "__main__":
    app.run()

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

"""Inventário DATASUS → seleção de arquivos reais → DuckLake → SQL e exportação."""

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
    from omnisus_db.sources.datasus_ftp.filenames import decode_for

    return REGISTRY, UTC, Path, asyncio, datetime, decode_for, json, mo, odb, pl, uuid4


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Inventário e download real do DATASUS

    [![Open in molab](https://molab.marimo.io/molab-shield.svg)](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/explorar/inventario_dados_reais.py)

    **1. Consulte o servidor → 2. filtre os arquivos → 3. baixe e explore.**

    Todos os registros vêm do FTP público do Ministério da Saúde. O exemplo inicial
    é **SIM · Roraima · 2023**. A seleção permite até três arquivos, com limite
    total de 25 MiB comprimidos.

    ## Como executar

    ```bash
    uv sync --locked --extra notebooks
    uv run --locked --extra notebooks marimo edit notebooks/explorar/inventario_dados_reais.py
    ```

    Cada tentativa grava em `data/lake/inventario-real/<data-uuid>/`.

    ```bash
    uv run --locked --extra notebooks marimo export html notebooks/explorar/inventario_dados_reais.py -o /tmp/inventario-dados-reais.html -- --executar true
    ```

    Esse comando **acessa o DATASUS e baixa dados**. Sem `--executar true` (e com
    `EXECUTAR = False`), a abertura não consulta o servidor.
    """)
    return


@app.cell
def _(REGISTRY, pl):
    catalogo = pl.DataFrame(
        [
            {"base": d.name, "periodicidade": d.cadence, "diretorio_ftp": d.ftp_dir}
            for d in REGISTRY.values()
        ]
    )
    catalogo
    return


@app.cell
def _(REGISTRY, mo):
    BASE = "sim_obitos"
    UF = "RR"
    ANO = 2023
    ARQUIVOS = None
    EXECUTAR = False
    executar = EXECUTAR or str(mo.cli_args().get("executar", "false")).lower() == "true"
    assert BASE in REGISTRY, f"base desconhecida: {BASE}"
    (BASE, UF, ANO, ARQUIVOS, executar)
    return ANO, ARQUIVOS, BASE, UF, executar


@app.cell
async def _(REGISTRY, UTC, asyncio, BASE, datetime, decode_for, executar, mo, odb, pl):
    mo.stop(
        not executar,
        mo.md("Para consultar o inventário, defina `EXECUTAR = True` ou `-- --executar true`."),
    )
    dataset = REGISTRY[BASE]
    try:
        _entries = await asyncio.to_thread(odb.browse, dataset.ftp_dir, refresh=True)
    except (odb.FtpUnavailable, odb.FtpPathNotFound):
        raise
    consulta_utc = datetime.now(UTC).isoformat()
    _rows = []
    for _entry in _entries:
        _scope = None if _entry.is_dir else decode_for(dataset, _entry.name)
        if _scope is not None:
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
    mo.stop(not _rows, mo.md("Nenhum arquivo reconhecido nesta listagem."))
    inventario = pl.DataFrame(_rows, schema_overrides={"mes": pl.Int64}).sort(
        ["ano", "uf", "mes"], descending=[True, False, False]
    )
    inventario
    return consulta_utc, dataset, inventario


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2 · Recorte do inventário
    """)
    return


@app.cell
def _(ANO, ARQUIVOS, UF, dataset, inventario, mo, pl):
    _territorio = pl.col("uf").is_null() if dataset.geography == "national" else pl.col("uf") == UF
    recorte = inventario.filter(_territorio & (pl.col("ano") == ANO))
    mo.stop(recorte.is_empty(), mo.md("Nenhum arquivo para esta combinação de UF e ano."))
    nomes = ARQUIVOS if ARQUIVOS else recorte["arquivo"].head(1).to_list()
    selecao = recorte.filter(pl.col("arquivo").is_in(nomes))
    mo.stop(selecao.is_empty(), mo.md("Nenhum arquivo selecionado."))
    mo.stop(
        selecao.height > 3 or selecao["bytes"].sum() > 25 * 1024**2,
        mo.md("Selecione até 3 arquivos que somem no máximo 25 MiB comprimidos."),
    )
    selecao
    return (selecao,)


@app.cell
async def _(
    Path,
    UTC,
    asyncio,
    consulta_utc,
    dataset,
    datetime,
    executar,
    inventario,
    json,
    mo,
    odb,
    pl,
    selecao,
    uuid4,
):
    mo.stop(
        not executar,
        mo.md("A importação segue `EXECUTAR` na célula de parâmetros."),
    )
    pasta = (
        Path(mo.notebook_location()).parents[1]
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
    _inicio = datetime.now(UTC).isoformat()
    abortado = False
    _unresolved = []
    try:
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
    desfechos = pl.DataFrame(
        [
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
    )
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
        "desfechos": desfechos.to_dicts(),
    }
    (pasta / "execucao.json").write_text(json.dumps(manifesto, indent=2, ensure_ascii=False))
    if executar and (abortado or relatorio.failed or relatorio.skipped):
        raise RuntimeError(f"Importação incompleta. Inspecione {pasta / 'execucao.json'}")
    desfechos
    return manifesto, pasta, relatorio, target


@app.cell
def _(dataset, mo, odb, pasta, relatorio, target):
    mo.stop(not relatorio.ok, mo.md("Nenhum escopo confirmado para consultar."))
    tabela_sql = f'lake."{dataset.name}"'
    with odb.LakeReader(target) as _leitor:
        _conn = _leitor.connect()
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
    {"total": total, "resumo": resumo, "amostra": amostra, "esquema": esquema, "pasta": str(pasta)}
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    Cada execução cria um lake novo para evitar duplicação por append. Aguarde a
    importação terminar antes de repetir.

    Fonte: [FTP público DATASUS](https://datasus.saude.gov.br/transferencia-de-arquivos/).
    Consulte também `docs/guides/inventory.md` para `odb.available()` e `odb.browse()`.
    """)
    return


if __name__ == "__main__":
    app.run()

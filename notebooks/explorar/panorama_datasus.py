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

"""Learn all 18 DATASUS portal categories with a persisted, real sample archive."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="full", app_title="DATASUS · panorama das 18 categorias")


@app.cell
def _():
    import asyncio
    import json
    from datetime import UTC, datetime
    from pathlib import Path
    from uuid import uuid4

    import marimo as mo
    import polars as pl

    project_root = Path(__file__).resolve().parents[2]
    from _acervo.catalogo import SOURCES
    from _acervo.coleta import collect
    from _acervo.relatorio import maps, write_report

    archive_root = project_root / "data/lake/panorama-datasus"
    return (
        Path,
        SOURCES,
        UTC,
        archive_root,
        asyncio,
        collect,
        datetime,
        json,
        maps,
        mo,
        pl,
        uuid4,
        write_report,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Conhecer o DATASUS com dados reais

    [![Open in molab](https://molab.marimo.io/molab-shield.svg)](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/explorar/panorama_datasus.py)

    **18 categorias → arquivos originais → amostras de tabelas → mapa de colunas.**

    Este notebook reutiliza a última coleta local ao abrir. Ponha `PREPARAR = True`
    (ou `-- --preparar true`) para uma nova coleta a partir do portal e do FTP.

    Uma amostra por categoria permite estudar a estrutura; **não cobre todos os
    subtipos, agravos, períodos ou UFs**. TABWIN é um aplicativo: inspecionamos
    seus mapas, documentos e componentes sem executar programas. Bases antigas
    usam arquivos históricos, com os nomes e as datas preservados na proveniência.

    ## Como executar

    ```bash
    uv sync --locked --extra notebooks
    uv run --locked --extra notebooks marimo edit notebooks/explorar/panorama_datasus.py
    ```

    Cada coleta grava em `data/lake/panorama-datasus/<execucao>/`. O ponteiro
    `latest.json` só é publicado quando a tentativa termina, mesmo com falhas
    parciais.

    ```bash
    uv run --locked --extra notebooks marimo export html notebooks/explorar/panorama_datasus.py -o /tmp/panorama-datasus.html

    uv run --locked --extra notebooks marimo export html notebooks/explorar/panorama_datasus.py -o /tmp/panorama-datasus.html -- --preparar true
    ```
    """)
    return


@app.cell
def _(SOURCES, mo):
    CATEGORIAS = [s.key for s in SOURCES]
    LIMITE_LINHAS = 200
    CATEGORIA = "SIM"
    PREPARAR = False
    preparar = PREPARAR or str(mo.cli_args().get("preparar", "false")).lower() == "true"
    (CATEGORIAS, LIMITE_LINHAS, CATEGORIA, preparar)
    return CATEGORIA, CATEGORIAS, LIMITE_LINHAS, preparar


@app.cell
async def _(
    Path,
    UTC,
    archive_root,
    asyncio,
    CATEGORIAS,
    LIMITE_LINHAS,
    collect,
    datetime,
    json,
    mo,
    preparar,
    uuid4,
    write_report,
):
    if preparar:
        run_dir = archive_root / f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid4().hex[:8]}"
        manifesto = await asyncio.to_thread(
            collect, run_dir, list(CATEGORIAS), limit=int(LIMITE_LINHAS)
        )
        await asyncio.to_thread(write_report, manifesto, run_dir / "mapa")
        if any(s["status"] == "falha" for s in manifesto["fontes"]):
            raise RuntimeError(f"Coleta com falhas. Veja {run_dir / 'manifesto.json'}")
    else:
        _latest = archive_root / "latest.json"
        mo.stop(
            not _latest.exists(),
            mo.md("Ainda não há acervo local. Defina `PREPARAR = True` ou `-- --preparar true`."),
        )
        _manifest_path = Path(json.loads(_latest.read_text(encoding="utf-8"))["manifesto"])
        manifesto = json.loads(_manifest_path.read_text(encoding="utf-8"))
        run_dir = _manifest_path.parent
    manifesto["inicio_utc"], str(run_dir)
    return manifesto, run_dir


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1 · Visão geral
    """)
    return


@app.cell
def _(manifesto, maps, pl):
    fontes, tabelas, colunas, _membros = maps(manifesto)
    mapa_fontes = pl.DataFrame(fontes, infer_schema_length=None)
    mapa_tabelas = pl.DataFrame(tabelas, infer_schema_length=None) if tabelas else pl.DataFrame()
    mapa_colunas = pl.DataFrame(colunas, infer_schema_length=None) if colunas else pl.DataFrame()
    mapa_fontes.select(
        "categoria",
        "natureza",
        "subtipo_amostrado",
        "status",
        "arquivo",
        "tabelas",
        "colunas",
        "linhas_amostradas",
        "bytes",
    )
    return mapa_colunas, mapa_fontes, mapa_tabelas


@app.cell
def _(CATEGORIA, manifesto):
    fonte = next(s for s in manifesto["fontes"] if s["key"] == CATEGORIA)
    fonte
    return (fonte,)


@app.cell
def _(fonte, pl):
    membros = (
        pl.DataFrame(fonte["membros"], infer_schema_length=None)
        if fonte["membros"]
        else pl.DataFrame()
    )
    documentos = fonte["documentos"]
    membros
    return (documentos,)


@app.cell
def _(documentos):
    documentos
    return


@app.cell
def _(fonte, mo):
    mo.stop(
        not fonte["tabelas"],
        mo.md(
            "Esta categoria não possui tabelas amostradas nesta coleta. "
            "Para aplicativos, explore os membros e documentos acima."
        ),
    )
    detalhes = fonte["tabelas"][0]
    detalhes["membro"], detalhes["tabela"]
    return (detalhes,)


@app.cell
def _(detalhes, pl):
    amostra = pl.read_parquet(detalhes["amostra_parquet"])
    amostra
    return (amostra,)


@app.cell
def _(detalhes, pl):
    esquema = pl.DataFrame(detalhes["colunas"], infer_schema_length=None)
    esquema
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    Os valores permanecem em **texto bruto**, para conservar códigos e zeros à esquerda.
    O tipo físico original, a largura e as casas decimais aparecem no esquema.
    Nulos e valores distintos descrevem **só esta amostra**.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3 · Mapa completo do que foi obtido
    """)
    return


@app.cell
def _(mapa_fontes):
    mapa_fontes
    return


@app.cell
def _(mapa_tabelas):
    mapa_tabelas
    return


@app.cell
def _(mapa_colunas, run_dir):
    {"pasta_mapa": str(run_dir / "mapa"), "colunas": mapa_colunas}
    return


if __name__ == "__main__":
    app.run()

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

    Comece pela visão geral, escolha uma categoria e explore as tabelas, campos e
    registros reais. Este notebook reutiliza a última coleta local ao abrir.
    O botão abaixo prepara uma nova coleta a partir do portal e do FTP público.

    Uma amostra por categoria permite estudar a estrutura; **não cobre todos os
    subtipos, agravos, períodos ou UFs**. TABWIN é um aplicativo: inspecionamos
    seus mapas, documentos e componentes sem executar programas. Bases antigas
    usam arquivos históricos, com os nomes e as datas preservados na proveniência.

    ## Como executar

    ```bash
    uv sync --locked --extra notebooks
    uv run --locked --extra notebooks marimo edit notebooks/explorar/panorama_datasus.py
    ```

    Cada coleta grava em `data/lake/panorama-datasus/<execucao>/`: por categoria,
    consulta ao portal, inventário FTP, arquivo original, SHA-256, tentativas,
    amostras CSV/Parquet e descritores de colunas; além de `manifesto.json`
    (proveniência e estado final), `portal_transferencia.js` (cópia do seletor) e
    `mapa/` (relatório Markdown e mapas CSV/JSON). O ponteiro `latest.json` só é
    publicado quando a tentativa termina, mesmo com falhas parciais. Interromper a
    célula pode não encerrar imediatamente a thread de aquisição.

    ```bash
    # Exportar o acervo local já preparado (sem novos downloads)
    uv run --locked --extra notebooks marimo export html notebooks/explorar/panorama_datasus.py -o /tmp/panorama-datasus.html

    # Executar uma nova coleta real das 18 categorias e gerar o HTML
    uv run --locked --extra notebooks marimo export html notebooks/explorar/panorama_datasus.py -o /tmp/panorama-datasus.html -- --preparar true
    ```

    `--preparar true` é para execução automática, não para uma sessão interativa;
    falhas permanecem visíveis no manifesto e fazem a exportação terminar com erro.
    """)
    return


@app.cell
def _(SOURCES, mo):
    categorias = mo.ui.multiselect(
        [s.key for s in SOURCES],
        value=[s.key for s in SOURCES],
        label="Categorias para a próxima coleta",
        full_width=True,
    )
    tamanho = mo.ui.dropdown([50, 100, 200, 500], value=200, label="Máximo de linhas por tabela")
    mo.accordion(
        {
            "Preparar outra coleta": mo.vstack(
                [
                    categorias,
                    tamanho,
                    mo.md(
                        "Downloads completos limitados a 64 MiB por arquivo e 256 MiB por execução. "
                        "O ZIP pode conter várias tabelas; a amostra é extraída de cada uma. "
                        "A coleta é sequencial para limitar uso do servidor e memória."
                    ),
                ]
            )
        }
    )
    return categorias, tamanho


@app.cell
def _(categorias, mo, tamanho):
    download = mo.ui.run_button(
        label=f"Baixar amostras reais de {len(categorias.value)} categorias ({tamanho.value} linhas/tabela)",
        disabled=not categorias.value,
    )
    download
    return (download,)


@app.cell
async def _(
    Path,
    UTC,
    archive_root,
    asyncio,
    categorias,
    collect,
    datetime,
    download,
    json,
    mo,
    tamanho,
    uuid4,
    write_report,
):
    _automatico = str(mo.cli_args().get("preparar", "false")).lower() == "true"
    if _automatico or download.value:
        run_dir = archive_root / f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid4().hex[:8]}"
        mo.output.append(
            mo.md(f"Coleta em andamento: `{run_dir}`. Aguarde a conclusão antes de repetir.")
        )
        with mo.status.spinner(
            title="Consultando e baixando categorias; veja o progresso da célula…"
        ):
            manifesto = await asyncio.to_thread(
                collect, run_dir, list(categorias.value), limit=int(tamanho.value)
            )
            await asyncio.to_thread(write_report, manifesto, run_dir / "mapa")
        if _automatico and any(s["status"] == "falha" for s in manifesto["fontes"]):
            raise RuntimeError(f"Coleta com falhas. Veja {run_dir / 'manifesto.json'}")
    else:
        _latest = archive_root / "latest.json"
        mo.stop(
            not _latest.exists(),
            mo.callout("Ainda não há acervo local. Clique em Baixar amostras reais.", kind="info"),
        )
        _manifest_path = Path(json.loads(_latest.read_text(encoding="utf-8"))["manifesto"])
        manifesto = json.loads(_manifest_path.read_text(encoding="utf-8"))
        run_dir = _manifest_path.parent
    mo.output.append(
        mo.md(
            f"Coleta exibida: **{manifesto['inicio_utc']}** · "
            f"**{len(manifesto['fontes'])} categorias** · pasta `{run_dir}`. "
            "Alterar os controles acima só configura a próxima coleta."
        )
    )
    return manifesto, run_dir


@app.cell
def _(manifesto, maps, mo, pl):
    fontes, tabelas, colunas, _membros = maps(manifesto)
    mapa_fontes = pl.DataFrame(fontes, infer_schema_length=None)
    mapa_tabelas = pl.DataFrame(tabelas, infer_schema_length=None) if tabelas else pl.DataFrame()
    mapa_colunas = pl.DataFrame(colunas, infer_schema_length=None) if colunas else pl.DataFrame()
    _falhas = sum(s["status"] == "falha" for s in fontes)
    mo.vstack(
        [
            mo.md(
                f"## 1 · Visão geral\n\n**{len(tabelas)} tabelas** · "
                f"**{len(colunas)} ocorrências de colunas** · "
                f"**{sum(t['linhas_amostra'] for t in tabelas):,} linhas amostradas** · "
                f"**{_falhas} falhas**."
            ),
            mo.ui.table(
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
                ),
                selection=None,
                page_size=18,
                label="Cobertura efetivamente obtida",
            ),
            mo.callout(
                "O acervo contém falhas; os motivos aparecem na categoria correspondente."
                if _falhas
                else "Todas as categorias desta coleta têm amostra ou artefato real.",
                kind="warn" if _falhas else "success",
            ),
        ]
    )
    return mapa_colunas, mapa_fontes, mapa_tabelas


@app.cell
def _(manifesto, mo):
    categoria = mo.ui.dropdown(
        [s["key"] for s in manifesto["fontes"]],
        value="SIM"
        if any(s["key"] == "SIM" for s in manifesto["fontes"])
        else manifesto["fontes"][0]["key"],
        label="Categoria para estudar",
    )
    categoria
    return (categoria,)


@app.cell
def _(categoria, manifesto, mo):
    fonte = next(s for s in manifesto["fontes"] if s["key"] == categoria.value)
    _arquivo = fonte.get("arquivo", {})
    _origem = (
        mo.md(
            f"**Arquivo original:** [{_arquivo['arquivo']}]({_arquivo['url']})\n\n"
            f"**SHA-256:** `{_arquivo['sha256']}`\n\n"
            f"**Coleta UTC:** `{_arquivo['coleta_utc']}`"
        )
        if _arquivo
        else mo.md(fonte.get("erro", "Sem arquivo."))
    )
    mo.vstack(
        [
            mo.md(
                f"## 2 · {fonte['key']} — {fonte['title']}\n\n"
                f"**Pergunta de estudo:** {fonte['question']}\n\n**Limitação:** {fonte['limitation']}"
            ),
            _origem,
            mo.accordion(
                {"Proveniência e tentativas": mo.ui.table(fonte["tentativas"], selection=None)}
            ),
        ]
    )
    return (fonte,)


@app.cell
def _(fonte, mo):
    if fonte["membros"]:
        mo.output.append(
            mo.accordion(
                {
                    "Conteúdo do ZIP (programas não são executados)": mo.ui.table(
                        fonte["membros"], selection=None, page_size=10
                    )
                }
            )
        )
    if fonte["documentos"]:
        mo.output.append(
            mo.accordion(
                {
                    "Documentos textuais (trechos de até 6.000 bytes)": mo.ui.tabs(
                        {d["arquivo"]: mo.plain_text(d["trecho"]) for d in fonte["documentos"]}
                    )
                }
            )
        )
    mo.stop(
        not fonte["tabelas"],
        mo.md(
            "Esta categoria não possui tabelas amostradas nesta coleta. "
            "Para aplicativos, explore os membros e documentos acima."
        ),
    )
    tabela = mo.ui.dropdown(
        {t["membro"]: t["tabela"] for t in fonte["tabelas"]},
        value=fonte["tabelas"][0]["membro"],
        label="Tabela / membro do arquivo",
    )
    tabela
    return (tabela,)


@app.cell
def _(Path, fonte, mo, pl, tabela):
    detalhes = next(t for t in fonte["tabelas"] if t["tabela"] == tabela.value)
    amostra = pl.read_parquet(detalhes["amostra_parquet"])
    esquema = pl.DataFrame(detalhes["colunas"], infer_schema_length=None)
    mo.vstack(
        [
            mo.md(
                f"### {detalhes['membro']}\n\n**{detalhes['linhas_amostra']} linhas na amostra** · "
                f"**{detalhes['n_colunas']} colunas** · "
                f"**{detalhes['registros_ativos']} registros ativos no DBF completo**."
            ),
            mo.ui.tabs(
                {
                    "Registros reais": mo.ui.table(
                        amostra, selection=None, page_size=10, max_columns=None
                    ),
                    "Colunas e tipos": mo.ui.table(esquema, selection=None, page_size=15),
                    "Como interpretar": mo.md("""
                Os valores permanecem em **texto bruto**, para conservar códigos e zeros à esquerda.
                O tipo físico original, a largura e as casas decimais aparecem no esquema.
                `C` = caractere, `N` = numérico e `D` = data são descritores físicos DBF;
                eles não validam o significado de cada código.

                Nulos e valores distintos descrevem **só esta amostra**. As primeiras linhas
                são uma seleção de conveniência, sem representatividade estatística.
                Antes de contar pessoas, juntar bases ou calcular indicadores, identifique
                unidade de observação, chaves, período, cobertura e dicionário semântico.
            """),
                }
            ),
            mo.hstack(
                [
                    mo.download(
                        amostra.write_csv().encode("utf-8"),
                        filename=detalhes["tabela"] + ".csv",
                        label="Baixar amostra CSV",
                    ),
                    mo.download(
                        Path(detalhes["amostra_parquet"]).read_bytes(),
                        filename=detalhes["tabela"] + ".parquet",
                        label="Baixar amostra Parquet",
                    ),
                ]
            ),
        ]
    )
    return amostra, detalhes, esquema


@app.cell
def _(mapa_colunas, mapa_fontes, mapa_tabelas, mo, run_dir):
    _report = run_dir / "mapa/README.md"
    mo.vstack(
        [
            mo.md("## 3 · Mapa completo do que foi obtido"),
            mo.ui.tabs(
                {
                    "Categorias e arquivos": mo.ui.table(mapa_fontes, selection=None),
                    "Tabelas": mo.ui.table(mapa_tabelas, selection=None),
                    "Todas as colunas": mo.ui.table(mapa_colunas, selection=None),
                }
            ),
            mo.download(
                _report.read_bytes() if _report.exists() else b"",
                filename="mapa-datasus.md",
                label="Baixar relatório completo (Markdown)",
                disabled=not _report.exists(),
            ),
            mo.md(
                f"Relatório, CSVs e JSON: `{run_dir / 'mapa'}`. "
                "O mapa cobre todas as tabelas extraídas dos arquivos escolhidos. "
                "Outros arquivos do diretório têm apenas metadados de inventário, não esquemas inspecionados."
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()

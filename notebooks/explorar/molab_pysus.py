# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.16,<0.25",
#     "omnisus-db",
#     "polars>=1.44.2,<2.0",
#     "pysus",
# ]
#
# [tool.uv.sources]
# omnisus-db = { git = "https://github.com/raphaelfh/omnisus-db.git", rev = "5bdb25a45bea2056316dcd03c6a2c62a23a759cb" }
# ///

"""Laboratório marimo para exercitar a API do PySUS, sem importar omnisus-db."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="PySUS · laboratório")


@app.cell
def _():
    import asyncio
    import importlib.util
    import inspect
    import os
    from pathlib import Path

    import marimo as mo

    repositorio = Path(__file__).resolve().parents[2]
    cache = repositorio / "data/lake/pysus-lab"
    instalado = importlib.util.find_spec("pysus") is not None
    return asyncio, cache, inspect, instalado, mo, os


@app.cell(hide_code=True)
def _(instalado, mo):
    mo.md(f"""
    # PySUS · laboratório

    [![Open in molab](https://molab.marimo.io/molab-shield.svg)](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/explorar/molab_pysus.py)

    Notebook para **testar a biblioteca PySUS** (2.x): origens `ftp`, `dadosgov` e
    `saude`, listagem sem download, um recorte pequeno em DataFrame e o cliente
    `PySUS()`. Não usa a API do `omnisus-db`. Abrir o notebook não importa o PySUS,
    não baixa nada e não grava cache.

    PySUS no ambiente agora: **{"sim" if instalado else "não"}**.

    Edite os parâmetros na célula seguinte e ponha `EXECUTAR = True` (ou
    `-- --executar true`) para listar. `EXECUTAR_DOWNLOAD` e `EXECUTAR_CLIENTE`
    disparam o download e o cliente async.

    O extra `notebooks` deste repositório não instala o PySUS. No checkout:

    ```bash
    uv run --locked --extra notebooks --with pysus marimo edit notebooks/explorar/molab_pysus.py
    ```

    O cache vai para `data/lake/pysus-lab/` (`PYSUS_CACHEPATH`), não para `~/pysus`.
    Recorte inicial: **SINASC · Roraima · 2022**.
    """)
    return


@app.cell
def _(cache, instalado, mo, os):
    UF = "RR"
    ANO = 2022
    MES = 1
    AGRAVO = "deng"
    ORIGEM = "catalog"
    EXECUTAR = False
    EXECUTAR_DOWNLOAD = False
    EXECUTAR_CLIENTE = False
    executar = EXECUTAR or str(mo.cli_args().get("executar", "false")).lower() == "true"
    mo.stop(
        not instalado,
        mo.md(
            "Instale o PySUS (`uv run --with pysus`) e volte a abrir o notebook."
        ),
    )
    os.environ["PYSUS_CACHEPATH"] = str(cache)
    import pysus

    pysus.set_cache(cache)
    (UF, ANO, MES, AGRAVO, ORIGEM, executar, EXECUTAR_DOWNLOAD, EXECUTAR_CLIENTE, pysus)
    return (
        AGRAVO,
        ANO,
        EXECUTAR_CLIENTE,
        EXECUTAR_DOWNLOAD,
        MES,
        ORIGEM,
        UF,
        executar,
        pysus,
    )


@app.cell
def _(inspect, pysus):
    def _chamadas(modulo):
        return sorted(
            nome
            for nome, objeto in inspect.getmembers(modulo)
            if callable(objeto) and not nome.startswith("_")
        )

    resumo = {
        "versao": getattr(pysus, "__version__", None),
        "cache": str(pysus.CACHEPATH),
        "ftp": _chamadas(pysus.ftp),
        "dadosgov": _chamadas(pysus.dadosgov),
        "saude": _chamadas(pysus.saude),
    }
    resumo
    return


@app.cell
async def _(AGRAVO, ANO, MES, ORIGEM, UF, asyncio, executar, mo, pysus):
    mo.stop(
        not executar,
        mo.md(
            "Para listar arquivos remotos, defina `EXECUTAR = True` ou `-- --executar true`."
        ),
    )

    def _listar():
        linhas = []
        consultas = {
            "ftp.sinasc": lambda: pysus.ftp.sinasc(
                state=UF, year=int(ANO), download=False, source=ORIGEM
            ),
            "ftp.sim": lambda: pysus.ftp.sim(
                state=UF, year=int(ANO), download=False, source=ORIGEM
            ),
            "ftp.sih": lambda: pysus.ftp.sih(
                state=UF, year=int(ANO), month=int(MES), download=False, source=ORIGEM
            ),
            "ftp.sinan": lambda: pysus.ftp.sinan(
                disease=AGRAVO, year=int(ANO), download=False, source=ORIGEM
            ),
        }
        for nome, consulta in consultas.items():
            try:
                bag = consulta()
                n = len(bag) if hasattr(bag, "__len__") else None
                linhas.append(
                    {
                        "consulta": nome,
                        "ok": True,
                        "tipo": type(bag).__name__,
                        "n": n,
                        "repr": repr(bag)[:240],
                    }
                )
            except Exception as erro:
                linhas.append(
                    {
                        "consulta": nome,
                        "ok": False,
                        "tipo": type(erro).__name__,
                        "n": None,
                        "repr": str(erro)[:240],
                    }
                )
        return linhas

    listagem = await asyncio.to_thread(_listar)
    listagem
    return


@app.cell
async def _(ANO, EXECUTAR_DOWNLOAD, ORIGEM, UF, asyncio, mo, pysus):
    mo.stop(
        not EXECUTAR_DOWNLOAD,
        mo.md("Para baixar SINASC, defina `EXECUTAR_DOWNLOAD = True` na célula de parâmetros."),
    )

    def _baixar():
        return pysus.ftp.sinasc(
            state=UF, year=int(ANO), source=ORIGEM, as_dataframe=True
        )

    tabela = await asyncio.to_thread(_baixar)
    (type(tabela).__name__, getattr(tabela, "shape", None), tabela.head(8) if hasattr(tabela, "head") else tabela)
    return


@app.cell
async def _(ANO, EXECUTAR_CLIENTE, ORIGEM, UF, mo, pysus):
    mo.stop(
        not EXECUTAR_CLIENTE,
        mo.md("Para consultar o cliente `PySUS()`, defina `EXECUTAR_CLIENTE = True`."),
    )
    try:
        async with pysus.PySUS() as sessao:
            arquivos = await sessao.query(
                dataset="sinasc", state=UF, year=int(ANO), source=ORIGEM
            )
        amostra = arquivos[:8] if isinstance(arquivos, list) else arquivos
        saida = (type(arquivos).__name__, amostra)
    except Exception as erro:
        saida = f"{type(erro).__name__}: {erro}"
    saida
    return


if __name__ == "__main__":
    app.run()

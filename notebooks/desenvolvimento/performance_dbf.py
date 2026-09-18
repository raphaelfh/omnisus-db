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

"""Explore the measured Python/Rust DBF benchmarks without rerunning them."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="DBF · performance Python x Rust")


@app.cell
def _():
    import json
    from pathlib import Path

    import marimo as mo
    import polars as pl

    root = Path(__file__).resolve().parents[2]
    from _performance_dbf import (
        METRICS,
        PHASES,
        comparison_rows,
        measurement_rows,
        measurement_svg,
    )

    return METRICS, PHASES, comparison_rows, json, measurement_rows, measurement_svg, mo, pl, root


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Python x Rust: quanto muda na leitura DBF?

    [![Open in molab](https://molab.marimo.io/molab-shield.svg)](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/desenvolvimento/performance_dbf.py)

    **Explore tempo, memória e disco a partir de medições reais e reproduzíveis.**

    O leitor Rust substitui a conversão DBF → Arrow. Descompactação, staging
    Parquet e publicação continuam com as mesmas responsabilidades. Este notebook
    lê o relatório versionado; abrir ou alterar filtros não executa benchmarks.
    """)
    return


@app.cell
def _(comparison_rows, json, measurement_rows, mo, root):
    report_path = root / "reports/rust-dbf-performance.json"
    mo.stop(
        not report_path.exists(),
        mo.callout("Relatório de performance não encontrado.", kind="warn"),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    measurements = measurement_rows(report)
    comparisons = comparison_rows(measurements)
    return comparisons, measurements, report, report_path


@app.cell(hide_code=True)
def _(comparisons, measurements, mo, report):
    _amplified = [r for r in comparisons if r["amplified"] and r["phase"] == "dbf_to_arrow"]
    _dbc = [r for r in comparisons if r["phase"] == "dbc_to_parquet"]
    _aggregate = sum(r["python_ms"] for r in _dbc) / sum(r["rust_ms"] for r in _dbc)
    mo.md(f"""
    ## 1 · O que foi observado

    | Indicador | Resultado |
    | --- | ---: |
    | DBF → Arrow, corpora ampliados | {min(r["speedup"] for r in _amplified):.2f}x a {max(r["speedup"] for r in _amplified):.2f}x |
    | DBC → Parquet, agregado dos arquivos reais | {_aggregate:.2f}x |
    | Medições, sem aquecimento | {len(measurements)} |
    | Comparações corpus/etapa com equivalência confirmada | {len(comparisons)} |

    **Aceleração = mediana Python ÷ mediana Rust.** Acima de 1x, Rust foi mais
    rápido. O agregado DBC usa a razão entre as **somas das medianas**, sem
    incluir DBFs ampliados nem tempos de publicação.

    Ambiente medido: **{report["environment"]["cpu"]}** ·
    {report["environment"]["platform"]} · Python {report["environment"]["python"].split()[0]}.
    Coleta concluída em **{report["finished_at_utc"]}**.
    """)
    return


@app.cell
def _(PHASES, comparisons, measurement_svg, measurements, mo, pl, report):
    CORPUS = report["cases"][0]["corpus"]
    PHASE = report["cases"][0]["phases"][0]["phase"]
    METRIC = "time_ms"
    selected_case = next(c for c in report["cases"] if c["corpus"] == CORPUS)
    selected = [r for r in measurements if r["corpus"] == CORPUS and r["phase"] == PHASE]
    _comparison = next(r for r in comparisons if r["corpus"] == CORPUS and r["phase"] == PHASE)
    _unit = "ms" if METRIC == "time_ms" else "MiB"
    mo.Html(measurement_svg(selected, METRIC, PHASES[PHASE], _unit))
    {
        "corpus": CORPUS,
        "phase": PHASE,
        "speedup": _comparison["speedup"],
        "rss_ratio": _comparison["rss_ratio"],
        "rodadas": pl.DataFrame(selected).select(
            "backend", "round", "rows", "time_ms", "rss_mib", "disk_mib"
        ),
        "origem": selected_case["source_fixture"],
    }
    return


@app.cell
def _(PHASES, comparisons, pl):
    pl.DataFrame([{**r, "phase": PHASES[r["phase"]]} for r in comparisons])
    return


@app.cell(hide_code=True)
def _(mo, report):
    mo.md(f"""
    ## 4 · Como interpretar o teste

    - **{report["warmups"]} aquecimento e {report["rounds"]} medições** por backend/corpus/etapa,
      em processos novos e com ordem alternada. Aquecimentos não entram nos gráficos.
    - Lotes de **{report["batch_rows"]:,} registros**. Conteúdo ordenado e schema
      são conferidos **depois** da captura de tempo e RSS.
    - RSS é o pico do processo até a medição: inclui imports e preparação, não
      representa apenas a memória alocada pelo parser.
    - Disco temporário é amostrado a cada 5 ms: um **limite inferior** do pico.
      Zero pode significar ausência de arquivo ou um arquivo breve não observado.
    - Sem rede nos workers e sem limpeza do cache de páginas do sistema.
      Sete rodadas mostram dispersão local, não um intervalo de confiança.
    - Repetir amostras SIM/SIH não representa a diversidade de todo o DATASUS.

    Os gates locais definidos foram ≥2x em DBF → Arrow nos dois corpora ampliados,
    no máximo 10% de regressão agregada DBC → Parquet e 20% de regressão de RSS.
    O rollout também depende de testes de distribuição: **os números de performance
    não comprovam compatibilidade em outras plataformas**. Python continua como default.
    """)
    return


@app.cell
def _(json, report, report_path):
    {
        "arquivo": str(report_path),
        "packages": report["environment"]["packages"],
        "crates": report["environment"]["crates"],
        "source_sha256": report["environment"]["source_sha256"],
        "rust_wheel": report["rust_wheel"],
    }
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 5 · Repetir a medição

    Use o script existente, que mede em processos separados. Instale o wheel Rust
    release compatível com seu Python e plataforma; DuckLake precisa estar em cache.
    Troque `SEU_WHEEL.whl` pelo caminho real. Execute na raiz do repositório:

    ```bash
    uv run --no-sync python scripts/benchmark_resources.py --repeat 4 --rounds 7 --warmups 1 --rust-build-profile release --rust-wheel SEU_WHEEL.whl --output reports/rust-dbf-performance-local.json
    ```

    O arquivo de saída é diferente para preservar a evidência versionada. Para
    explorar outra medição, altere `report_path` na célula de leitura. Reexecutar
    apenas essa célula recarrega o JSON; os filtros não iniciam trabalho pesado.

    Consulte `reports/rust-dbf-validation.md` para testes de correção e instalação.
    Altere `CORPUS`, `PHASE` e `METRIC` na célula de comparação.
    """)
    return


if __name__ == "__main__":
    app.run()

"""Explore the measured Python/Rust DBF benchmarks without rerunning them."""
# marimo injects imports and displays final expressions.
# ruff: noqa: N803

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium", app_title="DBF · performance Python x Rust")


@app.cell
def _():
    import json
    import sys
    from pathlib import Path

    import marimo as mo
    import polars as pl

    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "notebooks"))
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
    report = json.loads(report_path.read_text())
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
def _(mo, report):
    _options = {
        f"{c['dataset'].upper()} · {'DBF ampliado ' + str(c['repeat']) + 'x' if c['amplified'] else 'arquivo original'} · {c['declared_records']:,} registros": c[
            "corpus"
        ]
        for c in report["cases"]
    }
    corpus = mo.ui.dropdown(
        _options,
        value=next(iter(_options)),
        label="Corpus",
        allow_select_none=False,
        full_width=True,
    )
    mo.vstack([mo.md("## 2 · Explore uma comparação"), corpus])
    return (corpus,)


@app.cell
def _(METRICS, PHASES, corpus, mo, report):
    selected_case = next(c for c in report["cases"] if c["corpus"] == corpus.value)
    phase = mo.ui.dropdown(
        {PHASES[p["phase"]]: p["phase"] for p in selected_case["phases"]},
        value=PHASES[selected_case["phases"][0]["phase"]],
        label="Etapa",
        allow_select_none=False,
        full_width=True,
    )
    metric = mo.ui.dropdown(METRICS, value="Tempo (ms)", label="Métrica", allow_select_none=False)
    mo.hstack([phase, metric], widths=[2, 1])
    return metric, phase, selected_case


@app.cell
def _(PHASES, comparisons, corpus, measurement_svg, measurements, metric, mo, phase, pl):
    selected = [
        r for r in measurements if r["corpus"] == corpus.value and r["phase"] == phase.value
    ]
    _comparison = next(
        r for r in comparisons if r["corpus"] == corpus.value and r["phase"] == phase.value
    )
    _unit = "ms" if metric.value == "time_ms" else "MiB"
    mo.vstack(
        [
            mo.Html(measurement_svg(selected, metric.value, PHASES[phase.value], _unit)),
            mo.md(
                f"**Aceleração: {_comparison['speedup']:.2f}x** · "
                f"**RSS Rust/Python: {_comparison['rss_ratio']:.3f}**. "
                "RSS abaixo de 1 indica menos memória. MiB = 1.048.576 bytes."
            ),
            mo.ui.table(
                pl.DataFrame(selected).select(
                    "backend", "round", "rows", "time_ms", "rss_mib", "disk_mib"
                ),
                selection=None,
                page_size=14,
                label="Rodadas medidas · exportação CSV disponível",
            ),
        ]
    )
    return (selected,)


@app.cell(hide_code=True)
def _(mo, selected_case):
    mo.md(f"""
    **Origem:** `{selected_case["source_fixture"]}` ·
    tipos DBF: **{", ".join(selected_case["field_types"])}** · encoding: **{selected_case["encoding"]}**.

    {"Este corpus repete os registros do DBF " + str(selected_case["repeat"]) + " vezes. Não é um DBC recomprimido; DBF → Parquet exclui descompactação." if selected_case["amplified"] else "Este é o arquivo DBC real versionado. DBC → Parquet inclui descompactação, parsing, IPC e escrita Parquet."}

    Publicação usa um lake novo por rodada, com dados previamente preparados:
    inclui criação do catálogo e commit, exclui parsing e encerramento do lake.
    """)
    return


@app.cell
def _(PHASES, comparisons, mo, pl):
    mo.vstack(
        [
            mo.md(
                "## 3 · Todas as comparações\n\nMedianas calculadas a partir das rodadas, sem os aquecimentos."
            ),
            mo.ui.table(
                pl.DataFrame([{**r, "phase": PHASES[r["phase"]]} for r in comparisons]),
                selection=None,
                page_size=12,
                label="Tempo por backend e razão de memória",
            ),
        ]
    )
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
def _(json, mo, report, report_path):
    mo.accordion(
        {
            "Proveniência: versões e hashes": mo.md(
                f"Arquivo: `{report_path}`\n\n```json\n"
                + json.dumps(
                    {
                        "packages": report["environment"]["packages"],
                        "crates": report["environment"]["crates"],
                        "source_sha256": report["environment"]["source_sha256"],
                        "rust_wheel": report["rust_wheel"],
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n```"
            ),
            "Baixar a evidência completa": mo.download(
                report_path.read_bytes(), filename=report_path.name, mimetype="application/json"
            ),
        }
    )
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
    O HTML exportado é uma fotografia dos resultados; os filtros reativos funcionam
    com `marimo edit` ou `marimo run`.
    """)
    return


if __name__ == "__main__":
    app.run()

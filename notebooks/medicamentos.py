"""Medicamentos: APAC no lake e observação explícita de estoque BNAFAR/Hórus."""
# ruff: noqa: N803

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="full", app_title="Medicamentos · fontes e pesquisa")


@app.cell
def _():
    import asyncio
    import json
    from dataclasses import asdict
    from pathlib import Path
    from uuid import uuid4

    import marimo as mo

    import omnisus_db as odb
    from omnisus_db.sources.medicamentos import fetch_stock_page

    medication_root = Path(__file__).resolve().parent.parent / "data/lake/medicamentos"
    return Path, asdict, asyncio, fetch_stock_page, json, medication_root, mo, odb, uuid4


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # 1. Descobrir: qual informação sobre medicamentos?

    **SIA-AM:** registros administrativos de APAC de medicamentos, úteis para estudar
    o componente especializado. Linhas não equivalem a pacientes únicos, doses ou
    dispensações efetivas. O procedimento principal exige interpretação por competência.

    **BNAFAR/Hórus:** a API pública verificada oferece **posição de estoque**.
    Estoque não mede dispensação nem comprova cobertura completa da assistência básica.
    O SI-BNAFAR recebe dados dos gestores; sua existência não implica extração pública.

    **Farmácia Popular/MGDI:** o catálogo oferece indicadores de pessoas atendidas;
    isso não representa o conjunto de dispensações das farmácias municipais.

    Abertura e exportação deste notebook não iniciam downloads. Consulte também
    `docs/sources/medicamentos.md` para as fontes oficiais e limites de interpretação.
    """)
    return


@app.cell
def _(mo, odb):
    plano_am = mo.ui.dictionary(
        {
            "uf": mo.ui.dropdown(list(odb.ALL_UFS), value="RR", label="UF do arquivo"),
            "ano": mo.ui.number(start=2008, stop=2099, value=2024, label="Ano"),
            "mes": mo.ui.number(start=1, stop=12, value=1, label="Mês de processamento"),
        }
    ).form(submit_button_label="Fixar recorte SIA-AM")
    mo.vstack([mo.md("## 2. Inspecionar e planejar"), plano_am])
    return (plano_am,)


@app.cell
def _(Path, mo):
    import yaml

    # Dicionário empacotado usado pelo importador; nenhuma consulta de rede.
    # O caminho vem do pacote para funcionar fora da pasta do repositório.
    import omnisus_db

    _path = Path(omnisus_db.__file__).parent / "data/dicionarios/sia_apac_medicamentos.yaml"
    _dictionary = yaml.safe_load(_path.read_text(encoding="utf-8"))
    mo.accordion(
        {
            "Dicionário SIA-AM usado na ingestão": mo.ui.table(
                [
                    {"campo": f["name"], "tipo": f["type"], "descrição": f.get("label", "")}
                    for f in _dictionary["schema"]["fields"]
                ],
                selection=None,
            )
        }
    )
    return


@app.cell
def _(mo, plano_am):
    mo.stop(plano_am.value is None, mo.md("Fixe UF, ano e mês para preparar a execução."))
    recorte_am = dict(plano_am.value)
    executar_am = mo.ui.run_button(label="Importar este recorte SIA-AM")
    mo.vstack(
        [
            mo.md(
                f"Recorte fixado: `{recorte_am}`. Política **skip_same**; um arquivo, "
                "limite comprimido de 25 MiB. Cada execução usa pasta própria. "
                "Não inicie outra execução enquanto esta estiver ativa: interromper "
                "a célula não garante interromper a thread."
            ),
            executar_am,
        ]
    )
    return executar_am, recorte_am


@app.cell
async def _(asdict, asyncio, executar_am, json, medication_root, mo, odb, recorte_am, uuid4):
    mo.stop(
        not executar_am.value, mo.md("## 3. Importar e verificar — aguardando execução explícita")
    )
    _scope = odb.ScopeKey(**recorte_am)
    run_am = str(uuid4())
    pasta_am = medication_root / run_am
    pasta_am.mkdir(parents=True, exist_ok=False)
    target_am = f"ducklake:{pasta_am.resolve() / 'dados.ducklake'}"
    (pasta_am / "plano.json").write_text(
        json.dumps(
            {
                "dataset": "sia_apac_medicamentos",
                "scope": recorte_am,
                "run_id": run_am,
                "target": target_am,
                "policy": "skip_same",
                "omnisus_db": odb.__version__,
            },
            indent=2,
        )
    )
    mo.output.append(mo.md(f"Plano salvo em `{pasta_am / 'plano.json'}`; execução `{run_am}`."))
    try:
        resultado_am = await asyncio.to_thread(
            odb.import_dataset,
            "sia_apac_medicamentos",
            scopes=[_scope],
            target=target_am,
            policy="skip_same",
            run_id=run_am,
            concurrency=1,
            max_payload_bytes=25 * 1024 * 1024,
            max_inflight_bytes=25 * 1024 * 1024,
        )
    except odb.ImportAbortedError as _error:
        (pasta_am / "abortado.json").write_text(
            json.dumps(
                {
                    "report": asdict(_error.report),
                    "unresolved": [(i, asdict(s)) for i, s in _error.unresolved],
                },
                indent=2,
            )
        )
        raise
    (pasta_am / "resultado.json").write_text(json.dumps(asdict(resultado_am), indent=2))
    mo.ui.table(
        [
            {
                "recorte": str(o.scope),
                "estado": o.status,
                "motivo": o.reason,
                "linhas": o.result.rows if o.result else 0,
            }
            for o in resultado_am.outcomes
        ],
        selection=None,
    )
    return pasta_am, resultado_am, run_am, target_am


@app.cell
def _(json, mo, odb, pasta_am, resultado_am, run_am, target_am):
    mo.stop(
        not resultado_am.ok or bool(resultado_am.failed),
        mo.md("Sem publicação concluída para analisar; examine o relatório."),
    )
    with odb.Lake.local(target_am) as _lake:
        publicacoes_am = _lake.publications(run_id=run_am)
        resumo_am = (
            _lake.connect()
            .execute("""
            SELECT ap_pripal AS procedimento_principal, count(*) AS registros_apac,
                   sum(ap_vl_ap) AS valor_aprovado
            FROM lake.sia_apac_medicamentos GROUP BY ap_pripal ORDER BY registros_apac DESC
        """)
            .pl()
        )
        snapshots_am = _lake.snapshots()
    (pasta_am / "publicacoes.json").write_text(
        json.dumps(
            {
                "publicacoes": publicacoes_am,
                "snapshots": snapshots_am,
            },
            indent=2,
            default=str,
        )
    )
    resumo_am.write_csv(pasta_am / "resumo_apac.csv")
    mo.vstack(
        [
            mo.md(
                "## 4. Analisar e reproduzir\nContagem de registros administrativos por "
                "procedimento principal e soma do valor aprovado. Não são doses nem "
                "pacientes únicos. Plano, relatório, publicação e resumo salvos juntos."
            ),
            mo.ui.table(resumo_am, selection=None),
        ]
    )
    return


@app.cell
def _(mo):
    plano_estoque = mo.ui.dictionary(
        {
            "codigo_uf": mo.ui.text(value="14", label="Código IBGE da UF"),
            "data": mo.ui.text(value="", label="Data de estoque AAAA-MM-DD (opcional)"),
        }
    ).form(submit_button_label="Consultar uma página de estoque (máximo 20 registros)")
    mo.vstack(
        [
            mo.md(
                "## Assistência básica: inspecionar a fonte disponível\n"
                "Esta consulta retorna estoque observado no Hórus, sem seleção automática "
                "do componente farmacêutico e sem publicação no lake. Uma página vazia "
                "não demonstra ausência de estoque; uma curta não demonstra completude."
            ),
            plano_estoque,
        ]
    )
    return (plano_estoque,)


@app.cell
async def _(asyncio, fetch_stock_page, json, medication_root, mo, plano_estoque, uuid4):
    mo.stop(plano_estoque.value is None, mo.md("Consulta HTTP aguardando envio do formulário."))
    _filters = {"codigo_uf": plano_estoque.value["codigo_uf"]}
    if plano_estoque.value["data"]:
        _filters["data_posicao_estoque"] = plano_estoque.value["data"]
    pagina_estoque = await asyncio.to_thread(fetch_stock_page, filters=_filters, limit=20)
    _pasta = medication_root / "estoque" / str(uuid4())
    _pasta.mkdir(parents=True, exist_ok=False)
    (_pasta / "resposta.json").write_bytes(pagina_estoque.raw)
    (_pasta / "proveniencia.json").write_text(json.dumps(pagina_estoque.provenance(), indent=2))
    mo.vstack(
        [
            mo.md(f"Observação parcial salva em `{_pasta}`. SHA-256: `{pagina_estoque.sha256}`."),
            mo.ui.table(pagina_estoque.records, selection=None),
        ]
    )
    return


if __name__ == "__main__":
    app.run()

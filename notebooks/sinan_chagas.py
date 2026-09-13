"""Trilha reproduzível: notificações preliminares de Chagas aguda."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="full", app_title="SINAN · Chagas aguda")


@app.cell
def _():
    import asyncio
    import json
    from pathlib import Path
    from uuid import uuid4

    import marimo as mo

    import omnisus_db as odb
    from omnisus_db.transforms.dictionaries import load_dicionario

    dataset = "sinan_chagas"
    root = Path(__file__).resolve().parent.parent / "data/lake/sinan-chagas"
    return Path, asyncio, dataset, json, load_dicionario, mo, odb, root, uuid4


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Chagas aguda: da fonte à análise reproduzível

    Esta trilha importa **arquivos nacionais preliminares de notificações**.
    Não representa Chagas crônica, pessoas únicas, casos confirmados ou incidência.
    A unidade publicada é o arquivo nacional de um ano. Filtre a geografia dos
    registros somente depois da importação; não atribua UF=BR às pessoas.

    Abrir ou exportar este notebook não inicia download ou publicação.
    Os dados são completos para o arquivo adquirido; a vigilância pode ser
    incompleta e a fonte pode revisar suas notificações.
    """)
    return


@app.cell
def _(mo):
    descobrir = mo.ui.run_button(label="1 · Consultar arquivos disponíveis no DATASUS")
    descobrir
    return (descobrir,)


@app.cell
async def _(asyncio, dataset, descobrir, mo, odb):
    mo.stop(
        not descobrir.value,
        mo.md("Consulte o inventário quando quiser verificar a disponibilidade atual."),
    )
    disponiveis = await asyncio.to_thread(odb.available, dataset, refresh=True)
    mo.ui.table(
        [{"ano_do_arquivo": s.ano, "abrangencia": "Nacional"} for s in disponiveis], selection=None
    )
    return


@app.cell
def _(dataset, load_dicionario, mo):
    dic = load_dicionario(dataset)
    mo.vstack(
        [
            mo.md("""## 2 · Inspecionar o contrato

        O inventário físico contém 108 campos observados em CHAGBR23.dbc.
        A validação exige agravo B571 e NU_ANO igual ao ano solicitado.
        Descritores físicos não substituem a revisão semântica do dicionário.
        [Dicionário oficial](https://portalsinan.saude.gov.br/images/documentos/Agravos/Chagas/DIC_DADOS_Chagas_v5.pdf).
        `_source_ano` é metadado de publicação. Campos originais, datas e códigos
        permanecem disponíveis sem renomeação semântica ou deduplicação.
        """),
            mo.ui.table(dic.fields, selection=None, page_size=12),
        ]
    )
    return


@app.cell
def _(mo, root):
    formulario = mo.ui.dictionary(
        {
            "ano": mo.ui.number(
                start=2023, stop=2079, value=2023, label="Ano do arquivo (confira o inventário)"
            ),
            "target": mo.ui.text(value=f"ducklake:{root / 'dados.ducklake'}", label="Lake local"),
            "policy": mo.ui.dropdown(
                ["skip_same", "error_if_exists", "replace"],
                value="skip_same",
                label="Política de publicação",
            ),
        }
    ).form(submit_button_label="3 · Fixar plano de importação")
    mo.vstack(
        [
            mo.md(
                "O plano é fixado ao enviar. `replace` substitui o ano nacional completo; `skip_same` recusa uma revisão diferente."
            ),
            formulario,
        ]
    )
    return (formulario,)


@app.cell
def _(dataset, formulario, json, mo, root, uuid4):
    mo.stop(formulario.value is None, mo.md("Preencha e fixe o plano para continuar."))
    plano = {"dataset": dataset, **formulario.value, "run_id": str(uuid4())}
    root.mkdir(parents=True, exist_ok=True)
    plano_path = root / f"{plano['run_id']}.json"
    plano_path.write_text(json.dumps(plano, ensure_ascii=False, indent=2))
    executar = mo.ui.run_button(label="4 · Baixar arquivo completo e publicar este plano")
    mo.vstack(
        [
            mo.md(
                f"Plano salvo: `{plano_path}`\n\nDestino: `{plano['target']}`\n\nExecução: `{plano['run_id']}`"
            ),
            plano,
            executar,
        ]
    )
    return executar, plano, plano_path


@app.cell
async def _(asyncio, executar, json, mo, odb, plano, plano_path):
    mo.stop(not executar.value, mo.md("A importação só começa pelo botão acima."))
    mo.output.append(
        mo.md(
            "Aguarde a execução. Interromper a célula não garante cancelar a thread; não inicie uma segunda escrita no mesmo lake."
        )
    )
    try:
        report = await asyncio.to_thread(
            odb.import_dataset,
            plano["dataset"],
            scopes=odb.scopes_for(plano["dataset"], years=[plano["ano"]]),
            target=plano["target"],
            policy=plano["policy"],
            run_id=plano["run_id"],
            concurrency=1,
            batch_size=1,
        )
        unresolved = []
    except odb.ImportAbortedError as exc:
        report = exc.report
        unresolved = [{"index": index, "scope": str(scope)} for index, scope in exc.unresolved]
    desfechos = [
        {
            "scope": str(o.scope),
            "status": o.status,
            "reason": o.reason,
            "rows": o.result.rows if o.result else None,
        }
        for o in report.outcomes
    ]
    plano_path.with_suffix(".result.json").write_text(
        json.dumps({"outcomes": desfechos, "unresolved": unresolved}, ensure_ascii=False, indent=2)
    )
    mo.vstack(
        [
            mo.ui.table(desfechos, selection=None),
            mo.md(
                f"Desfechos não resolvidos: `{unresolved}`. Consulte o manifesto antes de repetir uma execução interrompida."
            ),
        ]
    )
    return


@app.cell
def _(mo, root):
    consulta = mo.ui.dictionary(
        {
            "target": mo.ui.text(
                value=f"ducklake:{root / 'dados.ducklake'}", label="Lake que deseja inspecionar"
            ),
            "ano": mo.ui.number(start=2023, stop=2079, value=2023, label="Ano da publicação"),
        }
    ).form(submit_button_label="5 · Conferir publicações e analisar")
    mo.vstack(
        [
            mo.md(
                "Esta consulta independe da célula de importação: use também para recuperar uma execução anterior, depois de o escritor terminar."
            ),
            consulta,
        ]
    )
    return (consulta,)


@app.cell
def _(Path, consulta, dataset, json, mo, odb):
    mo.stop(consulta.value is None)
    _target = consulta.value["target"]
    mo.stop(
        not _target.startswith("ducklake:")
        or not Path(_target.removeprefix("ducklake:")).exists(),
        mo.md("Informe um catálogo local existente."),
    )
    with odb.Lake.local(_target) as _lake:
        _publications = [p for p in _lake.publications() if p["dataset"] == dataset]
        mo.output.append(mo.ui.table(_publications, selection=None))
        mo.stop(dataset not in _lake.tables(), mo.md("Nenhuma tabela deste dataset publicada."))
        _df = (
            _lake.connect()
            .execute(
                "SELECT sg_uf_not, classi_fin, count(*) AS registros "
                "FROM lake.sinan_chagas WHERE _source_ano = ? "
                "GROUP BY sg_uf_not, classi_fin ORDER BY sg_uf_not, classi_fin",
                [consulta.value["ano"]],
            )
            .pl()
        )
        _snapshot = _lake.snapshots()
    mo.vstack(
        [
            mo.md(
                "### Registros por UF de notificação e código de classificação\n\nCódigos são apresentados como publicados. Verifique a documentação antes de selecionar confirmados. Não some notificações como pessoas únicas e não calcule incidência sem definição de caso e denominador compatível."
            ),
            mo.ui.table(_df, selection=None),
            mo.download(_df.write_csv().encode(), filename="chagas-registros.csv"),
            mo.download(
                json.dumps(
                    {
                        "publications": _publications,
                        "snapshots": _snapshot,
                        "filters": consulta.value,
                    },
                    default=str,
                    ensure_ascii=False,
                    indent=2,
                ).encode(),
                filename="chagas-proveniencia.json",
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()

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

"""Consulta real dos metadados documentais pelo terminal, dentro do checkout."""

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="full", app_title="Metadados por coluna · CLI")


@app.cell
def _():
    import json
    import os
    import shlex
    import subprocess
    import sys
    from pathlib import Path

    import marimo as mo

    project_root = Path(__file__).resolve().parents[2]

    def run_python(arguments):
        # UTF-8 nos dois lados: no Windows o console padrão (cp1252) não codifica
        # caracteres como "→" que os scripts imprimem.
        result = subprocess.run(
            [sys.executable, *arguments],
            cwd=project_root,
            capture_output=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
            timeout=60,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(
                f"Comando terminou com código {result.returncode}:\n{result.stderr}"
            )
        return {
            "command": shlex.join([sys.executable, *arguments]),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def terminal(result):
        return mo.accordion(
            {
                "Comando executado e saída completa": mo.vstack(
                    [
                        mo.md("Execute a partir da raiz do checkout:"),
                        mo.md(f"```bash\n{result['command']}\n```"),
                        mo.md(f"Código de saída: **{result['returncode']}**"),
                        mo.ui.code_editor(value=result["stdout"], language="json", disabled=True),
                        mo.md(f"```text\n{result['stderr'] or '(stderr vazio)'}\n```"),
                    ]
                )
            }
        )

    return json, mo, run_python, terminal


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Acessar metadados pelo terminal

    [![Open in molab](https://molab.marimo.io/molab-shield.svg)](https://molab.marimo.io/github/raphaelfh/omnisus-db/blob/main/notebooks/desenvolvimento/metadados_cli.py)

    Este notebook **executa subprocessos reais** e transforma suas saídas JSON
    em tabelas. Funciona offline com os arquivos versionados do checkout.

    A CLI `omnisus-db` ainda não oferece um comando de dicionário semântico.
    O acesso demonstrado usa o **script experimental em `scripts/metadados/`** e comandos
    Python de terminal para consultar os CSVs/JSONs existentes. Não exige um lake
    aberto nem faz downloads. Use o ambiente do projeto com `jsonschema` e `pyarrow`.

    Há duas camadas de evidência: o exemplo `SIM/DO/SEXO` tem afirmações conferidas
    em uma fonte oficial; o inventário geral contém definições locais cuja
    validação semântica ainda está pendente. Nenhuma etapa recodifica registros.
    """)
    return


@app.cell
def _(json, run_python):
    document_result = run_python(
        [
            "scripts/metadados/consultar.py",
            "--metadata",
            "docs/dicionario/exemplos/sim_obitos.sexo.json",
            "--json",
        ]
    )
    metadata = json.loads(document_result["stdout"])
    assert metadata["field"]["id"] == "sim_obitos.sexo"
    return document_result, metadata


@app.cell(hide_code=True)
def _(document_result, json, metadata, mo, terminal):
    mo.vstack(
        [
            mo.md("""
            ## 1. Obter JSON validado de um campo

            ```bash
            python scripts/metadados/consultar.py \
              --metadata docs/dicionario/exemplos/sim_obitos.sexo.json --json
            ```

            `stdout` contém apenas JSON. Erros de validação terminam com código
            diferente de zero; não são substituídos por metadados fictícios.
            Este comando lê um documento de campo, não busca um dataset pelo nome.
            """),
            mo.md(
                f"**{metadata['field']['id']}** — {metadata['field']['description']}\n\n"
                f"Nome físico: `{metadata['field']['physical_name']}` · "
                f"Contrato: `{metadata['schema_version']}` · "
                f"Edição editorial: `{metadata['dictionary_version']}`"
            ),
            mo.ui.table(metadata["field"]["codes"], label="Códigos declarados no documento"),
            terminal(document_result),
            mo.download(
                data=json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"),
                filename="sim_obitos.sexo.metadata.json",
                mimetype="application/json",
                label="Baixar o metadado JSON completo",
            ),
        ]
    )
    return


@app.cell
def _(json, run_python):
    # Argumentos separados, sem shell=True: filtros não são interpretados pelo shell.
    evidence_code = (
        "import json,sys; m=json.load(open(sys.argv[1], encoding='utf-8')); "
        "print(json.dumps({k:m[k] for k in ['claims','sources','applicability','issues']}, "
        "ensure_ascii=False, indent=2))"
    )
    evidence_result = run_python(
        ["-c", evidence_code, "docs/dicionario/exemplos/sim_obitos.sexo.json"]
    )
    evidence = json.loads(evidence_result["stdout"])
    return evidence, evidence_result


@app.cell(hide_code=True)
def _(evidence, evidence_result, mo, terminal):
    mo.vstack(
        [
            mo.md("""
            ## 2. Ver a fonte e a data de checagem

            A validade estrutural do JSON não prova o significado do campo.
            `claims` informa **o que** foi conferido, por quem, quando e em qual
            página. `sources` identifica os bytes do documento com SHA-256.

            No exemplo, a descrição, o tipo físico e os códigos foram conferidos
            na página 2 do manual SIM de 07/2025, em **10/09/2026**. A aplicabilidade
            aos dados de 2023 permanece **unknown**. O tipo lógico legado é inteiro,
            apesar de o manual também listar letras; essa divergência está em `issues`.
            """),
            mo.ui.table(evidence["sources"], label="Fonte oficial e integridade"),
            mo.ui.table(
                [
                    {
                        "afirmacao": claim["target"],
                        "estado": claim["status"],
                        "checado_em": claim["checked_at"],
                        "responsavel": claim["reviewer"],
                        "evidencia": str(claim["evidence"]),
                    }
                    for claim in evidence["claims"]
                ],
                label="Checagem por afirmação",
            ),
            mo.md(f"**Aplicabilidade:** {evidence['applicability']['reason']}"),
            terminal(evidence_result),
        ]
    )
    return


@app.cell
def _(json, run_python):
    inventory_result = run_python(
        [
            "-c",
            "import csv,json,sys; "
            "print(json.dumps(list(csv.DictReader(open(sys.argv[1], encoding='utf-8'))), "
            "ensure_ascii=False))",
            "docs/dicionario/cobertura.csv",
        ]
    )
    inventory = json.loads(inventory_result["stdout"])
    return inventory, inventory_result


@app.cell(hide_code=True)
def _(inventory, inventory_result, mo, terminal):
    category = mo.ui.dropdown(
        [row["categoria"] for row in inventory], value="SIM", label="Categoria"
    )
    mo.vstack(
        [
            mo.md("""
            ## 3. Descobrir a cobertura e consultar outras colunas

            O CSV de cobertura inclui as 18 categorias. `campos.csv` reúne as
            1.326 ocorrências de colunas observadas em 65 tabelas da auditoria.
            Isso não cobre todos os subtipos e períodos disponíveis no DATASUS.
            A amostra TABWIN é um aplicativo e não possui colunas tabulares.
            """),
            mo.ui.table(inventory, label="Cobertura da auditoria de 10/09/2026"),
            terminal(inventory_result),
            category,
        ]
    )
    return (category,)


@app.cell
def _(category, json, run_python):
    filter_code = (
        "import csv,json,sys; rows=csv.DictReader(open(sys.argv[1], encoding='utf-8')); "
        "print(json.dumps([r for r in rows if r['categoria']==sys.argv[2]], "
        "ensure_ascii=False, indent=2))"
    )
    fields_result = run_python(["-c", filter_code, "docs/dicionario/campos.csv", category.value])
    fields = json.loads(fields_result["stdout"])
    return fields, fields_result


@app.cell(hide_code=True)
def _(fields, fields_result, mo, terminal):
    field_choices = {f"{row['tabela']} / {row['coluna']}": i for i, row in enumerate(fields)}
    preferred = next((key for key in field_choices if key.endswith(" / SEXO")), None)
    field_selector = mo.ui.dropdown(
        field_choices,
        value=preferred or next(iter(field_choices), None),
        label="Tabela / coluna observada",
    )
    mo.vstack(
        [
            mo.md(f"**{len(fields)} ocorrências** na categoria selecionada."),
            terminal(fields_result),
            field_selector if fields else mo.md("Esta amostra não contém tabelas de dados."),
        ]
    )
    return (field_selector,)


@app.cell(hide_code=True)
def _(field_selector, fields, json, mo):
    mo.stop(not fields or field_selector.value is None)
    selected_field = fields[field_selector.value]
    local_codes = json.loads(selected_field["codigos_locais_json"] or "{}")
    mo.vstack(
        [
            mo.ui.table([selected_field], label="Metadados disponíveis da coluna"),
            mo.ui.table(
                [{"codigo": code, "rotulo_local": label} for code, label in local_codes.items()],
                label="Códigos locais — revisão oficial pendente",
            )
            if local_codes
            else mo.md("Não há mapa local de códigos para esta ocorrência."),
            mo.md(
                "**Estado da auditoria:** "
                + selected_field["validacao_semantica"]
                + "\n\nCélula vazia significa informação não mapeada. Uma menção textual "
                "em PDF é uma pista para curadoria, não uma comprovação semântica."
            ),
        ]
    )
    return


@app.cell
def _(run_python):
    arrow_result = run_python(["scripts/metadados/consultar.py", "--arrow"])
    return (arrow_result,)


@app.cell(hide_code=True)
def _(arrow_result, mo, terminal):
    mo.vstack(
        [
            mo.md("""
            ## 4. Verificar o transporte por coluna

            ```bash
            python scripts/metadados/consultar.py --arrow
            ```

            O comando valida o exemplo e faz Arrow → Parquet → Arrow em memória,
            verificando a chave `omnisus:column`. A tabela é vazia: o teste é de
            transporte dos metadados, sem fabricar registros ou converter tipos.

            Para salvar o JSON em um terminal, escolha o destino desejado:

            ```bash
            python scripts/metadados/consultar.py --json > sexo.metadata.json
            ```

            O redirecionamento acima é uma receita, não é executado pelo notebook.
            `>` substitui o arquivo de destino caso já exista. Estes metadados ainda
            não são anexados automaticamente às exportações da biblioteca.
            """),
            terminal(arrow_result),
        ]
    )
    return


if __name__ == "__main__":
    app.run()

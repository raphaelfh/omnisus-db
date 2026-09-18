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
        return {
            "comando": result["command"],
            "returncode": result["returncode"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
        }

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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Obter JSON validado de um campo

    ```bash
    python scripts/metadados/consultar.py \
      --metadata docs/dicionario/exemplos/sim_obitos.sexo.json --json
    ```

    `stdout` contém apenas JSON. Erros de validação terminam com código diferente
    de zero; não são substituídos por metadados fictícios.
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


@app.cell
def _(document_result, metadata, terminal):
    {
        "id": metadata["field"]["id"],
        "descricao": metadata["field"]["description"],
        "physical_name": metadata["field"]["physical_name"],
        "schema_version": metadata["schema_version"],
        "dictionary_version": metadata["dictionary_version"],
        "codigos": metadata["field"]["codes"],
        "terminal": terminal(document_result),
    }
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
def _(mo):
    mo.md("""
    ## 2. Ver a fonte e a data de checagem

    A validade estrutural do JSON não prova o significado do campo.
    `claims` informa **o que** foi conferido, por quem, quando e em qual página.
    """)
    return


@app.cell
def _(evidence, evidence_result, terminal):
    {
        "fontes": evidence["sources"],
        "claims": evidence["claims"],
        "aplicabilidade": evidence["applicability"],
        "terminal": terminal(evidence_result),
    }
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
def _(mo):
    mo.md("""
    ## 3. Descobrir a cobertura e consultar outras colunas

    O CSV de cobertura inclui as 18 categorias. `campos.csv` reúne as 1.326
    ocorrências de colunas observadas em 65 tabelas da auditoria.
    """)
    return


@app.cell
def _(inventory, inventory_result, terminal):
    CATEGORIA = "SIM"
    COLUNA = "SEXO"
    {
        "cobertura": inventory,
        "terminal": terminal(inventory_result),
        "CATEGORIA": CATEGORIA,
        "COLUNA": COLUNA,
    }
    return CATEGORIA, COLUNA


@app.cell
def _(CATEGORIA, json, run_python):
    filter_code = (
        "import csv,json,sys; rows=csv.DictReader(open(sys.argv[1], encoding='utf-8')); "
        "print(json.dumps([r for r in rows if r['categoria']==sys.argv[2]], "
        "ensure_ascii=False, indent=2))"
    )
    fields_result = run_python(["-c", filter_code, "docs/dicionario/campos.csv", CATEGORIA])
    fields = json.loads(fields_result["stdout"])
    return fields, fields_result


@app.cell
def _(COLUNA, fields, fields_result, json, mo, terminal):
    mo.stop(not fields, mo.md("Esta amostra não contém tabelas de dados."))
    selected_field = next((row for row in fields if row["coluna"] == COLUNA), fields[0])
    local_codes = json.loads(selected_field["codigos_locais_json"] or "{}")
    {
        "ocorrencias": len(fields),
        "campo": selected_field,
        "codigos_locais": local_codes,
        "terminal": terminal(fields_result),
    }
    return


@app.cell
def _(run_python):
    arrow_result = run_python(["scripts/metadados/consultar.py", "--arrow"])
    return (arrow_result,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## 4. Verificar o transporte por coluna

    ```bash
    python scripts/metadados/consultar.py --arrow
    ```
    """)
    return


@app.cell
def _(arrow_result, terminal):
    terminal(arrow_result)
    return


if __name__ == "__main__":
    app.run()

"""Projeta a auditoria existente em docs; não consulta rede nem renova datas."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from omnisus_db.metadata import sources_registry

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs/dicionario"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-dir", type=Path, default=ROOT / "reports/2026-09-10-mapa-datasus")
    parser.add_argument("--check-local", action="store_true")
    args = parser.parse_args()
    audit_dir = args.audit_dir.resolve()
    audit = json.loads((audit_dir / "auditoria_fontes.json").read_text(encoding="utf-8"))
    checked_on = audit["consulta_utc"][:10]
    registry = sources_registry()
    sources = registry["sources"]
    if args.check_local:
        import hashlib

        by_hash = {source["sha256"]: source for source in sources}
        for item in audit["documentos"]:
            if "sha256" not in item:
                continue
            source = by_hash[item["sha256"]]
            original = Path(item["arquivo"])
            cache = (
                ROOT
                / "data/lake/panorama-datasus/documentacao-auditoria"
                / original.parent.name
                / original.name
            )
            path = original if original.is_file() else cache
            content = path.read_bytes()
            if (
                len(content) != source["bytes"]
                or hashlib.sha256(content).hexdigest() != source["sha256"]
            ):
                raise ValueError(f"Evidência local divergente: {path}")

    coverage = {row["categoria"]: row for row in read_csv(audit_dir / "auditoria_cobertura.csv")}
    rows = []
    for sample in read_csv(audit_dir / "fontes.csv"):
        category = sample["categoria"]
        current = coverage.get(category, {})
        source_ids = [source["id"] for source in sources if source["category"] == category]
        rows.append(
            {
                "categoria": category,
                "subtipo_amostrado": sample["subtipo_amostrado"],
                "tabelas_amostradas": int(sample["tabelas"]),
                "ocorrencias_colunas": int(sample["colunas"]),
                "rotulos_locais": int(current.get("rotulos_locais", 0)),
                "mapas_codigos_locais": int(current.get("mapas_de_codigos_locais", 0)),
                "pdfs_obtidos": len(source_ids),
                "nomes_mencionados_em_pdf": int(current.get("nomes_mencionados_em_pdf", 0)),
                "validacao_semantica_individual": "não auditada"
                if sample["tabelas"] != "0"
                else "não aplicável à amostra",
                "checagem_auditoria": checked_on,
                "source_ids": "|".join(source_ids),
            }
        )
    physical_columns = {
        (row["categoria"], row["tabela"], row["nome"]): row
        for row in read_csv(audit_dir / "colunas.csv")
    }
    columns = []
    for row in read_csv(audit_dir / "auditoria_colunas.csv"):
        physical = physical_columns[(row["categoria"], row["tabela"], row["coluna"])]
        columns.append(
            {
                **row,
                "tipo_origem": physical["tipo_origem"],
                "largura": physical["largura"],
                "decimais": physical["decimais"],
                "source_ids_mencao_textual": "|".join(
                    source["id"]
                    for source in sources
                    if source["url"] in row["mencao_textual_em_pdf"]
                ),
                "checagem_auditoria": checked_on,
            }
        )
    if len(columns) != len(physical_columns):
        raise ValueError("Cobertura de colunas divergente entre os relatórios de origem")
    # Preparar tudo antes de substituir projeções; uma falha de evidência não as atualiza.
    (DOCS / "fontes").mkdir(parents=True, exist_ok=True)
    (DOCS / "fontes/registro.json").write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (DOCS / "cobertura.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (DOCS / "campos.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(columns[0]))
        writer.writeheader()
        writer.writerows(columns)
    lines = [
        "# Catálogo da auditoria",
        "",
        f"Projeção gerada da auditoria `{audit_dir.name}`, consultada em **{checked_on}**.",
        "Regenerar este arquivo não faz nova consulta nem renova a checagem.",
        "",
        "As contagens abaixo representam a amostra de cada categoria, não todos os produtos",
        "existentes. Colunas são ocorrências por tabela. Rótulos locais e nomes encontrados",
        "em PDFs não são confirmações de significado, códigos ou vigência.",
        "",
        "| Categoria | Subtipo amostrado | Tabelas | Colunas | Rótulos locais | Mapas locais | PDFs obtidos |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['categoria']} | {row['subtipo_amostrado']} | {row['tabelas_amostradas']} | "
            f"{row['ocorrencias_colunas']} | {row['rotulos_locais']} | {row['mapas_codigos_locais']} | {row['pdfs_obtidos']} |"
        )
    lines += [
        "",
        "## Interpretação e prioridades",
        "",
        "- **SIM, SINASC e SIH/RD:** começar pela revisão dos campos já presentes nos YAMLs,",
        "  identificando diferenças de edição e colunas ainda sem definição.",
        "- **CNES/ST:** ampliar a cobertura do produto exato; o rótulo da categoria não cobre os demais subtipos.",
        "- **SIA/PA e IBGE/POPT:** não reutilizar automaticamente o dicionário de outro produto/API da mesma base.",
        "- **CIH, SISCOLO, SISMAMA e SISPRENATAL:** documentação não obtida nos locais consultados;",
        "  manter busca pendente. Isso não comprova inexistência de dicionários.",
        "- **SINAN:** os documentos específicos e de notificação geral se complementam; conferir a edição.",
        "- **DATASUS/TABWIN:** aplicativo amostrado, sem tabela de registros; não contar como falha de dicionário de coluna.",
        "",
        "## Evidências recuperáveis",
        "",
        "O [registro JSON](fontes/registro.json) fornece ID, URL oficial, hash e datas de cada PDF.",
        "Campos editoriais desconhecidos permanecem `null`; nomes de arquivo não são usados para inventar datas.",
        "O [CSV de cobertura](cobertura.csv) relaciona os IDs das fontes às categorias.",
        "O [inventário por campo](campos.csv) reúne as colunas físicas, rótulos/códigos locais",
        "e IDs das fontes com menção textual, mantendo a validação semântica como pendente.",
        "",
        "| Categoria | Documento | ID |",
        "| --- | --- | --- |",
    ]
    for source in sources:
        lines.append(
            f"| {source['category']} | [{source['title']}]({source['url']}) | `{source['id']}` |"
        )
    lines += [
        "",
        "## Rastreamento no repositório",
        "",
        f"As tabelas e todas as colunas estão em `reports/{audit_dir.name}/tabelas.csv` e `colunas.csv`.",
        "A auditoria detalhada está em `auditoria_colunas.csv`, `auditoria_fontes.json` e",
        "`AUDITORIA_DICIONARIOS.md` na mesma pasta. Esses relatórios são o retrato histórico",
        "usado nesta projeção; não são regenerados aqui.",
        "",
        "O [exemplo de contrato](exemplos/sim_obitos.sexo.json) acrescenta uma checagem pontual",
        "do campo SEXO no documento SIM de 2025, com aplicabilidade histórica pendente.",
        "Ele não promove os demais campos a revisados nem muda as contagens da auditoria.",
        "",
    ]
    (DOCS / "catalogo.md").write_text("\n".join(lines), encoding="utf-8")
    print(
        f"Catálogo: {len(rows)} categorias, {len(sources)} documentos; data preservada: {checked_on}."
    )


if __name__ == "__main__":
    main()

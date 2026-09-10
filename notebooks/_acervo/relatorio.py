"""Generate the same inspectable map for the notebook and the final report."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from .catalogo import PORTAL, PORTAL_SCRIPT


def maps(manifest):
    sources, tables, columns, members = [], [], [], []
    for source in manifest["fontes"]:
        raw = source.get("arquivo", {})
        inventory = source.get("inventario", {})
        sources.append(
            {
                "categoria": source["key"],
                "descricao": source["title"],
                "natureza": source["kind"],
                "subtipo_amostrado": source["subtype"],
                "status": source["status"],
                "arquivo": raw.get("arquivo"),
                "bytes": raw.get("bytes"),
                "url": raw.get("url"),
                "sha256": raw.get("sha256"),
                "tabelas": len(source["tabelas"]),
                "colunas": sum(t["n_colunas"] for t in source["tabelas"]),
                "linhas_amostradas": sum(t["linhas_amostra"] for t in source["tabelas"]),
                "arquivos_diretorio": inventory.get("arquivos_no_diretorio"),
                "diretorio_listado": inventory.get("diretorio"),
                "erro": source.get("erro"),
            }
        )
        for table in source["tabelas"]:
            tables.append(
                {"categoria": source["key"], **{k: v for k, v in table.items() if k != "colunas"}}
            )
            columns.extend(
                {
                    "categoria": source["key"],
                    "tabela": table["tabela"],
                    "membro": table["membro"],
                    **c,
                }
                for c in table["colunas"]
            )
        members.extend({"categoria": source["key"], **member} for member in source["membros"])
    return sources, tables, columns, members


def markdown_table(rows, fields):
    def value(v):
        return str("—" if v is None else v).replace("|", "\\|").replace("\n", " ")

    return "\n".join(
        ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
        + ["| " + " | ".join(value(row.get(k)) for k in fields) + " |" for row in rows]
    )


def write_report(manifest, directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    sources, tables, columns, members = maps(manifest)
    for name, rows in [
        ("fontes", sources),
        ("tabelas", tables),
        ("colunas", columns),
        ("membros_zip", members),
    ]:
        if rows:
            pl.DataFrame(rows, infer_schema_length=None).write_csv(directory / f"{name}.csv")
    (directory / "mapa.json").write_text(
        json.dumps(
            {
                "fontes": sources,
                "tabelas": tables,
                "colunas": columns,
                "membros_zip": members,
                "subtipos_portal": manifest.get("tipos_portal", []),
                "recuperacoes": manifest.get("recuperacoes", []),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    total_bytes = sum(s["bytes"] or 0 for s in sources)
    if manifest.get("tipos_portal"):
        pl.DataFrame(manifest["tipos_portal"]).write_csv(directory / "subtipos_portal.csv")
    lines = [
        "# Mapa do acervo didático DATASUS",
        "",
        f"Coleta iniciada em **{manifest['inicio_utc']}** e encerrada em **{manifest.get('fim_utc', 'em andamento')}**.",
        "",
        f"**{len(sources)} categorias**, **{sum(s['status'] == 'amostra' for s in sources)} com amostras tabulares**, "
        f"**{sum(s['status'] == 'artefato' for s in sources)} de aplicativo**, "
        f"**{sum(s['status'] == 'falha' for s in sources)} falhas**. "
        f"Foram extraídas **{len(tables)} tabelas**, **{len(columns)} ocorrências de colunas** e "
        f"**{sum(t['linhas_amostra'] for t in tables):,} linhas de amostra**. "
        f"Os arquivos escolhidos somam **{total_bytes / 1024**2:.2f} MiB**.",
        "",
        "## Alcance e leitura correta",
        "",
        "- Uma amostra por categoria do seletor. Isso **não cobre todos os subtipos, agravos, anos ou UFs** do DATASUS.",
        "- Cada DBC/ZIP escolhido foi baixado inteiro. As tabelas exportadas contêm somente as primeiras "
        f"{manifest['limite_linhas']} linhas ativas de cada tabela, ou todas quando há menos registros.",
        "- O inventário se refere ao diretório listado e os descritores de colunas se referem ao arquivo amostrado. "
        "Não extrapole esse esquema para todos os arquivos da categoria.",
        "- Campos são mantidos como texto bruto (Latin-1 nos DBFs), preservando zeros à esquerda, datas e códigos. "
        "Tipo DBF, largura e casas decimais são descritores físicos; String é o tipo da amostra.",
        "- Nulos e valores distintos são calculados somente na amostra. Os totais de registros ativos/excluídos "
        "vêm da geometria e dos marcadores físicos do DBF, cuja integridade foi conferida.",
        "- Arquivos nacionais e estaduais do IBGE se sobrepõem. Linhas de tabelas diferentes não são somáveis "
        "como pessoas únicas; códigos homônimos não comprovam que uma junção é válida.",
        "- Documentação e descritores físicos não equivalem a um dicionário semântico validado. "
        "Significados, unidades e categorias clínicas exigem a documentação específica.",
        "- ZIPs são inspecionados sem executar seus programas. Na Base Territorial, DBF é preferido "
        "às cópias CSV/XML/TXT da mesma tabela. Todos os membros permanecem no inventário do ZIP.",
        "",
        f"Fontes: [seletor de transferência DATASUS]({PORTAL}) e "
        f"[definições de categorias e subtipos do portal]({PORTAL_SCRIPT}). "
        "O manifesto registra URLs exatas de cada arquivo e SHA-256.",
        "",
        "## Visão geral",
        "",
        markdown_table(
            sources,
            [
                "categoria",
                "subtipo_amostrado",
                "status",
                "arquivo",
                "bytes",
                "tabelas",
                "colunas",
                "linhas_amostradas",
            ],
        ),
        "",
        "## Arquivos para consulta",
        "",
        "- [Fontes e arquivos](fontes.csv)",
        "- [Mapa de tabelas](tabelas.csv)",
        "- [Todas as colunas e descritores](colunas.csv)",
        "- [Membros dos ZIPs](membros_zip.csv)",
        "- [Mapa estruturado completo](mapa.json)",
        "- [Subtipos descritos pelo portal, incluindo não amostrados](subtipos_portal.csv)",
        "",
        "## Como escolher o próximo estudo",
        "",
        "Use o esquema para formular uma pergunta, examine o dicionário específico e só então decida "
        "o recorte a importar por inteiro. Comece pela unidade de observação: cadastro, exame, "
        "notificação, produção, população e território possuem denominadores distintos. "
        "Amostras de conveniência servem para aprender a estrutura, não para inferência populacional.",
        "",
    ]
    for source in manifest["fontes"]:
        raw = source.get("arquivo", {})
        inventory = source.get("inventario", {})
        lines.extend(
            [
                f"## {source['key']} — {source['title']}",
                "",
                f"**Natureza:** {source['kind']} · **Subtipo escolhido:** `{source['subtype']}` · **Status:** {source['status']}.",
                "",
                f"**Pergunta de estudo:** {source['question']}",
                "",
                f"**Limitação:** {source['limitation']}",
                "",
                f"**Inventário:** `{inventory.get('diretorio', 'não concluído')}`; "
                f"{inventory.get('arquivos_no_diretorio', 0)} arquivos no diretório, "
                f"{inventory.get('candidatos', 0)} candidatos do subtipo dentro do limite de tamanho.",
                "",
            ]
        )
        if raw:
            lines.extend(
                [
                    f"**Arquivo:** [{raw['arquivo']}]({raw['url']}) · {raw['bytes']:,} bytes.",
                    "",
                    f"**Coleta UTC:** `{raw['coleta_utc']}` · **Modificação informada pelo FTP (sem fuso):** `{raw['modificado_servidor']}`.",
                    "",
                    f"**SHA-256:** `{raw['sha256']}`",
                    "",
                    f"**Original local:** `{raw['local']}`",
                    "",
                ]
            )
        if source.get("erro"):
            lines.extend([f"**Erro:** {source['erro']}", ""])
        subtype_rows = [
            r
            for r in manifest.get("tipos_portal", [])
            if r["fonte"].upper().removesuffix("_P") == source["key"].upper()
        ]
        if subtype_rows:
            lines.extend(
                [
                    "### Subtipos descritos no portal (nem todos foram amostrados)",
                    "",
                    markdown_table(
                        subtype_rows, ["fonte", "sigla_arquivo", "desc_arquivo", "abrangencia"]
                    ),
                    "",
                ]
            )
        if inventory.get("portal_erro"):
            lines.extend(
                [
                    f"**Falha de consulta ao portal:** {inventory['portal_erro']}. Listagem FTP usada explicitamente.",
                    "",
                ]
            )
        if inventory.get("portal_resultados"):
            labels = sorted(
                {
                    r.get("fonte", "") + " / " + r.get("modalidade", "")
                    for r in inventory["portal_resultados"]
                }
            )
            lines.extend([f"**Rótulos retornados pelo portal:** {'; '.join(labels)}.", ""])
        if len(source["tentativas"]) > 1 or source["status"] == "falha":
            lines.extend(
                [
                    "### Tentativas de obtenção",
                    "",
                    markdown_table(source["tentativas"], ["arquivo", "status", "motivo"]),
                    "",
                ]
            )
        if source["membros"]:
            lines.extend(
                [
                    "### Conteúdo do ZIP",
                    "",
                    markdown_table(
                        source["membros"], ["arquivo", "bytes", "comprimidos", "diretorio"]
                    ),
                    "",
                ]
            )
        for table in source["tabelas"]:
            lines.extend(
                [
                    f"### Tabela `{table['membro']}`",
                    "",
                    f"**Identificador:** `{table['tabela']}` · **Campos:** {table['n_colunas']} · "
                    f"**Linhas na amostra:** {table['linhas_amostra']}.",
                    "",
                    f"Registros declarados: **{table['registros_declarados']}**; "
                    f"ativos: **{table['registros_ativos']}**; excluídos: **{table['registros_excluidos']}**. "
                    f"Reparo do terminador DBF: **{table.get('terminador_reparado', False)}**.",
                    "",
                    f"Amostra Parquet: `{table['amostra_parquet']}`",
                    "",
                    markdown_table(
                        table["colunas"],
                        [
                            "nome",
                            "tipo_origem",
                            "largura",
                            "decimais",
                            "tipo_amostra",
                            "nulos_amostra",
                            "distintos_amostra",
                        ],
                    ),
                    "",
                ]
            )
        if source["documentos"]:
            lines.extend(
                [
                    "### Documentos textuais encontrados",
                    "",
                    markdown_table(source["documentos"], ["arquivo", "bytes"]),
                    "",
                ]
            )
    report = directory / "README.md"
    if manifest.get("recuperacoes"):
        lines.extend(
            [
                "## Recuperações após a coleta inicial",
                "",
                markdown_table(manifest["recuperacoes"], ["categoria", "manifesto", "fim_utc"]),
                "",
            ]
        )
    report.write_text("\n".join(lines), encoding="utf-8")
    return report

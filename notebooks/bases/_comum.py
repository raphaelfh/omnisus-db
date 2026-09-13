"""O que se repete nos notebooks de bases/: onde uma execução fica e o que ela registra.

As chamadas da biblioteca que cada notebook ensina (`available`, `import_dataset`,
`LakeReader`, `publications`, `outdated`) ficam visíveis nas células. Este módulo
só grava arquivos, monta o filtro de um escopo e confere contagens.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import omnisus_db as odb
from omnisus_db.lake.publication import scope_fields
from omnisus_db.lake.sql import qualified

LIMITE_BYTES = 25 * 1024 * 1024
"""Teto do arquivo comprimido baixado nos recortes didáticos."""

_REPOSITORIO = Path(__file__).resolve().parents[2]


def raiz_dados() -> Path:
    """Pasta do lake de pesquisa compartilhado; `OMNISUS_NOTEBOOK_DATA` a substitui."""
    return Path(os.environ.get("OMNISUS_NOTEBOOK_DATA") or _REPOSITORIO / "data/lake/pesquisa")


def target_padrao() -> str:
    return f"ducklake:{raiz_dados() / 'dados.ducklake'}"


def executar_sem_botoes(cli_args: Mapping[str, object]) -> bool:
    """`-- --executar true` percorre as etapas dos botões sem interface."""
    return str(cli_args.get("executar", "false")).lower() == "true"


def salvar_json(caminho: Path, conteudo: object) -> Path:
    texto = json.dumps(conteudo, default=str, ensure_ascii=False, indent=2)
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def fixar_plano(target: str, **detalhes: Any) -> tuple[dict[str, Any], Path]:
    """Cria a pasta da execução e grava `plano.json` antes de qualquer download."""
    agora = datetime.now(UTC)
    run_id = f"{agora:%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    pasta = raiz_dados() / "execucoes" / run_id
    pasta.mkdir(parents=True)
    plano = {
        **detalhes,
        "target": target,
        "run_id": run_id,
        "omnisus_db": odb.__version__,
        "fixado_em_utc": agora.isoformat(),
    }
    salvar_json(pasta / "plano.json", plano)
    return plano, pasta


def desfechos(relatorio: odb.ImportReport) -> list[dict[str, Any]]:
    return [
        {
            "escopo": str(o.scope),
            "status": o.status,
            "linhas": o.result.rows if o.result else None,
            "motivo": o.reason,
        }
        for o in relatorio.outcomes
    ]


def registrar_importacao(
    pasta: Path,
    relatorio: odb.ImportReport,
    nao_resolvidos: Iterable[tuple[int, odb.ScopeKey]] = (),
) -> list[dict[str, Any]]:
    """Grava `resultado.json` e devolve a tabela de desfechos para exibir."""
    linhas = desfechos(relatorio)
    salvar_json(
        pasta / "resultado.json",
        {
            "linhas_importadas": relatorio.rows,
            "desfechos": linhas,
            "nao_resolvidos": [{"indice": i, "escopo": str(e)} for i, e in nao_resolvidos],
        },
    )
    return linhas


def filtro_escopo(escopo: odb.ScopeKey) -> tuple[str, list[object]]:
    """`WHERE` que seleciona as linhas de um escopo, nas colunas que a biblioteca grava."""
    campos = scope_fields(escopo)
    return " AND ".join(f'"{nome}" = ?' for nome in campos), list(campos.values())


def conferir(
    leitor: odb.LakeReader, dataset: str, escopos: Sequence[odb.ScopeKey]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Linhas no lake contra linhas publicadas, por escopo, e as publicações ativas."""
    ativas = [
        p
        for p in leitor.publications()
        if p["dataset"] == dataset and p["active"] and p["scope"] in escopos
    ]
    conferencia = []
    for escopo in escopos:
        where, args = filtro_escopo(escopo)
        sql = f"SELECT count(*) FROM {qualified(leitor.alias, dataset)} WHERE {where}"
        (no_lake,) = leitor.connect().execute(sql, args).fetchone()
        publicadas = sum(p["rows"] for p in ativas if p["scope"] == escopo)
        conferencia.append(
            {
                "escopo": str(escopo),
                "linhas_no_lake": no_lake,
                "linhas_publicadas": publicadas,
                "confere": no_lake == publicadas,
            }
        )
    return conferencia, ativas


def registrar_proveniencia(
    pasta: Path,
    *,
    plano: Mapping[str, Any],
    publicacoes: Sequence[Mapping[str, Any]],
    snapshot_id: int,
    consultas: Mapping[str, str],
) -> dict[str, Any]:
    """Grava `proveniencia.json`: o suficiente para citar e refazer o resultado."""
    registro = {
        "plano": dict(plano),
        "publicacoes": [dict(p) for p in publicacoes],
        "snapshot_id": snapshot_id,
        "consultas": dict(consultas),
        "omnisus_db": odb.__version__,
        "gerado_em_utc": datetime.now(UTC).isoformat(),
    }
    salvar_json(pasta / "proveniencia.json", registro)
    return registro

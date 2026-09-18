"""Helpers shared by the `notebooks/bases/` marimo notebooks.

The teaching surface stays in the notebook cells (`available`, `import_dataset`,
`LakeReader`, `publications`, `outdated`). This module only chooses where a run
lives, writes the JSON a citation needs, and reconciles row counts.

It lives in the installable package so a notebook opened on molab or with
``marimo edit --sandbox`` does not depend on a sibling ``_comum.py``.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from omnisus_db._version import __version__
from omnisus_db.lake import LakeReader
from omnisus_db.lake.publication import scope_fields
from omnisus_db.lake.sql import qualified
from omnisus_db.sources._base import ImportReport, ScopeKey

LIMITE_BYTES = 25 * 1024 * 1024
"""Teto do arquivo comprimido baixado nos recortes didáticos."""

_NOME_PROJETO = 'name = "omnisus-db"'


def _checkout_raiz() -> Path | None:
    """Raiz do repositório se o cwd estiver dentro de um checkout do omnisus-db."""
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        marker = candidate / "pyproject.toml"
        if not marker.is_file():
            continue
        try:
            texto = marker.read_text(encoding="utf-8")
        except OSError:
            continue
        if _NOME_PROJETO in texto and (candidate / "notebooks" / "bases").is_dir():
            return candidate
    return None


def raiz_dados() -> Path:
    """Pasta do lake de pesquisa compartilhado; `OMNISUS_NOTEBOOK_DATA` a substitui.

    No checkout, é ``data/lake/pesquisa`` na raiz do repositório. Fora dele
    (molab, sandbox), é ``data/lake/pesquisa`` relativo ao diretório de trabalho.
    """
    if env := os.environ.get("OMNISUS_NOTEBOOK_DATA"):
        return Path(env)
    checkout = _checkout_raiz()
    if checkout is not None:
        return checkout / "data/lake/pesquisa"
    return Path.cwd() / "data/lake/pesquisa"


def target_padrao() -> str:
    return f"ducklake:{raiz_dados() / 'dados.ducklake'}"


def executar_sem_botoes(cli_args: Mapping[str, object]) -> bool:
    """`-- --executar true` percorre as etapas dos botões sem interface.

    Vale para `marimo export html ...` ou `python notebook.py`; em `marimo edit`
    os argumentos de CLI não chegam à célula e as etapas seguem os botões.
    """
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
        "omnisus_db": __version__,
        "fixado_em_utc": agora.isoformat(),
    }
    salvar_json(pasta / "plano.json", plano)
    return plano, pasta


def desfechos(relatorio: ImportReport) -> list[dict[str, Any]]:
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
    relatorio: ImportReport,
    nao_resolvidos: Iterable[tuple[int, ScopeKey]] = (),
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


def filtro_escopo(escopo: ScopeKey) -> tuple[str, list[object]]:
    """`WHERE` que seleciona as linhas de um escopo, nas colunas que a biblioteca grava."""
    campos = scope_fields(escopo)
    return " AND ".join(f'"{nome}" = ?' for nome in campos), list(campos.values())


def conferir(
    leitor: LakeReader, dataset: str, escopos: Sequence[ScopeKey]
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
    consultas: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Grava `proveniencia.json`: o suficiente para citar e refazer o resultado.

    `consultas` mapeia cada nome a `{"sql": str, "parametros": list}`: o texto exato
    executado e os parâmetros posicionais dessa execução, para que a consulta possa
    ser refeita sem adivinhar com que UF, ano ou mês ela rodou.
    """
    for nome, consulta in consultas.items():
        if (
            not isinstance(consulta, Mapping)
            or "sql" not in consulta
            or "parametros" not in consulta
        ):
            raise ValueError(f"consulta {nome!r} precisa de 'sql' e 'parametros' para ser refeita")
    registro = {
        "plano": dict(plano),
        "publicacoes": [dict(p) for p in publicacoes],
        "snapshot_id": snapshot_id,
        "consultas": {
            nome: {"sql": consulta["sql"], "parametros": list(consulta["parametros"])}
            for nome, consulta in consultas.items()
        },
        "omnisus_db": __version__,
        "gerado_em_utc": datetime.now(UTC).isoformat(),
    }
    salvar_json(pasta / "proveniencia.json", registro)
    return registro

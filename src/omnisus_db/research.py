"""Helpers for citing a lake snapshot and importing without duplicating research rows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlparse

from omnisus_db._version import __version__
from omnisus_db.lake import DEFAULT_TARGET, Lake, LakeReader
from omnisus_db.lake.publication import ImportPolicy
from omnisus_db.lake.sql import qualified, quote_identifier
from omnisus_db.sources._base import ImportReport, ScopeKey
from omnisus_db.sources.datasus_ftp._runner import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CONCURRENCY,
)
from omnisus_db.sources.datasus_ftp.datasets import Dataset
from omnisus_db.sources.datasus_ftp.fetch import (
    DEFAULT_MAX_INFLIGHT_BYTES,
    DEFAULT_MAX_PAYLOAD_BYTES,
)
from omnisus_db.transforms.dictionaries import load_dicionario


@dataclass(frozen=True)
class Citation:
    """Structured citation plus the Portuguese paragraph the guide uses."""

    text: str
    snapshot_id: int
    omnisus_db: str
    dataset: str | None
    run_id: str | None
    publications: tuple[dict[str, Any], ...]


def latest_snapshot_id(lake: Lake | LakeReader) -> int:
    """The newest catalog snapshot; raises if the lake has no history yet."""
    snaps = lake.snapshots()
    if not snaps:
        raise LookupError("lake has no snapshots")
    raw = snaps[-1]["snapshot_id"]
    if type(raw) is not int:
        raise TypeError(f"snapshot_id must be int, got {type(raw).__name__}")
    return raw


def import_research(
    dataset: str | Dataset,
    *,
    scopes: Sequence[ScopeKey],
    run_id: str,
    target: str = DEFAULT_TARGET,
    concurrency: int = DEFAULT_CONCURRENCY,
    batch_size: int = DEFAULT_BATCH_SIZE,
    policy: ImportPolicy = "skip_same",
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
    max_inflight_bytes: int = DEFAULT_MAX_INFLIGHT_BYTES,
) -> ImportReport:
    """Import for a citable run: ``skip_same`` by default, ``run_id`` required.

    Refuses ``policy="append"``. Use :func:`~omnisus_db.import_dataset` for the
    operator default that duplicates on retry.
    """
    from omnisus_db import import_dataset

    if not str(run_id).strip():
        raise ValueError("import_research requires a nonempty run_id")
    if policy == "append":
        raise ValueError(
            "import_research refuses policy='append'; use import_dataset or policy='replace'"
        )
    return import_dataset(
        dataset,
        scopes=scopes,
        target=target,
        concurrency=concurrency,
        batch_size=batch_size,
        policy=policy,
        run_id=run_id,
        max_payload_bytes=max_payload_bytes,
        max_inflight_bytes=max_inflight_bytes,
    )


def municipality_join_key(value: object, *, digits: int = 6) -> str | None:
    """Leftmost IBGE municipality digits; does not pad or invent a check digit."""
    _require_join_digits(digits)
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:digits]


def municipality_join_key_sql(column: str, *, digits: int = 6) -> str:
    """SQL equivalent of :func:`municipality_join_key` on a stored column."""
    _require_join_digits(digits)
    ident = quote_identifier(column)
    return f"left(trim(CAST({ident} AS VARCHAR)), {digits})"


def citation_from_publications(
    publications: Sequence[Mapping[str, Any]],
    *,
    snapshot_id: int,
    dataset: str | None = None,
    run_id: str | None = None,
    accessed: date | None = None,
) -> Citation:
    """Format already-loaded publication rows (notebooks keep them in JSON)."""
    accessed_on = accessed or datetime.now(UTC).date()
    rows = [dict(row) for row in publications]
    if dataset:
        for row in rows:
            row.setdefault("dataset", dataset)
    if dataset == "ibge_populacao" or (rows and "url" in rows[0] and "source_uri" not in rows[0]):
        paragraphs = [_ibge_paragraph(row, snapshot_id, accessed_on) for row in rows]
    else:
        paragraphs = [_ftp_paragraph(row, snapshot_id, accessed_on, run_id) for row in rows]
    if not paragraphs:
        paragraphs = [
            (
                f"Nenhuma publicação ativa encontrada"
                f"{f' para {dataset}' if dataset else ''}. "
                f"Importado com omnisus-db {__version__}, lake snapshot {snapshot_id}"
                f"{f', execução {run_id}' if run_id else ''}."
            )
        ]
    return Citation(
        text="\n\n".join(paragraphs),
        snapshot_id=snapshot_id,
        omnisus_db=__version__,
        dataset=dataset,
        run_id=run_id,
        publications=tuple(rows),
    )


def cite(
    lake: Lake | LakeReader,
    *,
    dataset: str | None = None,
    snapshot_id: int | None = None,
    run_id: str | None = None,
    accessed: date | None = None,
) -> Citation:
    """Build the Portuguese citation from publications on this handle."""
    pinned = latest_snapshot_id(lake) if snapshot_id is None else snapshot_id
    if dataset == "ibge_populacao":
        rows = _ibge_manifest(lake)
    else:
        rows = [
            row
            for row in lake.publications(run_id=run_id)
            if row.get("active", True) and (dataset is None or row.get("dataset") == dataset)
        ]
    return citation_from_publications(
        rows,
        snapshot_id=pinned,
        dataset=dataset,
        run_id=run_id,
        accessed=accessed,
    )


def _require_join_digits(digits: int) -> None:
    if digits not in (6, 7):
        raise ValueError("digits must be 6 or 7")


def _filename(uri: str | None) -> str:
    if not uri:
        return "(arquivo desconhecido)"
    path = urlparse(uri).path or uri
    name = path.rsplit("/", 1)[-1]
    return name or uri


def _title(dataset: str) -> str:
    try:
        return load_dicionario(dataset).title
    except Exception:
        return dataset


def _ftp_paragraph(
    row: Mapping[str, Any], snapshot_id: int, accessed_on: date, run_id: str | None
) -> str:
    dataset = str(row.get("dataset") or "(dataset desconhecido)")
    uri = row.get("source_uri")
    sha = row.get("source_sha256") or "(SHA-256 desconhecido)"
    execucao = run_id or row.get("run_id") or "(run_id desconhecido)"
    titulo = _title(dataset) if row.get("dataset") else dataset
    return (
        f"{titulo} ({dataset}), arquivo {_filename(uri)} ({uri}), "
        f"SHA-256 {sha}, acessado em {accessed_on.isoformat()} pelo DATASUS. "
        f"Importado com omnisus-db {__version__}, lake snapshot {snapshot_id}, "
        f"execução {execucao}."
    )


def _ibge_paragraph(row: Mapping[str, Any], snapshot_id: int, accessed_on: date) -> str:
    url = row.get("url") or "(URL desconhecida)"
    sha = row.get("sha256") or "(SHA-256 desconhecido)"
    execucao = row.get("publication_id") or "(publication_id desconhecido)"
    return (
        f"IBGE · população (ibge_populacao), URL {url}, SHA-256 {sha}, "
        f"acessado em {accessed_on.isoformat()}. Importado com omnisus-db {__version__}, "
        f"lake snapshot {snapshot_id}, execução {execucao}."
    )


def _ibge_manifest(lake: Lake | LakeReader) -> list[dict[str, Any]]:
    tables = lake.tables()
    if "ibge_population_manifest" not in tables:
        return []
    rows = (
        lake.connect()
        .execute(
            f"SELECT publication_id, product, ano, sha256, url, collected_at "
            f"FROM {qualified(lake.alias, 'ibge_population_manifest')}"
        )
        .to_arrow_table()
        .to_pylist()
    )
    return list(rows)

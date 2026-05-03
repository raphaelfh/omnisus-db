"""Source / Dataset / Importer protocols and base types."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pyarrow as pa


@dataclass(frozen=True)
class ScopeKey:
    """Identifies one slice of a dataset (e.g., SP/2024 or MG/2024/01).

    `mes` is None for yearly datasets, set for monthly (SIH).
    """

    uf: str
    ano: int
    mes: int | None = None

    def __str__(self) -> str:
        if self.mes is None:
            return f"{self.uf}_{self.ano}"
        return f"{self.uf}_{self.ano}_{self.mes:02d}"


@dataclass(frozen=True)
class Dataset:
    """Immutable description of a dataset (e.g., SIM-DO)."""

    family: str
    name: str
    canonical_schema: pa.Schema
    partition_by: tuple[str, ...]
    dictionary_path: Path


@dataclass
class ImportResult:
    """Outcome of one import_scope call."""

    rows: int
    bytes_written: int
    duration_seconds: float
    snapshot_id: int | None = None


class Source(Protocol):
    """Protocol for a source family (DATASUS-FTP, IBGE, CNES)."""

    name: str

    async def list_available(self, dataset: str) -> list[ScopeKey]: ...
    async def fetch_bytes(self, dataset: str, scope: ScopeKey) -> bytes: ...

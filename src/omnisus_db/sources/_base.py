"""Shared value types for source families: scopes, results and reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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


@dataclass
class ImportResult:
    """Outcome of one import_scope call."""

    rows: int
    bytes_written: int
    duration_seconds: float
    snapshot_id: int | None = None


ScopeStatus = Literal["ok", "skipped", "failed"]


@dataclass(frozen=True)
class ScopeOutcome:
    """What happened to one scope in an import run.

    ``skipped`` and ``failed`` are different facts and must not be collapsed.
    A scope DATASUS never published is ``skipped`` — a normal, expected
    outcome of asking for a range. A scope that exists but could not be
    retrieved or ingested is ``failed``, and is worth retrying.
    """

    scope: ScopeKey
    status: ScopeStatus
    result: ImportResult | None = None
    """Set when ``status == "ok"``, ``None`` otherwise."""

    reason: str | None = None
    """Set when ``status`` is ``skipped`` or ``failed``, ``None`` otherwise."""


@dataclass(frozen=True)
class ImportReport:
    """Per-scope outcomes of one import run.

    A wide import reports what happened instead of dying on scope 3, so
    partial progress is visible and resumable.

    Inspect :attr:`failed` — never the report's truthiness. An empty run and a
    run where everything failed are different facts, and no falsy sentinel
    stands in for either (spec I6).
    """

    outcomes: tuple[ScopeOutcome, ...]

    @property
    def rows(self) -> int:
        """Total rows ingested across successful scopes."""
        return sum(o.result.rows for o in self.outcomes if o.result is not None)

    @property
    def ok(self) -> tuple[ScopeOutcome, ...]:
        return tuple(o for o in self.outcomes if o.status == "ok")

    @property
    def skipped(self) -> tuple[ScopeOutcome, ...]:
        return tuple(o for o in self.outcomes if o.status == "skipped")

    @property
    def failed(self) -> tuple[ScopeOutcome, ...]:
        return tuple(o for o in self.outcomes if o.status == "failed")

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
    run_id: str | None = None
    batch_id: str | None = None
    publication_id: str | None = None


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

    Normal FTP completion reports each requested input position. An
    ImportAbortedError carries a partial report of determined outcomes and
    separately identifies unresolved positions; inspect before retrying.

    Inspect :attr:`failed` — never the report's truthiness. An empty run and a
    run where everything failed are different facts, and no falsy sentinel
    stands in for either (spec I6).
    """

    outcomes: tuple[ScopeOutcome, ...]
    run_id: str | None = None

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


class ImportAbortedError(RuntimeError):
    """Partial progress is known, but the remaining inputs need inspection."""

    def __init__(
        self,
        report: ImportReport,
        unresolved: tuple[tuple[int, ScopeKey], ...],
    ) -> None:
        self.report = report
        self.unresolved = unresolved
        super().__init__(
            f"import aborted: {len(unresolved)} input(s) unresolved; inspect before retry"
        )

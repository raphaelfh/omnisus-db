"""Generic DATASUS-FTP pipeline (per spec §11.1 hybrid pattern).

Per-dataset modules (e.g. cnes/importers/st.py) wrap this when they need
extra behaviour. For datasets with no special behaviour the generic runner
is the whole importer.
"""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl
import structlog

from omnisus_db.lake import Lake
from omnisus_db.sources._base import (
    ImportReport,
    ImportResult,
    ScopeKey,
    ScopeOutcome,
)
from omnisus_db.sources.datasus_ftp.datasets import Dataset, in_coverage, resolve
from omnisus_db.sources.datasus_ftp.fetch import FtpFileNotFound, fetch_dbc_bytes
from omnisus_db.sources.datasus_ftp.parse import dbc_bytes_to_lazyframe

logger = structlog.get_logger(__name__)


async def import_scope(
    *,
    dataset: str | Dataset,
    scope: ScopeKey,
    lake: Lake,
) -> ImportResult:
    """Fetch + parse + sink one (dataset, scope) into the lake.

    ``dataset`` is a registry key, an alias, or a ``Dataset`` value. The
    value form is the open door of spec I3: an uncurated dataset with its
    own ``dictionary`` flows through exactly this path.
    """
    d = resolve(dataset)
    if d.monthly and scope.mes is None:
        raise ValueError(f"{d.name} is monthly; ScopeKey.mes is required")

    logger.info("import_scope.start", dataset=d.name, scope=str(scope))
    raw = await fetch_dbc_bytes(dataset=d, scope=scope)
    lf = dbc_bytes_to_lazyframe(
        raw, dataset=d.name, ano=scope.ano, uf=scope.uf, dictionary=d.dictionary
    )
    if d.monthly:
        lf = lf.with_columns(pl.lit(scope.mes).cast(pl.UInt8).alias("mes"))
    result = lake.ingest(d.name, lf, partition_by=d.partition_by)
    logger.info(
        "import_scope.done",
        dataset=d.name,
        scope=str(scope),
        rows=result.rows,
        snapshot_id=result.snapshot_id,
    )
    return result


def _require_well_formed(d: Dataset, scopes: Sequence[ScopeKey]) -> None:
    """Reject malformed scopes before the run starts, not during it.

    A monthly dataset asked for without a month is a caller bug, not an
    upstream condition, and it affects every scope equally — so it fails fast
    and loudly rather than becoming 700 identical ``failed`` outcomes that
    look like a server problem.
    """
    if not d.monthly:
        return
    bad = [s for s in scopes if s.mes is None]
    if bad:
        raise ValueError(
            f"{d.name} is monthly; ScopeKey.mes is required "
            f"({len(bad)} scope(s) without one, e.g. {bad[0]})"
        )


async def run_scopes(
    dataset: str | Dataset,
    *,
    scopes: Sequence[ScopeKey],
    lake: Lake,
) -> ImportReport:
    """Import many scopes, reporting per-scope outcomes instead of aborting.

    A wide import spans years DATASUS never published for a given UF. Before
    this, the first such gap raised and discarded every result already
    collected — including scopes whose rows were already committed — so a
    702-scope run died on scope 3 with no partial results and no resume.

    Two filters, cheapest first:

    1. ``coverage`` rejects scopes outside the dataset's declared window with
       no socket opened at all.
    2. A 550 from the server marks the scope ``skipped``. Anything else that
       exhausts its retry budget is ``failed`` and worth retrying.
    """
    d = resolve(dataset)
    _require_well_formed(d, scopes)

    outcomes: list[ScopeOutcome] = []
    for scope in scopes:
        if not in_coverage(d, scope):
            first, last = d.coverage
            outcomes.append(
                ScopeOutcome(
                    scope=scope,
                    status="skipped",
                    reason=f"outside declared coverage {first}..{last or 'ongoing'}",
                )
            )
            continue
        try:
            result = await import_scope(dataset=d, scope=scope, lake=lake)
        except FtpFileNotFound as exc:
            logger.info("run_scopes.skipped", dataset=d.name, scope=str(scope), reason=str(exc))
            outcomes.append(ScopeOutcome(scope=scope, status="skipped", reason=str(exc)))
        # Deliberately broad: a failure belongs to its scope, not to the run.
        # Narrowing here would let an unforeseen error abort the other 700.
        except Exception as exc:
            logger.warning("run_scopes.failed", dataset=d.name, scope=str(scope), error=str(exc))
            outcomes.append(ScopeOutcome(scope=scope, status="failed", reason=str(exc)))
        else:
            outcomes.append(ScopeOutcome(scope=scope, status="ok", result=result))

    report = ImportReport(outcomes=tuple(outcomes))
    logger.info(
        "run_scopes.done",
        dataset=d.name,
        ok=len(report.ok),
        skipped=len(report.skipped),
        failed=len(report.failed),
        rows=report.rows,
    )
    return report

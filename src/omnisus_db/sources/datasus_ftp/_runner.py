"""Generic DATASUS-FTP pipeline (per spec §11.1 hybrid pattern).

Per-dataset modules (e.g. cnes/importers/st.py) wrap this when they need
extra behaviour. For datasets with no special behaviour the generic runner
is the whole importer.
"""

from __future__ import annotations

import asyncio
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

_Fetched = tuple[int, ScopeKey, bytes | None, BaseException | None]
"""One fetched scope on its way to the consumer: exactly one of the payload
and the error is set."""

DEFAULT_CONCURRENCY = 6
"""Fetches in flight. DATASUS FTP is a shared public resource: this is
deliberately not "as fast as the network allows". Whether the server enforces
a per-IP connection limit is not known, so 6 stays below what comparable tools
run without reported trouble."""

DEFAULT_BATCH_SIZE = 24
"""Scopes per DuckLake transaction. One snapshot per scope meant 648 snapshots
and 648 small files for a wide SIH import. Batching trades atomicity
granularity for commit count: a failure mid-batch loses that batch's
uncommitted scopes, never the run, and they are reported failed and safe to
retry. ``batch_size=1`` restores per-scope atomicity."""


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
    result = ingest_raw(d, scope, raw, lake)
    logger.info(
        "import_scope.done",
        dataset=d.name,
        scope=str(scope),
        rows=result.rows,
        snapshot_id=result.snapshot_id,
    )
    return result


def ingest_raw(d: Dataset, scope: ScopeKey, raw: bytes, lake: Lake) -> ImportResult:
    """Parse fetched bytes and sink them. The consumer half of the pipeline.

    Synchronous on purpose: :class:`Lake` holds one DuckDB connection, which
    is not safe for concurrent use, and Polars already saturates cores inside
    a single parse. Parallelism belongs to fetch only (spec §5.2).
    """
    lf = dbc_bytes_to_lazyframe(
        raw, dataset=d.name, ano=scope.ano, uf=scope.uf, dictionary=d.dictionary
    )
    if d.monthly:
        lf = lf.with_columns(pl.lit(scope.mes).cast(pl.UInt8).alias("mes"))
    return lake.ingest(d.name, lf, partition_by=d.partition_by)


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
    concurrency: int = DEFAULT_CONCURRENCY,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> ImportReport:
    """Import many scopes, reporting per-scope outcomes instead of aborting.

    A wide import spans years DATASUS never published for a given UF. Before
    tolerance, the first such gap raised and discarded every result already
    collected — including scopes whose rows were already committed — so a
    702-scope run died on scope 3 with no partial results and no resume.

    Two filters keep work off the wire, cheapest first:

    1. ``coverage`` rejects scopes outside the dataset's declared window with
       no socket opened at all.
    2. A 550 from the server marks the scope ``skipped``. Anything else that
       exhausts its retry budget is ``failed`` and worth retrying.

    Shape: ``concurrency`` fetches in flight, **one** consumer parsing and
    sinking, with commits every ``batch_size`` scopes. Fetch and parse used to
    be fully serialized — connect, RETR, parse, insert, one at a time — so
    wall clock was ``sum(fetch) + sum(parse+sink)``.

    Memory is bounded by the queue, not just by ``concurrency``: a producer
    holds its slot until its payload is queued, so at most about
    ``2 * concurrency`` payloads are resident. Without that, every completed
    fetch would sit in memory waiting for the consumer, and a national-scale
    scope is hundreds of megabytes.
    """
    d = resolve(dataset)
    _require_well_formed(d, scopes)
    if concurrency < 1:
        raise ValueError(f"concurrency must be >= 1; got {concurrency}")
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1; got {batch_size}")

    outcomes: dict[int, ScopeOutcome] = {}
    queued: list[tuple[int, ScopeKey]] = []
    for index, scope in enumerate(scopes):
        if in_coverage(d, scope):
            queued.append((index, scope))
            continue
        first, last = d.coverage
        outcomes[index] = ScopeOutcome(
            scope=scope,
            status="skipped",
            reason=f"outside declared coverage {first}..{last or 'ongoing'}",
        )

    queue: asyncio.Queue[_Fetched | None] = asyncio.Queue(maxsize=concurrency)
    sem = asyncio.Semaphore(concurrency)

    async def produce(index: int, scope: ScopeKey) -> None:
        # The slot is held until the payload is queued, so completed fetches
        # cannot accumulate ahead of the consumer.
        async with sem:
            try:
                raw = await fetch_dbc_bytes(dataset=d, scope=scope)
            except Exception as exc:
                await queue.put((index, scope, None, exc))
            else:
                await queue.put((index, scope, raw, None))

    async def produce_all() -> None:
        try:
            await asyncio.gather(*(produce(i, s) for i, s in queued))
        finally:
            await queue.put(None)

    producer = asyncio.create_task(produce_all())
    try:
        exhausted = False
        while not exhausted:
            batch: dict[int, ScopeOutcome] = {}
            try:
                with lake.transaction():
                    while len(batch) < batch_size:
                        item = await queue.get()
                        if item is None:
                            exhausted = True
                            break
                        index, scope, raw, exc = item
                        if exc is not None:
                            batch[index] = _outcome_for_error(d, scope, exc)
                            continue
                        assert raw is not None, "raw is set whenever exc is None"
                        result = ingest_raw(d, scope, raw, lake)
                        batch[index] = ScopeOutcome(scope=scope, status="ok", result=result)
            except Exception as exc:
                # The batch rolled back, so nothing in it is committed. A scope
                # is only ``ok`` once its batch commits (spec §5.2).
                logger.warning("run_scopes.batch_failed", dataset=d.name, error=str(exc))
                for index, outcome in batch.items():
                    outcomes[index] = (
                        outcome
                        if outcome.status != "ok"
                        else ScopeOutcome(
                            scope=outcome.scope,
                            status="failed",
                            reason=f"batch rolled back: {exc}",
                        )
                    )
            else:
                outcomes.update(batch)
    finally:
        producer.cancel()
        await asyncio.gather(producer, return_exceptions=True)

    report = ImportReport(outcomes=tuple(outcomes[i] for i in sorted(outcomes)))
    logger.info(
        "run_scopes.done",
        dataset=d.name,
        ok=len(report.ok),
        skipped=len(report.skipped),
        failed=len(report.failed),
        rows=report.rows,
    )
    return report


def _outcome_for_error(d: Dataset, scope: ScopeKey, exc: BaseException) -> ScopeOutcome:
    """A missing file is a skip; everything else is a failure."""
    if isinstance(exc, FtpFileNotFound):
        logger.info("run_scopes.skipped", dataset=d.name, scope=str(scope), reason=str(exc))
        return ScopeOutcome(scope=scope, status="skipped", reason=str(exc))
    logger.warning("run_scopes.failed", dataset=d.name, scope=str(scope), error=str(exc))
    return ScopeOutcome(scope=scope, status="failed", reason=str(exc))

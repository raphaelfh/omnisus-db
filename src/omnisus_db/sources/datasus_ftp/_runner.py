"""Generic DATASUS-FTP pipeline (per spec §11.1 hybrid pattern).

Per-dataset modules (e.g. cnes/importers/st.py) wrap this when they need
extra behaviour. For datasets with no special behaviour the generic runner
is the whole importer.
"""

from __future__ import annotations

import asyncio
import hashlib
import tempfile
from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path
from uuid import uuid4

import structlog

from omnisus_db.lake import Lake
from omnisus_db.lake._transactions import TransactionStateError
from omnisus_db.lake.publication import ImportPolicy, validate_policy
from omnisus_db.sources._base import (
    ImportAbortedError,
    ImportReport,
    ImportResult,
    ScopeKey,
    ScopeOutcome,
)
from omnisus_db.sources.datasus_ftp.datasets import Dataset, in_coverage, resolve
from omnisus_db.sources.datasus_ftp.fetch import (
    DEFAULT_MAX_INFLIGHT_BYTES,
    DEFAULT_MAX_PAYLOAD_BYTES,
    FtpFileNotFound,
    download_limit,
    fetch_dbc_bytes,
)

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


class _ProducerStoppedError(RuntimeError):
    """The producer exited without completing the input stream."""


async def _next_fetched(
    queue: asyncio.Queue[_Fetched | None],
    producer: asyncio.Task[None],
) -> _Fetched | None:
    """Wait for either the next item or abnormal producer termination."""
    waiting = asyncio.create_task(queue.get())
    try:
        done, _ = await asyncio.wait({waiting, producer}, return_when=asyncio.FIRST_COMPLETED)
        if waiting in done:
            return waiting.result()
        if producer.cancelled():
            raise _ProducerStoppedError("producer cancelled")
        error = producer.exception()
        if error is not None:
            raise _ProducerStoppedError("producer failed") from error
        return await waiting
    finally:
        if not waiting.done():
            waiting.cancel()
        await asyncio.gather(waiting, return_exceptions=True)


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
    assert result is not None, "append always publishes"
    logger.info(
        "import_scope.done",
        dataset=d.name,
        scope=str(scope),
        rows=result.rows,
        snapshot_id=result.snapshot_id,
    )
    return result


def ingest_raw(
    d: Dataset,
    scope: ScopeKey,
    raw: bytes,
    lake: Lake,
    *,
    policy: ImportPolicy = "append",
    run_id: str | None = None,
    batch_id: str | None = None,
) -> ImportResult | None:
    """Validate to staging, then publish one source version atomically."""
    from omnisus_db.sources.datasus_ftp.dbf_contract import publication_parser_version
    from omnisus_db.sources.datasus_ftp.staging import dbc_bytes_to_parquet

    with tempfile.TemporaryDirectory(prefix="omnisus-source-") as tmp:
        staging = Path(tmp) / "scope.parquet"
        dbc_bytes_to_parquet(
            raw,
            staging,
            dataset=d.name,
            ano=scope.ano,
            uf=scope.uf,
            dictionary=d.dictionary,
            mes=scope.mes if d.monthly else None,
        )
        dictionary_hash = hashlib.sha256(
            d.dictionary.read_bytes()
            if d.dictionary is not None
            else files("omnisus_db.data.dicionarios").joinpath(d.name + ".yaml").read_bytes()
        ).hexdigest()
        return lake.publish_scope(
            d.name,
            staging,
            scope=scope,
            source_sha256=hashlib.sha256(raw).hexdigest(),
            parser_version=publication_parser_version(dictionary_hash),
            policy=policy,
            run_id=run_id,
            batch_id=batch_id,
            partition_by=d.partition_by,
        )


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
    policy: ImportPolicy = "append",
    run_id: str | None = None,
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
    max_inflight_bytes: int = DEFAULT_MAX_INFLIGHT_BYTES,
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

    Each producer reserves ``max_payload_bytes`` before fetching and holds
    that reservation until the consumer releases the compressed payload.
    At most ``max_inflight_bytes // max_payload_bytes`` payloads can occupy
    the pipeline. The fetcher enforces the per-file cap during receipt. This
    is not a total RSS limit: decompressed DBF and parsing memory are additional.
    """
    if lake.in_transaction:
        raise RuntimeError("run_scopes cannot run inside an existing Lake.transaction")
    d = resolve(dataset)
    _require_well_formed(d, scopes)
    validate_policy(policy)
    run_id = run_id or str(uuid4())
    if type(max_payload_bytes) is not int or max_payload_bytes < 1:
        raise ValueError("max_payload_bytes must be a positive integer")
    if type(max_inflight_bytes) is not int or max_inflight_bytes < max_payload_bytes:
        raise ValueError(
            "max_inflight_bytes must cover at least one max_payload_bytes reservation"
        )
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

    # Reserve the full permitted payload BEFORE starting a download. This
    # avoids partial-download deadlocks and covers completed queued payloads.
    byte_slots = asyncio.Semaphore(max_inflight_bytes // max_payload_bytes)
    held: set[int] = set()

    def release(index: int) -> None:
        if index in held:
            held.remove(index)
            byte_slots.release()

    async def produce(index: int, scope: ScopeKey) -> None:
        async with sem:
            await byte_slots.acquire()
            held.add(index)
            enqueued = False
            try:
                try:
                    with download_limit(max_payload_bytes):
                        raw = await fetch_dbc_bytes(dataset=d, scope=scope)
                    if len(raw) > max_payload_bytes:
                        del raw
                        raise ValueError("download exceeds payload bytes limit")
                except Exception as exc:
                    release(index)
                    await queue.put((index, scope, None, exc))
                else:
                    await queue.put((index, scope, raw, None))
                    enqueued = True
            finally:
                if not enqueued:
                    release(index)

    async def produce_all() -> None:
        tasks = [asyncio.create_task(produce(i, s)) for i, s in queued]
        try:
            await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        await queue.put(None)

    producer = asyncio.create_task(produce_all())
    try:
        exhausted = False
        while not exhausted:
            batch: dict[int, ScopeOutcome] = {}
            batch_id = str(uuid4())
            writing: set[int] = set()
            pending_skips: set[int] = set()
            try:
                with lake.transaction():
                    while len(batch) < batch_size:
                        item = await _next_fetched(queue, producer)
                        if item is None:
                            exhausted = True
                            break
                        index, scope, raw, exc = item
                        if exc is not None:
                            batch[index] = _outcome_for_error(d, scope, exc)
                            continue
                        assert raw is not None, "raw is set whenever exc is None"
                        writing.add(index)
                        batch[index] = ScopeOutcome(
                            scope=scope,
                            status="failed",
                            reason="ingestion did not complete",
                        )
                        try:
                            result = ingest_raw(
                                d,
                                scope,
                                raw,
                                lake,
                                policy=policy,
                                run_id=run_id,
                                batch_id=batch_id,
                            )
                        except TransactionStateError:
                            batch.pop(index, None)
                            raise
                        except Exception as exc:
                            batch[index] = ScopeOutcome(
                                scope=scope, status="failed", reason=str(exc)
                            )
                            raise
                        finally:
                            raw = None
                            item = None
                            release(index)
                        if result is None:
                            if any(o.scope == scope and o.status == "ok" for o in batch.values()):
                                pending_skips.add(index)
                            else:
                                writing.discard(index)
                            batch[index] = ScopeOutcome(
                                scope=scope,
                                status="skipped",
                                reason="same source and parser version already published",
                            )
                        else:
                            batch[index] = ScopeOutcome(scope=scope, status="ok", result=result)
            except Exception as exc:
                if (
                    isinstance(exc, (TransactionStateError, _ProducerStoppedError))
                    or not lake.is_usable
                ):
                    rollback_known = not isinstance(exc, TransactionStateError) and lake.is_usable
                    determined = dict(outcomes)
                    for i, outcome in batch.items():
                        if i in writing and not rollback_known:
                            continue
                        determined[i] = (
                            outcome
                            if outcome.status != "ok" and i not in pending_skips
                            else ScopeOutcome(
                                scope=outcome.scope,
                                status="failed",
                                reason=f"batch rolled back: {exc}",
                            )
                        )
                    partial = ImportReport(
                        tuple(determined[i] for i in sorted(determined)), run_id=run_id
                    )
                    unresolved = tuple(
                        (i, scope) for i, scope in enumerate(scopes) if i not in determined
                    )
                    raise ImportAbortedError(partial, unresolved) from exc

                logger.warning("run_scopes.batch_failed", dataset=d.name, error=str(exc))
                for index, outcome in batch.items():
                    outcomes[index] = (
                        outcome
                        if outcome.status != "ok" and index not in pending_skips
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
        while not queue.empty():
            queue.get_nowait()
        for index in tuple(held):
            release(index)

    report = ImportReport(outcomes=tuple(outcomes[i] for i in sorted(outcomes)), run_id=run_id)
    from omnisus_db.lake.publication import record_failed_attempts

    try:
        record_failed_attempts(lake, report)
    except Exception as exc:
        # Scope outcomes are still determined; only the durable audit write
        # requires inspection. Never turn already committed data into failure.
        raise ImportAbortedError(report, ()) from exc
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

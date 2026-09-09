"""CNES Master importer — fetches establishment names from the public API.

The public CNES-ST DBF distributed by DATASUS doesn't carry the establishment
name; that lives only in the CNES web service. This importer fetches names
from ``https://apidadosabertos.saude.gov.br/cnes/estabelecimentos/{cnes}`` and
upserts them into ``lake.cnes_master``.

Typical workflow:

1. ``import_cnes_st(...)`` populates ``lake.cnes_st`` (operational, FTP).
2. ``import_cnes_master()`` fetches names for every CNES present in cnes_st
   that isn't yet in cnes_master.
3. ``aux_cnes`` view auto-refreshes; explorer lookups now resolve names.

Re-runs are incremental by default (``only_missing=True``): codes already
in ``cnes_master`` are skipped, so periodic top-ups are cheap.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence

import httpx
import structlog

from omnisus_db.lake import DEFAULT_TARGET, Lake

logger = structlog.get_logger(__name__)

API_URL = "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos/{cnes}"

# Type alias: callback receives (done, total) after each fetch completes.
ProgressCallback = Callable[[int, int], None]


async def _fetch_one(client: httpx.AsyncClient, cnes: str) -> dict | None:
    """Fetch a single CNES record. Returns None on any failure (404, network).

    The API uses *unpadded* integer paths — passing ``"0123456"`` 404s.
    Strip leading zeros before the request, but keep the canonical 7-digit
    form in the returned record so it joins cleanly against ``cnes_st``.
    """
    cnes_canonical = cnes.zfill(7)
    cnes_path = cnes_canonical.lstrip("0") or "0"
    try:
        r = await client.get(API_URL.format(cnes=cnes_path), timeout=30)
    except httpx.HTTPError:
        return None
    if r.status_code != 200:
        return None
    try:
        d = r.json()
    except ValueError:
        return None
    nome_fantasia = (d.get("nome_fantasia") or "").strip()
    razao_social = (d.get("nome_razao_social") or "").strip()
    return {
        "cnes": cnes_canonical,
        "nome": nome_fantasia or razao_social or None,
        "nome_fantasia": nome_fantasia or None,
        "razao_social": razao_social or None,
    }


async def _fetch_all(
    codes: Sequence[str],
    *,
    concurrency: int,
    progress: ProgressCallback | None,
) -> list[dict]:
    """Fetch every code with bounded concurrency, reporting progress as we go."""
    sem = asyncio.Semaphore(concurrency)
    total = len(codes)
    done = 0
    records: list[dict] = []

    async with httpx.AsyncClient() as client:

        async def worker(c: str) -> dict | None:
            async with sem:
                return await _fetch_one(client, c)

        tasks = [asyncio.create_task(worker(c)) for c in codes]
        for fut in asyncio.as_completed(tasks):
            result = await fut
            if result is not None and result["nome"] is not None:
                records.append(result)
            done += 1
            if progress is not None:
                progress(done, total)

    return records


def _codes_from_lake(lake: Lake, *, only_missing: bool) -> list[str]:
    """Pull distinct non-null CNES codes from ``lake.cnes_st``.

    If ``only_missing=True`` and ``cnes_master`` already exists, returns only
    the codes not yet in ``cnes_master`` — making re-runs incremental.
    """
    if "cnes_st" not in lake.tables():
        return []
    con = lake.connect()
    if only_missing and "cnes_master" in lake.tables():
        sql = (
            f"SELECT DISTINCT s.cnes FROM {lake.alias}.cnes_st s "
            f"LEFT JOIN {lake.alias}.cnes_master m USING (cnes) "
            f"WHERE s.cnes IS NOT NULL AND s.cnes <> '' AND m.cnes IS NULL"
        )
    else:
        sql = (
            f"SELECT DISTINCT cnes FROM {lake.alias}.cnes_st WHERE cnes IS NOT NULL AND cnes <> ''"
        )
    return [r[0] for r in con.execute(sql).fetchall()]


def _ensure_master_table(lake: Lake) -> None:
    """Create ``cnes_master`` if it doesn't exist yet (idempotent)."""
    lake.connect().execute(
        f"""
        CREATE TABLE IF NOT EXISTS {lake.alias}.cnes_master (
            cnes VARCHAR,
            nome VARCHAR,
            nome_fantasia VARCHAR,
            razao_social VARCHAR
        )
        """
    )


def _upsert_master(lake: Lake, records: list[dict]) -> None:
    """Upsert records into ``cnes_master`` — delete existing rows for the
    incoming CNES codes, then insert the new ones.

    DuckLake doesn't support PRIMARY KEY / ON CONFLICT, so this is the
    simplest atomic-ish upsert. Idempotent by construction.
    """
    if not records:
        return
    con = lake.connect()
    codes = [r["cnes"] for r in records]
    placeholders = ", ".join("?" for _ in codes)
    con.execute(
        f"DELETE FROM {lake.alias}.cnes_master WHERE cnes IN ({placeholders})",
        codes,
    )
    con.executemany(
        f"INSERT INTO {lake.alias}.cnes_master VALUES (?, ?, ?, ?)",
        [(r["cnes"], r["nome"], r["nome_fantasia"], r["razao_social"]) for r in records],
    )


def import_cnes_master(
    *,
    codes: Sequence[str] | None = None,
    target: str = DEFAULT_TARGET,
    concurrency: int = 5,
    only_missing: bool = True,
    progress: ProgressCallback | None = None,
) -> int:
    """Fetch establishment names from the CNES API and upsert ``lake.cnes_master``.

    Args:
        codes: explicit list of 7-digit CNES codes. If ``None`` (default),
            pulls codes from ``lake.cnes_st``.
        target: lake target string (same shape used by every other importer).
        concurrency: max concurrent API requests (default 5 to be polite).
        only_missing: when ``True`` (default), skip codes already in
            ``cnes_master`` — re-runs become incremental top-ups.
        progress: optional ``(done, total)`` callback fired after each fetch
            completes. Used by the backend to stream job progress to the UI.

    Returns the number of records written in this run. Refreshes ``aux_cnes``
    so the new names are immediately visible to consumers.
    """
    with Lake.local(target) as lake:
        _ensure_master_table(lake)

        if codes is None:
            codes = _codes_from_lake(lake, only_missing=only_missing)
        codes = list(codes)
        logger.info("cnes_master.start", codes=len(codes), only_missing=only_missing)

        records = asyncio.run(_fetch_all(codes, concurrency=concurrency, progress=progress))
        _upsert_master(lake, records)
        lake.ensure_aux_cnes_view()

        logger.info("cnes_master.done", fetched=len(records), requested=len(codes))
        return len(records)

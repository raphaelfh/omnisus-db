"""Async DBC fetcher for DATASUS FTP (HTTP mirror)."""

from __future__ import annotations

import asyncio

import httpx
import structlog

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.inventory import scope_to_filename

logger = structlog.get_logger(__name__)

_PATH: dict[str, str] = {
    "sim_do": "SIM/CID10/DORES",
    "sinasc_nv": "SINASC/NOV/DNRES",
    "sih_rd": "SIHSUS/200801_/Dados",
    "cnes_st": "CNES/200508_/Dados/ST",
}
_BASE = "http://datasus.saude.gov.br/dissemin/publicos"


def url_for(dataset: str, scope: ScopeKey) -> str:
    if dataset not in _PATH:
        raise ValueError(f"unknown dataset: {dataset}")
    return f"{_BASE}/{_PATH[dataset]}/{scope_to_filename(dataset, scope)}"


async def fetch_dbc_bytes(
    *,
    dataset: str,
    scope: ScopeKey,
    timeout_seconds: float = 120.0,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
) -> bytes:
    """Fetch DBC bytes for one scope, with exponential retry on 5xx/network."""
    url = url_for(dataset, scope)
    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        for attempt in range(max_retries):
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                logger.info(
                    "datasus_ftp.fetched",
                    dataset=dataset,
                    scope=str(scope),
                    bytes=len(resp.content),
                    attempt=attempt,
                )
                return resp.content
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code < 500:
                    raise
                if attempt + 1 < max_retries:
                    await asyncio.sleep(backoff_seconds * (2**attempt))
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt + 1 < max_retries:
                    await asyncio.sleep(backoff_seconds * (2**attempt))
    assert last_exc is not None
    raise last_exc

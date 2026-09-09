"""Async DBC fetcher for DATASUS via anonymous FTP."""

from __future__ import annotations

import asyncio
import contextlib
import ftplib
import io

import structlog

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import Dataset, resolve
from omnisus_db.sources.datasus_ftp.filenames import scope_to_filename

logger = structlog.get_logger(__name__)

FTP_HOST = "ftp.datasus.gov.br"


def ftp_path_for(dataset: str | Dataset, scope: ScopeKey) -> tuple[str, str]:
    """Return (remote_dir, filename) for the given dataset/scope.

    Both values derive from the registry row (spec §3.1); there is no
    separate path map to keep in sync.
    """
    d = resolve(dataset)
    return d.ftp_dir, scope_to_filename(d, scope)


def _blocking_fetch(remote_dir: str, filename: str, timeout_seconds: float) -> bytes:
    """Synchronous FTP fetch returning bytes. Run via asyncio.to_thread."""
    buf = io.BytesIO()
    with contextlib.closing(ftplib.FTP(FTP_HOST, timeout=timeout_seconds)) as ftp:
        ftp.login()  # anonymous
        ftp.cwd(remote_dir)
        ftp.retrbinary(f"RETR {filename}", buf.write)
    return buf.getvalue()


async def fetch_dbc_bytes(
    *,
    dataset: str | Dataset,
    scope: ScopeKey,
    timeout_seconds: float = 120.0,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
) -> bytes:
    """Fetch DBC bytes for one scope from DATASUS FTP, with exponential retry."""
    d = resolve(dataset)
    remote_dir, filename = ftp_path_for(d, scope)
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            data = await asyncio.to_thread(_blocking_fetch, remote_dir, filename, timeout_seconds)
            logger.info(
                "datasus_ftp.fetched",
                dataset=d.name,
                scope=str(scope),
                bytes=len(data),
                attempt=attempt,
            )
            return data
        except (*ftplib.all_errors, OSError, TimeoutError) as exc:
            last_exc = exc
            # Permanent error (550 file not found) — don't retry
            if isinstance(exc, ftplib.error_perm):
                raise
            if attempt + 1 < max_retries:
                await asyncio.sleep(backoff_seconds * (2**attempt))
    assert last_exc is not None
    raise last_exc

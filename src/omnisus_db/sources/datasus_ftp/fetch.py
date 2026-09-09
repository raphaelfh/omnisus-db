"""Async DBC fetcher for DATASUS via anonymous FTP."""

from __future__ import annotations

import asyncio
import contextlib
import ftplib
import io

import structlog

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp._ftp import (
    FTP_HOST,
    TRANSIENT_FTP_ERRORS,
    is_missing,
)
from omnisus_db.sources.datasus_ftp.datasets import Dataset, resolve
from omnisus_db.sources.datasus_ftp.filenames import scope_to_filename

logger = structlog.get_logger(__name__)


class FtpFileNotFound(Exception):  # noqa: N818
    """DATASUS does not publish this file (550). Terminal — never retried.

    Distinct from :class:`FtpUnavailable`: a scope that does not exist is a
    normal outcome of asking for a range and becomes a ``skipped``
    :class:`~omnisus_db.sources._base.ScopeOutcome`, while a scope that exists
    but could not be fetched is ``failed`` and worth retrying.
    """


class FtpUnavailable(Exception):  # noqa: N818
    """The file could not be fetched within the retry budget."""


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
    """Fetch DBC bytes for one scope from DATASUS FTP, with exponential retry.

    Raises:
        FtpFileNotFound: DATASUS does not publish this scope (550). Terminal.
        FtpUnavailable: transient failures exhausted ``max_retries``.

    Only a 550 is terminal. Every other ``ftplib.error_perm`` is retried,
    because ``error_perm`` is *any* 5xx and DATASUS answers ``530 maximum
    number of allowed clients`` when its anonymous-connection pool is full —
    which is a throttle, not a missing file. Treating the whole class as
    permanent made a busy server indistinguishable from an absent dataset.
    """
    d = resolve(dataset)
    remote_dir, filename = ftp_path_for(d, scope)
    last_exc: BaseException | None = None
    for attempt in range(max_retries):
        try:
            data = await asyncio.to_thread(_blocking_fetch, remote_dir, filename, timeout_seconds)
        except TRANSIENT_FTP_ERRORS as exc:
            if is_missing(exc):
                raise FtpFileNotFound(f"{remote_dir}/{filename}: {exc}") from exc
            last_exc = exc
            if attempt + 1 < max_retries:
                await asyncio.sleep(backoff_seconds * (2**attempt))
            continue
        logger.info(
            "datasus_ftp.fetched",
            dataset=d.name,
            scope=str(scope),
            bytes=len(data),
            attempt=attempt,
        )
        return data
    raise FtpUnavailable(f"{remote_dir}/{filename}: {max_retries} attempts failed") from last_exc

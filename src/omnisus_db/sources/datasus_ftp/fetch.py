"""Async DBC fetcher for DATASUS via anonymous FTP."""

from __future__ import annotations

import asyncio
import contextlib
import ftplib
import io
import socket
import threading
from contextvars import ContextVar

import structlog

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp._ftp import (
    FTP_HOST,
    TRANSIENT_FTP_ERRORS,
    is_missing,
)
from omnisus_db.sources.datasus_ftp.datasets import Dataset, Release, resolve
from omnisus_db.sources.datasus_ftp.filenames import scope_to_filename

logger = structlog.get_logger(__name__)

DEFAULT_MAX_PAYLOAD_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_INFLIGHT_BYTES = 1024 * 1024 * 1024
_DOWNLOAD_LIMIT: ContextVar[int] = ContextVar("download_limit", default=DEFAULT_MAX_PAYLOAD_BYTES)


@contextlib.contextmanager
def download_limit(max_bytes: int):
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("max_payload_bytes must be a positive integer")
    token = _DOWNLOAD_LIMIT.set(max_bytes)
    try:
        yield
    finally:
        _DOWNLOAD_LIMIT.reset(token)


class _DownloadControl:
    """Own control/data sockets so cancellation can stop a blocking transfer."""

    def __init__(self):
        self.cancelled = threading.Event()
        self.ftp = None
        self.sockets = []
        self.guard = threading.Lock()

    def check(self):
        if self.cancelled.is_set():
            raise InterruptedError("download cancelled")

    def track(self, connection):
        if connection is not None:
            with self.guard:
                self.sockets.append(connection)
            if self.cancelled.is_set():
                self.cancel()
                self.check()

    def cancel(self):
        self.cancelled.set()
        with self.guard:
            connections = list(self.sockets)
        # FTP.connect assigns sock before reading the server greeting, so it
        # may already exist even though connect has not returned to track it.
        if self.ftp is not None:
            connection = getattr(self.ftp, "sock", None)
            if connection is not None:
                connections.append(connection)
        for connection in connections:
            with contextlib.suppress(OSError):
                connection.shutdown(socket.SHUT_RDWR)
            with contextlib.suppress(OSError):
                connection.close()

    def close_ftp(self):
        # BufferedReader.close can wait for a worker holding its read lock.
        # Only call this off the event loop, after shutting down known sockets.
        if self.ftp is not None:
            with contextlib.suppress(OSError):
                self.ftp.close()


_ACTIVE_DOWNLOAD: ContextVar[_DownloadControl | None] = ContextVar("active_download", default=None)


async def _download(remote_dir: str, filename: str, timeout_seconds: float) -> bytes:
    control = _DownloadControl()
    token = _ACTIVE_DOWNLOAD.set(control)
    try:
        worker = asyncio.create_task(
            asyncio.to_thread(_blocking_fetch, remote_dir, filename, timeout_seconds)
        )
        try:
            return await asyncio.shield(worker)
        except asyncio.CancelledError:
            control.cancel()
            closing = asyncio.create_task(asyncio.to_thread(control.close_ftp))
            finished = asyncio.gather(worker, closing, return_exceptions=True)
            # A reservation cannot be released while its worker still owns
            # bytes. Connect/DNS stages that cannot be interrupted must finish
            # (or time out); repeated task cancellation does not orphan them.
            while not finished.done():
                try:
                    await asyncio.shield(finished)
                except asyncio.CancelledError:
                    continue
            # Do not keep a completed worker's payload in a cancellation
            # traceback after the caller releases its byte reservation.
            del worker, closing, finished
            raise
    finally:
        _ACTIVE_DOWNLOAD.reset(token)


class FtpFileNotFound(Exception):  # noqa: N818
    """DATASUS does not publish this file (550). Terminal — never retried.

    Distinct from :class:`FtpUnavailable`: a scope that does not exist is a
    normal outcome of asking for a range and becomes a ``skipped``
    :class:`~omnisus_db.sources._base.ScopeOutcome`, while a scope that exists
    but could not be fetched is ``failed`` and worth retrying.
    """


class FtpUnavailable(Exception):  # noqa: N818
    """The file could not be fetched within the retry budget."""


def ftp_path_for(
    dataset: str | Dataset, scope: ScopeKey, release: Release = "final"
) -> tuple[str, str]:
    """Return (remote_dir, filename) for ``scope`` in ``release``.

    Pure: the release comes from the caller, who learned it from the listing
    (``available_releases``). Nothing here tries one directory then another.
    """
    d = resolve(dataset)
    directories = d.directories()
    if release not in directories:
        raise ValueError(f"{d.name} has no {release} directory")
    return directories[release], scope_to_filename(d, scope)


def _blocking_fetch(remote_dir: str, filename: str, timeout_seconds: float) -> bytes:
    """Synchronous FTP fetch returning bytes. Run via asyncio.to_thread."""
    control = _ACTIVE_DOWNLOAD.get() or _DownloadControl()
    max_bytes = _DOWNLOAD_LIMIT.get()

    class TrackedFTP(ftplib.FTP):
        def ntransfercmd(self, *args, **kwargs):
            connection, size = super().ntransfercmd(*args, **kwargs)
            control.track(connection)
            return connection, size

    # Closing BytesIO also releases storage referenced by an exception
    # traceback, so retries and queued errors cannot retain previous payloads.
    with io.BytesIO() as buf:

        def write(chunk: bytes) -> None:
            control.check()
            if buf.tell() + len(chunk) > max_bytes:
                raise ValueError(f"download exceeds payload limit of {max_bytes} bytes")
            buf.write(chunk)

        with contextlib.closing(TrackedFTP(timeout=timeout_seconds)) as ftp:
            control.ftp = ftp
            control.check()
            ftp.connect(FTP_HOST)
            control.track(getattr(ftp, "sock", None))
            control.check()
            ftp.login()
            ftp.cwd(remote_dir)
            ftp.retrbinary(f"RETR {filename}", write)
            control.check()
        return buf.getvalue()


async def fetch_dbc_bytes(
    *,
    dataset: str | Dataset,
    scope: ScopeKey,
    release: Release = "final",
    timeout_seconds: float = 120.0,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
    max_bytes: int | None = None,
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
    remote_dir, filename = ftp_path_for(d, scope, release)
    last_exc: BaseException | None = None
    for attempt in range(max_retries):
        try:
            with download_limit(_DOWNLOAD_LIMIT.get() if max_bytes is None else max_bytes):
                data = await _download(remote_dir, filename, timeout_seconds)
                if len(data) > _DOWNLOAD_LIMIT.get():
                    del data
                    raise ValueError("download exceeds payload bytes limit")
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

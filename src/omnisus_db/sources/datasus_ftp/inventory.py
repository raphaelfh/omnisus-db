"""DATASUS FTP inventory: list, crawl, and decode what the server actually has.

Three layers over one primitive (spec §4.1):

    list_dir(path)      -> Listing          one LIST. The primitive.
    crawl(path, depth=) -> Iterator[FtpEntry]  bounded recursion, open-world.
    available(dataset)  -> list[ScopeKey]   registry-decoded, closed-world.

``available`` and ``crawl`` are the same mechanism at two levels of
interpretation — the only difference is whether filenames get decoded. The
registry names the eleven directories that matter, so the oracle path never
recurses: no queue, no thread pool, no locks.

This module has no dependency on ``Lake``.
"""

from __future__ import annotations

import contextlib
import ftplib
import time
from dataclasses import dataclass
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)

FTP_HOST = "ftp.datasus.gov.br"

_DIR_MARKER = "<DIR>"


class FtpPathNotFound(Exception):  # noqa: N818
    """The remote directory does not exist, or access was denied (550).

    Terminal — never retried. Distinct from an existing but empty directory,
    which returns an empty :class:`Listing` (spec I6).
    """


class FtpUnavailable(Exception):  # noqa: N818
    """The server could not be reached within the retry budget."""


@dataclass(frozen=True)
class FtpEntry:
    """One line of a DATASUS FTP directory listing."""

    name: str
    """File or directory name, spaces preserved."""

    path: str
    """Absolute remote path."""

    parent: str
    """Absolute path of the containing directory."""

    is_dir: bool

    size_bytes: int
    """0 for directories. Exceeds 32 bits in the wild (spec §4.2)."""

    modified: datetime
    """Server-reported mtime. Detects DATASUS republishing a file we ingested."""


@dataclass(frozen=True)
class Listing:
    """The result of one LIST, including what could not be parsed.

    ``skipped`` is structural, not a log line: the Tier 3 probe asserts it is
    zero for registry directories, and an empty ``entries`` with a missing
    directory is impossible — that raises :class:`FtpPathNotFound` (spec I6).
    """

    entries: tuple[FtpEntry, ...]
    skipped: int
    path: str

    @property
    def files(self) -> tuple[FtpEntry, ...]:
        return tuple(e for e in self.entries if not e.is_dir)

    @property
    def dirs(self) -> tuple[FtpEntry, ...]:
        return tuple(e for e in self.entries if e.is_dir)


def _parse_msdos_line(line: str, parent: str) -> FtpEntry | None:
    """Parse one MS-DOS-format LIST line, or ``None`` if it is malformed.

    DATASUS answers ``500 Command not understood`` to MLSD, so LIST is the
    only option and its format is MS-DOS, not Unix::

        01-31-20  02:48PM                76107 DOAC1996.dbc
        02-24-18  07:38AM       <DIR>          199407_200712

    Field 2 is the byte size or ``<DIR>``; the name is everything after it,
    rejoined, because DATASUS names contain spaces.

    Note the two-digit year here goes through ``strptime`` (``%y``: 00-68 ->
    2000s), which is deliberately NOT the filename codec's pivot of 80. These
    are different clocks and must not be conflated.
    """
    parts = line.split()
    if len(parts) < 4:
        return None
    marker = parts[2]
    is_dir = marker == _DIR_MARKER
    if not is_dir:
        try:
            size = int(marker)
        except ValueError:
            return None
    else:
        size = 0
    try:
        modified = datetime.strptime(f"{parts[0]} {parts[1]}", "%m-%d-%y %I:%M%p")
    except ValueError:
        return None
    name = " ".join(parts[3:])
    if not name:
        return None
    base = parent.rstrip("/")
    return FtpEntry(
        name=name,
        path=f"{base}/{name}",
        parent=parent,
        is_dir=is_dir,
        size_bytes=size,
        modified=modified,
    )


def _blocking_list(path: str, timeout_seconds: float) -> list[str]:
    """One anonymous-FTP LIST of ``path``. The patch seam for tests.

    ``encoding = "latin-1"`` is required: ftplib defaults to UTF-8 and raises
    UnicodeDecodeError on real DATASUS listings (spec §4.2).
    """
    lines: list[str] = []
    with contextlib.closing(ftplib.FTP(FTP_HOST, timeout=timeout_seconds)) as ftp:
        ftp.encoding = "latin-1"
        ftp.login()  # anonymous
        ftp.voidcmd("TYPE I")
        ftp.cwd(path)
        ftp.dir(lines.append)
    return lines


def list_dir(
    path: str,
    *,
    timeout_seconds: float = 60.0,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
) -> Listing:
    """List one remote directory. The primitive every other layer builds on.

    Raises:
        FtpPathNotFound: the directory is missing or access was denied (550).
            Terminal — never retried.
        FtpUnavailable: transient failures exhausted ``max_retries``.

    An existing but empty directory returns an empty :class:`Listing`; empty
    and failed are never the same value (spec I6). Every connection attempt is
    fresh, because a long-lived FTP control connection to DATASUS does not
    survive a transient error.

    ``path`` is normalised exactly once, on entry — trailing slashes stripped
    — so ``Listing.path`` and every ``FtpEntry.parent`` carry the canonical
    form regardless of what the caller passed (a caller-supplied ``/x/`` and
    ``/x`` must never diverge downstream, e.g. in the Task 5 cache).
    """
    path = path.rstrip("/") or "/"
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            raw = _blocking_list(path, timeout_seconds)
        except ftplib.error_perm as exc:
            raise FtpPathNotFound(f"{path}: {exc}") from exc
        except (*ftplib.all_errors, OSError, TimeoutError) as exc:
            last_exc = exc
            if attempt + 1 < max_retries:
                time.sleep(backoff_seconds * (2**attempt))
            continue
        entries: list[FtpEntry] = []
        skipped = 0
        for line in raw:
            entry = _parse_msdos_line(line, path)
            if entry is None:
                skipped += 1
            else:
                entries.append(entry)
        if skipped:
            logger.warning("inventory.skipped_lines", path=path, skipped=skipped)
        logger.info("inventory.listed", path=path, entries=len(entries), skipped=skipped)
        return Listing(entries=tuple(entries), skipped=skipped, path=path)
    raise FtpUnavailable(f"{path}: {max_retries} attempts failed") from last_exc

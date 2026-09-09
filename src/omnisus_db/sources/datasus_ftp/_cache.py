"""Persistence for the FTP inventory (spec §4.4).

One Parquet per listed directory, named from the slugified remote path so
``ls`` is debuggable. Staleness lives in a ``fetched_at`` column inside the
file — there is no sidecar metadata to desynchronise.

The cache is never authoritative (spec I8): anything unreadable is a miss,
never an error. It knows nothing about FTP.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import structlog

from omnisus_db.sources.datasus_ftp.inventory import FtpEntry, Listing

logger = structlog.get_logger(__name__)

_SLUG_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def cache_dir() -> Path:
    """Directory holding cached listings.

    ``OMNISUS_CACHE_DIR`` wins; otherwise ``${XDG_CACHE_HOME:-~/.cache}``.
    """
    override = os.environ.get("OMNISUS_CACHE_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "omnisus-db" / "inventory"


def cache_path(remote_path: str) -> Path:
    """Cache file for one remote directory, named from a readable slug."""
    slug = _SLUG_UNSAFE.sub("_", remote_path.strip("/")) or "root"
    return cache_dir() / f"{slug}.parquet"


def write_cache(listing: Listing) -> Path:
    """Persist a listing atomically. Returns the file written."""
    target = cache_path(listing.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).replace(tzinfo=None)
    frame = pl.DataFrame(
        {
            "name": [e.name for e in listing.entries],
            "path": [e.path for e in listing.entries],
            "parent": [e.parent for e in listing.entries],
            "is_dir": [e.is_dir for e in listing.entries],
            "size_bytes": [e.size_bytes for e in listing.entries],
            "modified": [e.modified for e in listing.entries],
        },
        schema={
            "name": pl.Utf8,
            "path": pl.Utf8,
            "parent": pl.Utf8,
            "is_dir": pl.Boolean,
            "size_bytes": pl.Int64,
            "modified": pl.Datetime("us"),
        },
    ).with_columns(
        pl.lit(listing.path).alias("listing_path"),
        pl.lit(listing.skipped).cast(pl.Int64).alias("skipped"),
        pl.lit(now).cast(pl.Datetime("us")).alias("fetched_at"),
    )
    tmp = target.with_suffix(".parquet.tmp")
    frame.write_parquet(tmp, compression="zstd")
    os.replace(tmp, target)
    return target


def read_cached(remote_path: str, *, ttl_hours: float = 24.0) -> Listing | None:
    """Return the cached listing, or ``None`` on miss, stale or unreadable.

    Never raises: a corrupt cache is a miss (spec I8).
    """
    target = cache_path(remote_path)
    try:
        frame = pl.read_parquet(target)
    except Exception as exc:
        if target.exists():
            logger.warning("inventory.cache_unreadable", path=str(target), error=str(exc))
        return None
    try:
        # A zero-row frame carries no fetched_at value, so an empty directory's
        # staleness comes from the file's mtime. Without this an empty cached
        # listing would never expire.
        fetched_at = frame.get_column("fetched_at").max() if frame.height else None
        if fetched_at is None:
            fetched_at = datetime.fromtimestamp(target.stat().st_mtime)
        if datetime.now(UTC).replace(tzinfo=None) - fetched_at > timedelta(hours=ttl_hours):
            return None
        skipped = int(frame.get_column("skipped").max() or 0) if frame.height else 0
        entries = tuple(
            FtpEntry(
                name=row["name"],
                path=row["path"],
                parent=row["parent"],
                is_dir=row["is_dir"],
                size_bytes=int(row["size_bytes"]),
                modified=row["modified"],
            )
            for row in frame.iter_rows(named=True)
        )
    except Exception as exc:
        logger.warning("inventory.cache_malformed", path=str(target), error=str(exc))
        return None
    return Listing(entries=entries, skipped=skipped, path=remote_path)

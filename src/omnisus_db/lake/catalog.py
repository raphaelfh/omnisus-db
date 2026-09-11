"""DuckLake target URI parsing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote_plus, urlsplit


@dataclass(frozen=True)
class CatalogURI:
    """Resolved DuckLake target."""

    catalog_uri: str  # sqlite:/path or postgresql://...
    storage_root: str  # local path or s3://...


def parse_target(target: str) -> CatalogURI:
    """Parse an ``omnisus-db`` target string.

    Forms accepted:
        ``ducklake:./omnisus.ducklake``
            -> sqlite catalog at ``./omnisus-catalog.sqlite``
            -> storage at ``./omnisus.ducklake/``
        ``ducklake:postgresql://user:pwd@host/db?storage=s3://bucket/lake``
            -> postgres catalog
            -> storage at ``s3://bucket/lake``
    """
    if not target.startswith("ducklake:"):
        raise ValueError("target must start with 'ducklake:'")
    body = target[len("ducklake:") :]

    if body.startswith(("postgresql://", "postgres://")):
        try:
            split = urlsplit(body)
        except ValueError:
            raise ValueError("invalid postgres target URI") from None
        storage = []
        kept = []
        for part in split.query.split("&"):
            key, _, value = part.partition("=")
            if unquote_plus(key) == "storage":
                storage.append(unquote_plus(value))
            elif part:
                kept.append(part)
        if len(storage) != 1 or not storage[0]:
            raise ValueError("postgres target requires exactly one ?storage=<path or s3 uri>")
        # Rebuilt by hand: urlunsplit restores the empty authority of a
        # ``postgresql:///?host=…`` DSN only for schemes it knows, and libpq
        # rejects the ``postgresql:/?host=…`` it produced instead.
        clean_url = body.partition("?")[0]
        if kept:
            clean_url += "?" + "&".join(kept)
        if split.fragment:
            clean_url += "#" + split.fragment
        return CatalogURI(catalog_uri=clean_url, storage_root=storage[0])

    storage_path = Path(body).expanduser().resolve()
    catalog_path = storage_path.with_name(storage_path.stem + "-catalog.sqlite")
    return CatalogURI(
        catalog_uri=f"sqlite:{catalog_path}",
        storage_root=str(storage_path),
    )


DEFAULT_TARGET = "ducklake:./omnisus.ducklake"
"""Default lake target for the Python API and the CLI — its single home (spec I4)."""

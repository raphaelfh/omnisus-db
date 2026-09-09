"""DuckLake target URI parsing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


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
        raise ValueError(f"target must start with 'ducklake:' (got: {target!r})")
    body = target[len("ducklake:") :]

    if body.startswith(("postgresql://", "postgres://")):
        split = urlsplit(body)
        params = parse_qs(split.query)
        storage = params.get("storage", [None])[0]
        if not storage:
            raise ValueError("postgres target requires ?storage=<path or s3 uri>")
        clean_url = body.split("?", 1)[0]
        return CatalogURI(catalog_uri=clean_url, storage_root=storage)

    storage_path = Path(body).expanduser().resolve()
    catalog_path = storage_path.with_name(storage_path.stem + "-catalog.sqlite")
    return CatalogURI(
        catalog_uri=f"sqlite:{catalog_path}",
        storage_root=str(storage_path),
    )


DEFAULT_TARGET = "ducklake:./omnisus.ducklake"
"""Default lake target for the Python API and the CLI — its single home (spec I4)."""

"""CNES-ST importer (delegates to datasus_ftp _runner)."""

from __future__ import annotations

from omnisus_db.lake import Lake
from omnisus_db.sources._base import ImportResult, ScopeKey
from omnisus_db.sources.datasus_ftp._runner import import_scope


async def import_st_scope(*, scope: ScopeKey, lake: Lake) -> ImportResult:
    """Import one CNES-ST scope. Thin wrapper around the generic FTP runner."""
    return await import_scope(dataset="cnes_st", scope=scope, lake=lake)

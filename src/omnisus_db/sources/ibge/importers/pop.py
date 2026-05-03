"""IBGE pop importer."""

from __future__ import annotations

from omnisus_db.lake import Lake
from omnisus_db.sources._base import ImportResult
from omnisus_db.sources.ibge.fetch import fetch_pop_by_year
from omnisus_db.sources.ibge.parse import pop_json_to_lazyframe


async def import_pop_year(*, year: int, lake: Lake) -> ImportResult:
    """Fetch and ingest one year of IBGE population data."""
    payload = await fetch_pop_by_year(year)
    lf = pop_json_to_lazyframe(payload, year=year)
    return lake.ingest("ibge_pop", lf, partition_by=("ano",))

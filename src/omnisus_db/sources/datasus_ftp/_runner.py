"""Generic DATASUS-FTP pipeline (per spec §11.1 hybrid pattern).

Per-dataset modules (e.g. cnes/importers/st.py) wrap this when they need
extra behaviour. For datasets with no special behaviour the generic runner
is the whole importer.
"""

from __future__ import annotations

import polars as pl
import structlog

from omnisus_db.lake import Lake
from omnisus_db.sources._base import ImportResult, ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import Dataset, resolve
from omnisus_db.sources.datasus_ftp.fetch import fetch_dbc_bytes
from omnisus_db.sources.datasus_ftp.parse import dbc_bytes_to_lazyframe

logger = structlog.get_logger(__name__)


async def import_scope(
    *,
    dataset: str | Dataset,
    scope: ScopeKey,
    lake: Lake,
) -> ImportResult:
    """Fetch + parse + sink one (dataset, scope) into the lake.

    ``dataset`` is a registry key, an alias, or a ``Dataset`` value. The
    value form is the open door of spec I3: an uncurated dataset with its
    own ``dictionary`` flows through exactly this path.
    """
    d = resolve(dataset)
    if d.monthly and scope.mes is None:
        raise ValueError(f"{d.name} is monthly; ScopeKey.mes is required")

    logger.info("import_scope.start", dataset=d.name, scope=str(scope))
    raw = await fetch_dbc_bytes(dataset=d, scope=scope)
    lf = dbc_bytes_to_lazyframe(
        raw, dataset=d.name, ano=scope.ano, uf=scope.uf, dictionary=d.dictionary
    )
    if d.monthly:
        lf = lf.with_columns(pl.lit(scope.mes).cast(pl.UInt8).alias("mes"))
    result = lake.ingest(d.name, lf, partition_by=d.partition_by)
    logger.info(
        "import_scope.done",
        dataset=d.name,
        scope=str(scope),
        rows=result.rows,
        snapshot_id=result.snapshot_id,
    )
    return result

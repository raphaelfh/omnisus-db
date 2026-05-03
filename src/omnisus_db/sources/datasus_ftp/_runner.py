"""Generic DATASUS-FTP pipeline (per spec §11.1 hybrid pattern).

Per-dataset modules (e.g. importers/sih.py) override this default when they
need custom logic. For simple datasets (SIM, SINASC, CNES), the generic
runner is enough.
"""

from __future__ import annotations

import polars as pl
import structlog

from omnisus_db.lake import Lake
from omnisus_db.sources._base import ImportResult, ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import get_config
from omnisus_db.sources.datasus_ftp.fetch import fetch_dbc_bytes
from omnisus_db.sources.datasus_ftp.parse import dbc_bytes_to_lazyframe

logger = structlog.get_logger(__name__)


async def import_scope(
    *,
    dataset: str,
    scope: ScopeKey,
    lake: Lake,
) -> ImportResult:
    """Fetch + parse + sink one (dataset, scope) into the lake."""
    cfg = get_config(dataset)
    if cfg.monthly and scope.mes is None:
        raise ValueError(f"{dataset} is monthly; ScopeKey.mes is required")

    logger.info("import_scope.start", dataset=dataset, scope=str(scope))
    raw = await fetch_dbc_bytes(dataset=dataset, scope=scope)
    lf = dbc_bytes_to_lazyframe(raw, dataset=dataset, ano=scope.ano, uf=scope.uf)
    if cfg.monthly:
        lf = lf.with_columns(pl.lit(scope.mes).cast(pl.UInt8).alias("mes"))
    result = lake.ingest(dataset, lf, partition_by=cfg.partition_by)
    logger.info(
        "import_scope.done",
        dataset=dataset,
        scope=str(scope),
        rows=result.rows,
        snapshot_id=result.snapshot_id,
    )
    return result

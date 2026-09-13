"""Execute the existing inventory result cell against a national lake."""

import importlib.util
from pathlib import Path

import marimo as mo
import polars as pl

import omnisus_db as odb
from omnisus_db.sources.datasus_ftp.datasets import resolve

NOTEBOOK = Path(__file__).resolve().parents[3] / "notebooks/explorar/inventario_dados_reais.py"


async def test_national_inventory_result_exports_complete_data(tmp_path):
    spec = importlib.util.spec_from_file_location("national_inventory", NOTEBOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cell = next(c for c in module.app._cell_manager.cells() if "resumo" in c._cell.defs)
    target = f"ducklake:{tmp_path}/national.ducklake"
    frame = pl.DataFrame({"_source_ano": [2023, 2023], "sg_uf_not": ["15", "33"]})
    with odb.Lake.local(target) as lake:
        lake.ingest("sinan_chagas", frame.lazy())
    report = odb.ImportReport(
        outcomes=(
            odb.ScopeOutcome(
                scope=odb.ScopeKey(uf=None, ano=2023),
                status="ok",
                result=odb.ImportResult(rows=2, bytes_written=0, duration_seconds=0),
            ),
        )
    )
    _, values = await cell.run(
        dataset=resolve("sinan_chagas"),
        mo=mo,
        odb=odb,
        pasta=tmp_path,
        relatorio=report,
        target=target,
    )
    assert values["resumo"].rows() == [(2023, 2)]
    assert pl.read_parquet(tmp_path / "sinan_chagas.parquet").equals(frame)
    assert pl.read_csv(tmp_path / "sinan_chagas.csv").height == 2

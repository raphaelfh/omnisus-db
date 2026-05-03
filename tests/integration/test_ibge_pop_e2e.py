"""End-to-end: IBGE SIDRA mock -> import_ibge_pop() -> lake -> query."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

import omnisus_db as odb
from omnisus_db.lake import Lake


@pytest.mark.integration
@respx.mock
def test_import_ibge_pop_e2e(tmp_path: Path) -> None:
    body = [
        {
            "id": "1",
            "resultados": [
                {
                    "series": [
                        {"localidade": {"id": "3550308"}, "serie": {"2022": "12500000"}},
                        {"localidade": {"id": "3304557"}, "serie": {"2022": "6700000"}},
                    ]
                }
            ],
        }
    ]
    respx.get(
        "https://servicodados.ibge.gov.br/api/v3/agregados/793/periodos/2022/variaveis/93?localidades=N6"
    ).mock(return_value=httpx.Response(200, content=json.dumps(body)))

    target = f"ducklake:{tmp_path}/test.ducklake"
    odb.import_ibge_pop(years=[2022], target=target)

    lake = Lake.local(target)
    rows = (
        lake.connect().execute("SELECT count(*) FROM lake.ibge_pop WHERE ano=2022").fetchone()[0]
    )
    assert rows == 2
    lake.close()

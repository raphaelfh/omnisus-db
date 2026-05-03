"""Tests for IBGE SIDRA fetcher."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from omnisus_db.sources.ibge.fetch import fetch_pop_by_year


@pytest.mark.asyncio
@respx.mock
async def test_fetch_pop_returns_json_payload() -> None:
    body = [
        {
            "id": "1",
            "variavel": "População residente",
            "resultados": [
                {
                    "series": [
                        {
                            "localidade": {"id": "3550308", "nivel": {}},
                            "serie": {"2022": "11451245"},
                        }
                    ]
                }
            ],
        }
    ]
    respx.get(
        "https://servicodados.ibge.gov.br/api/v3/agregados/793/periodos/2022/variaveis/93?localidades=N6"
    ).mock(return_value=httpx.Response(200, content=json.dumps(body)))

    data = await fetch_pop_by_year(2022)
    assert data[0]["id"] == "1"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_pop_raises_on_5xx() -> None:
    respx.get(
        "https://servicodados.ibge.gov.br/api/v3/agregados/793/periodos/2024/variaveis/93?localidades=N6"
    ).mock(return_value=httpx.Response(503))
    with pytest.raises(httpx.HTTPStatusError):
        await fetch_pop_by_year(2024)

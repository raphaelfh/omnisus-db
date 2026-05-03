"""Tests for datasus_ftp.fetch — async DBC HTTP fetcher."""

from __future__ import annotations

import httpx
import pytest
import respx

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.fetch import fetch_dbc_bytes


@pytest.mark.asyncio
@respx.mock
async def test_fetch_dbc_bytes_returns_payload() -> None:
    payload = b"\x00\x01FAKE_DBC_BYTES"
    respx.get("http://datasus.saude.gov.br/dissemin/publicos/SIM/CID10/DORES/DOSP2024.dbc").mock(
        return_value=httpx.Response(200, content=payload)
    )

    data = await fetch_dbc_bytes(
        dataset="sim_do",
        scope=ScopeKey(uf="SP", ano=2024),
    )
    assert data == payload


@pytest.mark.asyncio
@respx.mock
async def test_fetch_dbc_bytes_retries_on_5xx() -> None:
    payload = b"OK"
    route = respx.get(
        "http://datasus.saude.gov.br/dissemin/publicos/SIM/CID10/DORES/DOSP2024.dbc"
    ).mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, content=payload),
        ]
    )
    data = await fetch_dbc_bytes(
        dataset="sim_do",
        scope=ScopeKey(uf="SP", ano=2024),
        max_retries=3,
        backoff_seconds=0,
    )
    assert data == payload
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_fetch_dbc_bytes_raises_after_max_retries() -> None:
    respx.get("http://datasus.saude.gov.br/dissemin/publicos/SIM/CID10/DORES/DOSP2024.dbc").mock(
        return_value=httpx.Response(503)
    )
    with pytest.raises(httpx.HTTPStatusError):
        await fetch_dbc_bytes(
            dataset="sim_do",
            scope=ScopeKey(uf="SP", ano=2024),
            max_retries=2,
            backoff_seconds=0,
        )

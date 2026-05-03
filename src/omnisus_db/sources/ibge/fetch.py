"""IBGE SIDRA REST API fetcher."""

from __future__ import annotations

import httpx

# SIDRA agregado 793 = População residente (projeções)
# Variável 93 = População residente
_AGREGADO_POP = 793
_VAR_POP = 93


async def fetch_pop_by_year(year: int) -> list[dict]:
    """Fetch population by município for one year.

    Returns the raw IBGE SIDRA JSON payload (a list of one dict).
    """
    url = (
        f"https://servicodados.ibge.gov.br/api/v3/agregados/{_AGREGADO_POP}"
        f"/periodos/{year}/variaveis/{_VAR_POP}?localidades=N6"
    )
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()

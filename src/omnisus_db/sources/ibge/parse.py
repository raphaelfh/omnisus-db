"""IBGE SIDRA JSON → Polars LazyFrame."""

from __future__ import annotations

import polars as pl


def pop_json_to_lazyframe(payload: list[dict], year: int) -> pl.LazyFrame:
    """Flatten the IBGE SIDRA payload to (codigo_ibge, ano, populacao)."""
    schema = {
        "codigo_ibge": pl.Utf8,
        "ano": pl.UInt16,
        "populacao": pl.UInt32,
    }
    if not payload:
        return pl.DataFrame(
            {"codigo_ibge": [], "ano": [], "populacao": []},
            schema=schema,
        ).lazy()

    rows = []
    series = payload[0].get("resultados", [{}])[0].get("series", [])
    for s in series:
        cod = s["localidade"]["id"]
        for ano_str, pop_str in s["serie"].items():
            try:
                pop = int(pop_str)
            except (ValueError, TypeError):
                continue
            rows.append(
                {
                    "codigo_ibge": str(cod),
                    "ano": int(ano_str),
                    "populacao": pop,
                }
            )
    return pl.DataFrame(rows, schema=schema).lazy()

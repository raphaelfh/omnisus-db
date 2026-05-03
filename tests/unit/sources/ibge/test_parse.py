"""Tests for IBGE pop JSON → Polars."""

from __future__ import annotations

import polars as pl

from omnisus_db.sources.ibge.parse import pop_json_to_lazyframe


def test_pop_json_flattens_to_rows() -> None:
    payload = [
        {
            "id": "1",
            "resultados": [
                {
                    "series": [
                        {"localidade": {"id": "3550308"}, "serie": {"2022": "11451245"}},
                        {"localidade": {"id": "3304557"}, "serie": {"2022": "6700000"}},
                    ]
                }
            ],
        }
    ]
    lf = pop_json_to_lazyframe(payload, year=2022)
    df = lf.collect()
    assert df.height == 2
    assert set(df.columns) == {"codigo_ibge", "ano", "populacao"}
    assert df["ano"].dtype == pl.UInt16


def test_pop_json_skips_non_numeric_population() -> None:
    payload = [
        {
            "resultados": [
                {
                    "series": [
                        {"localidade": {"id": "111"}, "serie": {"2022": "..."}},
                        {"localidade": {"id": "222"}, "serie": {"2022": "100"}},
                    ]
                }
            ],
        }
    ]
    lf = pop_json_to_lazyframe(payload, year=2022)
    df = lf.collect()
    assert df.height == 1
    assert df["codigo_ibge"][0] == "222"


def test_pop_json_empty_payload_returns_empty_frame() -> None:
    lf = pop_json_to_lazyframe([], year=2022)
    df = lf.collect()
    assert df.height == 0
    assert set(df.columns) == {"codigo_ibge", "ano", "populacao"}

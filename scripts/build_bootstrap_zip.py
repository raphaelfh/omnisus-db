"""Build src/omnisus_db/data/auxiliares-bootstrap.zip from upstream sources.

Run once or on `omnisus-db lake update-auxiliares` to refresh.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import httpx
import polars as pl

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "src" / "omnisus_db" / "data" / "auxiliares-bootstrap.zip"

REGIAO_BY_CODE = {
    "1": "Norte",
    "2": "Nordeste",
    "3": "Sudeste",
    "4": "Sul",
    "5": "Centro-Oeste",
}


def fetch_uf() -> pl.DataFrame:
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
    data = httpx.get(url, timeout=30).raise_for_status().json()
    rows = [
        {
            "codigo_ibge": str(item["id"]),
            "sigla": item["sigla"],
            "nome": item["nome"],
            "regiao": REGIAO_BY_CODE[str(item["id"])[0]],
        }
        for item in data
    ]
    return pl.DataFrame(rows)


def fetch_municipios() -> pl.DataFrame:
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    data = httpx.get(url, timeout=60).raise_for_status().json()
    rows = []
    for item in data:
        # The full path varies — use a helper to dig out the UF id robustly
        try:
            uf_id = str(item["microrregiao"]["mesorregiao"]["UF"]["id"])
        except (KeyError, TypeError):
            try:
                uf_id = str(item["regiao-imediata"]["regiao-intermediaria"]["UF"]["id"])
            except (KeyError, TypeError):
                continue
        rows.append(
            {
                "codigo_ibge": str(item["id"]),
                "nome": item["nome"],
                "uf_codigo": uf_id,
                "latitude": None,
                "longitude": None,
            }
        )
    return pl.DataFrame(
        rows,
        schema={
            "codigo_ibge": pl.Utf8,
            "nome": pl.Utf8,
            "uf_codigo": pl.Utf8,
            "latitude": pl.Float64,
            "longitude": pl.Float64,
        },
    )


def fetch_cid10() -> pl.DataFrame:
    """CID-10 minimal seed.

    For Day 1 we ship a tiny seed (a few representative codes). Production
    builds will source from DATASUS Tabnet CSV at:
    http://www2.datasus.gov.br/cid10/V2008/Downloads.htm
    The `lake update-auxiliares` CLI command (Phase 5) will refresh from
    the authoritative source.
    """
    rows = [
        {"codigo": "A00", "descricao": "Cólera", "capitulo": 1, "bloco": "A00-A09"},
        {
            "codigo": "A09",
            "descricao": "Diarreia e gastroenterite de origem infecciosa presumível",
            "capitulo": 1,
            "bloco": "A00-A09",
        },
        {"codigo": "B20", "descricao": "Doença pelo HIV", "capitulo": 1, "bloco": "B20-B24"},
        {
            "codigo": "C50",
            "descricao": "Neoplasia maligna da mama",
            "capitulo": 2,
            "bloco": "C50-C50",
        },
        {
            "codigo": "E10",
            "descricao": "Diabetes mellitus tipo 1",
            "capitulo": 4,
            "bloco": "E10-E14",
        },
        {
            "codigo": "E11",
            "descricao": "Diabetes mellitus tipo 2",
            "capitulo": 4,
            "bloco": "E10-E14",
        },
        {
            "codigo": "I10",
            "descricao": "Hipertensão essencial (primária)",
            "capitulo": 9,
            "bloco": "I10-I15",
        },
        {
            "codigo": "I21",
            "descricao": "Infarto agudo do miocárdio",
            "capitulo": 9,
            "bloco": "I20-I25",
        },
        {"codigo": "I63", "descricao": "Infarto cerebral", "capitulo": 9, "bloco": "I60-I69"},
        {
            "codigo": "J18",
            "descricao": "Pneumonia por organismo não especificado",
            "capitulo": 10,
            "bloco": "J09-J18",
        },
        {
            "codigo": "K70",
            "descricao": "Doença alcoólica do fígado",
            "capitulo": 11,
            "bloco": "K70-K77",
        },
        {"codigo": "N18", "descricao": "Doença renal crônica", "capitulo": 14, "bloco": "N17-N19"},
        {
            "codigo": "O80",
            "descricao": "Parto único espontâneo",
            "capitulo": 15,
            "bloco": "O80-O84",
        },
        {
            "codigo": "P07",
            "descricao": "Recém-nascido de baixo peso",
            "capitulo": 16,
            "bloco": "P05-P08",
        },
        {
            "codigo": "R09",
            "descricao": "Outros sintomas dos sistemas circulatório e respiratório",
            "capitulo": 18,
            "bloco": "R00-R09",
        },
        {
            "codigo": "U07",
            "descricao": "Uso emergencial de U07 (COVID-19)",
            "capitulo": 22,
            "bloco": "U00-U49",
        },
    ]
    return pl.DataFrame(rows)


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, df in [
            ("aux_uf.parquet", fetch_uf()),
            ("aux_municipios.parquet", fetch_municipios()),
            ("aux_cid10.parquet", fetch_cid10()),
        ]:
            buf = io.BytesIO()
            df.write_parquet(buf, compression="zstd")
            zf.writestr(name, buf.getvalue())
            print(f"  added {name}: {df.height} rows")
    print(f"wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()

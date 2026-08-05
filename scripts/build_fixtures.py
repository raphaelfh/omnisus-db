"""Generate mini DBC test fixtures by downloading real DATASUS files.

Run manually once. Outputs are committed to tests/fixtures/dbc/.
We use the smallest UF (RR — Roraima) and recent years to keep fixtures tiny.

The HTTP mirror (datasus.saude.gov.br/dissemin/publicos) is currently 404,
so this script downloads via the FTP server (ftp.datasus.gov.br). The
production async fetcher in `omnisus_db.sources.datasus_ftp.fetch` keeps the
HTTP shape because tests mock it; an FTP transport will be added later.
"""

from __future__ import annotations

import ftplib
import io
from pathlib import Path

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.inventory import scope_to_filename

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "dbc"

FTP_HOST = "ftp.datasus.gov.br"
FTP_TIMEOUT = 60

DATASET_FTP_PATH: dict[str, str] = {
    "sim_do": "/dissemin/publicos/SIM/CID10/DORES",
    "sinasc_nv": "/dissemin/publicos/SINASC/NOV/DNRES",
    "sih_rd": "/dissemin/publicos/SIHSUS/200801_/Dados",
    "sia_bi": "/dissemin/publicos/SIASUS/200801_/Dados",
    "cnes_st": "/dissemin/publicos/CNES/200508_/Dados/ST",
}

TARGETS: list[tuple[str, ScopeKey, str]] = [
    ("sim_do", ScopeKey(uf="RR", ano=2023), "sim_rr_2023_mini.dbc"),
    ("sinasc_nv", ScopeKey(uf="RR", ano=2022), "sinasc_rr_2022_mini.dbc"),
    ("sih_rd", ScopeKey(uf="RR", ano=2024, mes=1), "sih_rr_2024_01_mini.dbc"),
    ("sia_bi", ScopeKey(uf="RR", ano=2024, mes=1), "sia_bi_rr_2024_01_mini.dbc"),
    ("cnes_st", ScopeKey(uf="RR", ano=2024, mes=1), "cnes_rr_2024_01_mini.dbc"),
]


def fetch_via_ftp(dataset: str, scope: ScopeKey) -> bytes:
    filename = scope_to_filename(dataset, scope).upper().replace(".DBC", ".dbc")
    # DATASUS uses uppercase filenames on the server, but uppercase prefix is
    # already in scope_to_filename; ensure casing matches the server convention.
    ftp_path = DATASET_FTP_PATH[dataset]
    buf = io.BytesIO()
    with ftplib.FTP(FTP_HOST, timeout=FTP_TIMEOUT) as ftp:
        ftp.login()
        ftp.cwd(ftp_path)
        # Try the lowercase .dbc first, then uppercase .DBC if it 550s.
        try:
            ftp.retrbinary(f"RETR {filename}", buf.write)
        except ftplib.error_perm:
            buf.seek(0)
            buf.truncate()
            ftp.retrbinary(f"RETR {filename.upper()}", buf.write)
    return buf.getvalue()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for dataset, scope, fname in TARGETS:
        out_file = OUT / fname
        if out_file.exists():
            print(f"skip (exists): {out_file}")
            continue
        print(f"fetching {dataset} {scope} -> {out_file}")
        try:
            data = fetch_via_ftp(dataset, scope)
        except Exception as exc:
            print(f"  FAILED: {exc}")
            continue
        out_file.write_bytes(data)
        print(f"  wrote {len(data) / 1024:.1f} KB")


if __name__ == "__main__":
    main()

"""Generate mini DBC test fixtures by downloading real DATASUS files.

Run manually once. Outputs are committed to tests/fixtures/dbc/.
We use the smallest UF (RR — Roraima) and recent years to keep fixtures tiny.

Downloads over anonymous FTP (ftp.datasus.gov.br); the HTTP mirror at
datasus.saude.gov.br/dissemin/publicos is 404. The production fetcher in
``omnisus_db.sources.datasus_ftp.fetch`` uses the same transport.

Every remote path comes from the registry row, so this script covers whatever
the registry covers. It used to carry a hand-copied path map for 5 of the 11
datasets, which meant ``conftest.py``'s advice — "run scripts/build_fixtures.py"
— was a dead end for the other 6 (spec I4).
"""

from __future__ import annotations

import ftplib
import io
from pathlib import Path

import omnisus_db as odb
from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp._ftp import FTP_HOST
from omnisus_db.sources.datasus_ftp.fetch import ftp_path_for
from omnisus_db.sources.datasus_ftp.filenames import scope_to_filename

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "dbc"

FTP_TIMEOUT = 60

TARGETS: list[tuple[str, ScopeKey, str]] = [
    ("sinan_chagas", ScopeKey(uf=None, ano=2023), "sinan_chagas_br_2023.dbc"),
    ("sinan_hanseniase", ScopeKey(uf=None, ano=2026), "sinan_hanseniase_br_2026.dbc"),
    ("sim_obitos", ScopeKey(uf="RR", ano=2023), "sim_rr_2023_mini.dbc"),
    ("sinasc_nascidos_vivos", ScopeKey(uf="RR", ano=2022), "sinasc_rr_2022_mini.dbc"),
    ("sih_aih_reduzida", ScopeKey(uf="RR", ano=2024, mes=1), "sih_rr_2024_01_mini.dbc"),
    ("sia_bpa_individualizado", ScopeKey(uf="RR", ano=2024, mes=1), "sia_bi_rr_2024_01_mini.dbc"),
    ("sia_apac_medicamentos", ScopeKey(uf="RR", ano=2024, mes=1), "sia_am_rr_2024_01_mini.dbc"),
    ("sia_apac_quimioterapia", ScopeKey(uf="RR", ano=2024, mes=1), "sia_aq_rr_2024_01_mini.dbc"),
    (
        "sia_apac_tratamento_dialitico",
        ScopeKey(uf="RR", ano=2024, mes=1),
        "sia_atd_rr_2024_01_mini.dbc",
    ),
    ("sia_apac_laudos_diversos", ScopeKey(uf="RR", ano=2024, mes=1), "sia_ad_rr_2024_01_mini.dbc"),
    ("sia_psicossocial", ScopeKey(uf="RR", ano=2024, mes=1), "sia_ps_rr_2024_01_mini.dbc"),
    (
        "sia_apac_cirurgia_bariatrica",
        ScopeKey(uf="SP", ano=2024, mes=1),
        "sia_abo_sp_2024_01_mini.dbc",
    ),
    ("cnes_estabelecimentos", ScopeKey(uf="RR", ano=2024, mes=1), "cnes_rr_2024_01_mini.dbc"),
]
"""One entry per registry row. ``tests/unit/test_public_api.py`` asserts this
list and its own ``_FIXTURE_FOR`` agree, so neither can drift from the other
or from the registry."""


def fetch_via_ftp(dataset: str, scope: ScopeKey) -> bytes:
    filename = scope_to_filename(dataset, scope).upper().replace(".DBC", ".dbc")
    # DATASUS uses uppercase filenames on the server, but uppercase prefix is
    # already in scope_to_filename; ensure casing matches the server convention.
    release = odb.available_releases(dataset).get(scope, "final")
    ftp_path = ftp_path_for(dataset, scope, release)[0]
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

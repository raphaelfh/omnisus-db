"""DATASUS CNS cipher: decrypt, validate and classify the patient key.

The public SIA dissemination encrypts the patient CNS by storing each digit
as ``chr(digit + 0x7B)`` — alphabet ``\\x7b``-``\\x84``. Field-verified
(2026-08) to be the SAME cipher across APAC (``AP_CNSPCN``), BPA-I and RAAS
(``CNS_PAC``), which makes the decoded CNS a deterministic person key across
all identifiable SIA families.

Requires the source column to have been read with **latin-1** (cp1252 raises
``UnicodeDecodeError`` on ``0x81``; see the ``sia_bi`` dicionário).

Caveats the linkage layer must own (measured):
- ~97% of CNS in APAC-AM are *provisórios* (first digit 7/8/9); measured
  identifier-churn λ ≈ 0.0034/year in chronically-linked patients.
- BPA-I carries ~1-7% blank CNS depending on UF/competência.
- a valid check digit proves the DECODER, not the person's identity.
"""

from __future__ import annotations

import polars as pl

_OFFSET = 0x7B
_ALPHABET_MAX = 0x84


def cns_decrypt(value: str | None) -> str | None:
    """Decrypt one ciphered CNS. Returns None for blank/non-cipher input."""
    if not value:
        return None
    if len(value) != 15:
        return None
    ords = [ord(ch) for ch in value]
    if any(o < _OFFSET or o > _ALPHABET_MAX for o in ords):
        return None
    return "".join(str(o - _OFFSET) for o in ords)


def cns_is_valid(cns: str | None) -> bool:
    """CNS mod-11 check. Provisórios (7/8/9) and definitivos (1/2) differ."""
    if not cns or len(cns) != 15 or not cns.isdigit():
        return False
    if cns[0] in "789":
        return sum(int(cns[i]) * (15 - i) for i in range(15)) % 11 == 0
    if cns[0] not in "12":
        return False
    pis = cns[:11]
    s = sum(int(pis[i]) * (15 - i) for i in range(11))
    dv = 11 - (s % 11)
    if dv == 11:
        dv = 0
    if dv == 10:
        dv2 = 11 - ((s + 2) % 11)
        return cns[11:] == f"001{dv2}"
    return cns[11:] == f"000{dv}"


def cns_class(cns: str | None) -> str | None:
    """'definitivo' (1/2 — PIS/PASEP-anchored) or 'provisorio' (7/8/9)."""
    if not cns:
        return None
    return "definitivo" if cns[0] in "12" else "provisorio"


def with_decoded_cns(
    lf: pl.LazyFrame,
    *,
    source_col: str,
    out_col: str = "cns",
) -> pl.LazyFrame:
    """Add ``out_col`` (decrypted CNS or null) and ``{out_col}_valido``.

    Row-wise Python UDF: fine for the pilot scale (<10M rows); revisit as a
    native expression if it ever shows up in profiles.
    """
    return lf.with_columns(
        pl.col(source_col).map_elements(cns_decrypt, return_dtype=pl.Utf8).alias(out_col)
    ).with_columns(
        pl.col(out_col)
        .map_elements(cns_is_valid, return_dtype=pl.Boolean)
        .fill_null(False)
        .alias(f"{out_col}_valido")
    )

"""Tests for the DATASUS CNS cipher transform — the linkage key enabler.

Field-measured facts these tests encode:
- cipher: each digit is stored as chr(digit + 0x7B); alphabet \x7b-\x84.
- the SAME cipher is used in APAC (AP_CNSPCN), BPA-I and RAAS (CNS_PAC),
  so decoding yields a deterministic person key across SIA families.
- decoded values pass the CNS mod-11 check-digit (100% in APAC/RAAS files,
  98.8% in the RR BPA-I fixture; blanks exist in BPA-I).
"""

from __future__ import annotations

import polars as pl

from omnisus_db.transforms.cns import (
    cns_class,
    cns_decrypt,
    cns_is_valid,
    with_decoded_cns,
)

# structurally valid, synthetic (sum of digit*(15-i) divisible by 11)
VALID_PROVISORIO = "700000000000005"
ENC_VALID_PROVISORIO = "".join(chr(int(d) + 0x7B) for d in VALID_PROVISORIO)


def test_decrypt_known_cipher() -> None:
    assert cns_decrypt(ENC_VALID_PROVISORIO) == VALID_PROVISORIO


def test_decrypt_blank_returns_none() -> None:
    assert cns_decrypt(" " * 15) is None
    assert cns_decrypt("") is None
    assert cns_decrypt(None) is None


def test_decrypt_out_of_alphabet_returns_none() -> None:
    assert cns_decrypt("701211111111119") is None  # plain digits, not cipher


def test_is_valid_mod11_provisorio() -> None:
    assert cns_is_valid(VALID_PROVISORIO) is True
    assert cns_is_valid("700000000000004") is False  # broken check digit
    assert cns_is_valid(None) is False


def test_class_by_first_digit() -> None:
    assert cns_class("700000000000005") == "provisorio"
    assert cns_class("100000000000009") == "definitivo"
    assert cns_class(None) is None


def test_with_decoded_cns_polars_pipeline() -> None:
    df = pl.DataFrame({"cns_pac": [ENC_VALID_PROVISORIO, " " * 15, "lixo"]})
    out = with_decoded_cns(df.lazy(), source_col="cns_pac").collect()
    assert out["cns"].to_list() == [VALID_PROVISORIO, None, None]
    assert out["cns_valido"].to_list() == [True, False, False]


def test_with_decoded_cns_on_real_fixture(dbc_fixture) -> None:
    """RR BPA-I fixture: measured 98.8% valid, 1.1% blank."""
    from omnisus_db.sources.datasus_ftp.parse import dbc_bytes_to_lazyframe

    lf = dbc_bytes_to_lazyframe(
        dbc_fixture("sia_bi_rr_2024_01_mini").read_bytes(), dataset="sia_bpa_individualizado"
    )
    out = with_decoded_cns(lf, source_col="cns_pac").collect()
    valid_rate = out["cns_valido"].sum() / out.height
    assert 0.95 < valid_rate <= 1.0, f"valid rate {valid_rate:.3f} outside measured band"

"""Tests for the SIA BPA-I (BI) dataset: dicionário, inventory and parse.

The BI is the identifiable backbone of SIA: it carries CNS_PAC (encrypted
patient CNS) plus DTNASC — measured at 93% of the identifiable universe in
AC 2024-01. Two field-measured constraints drive these tests:

- encoding MUST be latin-1: the CNS cipher uses bytes 0x7B-0x84 and 0x81 is
  undefined in cp1252 (UnicodeDecodeError with strict codecs).
- layout: 36 fields, rec_len 245, verified identical in AC and RR 2024-01.
"""

from __future__ import annotations

import polars as pl

from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp.datasets import get_config
from omnisus_db.sources.datasus_ftp.fetch import ftp_path_for
from omnisus_db.sources.datasus_ftp.filenames import parse_filename, scope_to_filename
from omnisus_db.sources.datasus_ftp.parse import dbc_bytes_to_lazyframe
from omnisus_db.transforms.dictionaries import load_dicionario


def test_dicionario_loads_with_latin1_encoding() -> None:
    dic = load_dicionario("sia_bi")
    assert dic.encoding == "latin-1"


def test_dicionario_has_measured_field_count_and_keys() -> None:
    dic = load_dicionario("sia_bi")
    names = [f["name"] for f in dic.fields]
    assert len(names) == 36
    # linkage-critical fields
    for key in ("cns_pac", "dtnasc", "sexopac", "munpac", "cidpri", "proc_id"):
        assert key in names, f"missing {key}"


def test_registry_config_is_monthly_with_uf_partition() -> None:
    cfg = get_config("sia_bi")
    assert cfg.monthly is True
    assert cfg.partition_by == ("ano", "uf", "mes")


def test_inventory_roundtrip() -> None:
    scope, dataset = parse_filename("BIRR2401.dbc")
    assert dataset == "sia_bi"
    assert scope == ScopeKey(uf="RR", ano=2024, mes=1)
    assert scope_to_filename("sia_bi", scope) == "BIRR2401.dbc"


def test_ftp_path_points_to_siasus() -> None:
    remote_dir, filename = ftp_path_for("sia_bi", ScopeKey(uf="RR", ano=2024, mes=1))
    assert remote_dir == "/dissemin/publicos/SIASUS/200801_/Dados"
    assert filename == "BIRR2401.dbc"


def test_parse_real_fixture_preserves_encrypted_cns(dbc_fixture) -> None:
    """Parsing must not crash on cipher bytes and must keep them intact."""
    dbc_path = dbc_fixture("sia_bi_rr_2024_01_mini")
    lf = dbc_bytes_to_lazyframe(dbc_path.read_bytes(), dataset="sia_bi", ano=2024, uf="RR")
    assert isinstance(lf, pl.LazyFrame)
    df = lf.collect()
    assert df.height == 12_099  # nrec measured from the DBF header
    assert "cns_pac" in df.columns
    # cipher alphabet is \x7b-\x84; latin-1 must preserve it 1:1
    sample = [v for v in df["cns_pac"].head(200).to_list() if v and v.strip()]
    assert sample, "expected non-blank CNS values in fixture"
    assert any(all("\x7b" <= ch <= "\x84" for ch in v) for v in sample)


def test_parse_fixture_decodes_dates_and_partitions(dbc_fixture) -> None:
    dbc_path = dbc_fixture("sia_bi_rr_2024_01_mini")
    df = dbc_bytes_to_lazyframe(
        dbc_path.read_bytes(), dataset="sia_bi", ano=2024, uf="RR"
    ).collect()
    assert df["ano"].unique().to_list() == [2024]
    assert df["uf"].unique().to_list() == ["RR"]
    # DTNASC is AAAAMMDD; measured 100% plausible in AC and RR
    nascs = [v for v in df["dtnasc"].head(100).to_list() if v]
    assert all(len(v) == 8 and v[:2] in ("19", "20") for v in nascs)

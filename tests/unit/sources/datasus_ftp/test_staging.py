from decimal import Decimal

import polars as pl
import pytest

from omnisus_db.sources.datasus_ftp import parse
from omnisus_db.sources.datasus_ftp.staging import dbc_bytes_to_parquet


def records(monkeypatch, values, batch=2):
    monkeypatch.setattr(parse.datasus_dbc, "decompress_bytes", lambda _: b"fake")
    monkeypatch.setattr(parse, "_stream_records", lambda *_args, **_kwargs: iter(values))
    monkeypatch.setattr(parse, "BATCH_ROWS", batch)


def test_null_first_and_missing_columns_are_preserved(monkeypatch, tmp_path):
    records(monkeypatch, [{"X": None}, {"X": None}, {"X": 2**60 + 1, "Y": "a"}])
    target = tmp_path / "output.parquet"
    result = dbc_bytes_to_parquet(b"x", target, dataset="sim_do", ano=2023, uf="RR", mes=1)
    df = pl.read_parquet(target)
    assert result.rows == 3 and result.bytes == target.stat().st_size
    assert df["x"].to_list() == [None, None, 2**60 + 1]
    assert df["y"].to_list() == [None, None, "a"]
    assert df["ano"].dtype == pl.UInt16
    assert df["mes"].to_list() == [1, 1, 1]
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize(
    "values,batch", [([1, 1.5], 2), ([2**60 + 1, 1.5], 1), ([Decimal("1.1"), 1], 2), ([1, "a"], 1)]
)
def test_incompatible_families_rejected_without_publishing(monkeypatch, tmp_path, values, batch):
    records(monkeypatch, [{"X": value} for value in values], batch)
    target = tmp_path / "output.parquet"
    target.write_bytes(b"previous")
    with pytest.raises((TypeError, ValueError)):
        dbc_bytes_to_parquet(b"x", target, dataset="sim_do", ano=2023, uf="RR")
    assert target.read_bytes() == b"previous"
    assert list(tmp_path.iterdir()) == [target]


def test_legacy_parser_rejects_lossy_batches(monkeypatch):
    records(monkeypatch, [{"X": 2**60 + 1}, {"X": 1.5}], 1)
    with pytest.raises((TypeError, ValueError)):
        parse.dbc_bytes_to_lazyframe(b"x", dataset="sim_do")


def test_fixture_multiple_batches_equivalent(dbc_fixture, monkeypatch, tmp_path):
    raw = dbc_fixture("sim_rr_2023_mini").read_bytes()
    expected = parse.dbc_bytes_to_lazyframe(raw, dataset="sim_do", ano=2023, uf="RR").collect()
    monkeypatch.setattr(parse, "BATCH_ROWS", 7)
    target = tmp_path / "output.parquet"
    dbc_bytes_to_parquet(raw, target, dataset="sim_do", ano=2023, uf="RR")
    assert pl.read_parquet(target).equals(expected)


def test_integrity_failure_does_not_publish(monkeypatch, tmp_path):
    records(monkeypatch, [{"X": 1}])

    def fail(*args, **kwargs):
        raise parse.DbfIntegrityError("early stop")

    monkeypatch.setattr(parse, "_check_record_count", fail)
    with pytest.raises(parse.DbfIntegrityError):
        dbc_bytes_to_parquet(b"x", tmp_path / "out.parquet", dataset="sim_do", ano=2023, uf="RR")
    assert not list(tmp_path.iterdir())


def test_cancelled_stream_cleans_spool_and_closes_generator(monkeypatch, tmp_path):
    records(monkeypatch, [], 1)
    closed = []

    def interrupted(*args, **kwargs):
        try:
            yield {"X": 1}
            raise KeyboardInterrupt()
        finally:
            closed.append(True)

    monkeypatch.setattr(parse, "_stream_records", interrupted)
    with pytest.raises(KeyboardInterrupt):
        dbc_bytes_to_parquet(b"x", tmp_path / "out.parquet", dataset="sim_do")
    assert closed == [True]
    assert not list(tmp_path.iterdir())


def test_empty_staging_preserves_partition_schema(monkeypatch, tmp_path):
    records(monkeypatch, [])
    target = tmp_path / "out.parquet"
    result = dbc_bytes_to_parquet(b"x", target, dataset="sim_do", ano=2023, uf="RR")
    assert result.rows == 0
    assert pl.read_parquet(target)["ano"].dtype == pl.UInt16

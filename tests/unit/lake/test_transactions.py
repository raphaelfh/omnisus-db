import asyncio

import polars as pl
import pytest

from omnisus_db.lake import Lake
from tests.helpers.connection_faults import FaultyConnection


class CleanupInterrupted(BaseException):
    pass


def test_schema_cache_recovers_after_rollback(tmp_path):
    with Lake.local(f"ducklake:{tmp_path}/cache.ducklake") as lake:
        lake.ingest("sample", pl.DataFrame({"i": [1]}).lazy())
        frame = pl.DataFrame({"i": [2], "new_column": [3]}).lazy()
        with pytest.raises(ValueError, match="abort"), lake.transaction():
            lake.ingest("sample", frame)
            raise ValueError("abort")
        lake.ingest("sample", frame)
        assert lake.connect().execute(
            "SELECT i, new_column FROM lake.sample ORDER BY i"
        ).fetchall() == [(1, None), (2, 3)]


@pytest.mark.parametrize("timing", ["before", "after"])
def test_commit_failure_invalidates_handle(tmp_path, timing):
    from omnisus_db.lake import CommitOutcomeUnknown

    with Lake.local(f"ducklake:{tmp_path}/commit.ducklake") as lake:
        original = lake.connect()
        injected = RuntimeError("commit acknowledgement failed")
        lake._con = FaultyConnection(original, **{timing: {"COMMIT": injected}})
        with pytest.raises(CommitOutcomeUnknown) as caught, lake.transaction():
            lake.connect().execute("CREATE TABLE lake.sample(i INTEGER)")
            lake.connect().execute("INSERT INTO lake.sample VALUES (1)")
        assert caught.value.__cause__ is injected
        assert lake.is_usable is False
        with pytest.raises(RuntimeError, match="unusable"):
            lake.connect()
        for operation in (
            lake.tables,
            lake.snapshots,
            lake.bootstrap_auxiliares,
            lake.ensure_aux_cnes_view,
            lambda: lake.optimize("sample"),
            lake.vacuum,
        ):
            with pytest.raises(RuntimeError, match="unusable"):
                operation()
        if timing == "after":
            assert original.execute("SELECT * FROM lake.sample").fetchall() == [(1,)]


def test_failed_rollback_preserves_original_cause(tmp_path):
    from omnisus_db.lake import TransactionStateError

    with Lake.local(f"ducklake:{tmp_path}/rollback.ducklake") as lake:
        lake._con = FaultyConnection(
            lake.connect(), before={"ROLLBACK": RuntimeError("rollback unavailable")}
        )
        original = ValueError("bad input")
        with pytest.raises(TransactionStateError) as caught, lake.transaction():
            raise original
        assert caught.value.__cause__ is original
        assert lake.is_usable is False


def test_begin_failure_stops_the_handle(tmp_path):
    from omnisus_db.lake import TransactionStateError

    with Lake.local(f"ducklake:{tmp_path}/begin.ducklake") as lake:
        injected = RuntimeError("cannot begin")
        lake._con = FaultyConnection(lake.connect(), before={"BEGIN": injected})
        with pytest.raises(TransactionStateError) as caught, lake.transaction():
            pytest.fail("body must not run")
        assert caught.value.__cause__ is injected
        assert not lake.is_usable


@pytest.mark.parametrize("signal", [asyncio.CancelledError(), KeyboardInterrupt(), SystemExit()])
def test_begin_interruption_preserves_signal_and_invalidates_handle(tmp_path, signal):
    with Lake.local(f"ducklake:{tmp_path}/begin-interrupted.ducklake") as lake:
        lake._con = FaultyConnection(lake.connect(), before={"BEGIN": signal})
        with pytest.raises(type(signal)) as caught, lake.transaction():
            pytest.fail("body must not run")
        assert caught.value is signal
        assert lake.is_usable is False


@pytest.mark.parametrize("signal", [asyncio.CancelledError(), KeyboardInterrupt(), SystemExit()])
def test_rollback_interruption_preserves_original_signal(tmp_path, signal):
    with Lake.local(f"ducklake:{tmp_path}/rollback-interrupted.ducklake") as lake:
        cleanup_signal = CleanupInterrupted()
        lake._con = FaultyConnection(lake.connect(), before={"ROLLBACK": cleanup_signal})
        with pytest.raises(type(signal)) as caught, lake.transaction():
            raise signal
        assert caught.value is signal
        assert lake.is_usable is False


def test_empty_and_nested_transactions(tmp_path):
    lake = Lake.local(f"ducklake:{tmp_path}/empty.ducklake")
    with lake.transaction() as receipt:
        assert receipt.committed is False
        with pytest.raises(RuntimeError, match="nested"), lake.transaction():
            pass
    assert receipt.committed is True
    assert receipt.snapshot_id is None
    lake.close()
    lake.close()
    assert lake.is_usable is False

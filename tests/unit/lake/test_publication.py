import hashlib
import multiprocessing

import polars as pl
import pytest

from omnisus_db.lake import Lake
from omnisus_db.sources._base import ScopeKey


def _try_writer(target, queue):
    try:
        with Lake.local(target):
            queue.put("opened")
    except Exception as exc:
        queue.put(type(exc).__name__)


def test_second_process_writer_rejected_and_released(tmp_path):
    target = f"ducklake:{tmp_path}/p.ducklake"
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    with Lake.local(target):
        process = context.Process(target=_try_writer, args=(target, queue))
        process.start()
        process.join(15)
        assert not process.is_alive()
        assert queue.get(timeout=2) == "WriterBusyError"
    with Lake.local(target) as lake:
        lake.ingest("t", pl.DataFrame({"x": [1]}).lazy())


def test_same_process_handle_and_symlink_are_locked(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    with Lake.local(f"ducklake:{real}/p.ducklake"), pytest.raises(Exception, match="writer"):
        Lake.local(f"ducklake:{alias}/p.ducklake")


def _publish(lake, tmp_path, uf="SP", value=1, policy="append", digest=None, run_id="run-1"):
    path = tmp_path / f"{uf}-{value}.parquet"
    pl.DataFrame({"ano": [2024], "mes": [1], "uf": [uf], "v": [value]}).write_parquet(path)
    return lake.publish_scope(
        "t",
        path,
        scope=ScopeKey(uf=uf, ano=2024, mes=1),
        source_sha256=digest or hashlib.sha256(str(value).encode()).hexdigest(),
        parser_version="parser-v1",
        policy=policy,
        run_id=run_id,
        partition_by=("ano", "mes"),
    )


def test_skip_same_and_changed_version(tmp_path):
    with Lake.local(f"ducklake:{tmp_path}/p.ducklake") as lake:
        result = _publish(lake, tmp_path)
        assert result.run_id == "run-1"
        assert _publish(lake, tmp_path, policy="skip_same") is None
        with pytest.raises(ValueError, match=r"different|version"):
            _publish(lake, tmp_path, value=2, policy="skip_same")
        assert lake.connect().execute("SELECT v FROM lake.t").fetchall() == [(1,)]
        assert len(lake.publications(run_id="run-1")) == 1


def test_replace_preserves_other_uf_and_manifest(tmp_path):
    with Lake.local(f"ducklake:{tmp_path}/p.ducklake") as lake:
        _publish(lake, tmp_path)
        _publish(lake, tmp_path, uf="RJ", value=3)
        _publish(lake, tmp_path, value=2, policy="replace")
        assert lake.connect().execute("SELECT uf,v FROM lake.t ORDER BY uf").fetchall() == [
            ("RJ", 3),
            ("SP", 2),
        ]
        records = lake.publications()
        assert len(records) == 3
        assert sum(r["active"] for r in records) == 2


def test_replace_invalid_scope_or_empty_preserves_data(tmp_path):
    with Lake.local(f"ducklake:{tmp_path}/p.ducklake") as lake:
        _publish(lake, tmp_path)
        for frame in [
            pl.DataFrame({"ano": [2024], "mes": [1], "uf": ["RJ"], "v": [9]}),
            pl.DataFrame(
                schema={"ano": pl.Int64, "mes": pl.Int64, "uf": pl.String, "v": pl.Int64}
            ),
        ]:
            path = tmp_path / "bad.parquet"
            frame.write_parquet(path)
            with pytest.raises(ValueError, match=r"scope|empty"):
                lake.publish_scope(
                    "t",
                    path,
                    scope=ScopeKey(uf="SP", ano=2024, mes=1),
                    source_sha256="a" * 64,
                    parser_version="v1",
                    policy="replace",
                )
        assert lake.connect().execute("SELECT v FROM lake.t").fetchall() == [(1,)]


def test_legacy_rows_not_declared_managed_by_append(tmp_path):
    with Lake.local(f"ducklake:{tmp_path}/p.ducklake") as lake:
        lake.ingest("t", pl.DataFrame({"ano": [2024], "mes": [1], "uf": ["SP"], "v": [9]}).lazy())
        _publish(lake, tmp_path)
        with pytest.raises(ValueError, match=r"legacy|unmanaged"):
            _publish(lake, tmp_path, value=2, policy="replace")
        assert lake.connect().execute("SELECT count(*) FROM lake.t").fetchone()[0] == 2


def test_publication_and_rows_rollback_together(tmp_path):
    with Lake.local(f"ducklake:{tmp_path}/p.ducklake") as lake:
        _publish(lake, tmp_path)
        with pytest.raises(RuntimeError), lake.transaction():
            _publish(lake, tmp_path, value=2, policy="replace", run_id="rollback")
            raise RuntimeError("abort")
        assert lake.connect().execute("SELECT v FROM lake.t").fetchall() == [(1,)]
        assert lake.publications(run_id="rollback") == []


def test_lost_commit_confirmation_can_be_reconciled(tmp_path):
    from omnisus_db.lake import CommitOutcomeUnknown
    from tests.helpers.connection_faults import FaultyConnection

    target = f"ducklake:{tmp_path}/lost.ducklake"
    with Lake.local(target) as lake:
        lake._con = FaultyConnection(
            lake.connect(), after={"COMMIT": RuntimeError("confirmation lost")}
        )
        with pytest.raises(CommitOutcomeUnknown):
            _publish(lake, tmp_path, run_id="recover-me")
    with Lake.local(target) as reopened:
        records = reopened.publications(run_id="recover-me")
        assert len(records) == 1 and records[0]["rows"] == 1
        assert reopened.connect().execute("SELECT v FROM lake.t").fetchall() == [(1,)]


def _publish_national(lake, tmp_path, ano=2023, value=1):
    path = tmp_path / f"BR-{ano}.parquet"
    pl.DataFrame({"_source_ano": [ano], "v": [value]}).write_parquet(path)
    return lake.publish_scope(
        "n",
        path,
        scope=ScopeKey(uf=None, ano=ano),
        source_sha256=hashlib.sha256(f"BR{ano}".encode()).hexdigest(),
        parser_version="parser-v1",
        run_id="national",
        partition_by=("_source_ano",),
    )


def test_publications_carry_a_decoded_scope(tmp_path):
    """The app decoded scope_json itself, including our private _source_ano
    encoding. The package now hands back the ScopeKey it wrote."""
    with Lake.local(f"ducklake:{tmp_path}/s.ducklake") as lake:
        _publish(lake, tmp_path)
        _publish_national(lake, tmp_path)
        scopes = {r["dataset"]: r["scope"] for r in lake.publications()}
        assert scopes == {
            "t": ScopeKey(uf="SP", ano=2024, mes=1),
            "n": ScopeKey(uf=None, ano=2023),
        }


def test_scope_from_fields_rejects_shapes_this_version_never_writes():
    from omnisus_db.lake.publication import scope_from_fields

    assert scope_from_fields({"ano": 2024, "uf": "SP"}) == ScopeKey(uf="SP", ano=2024)
    assert scope_from_fields({"_source_ano": 2023}) == ScopeKey(uf=None, ano=2023)
    assert scope_from_fields({"product": "estimate", "ano": 2024}) is None
    assert scope_from_fields({"ano": "2024", "uf": "SP"}) is None


def test_parser_version_change_is_not_skip_same(tmp_path):
    with Lake.local(f"ducklake:{tmp_path}/v.ducklake") as lake:
        _publish(lake, tmp_path)
        with pytest.raises(ValueError, match="version"):
            lake.publish_scope(
                "t",
                tmp_path / "SP-1.parquet",
                scope=ScopeKey(uf="SP", ano=2024, mes=1),
                source_sha256=hashlib.sha256(b"1").hexdigest(),
                parser_version="parser-v2",
                policy="skip_same",
            )

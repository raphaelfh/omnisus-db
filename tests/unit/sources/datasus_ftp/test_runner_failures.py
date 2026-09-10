import pytest

from omnisus_db.lake import Lake
from omnisus_db.sources._base import ScopeKey
from omnisus_db.sources.datasus_ftp._runner import run_scopes
from tests.helpers.connection_faults import FaultyConnection


@pytest.mark.asyncio
@pytest.mark.parametrize("years", [(2022,), (2021, 2022, 2023)])
async def test_bad_dbc_is_never_omitted(tmp_path, monkeypatch, dbc_fixture, years):
    raw = dbc_fixture("sim_rr_2023_mini").read_bytes()

    async def fetch(*, dataset, scope):
        return b"invalid dbc" if scope.ano == 2022 else raw

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fetch)
    scopes = [ScopeKey(uf="RR", ano=year) for year in years]
    with Lake.local(f"ducklake:{tmp_path}/mixed.ducklake") as lake:
        report = await run_scopes("sim_do", scopes=scopes, lake=lake, concurrency=1, batch_size=2)
        assert [outcome.scope for outcome in report.outcomes] == scopes
        expected = ["failed"] if len(years) == 1 else ["failed", "failed", "ok"]
        assert [outcome.status for outcome in report.outcomes] == expected
        if len(years) == 1:
            assert report.rows == 0
        else:
            stored = (
                lake.connect()
                .execute("SELECT ano, count(*) FROM lake.sim_do GROUP BY ano")
                .fetchall()
            )
            assert stored == [(2023, report.rows)]
            assert report.rows > 0


@pytest.mark.asyncio
async def test_repeated_input_positions_are_preserved(tmp_path, monkeypatch, dbc_fixture):
    raw = dbc_fixture("sim_rr_2023_mini").read_bytes()

    async def fetch(**kwargs):
        return raw

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fetch)
    scope = ScopeKey(uf="RR", ano=2023)
    with Lake.local(f"ducklake:{tmp_path}/repeat.ducklake") as lake:
        report = await run_scopes("sim_do", scopes=[scope, scope], lake=lake)
        assert [outcome.scope for outcome in report.outcomes] == [scope, scope]
        assert len(report.ok) == 2
        assert (
            lake.connect().execute("SELECT count(*) FROM lake.sim_do").fetchone()[0] == report.rows
        )


@pytest.mark.asyncio
async def test_commit_unknown_aborts_without_retry(tmp_path, monkeypatch, dbc_fixture):
    from omnisus_db import ImportAbortedError

    raw = dbc_fixture("sim_rr_2023_mini").read_bytes()

    async def fetch(**kwargs):
        return raw

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fetch)
    scopes = [ScopeKey(uf="RR", ano=year) for year in (2021, 2022)]
    with Lake.local(f"ducklake:{tmp_path}/unknown.ducklake") as lake:
        real = lake.connect()
        lake._con = FaultyConnection(real, after={"COMMIT": RuntimeError("ack lost")})
        with pytest.raises(ImportAbortedError) as caught:
            await run_scopes("sim_do", scopes=scopes, lake=lake, batch_size=1, concurrency=1)
        assert caught.value.report.rows == 0
        assert caught.value.unresolved == tuple(enumerate(scopes))
        assert real.execute("SELECT DISTINCT ano FROM lake.sim_do").fetchall() == [(2021,)]
        assert not lake.is_usable


@pytest.mark.asyncio
async def test_abort_keeps_previously_committed_progress(tmp_path, monkeypatch, dbc_fixture):
    from omnisus_db import ImportAbortedError

    raw = dbc_fixture("sim_rr_2023_mini").read_bytes()

    async def fetch(**kwargs):
        return raw

    class FailSecondCommit(FaultyConnection):
        commits = 0

        def execute(self, sql, parameters=None):
            if sql.strip().upper() == "COMMIT":
                self.commits += 1
                if self.commits == 2:
                    raise RuntimeError("second commit unavailable")
            return super().execute(sql, parameters)

    monkeypatch.setattr("omnisus_db.sources.datasus_ftp._runner.fetch_dbc_bytes", fetch)
    scopes = [ScopeKey(uf="RR", ano=year) for year in (2021, 2022, 2023)]
    with Lake.local(f"ducklake:{tmp_path}/partial.ducklake") as lake:
        lake._con = FailSecondCommit(lake.connect())
        with pytest.raises(ImportAbortedError) as caught:
            await run_scopes("sim_do", scopes=scopes, lake=lake, batch_size=1, concurrency=1)
        assert [outcome.scope for outcome in caught.value.report.ok] == scopes[:1]
        assert caught.value.report.rows > 0
        assert caught.value.unresolved == ((1, scopes[1]), (2, scopes[2]))

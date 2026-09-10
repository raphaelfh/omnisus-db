"""Adversarial audit controls. Creates temporary lakes; does not change source."""

import contextlib
import hashlib
import json
import logging
import subprocess
import tempfile
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import polars as pl
import structlog

import omnisus_db as odb
from omnisus_db.lake import Lake
from omnisus_db.sources.cnes.importers.master import _ensure_master_table, _upsert_master

ROOT = Path(__file__).resolve().parents[4]
BASE = "e681aceb869004dc192c4aaa588a51adc6d54ac7"
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL))


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def file_hashes():
    paths = [
        *(ROOT / "src").rglob("*.py"),
        ROOT / "pyproject.toml",
        ROOT / "uv.lock",
        ROOT / ".github/workflows/release.yml",
        ROOT / ".github/workflows/test.yml",
    ]
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
    }


def release_state(revision):
    def read(path):
        return git("show", f"{revision}:{path}")

    return {
        "requires_python": tomllib.loads(read("pyproject.toml"))["project"]["requires-python"],
        "lock_requires_python": tomllib.loads(read("uv.lock"))["requires-python"],
        "gate_commands": [
            line.strip()
            for line in read(".github/workflows/release.yml").splitlines()
            if "uv python install" in line or "uv venv -p" in line
        ],
    }


def snapshot_control(tmp):
    with Lake.local(f"ducklake:{tmp}/snapshot") as lake:
        direct = lake.ingest("t", pl.DataFrame({"v": [1]}).lazy())
        direct_committed = lake.snapshots()[-1]["snapshot_id"]
        with lake.transaction():
            batched = lake.ingest("t", pl.DataFrame({"v": [2]}).lazy())
        return {
            "direct_reported": direct.snapshot_id,
            "direct_committed": direct_committed,
            "batched_reported": batched.snapshot_id,
            "batched_committed": lake.snapshots()[-1]["snapshot_id"],
        }


def upsert_control(tmp):
    results = {}
    for atomic in (False, True):
        with Lake.local(f"ducklake:{tmp}/upsert-{atomic}") as lake:
            _ensure_master_table(lake)
            rows = [
                {
                    "cnes": "1234567",
                    "nome": "Synthetic control",
                    "nome_fantasia": None,
                    "razao_social": None,
                }
            ]
            _upsert_master(lake, rows)
            con = lake.connect()

            class FailInsert:
                def __init__(self, connection):
                    self.connection = connection

                def execute(self, *args, **kwargs):
                    return self.connection.execute(*args, **kwargs)

                def executemany(self, *_args, **_kwargs):
                    raise RuntimeError("same injected failure in both arms")

            with (
                contextlib.suppress(RuntimeError),
                patch.object(lake, "connect", return_value=FailInsert(con)),
                lake.transaction() if atomic else contextlib.nullcontext(),
            ):
                _upsert_master(lake, rows)
            results[str(atomic)] = con.execute("SELECT count(*) FROM lake.cnes_master").fetchone()[
                0
            ]
    return results


def parser_failure_control(tmp):
    raw = (ROOT / "tests/fixtures/dbc/sim_rr_2023_mini.dbc").read_bytes()

    def fetch(_remote_dir, filename, _timeout):
        return b"bad DBC" if "2022" in filename else raw

    with patch("omnisus_db.sources.datasus_ftp.fetch._blocking_fetch", side_effect=fetch):
        result = odb.import_dataset(
            "sim_do",
            scopes=[odb.ScopeKey("RR", year) for year in (2021, 2022, 2023)],
            target=f"ducklake:{tmp}/partial",
            concurrency=1,
            batch_size=2,
        )
    with Lake.local(f"ducklake:{tmp}/partial") as lake:
        stored = (
            lake.connect()
            .execute("SELECT ano, count(*) FROM lake.sim_do GROUP BY ano ORDER BY ano")
            .fetchall()
        )
    return {
        "requested_years": [2021, 2022, 2023],
        "outcomes": [{"year": o.scope.ano, "status": o.status} for o in result.outcomes],
        "stored_year_counts": stored,
    }


def numeric_order_control(tmp):
    results = {}
    for first_float in (False, True):
        frames = [pl.DataFrame({"v": [1]}), pl.DataFrame({"v": [1.75]})]
        if first_float:
            frames.reverse()
        with Lake.local(f"ducklake:{tmp}/types-{first_float}") as lake:
            for frame in frames:
                lake.ingest("t", frame.lazy())
            results[str(first_float)] = {
                "values": lake.connect().execute("SELECT v FROM lake.t ORDER BY v").fetchall(),
                "schema": lake.connect().execute("DESCRIBE lake.t").fetchall(),
            }
    return results


started = datetime.now(UTC).isoformat()
head = git("rev-parse", "HEAD")
before = file_hashes()
assert Path(odb.__file__).resolve() == ROOT / "src/omnisus_db/__init__.py"
with tempfile.TemporaryDirectory(prefix="omnisus-adversarial-") as directory:
    temp = Path(directory)
    results = {
        "snapshot_control": snapshot_control(temp),
        "upsert_control_without_vs_with_transaction": upsert_control(temp),
        "partial_batch": parser_failure_control(temp),
        "numeric_order_control_int_first_vs_float_first": numeric_order_control(temp),
    }
after = file_hashes()
assert git("rev-parse", "HEAD") == head, "HEAD changed during audit"
assert before == after, "Source/config files changed during audit"
print(
    json.dumps(
        {
            "started_at": started,
            "finished_at": datetime.now(UTC).isoformat(),
            "original_report_commit": BASE,
            "current_commit": head,
            "imported_package": odb.__file__,
            "files_sha256": before,
            "source_and_tests_changed_since_original_commit": git(
                "diff", "--name-only", BASE, head, "--", "src", "tests"
            ),
            "release_at_original_commit": release_state(BASE),
            "release_at_current_commit": release_state(head),
            "results": results,
        },
        indent=2,
        ensure_ascii=False,
        default=str,
    )
)

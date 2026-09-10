"""Performance presentation must preserve the benchmark's measurement boundaries."""

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "notebooks"))
from _performance_dbf import comparison_rows, measurement_rows, measurement_svg  # noqa: E402


@pytest.fixture
def report():
    return json.loads((ROOT / "reports/rust-dbf-performance.json").read_text())


def test_real_report_keeps_all_measured_runs_and_phase_boundaries(report):
    rows = measurement_rows(report)
    assert len(rows) == 168  # 4 corpora x 3 phases x 2 backends x 7 rounds
    assert len(comparison_rows(rows)) == 12
    assert {r["phase"] for r in rows if r["amplified"]} == {
        "dbf_to_arrow",
        "dbf_to_parquet",
        "lake_publication",
    }
    assert {r["phase"] for r in rows if not r["amplified"]} == {
        "dbf_to_arrow",
        "dbc_to_parquet",
        "lake_publication",
    }


def test_medians_exclude_warmups_and_ignore_cached_summaries(report):
    report = copy.deepcopy(report)
    phase = report["cases"][0]["phases"][0]
    for warmup in phase["warmups"]:
        warmup["seconds"] = 1e9
    for run in phase["runs"]:
        run["seconds"] = (run["round"] + 1) * (0.002 if run["mode"] == "python" else 0.001)
    phase["summary"] = {}
    first = comparison_rows(measurement_rows(report))[0]
    assert first["python_ms"] == 8
    assert first["rust_ms"] == 4
    assert first["speedup"] == 2


@pytest.mark.parametrize("failure", ["incomplete", "mismatch", "missing_round"])
def test_invalid_evidence_is_not_presented_as_success(report, failure):
    if failure == "incomplete":
        report["completed"] = False
    elif failure == "mismatch":
        report["cases"][0]["phases"][0]["runs"][0]["matches_reference"] = False
    else:
        report["cases"][0]["phases"][0]["runs"].pop()
    with pytest.raises(ValueError):
        measurement_rows(report)


def test_zero_disk_chart_is_valid_and_labels_are_escaped(report):
    rows = measurement_rows(report)[:14]
    for row in rows:
        row["disk_mib"] = 0
    svg = measurement_svg(rows, "disk_mib", "<disco>", "MiB")
    assert "<svg" in svg and "nan" not in svg and "inf" not in svg
    assert "&lt;disco&gt;" in svg
    assert "<disco>" not in svg

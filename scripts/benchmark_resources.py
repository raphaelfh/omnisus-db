"""Isolated baseline/staging benchmark; no nationwide performance inference.

Run: PYTHONPATH=src .venv/bin/python scripts/benchmark_resources.py --repeat 12
The amplified case repeats real decompressed SIM records and patches nrec. It
is deterministic DBF, not a new DBC compression sample; both workers bypass
DBC decompression for this case. Small fixtures exercise real decompression.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import datasus_dbc
import polars as pl
import pyarrow.parquet as pq

from omnisus_db.sources.datasus_ftp import parse
from omnisus_db.sources.datasus_ftp.staging import dbc_bytes_to_parquet
from omnisus_db.transforms.dictionaries import load_dicionario

ROOT = Path(__file__).resolve().parents[1]


def worker(args):
    # Match batches to the production default, allow a smaller value for probes.
    parse.BATCH_ROWS = args.batch_rows
    raw = Path(args.input).read_bytes()
    if args.dbf:
        parse.datasus_dbc.decompress_bytes = lambda _: raw
    with tempfile.TemporaryDirectory(prefix="dbc-bench-") as directory:
        tempfile.tempdir = directory
        root = Path(directory)
        target = root / "output.parquet"
        peak_disk = 0
        stopped = threading.Event()

        def monitor():
            nonlocal peak_disk
            while not stopped.is_set():
                total = 0
                for path in root.rglob("*"):
                    try:
                        if path.is_file():
                            total += path.stat().st_size
                    except FileNotFoundError:
                        pass
                peak_disk = max(peak_disk, total)
                stopped.wait(0.005)

        thread = threading.Thread(target=monitor)
        thread.start()
        start = time.perf_counter()
        try:
            if args.worker == "baseline":
                # Historical parser, followed by the old Lake Parquet sink.
                dic = load_dicionario(args.dataset)
                dbf = datasus_dbc.decompress_bytes(raw)
                parse._check_dbf_length(dbf, dataset=args.dataset)
                batches, buffer, count = [], [], 0
                for rec in parse._stream_records(dbf, encoding=dic.encoding):
                    count += 1
                    buffer.append(rec)
                    if len(buffer) >= parse.BATCH_ROWS:
                        batches.append(pl.DataFrame(buffer, infer_schema_length=None))
                        buffer.clear()
                if buffer:
                    batches.append(pl.DataFrame(buffer, infer_schema_length=None))
                parse._check_record_count(dbf, count, dataset=args.dataset)
                df = pl.concat(batches, how="diagonal_relaxed")
                df = df.rename({c: c.lower() for c in df.columns}).with_columns(
                    pl.lit(2023).cast(pl.UInt16).alias("ano"), pl.lit("RR").alias("uf")
                )
                df.lazy().sink_parquet(target)
            else:
                dbc_bytes_to_parquet(raw, target, dataset=args.dataset, ano=2023, uf="RR")
            seconds = time.perf_counter() - start
            # Sample RSS before equivalence hashing so that validation does not
            # contaminate measured pipeline memory.
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform != "darwin":
                rss *= 1024
            peak_disk = max(peak_disk, target.stat().st_size)
        finally:
            stopped.set()
            thread.join()
        # Streaming ordered rows, with normalized logical Polars schema.
        parquet = pq.ParquetFile(target)
        digest = hashlib.sha256()
        for batch in parquet.iter_batches(batch_size=1024):
            for row in batch.to_pylist():
                digest.update(
                    (
                        json.dumps(row, default=str, ensure_ascii=False, sort_keys=True) + "\n"
                    ).encode()
                )
        print(
            json.dumps(
                {
                    "mode": args.worker,
                    "seconds": seconds,
                    "peak_rss_bytes": rss,
                    "peak_temp_disk_bytes_sampled": peak_disk,
                    "temp_sample_interval_ms": 5,
                    "output_bytes": target.stat().st_size,
                    "rows": parquet.metadata.num_rows,
                    "ordered_rows_sha256": digest.hexdigest(),
                    "schema": {
                        name: str(dtype) for name, dtype in pl.read_parquet_schema(target).items()
                    },
                }
            )
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=["baseline", "staging"])
    parser.add_argument("--input")
    parser.add_argument("--dataset", default="sim_do")
    parser.add_argument("--dbf", action="store_true")
    parser.add_argument("--repeat", type=int, default=12)
    parser.add_argument("--batch-rows", type=int, default=100_000)
    parser.add_argument("--output", type=Path, default=ROOT / "reports/benchmark-d6.json")
    args = parser.parse_args()
    if args.worker:
        worker(args)
        return
    fixture = ROOT / "tests/fixtures/dbc/sim_rr_2023_mini.dbc"
    raw = fixture.read_bytes()
    dbf = datasus_dbc.decompress_bytes(raw)
    nrec, header, length = parse._read_dbf_geometry(dbf)
    patched = bytearray(dbf[:header])
    patched[4:8] = (nrec * args.repeat).to_bytes(4, "little")
    amplified = bytes(patched) + dbf[header : header + nrec * length] * args.repeat + b"\x1a"
    results = []
    with tempfile.TemporaryDirectory(prefix="dbc-corpus-") as directory:
        synthetic = Path(directory) / "amplified.dbf"
        synthetic.write_bytes(amplified)
        for name, path, is_dbf in [
            ("sim_rr_2023_mini", fixture, False),
            ("sim_dbf_amplified", synthetic, True),
        ]:
            case = {
                "corpus": name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "input_bytes": path.stat().st_size,
                "repeat": args.repeat if is_dbf else 1,
                "decompression": "bypassed; deterministic repeated DBF records"
                if is_dbf
                else "real DBC",
                "runs": [],
            }
            for mode in ["baseline", "staging"]:
                command = [
                    sys.executable,
                    __file__,
                    "--worker",
                    mode,
                    "--input",
                    str(path),
                    "--batch-rows",
                    str(args.batch_rows),
                ]
                if is_dbf:
                    command.append("--dbf")
                process = subprocess.run(
                    command, check=True, capture_output=True, text=True, env=os.environ.copy()
                )
                case["runs"].append(json.loads(process.stdout.strip().splitlines()[-1]))
            old, new = case["runs"]
            case["equivalent"] = all(
                old[key] == new[key] for key in ["rows", "schema", "ordered_rows_sha256"]
            )
            if not case["equivalent"]:
                raise AssertionError(f"Equivalence failed for {name}")
            results.append(case)
    evidence = {
        "python": sys.version,
        "platform": sys.platform,
        "batch_rows": args.batch_rows,
        "limitations": [
            "Single run per mode, separate fresh processes; no statistical confidence interval.",
            "Peak temp disk is sampled every 5 ms and is a lower bound.",
            "Amplified corpus repeats one municipal fixture and does not represent nationwide heterogeneity.",
            "DBC decompression still materializes the full DBF.",
        ],
        "cases": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()

# Task 4 — D6 staging and resource evidence

Implemented `sources/datasus_ftp/staging.py::dbc_bytes_to_parquet(raw, path, *, dataset, ano=None, uf=None, dictionary=None, mes=None)` returning immutable `StagingResult(rows, bytes)`. Parent integrates runner/Lake.

The parser spools one Arrow IPC file per batch, reconciles schema, and writes Parquet in a second bounded pass. No frame list accumulates. Null-first/absent columns preserve values; value-family validation precedes Arrow inference, so integers cannot silently become float/string even within one batch. Cross-family changes fail; supported widening remains in-family. DBF length and parsed/deleted-count checks precede atomic replacement of target. Existing targets survive error. Cancellation cleans spools and closes record generator. Legacy LazyFrame materializes Parquet before temporary removal, retaining the `_stream_records` and explicit `parse.datasus_dbc` monkeypatch seams.

## Tests (RED / GREEN)

- RED: newly added staging suite failed collection with ModuleNotFoundError for the missing staging API.
- GREEN: `PYTHONPATH=src .venv/bin/python -m pytest tests/unit/sources/datasus_ftp/test_staging.py tests/unit/sources/datasus_ftp/test_parse.py tests/unit/sources/datasus_ftp/test_integrity.py -q`: **20 passed**.
- Cases cover multi-batch fixture equality, >2^60 integer preservation, null-first/missing fields, same/across-batch incompatible families, old LazyFrame loss prevention, integrity failure, cancellation cleanup, empty partition schema. Existing integrity suite also exercises actual truncation, embedded EOF and deleted rows through staging.
- Ruff check clean for all four owned Python files. During cleanup Ruff initially removed the decompression seam as unused; explicit re-export fixed it and all 20 tests were rerun successfully.

## Benchmark

Fresh subprocess per mode; historical materialized parser (including historical diagonal_relaxed) followed by Parquet sink versus new staging directly. This intentionally retains the old behavior only in the benchmark baseline. Ordered row SHA-256 and logical schema match for each pair. Full corpus hashes, output sizes, schema, timings and environment are in the JSON artifacts.

### benchmark-d6.json — batch_rows=10000

| Corpus | Rows | Mode | Seconds | Peak RSS MiB | Sampled temp MiB |
|---|---:|---|---:|---:|---:|
| sim_rr_2023_mini | 3311 | baseline | 0.129 | 178.8 | 1.5 |
| sim_rr_2023_mini | 3311 | staging | 0.204 | 142.5 | 1.7 |
| sim_dbf_amplified | 39732 | baseline | 1.102 | 359.1 | 18.6 |
| sim_dbf_amplified | 39732 | staging | 1.699 | 198.9 | 33.8 |

### benchmark-d6-default.json — batch_rows=100000

| Corpus | Rows | Mode | Seconds | Peak RSS MiB | Sampled temp MiB |
|---|---:|---|---:|---:|---:|
| sim_rr_2023_mini | 3311 | baseline | 0.132 | 178.9 | 1.5 |
| sim_rr_2023_mini | 3311 | staging | 0.201 | 142.7 | 1.7 |
| sim_dbf_amplified | 132440 | baseline | 3.705 | 1328.5 | 61.9 |
| sim_dbf_amplified | 132440 | staging | 6.571 | 758.0 | 112.5 |

Reproduce with:

```
PYTHONPATH=src .venv/bin/python scripts/benchmark_resources.py --repeat 12 --batch-rows 10000
PYTHONPATH=src .venv/bin/python scripts/benchmark_resources.py --repeat 40 --output reports/benchmark-d6-default.json
```

Limitations: one run per mode, no statistical interval; temp disk sampled every 5 ms is a lower bound. The larger corpus repeats SIM fixture DBF records and patches its record count; decompression is bypassed for that deterministic DBF case, while real DBC fixture exercises decompression. DBC decompression still materializes the complete DBF. Spooling adds disk and CPU; the compatibility LazyFrame still materializes the final dataset. These narrow local measurements provide no nationwide performance claim. A first overly large 500x exploratory invocation was interrupted before producing evidence; only completed 12x/40x runs are reported.

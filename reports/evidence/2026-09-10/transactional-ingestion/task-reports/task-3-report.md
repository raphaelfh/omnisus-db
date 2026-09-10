# Task 3 implementation report

## Implemented

- Added `ImportAbortedError`, carrying a committed partial `ImportReport` and the unresolved `(input_index, ScopeKey)` pairs, and exported it from the package root.
- Changed DATASUS runner accounting to track outcomes by input position before ingestion starts. Parse/ingest failures now remain visible, rolled-back provisional successes become failures, and repeated equal scopes retain their separate positions.
- Fatal transaction state failures now stop the run with `ImportAbortedError`. Previously committed outcomes remain in the partial report, while every possibly committed or not-yet-determined input remains unresolved and is never retried automatically.
- Moved the producer sentinel to normal completion so cancellation during a fatal consumer exit cannot block cleanup trying to enqueue it.

## TDD evidence

### RED: positional failure accounting

Command:

```text
uv run --locked --extra dev pytest tests/unit/sources/datasus_ftp/test_runner_failures.py -q
```

Relevant output before production changes:

```text
FF.
FAILED test_bad_dbc_is_never_omitted[years0]
  assert [] == [ScopeKey(uf='RR', ano=2022, mes=None)]
FAILED test_bad_dbc_is_never_omitted[years1]
  report omitted the 2022 input position
2 failed, 1 passed in 0.92s
```

This was the expected defect: the runner had no provisional outcome for the scope whose DBC parsing raised.

### RED: fatal transaction outcome

After adding the two commit-unknown tests, the same command produced:

```text
FF.FF
FAILED test_bad_dbc_is_never_omitted[years0]
FAILED test_bad_dbc_is_never_omitted[years1]
FAILED test_commit_unknown_aborts_without_retry
FAILED test_abort_keeps_previously_committed_progress
4 failed, 1 passed in 0.94s
```

The fatal tests failed because `ImportAbortedError` was not yet defined or exported, as expected.

### GREEN

Focused command:

```text
uv run --locked --extra dev pytest tests/unit/sources/datasus_ftp/test_runner_failures.py -q
..... [100%]
5 passed in 1.42s
```

Python 3.12 compatibility command:

```text
uv run --python 3.12 --locked --extra dev pytest tests/unit/sources/datasus_ftp/test_runner_failures.py -q
Using CPython 3.12.13
..... [100%]
5 passed in 7.82s
```

Selected regressions:

```text
uv run --locked --extra dev pytest tests/unit/sources/datasus_ftp/test_runner_failures.py tests/unit/sources/datasus_ftp/test_tolerance.py tests/unit/sources/datasus_ftp/test_runner_concurrency.py tests/unit/test_public_api.py -q
......................................... [100%]
41 passed in 12.41s
```

Required full selected suite:

```text
uv run --locked --extra dev pytest -m 'not e2e and not perf' -q
406 passed, 47 deselected in 25.54s
```

Scoped lint:

```text
uv run --locked --extra dev ruff check src/omnisus_db/sources/_base.py src/omnisus_db/sources/datasus_ftp/_runner.py src/omnisus_db/__init__.py tests/unit/sources/datasus_ftp/test_runner_failures.py
All checks passed!
```

Validated versions: Python 3.13.12, DuckDB 1.5.5, Polars 1.44.2, PyArrow 25.0.1. Python 3.12.13 was also verified with the focused suite. No live network data was used.

## Files changed

- `src/omnisus_db/sources/_base.py`
- `src/omnisus_db/sources/datasus_ftp/_runner.py`
- `src/omnisus_db/__init__.py`
- `tests/unit/sources/datasus_ftp/test_runner_failures.py`

## Self-review

- Confirmed all outcome maps use input indexes, so equality of repeated `ScopeKey` values cannot collapse inputs.
- Confirmed fatal accounting excludes every scope that entered the transaction write path, including the scope whose transaction state error was raised internally.
- Confirmed nonfatal parse failures are published while provisional successes from the same rolled-back batch become failures.
- Confirmed producer cancellation cannot wait on a sentinel enqueue after fatal exit.
- `git diff --check` and scoped Ruff checks passed. No unrelated files or dependency metadata were changed.

## Concerns

None.

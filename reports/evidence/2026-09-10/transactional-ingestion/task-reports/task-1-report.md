# Task 1 implementation report

## Implemented

- Added `TransactionReceipt`, `TransactionStateError`, and `CommitOutcomeUnknown`, with the required public error exports.
- Added explicit Lake transaction and lifecycle state, guarded access after close or invalidation, idempotent close, and snapshot receipt handling.
- Replaced the managed transaction boundary so rollback clears schema caches, nested transactions are rejected, commit failures invalidate the handle, and post-commit snapshot lookup cannot undo confirmed receipt state.
- Guarded `tables`, `snapshots`, `optimize`, `vacuum`, `bootstrap_auxiliares`, and `ensure_aux_cnes_view` against invalid handles.
- Applied the controller ruling to catch BEGIN and rollback-cleanup `BaseException` failures. `CancelledError`, `KeyboardInterrupt`, and `SystemExit` retain object identity; cleanup failures cannot replace the original signal; affected handles are invalidated.
- Added the one-shot real-connection fault seam and focused DuckLake regressions.

## TDD evidence

### RED

Command:

`uv run --locked --extra dev pytest tests/unit/lake/test_transactions.py -q`

Result: expected failure in 1.01s of pytest runtime (7.1s command wall time). The cache regression reached real DuckLake and failed with `Binder Error: Table "sample" does not have a column with name "new_column"`, independently confirming stale schema state after rollback. The other regressions failed on missing transaction error exports and missing `is_usable`; the unimplemented rollback interruption also escaped during cleanup. This was the expected pre-implementation behavior.

### GREEN

Command:

`uv run --locked --extra dev pytest tests/unit/lake/test_transactions.py -q`

Result: `12 passed in 0.91s` (4.2s command wall time).

## Task checks

- `uv run --locked --extra dev pytest tests/unit/lake/test_transactions.py tests/unit/lake/test_operations.py -q` — `22 passed in 1.08s` (parallel check batch completed in 5.6s).
- `uv run --locked --extra dev ruff check src/omnisus_db/lake tests/helpers tests/unit/lake/test_transactions.py` — `All checks passed!` (same 5.6s batch).
- `uv run --locked --extra dev mypy src` — `Success: no issues found in 36 source files` (same 5.6s batch).
- `uv run --locked --extra dev pytest -q` — `445 passed in 29.48s` (31.0s command wall time).
- After the commit hook mechanically reformatted two files, `uv run --locked --extra dev pytest tests/unit/lake/test_transactions.py -q` passed `12 passed in 0.70s`, and `ruff format --check` reported all 9 files formatted (4.2s combined command wall time).
- Python 3.12 validation was intentionally left to the controller's prepared final gate, per controller instruction; this task ran in the baseline Python 3.13.12 environment.

## Files changed

- `src/omnisus_db/lake/_transactions.py`
- `src/omnisus_db/lake/operations.py`
- `src/omnisus_db/lake/__init__.py`
- `tests/helpers/__init__.py`
- `tests/helpers/connection_faults.py`
- `tests/unit/lake/test_transactions.py`

## Self-review

- Confirmed the diff stays within the task's transaction boundary and guards; no ingestion-runner behavior or dependency files changed.
- Confirmed every realistic missing state transition is covered: cache cleanup, commit invalidation, rollback-failure invalidation and cause, BEGIN failure, control-flow signal identity, nesting, empty receipts, and idempotent close.
- The mandated `CommitOutcomeUnknown` name needs a narrow Ruff `N818` suppression because the public API intentionally omits an `Error` suffix.
- `git diff --check` is clean.

## Concerns

None.

## Commit

`e89b46b fix: make managed lake transactions recoverable`

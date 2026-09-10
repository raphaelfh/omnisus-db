# Task 2 report: publish snapshots only after commit

## Implementation

- `Lake.ingest` now validates the handle and owns a managed transaction for direct calls.
- Writes performed inside an existing `Lake.transaction()` create `ImportResult` with `snapshot_id=None` and register it in `_pending_results`.
- Task 1 transaction finalization fills all pending results after a successful commit; rollback leaves them unresolved.
- Removed the in-ingest `ducklake_snapshots` metadata query and updated the API docstring.
- Added coverage for committed batch snapshots, rollback results, and unavailable post-commit metadata.

## TDD evidence

### RED

Command:

```text
uv run --locked --extra dev pytest tests/unit/lake/test_transactions.py -k 'snapshot or pending' -q
```

Initial result: `3 failed, 12 deselected`. The three new tests failed because in-transaction results had snapshot IDs, rollback results retained an ID, and direct ingest still read the snapshot metadata in the old write path.

### GREEN

Command:

```text
uv run --locked --extra dev pytest tests/unit/lake/test_transactions.py -k 'snapshot or pending' -q
```

Result: `3 passed, 12 deselected`.

## Verification

```text
uv run --locked --extra dev pytest tests/unit/lake -q
55 passed in 2.38s

uv run --locked --extra dev mypy src
Success: no issues found in 36 source files

uv run --locked --extra dev pytest -m 'not e2e and not perf' -q
401 passed, 47 deselected in 24.26s
```

## Files changed

- `src/omnisus_db/lake/operations.py`
- `tests/unit/lake/test_transactions.py`
- `.superpowers/sdd/2026-09-09-transactional-ingestion/task-2-report.md`

## Self-review

The direct-call recursion enters the transaction exactly once, pending results are appended only after the insert succeeds, and Task 1 clears pending state in its `finally` block after assigning committed snapshot IDs. No unrelated files or dependencies were changed. `git diff --check` passed.

## Concerns

None.

## Round 1 fix

Strengthened `test_ingest_reports_a_real_snapshot_id` in
`tests/unit/lake/test_ingest_performance.py` to assert that a direct ingest
creates exactly one new snapshot and that the returned ID matches the latest
committed history entry. Existing snapshot ID assertions remain intact.

Python and test command:

```text
python3 --version
Python 3.14.0
uv run --locked --extra dev python --version
Python 3.13.12
uv run --locked --extra dev pytest tests/unit/lake/test_ingest_performance.py tests/unit/lake/test_transactions.py -m 'not e2e and not perf' -q
26 passed in 1.61s
```

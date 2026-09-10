# Task 4 implementation report

## Implemented

- Added `_ProducerStoppedError` and `_next_fetched`, which races the queue waiter against the producer and always cancels/awaits the queue waiter during cleanup.
- Changed the consumer to use `_next_fetched`, so a producer that exits without the sentinel cannot deadlock ingestion.
- Made `produce_all` explicitly create, own, cancel, and await every child producer after abnormal termination. This covers the case where `asyncio.gather` has already completed exceptionally while siblings remain alive.
- Preserved known rollback outcomes as determined failures while retaining unresolved outcomes for unknown transaction state.
- Added deterministic coverage for a dead producer, abnormal producer/sibling cleanup, and cancellation with a full queue after a prior commit.

## TDD evidence

### RED

Command:

```text
uv run --locked --extra dev pytest tests/unit/sources/datasus_ftp/test_runner_failures.py::test_dead_producer_does_not_leave_queue_waiter tests/unit/sources/datasus_ftp/test_runner_failures.py::test_abnormal_producer_cancels_and_awaits_sibling -q
```

Relevant output:

```text
FF                                                                       [100%]
test_dead_producer_does_not_leave_queue_waiter: AttributeError: module ... has no attribute '_ProducerStoppedError'
test_abnormal_producer_cancels_and_awaits_sibling: TimeoutError
2 failed in 2.90s
```

These failures were expected: the queue/producer race helper did not exist, and the consumer remained blocked on `queue.get()` after the producer failed while its sibling stayed alive.

### GREEN

Command:

```text
uv run --locked --extra dev pytest tests/unit/sources/datasus_ftp/test_runner_failures.py::test_dead_producer_does_not_leave_queue_waiter tests/unit/sources/datasus_ftp/test_runner_failures.py::test_abnormal_producer_cancels_and_awaits_sibling -q
```

Output:

```text
..                                                                       [100%]
2 passed in 0.51s
```

Cancellation acceptance command:

```text
uv run --locked --extra dev pytest tests/unit/sources/datasus_ftp/test_runner_failures.py::test_dead_producer_does_not_leave_queue_waiter tests/unit/sources/datasus_ftp/test_runner_failures.py::test_abnormal_producer_cancels_and_awaits_sibling tests/unit/sources/datasus_ftp/test_runner_failures.py::test_cancel_with_full_queue_preserves_previous_commit -q
```

Output:

```text
...                                                                      [100%]
3 passed in 0.81s
```

## Verification

```text
$ uv run --locked --extra dev pytest tests/unit/sources/datasus_ftp/test_runner_failures.py tests/unit/sources/datasus_ftp/test_runner_concurrency.py -q
..............                                                           [100%]
14 passed in 6.62s

$ uv run --locked --extra dev ruff check src/omnisus_db/sources/datasus_ftp/_runner.py tests/unit/sources/datasus_ftp/test_runner_failures.py
All checks passed!

$ uv run --locked --extra dev mypy src
Success: no issues found in 36 source files

$ uv run --locked --extra dev pytest -m 'not e2e and not perf' -q
409 passed, 47 deselected in 27.15s

$ git diff --check
(no output; exit 0)
```

The first combined Ruff run found `SIM117` and `ASYNC110` in the new tests. I combined the context managers and documented the intentional zero-duration event-loop yield; the clean Ruff result above is after those corrections.

## Files changed

- `src/omnisus_db/sources/datasus_ftp/_runner.py`
- `tests/unit/sources/datasus_ftp/test_runner_failures.py`
- `.superpowers/sdd/2026-09-09-transactional-ingestion/task-4-report.md`

## Self-review

- Confirmed normal completion still queues the sentinel only after all child producers finish.
- Confirmed every abnormal `produce_all` exit cancels and awaits all child tasks, including the completed failing child.
- Confirmed cancellation identity remains `CancelledError`, the lake stays usable, and the previously committed scope remains stored.
- Confirmed known rollback marks written batch outcomes failed, while `TransactionStateError` continues to leave actively written positions unresolved.
- No unrelated architecture or dependencies were changed.

## Concerns

None.

## Round 1 review fix

Added a deterministic regression in which the second producer queue insertion fails only after the first scope has been written inside an incomplete batch. The test confirms that the known rollback reports the written scope as a determined failure, leaves only the remaining input unresolved, rolls back the newly created table and its rows, preserves lake usability, and leaves no tasks alive. Existing unknown-COMMIT tests remain the contrasting unresolved-state coverage. No production change was needed.

Initial covering run exposed an incorrect test assumption rather than a product defect:

```text
$ uv run --locked --extra dev pytest -m 'not e2e and not perf' tests/unit/sources/datasus_ftp/test_runner_failures.py tests/unit/sources/datasus_ftp/test_runner_concurrency.py -q
..F............                                                          [100%]
FAILED test_producer_failure_marks_rolled_back_write_as_determined
CatalogException: Table with name sim_do does not exist!
1 failed, 14 passed in 6.70s
```

The fresh-catalog rollback removes the table itself, so the storage assertion was corrected to verify that `lake.sim_do` is absent from `information_schema.tables`.

Final covering commands and output:

```text
$ uv run --locked --extra dev pytest -m 'not e2e and not perf' tests/unit/sources/datasus_ftp/test_runner_failures.py tests/unit/sources/datasus_ftp/test_runner_concurrency.py -q
...............                                                          [100%]
15 passed in 6.81s

$ uv run --locked --extra dev ruff check tests/unit/sources/datasus_ftp/test_runner_failures.py
All checks passed!
```

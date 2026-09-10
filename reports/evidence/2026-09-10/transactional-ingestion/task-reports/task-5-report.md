# Task 5 Report: Publicar refresh CNES de forma atômica

## Status

DONE

## Implemented

- Added `_prepare_master_rows` to validate CNES rows before any mutation and reject conflicting duplicate records.
- Made `_upsert_master` transactional when called directly, while reusing an enclosing transaction when present.
- Normalized and deduplicated requested codes before fetching, so duplicate codes fetch once and progress totals count unique codes.
- Moved CNES table creation, upsert, and `aux_cnes` view refresh into one managed transaction after fetch and validation.
- Preserved the existing HTTP failure omission behavior and public integer return value.

## TDD Evidence

RED command:

```text
uv run --locked --extra dev pytest tests/unit/sources/cnes/test_master.py -k 'preserves_previous_record or conflicting_records or duplicate_codes or view_failure' -q
```

Result before implementation:

```text
FFFF [100%]
4 failed, 10 deselected in 0.76s
```

The failures showed deletion was not rolled back on insert failure, conflicting rows were accepted, duplicate codes fetched twice, and a view failure left the replacement row published.

GREEN command:

```text
uv run --locked --extra dev pytest tests/unit/sources/cnes/test_master.py -k 'preserves_previous_record or conflicting_records or duplicate_codes or view_failure' -q
```

Result:

```text
.... [100%]
4 passed, 10 deselected in 0.76s
```

## Verification

```text
uv run --locked --extra dev pytest tests/unit/sources/cnes/test_master.py tests/unit/lake/test_transactions.py -q
29 passed in 2.46s

uv run --locked --extra dev mypy src
Success: no issues found in 36 source files

uv run --locked --extra dev pytest -m 'not e2e and not perf' -q
414 passed, 47 deselected in 27.03s

uv run --locked --extra dev ruff check src/omnisus_db/sources/cnes/importers/master.py tests/unit/sources/cnes/test_master.py
All checks passed!
```

## Files changed

- `src/omnisus_db/sources/cnes/importers/master.py`
- `tests/unit/sources/cnes/test_master.py`

## Self-review and concerns

The implementation is scoped to the brief. No new dependencies, schema migrations, or changes to temporal auxiliary view semantics were introduced. No unresolved concerns.

# Task 6 implementation report

## Implemented

- Added CLI handling for `ImportAbortedError`, showing confirmed rows, failed
  outcomes, unresolved inputs, and exit status 1 without printing a completed
  import summary.
- Completed imports with failed outcomes now use the red `failed` marker.
- Updated the `import_dataset` docstring, inventory guide, and changelog with
  transaction and interrupted-import behavior.
- Added real CLI regressions for invalid DBC and interrupted progress, plus a
  public API contract test for `ImportAbortedError`.

## TDD evidence

RED:

```text
uv run --locked --extra dev pytest tests/unit/cli/test_main.py -k 'invalid_dbc or abort_prints' -q
1 failed, 1 passed, 22 deselected
```

The interruption test failed because `ImportAbortedError` propagated without
the required partial-progress message; the invalid-DBC control already passed.

GREEN:

```text
uv run --locked --extra dev pytest tests/unit/cli/test_main.py -k 'invalid_dbc or abort_prints' -q
2 passed, 22 deselected in 0.26s
uv run --locked --extra dev pytest tests/unit/test_public_api.py -k import_aborted_error -q
1 passed, 24 deselected in 0.19s
```

## Verification

```text
uv run --locked --extra dev pytest tests/unit/cli tests/unit/test_public_api.py -q
58 passed in 7.88s
uv run --locked --extra docs mkdocs build --strict
Documentation built in 0.79 seconds (strict build passed; upstream Material warning emitted)
uv run --locked python scripts/gen_datasets_doc.py --check
All checks passed!
uv run --locked --extra dev ruff check src/omnisus_db/cli/main.py src/omnisus_db/__init__.py tests/unit/cli/test_main.py tests/unit/test_public_api.py
All checks passed!
uv run --locked --extra dev pytest -m 'not e2e and not perf' -q
417 passed, 47 deselected in 25.67s
git diff --check
passed
```

## Files changed

`src/omnisus_db/cli/main.py`, `src/omnisus_db/__init__.py`,
`tests/unit/cli/test_main.py`, `tests/unit/test_public_api.py`,
`docs/guides/inventory.md`, and `CHANGELOG.md`.

## Self-review and concerns

The exception boundary covers only the two FTP import calls. The CLI console
width is fixed at 120 so the required interruption sentence remains intact in
`CliRunner` output. No runtime dependencies or unrelated refactors were added.

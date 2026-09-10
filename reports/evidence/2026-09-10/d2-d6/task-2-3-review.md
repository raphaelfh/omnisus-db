# Independent review — D3 and D4

Reviewed diff against 468145d in the D2–D6 worktree, scoped to catalog/SQL/connection/maintenance/schema, D3/D4 portions of operations, maintenance CLI, and focused tests. No production edits.

Spec verdict: PASS for D3 and D4 within reviewed scope after scoped re-review.
Quality verdict: PASS after scoped re-review. Both original P2 findings are resolved; no outstanding P1/P2 findings.

## Resolved P2 — Sanitize URI parser exceptions before they escape

Source: `src/omnisus_db/lake/catalog.py:34`.

`urlsplit(body)` can raise a ValueError whose text includes the complete authority, including the password. This happens before the sanitized remote-attachment exception handler. Reproduced using `parse_target('ducklake:postgresql://user:SENTINEL_PASSWORD@host＃/db?storage=s3://bucket/data')`: exception text is `netloc 'user:SENTINEL_PASSWORD@host＃' contains invalid characters under NFKC normalization`. Thus a malformed remote target exposes credentials through normal exception display, violating D3's credential-safe errors contract. Wrap parser failures and raise a fixed safe message with suppressed exception chaining; add a regression asserting no password in the visible exception/traceback.

## Resolved P2 — Register maintenance commands before the module entrypoint runs

Source: `src/omnisus_db/cli/main.py:410` and `:420` (entrypoint at `:392–393`).

The two new command decorators run after `if __name__ == '__main__': app()`. Invoking the existing module entrypoint therefore starts Typer before these commands exist. Reproduced with `PYTHONPATH=src .venv/bin/python -m omnisus_db.cli.main lake expire-snapshots --help`: exit 2, `No such command 'expire-snapshots'`. The same applies to cleanup-files. Imported CliRunner/console-script tests do not expose this registration ordering issue. Move the entrypoint to the end and verify both module commands.

## Verification

- `.venv/bin/python -m pytest -q tests/unit/lake/test_maintenance.py tests/unit/lake/test_schema_safety.py`: 15 passed in 1.19s.
- A separate `PYTHONPATH=src` temporary lake probe used a catalog alias containing a space and double quote, and a table name containing apostrophe/double quote. Ingestion, optimize, expire_snapshots(dry_run=False), and cleanup_files(dry_run=False) succeeded.
- Reviewed all-shared-column validation before ALTER, same-family widening, decimal/family mismatch rejection, transaction integration, latest CNES row/NULL preservation, and persistent latest-tie guard. No further substantiated P1/P2 issue found in D4. D5 and evolving runner integration excluded as requested.

## Scoped fix verification

Re-reviewed only the two requested D3 fixes. `parse_target` now catches `urlsplit` ValueError and raises a fixed safe message with `from None`; the module entrypoint is now after both maintenance decorators. Both fixes address the original reproduction.

- Focused regression selection: 2 passed, 34 deselected in 0.34s.
- Additional formatted traceback probe confirms the sentinel password is absent.
- `PYTHONPATH=src .venv/bin/python -m omnisus_db.cli.main lake cleanup-files --help` exits 0; the regression test independently verifies expire-snapshots exits 0.
- D4 verdict carried forward without a broad re-review.

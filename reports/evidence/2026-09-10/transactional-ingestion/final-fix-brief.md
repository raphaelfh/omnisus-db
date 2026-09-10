# Final combined fix wave — transactional ingestion D1

Worktree: /Users/raphael/PycharmProjects/omnisus-db/.claude/worktrees/transactional-ingestion.
BASE:18dd077. Binding spec: docs/superpowers/specs/2026-09-09-transactional-ingestion-design.md. Read global-constraints.md alongside this brief.

## Consolidated findings (final reviewer)

1. Important — src/omnisus_db/sources/datasus_ftp/_runner.py:250: Nested transaction rejection becomes an infinite runner loop. Calling run_scopes inside an existing Lake.transaction makes transaction entry raise RuntimeError. The handle remains usable, so runner classifies this as ordinary batch failure. Batch is empty; it retries without consuming input or awaiting anything. This spins indefinitely and prevents asynchronous cancellation. A bounded probe using actual Lake.transaction reproduced repeated entry attempts. Reject managed nesting before starting producers, or explicitly abort failures before transaction entry. Add regression proving prompt rejection and preservation of enclosing transaction.

2. Important — src/omnisus_db/lake/operations.py:158: An interruption first raised during rollback loses its identity. When body raises ordinary exception and ROLLBACK raises KeyboardInterrupt/SystemExit/CancelledError, handler examines original exception only and replaces interruption with TransactionStateError. Commit-failure cleanup at173 similarly discards new interruption. Bounded probes reproduced all three conversions. Preserve existing original interruption preferentially; otherwise propagate interruption raised during cleanup, retaining original failure context and invalidating handle. Add tests where first interruption occurs during cleanup; existing tests cover interruptions originating in body.

3. Minor — src/omnisus_db/cli/main.py:20: Global Console(width=120) changes every command to satisfy captured-output assertion. Restore automatic width AND remove no_wrap=True from interruption message together. 80-column rendering probe with no_wrap truncated final warning to inspec. Test visibility using whitespace-normalized output, including narrow console.

4. Environmental advisory, no code action: MkDocs Material banner concerns2.0 while current project is constrained1.x. Strict docs pass. Preserve evidence, no suppression.

## Controller rulings

- Reject run_scopes called inside an existing managed transaction before starting producers, with a clear RuntimeError, keeping enclosing transaction and handle usable. Do not attempt to join/commit the caller's transaction or silently retry entry. This enforces existing managed-nesting rejection and avoids unsupported transaction ownership.
- Preserve the earliest control-flow interruption. If original failure is already a non-Exception BaseException, keep its identity even if cleanup fails. If original failure is an ordinary Exception and cleanup raises a non-Exception BaseException, propagate that cleanup interruption with original failure as its cause/context and invalidate handle. Ordinary cleanup failures retain existing TransactionStateError/CommitOutcomeUnknown behavior. No retry.
- CLI uses runtime width. Normalize whitespace in semantic text assertions and explicitly exercise a narrow Console so critical warning stays visible. Do not solve this by changing global width or truncating output.

## Execution

One implementer owns all findings. Follow TDD and read test-driven-development/writing-good-tests.md. Write focused failing regressions before source edits. Nested runner test must be bounded even on old infinite-loop behavior (do not rely solely on asyncio.wait_for around a coroutine that may never yield; use a guarded transaction-entry seam with finite attempt limit or equivalent safe probe).
Covering files: tests/unit/lake/test_transactions.py; tests/unit/sources/datasus_ftp/test_runner_failures.py and test_runner_concurrency.py; tests/unit/cli/test_main.py. Preserve input multiplicity, confirmed/unresolved semantics, no source APIs live. Use -m 'not e2e and not perf'. Use existing .venv Python3.13; do not switch interpreter. Run covering tests and scoped lint/mypy. Controller owns final full matrix and package gate, so no duplicate full suite.
Self-review and commit only changed source/tests. No subagents or reviewers. Report questions to controller. Full report including RED/GREEN exact command/output and fix-to-test mapping at final-fix-report.md in this directory. Return short status, commits, test summary, concerns, report path. This is the single combined final fix wave; be careful with causality and cancellation.

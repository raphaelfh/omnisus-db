# SDD ledger — plan: docs/superpowers/plans/2026-09-09-transactional-ingestion.md

Branch: codex/transactional-ingestion. Base: fcb9d5b. Worktree: /Users/raphael/PycharmProjects/omnisus-db/.claude/worktrees/transactional-ingestion.
Spec: docs/superpowers/specs/2026-09-09-transactional-ingestion-design.md.

## Preflight

| Tasks | Output against input checked | Finding |
|---|---|---|
| 1 → 2 | operations.py, transaction test file, pending result list and receipt | Compatible; Task 2 begins registering pending results after Task 1 adds finalization. |
| 1 → 3 | TransactionStateError/is_usable consumed by runner | Compatible; ordinary errors permit later batches, fatal errors abort. |
| 1 → 4 | rollback state and producer cancellation | Signals must retain identity even if SQL cleanup fails; apply interruption ruling below. |
| 1 → 5 | transaction/in_transaction and FaultyConnection | Compatible; helper joins existing context, public importer owns publication. |
| 1 → 6 | transaction/snapshot contract documented | Compatible; docs must distinguish operational writer precondition from implemented lock. |
| 2 → 3 | committed ImportResult published by runner | Compatible; outcomes only become ok after context exits. |
| 2 → 4 | finalized batches survive cancellation | Compatible; cancel rolls back current batch only. |
| 2 → 5 | common transaction boundaries | Compatible; CNES writes raw prepared tuples in managed context. |
| 2 → 6 | pending snapshot documentation | Compatible; None remains valid after metadata read failure. |
| 3 → 4 | runner.py/failure tests and ImportAbortedError | Task 3 moves sentinel to normal path; Task 4 detects producer failure. Task 3 must already clean up fatal exits. |
| 3 → 5 | root API common import exports | No edits shared by Task 5; existing signatures preserved. |
| 3 → 6 | root __init__.py and ImportAbortedError | Compatible; Task 6 adds presentation/docstrings atop exported type. |
| 4 → 5 | managed transaction cleanup | Compatible; CNES sync publication does not depend on runner helper. |
| 4 → 6 | interrupted partial report | Compatible; producer failure maps to same CLI failure path. |
| 5 → 6 | atomic refresh and unique-code progress docs | Compatible; HTTP failure integer policy remains unchanged. |
| 1 internal | six created/modified files, cache regression, fault types, lifecycle | BEGIN code catches Exception, but signal during BEGIN or rollback can leave unsafe handle; follow binding signal/invalidation contract rather than literal snippet. |
| 2 internal | owned/joined transaction and tests | Compatible; preserve semantic assertions if atomic direct ingestion reduces historical snapshot count. |
| 3 internal | by-index outcomes, fatal before conversion, sentinel cleanup | Compatible; source cleanup must preserve raised abort/cancellation instead of replacing it. |
| 4 internal | race helper, producer lifetime, queue cancellation tests | gather can leave child producer tasks alive after one child fails; cancellation must await all producers. Normal producer completion assumes sentinel; verify under actual producer contract. |
| 5 internal | prevalidation, same tx for view, duplicate code tests | Compatible; repeated validation is protective but shared helper avoids duplicate validation logic. |
| 6 internal | CLI markers, public API tests, docs | Compatible; test_public_api.py is listed but snippet lacks explicit new export assertion: add meaningful public exception test. |

Ruling: Use the existing ignored .claude/worktrees directory for isolation — repository already maintains worktrees there and this avoids an unrelated main-branch gitignore commit — cost if wrong: relocate this reversible checkout.
Ruling: Preserve cancellation/KeyboardInterrupt/SystemExit identity and invalidate the handle when BEGIN or cleanup is interrupted, including BaseException failures — the spec's lifecycle and interruption guarantees bind over narrower example catch blocks — cost if wrong: stricter invalidation requires reopening a handle.
Ruling: Producer cleanup must explicitly cancel and await outstanding child producers after abnormal gather termination — asyncio.gather alone does not guarantee that sibling tasks terminate — cost if wrong: a small additional lifecycle cleanup block.
Ruling: Add a focused public ImportAbortedError export/payload test in Task 6 — the plan lists the public API test file and acceptance requires the exported contract, although its snippet is absent — cost if wrong: one redundant behavioral test.

## Tasks
- [x] Task 1: transaction boundary, cache and handle state
- [x] Task 2: snapshot finalization and atomic direct ingest
- [x] Task 3: complete outcomes and explicit unknown commits
- [x] Task 4: producer cleanup and cancellation
- [x] Task 5: atomic CNES refresh
- [x] Task 6: CLI/API/documentation
- [x] Final validation and broad review

Baseline: Python 3.13.12; 386 passed, 47 deselected; coverage 91.28%; 41.72s. Log baseline.log.
Task 1: dispatched /root/implement_1; BASE fcb9d5b7b5b085c94cae6dacf688c52577909c7a.
Task 1: implemented e89b46b; review dispatched /root/review_1, package review-fcb9d5b..e89b46b.diff. Report task-1-report.md. Focused 12 passed; task 22 passed; full unfiltered run 445 passed (agent did not apply requested marker selection). Final certification will use the explicit offline marker selection; subsequent agents receive exact command.
Task 1: complete (commits fcb9d5b..e89b46b, review clean). Reviewer /root/review_1 approved spec and quality with no findings. Cross-task Python 3.12 verification assigned to prepared final gate; no implementation gap.
Task 2: BASE e89b46b; ready for dispatch.

Task 2: implemented 14eb09f; reviewer /root/review_2; package review-e89b46b..14eb09f.diff. RED 3 failed; GREEN 3 passed; full selected 401 passed/47 deselected.
Task 2: review /root/review_2 requested a change in named test_ingest_performance.py (no production defect). Python matrix remains final gate.
Ruling: Strengthen the existing direct-ingest snapshot test to assert one new snapshot for CREATE plus INSERT — the reviewer flags a named file missing from the diff, while the plan only conditionally requests expectation updates; this assertion directly validates the binding atomic direct-ingest requirement — cost if wrong: a redundant snapshot-count assertion.
Task 2: fix round 1/5 dispatched to original implementer; FIX_BASE 14eb09f.
Task 2: fix round 1/5 (1 open — reviewer requires CREATE/INSERT changes metadata assertion beyond snapshot delta/ID; commits 14eb09f..2142007). Next fix dispatched to original implementer; FIX_BASE 2142007.

Task 2: fix round 2/5 (1 addressed, 0 open; commits 2142007..75ff145). Reviewer /root/rereview_2b approved.
Task 2: complete (commits e89b46b..75ff145, review clean). Python matrix assigned final gate.
Task 3: BASE75ff145; dispatch /root/implement_3.

Task 3: complete (commits 75ff145..5f2abb1, review clean). Reviewer /root/review_3 approved both verdicts, no findings. Full selected suite 406 passed/47 deselected; Python matrix final gate. Restored .venv explicitly to3.13 after worker additional3.12 check.
Task 4: BASE5f2abb1; dispatch /root/implement_4.
Task 4: implemented cf3ca21; reviewer /root/review_4 (gpt-6-astra) assessing concurrency. Full selected409 passed/47 deselected; task14 passed. Package review-5f2abb1..cf3ca21.diff.
Task 4: review Important — missing deterministic producer failure after a current-batch write, to prove known rollback reports that scope failed and remaining inputs unresolved. No production defect identified. Fix round1/5 dispatched to original implementer; FIX_BASE cf3ca21.

Task 4: fix round1/5 (1 addressed,0 open; commits cf3ca21..949561b), reviewer /root/rereview_4.
Task 4: complete (commits 5f2abb1..949561b, review clean). Covering15 passed.
Task 5: BASE949561b; dispatch /root/implement_5.

Task 5: complete (commits 949561b..faf17e9, review clean). Reviewer /root/review_5; no findings. Focused29 passed; full selected414 passed/47 deselected.
Task 6: BASEfaf17e9; dispatch /root/implement_6.

Task 6: minor (deferred): global Console(width=120) alters formatting of all CLI commands; reviewer recommends environment-sensitive width. Final whole-branch review must triage.
Task 6: minor (deferred): MkDocs Material emits upstream warning banner; capture full text and document applicability at final gate.
Task 6: complete (commits faf17e9..18dd077, review clean with 2 deferred minors). Reviewer /root/review_6 approved spec and quality. 417 passed/47 deselected; final matrix pending.
Final gate: source HEAD18dd077; global validation and broad review starting.

Initial final gate on18dd077: Python3.13.12 and3.12.13 both417 passed/47 deselected, coverage91.88%; lint,format,mypy,docs,generateddocs,15 dictionary validations,build,lock,diff all exit0. Logs preserved pre-review-fix-checks/. Broad review checking nested-runner loop and CLI truncation before final certification.
Final broad review /root/final_review: 2 Important (nested runner busy loop; first interruption during rollback/commit cleanup replaced), 1 actionable Minor (global width/no_wrap truncates CLI warning), Material banner informational. Full findings in final-fix-brief.md.
Ruling: Reject runner execution inside an existing managed transaction before starting producers — nesting is already unsupported and retrying entry without consuming causes a busy loop — cost if wrong: callers must move the runner outside their outer transaction.
Ruling: Preserve the earliest control-flow interruption, including one first raised during cleanup of an ordinary failure, with the original failure chained and handle invalidated — interruption identity applies throughout the managed boundary — cost if wrong: callers see the cleanup interruption instead of a transaction-state exception.
Final combined fix wave: BASE18dd077, dispatch /root/final_fixer. Includes restoring automatic CLI width and whitespace-normalized narrow-console regression. No banner suppression.
Final fix:30ce324; 66 covering tests passed, scoped static checks passed. Scoped reviewer /root/final_rereview approved all3 actionable findings; no new breakage or out-of-scope observations. Final-review-result.md records resolution. Material banner informational only.
Ruling: Distinguish new failing regressions from controls of already implemented behavior when recording TDD — the plan itself expects repeated-scope and invalid-DBC compatibility controls to pass before later tasks, so a blanket claim that every new assertion first failed would be false — cost if wrong: a misclassified control would need an additional historical regression probe.

Final validation on30ce324: Python3.13.12 429 passed/47 deselected in35.90s; Python3.12.13 429 passed/47 deselected in35.45s; both coverage91.97%. All global checks exit0. Wheel-only clean3.12 installation60 compatible packages, isolated site-packages import and real DuckLake transaction smoke passed.
Final gate: complete; all tasks and final review closed, no parked findings.

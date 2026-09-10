# Independent integration review — D2–D6

Review baseline: 468145d, including tracked changes and new untracked production/tests. Reviewed design/plan, D2 and staging reports, and D2/D3/D4 scoped reviews. No production edits. Review performed 2026-09-10 against the in-progress integration worktree.

## Final verdict

**Spec: PASS for the reviewed integration scope. Quality: PASS.** All three initial P2 findings, including the follow-on FTP welcome-response cancellation issue, are resolved and independently verified. No remaining actionable P1/P2 finding identified. The final correction evidence is recorded below; initial findings are retained as review history. Global documentation/build/type checks remain the controller’s separate responsibility.

## Initial verdict (superseded)

**Spec/quality: changes required**, with three reproduced P2 findings below. No P1 finding identified. The controller was notified immediately and is addressing them; this verdict describes the reviewed snapshot and will require verification after fixes.

### P2 — Cancelled fetch leaves the worker and resident payload running

`src/omnisus_db/sources/datasus_ftp/fetch.py:108–110`, interacting with `_runner.py:384–390`.

`asyncio.to_thread` cancellation cancels the awaiter without stopping the blocking FTP worker. The producer then finishes its cancellation handler and releases its reservation although the thread still owns the socket and download buffer. In a persistent event loop, cancellation returns while those resources remain alive; the synchronous wrapper's executor shutdown can instead wait for the outstanding worker. Hold the reservation until the actual worker terminates, signal cancellation to the blocking operation and close/interrupt active sockets where feasible, while honestly accounting for connection/DNS limitations.

Bounded proof: `/tmp/probe_d6_review.py` uses a controlled FTP implementation, 1 KiB buffered payload and a threading.Event with a three-second failsafe. Cancelling and awaiting the task prints `{'fetch_task_done': True, 'FTP_closed_after_cancel': False, 'worker_released': False}`. The probe releases the worker before exiting.

### P2 — Failed download buffers remain alive through exception tracebacks

`src/omnisus_db/sources/datasus_ftp/fetch.py:66–78,116`.

The BytesIO has no explicit close on failure. Retry exceptions retain `_blocking_fetch` frames and their live buffers through `last_exc`, so a new attempt allocates its payload while the previous payload remains resident under the same single reservation. Queued error objects similarly retain failed buffers after their reservation is released. Close the buffer on every exit, including failure, rather than relying on eventual traceback collection.

Bounded proof: `/tmp/probe_d6_budget_review.py` tracks actual BytesIO instances with weak references. A controlled FTP writes 1024 bytes then raises ConnectionResetError, with `max_bytes=1024`, three retries and zero backoff. Observed resident buffer bytes: 1024, 2048, 2048; 1024 bytes remain retained with final FtpUnavailable. This doubles a one-payload budget without large allocations or network access.

### P2 — Replay skipped against an uncommitted publication survives batch rollback

`src/omnisus_db/sources/datasus_ftp/_runner.py:335–340,351–360,372–380`.

With `skip_same`, a duplicate input can see a publication inserted earlier in the same transaction. Its `None` result becomes a skipped outcome and is removed from `writing`. If a later input fails, the original publication rolls back but the duplicate remains reported as already published. The same dependency is incorrectly considered determined on unknown commit. Track skips dependent on the current transaction so known rollback marks them failed and unknown commit leaves them unresolved. Durable replays against preexisting publications can remain determined.

Bounded proof: `/tmp/probe_d5_skip_review.py` uses the real SIM fixture and a temporary DuckLake, scopes `[RR/2023, RR/2023, RR/2024]`, concurrency 1, batch size 3, `skip_same`; the last payload is malformed. Outcomes are `[failed, skipped('same source and parser version already published'), failed]` while `publications=[]` and the only remaining table is `_omnisus_attempts`.

## Additional evidence and scope

- Focused suite: `PYTHONPATH=src .venv/bin/pytest tests/unit/lake/test_publication.py tests/unit/sources/datasus_ftp/test_resource_limits.py tests/unit/sources/datasus_ftp/test_runner_failures.py tests/unit/sources/datasus_ftp/test_staging.py -q`: **34 passed in 7.63s** on the pre-fix snapshot. These tests did not catch the three probes above.
- Inspected canonical-path lock acquisition before connection and release on construction/close failures, transactional publication/manifests, scope predicates including UF, unmanaged-count protection, schema validation before replacement, pending post-commit receipts, durable recovery lookup, API policy/resource forwarding, and staging's temporary-file/record-generator cleanup.
- No additional substantiated P1/P2 finding in those paths. Arbitrary raw SQL mutations remain outside provenance certification as agreed; count-based managed inventory is not a content-integrity certificate against external mutation.
- D2 latest-estimate/census restriction is controller-approved and not a defect. D2 and scoped D3/D4 reviews were read rather than repeated. Documented full DBF decompression and synthetic benchmark limitations are not findings.
- This review did not perform a new network/source scientific audit, Windows execution, cloud locking verification, or a representative national resource benchmark. Public-facing documentation and typing were concurrently being adjusted by the controller.

## Scoped re-review — first correction pass

- The BytesIO lifetime fix passes the retry-buffer regression; the three attempts retain one payload at a time, and all buffers are closed afterward.
- Pending replay skips now become failed on known rollback while durable preexisting replays remain skipped. Independent lost-confirmation probe `/tmp/probe_d5_unknown_review.py` (run with `PYTHONPATH=src:.`) verifies a real committed publication with both dependent input positions unresolved: `determined 0 unresolved [0, 1]`, `durable_publications 1`.
- The expanded focused suite above passes **38 tests in 8.47s**.
- Cancellation now shields and joins workers and tracks transfer sockets, but the first correction introduces an event-loop blocking gap during the FTP welcome response. `FTP.connect` creates `ftp.sock`/its buffered reader before returning; the socket is only added to tracked sockets afterward. Cancellation calls `ftp.close()` synchronously without first shutting down this newly available socket, and buffered-reader close blocks behind a worker reading the welcome response. `/tmp/probe_d6_greeting_review.py` uses a local socketpair (no network) and the real `ftplib.getresp`: a callback scheduled for 30 ms runs at 303 ms, when a controlled welcome message finally unblocks the reader. The production default timeout is 120 seconds. **P2 remains for cancellation until this socket is interrupted before synchronous close.** Controller notified; revision pending.


## Final scoped verification — all findings resolved

The final cancellation revision shuts down dynamically available `ftp.sock` even before `FTP.connect` returns, then performs FTP close off the event loop. Both closing and the actual worker are awaited under a shield; repeated cancellations cannot release the reservation early. Completed worker/task references are deleted before propagating cancellation, and BytesIO closes on every blocking-worker exit.

Verification:

- `PYTHONPATH=src .venv/bin/pytest tests/unit/lake/test_publication.py tests/unit/sources/datasus_ftp/test_resource_limits.py tests/unit/sources/datasus_ftp/test_runner_failures.py tests/unit/sources/datasus_ftp/test_staging.py tests/unit/sources/datasus_ftp/test_fetch.py -q`: **48 passed in 8.62s**. This includes the real BufferedReader/socketpair greeting regression, payload bounds, failed-retry buffer lifetimes, cancellation cleanup, rollback-dependent versus durable skips, publication/lock/recovery cases, and existing fetch/runner/staging regressions.
- Independent `/tmp/probe_d6_repeated_review.py` applies three cancellations while a controlled blocking worker still holds a 1024-byte buffer. The event loop continues through each timer, the task remains pending while the worker owns bytes, and after explicit release cancellation completes with worker ended, FTP closed, and all tracked BytesIO buffers closed. Output: `three_cancellations_joined_worker=True closed_all_buffers=True loop_ticks_progressed=True`.
- The earlier independent lost-commit probe already verified both the first publication input and its dependent replay are unresolved despite a committed publication being recoverable by run ID.

No further P1/P2 issue identified in these corrections. Platform/OS DNS and not-yet-created sockets may still defer completion; the code waits for the worker rather than claiming arbitrary thread interruption, and the documented limitation is accurate. No national/network resource claim is inferred from the controlled probes.

## Final documentation follow-up — controller record

The independent reviewer checked the new operational guide, architecture, notebook recipes and implementation report. Two material wording corrections were requested and applied: staging Parquet uses Snappy (Zstd belongs to final DuckLake writing), and the amplified benchmark bypasses DBC decompression, so its timings do not describe the complete DBC pipeline. A separate real 3,311-row DBC case exercises decompression. Remaining CNES, IBGE, cloud and replay descriptions were reported consistent with the reviewed code.

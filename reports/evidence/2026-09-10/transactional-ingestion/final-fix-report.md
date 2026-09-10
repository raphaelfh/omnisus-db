# Final combined fix report

Status: complete; three actionable findings addressed in a single wave.
Base: 18dd077. Commit: 30ce324 (fix: preserve transaction interruptions and reject nested runners).
Worktree: /Users/raphael/PycharmProjects/omnisus-db/.claude/worktrees/transactional-ingestion
Branch: codex/transactional-ingestion. Interpreter: existing .venv, Python 3.13.12.
Only six source/test files committed. No dependencies, lockfiles, network-source behavior, or interpreter changes.

## Fix-to-test mapping

1. Nested runner: run_scopes checks lake.in_transaction before any producer setup and raises a clear RuntimeError. test_nested_runner_rejects_without_disturbing_enclosing_transaction uses a real Lake transaction plus a guarded real entry seam (pytest.fail after two attempts) so the original non-yielding loop cannot hang the suite. It verifies rejection, no fetching/task leaks, enclosing transaction active and usable, and successful commit of caller writes before and after rejection.
2. Cleanup interruption: both body-failure rollback and failed-COMMIT cleanup propagate the cleanup BaseException when the original failure is an ordinary Exception. Explicit cause retains the original failure, and invalidation precedes propagation. Existing original control-flow interruptions still take precedence. test_first_interruption_during_cleanup_is_preserved covers both phases × CancelledError/KeyboardInterrupt/SystemExit, identity, cause, unusability, and transaction-state reset. test_commit_interruption_precedes_cleanup_interruption adds earliest-interruption identity checks for COMMIT; existing body-interruption and ordinary cleanup-error tests also ran.
3. CLI: restored Console() runtime width and removed no_wrap=True from interrupted import output. test_import_abort_prints_partial_progress covers default/40/80 widths with whitespace-normalized semantic assertions for interruption, confirmed rows, failed count, unresolved count, full retry warning, exit status, and absence of success wording.
4. MkDocs advisory: no code action; existing controller evidence about Material 2.0 banner versus constrained 1.x remains applicable. No suppression added; docs/package/full-matrix gates remain controller-owned.

## TDD evidence

Skills read: test-driven-development/SKILL.md and writing-good-tests.md; subagent-driven-development/SKILL.md final-fix-wave guidance. Tests written first. No subagents/reviewers launched.

RED command (before source edits):
```sh
.venv/bin/python -m pytest tests/unit/lake/test_transactions.py tests/unit/sources/datasus_ftp/test_runner_failures.py tests/unit/cli/test_main.py -m 'not e2e and not perf' -k 'first_interruption_during_cleanup or commit_interruption_precedes or nested_runner or import_abort_prints' -q
```
Result: 9 failed, 4 passed, 47 deselected in 1.13s. Failures are exactly six cleanup signal conversions, bounded nested-entry guard, and CLI truncation at 40/80 columns. Four precedence/default-width controls already passed.
Full captured output:
```text
FFFFFF...F.FF                                                            [100%]
=================================== FAILURES ===================================
___ test_first_interruption_during_cleanup_is_preserved[CancelledError-body] ___

tmp_path = PosixPath('/private/var/folders/4r/23s40zyn5sj803822cccdlg80000gn/T/pytest-of-raphael/pytest-225/test_first_interruption_during0')
phase = 'body', signal_type = <class 'asyncio.exceptions.CancelledError'>

    @pytest.mark.parametrize("phase", ["body", "commit"])
    @pytest.mark.parametrize("signal_type", [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
    def test_first_interruption_during_cleanup_is_preserved(tmp_path, phase, signal_type):
        with Lake.local(f"ducklake:{tmp_path}/cleanup-first.ducklake") as lake:
            original = ValueError("original failure")
            signal = signal_type("cleanup interrupted")
            faults = {"ROLLBACK": signal}
            if phase == "commit":
                faults["COMMIT"] = original
            lake._con = FaultyConnection(lake.connect(), before=faults)
            with pytest.raises(signal_type) as caught, lake.transaction():
                if phase == "body":
>                   raise original
E                   ValueError: original failure
E                   rollback also failed: cleanup interrupted

tests/unit/lake/test_transactions.py:170: ValueError

The above exception was the direct cause of the following exception:

tmp_path = PosixPath('/private/var/folders/4r/23s40zyn5sj803822cccdlg80000gn/T/pytest-of-raphael/pytest-225/test_first_interruption_during0')
phase = 'body', signal_type = <class 'asyncio.exceptions.CancelledError'>

    @pytest.mark.parametrize("phase", ["body", "commit"])
    @pytest.mark.parametrize("signal_type", [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
    def test_first_interruption_during_cleanup_is_preserved(tmp_path, phase, signal_type):
        with Lake.local(f"ducklake:{tmp_path}/cleanup-first.ducklake") as lake:
            original = ValueError("original failure")
            signal = signal_type("cleanup interrupted")
            faults = {"ROLLBACK": signal}
            if phase == "commit":
                faults["COMMIT"] = original
            lake._con = FaultyConnection(lake.connect(), before=faults)
>           with pytest.raises(signal_type) as caught, lake.transaction():
                                                       ^^^^^^^^^^^^^^^^^^

tests/unit/lake/test_transactions.py:168:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
/Users/raphael/Library/Application Support/uv/python/cpython-3.13.12-macos-aarch64-none/lib/python3.13/contextlib.py:162: in __exit__
    self.gen.throw(value)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <omnisus_db.lake.operations.Lake object at 0x10b4a41a0>

    @contextlib.contextmanager
    def transaction(self) -> Iterator[TransactionReceipt]:
        self.connect()  # Reject closed or invalidated handles.
        if self._in_transaction:
            raise RuntimeError("nested Lake.transaction is not supported")
        self._columns.clear()
        self._ensured.clear()
        try:
            before = self._read_snapshot()
            self._con.execute("BEGIN TRANSACTION")
        except BaseException as exc:
            self._unusable = True
            if not isinstance(exc, Exception):
                raise
            raise TransactionStateError("could not begin managed transaction") from exc

        receipt = TransactionReceipt()
        self._in_transaction = True
        self._pending_results = []
        try:
            try:
                yield receipt
            except BaseException as original:
                try:
                    self._con.execute("ROLLBACK")
                except BaseException as rollback_error:
                    self._unusable = True
                    original.add_note(f"rollback also failed: {rollback_error}")
                    if isinstance(original, Exception):
>                       raise TransactionStateError(
                            "rollback failed; handle unusable"
                        ) from original
E                       omnisus_db.lake._transactions.TransactionStateError: rollback failed; handle unusable

src/omnisus_db/lake/operations.py:162: TransactionStateError
__ test_first_interruption_during_cleanup_is_preserved[CancelledError-commit] __

self = <omnisus_db.lake.operations.Lake object at 0x10b4f8cd0>

    @contextlib.contextmanager
    def transaction(self) -> Iterator[TransactionReceipt]:
        self.connect()  # Reject closed or invalidated handles.
        if self._in_transaction:
            raise RuntimeError("nested Lake.transaction is not supported")
        self._columns.clear()
        self._ensured.clear()
        try:
            before = self._read_snapshot()
            self._con.execute("BEGIN TRANSACTION")
        except BaseException as exc:
            self._unusable = True
            if not isinstance(exc, Exception):
                raise
            raise TransactionStateError("could not begin managed transaction") from exc

        receipt = TransactionReceipt()
        self._in_transaction = True
        self._pending_results = []
        try:
            try:
                yield receipt
            except BaseException as original:
                try:
                    self._con.execute("ROLLBACK")
                except BaseException as rollback_error:
                    self._unusable = True
                    original.add_note(f"rollback also failed: {rollback_error}")
                    if isinstance(original, Exception):
                        raise TransactionStateError(
                            "rollback failed; handle unusable"
                        ) from original
                raise
            else:
                try:
>                   self._con.execute("COMMIT")

src/omnisus_db/lake/operations.py:168:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests/helpers/connection_faults.py:14: in execute
    self._fail(self.before, sql)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <tests.helpers.connection_faults.FaultyConnection object at 0x10b4f8e10>
rules = {}, sql = 'COMMIT'

    def _fail(self, rules, sql):
        normalized = sql.strip().upper()
        for prefix in tuple(rules):
            if normalized.startswith(prefix):
>               raise rules.pop(prefix)
E               ValueError: original failure
E               rollback cleanup also failed: cleanup interrupted

tests/helpers/connection_faults.py:11: ValueError

The above exception was the direct cause of the following exception:

tmp_path = PosixPath('/private/var/folders/4r/23s40zyn5sj803822cccdlg80000gn/T/pytest-of-raphael/pytest-225/test_first_interruption_during1')
phase = 'commit', signal_type = <class 'asyncio.exceptions.CancelledError'>

    @pytest.mark.parametrize("phase", ["body", "commit"])
    @pytest.mark.parametrize("signal_type", [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
    def test_first_interruption_during_cleanup_is_preserved(tmp_path, phase, signal_type):
        with Lake.local(f"ducklake:{tmp_path}/cleanup-first.ducklake") as lake:
            original = ValueError("original failure")
            signal = signal_type("cleanup interrupted")
            faults = {"ROLLBACK": signal}
            if phase == "commit":
                faults["COMMIT"] = original
            lake._con = FaultyConnection(lake.connect(), before=faults)
>           with pytest.raises(signal_type) as caught, lake.transaction():
                                                       ^^^^^^^^^^^^^^^^^^

tests/unit/lake/test_transactions.py:168:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
/Users/raphael/Library/Application Support/uv/python/cpython-3.13.12-macos-aarch64-none/lib/python3.13/contextlib.py:148: in __exit__
    next(self.gen)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <omnisus_db.lake.operations.Lake object at 0x10b4f8cd0>

    @contextlib.contextmanager
    def transaction(self) -> Iterator[TransactionReceipt]:
        self.connect()  # Reject closed or invalidated handles.
        if self._in_transaction:
            raise RuntimeError("nested Lake.transaction is not supported")
        self._columns.clear()
        self._ensured.clear()
        try:
            before = self._read_snapshot()
            self._con.execute("BEGIN TRANSACTION")
        except BaseException as exc:
            self._unusable = True
            if not isinstance(exc, Exception):
                raise
            raise TransactionStateError("could not begin managed transaction") from exc

        receipt = TransactionReceipt()
        self._in_transaction = True
        self._pending_results = []
        try:
            try:
                yield receipt
            except BaseException as original:
                try:
                    self._con.execute("ROLLBACK")
                except BaseException as rollback_error:
                    self._unusable = True
                    original.add_note(f"rollback also failed: {rollback_error}")
                    if isinstance(original, Exception):
                        raise TransactionStateError(
                            "rollback failed; handle unusable"
                        ) from original
                raise
            else:
                try:
                    self._con.execute("COMMIT")
                except BaseException as original:
                    self._unusable = True
                    try:
                        self._con.execute("ROLLBACK")
                    except BaseException as rollback_error:
                        original.add_note(f"rollback cleanup also failed: {rollback_error}")
                    if not isinstance(original, Exception):
                        raise
>                   raise CommitOutcomeUnknown(
                        "commit outcome unknown; inspect before retry"
                    ) from original
E                   omnisus_db.lake._transactions.CommitOutcomeUnknown: commit outcome unknown; inspect before retry

src/omnisus_db/lake/operations.py:177: CommitOutcomeUnknown
_ test_first_interruption_during_cleanup_is_preserved[KeyboardInterrupt-body] __

tmp_path = PosixPath('/private/var/folders/4r/23s40zyn5sj803822cccdlg80000gn/T/pytest-of-raphael/pytest-225/test_first_interruption_during2')
phase = 'body', signal_type = <class 'KeyboardInterrupt'>

    @pytest.mark.parametrize("phase", ["body", "commit"])
    @pytest.mark.parametrize("signal_type", [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
    def test_first_interruption_during_cleanup_is_preserved(tmp_path, phase, signal_type):
        with Lake.local(f"ducklake:{tmp_path}/cleanup-first.ducklake") as lake:
            original = ValueError("original failure")
            signal = signal_type("cleanup interrupted")
            faults = {"ROLLBACK": signal}
            if phase == "commit":
                faults["COMMIT"] = original
            lake._con = FaultyConnection(lake.connect(), before=faults)
            with pytest.raises(signal_type) as caught, lake.transaction():
                if phase == "body":
>                   raise original
E                   ValueError: original failure
E                   rollback also failed: cleanup interrupted

tests/unit/lake/test_transactions.py:170: ValueError

The above exception was the direct cause of the following exception:

tmp_path = PosixPath('/private/var/folders/4r/23s40zyn5sj803822cccdlg80000gn/T/pytest-of-raphael/pytest-225/test_first_interruption_during2')
phase = 'body', signal_type = <class 'KeyboardInterrupt'>

    @pytest.mark.parametrize("phase", ["body", "commit"])
    @pytest.mark.parametrize("signal_type", [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
    def test_first_interruption_during_cleanup_is_preserved(tmp_path, phase, signal_type):
        with Lake.local(f"ducklake:{tmp_path}/cleanup-first.ducklake") as lake:
            original = ValueError("original failure")
            signal = signal_type("cleanup interrupted")
            faults = {"ROLLBACK": signal}
            if phase == "commit":
                faults["COMMIT"] = original
            lake._con = FaultyConnection(lake.connect(), before=faults)
>           with pytest.raises(signal_type) as caught, lake.transaction():
                                                       ^^^^^^^^^^^^^^^^^^

tests/unit/lake/test_transactions.py:168:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
/Users/raphael/Library/Application Support/uv/python/cpython-3.13.12-macos-aarch64-none/lib/python3.13/contextlib.py:162: in __exit__
    self.gen.throw(value)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <omnisus_db.lake.operations.Lake object at 0x10b4f9310>

    @contextlib.contextmanager
    def transaction(self) -> Iterator[TransactionReceipt]:
        self.connect()  # Reject closed or invalidated handles.
        if self._in_transaction:
            raise RuntimeError("nested Lake.transaction is not supported")
        self._columns.clear()
        self._ensured.clear()
        try:
            before = self._read_snapshot()
            self._con.execute("BEGIN TRANSACTION")
        except BaseException as exc:
            self._unusable = True
            if not isinstance(exc, Exception):
                raise
            raise TransactionStateError("could not begin managed transaction") from exc

        receipt = TransactionReceipt()
        self._in_transaction = True
        self._pending_results = []
        try:
            try:
                yield receipt
            except BaseException as original:
                try:
                    self._con.execute("ROLLBACK")
                except BaseException as rollback_error:
                    self._unusable = True
                    original.add_note(f"rollback also failed: {rollback_error}")
                    if isinstance(original, Exception):
>                       raise TransactionStateError(
                            "rollback failed; handle unusable"
                        ) from original
E                       omnisus_db.lake._transactions.TransactionStateError: rollback failed; handle unusable

src/omnisus_db/lake/operations.py:162: TransactionStateError
_ test_first_interruption_during_cleanup_is_preserved[KeyboardInterrupt-commit] _

self = <omnisus_db.lake.operations.Lake object at 0x10bf24e90>

    @contextlib.contextmanager
    def transaction(self) -> Iterator[TransactionReceipt]:
        self.connect()  # Reject closed or invalidated handles.
        if self._in_transaction:
            raise RuntimeError("nested Lake.transaction is not supported")
        self._columns.clear()
        self._ensured.clear()
        try:
            before = self._read_snapshot()
            self._con.execute("BEGIN TRANSACTION")
        except BaseException as exc:
            self._unusable = True
            if not isinstance(exc, Exception):
                raise
            raise TransactionStateError("could not begin managed transaction") from exc

        receipt = TransactionReceipt()
        self._in_transaction = True
        self._pending_results = []
        try:
            try:
                yield receipt
            except BaseException as original:
                try:
                    self._con.execute("ROLLBACK")
                except BaseException as rollback_error:
                    self._unusable = True
                    original.add_note(f"rollback also failed: {rollback_error}")
                    if isinstance(original, Exception):
                        raise TransactionStateError(
                            "rollback failed; handle unusable"
                        ) from original
                raise
            else:
                try:
>                   self._con.execute("COMMIT")

src/omnisus_db/lake/operations.py:168:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests/helpers/connection_faults.py:14: in execute
    self._fail(self.before, sql)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <tests.helpers.connection_faults.FaultyConnection object at 0x10bf24fc0>
rules = {}, sql = 'COMMIT'

    def _fail(self, rules, sql):
        normalized = sql.strip().upper()
        for prefix in tuple(rules):
            if normalized.startswith(prefix):
>               raise rules.pop(prefix)
E               ValueError: original failure
E               rollback cleanup also failed: cleanup interrupted

tests/helpers/connection_faults.py:11: ValueError

The above exception was the direct cause of the following exception:

tmp_path = PosixPath('/private/var/folders/4r/23s40zyn5sj803822cccdlg80000gn/T/pytest-of-raphael/pytest-225/test_first_interruption_during3')
phase = 'commit', signal_type = <class 'KeyboardInterrupt'>

    @pytest.mark.parametrize("phase", ["body", "commit"])
    @pytest.mark.parametrize("signal_type", [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
    def test_first_interruption_during_cleanup_is_preserved(tmp_path, phase, signal_type):
        with Lake.local(f"ducklake:{tmp_path}/cleanup-first.ducklake") as lake:
            original = ValueError("original failure")
            signal = signal_type("cleanup interrupted")
            faults = {"ROLLBACK": signal}
            if phase == "commit":
                faults["COMMIT"] = original
            lake._con = FaultyConnection(lake.connect(), before=faults)
>           with pytest.raises(signal_type) as caught, lake.transaction():
                                                       ^^^^^^^^^^^^^^^^^^

tests/unit/lake/test_transactions.py:168:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
/Users/raphael/Library/Application Support/uv/python/cpython-3.13.12-macos-aarch64-none/lib/python3.13/contextlib.py:148: in __exit__
    next(self.gen)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <omnisus_db.lake.operations.Lake object at 0x10bf24e90>

    @contextlib.contextmanager
    def transaction(self) -> Iterator[TransactionReceipt]:
        self.connect()  # Reject closed or invalidated handles.
        if self._in_transaction:
            raise RuntimeError("nested Lake.transaction is not supported")
        self._columns.clear()
        self._ensured.clear()
        try:
            before = self._read_snapshot()
            self._con.execute("BEGIN TRANSACTION")
        except BaseException as exc:
            self._unusable = True
            if not isinstance(exc, Exception):
                raise
            raise TransactionStateError("could not begin managed transaction") from exc

        receipt = TransactionReceipt()
        self._in_transaction = True
        self._pending_results = []
        try:
            try:
                yield receipt
            except BaseException as original:
                try:
                    self._con.execute("ROLLBACK")
                except BaseException as rollback_error:
                    self._unusable = True
                    original.add_note(f"rollback also failed: {rollback_error}")
                    if isinstance(original, Exception):
                        raise TransactionStateError(
                            "rollback failed; handle unusable"
                        ) from original
                raise
            else:
                try:
                    self._con.execute("COMMIT")
                except BaseException as original:
                    self._unusable = True
                    try:
                        self._con.execute("ROLLBACK")
                    except BaseException as rollback_error:
                        original.add_note(f"rollback cleanup also failed: {rollback_error}")
                    if not isinstance(original, Exception):
                        raise
>                   raise CommitOutcomeUnknown(
                        "commit outcome unknown; inspect before retry"
                    ) from original
E                   omnisus_db.lake._transactions.CommitOutcomeUnknown: commit outcome unknown; inspect before retry

src/omnisus_db/lake/operations.py:177: CommitOutcomeUnknown
_____ test_first_interruption_during_cleanup_is_preserved[SystemExit-body] _____

tmp_path = PosixPath('/private/var/folders/4r/23s40zyn5sj803822cccdlg80000gn/T/pytest-of-raphael/pytest-225/test_first_interruption_during4')
phase = 'body', signal_type = <class 'SystemExit'>

    @pytest.mark.parametrize("phase", ["body", "commit"])
    @pytest.mark.parametrize("signal_type", [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
    def test_first_interruption_during_cleanup_is_preserved(tmp_path, phase, signal_type):
        with Lake.local(f"ducklake:{tmp_path}/cleanup-first.ducklake") as lake:
            original = ValueError("original failure")
            signal = signal_type("cleanup interrupted")
            faults = {"ROLLBACK": signal}
            if phase == "commit":
                faults["COMMIT"] = original
            lake._con = FaultyConnection(lake.connect(), before=faults)
            with pytest.raises(signal_type) as caught, lake.transaction():
                if phase == "body":
>                   raise original
E                   ValueError: original failure
E                   rollback also failed: cleanup interrupted

tests/unit/lake/test_transactions.py:170: ValueError

The above exception was the direct cause of the following exception:

tmp_path = PosixPath('/private/var/folders/4r/23s40zyn5sj803822cccdlg80000gn/T/pytest-of-raphael/pytest-225/test_first_interruption_during4')
phase = 'body', signal_type = <class 'SystemExit'>

    @pytest.mark.parametrize("phase", ["body", "commit"])
    @pytest.mark.parametrize("signal_type", [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
    def test_first_interruption_during_cleanup_is_preserved(tmp_path, phase, signal_type):
        with Lake.local(f"ducklake:{tmp_path}/cleanup-first.ducklake") as lake:
            original = ValueError("original failure")
            signal = signal_type("cleanup interrupted")
            faults = {"ROLLBACK": signal}
            if phase == "commit":
                faults["COMMIT"] = original
            lake._con = FaultyConnection(lake.connect(), before=faults)
>           with pytest.raises(signal_type) as caught, lake.transaction():
                                                       ^^^^^^^^^^^^^^^^^^

tests/unit/lake/test_transactions.py:168:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
/Users/raphael/Library/Application Support/uv/python/cpython-3.13.12-macos-aarch64-none/lib/python3.13/contextlib.py:162: in __exit__
    self.gen.throw(value)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <omnisus_db.lake.operations.Lake object at 0x10bf255b0>

    @contextlib.contextmanager
    def transaction(self) -> Iterator[TransactionReceipt]:
        self.connect()  # Reject closed or invalidated handles.
        if self._in_transaction:
            raise RuntimeError("nested Lake.transaction is not supported")
        self._columns.clear()
        self._ensured.clear()
        try:
            before = self._read_snapshot()
            self._con.execute("BEGIN TRANSACTION")
        except BaseException as exc:
            self._unusable = True
            if not isinstance(exc, Exception):
                raise
            raise TransactionStateError("could not begin managed transaction") from exc

        receipt = TransactionReceipt()
        self._in_transaction = True
        self._pending_results = []
        try:
            try:
                yield receipt
            except BaseException as original:
                try:
                    self._con.execute("ROLLBACK")
                except BaseException as rollback_error:
                    self._unusable = True
                    original.add_note(f"rollback also failed: {rollback_error}")
                    if isinstance(original, Exception):
>                       raise TransactionStateError(
                            "rollback failed; handle unusable"
                        ) from original
E                       omnisus_db.lake._transactions.TransactionStateError: rollback failed; handle unusable

src/omnisus_db/lake/operations.py:162: TransactionStateError
____ test_first_interruption_during_cleanup_is_preserved[SystemExit-commit] ____

self = <omnisus_db.lake.operations.Lake object at 0x10b449a30>

    @contextlib.contextmanager
    def transaction(self) -> Iterator[TransactionReceipt]:
        self.connect()  # Reject closed or invalidated handles.
        if self._in_transaction:
            raise RuntimeError("nested Lake.transaction is not supported")
        self._columns.clear()
        self._ensured.clear()
        try:
            before = self._read_snapshot()
            self._con.execute("BEGIN TRANSACTION")
        except BaseException as exc:
            self._unusable = True
            if not isinstance(exc, Exception):
                raise
            raise TransactionStateError("could not begin managed transaction") from exc

        receipt = TransactionReceipt()
        self._in_transaction = True
        self._pending_results = []
        try:
            try:
                yield receipt
            except BaseException as original:
                try:
                    self._con.execute("ROLLBACK")
                except BaseException as rollback_error:
                    self._unusable = True
                    original.add_note(f"rollback also failed: {rollback_error}")
                    if isinstance(original, Exception):
                        raise TransactionStateError(
                            "rollback failed; handle unusable"
                        ) from original
                raise
            else:
                try:
>                   self._con.execute("COMMIT")

src/omnisus_db/lake/operations.py:168:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
tests/helpers/connection_faults.py:14: in execute
    self._fail(self.before, sql)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <tests.helpers.connection_faults.FaultyConnection object at 0x10b449c70>
rules = {}, sql = 'COMMIT'

    def _fail(self, rules, sql):
        normalized = sql.strip().upper()
        for prefix in tuple(rules):
            if normalized.startswith(prefix):
>               raise rules.pop(prefix)
E               ValueError: original failure
E               rollback cleanup also failed: cleanup interrupted

tests/helpers/connection_faults.py:11: ValueError

The above exception was the direct cause of the following exception:

tmp_path = PosixPath('/private/var/folders/4r/23s40zyn5sj803822cccdlg80000gn/T/pytest-of-raphael/pytest-225/test_first_interruption_during5')
phase = 'commit', signal_type = <class 'SystemExit'>

    @pytest.mark.parametrize("phase", ["body", "commit"])
    @pytest.mark.parametrize("signal_type", [asyncio.CancelledError, KeyboardInterrupt, SystemExit])
    def test_first_interruption_during_cleanup_is_preserved(tmp_path, phase, signal_type):
        with Lake.local(f"ducklake:{tmp_path}/cleanup-first.ducklake") as lake:
            original = ValueError("original failure")
            signal = signal_type("cleanup interrupted")
            faults = {"ROLLBACK": signal}
            if phase == "commit":
                faults["COMMIT"] = original
            lake._con = FaultyConnection(lake.connect(), before=faults)
>           with pytest.raises(signal_type) as caught, lake.transaction():
                                                       ^^^^^^^^^^^^^^^^^^

tests/unit/lake/test_transactions.py:168:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
/Users/raphael/Library/Application Support/uv/python/cpython-3.13.12-macos-aarch64-none/lib/python3.13/contextlib.py:148: in __exit__
    next(self.gen)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <omnisus_db.lake.operations.Lake object at 0x10b449a30>

    @contextlib.contextmanager
    def transaction(self) -> Iterator[TransactionReceipt]:
        self.connect()  # Reject closed or invalidated handles.
        if self._in_transaction:
            raise RuntimeError("nested Lake.transaction is not supported")
        self._columns.clear()
        self._ensured.clear()
        try:
            before = self._read_snapshot()
            self._con.execute("BEGIN TRANSACTION")
        except BaseException as exc:
            self._unusable = True
            if not isinstance(exc, Exception):
                raise
            raise TransactionStateError("could not begin managed transaction") from exc

        receipt = TransactionReceipt()
        self._in_transaction = True
        self._pending_results = []
        try:
            try:
                yield receipt
            except BaseException as original:
                try:
                    self._con.execute("ROLLBACK")
                except BaseException as rollback_error:
                    self._unusable = True
                    original.add_note(f"rollback also failed: {rollback_error}")
                    if isinstance(original, Exception):
                        raise TransactionStateError(
                            "rollback failed; handle unusable"
                        ) from original
                raise
            else:
                try:
                    self._con.execute("COMMIT")
                except BaseException as original:
                    self._unusable = True
                    try:
                        self._con.execute("ROLLBACK")
                    except BaseException as rollback_error:
                        original.add_note(f"rollback cleanup also failed: {rollback_error}")
                    if not isinstance(original, Exception):
                        raise
>                   raise CommitOutcomeUnknown(
                        "commit outcome unknown; inspect before retry"
                    ) from original
E                   omnisus_db.lake._transactions.CommitOutcomeUnknown: commit outcome unknown; inspect before retry

src/omnisus_db/lake/operations.py:177: CommitOutcomeUnknown
_____ test_nested_runner_rejects_without_disturbing_enclosing_transaction ______

tmp_path = PosixPath('/private/var/folders/4r/23s40zyn5sj803822cccdlg80000gn/T/pytest-of-raphael/pytest-225/test_nested_runner_rejects_wit0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x10bf243e0>

    @pytest.mark.asyncio
    async def test_nested_runner_rejects_without_disturbing_enclosing_transaction(
        tmp_path, monkeypatch
    ):
        from contextlib import contextmanager

        from omnisus_db.sources.datasus_ftp import _runner

        fetched = []

        async def fetch(**kwargs):
            fetched.append(kwargs)
            return b"must not fetch"

        monkeypatch.setattr(_runner, "fetch_dbc_bytes", fetch)
        baseline = asyncio.all_tasks()
        with Lake.local(f"ducklake:{tmp_path}/nested.ducklake") as lake:
            real_transaction = lake.transaction
            attempts = 0

            @contextmanager
            def bounded_transaction():
                nonlocal attempts
                attempts += 1
                if attempts > 2:
                    pytest.fail("runner repeatedly attempts nested transaction entry")
                with real_transaction() as receipt:
                    yield receipt

            with lake.transaction() as receipt:
                lake.connect().execute("CREATE TABLE lake.caller(i INTEGER)")
                lake.connect().execute("INSERT INTO lake.caller VALUES (1)")
                monkeypatch.setattr(lake, "transaction", bounded_transaction)
                with pytest.raises(RuntimeError, match="nested|active|existing"):
>                   await run_scopes(
                        "sim_do", scopes=[ScopeKey(uf="RR", ano=2023)], lake=lake
                    )

tests/unit/sources/datasus_ftp/test_runner_failures.py:311:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
src/omnisus_db/sources/datasus_ftp/_runner.py:222: in run_scopes
    with lake.transaction():
         ^^^^^^^^^^^^^^^^^^
/Users/raphael/Library/Application Support/uv/python/cpython-3.13.12-macos-aarch64-none/lib/python3.13/contextlib.py:141: in __enter__
    return next(self.gen)
           ^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    @contextmanager
    def bounded_transaction():
        nonlocal attempts
        attempts += 1
        if attempts > 2:
>           pytest.fail("runner repeatedly attempts nested transaction entry")
E           Failed: runner repeatedly attempts nested transaction entry

tests/unit/sources/datasus_ftp/test_runner_failures.py:302: Failed
----------------------------- Captured stdout call -----------------------------
2026-09-10 10:09:51 [warning  ] run_scopes.batch_failed        dataset=sim_do error='nested Lake.transaction is not supported'
2026-09-10 10:09:51 [warning  ] run_scopes.batch_failed        dataset=sim_do error='nested Lake.transaction is not supported'
________________ test_import_abort_prints_partial_progress[40] _________________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x10b57f130>
tmp_path = PosixPath('/private/var/folders/4r/23s40zyn5sj803822cccdlg80000gn/T/pytest-of-raphael/pytest-225/test_import_abort_prints_parti1')
width = 40

    @pytest.mark.parametrize("width", [None, 40, 80])
    def test_import_abort_prints_partial_progress(monkeypatch, tmp_path: Path, width) -> None:
        from rich.console import Console

        if width is not None:
            monkeypatch.setattr("omnisus_db.cli.main.console", Console(width=width))
        import omnisus_db as odb

        def abort(*args: object, **kwargs: object) -> None:
            report = odb.ImportReport(outcomes=())
            unresolved = ((0, odb.ScopeKey(uf="RR", ano=2023)),)
            raise odb.ImportAbortedError(report, unresolved)

        monkeypatch.setattr(odb, "import_dataset", abort)
        result = runner.invoke(
            app,
            [
                "import",
                "sim_do",
                "--year",
                "2023",
                "--ufs",
                "RR",
                "--target",
                f"ducklake:{tmp_path}/partial.ducklake",
            ],
        )
        assert result.exit_code == 1
        output = " ".join(result.stdout.split())
        assert "import interrupted" in output
        assert "0 confirmed rows" in output
>       assert "0 failed" in output
E       AssertionError: assert '0 failed' in 'import interrupted: 0 confirmed rows, 0'

tests/unit/cli/test_main.py:317: AssertionError
________________ test_import_abort_prints_partial_progress[80] _________________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x10b57e140>
tmp_path = PosixPath('/private/var/folders/4r/23s40zyn5sj803822cccdlg80000gn/T/pytest-of-raphael/pytest-225/test_import_abort_prints_parti2')
width = 80

    @pytest.mark.parametrize("width", [None, 40, 80])
    def test_import_abort_prints_partial_progress(monkeypatch, tmp_path: Path, width) -> None:
        from rich.console import Console

        if width is not None:
            monkeypatch.setattr("omnisus_db.cli.main.console", Console(width=width))
        import omnisus_db as odb

        def abort(*args: object, **kwargs: object) -> None:
            report = odb.ImportReport(outcomes=())
            unresolved = ((0, odb.ScopeKey(uf="RR", ano=2023)),)
            raise odb.ImportAbortedError(report, unresolved)

        monkeypatch.setattr(odb, "import_dataset", abort)
        result = runner.invoke(
            app,
            [
                "import",
                "sim_do",
                "--year",
                "2023",
                "--ufs",
                "RR",
                "--target",
                f"ducklake:{tmp_path}/partial.ducklake",
            ],
        )
        assert result.exit_code == 1
        output = " ".join(result.stdout.split())
        assert "import interrupted" in output
        assert "0 confirmed rows" in output
        assert "0 failed" in output
        assert "1 unresolved" in output
>       assert "inspect before retry" in output
E       AssertionError: assert 'inspect before retry' in 'import interrupted: 0 confirmed rows, 0 failed, 1 unresolved; inspect before ret'

tests/unit/cli/test_main.py:319: AssertionError
=========================== short test summary info ============================
FAILED tests/unit/lake/test_transactions.py::test_first_interruption_during_cleanup_is_preserved[CancelledError-body]
FAILED tests/unit/lake/test_transactions.py::test_first_interruption_during_cleanup_is_preserved[CancelledError-commit]
FAILED tests/unit/lake/test_transactions.py::test_first_interruption_during_cleanup_is_preserved[KeyboardInterrupt-body]
FAILED tests/unit/lake/test_transactions.py::test_first_interruption_during_cleanup_is_preserved[KeyboardInterrupt-commit]
FAILED tests/unit/lake/test_transactions.py::test_first_interruption_during_cleanup_is_preserved[SystemExit-body]
FAILED tests/unit/lake/test_transactions.py::test_first_interruption_during_cleanup_is_preserved[SystemExit-commit]
FAILED tests/unit/sources/datasus_ftp/test_runner_failures.py::test_nested_runner_rejects_without_disturbing_enclosing_transaction
FAILED tests/unit/cli/test_main.py::test_import_abort_prints_partial_progress[40]
FAILED tests/unit/cli/test_main.py::test_import_abort_prints_partial_progress[80]
9 failed, 4 passed, 47 deselected in 1.13s

```

GREEN covering command:
```sh
.venv/bin/python -m pytest tests/unit/lake/test_transactions.py tests/unit/sources/datasus_ftp/test_runner_failures.py tests/unit/sources/datasus_ftp/test_runner_concurrency.py tests/unit/cli/test_main.py -m 'not e2e and not perf' -q
```
Full output:
```text
..................................................................       [100%]
66 passed in 13.08s

```

## Scoped static checks

```sh
.venv/bin/ruff check src/omnisus_db/lake/operations.py src/omnisus_db/sources/datasus_ftp/_runner.py src/omnisus_db/cli/main.py tests/unit/lake/test_transactions.py tests/unit/sources/datasus_ftp/test_runner_failures.py tests/unit/cli/test_main.py
# All checks passed!
.venv/bin/ruff format --check src/omnisus_db/lake/operations.py src/omnisus_db/sources/datasus_ftp/_runner.py src/omnisus_db/cli/main.py tests/unit/lake/test_transactions.py tests/unit/sources/datasus_ftp/test_runner_failures.py tests/unit/cli/test_main.py
# 6 files already formatted
.venv/bin/mypy src/omnisus_db/lake/operations.py src/omnisus_db/sources/datasus_ftp/_runner.py src/omnisus_db/cli/main.py
# Success: no issues found in 3 source files
git diff --check
# no output
```

Initial Ruff identified an intentional regex needing raw-string syntax and one test formatting issue; both corrected after GREEN without semantic changes. Final scoped checks and commit hooks passed. Commit hooks: conflict markers, EOF, trailing whitespace, large files, Ruff check/format and mypy (src) passed; unrelated YAML/TOML/docs/dictionaries checks skipped.

## Self-review and limitations

Reviewed entire six-file diff. Minimal source edits implement controller rulings; no retry path added, original ordinary rollback/commit classification remains intact, transaction finally resets state, and enclosing transaction is never entered/committed by runner on rejection. Mutation check: removing nested validation trips the bounded guard; converting cleanup interruptions to transaction errors fails all six signal cases; preferring later interruption breaks precedence tests; restoring no_wrap truncates narrow CLI output.

Existing covering tests preserve committed/unresolved semantics, cancellation cleanup, concurrency behavior, and repeated input multiplicity. Tests use actual DuckLake in temporary directories and local DBC fixtures; no live FTP/IBGE/CNES calls. No full matrix or package gates duplicated. No unresolved implementation concerns; controller owns final Python 3.13/3.12 matrix, coverage, package/docs gates and scoped re-review.

Git index write required escalation after sandbox rejection; escalation succeeded and commit hooks passed. No source-operation escalation or approval remains pending.

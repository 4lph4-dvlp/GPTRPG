---
phase: 01-rules-core-and-event-log
reviewed: 2026-08-01T09:14:14Z
depth: standard
files_reviewed: 29
files_reviewed_list:
  - .gitignore
  - .importlinter
  - pyproject.toml
  - .python-version
  - README.md
  - src/gptrpg/cli/__init__.py
  - src/gptrpg/cli/main.py
  - src/gptrpg/event_log/__init__.py
  - src/gptrpg/event_log/replay_roller.py
  - src/gptrpg/event_log/schema.py
  - src/gptrpg/event_log/store.py
  - src/gptrpg/__init__.py
  - src/gptrpg/py.typed
  - src/gptrpg/rules_core/dice.py
  - src/gptrpg/rules_core/grading.py
  - src/gptrpg/rules_core/__init__.py
  - src/gptrpg/rules_core/reducer.py
  - src/gptrpg/rules_core/resolution.py
  - src/gptrpg/session_actor/actor.py
  - src/gptrpg/session_actor/__init__.py
  - src/gptrpg/session_actor/live_roller.py
  - src/gptrpg/session_actor/projection.py
  - tests/conftest.py
  - tests/test_boundaries.py
  - tests/test_cli.py
  - tests/test_dice_replay.py
  - tests/test_event_log.py
  - tests/test_grading.py
  - tests/test_resolution_edges.py
  - tests/test_reverse_verification.py
  - tests/test_scaffold.py
  - tests/test_session_actor.py
  - tests/test_tracer.py
  - uv.lock
findings:
  critical: 0
  warning: 5
  info: 2
  total: 7
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-08-01T09:14:14Z
**Depth:** standard
**Files Reviewed:** 29 source/config files (`uv.lock` inspected for supply-chain sanity only — a generated lock file, not walked line-by-line)
**Status:** issues_found

## Summary

Reviewed the rules-core / event-log / session-actor / CLI stack that makes up Phase 01. The architecture is disciplined: `rules_core` is genuinely free of time/random/IO (verified by `.importlinter` + `pyproject.toml` ruff bans + a self-testing `test_boundaries.py` that proves the contract actually catches a violation), the event schema is closed (`extra="forbid"`, `frozen=True`), SQL is fully parameterized, no `eval`/`exec`/shell calls exist, and JSON parsing goes through pydantic's `validate_json` (no pickle). No SQL injection, command injection, hardcoded secrets, or unsafe deserialization were found — no Critical findings.

The issues found are all robustness/quality gaps: missing bounds validation on dice rolls (the one domain invariant this whole project is built to make "검산 가능", verifiable), a resource-leak on `EventStore.initialize()` re-entry, an un-guarded duplication of the `Grade` literal across two layers with no test enforcing the two stay in sync, a non-idempotent `SessionActor.stop()`, and a CLI exception-handling gap that can leak a raw traceback to a shell user for error classes the code didn't anticipate. None of these are hit by the current test suite because the current tests only exercise the "happy" architectural assumptions (single writer, well-behaved `Roller`, single `stop()` call) — they don't adversarially probe the assumptions themselves.

## Warnings

### WR-01: Dice roll values are never bounds-checked (1–6) anywhere in the compute or persistence path

**File:** `src/gptrpg/rules_core/resolution.py:60-98`, `src/gptrpg/event_log/schema.py:86-95`

**Issue:** `resolve_2d6` and `reroll_2d6` call `roller.roll_d6()` and trust the return value unconditionally:
```python
rolls = (roller.roll_d6(), roller.roll_d6())
total = sum(rolls) + _flat_total(modifiers)
```
`Roller` is a structural `Protocol` (`src/gptrpg/rules_core/dice.py:6-15`) — *any* object with a `roll_d6(self) -> int` method satisfies it, so a buggy or malicious implementation can return `0`, negative numbers, or values `>6`. Nothing in `resolve_2d6`/`reroll_2d6` validates the range, and `CheckResolved.rolls: list[int]` (`event_log/schema.py:91`) has no `Field(ge=1, le=6)` constraint either. Because the event log is append-only, an invalid roll that slips through is permanent and un-correctable, directly undermining the project's stated core value proposition ("검산 가능한 순수 판정 코드" — verifiable resolution code). `LiveRoller` itself even carries a comment warning about exactly this class of off-by-one bug (`secrets.randbelow(6) + 1`), showing the risk is known but not defended against.

**Fix:** Validate at the boundary that actually knows the domain invariant (`resolve_2d6`/`reroll_2d6`), and/or constrain the schema field:
```python
# resolution.py
def _validated_roll(roller: Roller) -> int:
    value = roller.roll_d6()
    if not 1 <= value <= 6:
        raise ValueError(f"roll_d6() returned out-of-range value: {value!r}")
    return value

rolls = (_validated_roll(roller), _validated_roll(roller))
```
```python
# event_log/schema.py
rolls: list[Annotated[int, Field(ge=1, le=6)]]
```

---

### WR-02: `EventStore.initialize()` leaks the previous sqlite3 connection if called twice

**File:** `src/gptrpg/event_log/store.py:39-45`

**Issue:**
```python
def initialize(self) -> None:
    self._conn = sqlite3.connect(self._db_path)
    ...
```
If `initialize()` is invoked a second time on the same `EventStore` instance, the previous `sqlite3.Connection` is overwritten and dropped without being closed — the handle (and its WAL/journal file descriptors) leaks for the lifetime of the process. Current call sites only invoke `initialize()` once, so this isn't exercised today, but nothing in the class guards against re-entry, and there's no test asserting idempotency.

**Fix:**
```python
def initialize(self) -> None:
    if self._conn is not None:
        return  # or: raise RuntimeError("EventStore already initialized")
    self._conn = sqlite3.connect(self._db_path)
    ...
```

---

### WR-03: `Grade` literal duplicated across `rules_core` and `event_log` with no test enforcing the two stay in sync

**File:** `src/gptrpg/rules_core/grading.py:5`, `src/gptrpg/event_log/schema.py:22-23`

**Issue:** `event_log/schema.py` intentionally redeclares `Grade = Literal["strong_hit", "weak_hit", "miss"]` instead of importing from `rules_core.grading` (correctly, per the layering contract — `event_log` must not know `rules_core`). The comment acknowledges the tradeoff ("두 층은 서로를 모른다"), but no test anywhere asserts the two literal value sets are actually equal. If a future change adds/renames a grade in `grading.py` (e.g. adds `"critical_hit"`) without updating `schema.py`, `CheckResolved` construction would start raising `ValidationError` for previously-valid grades — a silent, hard-to-diagnose split-brain between the two layers, which is exactly the class of bug the project elsewhere goes out of its way to fail loudly on (see `UnknownEventType`, `ReplayExhausted`).

**Fix:** Add a lightweight sync test (in `tests/`, not in either module, to preserve the boundary):
```python
from typing import get_args
from gptrpg.rules_core.grading import Grade as CoreGrade
from gptrpg.event_log.schema import Grade as SchemaGrade

def test_core_and_schema_grade_literals_stay_in_sync():
    assert set(get_args(CoreGrade)) == set(get_args(SchemaGrade))
```

---

### WR-04: `SessionActor.stop()` is not safe against concurrent invocation

**File:** `src/gptrpg/session_actor/actor.py:130-135`

**Issue:**
```python
async def stop(self) -> None:
    if self._task is not None:
        await self._queue.put(None)
        await self._task
        self._task = None
```
The `if self._task is not None` check and the `self._task = None` assignment are not atomic across the intervening `await` points. If `stop()` is called twice concurrently (e.g. from two different cleanup paths racing during error handling), both calls can observe `self._task is not None`, both `put(None)` a sentinel, and the second sentinel is left orphaned in the queue after the consumer loop has already exited on the first sentinel — harmless today only because nothing currently calls `stop()` from more than one place per actor, but it's an un-guarded invariant.

**Fix:** Guard with an idempotency flag or a lock:
```python
async def stop(self) -> None:
    if self._task is None:
        return
    task, self._task = self._task, None
    await self._queue.put(None)
    await task
```

---

### WR-05: CLI `_cmd_submit` only catches the two known rejection exceptions — any other exception surfaces as a raw traceback

**File:** `src/gptrpg/cli/main.py:91-109`

**Issue:**
```python
try:
    seq = asyncio.run(_run_submit(store, args.session, command))
except (CommandRejected, SequenceConflict) as exc:
    print(f"오류: {exc}", file=sys.stderr)
    return 1
finally:
    store.close()
```
`main.py`'s own docstring states its job is only to turn state into text and never contain game rules — implying error output should always be human-readable. But `SessionActor._run` (`session_actor/actor.py:154-161`) forwards *any* exception raised during `_process` to the caller's future unfiltered (`except Exception as exc: ... future.set_exception(exc)`), and only `UnsupportedModifier` is deliberately translated into `CommandRejected` (`actor.py:242-244`). Any other exception class reaching `_process` — e.g. a non-primary-key `sqlite3.IntegrityError` re-raised by `EventStore.append` (`store.py:88-91`), or an `sqlite3.OperationalError` from a locked/corrupt database file — propagates straight through `_cmd_submit`, is not caught by the `except (CommandRejected, SequenceConflict)` clause, and reaches the top of `main()` unhandled, producing a full Python traceback on stderr for an end user running a CLI tool. This directly contradicts the behavior the existing test (`test_submit_sequence_conflict_becomes_one_line_message_not_traceback`) verifies only for the sequence-conflict case, not the general case.

**Fix:** Widen the catch to a general "expected operational failure" boundary, or explicitly wrap store-layer errors:
```python
except (CommandRejected, SequenceConflict) as exc:
    print(f"오류: {exc}", file=sys.stderr)
    return 1
except sqlite3.Error as exc:
    print(f"오류: 저장소 오류 — {exc}", file=sys.stderr)
    return 1
```

## Info

### IN-01: `py.typed` marker present but no static type checker is configured to back its promise

**File:** `src/gptrpg/py.typed`, `pyproject.toml:21-28`

**Issue:** The package ships a PEP 561 `py.typed` marker, publicly promising downstream consumers that its type hints are checked and reliable. But `[dependency-groups].dev` has no `mypy`/`pyright`/`ty` entry, and there's no `[tool.mypy]` config or CI step visible in the reviewed files that actually enforces type correctness — the marker's promise currently rests entirely on manual discipline.

**Fix:** Either add a type checker to the dev dependency group and a CI/pre-commit check, or defer adding `py.typed` until type-checking is actually enforced.

### IN-02: CLI `roll --target` and AI-call numeric flags accept values that pass argparse but have no CLI-level sanity bound

**File:** `src/gptrpg/cli/main.py:161-166`

**Issue:** `roll_parser.add_argument("--target", type=int, default=DEFAULT_TARGET)` accepts any integer, including negative or absurdly large values, with no upfront validation before it reaches `resolve_2d6`. The actor layer doesn't reject it either (only `latency_ms`/token fields are checked for `>= 0` in `_prepare_ai_call`). Not incorrect per se (grading math is well-defined for any integer target), but a typo'd `--target -10` would silently record a nonsensical check rather than being rejected with a clear message.

**Fix:** Consider adding a minimal sanity bound (e.g. `target >= 2`) in `_prepare_resolve_check`, consistent with the validation style already used for the other five command types.

---

_Reviewed: 2026-08-01T09:14:14Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

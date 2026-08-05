---
phase: 01-rules-core-and-event-log
verified: 2026-08-01T18:30:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification: null
---

# Phase 1: 규칙 코어와 사건 기록 Verification Report

**Phase Goal:** 게임의 진실이 순서대로 쌓인 사건 기록에만 있고, 규칙 계산은 시간을 모르는 순수 코드로만 일어난다
**Verified:** 2026-08-01T18:30:00Z
**Status:** passed
**Re-verification:** No — initial verification (no prior `01-VERIFICATION.md` existed)

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 어떤 시점의 게임 상태든 사건 기록을 처음부터 훑어서 똑같이 다시 만들어낼 수 있다 | ✓ VERIFIED | `session_actor/projection.py::rebuild_state` reads the full log and folds via `rules_core/reducer.py::fold`, which always starts at `initial_state` (no snapshot, D-08). Live-tested during this verification: built a 3-event session via CLI, ran `gptrpg replay` twice — byte-identical output (`diff` clean). Also covered by `tests/test_tracer.py::test_replay_output_is_identical_across_two_runs` and `tests/test_session_actor.py::test_rebuild_state_does_not_write_and_is_repeatable` (both in the 142-test green suite). |
| 2 | 주사위를 굴리고 판정 결과가 나오기까지 AI가 끼어드는 지점이 코드 어디에도 없다 | ✓ VERIFIED | `rules_core/resolution.py::resolve_2d6`/`reroll_2d6` take an injected `Roller` and call only `roller.roll_d6()` — no network/AI call surface exists in `rules_core` at all. Verified mechanically: `grep` of all `rules_core/*.py` imports shows only `typing`, `dataclasses`, `collections.abc`, and sibling `rules_core` modules. `.importlinter`'s `forbidden` contract additionally blocks `socket`/`urllib`/`http`/`asyncio` inside `rules_core`, and `uv run lint-imports` (re-run live) reports `2 kept, 0 broken`. |
| 3 | 같은 주사위 굴림을 다시 재생하면 같은 결과가 나온다 (굴림 원본이 기록에 남는다) | ✓ VERIFIED | `CheckResolved.rolls: list[int]` stores every rolled eye (not just the total); `event_log/replay_roller.py::ReplayRoller` feeds recorded rolls back through the unmodified `resolve_2d6`. `tests/test_dice_replay.py::test_replay_reproduces_three_checks_recorded_from_live_rolls` and the hypothesis property test `test_replaying_same_recorded_rolls_twice_is_always_deterministic` are in the green suite. Exhaustion fails loudly via `ReplayExhausted` rather than fabricating a value (`test_replay_roller_raises_replay_exhausted_when_rolls_run_out`). |
| 4 | 규칙 계산 코드에 타이머·접속 상태·현재 시각 같은 개념이 하나도 등장하지 않는다 | ✓ VERIFIED | `.importlinter`'s `forbidden` contract (`source_modules = gptrpg.rules_core`) bans `time`, `random`, `os`, `socket`, `datetime`, `secrets`, `sqlite3`, `asyncio`, `pathlib`, `urllib`, `http`, with `include_external_packages = True` (so stdlib modules are actually caught, not silently skipped). Confirmed live: `uv run lint-imports` → `rules_core는 시간·무작위·파일·네트워크·비동기를 모른다 KEPT`. The contract is proven armed, not decorative, by `tests/test_boundaries.py::test_contract_actually_catches_a_violation`, which writes a `random`-importing probe module into `rules_core` and asserts the contract *fails* (re-run live: PASSED, i.e. the violation was correctly caught). |
| 5 | 한 세션에 대해 상태를 바꿀 수 있는 주체가 하나뿐이라는 것이 코드 구조로 강제된다 | ✓ VERIFIED | Two-layer enforcement, both inspected directly in `src/gptrpg/session_actor/actor.py`: (a) `SessionActor` holds one `asyncio.Queue` + one consumer task (`_run`); all commands funnel through `submit()` → queue → single `_process` call, so within a process, writes are serialized. (b) `SessionRegistry.get_or_create(session_id)` returns the same live actor for a repeated `session_id`, never a second one. (c) Cross-process/second layer: `EventStore`'s composite `PRIMARY KEY (session_id, seq)` rejects a second writer at the same seq via `SequenceConflict`, and `SessionActor` never catches/retries it — it propagates to the caller (`_run`'s `except Exception` sets it on the future, doesn't swallow it). Backed by `tests/test_session_actor.py::test_sequence_conflict_is_not_swallowed_and_reaches_the_caller` and `::test_registry_returns_same_actor_for_same_session_id_and_different_for_another`, both green. |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | project scaffold, pytest/ruff config, `[project.scripts]` | ✓ VERIFIED | `[tool.pytest.ini_options]`, `[tool.ruff.lint.flake8-tidy-imports.banned-api]`, `[tool.ruff.lint.per-file-ignores]`, `[project.scripts] gptrpg = "gptrpg.cli.main:main"` all present |
| `.importlinter` | forbidden + layers contracts, pipe-separated siblings | ✓ VERIFIED | Exact text `gptrpg.rules_core \| gptrpg.event_log` present; `include_external_packages = True` present; all 11 forbidden modules listed |
| `src/gptrpg/rules_core/{dice,grading,resolution,reducer}.py` | pure 2d6 resolution, no time/random/IO | ✓ VERIFIED | Imports checked directly — only `typing`/`dataclasses`/`collections.abc`/sibling modules |
| `src/gptrpg/event_log/{schema,store,replay_roller}.py` | six-type discriminated union, SQLite append-only store, replay roller | ✓ VERIFIED | `GameEvent = Annotated[Union[6 types], Field(discriminator="event_type")]`; `EventStore` has exactly 5 public methods (`initialize`, `next_seq`, `append`, `read_events`, `close`) — no update/delete |
| `src/gptrpg/session_actor/{actor,projection,live_roller}.py` | single-writer queue actor, read-only projection, cryptographic live roller | ✓ VERIFIED | `LiveRoller.roll_d6` uses `secrets.randbelow(6) + 1`; `rebuild_state` only reads |
| `src/gptrpg/cli/main.py` | `submit {declare,confirm,roll,narrate,clock,ai}` / `replay` | ✓ VERIFIED | Live-invoked during this verification; zero game-rule logic, only arg→Command→actor→text |
| `tests/*.py` (11 files, 2240 lines) | boundary, tracer, event-log, grading, edge, reverse-verification, session-actor, CLI tests | ✓ VERIFIED | `uv run pytest -q` → 142 passed (re-run live) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `tests/test_boundaries.py` | `.importlinter` | `lint_imports(config_filename=".importlinter")` | ✓ WIRED | Re-run live: both `test_import_contracts_are_kept` and `test_contract_actually_catches_a_violation` pass |
| `session_actor/actor.py` | `rules_core/resolution.py` | `resolve_2d6(self._roller, ...)` in `_prepare_resolve_check` | ✓ WIRED | Confirmed by direct file read |
| `session_actor/actor.py` | `event_log/store.py` | `self._store.append(event)` — the only append call site | ✓ WIRED | grep confirms no other module calls `EventStore.append` outside `actor.py` and tests |
| `session_actor/projection.py` | `rules_core/reducer.py` | `fold(...)` over events read from the store | ✓ WIRED | Confirmed by direct file read |
| `cli/main.py` | `session_actor/actor.py` / `projection.py` | `SessionRegistry` / `rebuild_state` | ✓ WIRED | Confirmed live via CLI invocation |
| `event_log/store.py` | `event_log/schema.py` | `append` serializes via `model_dump_json()`; `read_events` restores via `parse_event` (pydantic `validate_json`, no pickle/eval) | ✓ WIRED | Confirmed by direct file read |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RIG-02 | 01-01, 01-02, 01-04 | 주사위와 판정 계산이 순수 코드로만 일어나며 AI가 수치를 바꿀 수 있는 지점이 없다 | ✓ SATISFIED | `.importlinter` forbidden contract + rules_core import audit + `resolve_2d6`/`reroll_2d6` take only an injected `Roller`; REQUIREMENTS.md already marks RIG-02 `[x]` |
| RIG-06 | 01-02, 01-03, 01-05, 01-06 | 모든 사건이 순서대로 기록되고 현재 상태는 그 기록에서 만들어진다 | ✓ SATISFIED | `EventStore` append-only + composite PK, `rebuild_state`/`fold` always replay from scratch, reverse-verification gate (9 tests) proves all 6 D-11 numbers are derivable; REQUIREMENTS.md already marks RIG-06 `[x]` |

No orphaned requirements — REQUIREMENTS.md's Traceability table maps only RIG-02 and RIG-06 to Phase 1, and both appear in the `requirements:` frontmatter of at least one plan.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found anywhere in `src/gptrpg/` or `tests/` (grepped live). No stub returns, no hardcoded-empty data paths feeding rendered/persisted output.

The prior code review (`01-REVIEW.md`, 2026-08-01) found 0 critical and 5 warning-level robustness gaps (dice-roll bounds not validated at the `rules_core` boundary; `EventStore.initialize()` re-entry leak; unsynced `Grade` literal duplication between `rules_core` and `event_log`; `SessionActor.stop()` not safe under concurrent invocation; a CLI exception-handling gap that could leak a raw traceback for an unanticipated exception class). None of these were found, by this verification, to falsify any of the five ROADMAP success criteria — they are legitimate hardening items for later phases (WR-01 in particular is worth carrying into Phase 2/3 since a misbehaving `Roller` implementation could theoretically write an out-of-range roll into the append-only log), not gaps in what Phase 1 was chartered to prove. Not classified as blockers.

### Human Verification Required

None. The one human-verify checkpoint this phase required (01-06 Task 3 — "재생 출력이 읽히는가") was already resolved during execution with direct human approval, documented in `01-06-SUMMARY.md`'s "Checkpoint Resolution" section, and this verification independently re-confirmed the underlying behavior (byte-identical repeat replay) live.

### Gaps Summary

None. All 5 ROADMAP success criteria are independently verified against the live codebase (not just SUMMARY.md claims): full test suite re-run (142 passed), `uv run lint-imports` re-run (2 contracts kept, 0 broken), `uv run ruff check .` re-run (clean), and a live CLI session built and replayed twice with byte-identical output. `.importlinter`'s pipe-separated sibling syntax and `include_external_packages = True` were checked directly in the file (not inferred from the plan), and the "contract actually catches a violation" test was re-run live to confirm it isn't decorative.

---

_Verified: 2026-08-01T18:30:00Z_
_Verifier: Claude (gsd-verifier)_

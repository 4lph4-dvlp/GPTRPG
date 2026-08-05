---
phase: 01-rules-core-and-event-log
plan: 03
subsystem: event-log
tags: [pydantic, sqlite, discriminated-union, event-sourcing, sequence-conflict]

requires:
  - phase: 01-02
    provides: "Event envelope shape (session_id, seq, schema_version, visibility, caused_by_seq, recorded_at), CheckResolved event, EventStore with composite PK optimistic concurrency, apply_event/fold reducer skeleton"
provides:
  - "Final six event types locked: ActionDeclared, ActionConfirmed, CheckResolved, NarrationAppended, ClockAdvanced, AiInvoked -- GameEvent is now a real Annotated[Union[...], Field(discriminator=\"event_type\")]"
  - "apply_event handles all six types (turn_count, check_count/miss_count/last_grade, narration_count, clock_advances/clock_segment, ai_calls/total_tokens) and raises UnknownEventType instead of silently no-op-ing on an unrecognized event_type"
  - "read_events(session_id, from_seq) inclusive-boundary contract stated explicitly in its docstring and locked by test"
  - "tests/test_event_log.py: 75 tests across schema / fold / concurrency, selectable via -k"
affects: [01-04, 01-05, 01-06, Phase 3, Phase 4, Phase 6]

tech-stack:
  added: []
  patterns:
    - "GameEvent = Annotated[Union[Six types...], Field(discriminator=\"event_type\")] -- Python's typing.Union collapses a single-member union to that member, so a real discriminated union needs >=2 members; 01-02 deferred this until now"
    - "apply_event raises UnknownEventType(event_type) on an unrecognized event_type rather than silently advancing last_seq only -- adding a new event type without a matching reducer branch can no longer pass unnoticed"
    - "Concurrency test opens two independent EventStore instances (each with its own sqlite3 connection) from separate threads writing the same (session_id, seq) -- sqlite3 connections are thread-bound, so each thread must own its own EventStore, not share one created in the test's main thread"

key-files:
  created: []
  modified:
    - src/gptrpg/event_log/schema.py
    - src/gptrpg/event_log/store.py
    - src/gptrpg/rules_core/reducer.py
    - tests/test_event_log.py

key-decisions:
  - "No architectural checkpoint needed (see plan's \"되돌릴 수 없는 결정에 체크포인트를 넣지 않은 이유\" section) -- D-10/D-13 were already locked by the human in 01-CONTEXT.md; this plan only fixes the field names, which is Claude's Discretion per 01-RESEARCH.md's D-11 reverse-verification criterion."
  - "UnknownEventType is a new reducer-level exception (not part of the plan's exports list) added under deviation Rule 2 (missing critical functionality) -- the plan's action text explicitly requires '모르는 종류가 오면 예외를 던진다', but 01-02's apply_event silently fell through to a last_seq-only update for anything it didn't recognize. Making that failure mode an explicit exception is required to satisfy the plan's own acceptance criteria, so it was implemented as written rather than treated as a separate ask."

patterns-established:
  - "Every non-envelope field on the six event types is required with no default (aside from the inherited visibility='public') -- 'required unless the field default already answers the M0 scope question' is the rule new event types should follow"

requirements-completed: [RIG-06]

coverage:
  - id: D1
    description: "Six event types (action_declared, action_confirmed, check_resolved, narration_appended, clock_advanced, ai_invoked) each have their required fields locked in code; a minimal valid payload succeeds, a payload missing any one required field is rejected with a message naming the class and field, and a payload with a typo'd extra field is rejected"
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_event_log.py -k schema (61 parametrized cases: minimal valid payload x6, missing required field x23, extra field x6, frozen x6, visibility default/reject x6, schema_version x6, parse_event roundtrip x6, reroll roundtrip, unknown event_type rejection)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Created event objects are immutable (frozen=True inherited from EventEnvelope) and an unrecognized event_type is rejected by the discriminated union rather than silently accepted"
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_event_log.py::test_schema_event_object_is_frozen (parametrized x6), tests/test_event_log.py::test_schema_unknown_event_type_is_rejected"
        status: pass
      - kind: manual_procedural
        ref: "uv run python -c \"from gptrpg.event_log.schema import EVENT_ADAPTER; EVENT_ADAPTER.validate_python({'event_type':'nope'})\" (non-zero exit, confirmed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "apply_event folds all six event types into the matching GameState counters (turn_count, check_count/miss_count/last_grade, narration_count, clock_advances/clock_segment, ai_calls/total_tokens), and raises UnknownEventType for any event_type it doesn't recognize instead of silently no-op-ing"
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_event_log.py::test_fold_all_six_types_move_the_matching_state_fields, tests/test_event_log.py::test_fold_apply_event_raises_for_unknown_event_type"
        status: pass
    human_judgment: false
  - id: D4
    description: "Empty and single-event sessions fold without exception (last_seq=-1 for empty, correct last_seq for one event); folding the same record twice produces identical results (fold has no side effects)"
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_event_log.py::test_fold_empty_session_has_initial_state_and_last_seq_negative_one, tests/test_event_log.py::test_fold_single_event_session_is_handled, tests/test_event_log.py::test_fold_is_pure_folding_same_record_twice_gives_same_result"
        status: pass
    human_judgment: false
  - id: D5
    description: "First event's seq is 0; read_events(session_id, from_seq=n) includes seq==n in its result (inclusive boundary, now stated in the docstring); results are always ascending seq order even if rows were inserted out of order; two sessions interleaved in one SQLite file reconstruct identically to each session stored alone"
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_event_log.py::test_fold_first_event_seq_is_zero_and_read_events_from_seq_includes_boundary, tests/test_event_log.py::test_fold_read_events_is_always_in_ascending_seq_order_even_if_inserted_out_of_order, tests/test_event_log.py::test_fold_two_sessions_interleaved_in_one_file_reconstruct_independently, tests/test_event_log.py::test_fold_read_events_docstring_states_boundary_is_inclusive"
        status: pass
    human_judgment: false
  - id: D6
    description: "Writing the same (session_id, seq) twice -- whether sequentially on one EventStore or concurrently from two independent EventStore connections on separate threads -- results in exactly one persisted event and SequenceConflict (or, for genuine same-instant file-lock contention, sqlite3.OperationalError) on the loser; EventStore exposes exactly five public methods (initialize, next_seq, append, read_events, close), so no update/delete path exists; recorded_at roundtrips character-for-character through storage"
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_event_log.py::test_fold_duplicate_seq_write_is_rejected_and_only_one_event_persists, tests/test_event_log.py::test_concurrency_same_session_same_seq_twice_second_write_is_rejected, tests/test_event_log.py::test_concurrency_two_connections_writing_same_seq_only_one_commits, tests/test_event_log.py::test_fold_event_store_public_method_names_are_exactly_five, tests/test_event_log.py::test_fold_timestamp_roundtrips_character_for_character"
        status: pass
    human_judgment: false

duration: ~25min
completed: 2026-07-31
status: complete
---

# Phase 01-03: Six Event Types Locked + Store/Reducer Widened Summary

**The event schema is now closed at six types (action_declared/action_confirmed/check_resolved/narration_appended/clock_advanced/ai_invoked) as a real pydantic discriminated union, with the storage layer and reducer widened to handle all six and reject anything unrecognized instead of silently ignoring it.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-31T04:25:38Z (per STATE.md's last_updated at plan start)
- **Completed:** 2026-07-31T04:33:12Z
- **Tasks:** 2/2 completed
- **Files modified:** 4 (0 created, 4 modified)

## Accomplishments

- **Task 1 (schema):** Added `ActionDeclared`, `ActionConfirmed`, `NarrationAppended`, `ClockAdvanced`, `AiInvoked` to `event_log/schema.py` alongside 01-02's `CheckResolved`. `GameEvent` is now a genuine `Annotated[Union[...], Field(discriminator="event_type")]` (01-02 left it as a plain single-member alias since `typing.Union` collapses with one member). All six inherit `EventEnvelope`'s `extra="forbid"` + `frozen=True`, so a missing required field, a typo'd extra field, or a post-construction mutation attempt are all rejected by pydantic before anything reaches storage. An unrecognized `event_type` is rejected by the discriminator itself.
- **Task 2 (store + reducer):** `rules_core/reducer.py`'s `apply_event` now folds all six types into `GameState`'s matching counters and raises a new `UnknownEventType` exception for anything it doesn't recognize -- replacing 01-02's placeholder fallback that silently advanced `last_seq` only for unhandled types (which would have let a newly-added event type pass through the reducer unnoticed). `event_log/store.py`'s `read_events` docstring now states its inclusive-boundary contract explicitly (the behavior -- `seq >= ?` -- was already inclusive; only the documentation and an explicit test were missing).
- **75 tests in `tests/test_event_log.py`**, selectable via `-k schema` (61 cases), `-k fold` (12 cases), or `-k concurrency` (2 cases) exactly as the plan required. Covers: minimal valid payload per type, missing-required-field per unique field (23 cases), extra-field rejection per type, frozen-object rejection per type, visibility default/rejection per type, schema_version match per type, `parse_event` roundtrip per type, a `check_resolved` reroll case (4 rolls), unknown `event_type` rejection, all-six-types-fold-correctly, unknown-type-raises, empty/single-event session handling, fold purity, seq-0 + inclusive `from_seq` boundary, out-of-order-insert-still-reads-ascending, two-sessions-interleaved-reconstruct-independently, duplicate-seq rejection, timestamp roundtrip, `EventStore`'s exactly-five-public-methods invariant, and the two-thread same-seq concurrency race.
- Full regression baseline held: `uv run pytest` (88 passed, including 01-02's tracer and replay-roller tests), `uv run lint-imports` (2 contracts kept, 0 broken -- the reducer still imports nothing from `event_log`), `uv run ruff check .` (clean).

## Task Commits

Each task was committed atomically:

1. **Task 1: Lock six event type schemas with required fields** - `b22455d` (feat)
2. **Task 2: Widen store and reducer to all six event types, lock concurrency guarantees** - `e773867` (feat)

## Files Created/Modified

- `src/gptrpg/event_log/schema.py` - Added `ActionDeclared`, `ActionConfirmed`, `NarrationAppended`, `ClockAdvanced`, `AiInvoked`; `GameEvent` became a real discriminated union; added `schema_version` (D-12) regime docstring at module top
- `src/gptrpg/event_log/store.py` - `read_events` docstring now states the inclusive `from_seq` boundary explicitly (behavior unchanged, already inclusive)
- `src/gptrpg/rules_core/reducer.py` - `apply_event` handles all six event types; added `UnknownEventType` exception raised for any unrecognized `event_type`
- `tests/test_event_log.py` - New file, 75 tests across schema/fold/concurrency

## Decisions Made

- **No checkpoint before Task 1's `one-way` reversibility rating.** The plan itself documents why: D-10 and D-13 were already locked by the human in `01-CONTEXT.md`; re-asking would be re-litigating a closed decision, not confirming an open one. The only genuinely open architectural item in this wave (`caused_by_seq`) was already resolved as a checkpoint in 01-02's Task 1.
- **`UnknownEventType` added as a new reducer-level exception**, not in the plan's `<interfaces>` exports table. The plan's Task 2 `<action>` text explicitly says "모르는 종류가 오면 예외를 던진다" (raise an exception for an unknown type) and the acceptance criteria require a test asserting exactly that -- so this isn't scope creep, it's implementing what the plan's own prose specifies where the interfaces table was silent on the exception's name.
- **Field naming for `ActionConfirmed`.** Followed the plan's explicit instruction not to store a confidence/certainty score -- only `system_suggestion` (dict) and `player_confirmed` (bool) are stored, since every classification is human-confirmed anyway and a confidence number wouldn't be a game truth.

## Deviations from Plan

None -- plan executed exactly as written. The `UnknownEventType` exception (see Decisions Made above) is implementing the plan's own action text, not a deviation from it.

## Issues Encountered

**Thread-local sqlite3 connections in the concurrency test.** The first draft of `test_concurrency_two_connections_writing_same_seq_only_one_commits` created both `EventStore` instances (and called `.initialize()`, which opens the `sqlite3.connect()`) in the test's main thread, then handed them to two worker threads. Python's `sqlite3` module raises `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread` in that case (the default `check_same_thread=True` behavior, which `EventStore.initialize()` correctly leaves untouched -- per 01-RESEARCH.md's Pattern 3, loosening it would remove a genuine safety net). Fixed by moving `EventStore(...)` construction and `.initialize()` inside each worker thread's own function, so each thread owns a connection it created itself -- still faithfully modeling "two independent writers hit the same file," which is what the plan's action text asks the test to prove (`애플리케이션 안의 잠금 장치로 대신하지 않는다`).

## Next Phase Readiness

- The six event type names and their required fields (see `01-03-PLAN.md`'s `<interfaces>` table, reproduced verbatim in the schema classes) are now locked for Phase 3 (`action_declared`/`action_confirmed`/`ai_invoked` producers), Phase 4 (`clock_advanced` producer), and Phase 6 (all six as measurement inputs -- MEAS-01~04).
- `schema_version` regime is documented at the top of `schema.py`: old records are never rewritten in place; a real shape change bumps `EVENT_SCHEMA_VERSION` and adds a legacy-version read path. No such path exists yet because no shape change has happened -- this is a contract for future plans, not a gap in this one.
- `apply_event`'s new `UnknownEventType` exception means any future event type added to `schema.py` without a matching reducer branch will fail loudly (a test, or real replay, will raise) rather than silently under-counting -- this directly protects Phase 6's measurement pipeline from a class of bug that would otherwise only surface after both M0 experiment sessions are already recorded and unreplayable.
- 01-04/01-05/01-06 can build directly on `EventStore`, `apply_event`, and `fold` without further widening -- all six types are fully wired end-to-end (construct → append → read → parse → fold).

---
*Phase: 01-rules-core-and-event-log*
*Completed: 2026-07-31*

## Self-Check: PASSED

All 4 modified files verified present on disk with the expected symbols; both task commits (`b22455d`, `e773867`) verified present in `git log --oneline --all`; `uv run pytest tests/test_event_log.py -x` (75 passed), `uv run pytest` (88 passed), `uv run lint-imports` (2 kept, 0 broken), and `uv run ruff check .` (clean) all re-verified after the final commit.

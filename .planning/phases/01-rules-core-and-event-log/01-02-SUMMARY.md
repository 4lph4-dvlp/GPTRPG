---
phase: 01-rules-core-and-event-log
plan: 02
subsystem: rules-engine
tags: [pydantic, sqlite, asyncio, hypothesis, event-sourcing, dice]

requires:
  - phase: 01-01
    provides: "uv-managed src-layout package with four bounded subpackages (rules_core, event_log, session_actor, cli) and a live import-linter + ruff boundary contract"
provides:
  - "First real end-to-end path: CLI `submit` -> SessionActor (asyncio.Queue, single consumer) -> rules_core.resolve_2d6 (pure) -> event_log.EventStore.append (SQLite) -> CLI `replay` -> rebuild_state (fold from scratch, no snapshot)"
  - "Locked event envelope shape (session_id, seq, schema_version, visibility, caused_by_seq, recorded_at) and the check_resolved event's required fields (move, rolls, modifiers, target, grade)"
  - "ReplayRoller / ReplayExhausted / rolls_from_events — deterministic dice replay with explicit failure on exhaustion instead of silently fabricating values"
affects: [01-03, 01-04, 01-05, 01-06]

tech-stack:
  added: []
  patterns:
    - "Roller Protocol (structural typing, PEP 544) injected into resolve_2d6 — LiveRoller (secrets) and ReplayRoller (recorded values) both satisfy it without inheritance"
    - "rules_core.reducer.apply_event takes (event_type: str, payload: Mapping), never a pydantic event object — the only way session_actor bridges rules_core and event_log without either importing the other"
    - "event_log/schema.py re-declares its own Grade Literal instead of importing rules_core.grading.Grade — siblings in the layers contract must stay independent"
    - "sqlite3.IntegrityError branched on e.sqlite_errorcode == SQLITE_CONSTRAINT_PRIMARYKEY, never string-matched, to survive SQLite message wording changes"

key-files:
  created:
    - src/gptrpg/rules_core/dice.py
    - src/gptrpg/rules_core/grading.py
    - src/gptrpg/rules_core/resolution.py
    - src/gptrpg/rules_core/reducer.py
    - src/gptrpg/event_log/schema.py
    - src/gptrpg/event_log/store.py
    - src/gptrpg/event_log/replay_roller.py
    - src/gptrpg/session_actor/live_roller.py
    - src/gptrpg/session_actor/actor.py
    - src/gptrpg/session_actor/projection.py
    - src/gptrpg/cli/main.py
    - tests/test_tracer.py
    - tests/test_dice_replay.py
  modified:
    - pyproject.toml

key-decisions:
  - "Task 1 checkpoint (caused_by_seq): option-a selected — the event envelope and events table carry a nullable caused_by_seq integer. Without it, Phase 6's two response-latency measurements (input->confirmation, confirmation->first narration token) cannot be computed when multiple players submit near-simultaneously, and the two M0 experiment sessions cannot be rerun to backfill the field."
  - "GameEvent is currently a plain alias (GameEvent = CheckResolved), not a real discriminated Union — Python's typing.Union collapses a single-member union to that member, so a Field(discriminator=...) has nothing to discriminate yet. 01-03 turns this into a genuine Annotated[Union[...], Field(discriminator=\"event_type\")] once more event types exist."
  - "SessionActor.state is rebuilt via apply_event on every processed command (not by re-reading the store) to keep the live-session code path exercising the same reducer that replay uses, without adding an extra read after every append"

patterns-established:
  - "Every rules_core module imports only typing/dataclasses/collections.abc — verified both by the import-linter forbidden contract and a direct ast-walk check for pydantic imports"
  - "CLI subcommands (submit/replay) contain zero game rules — they only marshal argv into typed calls against session_actor"

requirements-completed: [RIG-02, RIG-06]

coverage:
  - id: D1
    description: "A single check resolves end-to-end: CLI submit queues a command, SessionActor resolves 2d6 via the pure rules_core and appends one check_resolved event to SQLite; CLI replay reads that file from scratch and reconstructs state with no snapshot involved, and two replay runs of the same file produce byte-identical output"
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_tracer.py#test_submit_twice_appends_two_events_with_sequential_seq"
        status: pass
      - kind: unit
        ref: "tests/test_tracer.py#test_replay_shows_check_count_and_last_grade"
        status: pass
      - kind: unit
        ref: "tests/test_tracer.py#test_replay_output_is_identical_across_two_runs"
        status: pass
      - kind: manual_procedural
        ref: "uv run gptrpg submit --db <tmp> --session s1 --command roll --move '문을 부순다' && uv run gptrpg replay --db <tmp> --session s1 (run twice, diffed, identical)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A resolved check's stored event carries the full calculation trail (two 1-6 rolls, modifiers with type/value/source, target, grade) and the rules_core dice/grading math never touches AI, time, randomness, or storage directly (RIG-02)"
    requirement: "RIG-02"
    verification:
      - kind: unit
        ref: "tests/test_tracer.py#test_stored_check_event_has_full_calculation_detail"
        status: pass
      - kind: unit
        ref: "tests/test_tracer.py#test_resolve_2d6_total_and_grade_are_internally_consistent"
        status: pass
      - kind: automated
        ref: "uv run python -c \"import ast,pathlib,sys; sys.exit(any('pydantic' in n.names[0].name for p in pathlib.Path('src/gptrpg/rules_core').rglob('*.py') for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,ast.Import)))\" (exit 0)"
        status: pass
      - kind: automated
        ref: "uv run lint-imports (2 contracts kept, 0 broken)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Replaying the same recorded dice values always reproduces the same rolls/total/grade, and requesting more rolls than were recorded fails explicitly with ReplayExhausted instead of fabricating a value"
    requirement: "RIG-02"
    verification:
      - kind: unit
        ref: "tests/test_dice_replay.py#test_replay_reproduces_three_checks_recorded_from_live_rolls"
        status: pass
      - kind: unit
        ref: "tests/test_dice_replay.py#test_replay_roller_raises_replay_exhausted_when_rolls_run_out"
        status: pass
      - kind: unit
        ref: "tests/test_dice_replay.py#test_live_roller_always_returns_one_to_six"
        status: pass
      - kind: unit
        ref: "tests/test_dice_replay.py#test_replaying_same_recorded_rolls_twice_is_always_deterministic (hypothesis property test)"
        status: pass
    human_judgment: false

duration: ~55min
completed: 2026-07-31
status: complete
---

# Phase 01-02: Tracer + Replay Roller Summary

**One real path wired end-to-end — CLI `submit` queues a command through a single-writer SessionActor, resolves 2d6 in pure rules_core, appends one `check_resolved` event to a SQLite log with `PRIMARY KEY (session_id, seq)`, and CLI `replay` folds that log from scratch (no snapshot) back into human-readable state — plus a `ReplayRoller` that feeds recorded dice values back through the same `resolve_2d6` for deterministic re-derivation.**

## Performance

- **Duration:** ~55 min (includes a blocking architectural checkpoint relayed by the orchestrator)
- **Started:** 2026-07-31T03:39:59Z (approx., per STATE.md's last_updated at plan start)
- **Completed:** 2026-07-31T04:24:14Z
- **Tasks:** 2/2 completed (Task 1 was the checkpoint:decision gate, resolved via orchestrator relay per this plan's explicit note that gate="blocking" — not "blocking-human" — permits relay)
- **Files modified:** 14 (13 created, 1 modified)

## Accomplishments
- **Task 1 decision resolved: option-a.** The event envelope and `events` table both carry a nullable `caused_by_seq INTEGER` — required for Phase 6 to compute the two response-latency measurements (MEAS-02) when multiple players submit near-simultaneously, and irrecoverable after the fact since the two M0 experiment sessions can't be rerun.
- **Tracer (Task 2):** `submit --command roll` → `SessionActor` (asyncio.Queue, single consumer) → `resolve_2d6` (pure, Roller-Protocol-injected) → `EventStore.append` (SQLite, WAL, optimistic concurrency via composite PK) → `replay` → `rebuild_state` (read-only fold, no snapshot) → human-readable stdout. Two replay runs of the same file produce byte-identical output.
- **Replay roller (Task 3):** `ReplayRoller` feeds recorded rolls back through the unmodified `resolve_2d6`, reproducing rolls/total/grade exactly; exhaustion raises `ReplayExhausted` (converted from `StopIteration`, never left to leak) instead of silently fabricating a value. A hypothesis property test proves replaying the same recorded rolls twice is always deterministic.
- Boundary contract from 01-01 held under real code: `uv run lint-imports` — 2 contracts kept, 0 broken; `rules_core/` verified via AST walk to import zero `pydantic`.

## Task Commits

Each task was committed atomically:

1. **Task 1: caused_by_seq decision checkpoint** — no commit (decision-only gate; option-a recorded here, no files touched before the decision per the plan's acceptance criteria)
2. **Task 2: tracer — CLI submit/replay through rules_core to event log** - `810d95c` (feat)
3. **Task 3: replay roller — feed recorded rolls back through resolve_2d6** - `7b9f6dc` (feat)

## Files Created/Modified
- `pyproject.toml` - `[project.scripts] gptrpg = "gptrpg.cli.main:main"` added
- `src/gptrpg/rules_core/dice.py` - `Roller` Protocol (structural, `roll_d6() -> int`)
- `src/gptrpg/rules_core/grading.py` - `Grade`, `DEFAULT_TARGET`, `WEAK_HIT_BAND`, `grade_for_total`
- `src/gptrpg/rules_core/resolution.py` - `Modifier`, `CheckOutcome`, `resolve_2d6`
- `src/gptrpg/rules_core/reducer.py` - `GameState`, `initial_state`, `apply_event`, `fold`
- `src/gptrpg/event_log/schema.py` - `EventEnvelope`, `ModifierRecord`, `CheckResolved`, `GameEvent`, `parse_event`, `utc_now_iso` — `extra="forbid"` + `frozen=True`
- `src/gptrpg/event_log/store.py` - `EventStore` (SQLite, WAL, composite PK), `SequenceConflict`
- `src/gptrpg/event_log/replay_roller.py` - `ReplayRoller`, `ReplayExhausted`, `rolls_from_events`
- `src/gptrpg/session_actor/live_roller.py` - `LiveRoller` (`secrets.randbelow(6) + 1`)
- `src/gptrpg/session_actor/actor.py` - `SessionActor`, `ResolveCheck`, `CommandRejected`
- `src/gptrpg/session_actor/projection.py` - `rebuild_state` (read-only)
- `src/gptrpg/cli/main.py` - `main`, `submit`/`replay` subcommands
- `tests/test_tracer.py` - end-to-end integration assertions (5 tests)
- `tests/test_dice_replay.py` - replay determinism + exhaustion + property-based test (4 tests)

## Decisions Made
- **caused_by_seq: option-a** (see Task 1 checkpoint above) — this was the only architectural decision in this plan; recorded in frontmatter `key-decisions`.
- `GameEvent = CheckResolved` (plain alias, not yet a real discriminated Union) — deferred until 01-03 adds the remaining 5 event types, since `typing.Union` with one member collapses to that member and a `discriminator` field needs at least two.
- `event_log/schema.py` re-declares its own `Grade` Literal rather than importing `rules_core.grading.Grade`, keeping the two sibling layers independent per the import-linter `layers` contract (verified: `lint-imports` still passes with 0 broken contracts).

## Deviations from Plan

None — plan executed exactly as written, including the Task 1 checkpoint gate (no `event_log/schema.py` or `store.py` existed before the decision was resolved — verified via `test ! -f` before implementation began).

## Issues Encountered

**Checkpoint resolution channel.** Task 1 is `type="checkpoint:decision" gate="blocking"` (not `gate="blocking-human"`). Per this plan's explicit scope note ("the orchestrator will present it to the user and relay their choice back to you to continue"), the orchestrator relayed the user's direct selection of option-a. This is architecturally distinct from the `gate="blocking-human"` package-legitimacy checkpoint in 01-01, which specifically required a verified direct human channel and could not be satisfied by any orchestrator relay — the two gate types intentionally have different resumption rules.

## Next Phase Readiness
- The event envelope shape (`session_id`, `seq`, `schema_version`, `visibility`, `caused_by_seq`, `recorded_at`) and the `check_resolved` event's required fields are locked — 01-03 adds the remaining 5 event types (`action_declared`, `action_confirmed`, `narration_appended`, `clock_advanced`, `ai_invoked`) on top of this shape without renaming anything established here.
- `apply_event`'s "unknown event type → advance `last_seq` only" fallback is already in place, so 01-03 can add new `event_type` branches to the reducer incrementally without breaking `fold` for events it doesn't yet recognize.
- `GameEvent` will need to become a real `Annotated[Union[...], Field(discriminator="event_type")]` once 01-03 adds more members — flagged above as a known, intentional gap, not a stub that silently under-serves anything in scope for this plan.
- `uv run pytest -q` (13 passed), `uv run ruff check .`, and `uv run lint-imports` all exit 0 as the standing regression baseline for 01-03 onward.

---
*Phase: 01-rules-core-and-event-log*
*Completed: 2026-07-31*

## Self-Check: PASSED

All 13 created/modified files verified present on disk; both task commits (`810d95c`, `7b9f6dc`) verified present in `git log --oneline --all`.

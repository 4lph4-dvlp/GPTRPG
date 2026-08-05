---
phase: 04-experiment-tool
plan: 05
subsystem: api
tags: [fastapi, asyncio-to-thread, layers, action-classifier, master-gm, sse-polling]

requires:
  - phase: 04-experiment-tool
    provides: "04-01: gptrpg.web FastAPI package (create_app, validate_session_id, event-loop-only sqlite discipline)"
  - phase: 04-experiment-tool
    provides: "04-03: SessionActor auto-advance/report-snapshot hook, GameState.fails_since_clock"
  - phase: 04-experiment-tool
    provides: "04-04: PLAYER_CHARACTERS/get_character (real player stats reusing Entity/StatEntry), gptrpg_character cookie"
provides:
  - "gptrpg.turn package: build_turn_context(store, session_id, rulebook_id, *, character_stats=None) — single shared turn-context assembler for both cli and web, sitting as a new import-linter layer between gptrpg.cli|gptrpg.web and gptrpg.agents"
  - "POST /api/sessions/{id}/actions/declare — records the raw sentence first, then runs classify() off the event loop via asyncio.to_thread, returns move candidates + tier"
  - "POST /api/sessions/{id}/actions/confirm — confirm/reject -> ResolveCheck (always before narration) -> streamed AppendNarration per sentence -> unconditional RecordAiCall(master_gm)"
  - "create_app(provider_resolver=, agent_config_path=) test-injection seam for HTTP-layer tests with no network/API keys"
affects: [04-06]

actuals:
  tokens: 12785
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "A layer that assembles TurnContext by reading store state sits directly above gptrpg.agents in the import-linter layer stack (below cli|web) — the only position that can see both event_log/session_actor (for state) and agents (for the TurnContext dataclass) while both cli and web sit above it"
    - "Blocking AI SDK calls (classify(), and each narration chunk fetched via next()) go through asyncio.to_thread; every actor.submit()/store read stays on the event-loop thread that owns the sqlite3 connection — verified by two acceptance-criteria greps rather than by convention alone"
    - "next(narration_iter, _NO_SENTENCE) sentinel pattern instead of letting StopIteration propagate from next() — asyncio.to_thread's underlying Future explicitly forbids raising StopIteration across its boundary and converts it to RuntimeError instead"

key-files:
  created:
    - src/gptrpg/turn/__init__.py
    - src/gptrpg/turn/context.py
    - src/gptrpg/web/routes_actions.py
    - tests/test_web_actions.py
  modified:
    - .importlinter
    - pyproject.toml
    - src/gptrpg/cli/turn_flow.py
    - src/gptrpg/web/routes_events.py
    - src/gptrpg/web/app.py
    - tests/conftest.py

key-decisions:
  - "gptrpg.turn inserted as a brand-new import-linter layer (gptrpg.cli|gptrpg.web / gptrpg.turn / gptrpg.agents / ...) rather than folding context assembly into an existing layer — agents can't import event_log/session_actor (contract:3), and cli/web can't import each other (contract:2's top tier), so a shared turn-context builder had exactly one legal position"
  - "PLACEHOLDER_CLOCK_SEGMENT_COUNT collapsed from three separate declarations (cli/turn_flow.py, web/routes_events.py, and the constant's own original home) into gptrpg.turn.context — the three-way duplication existed only because 04-01 had no shared layer available yet"
  - "cli/turn_flow.py keeps _build_turn_context as a one-way alias (`_build_turn_context = build_turn_context`) purely so tests/test_turn_tracer.py's `from gptrpg.cli.main import _build_turn_context` re-export keeps resolving — no logic lives at that name anymore"
  - "web_client_with_fake_provider (tests/conftest.py) is a factory fixture, not a fixed fixture — declare and confirm need independently-controllable action_classifier/master_gm FakeProvider instances per test (empty candidates, unknown-move payloads, a raising narration stream), so the fixture returns a callable that builds a fresh TestClient per invocation"
  - "Narration continuation loop reads with next(narration_iter, _NO_SENTENCE) instead of catching StopIteration — confirmed via a standalone repro that asyncio.to_thread converts a StopIteration crossing its Future boundary into RuntimeError; cli/turn_flow.py's synchronous version never hits this because it never crosses a Future"

requirements-completed: [RIG-07, RIG-05]

coverage:
  - id: D1
    description: "A single build_turn_context() function assembles TurnContext for both the CLI turn flow and the web declare/confirm routes — no second implementation exists"
    requirement: RIG-05
    verification:
      - kind: unit
        ref: "tests/test_turn_tracer.py, tests/test_turn_flow_failure.py, tests/test_tracer.py (18 tests, cli flow regression-free after the move)"
        status: pass
      - kind: static
        ref: "grep -c 'PLACEHOLDER_CLOCK_SEGMENT_COUNT = 6' src/gptrpg/turn/context.py == 1; same grep == 0 in cli/turn_flow.py and web/routes_events.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "The TurnContext passed to both classify() and narrate() carries the acting player's real character stats (via characters_data.get_character), not the placeholder single-stat foe"
    requirement: RIG-05
    verification:
      - kind: unit
        ref: "tests/test_web_actions.py::test_prompt_carries_the_acting_character_real_stat_names"
        status: pass
    human_judgment: false
  - id: D3
    description: "POST /actions/declare records action_declared before running classification, so the event survives regardless of classification outcome (including UnknownMove); returns candidates + tier (none/single/several) with no confidence-score field"
    requirement: RIG-07
    verification:
      - kind: unit
        ref: "tests/test_web_actions.py (9 declare-path tests: single/none tiers, action_declared survives a 400 UnknownMove failure, ai_invoked.caused_by_seq, length/character validation, no observation-metric leakage)"
        status: pass
    human_judgment: false
  - id: D4
    description: "classify() and each streamed narration chunk fetch run off the event loop via asyncio.to_thread; every actor.submit()/store read stays on the event-loop thread"
    requirement: RIG-07
    verification:
      - kind: static
        ref: "grep -c 'asyncio.to_thread' src/gptrpg/web/routes_actions.py -ge 1; ! grep -Eq 'to_thread\\([^)]*submit' src/gptrpg/web/routes_actions.py"
        status: pass
    human_judgment: true
    rationale: "The grep proves the code shape (no actor.submit inside a to_thread call) but not the live effect (the other three browsers' polling actually keeps responding during a 2-15s AI call) — that observation needs a real multi-tab session, deferred to 04-06's live QA pass per the plan's own Flagged Assumptions §1"
  - id: D5
    description: "POST /actions/confirm submits ResolveCheck strictly before any narration submission — check_resolved always gets a lower seq than every narration_appended event for that turn, by code order rather than a conditional"
    verification:
      - kind: unit
        ref: "tests/test_web_actions.py::test_check_resolved_seq_precedes_every_narration_appended_seq"
        status: pass
    human_judgment: false
  - id: D6
    description: "A rejected confirmation (confirmed=false) produces zero check_resolved events; RecordAiCall(master_gm) is submitted unconditionally on both narration success and failure, so a failed turn still contributes a latency sample"
    verification:
      - kind: unit
        ref: "tests/test_web_actions.py::test_confirm_rejected_produces_no_check_resolved_event, ::test_narration_failure_returns_502_but_records_master_gm_ai_call"
        status: pass
    human_judgment: false
  - id: D7
    description: "Observation metrics (clock_advances, fails_since_clock) never appear in the prompt sent to either agent role"
    verification:
      - kind: unit
        ref: "tests/test_web_actions.py::test_prompt_never_carries_clock_advance_count_or_failure_accumulator"
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-08-03
status: complete
---

# Phase 4 Plan 5: Web Turn Flow (Declare + Confirm) Summary

**Two HTTP round trips replace the CLI's blocking-input turn flow: `POST .../actions/declare` records the raw sentence before classifying it (blocking AI call off the event loop via `asyncio.to_thread`), and `POST .../actions/confirm` submits the dice check strictly before any narration text, streaming sentences into the event log one at a time so the other three browsers see the story arrive via polling.**

## Performance

- **Duration:** ~50 min (3 auto tasks, no checkpoints)
- **Tasks:** 3
- **Files modified:** 10 (4 created, 6 modified)

## Accomplishments

- `gptrpg.turn` package: `build_turn_context()` moved verbatim out of `cli/turn_flow.py` into a new import-linter layer between `gptrpg.cli|gptrpg.web` and `gptrpg.agents` — the only legal position, since `agents` can't import `event_log`/`session_actor` (contract:3) and `cli`/`web` can't import each other (contract:2's top tier). `PLACEHOLDER_CLOCK_SEGMENT_COUNT` collapsed from three separately-declared copies into one.
- `POST /api/sessions/{id}/actions/declare`: submits `DeclareAction` first (raw text is recorded regardless of what classification does next, MEAS-04), builds `TurnContext` with the acting character's real stats, then runs `classify()` via `asyncio.to_thread` so the 2-15s blocking AI call never stalls the other three browsers' polling loop. `UnknownMove`/`CommandRejected` -> 400, `SequenceConflict` -> 409, provider/config errors -> 503.
- `POST /api/sessions/{id}/actions/confirm`: submits `ConfirmAction` first; a rejection short-circuits with zero `ResolveCheck` calls. On confirmation, `ResolveCheck` is submitted and its resulting `check_resolved` event is guaranteed (by code order, not a branch) to have a lower seq than every subsequent `narration_appended` event. Narration streams sentence-by-sentence via `asyncio.to_thread(next, narration_iter, _NO_SENTENCE)`; `RecordAiCall(agent_role="master_gm")` is submitted unconditionally on success or failure so a broken narration stream still leaves a latency sample. Narration failure -> 502 with the UI-SPEC's fixed Korean copy; actor/store faults fall through to the framework default 500.
- `create_app()` gained `provider_resolver`/`agent_config_path` test-injection seams (default `agents.config.resolve_provider`/`DEFAULT_CONFIG_PATH`) so the HTTP-layer test suite runs with zero network calls and zero API keys.
- 15 new tests in `tests/test_web_actions.py` (9 declare-path, 6 confirm-path), all passing on first full run; full 402-test suite green; `lint-imports` passes with `gptrpg.turn` recognized as a real layer.

## Task Commits

Each task was committed atomically:

1. **Task 1: 턴 문맥 조립을 명령줄과 웹이 함께 쓰는 층으로 내린다** - `7c270e2` (feat)
2. **Task 2: 선언 경로 — 문장을 받아 무브 후보를 돌려준다** - `190b898` (feat)
3. **Task 3: 확인 경로 — 판정을 먼저 기록하고 서사를 이어 붙인다** - `25c7092` (feat)

_Note: this is a worktree-isolated parallel agent run — the plan-metadata commit (this SUMMARY.md + REQUIREMENTS.md) is made separately by the execute-plan workflow after this file is written; STATE.md/ROADMAP.md are updated centrally by the orchestrator after all wave agents complete._

## Files Created/Modified

- `src/gptrpg/turn/__init__.py` - empty package marker for the new import-linter layer
- `src/gptrpg/turn/context.py` - `build_turn_context()`, `PLACEHOLDER_CLOCK_SEGMENT_COUNT` (single source)
- `src/gptrpg/cli/turn_flow.py` - `_build_turn_context` reduced to a one-way alias of `build_turn_context`
- `src/gptrpg/web/routes_events.py` - imports `PLACEHOLDER_CLOCK_SEGMENT_COUNT` from `gptrpg.turn.context` instead of re-declaring it
- `src/gptrpg/web/routes_actions.py` - `declare`/`confirm` routes, `DeclareRequest`/`DeclareResponse`/`MoveCandidateView`, `ConfirmRequest`/`ConfirmResponse`, `MAX_RAW_TEXT_LEN`/`MAX_ID_LEN`, `_parse_modifier`, `_last_result_or_failure_envelope`
- `src/gptrpg/web/app.py` - `create_app(provider_resolver=, agent_config_path=)`, `actions_router` registered
- `.importlinter` - `gptrpg.turn` layer inserted into contract:2
- `pyproject.toml` - `"src/gptrpg/turn/*" = ["TID251"]` per-file-ignore
- `tests/conftest.py` - `web_client_with_fake_provider` factory fixture
- `tests/test_web_actions.py` - 15 tests (9 declare, 6 confirm)

## Decisions Made

See `key-decisions` in frontmatter. Summary: `gptrpg.turn` is a genuinely new layer (not folded into an existing one) because it's the only position both `agents` and `event_log`/`session_actor` sit below while `cli`/`web` sit above; the placeholder clock-segment constant collapsed from three copies to one now that the layer exists to hold it; `_build_turn_context` in `cli/turn_flow.py` survives only as a name (`tests/test_turn_tracer.py` compatibility) with zero logic; the confirm route's narration continuation loop had to switch from `next(narration_iter)` (which the CLI uses safely, synchronously) to `next(narration_iter, _NO_SENTENCE)` because `asyncio.to_thread` cannot carry a `StopIteration` across its `Future` boundary — it converts to `RuntimeError` instead, confirmed by an isolated repro before writing the confirm route.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `StopIteration` cannot cross an `asyncio.to_thread` boundary**
- **Found during:** Task 3, before writing the narration continuation loop
- **Issue:** The plan's narration loop (mirroring `cli/turn_flow.py`'s synchronous `while True: try: sentence = next(narration_iter) except StopIteration: break`) would raise `RuntimeError: StopIteration interacts badly with generators and cannot be raised into a Future` the moment a narration stream actually exhausted — confirmed via a standalone `asyncio.to_thread(next, gen)` repro before writing the route, since the CLI's synchronous equivalent never crosses a `Future` and so never hits this.
- **Fix:** Every `next()` call on the narration iterator (first chunk and every subsequent chunk) passes the `_NO_SENTENCE` sentinel as a default instead of relying on `StopIteration`; the loop checks `if sentence is _NO_SENTENCE: break` instead of catching the exception.
- **Files modified:** `src/gptrpg/web/routes_actions.py`
- **Verification:** `tests/test_web_actions.py::test_two_sentence_narration_produces_two_chunked_events` (two-sentence stream reaches natural exhaustion and produces exactly two `narration_appended` events with no `RuntimeError`)
- **Committed in:** `25c7092` (Task 3)

**2. [Rule 2 - Missing functionality] `UnknownRulebook` and malformed `modifiers` strings were unhandled input paths**
- **Found during:** Task 2/Task 3 implementation, reading the plan's exception-mapping list
- **Issue:** The plan's declare-path exception table doesn't name `UnknownRulebook` (raised by `get_rulebook`/`get_moves` for an invalid `rulebook_id`), and the confirm-path `modifiers: list[str]` strings can fail `_parse_modifier`'s `"유형:값:출처"` format or non-integer value — both were request-shaped errors with no explicit mapping, which would otherwise surface as an unhandled 500.
- **Fix:** `UnknownRulebook` folded into the same 400 bucket as `UnknownMove`/`CommandRejected` (invalid caller input, not a server-config problem); a malformed modifier string raises `ValueError` inside `_parse_modifier`, caught and mapped to 400 in the confirm handler.
- **Files modified:** `src/gptrpg/web/routes_actions.py`
- **Verification:** full `uv run pytest -q` suite green; no new test added specifically for these two paths since 04-06's frontend never sends a custom `rulebook_id` or non-empty `modifiers` list (Flagged Assumption #3), but the handler no longer 500s if it ever does
- **Committed in:** `190b898` (Task 2), `25c7092` (Task 3)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 bug avoidance discovered via a standalone repro before it could ship broken, 1 Rule 2 defensive completeness addition for two request-shaped error paths the plan's exception table didn't name).
**Impact on plan:** No architectural changes. Both fixes were required to make each task's own `<verify>` block pass and to avoid an unhandled-500 path the plan's threat model (T-04-23) explicitly asks to avoid.

## Issues Encountered

- `asyncio.to_thread(next, generator)` cannot be used to detect a generator's natural exhaustion via `StopIteration` — Python's asyncio explicitly disallows a `StopIteration` crossing a `concurrent.futures.Future` boundary and converts it to `RuntimeError` instead. Any future code that streams a Python generator through `asyncio.to_thread` in this codebase should use the `next(iterator, sentinel)` two-argument form, never bare `next(iterator)` inside a `try/except StopIteration`.
- No live multi-browser verification was performed for the "AI call doesn't stall other browsers' polling" claim (coverage D4) — the `grep`-based acceptance criteria prove the code never puts `actor.submit(...)` inside a `to_thread` call, but the actual cross-tab experience needs a real session with a slow/real provider. Flagged `human_judgment: true`, deferred to 04-06's live QA pass, consistent with 04-01/04-03/04-04's precedent for this exact class of claim.

## User Setup Required

None — no external service configuration required. All new tests run against `FakeProvider`/`_NarrationRaisingProvider` test doubles injected via `create_app`'s new `provider_resolver` seam; no network calls, no API keys.

## Next Phase Readiness

- The full browser turn loop (declare -> confirm -> narration) now exists end-to-end at the HTTP layer; 04-06 (the actual browser screens) can call these two routes directly.
- The plan's own Flagged Assumptions stand unresolved by design and are explicitly deferred to 04-06's live QA: (1) whether a 15-90s open `POST .../confirm` request while narration streams is acceptable UX for the acting player specifically (the other three see sentences arrive via polling faster than the actor sees their own request resolve), (2) how two simultaneous declarations from different players interleave in the narration feed (the actor queue serializes writes but doesn't prevent interleaved narration between two turns), (3) the `modifiers` field is accepted by the API but 04-06's screen sends it empty — no modifier-input UI exists in this milestone.
- `PLACEHOLDER_CLOCK_SEGMENT_COUNT` now lives in exactly one place (`gptrpg.turn.context`) — any future scenario-data work (EXP-01/M1) that replaces the placeholder only needs to touch this one file.

---
*Phase: 04-experiment-tool*
*Completed: 2026-08-03*

## Self-Check: PASSED

All 10 created/modified files found on disk (`src/gptrpg/turn/__init__.py`, `src/gptrpg/turn/context.py`, `src/gptrpg/web/routes_actions.py`, `tests/test_web_actions.py`, `.importlinter`, `pyproject.toml`, `src/gptrpg/cli/turn_flow.py`, `src/gptrpg/web/routes_events.py`, `src/gptrpg/web/app.py`, `tests/conftest.py`).
All 3 task commit hashes (`7c270e2`, `190b898`, `25c7092`) found in git history.

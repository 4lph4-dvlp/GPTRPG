# Phase 4: 실험 도구 완성 - Pattern Map

**Mapped:** 2026-08-03
**Files analyzed:** 13 (new) + 4 (modified)
**Analogs found:** 15 / 17

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `src/gptrpg/web/app.py` | config/bootstrap | request-response | `src/gptrpg/cli/main.py` (`main()`, arg-parsing/wiring section) | role-match |
| `src/gptrpg/web/routes_events.py` | controller/route | CRUD (read, polling) | `src/gptrpg/cli/main.py` (`_cmd_replay`) + `src/gptrpg/session_actor/projection.py` (`rebuild_state`) | role-match |
| `src/gptrpg/web/routes_actions.py` | controller/route | request-response (split propose/confirm) | `src/gptrpg/cli/turn_flow.py` (`_turn_flow`, declare/classify/confirm/resolve/narrate sections) | role-match (needs restructuring, blocking I/O split) |
| `src/gptrpg/web/routes_characters.py` | controller/route | CRUD (read-only) | `src/gptrpg/cli/main.py` (`_cmd_replay`, simple read + print pattern) | partial match (no existing read-only single-entity endpoint) |
| `src/gptrpg/web/report.py` | service/utility | transform (aggregation) | `src/gptrpg/cli/main.py` (`_cmd_replay`, same GameState fields printed) | exact (fields identical, only output format differs) |
| `src/gptrpg/web/characters_data.py` (new player-character registry) | config/model | CRUD (static lookup) | `src/gptrpg/rulebooks/dungeonworld_like.py` (`EXAMPLE_SINGLE_STAT_FOE` constant) | exact (same `Entity`/`StatEntry` construction pattern) |
| `src/gptrpg/rules_core/reducer.py` (MODIFY: add `fails_since_clock`) | model/reducer | event-driven (fold) | itself — extend existing `apply_event`/`GameState` pattern | exact |
| `src/gptrpg/session_actor/actor.py` (MODIFY: auto-advance hook + report auto-save) | service | event-driven | itself — extend `_process` method | exact |
| `src/gptrpg/cli/main.py` (MODIFY: add `report` subcommand) | controller (CLI) | CRUD (read) | itself — `_cmd_replay` (near-identical shape: init store, rebuild_state, print fields) | exact |
| `tests/test_reducer_fails_since_clock.py` | test | event-driven | `tests/test_reducer_failure_count.py` | exact |
| `tests/test_session_actor_auto_advance.py` | test | event-driven | `tests/test_session_actor.py` | exact |
| `tests/test_web_events.py` | test | request-response | `tests/test_session_actor.py` (fixture/setup style) + FastAPI `TestClient` pattern (no existing analog) | role-match (new pattern needed for `TestClient`) |
| `tests/test_web_characters.py` | test | request-response | same as above | role-match |
| `tests/test_report.py` | test | transform | `tests/test_reducer_failure_count.py` (pure-function unit test style: build fixture `GameState`/pairs, assert fields) | exact |
| `frontend/src/main.ts` | client/poller | streaming (polling) | none — first frontend file in repo | no analog |
| `frontend/index.html`, `frontend/package.json` | config | — | none — first frontend files in repo | no analog |
| `.importlinter` (MODIFY: add `gptrpg.web` co-equal layer) | config | — | itself — contract:2 layers list | exact |
| `pyproject.toml` (MODIFY: add fastapi/uvicorn deps, TID251 exemption for `web/*`) | config | — | itself — `[tool.ruff.lint.per-file-ignores]` existing entries (`cli/*`, `session_actor/*`) | exact |

## Pattern Assignments

### `src/gptrpg/web/app.py` (bootstrap, request-response)

**Analog:** `src/gptrpg/cli/main.py` lines 1-53 (imports) and 102-129 (`_run_submit`/`_cmd_submit` — store lifecycle: init, use, close)

**Imports pattern** (`cli/main.py:1-47`):
```python
import argparse
import asyncio
...
from gptrpg.event_log.store import EventStore, SequenceConflict
from gptrpg.session_actor.actor import (
    AdvanceClock, AppendNarration, Command, CommandRejected,
    ConfirmAction, DeclareAction, RecordAiCall, ResolveCheck, SessionRegistry,
)
from gptrpg.session_actor.projection import rebuild_state
```
`web/app.py` should import the exact same lower layers (`event_log.store`, `session_actor.actor`, `session_actor.projection`) — never re-derive state independently.

**Store lifecycle pattern** (`cli/main.py:102-129`):
```python
store = EventStore(args.db)
store.initialize()
try:
    seq = asyncio.run(_run_submit(store, args.session, command))
except (CommandRejected, SequenceConflict) as exc:
    print(f"오류: {exc}", file=sys.stderr)
    return 1
finally:
    store.close()
```
For the web app, `EventStore.initialize()` should happen once at process startup (FastAPI lifespan/startup event) rather than per-request, and `SessionRegistry` (already handles "one actor per session_id", `session_actor/actor.py:381-403`) should be constructed once and shared across requests — reuse `SessionRegistry.get_or_create(session_id)` exactly as `cli/main.py:103-104` does, don't reinvent session bookkeeping.

**Error handling pattern**: `CommandRejected`/`SequenceConflict` are the two exceptions that cross the session_actor boundary (`session_actor/actor.py:145-146`, `event_log/store.py:23-29`). Routes must catch both and translate to HTTP 4xx, mirroring the CLI's `except (CommandRejected, SequenceConflict) as exc: print(...); return 1` shape — same exception set, different response mechanism (raise `HTTPException` instead of printing + exit code).

---

### `src/gptrpg/web/routes_events.py` (controller, CRUD read/polling)

**Analog:** `src/gptrpg/cli/main.py:132-154` (`_cmd_replay`) + `src/gptrpg/session_actor/projection.py:1-12` (`rebuild_state`)

**Core pattern** (`cli/main.py:132-154`, adapt print-lines to JSON fields):
```python
def _cmd_replay(args: argparse.Namespace) -> int:
    store = EventStore(args.db)
    store.initialize()
    try:
        state = rebuild_state(store, args.session)
    finally:
        store.close()
    print(f"사건 수: {state.last_seq + 1}")
    print(f"턴 수: {state.turn_count}")
    ...
```
`projection.py`'s `rebuild_state(store, session_id)` (lines 7-11) is the single source of truth for "state as of now" — the polling endpoint must call this (or `store.read_events(session_id, from_seq)` directly for the raw event list) rather than re-implementing folding logic, per RESEARCH.md's explicit anti-pattern warning ("never independently compute turn_count/failure_count/clock_segment").

**Read pattern** (`event_log/store.py:93-103`):
```python
def read_events(self, session_id: str, from_seq: int = 0) -> list[GameEvent]:
    """순번 오름차순. 경계는 포함이다."""
    conn = self._require_conn()
    rows = conn.execute(
        "SELECT payload FROM events WHERE session_id = ? AND seq >= ? ORDER BY seq",
        (session_id, from_seq),
    ).fetchall()
    return [parse_event(row[0]) for row in rows]
```
Both D-38 (polling, `from_seq=last_seen+1`) and D-41 (reconnect, `from_seq=0`) call this exact function with different `from_seq` values — the endpoint is a thin wrapper: `store.read_events(session_id, from_seq=from_seq)`, no new sync/resume logic (per RESEARCH.md "Don't Hand-Roll" table).

**Response model pattern**: `GameEvent` (`event_log/schema.py`) is already a pydantic discriminated union — use it directly as `response_model=list[GameEvent]` (FastAPI), don't hand-roll a second wire schema.

---

### `src/gptrpg/web/routes_actions.py` (controller, request-response, propose/confirm split)

**Analog:** `src/gptrpg/cli/turn_flow.py:219-424` (`_turn_flow`)

**Declare + classify pattern** (`turn_flow.py:227-269`, split off the `input()`-driven confirmation, keep the classify+RecordAiCall part verbatim for the `declare` endpoint):
```python
declare_seq = await actor.submit(DeclareAction(player_id=args.player, raw_text=args.text))
rulebook = get_rulebook(args.rulebook)
moves = get_moves(args.rulebook)
ctx = _build_turn_context(store, args.session, args.rulebook)
classifier_choice = _resolve_role_choice(args, "action_classifier")
classifier_provider = resolve_provider("action_classifier", {"action_classifier": classifier_choice}, os.environ)
proposal = classify(provider=classifier_provider, model=classifier_choice.model, ctx=ctx,
                     raw_text=args.text, moves=moves, rulebook_display_name=rulebook.display_name)
ai_result = proposal.ai
await actor.submit(RecordAiCall(agent_role="action_classifier", ..., caused_by_seq=declare_seq))
```
Per RESEARCH.md Pitfall 1, the blocking `classify()` call must be wrapped in `await asyncio.to_thread(...)` inside the FastAPI handler — this is new code, no existing async wrapper to copy, but the surrounding submit/RecordAiCall calls are already `async` (`actor.submit` is `async def`, `session_actor/actor.py:170-178`) and should be `await`ed on the main loop exactly as `turn_flow.py` does.

**Confirm + resolve + narrate loop pattern** (`turn_flow.py:295-410`) — reusable almost verbatim except the `input()`-driven `_read_single_confirmation`/`_prompt_candidate_or_reject` (lines 164-197), which the browser replaces:
```python
confirm_seq = await actor.submit(ConfirmAction(
    player_id=args.player, move=picked.move, stat=picked.stat,
    system_suggestion={"move": suggestion.move, "stat": suggestion.stat},
    player_confirmed=confirmed, caused_by_seq=declare_seq,
))
if not confirmed:
    return 0
resolve_seq = await actor.submit(ResolveCheck(
    move=picked.move, modifiers=modifiers, target=args.target,
    rulebook_id=args.rulebook, caused_by_seq=confirm_seq,
))
check_event = store.read_events(args.session, from_seq=resolve_seq)[0]
```
Narration loop (`turn_flow.py:343-385`) — same per-sentence `AppendNarration` submission pattern, but each `next(narration_iter, ...)` call must move to `asyncio.to_thread` per Pitfall 1.

**Error handling pattern**: `turn_flow.py:359-421` wraps only the AI-stream-generation/iteration in `except Exception` (never `BaseException`), keeps `actor.submit(...)` calls *outside* the narration try block (WR-01 comment, lines 338-342) so session_actor/store failures propagate distinctly from narration failures. Web routes should preserve this same try-block boundary, translating to distinct HTTP status codes (e.g. 502 for narration failure vs 500 for actor/store failure) rather than collapsing both into one generic error.

---

### `src/gptrpg/web/routes_characters.py` (controller, CRUD read-only)

**Analog:** `src/gptrpg/rulebooks/dungeonworld_like.py:36-46` (`EXAMPLE_SINGLE_STAT_FOE`, `Entity`/`StatEntry` construction) — no existing HTTP read-only route to copy from since this is the first web layer.

**Core pattern** (`rules_core/entities.py:64-91`, `Entity`/`StatEntry` dataclasses, frozen and self-validating):
```python
@dataclass(frozen=True)
class Entity:
    entity_id: str
    display_name: str
    rulebook_id: str
    stats: tuple[StatEntry, ...] = ()
```
Per RESEARCH.md Open Question 1 (recommended): author a small `player_id -> Entity` dict as a Python module constant in `web/characters_data.py`, following the exact precedent of `EXAMPLE_SINGLE_STAT_FOE` (`rulebooks/dungeonworld_like.py:36-46`):
```python
EXAMPLE_SINGLE_STAT_FOE = Entity(
    entity_id="dungeonworld_like.example_single_stat_foe",
    display_name="상태값 하나짜리 예시 적",
    rulebook_id=DUNGEONWORLD_LIKE_ID,
    stats=(StatEntry(name="체력", current=5, max=5, depleted_effect_ref="dungeonworld_like.hp_depleted"),),
)
```
The route itself is a simple dict lookup + `Entity` serialization (pydantic can't directly serialize a stdlib `dataclass` without `model_config`/adapter — either add a thin pydantic mirror model or use `dataclasses.asdict()` and return a plain dict, since `Entity` is a `dataclasses.dataclass`, not a pydantic `BaseModel`, unlike `GameEvent`).

---

### `src/gptrpg/web/report.py` (service/utility, transform)

**Analog:** `src/gptrpg/cli/main.py:132-154` (`_cmd_replay`) — same `GameState` fields, only output format differs (print lines vs. JSON dict).

**Core pattern** (fields exactly matching `_cmd_replay`'s prints, `cli/main.py:144-153`):
```python
print(f"사건 수: {state.last_seq + 1}")
print(f"턴 수: {state.turn_count}")
print(f"판정 수: {state.check_count}")
print(f"판정 실패 수: {state.failure_count}")
print(f"위협 시계 현재 칸: {state.clock_segment}")
print(f"시계 진행 횟수: {state.clock_advances}")
print(f"서사 조각 수: {state.narration_count}")
print(f"AI 호출 수: {state.ai_calls}")
print(f"토큰 합계: {state.total_tokens}")
print(f"마지막 판정 등급: {state.last_grade}")
```
`build_report(state)` (see RESEARCH.md Code Examples, already sketched) should reuse this exact field set as a `dict`, adding the derived `failure_to_clock_ratio = failure_count / clock_advances if clock_advances else None` (MEAS-03). This function is the single shared implementation used by both the new CLI `report` subcommand (in `cli/main.py`, following `_cmd_replay`'s exact init-store/rebuild_state/print shape) and `SessionActor`'s auto-save hook — write it once in `web/report.py` (or a neutral shared module) and import from both `cli/main.py` and `session_actor/actor.py`, mirroring how `_build_turn_context` in `turn_flow.py` is re-exported for `cli/main.py`'s `test_turn_tracer.py` compatibility (`cli/main.py:49-52`, one-directional re-export, no circular import).

**Layering note**: `cli` and `web` must be co-equal per RESEARCH.md's `.importlinter` fix — if `report.py`'s logic is needed by both, it cannot live in `cli/` (web can't import cli) nor purely in `web/` (cli can't import web either, per the corrected layers). Put `build_report`/`write_report` in a module reachable by both — e.g. `session_actor/report.py` (session_actor already sits below both cli and web in the layer stack) or a new sibling layer. This is a genuine open design point for the planner, not resolved by an existing analog.

---

## Shared Patterns

### Async command submission via SessionActor
**Source:** `src/gptrpg/session_actor/actor.py:170-178` (`SessionActor.submit`), used throughout `cli/turn_flow.py`
**Apply to:** `routes_actions.py`, `routes_events.py` (for triggering any writes), auto-advance hook
```python
async def submit(self, command: Command) -> int:
    future: asyncio.Future[int] = asyncio.get_running_loop().create_future()
    await self._queue.put((command, future))
    return await future
```
All web routes that submit commands should `await actor.submit(SomeCommand(...))` exactly like `turn_flow.py` — never bypass the queue, never talk to `EventStore.append` directly from a route handler (violates D-09 single-writer invariant).

### CommandRejected / SequenceConflict error translation
**Source:** `src/gptrpg/cli/main.py:122-124` (`except (CommandRejected, SequenceConflict) as exc: print(...); return 1`)
**Apply to:** all POST routes in `routes_actions.py`, `routes_characters.py` selection endpoint
```python
except (CommandRejected, SequenceConflict) as exc:
    print(f"오류: {exc}", file=sys.stderr)
    return 1
```
Web equivalent: catch the same two exception types, raise `HTTPException(status_code=400, detail=str(exc))` (validation) or `409` (sequence conflict) respectively — same exception set as the CLI, translated to HTTP status instead of exit code.

### SessionRegistry for per-session actor reuse
**Source:** `src/gptrpg/session_actor/actor.py:381-403` (`SessionRegistry.get_or_create`)
**Apply to:** `web/app.py` startup, shared across all route modules via FastAPI dependency injection
```python
def get_or_create(self, session_id: str) -> SessionActor:
    actor = self._actors.get(session_id)
    if actor is None:
        actor = SessionActor(self._store, session_id, self._roller_factory())
        actor.start()
        self._actors[session_id] = actor
    return actor
```
One `SessionRegistry` instance should be constructed at app startup and injected into every route (e.g. via `app.state` or FastAPI `Depends`), never re-created per-request — this is what already gives D-09's single-writer guarantee across 4 concurrent browser POSTs, no new coordination code needed.

### GameEvent as wire format (no second schema)
**Source:** `src/gptrpg/event_log/schema.py` (pydantic discriminated union `GameEvent`), `event_log/store.py:93-103`
**Apply to:** `routes_events.py` response model
Reuse `GameEvent`/`parse_event` directly as FastAPI's `response_model` — do not hand-roll a parallel JSON shape for events (RESEARCH.md Don't-Hand-Roll table, first row).

### Test fixture style: pure GameState/fold construction
**Source:** `tests/test_reducer_failure_count.py:15-30` (`_v2_check_resolved`/`_v1_check_resolved` payload builders, then `apply_event`/`fold` directly, no store/actor needed)
**Apply to:** `tests/test_reducer_fails_since_clock.py`, `tests/test_report.py`
```python
def _v2_check_resolved(seq: int, grade: str, counts_as_failure: bool) -> dict:
    return {"seq": seq, "grade": grade, "schema_version": 2, "counts_as_failure": counts_as_failure}

state = apply_event(initial_state("s1"), "check_resolved", _v2_check_resolved(0, "failure", True))
assert state.failure_count == 1, "..."
```
Unit tests for pure reducer/report logic should build small payload dicts and call `apply_event`/`fold`/`build_report` directly — no `EventStore`, no `SessionActor`, no asyncio needed (fast, matches existing convention).

### Test fixture style: actor-level integration
**Source:** `tests/test_session_actor.py:1-40` (imports `SessionActor`, `SessionRegistry`, `_FixedRoller`, `EventStore` in-memory/temp-file, `pytest-asyncio` auto mode)
**Apply to:** `tests/test_session_actor_auto_advance.py`
Same fixture shape: a `_FixedRoller` test double (see full file for exact roll sequence stubbing), a temp `EventStore`, `SessionRegistry(store).get_or_create(session_id)`, then `await actor.submit(...)` sequences with `pytest.raises(CommandRejected)` where relevant. `asyncio_mode = "auto"` (`pyproject.toml`) means test functions can be plain `async def` with no extra decorator.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/src/main.ts` | client/poller | streaming (polling) | First frontend file in the repo — no existing TypeScript code anywhere in `GPTRPG` (verified: `src/gptrpg` is Python-only). Planner must build the poll-loop/cookie/DOM-render logic fresh per RESEARCH.md's Code Examples and Architecture sections (D-38/D-40/D-43 patterns), no in-repo precedent. |
| `frontend/index.html`, `frontend/package.json` | config | — | Same reason — new Vite `vanilla-ts` scaffold, use `npm create vite@latest frontend -- --template vanilla-ts` per RESEARCH.md Standard Stack rather than hand-authoring. |
| `tests/test_web_events.py`, `tests/test_web_characters.py` | test | request-response | No existing FastAPI `TestClient` usage anywhere in `tests/` — this is the first HTTP-layer test file. RESEARCH.md's Validation Architecture section is the reference (FastAPI `TestClient` is synchronous to call, no `pytest-asyncio` needed for these files even though endpoints are `async def`). |

## Metadata

**Analog search scope:** `src/gptrpg/` (all subpackages), `tests/`, `.importlinter`, `pyproject.toml`
**Files scanned:** `session_actor/actor.py`, `event_log/store.py`, `event_log/schema.py` (referenced), `rules_core/reducer.py`, `rules_core/entities.py`, `cli/main.py`, `cli/turn_flow.py`, `session_actor/projection.py`, `rulebooks/dungeonworld_like.py`, `tests/test_reducer_failure_count.py`, `tests/test_session_actor.py`, `.importlinter`, `pyproject.toml`
**Pattern extraction date:** 2026-08-03

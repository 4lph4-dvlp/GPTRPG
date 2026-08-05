---
phase: 04-experiment-tool
plan: 01
subsystem: api
tags: [fastapi, uvicorn, httpx, vite, typescript, polling, import-linter]

requires:
  - phase: 01-foundation
    provides: EventStore/GameEvent schema (event_log), append-only sqlite store with read_events(session_id, from_seq) inclusive-boundary semantics
  - phase: 02-session-actor
    provides: SessionActor/SessionRegistry (one actor per session, D-09①), rebuild_state fold-from-scratch projection
provides:
  - "gptrpg.web FastAPI package: create_app(db_path, static_dir), app.py uvicorn entrypoint, validate_session_id path-traversal guard"
  - "GET /api/sessions/{session_id}/events?from_seq=N polling endpoint returning GameEvent list + GameStateView"
  - "Vite vanilla-ts frontend scaffold with a 1.5s poll loop, disconnect banner, textContent-only rendering"
  - ".importlinter contract:2 top layer widened to `gptrpg.cli | gptrpg.web` (co-equal layers)"
affects: [04-02, 04-03, 04-04, 04-05, 04-06]

actuals:
  tokens: 9532
  tasks: 3
  commits: 4

tech-stack:
  added: [fastapi==0.141.1, uvicorn==0.52.1, httpx==0.28.1 (dev), vite ^8.2.0, typescript ~6.0.2]
  patterns:
    - "Router-level FastAPI dependency injection (`app.include_router(..., dependencies=[Depends(fn)])`) instead of a module-level import, to avoid a routes<->app circular import while keeping validation logic in app.py"
    - "web layer re-declares PLACEHOLDER_CLOCK_SEGMENT_COUNT locally (cannot import cli/turn_flow.py's copy — layer boundary forbids it)"
    - "textContent-only DOM rendering discipline for all AI/player-originated text (frontend/src/session_view.ts)"

key-files:
  created:
    - src/gptrpg/web/__init__.py
    - src/gptrpg/web/app.py
    - src/gptrpg/web/routes_events.py
    - frontend/index.html
    - frontend/src/main.ts
    - frontend/src/session_view.ts
    - frontend/src/style.css
    - tests/test_web_events.py
  modified:
    - pyproject.toml
    - .importlinter
    - tests/conftest.py

key-decisions:
  - "validate_session_id lives in app.py but is wired via router-level `dependencies=[Depends(...)]` at include_router time, not imported into routes_events.py — avoids a circular import between the two modules while keeping the check in the file the plan specified"
  - "src/gptrpg/web/__init__.py (originally a Task 3 action) was created empty during Task 2 instead, because import-linter's `layers` contract raises a hard ValueError when a declared layer module doesn't exist on disk yet — Task 2's own <verify> (which runs the full pytest suite, including tests/test_boundaries.py) cannot pass otherwise"
  - "Path-traversal test for session_id uses a non-dot-segment value (`..escape`, not a bare `..`) — httpx normalizes RFC 3986 dot-segments client-side before the request ever reaches the server, so a literal `..` in the URL 404s at the transport layer instead of reaching validate_session_id"

requirements-completed: [RIG-07]

coverage:
  - id: D1
    description: "GET /api/sessions/{id}/events?from_seq=N returns events with seq >= from_seq (boundary inclusive) plus the reducer-derived GameStateView"
    requirement: RIG-07
    verification:
      - kind: unit
        ref: "tests/test_web_events.py#test_from_seq_boundary_is_inclusive"
        status: pass
      - kind: unit
        ref: "tests/test_web_events.py#test_state_matches_rebuild_state"
        status: pass
    human_judgment: false
  - id: D2
    description: "from_seq=0 replays full session history (used for refresh/reconnect, D-41)"
    requirement: RIG-07
    verification:
      - kind: unit
        ref: "tests/test_web_events.py#test_from_seq_zero_returns_full_history"
        status: pass
    human_judgment: false
  - id: D3
    description: "Negative from_seq rejected with 422; malformed session_id (path-traversal-shaped) rejected with 400"
    verification:
      - kind: unit
        ref: "tests/test_web_events.py#test_negative_from_seq_rejected_with_422"
        status: pass
      - kind: unit
        ref: "tests/test_web_events.py#test_path_traversal_session_id_rejected_with_400"
        status: pass
    human_judgment: false
  - id: D4
    description: "Empty session returns 200 with empty event list + initial state (not 404)"
    verification:
      - kind: unit
        ref: "tests/test_web_events.py#test_empty_session_returns_200_with_empty_list_and_initial_state"
        status: pass
    human_judgment: false
  - id: D5
    description: "Browser polls every 1.5s, renders narration feed via textContent only, shows disconnect banner after 7 consecutive failures, auto-scrolls only when already near the bottom"
    requirement: RIG-07
    verification:
      - kind: e2e
        ref: "manual smoke: uvicorn gptrpg.web.app:app + curl round-trip against a seeded session (see Issues Encountered)"
        status: pass
    human_judgment: true
    rationale: "Live browser behavior (auto-scroll threshold, banner timing, multi-tab convergence) is flagged `verification: backstop` in the plan's must_haves and needs an eyes-on check in 04-06's live QA — a curl/tsc check proves the wiring but not the visual behavior"

duration: 25min
completed: 2026-08-03
status: complete
---

# Phase 4 Plan 1: Web Polling Tracer Summary

**First end-to-end vertical slice: FastAPI polling endpoint (`GET /api/sessions/{id}/events`) + Vite vanilla-ts frontend that polls every 1.5s, replays full history from `from_seq=0` on reconnect, and shows a disconnect banner after ~10s of failures — all rendering via `textContent` only.**

## Performance

- **Duration:** ~25 min (Task 2 + Task 3, after Task 1's human-verify checkpoint was approved)
- **Started:** 2026-08-03T09:59:00+09:00 (worktree recreation after infra loss, see Issues Encountered)
- **Completed:** 2026-08-03T10:10:42+09:00
- **Tasks:** 3 (1 checkpoint + 2 auto/tracer)
- **Files modified:** 15 (excluding `uv.lock`/`frontend/package-lock.json` lockfiles)

## Accomplishments
- `gptrpg.web` package installed and wired as a co-equal import-linter layer alongside `gptrpg.cli` — neither imports the other, both may call `agents` and below
- `GET /api/sessions/{session_id}/events?from_seq=N` polling endpoint: inclusive boundary, full-history replay at `from_seq=0`, 400 on malformed `session_id` (T-04-05 mitigation), 200+empty-state on a session with zero events
- Vite vanilla-ts frontend scaffold with a real poll loop (`frontend/src/main.ts`), pure-DOM rendering (`frontend/src/session_view.ts`, zero `innerHTML` anywhere), and UI-SPEC design tokens (`frontend/src/style.css`)
- 6 new backend tests (`tests/test_web_events.py`) covering all 6 `<behavior>` items from the plan; RED confirmed before implementation existed, GREEN after
- Live smoke-tested: `uv run uvicorn gptrpg.web.app:app` + `curl` round-trip against a real seeded session, confirmed 200 + correct empty-state JSON shape

## Task Commits

Each task was committed atomically:

1. **Task 1: 설치할 다섯 꾸러미의 정당성 확인** — checkpoint only, no commit (human approved 5 package source repos)
2. **Task 2: 의존성 설치 · 프런트엔드 스캐폴드 · 경계 계약 갱신** - `1f4d50e` (feat)
3. **Task 3: 트레이서 (RED)** - `20faa72` (test)
3. **Task 3: 트레이서 (GREEN)** - `cca0195` (feat)

_Task 3 carried `tdd="true"` — RED (failing test, confirmed via ModuleNotFoundError with implementation temporarily removed) and GREEN (implementation, all 6 tests + full 330-test suite pass) are separate commits per the TDD gate._

## Files Created/Modified
- `src/gptrpg/web/app.py` - `create_app()`, lifespan-scoped `EventStore`/`SessionRegistry`, `validate_session_id`, uvicorn entrypoint `app`
- `src/gptrpg/web/routes_events.py` - polling router, `GameStateView`/`PollResponse` models, `PLACEHOLDER_CLOCK_SEGMENT_COUNT`
- `src/gptrpg/web/__init__.py` - empty package marker
- `frontend/src/main.ts` - poll loop, `POLL_INTERVAL_MS`/`DISCONNECT_AFTER_FAILURES`, disconnect banner
- `frontend/src/session_view.ts` - `renderFeed`/`renderHeader`/`renderEmptyState`, textContent-only, bottom-threshold autoscroll
- `frontend/index.html` - bare `#app` div, scaffold demo markup stripped
- `frontend/src/style.css` - 04-UI-SPEC.md tokens only (font stack, color roles, spacing scale, 44px touch target)
- `tests/test_web_events.py` - 6 tests covering the plan's `<behavior>` list
- `tests/conftest.py` - `web_app`/`web_client` fixtures
- `.importlinter` - contract:2 top layer `gptrpg.cli | gptrpg.web`
- `pyproject.toml` - fastapi/uvicorn deps, httpx dev dep, `TID251` exemption for `src/gptrpg/web/*`

## Decisions Made
- **Circular-import avoidance:** `validate_session_id` lives in `app.py` (per plan) but is applied via `app.include_router(events_router, prefix="/api", dependencies=[Depends(validate_session_id)])` rather than `routes_events.py` importing it directly — a direct import would create an `app.py` ↔ `routes_events.py` cycle whose success depends on which module gets imported first (fragile). Router-level dependency injection resolves path parameters (`session_id`) per-request regardless of import order.
- **`src/gptrpg/web/__init__.py` created in Task 2, not Task 3:** import-linter's `layers` contract (`_check_all_containerless_layers_exist`) raises a hard `ValueError` — not a soft warning — when a declared layer module doesn't exist on disk. Task 2's own `<verify>` runs `uv run pytest -q`, which includes `tests/test_boundaries.py::test_import_contracts_are_kept`; that test would fail until the module exists. Creating the empty `__init__.py` slightly early (it's Task 3's literal first action anyway) makes Task 2 self-consistent without changing Task 3's scope.
- **Path-traversal test value:** used `..escape` (dots embedded in a longer segment) instead of a bare `..` or `..%2Fescape` — HTTP clients (httpx) resolve RFC 3986 dot-segments before sending, and ASGI routers reject encoded slashes (`%2F`) as not matching a single-segment path parameter, so both would 404 at the transport/routing layer before ever reaching `validate_session_id`. A non-dot-segment value that still fails the `^[A-Za-z0-9_-]{1,64}$` regex reaches the handler and correctly exercises the 400 path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree infrastructure vanished mid-execution and had to be recreated**
- **Found during:** Resuming after Task 1's checkpoint approval
- **Issue:** The assigned worktree (`agent-abfd890d53f72ad6b`) and its branch (`worktree-agent-abfd890d53f72ad6b`) no longer existed when execution resumed — `git worktree list` showed only the sibling plan's worktree. No commits had been made yet (Task 1 was checkpoint-only), so no work was lost, but continuing required a working, correctly-based worktree.
- **Fix:** Recreated the worktree at the same path with `git worktree add -b worktree-agent-abfd890d53f72ad6b <path> <expected-base-sha>`, verified the merge-base matched the orchestrator's expected base SHA and the branch matched the required `worktree-agent-*` naming pattern before any commit.
- **Files modified:** none (infrastructure only)
- **Committed in:** n/a (pre-work recovery step)

**2. [Rule 3 - Blocking] `src/gptrpg/web/__init__.py` created during Task 2 instead of Task 3**
- **Found during:** Task 2's `<verify>` (`uv run lint-imports && uv run pytest -q`)
- **Issue:** import-linter's `layers` contract fails hard (`ValueError: Missing layer 'gptrpg.web': module gptrpg.web does not exist`) when a declared layer has no corresponding module on disk — this broke both `lint-imports` and 3 pre-existing tests in `tests/test_boundaries.py` immediately after adding `gptrpg.cli | gptrpg.web` to `.importlinter`, before Task 3 had created the package.
- **Fix:** Created `src/gptrpg/web/__init__.py` as an empty file in Task 2 (this is literally Task 3's first specified action — pulled forward, not new scope).
- **Files modified:** `src/gptrpg/web/__init__.py`
- **Verification:** `uv run lint-imports` → 3 kept, 0 broken; `uv run pytest -q` → 324/324 passed at end of Task 2
- **Committed in:** `1f4d50e` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - blocking issues, both infrastructure/sequencing, no functional scope creep)
**Impact on plan:** No architectural changes. Both fixes were required to make each task's own `<verify>` block pass in the order the plan specified.

## Issues Encountered
- import-linter's `layers` contract contains a hidden ordering assumption (declared layer modules must exist on disk) not stated in the plan's Task 2 acceptance criteria — resolved via deviation #2 above. Future plans in this codebase adding a new import-linter layer before the corresponding package exists should create at least an empty `__init__.py` in the same task that edits `.importlinter`.
- httpx (TestClient's transport) normalizes RFC 3986 dot-segments (`..`) out of request paths before sending, and percent-encoded slashes (`%2F`) don't survive ASGI single-segment path routing either — neither reaches the FastAPI handler, so testing "malformed `session_id`" required a value that fails the regex without being interpretable as a directory-navigation instruction. Documented inline in the test docstring for future readers.
- No live browser (Playwright/manual click-through) verification was performed in this plan — the `<verify>` automated commands (pytest, lint-imports, tsc) plus a curl-based uvicorn smoke test cover the wiring; the plan's own `must_haves.truths` autoscroll item is explicitly `verification: backstop`, deferred to 04-06's live QA pass per the plan's own Flagged Assumptions section.

## User Setup Required
None - no external service configuration required. `fastapi`/`uvicorn`/`httpx` install via `uv`, `vite`/`typescript` via `npm`, both already verified present in the environment (04-RESEARCH.md's Environment Availability table).

## Next Phase Readiness
- The polling/replay/reconnect vertical slice (RIG-07's core mechanism) is proven end-to-end: backend endpoint, frontend poll loop, textContent-safe rendering, disconnect banner.
- 04-02 (session aggregation/report CLI) and later plans in this phase build on top of `validate_session_id` (already the sole path-traversal guard for the session_id-as-filename pattern they'll use) and `gptrpg.web`'s layer position — no changes needed to either.
- `PLACEHOLDER_CLOCK_SEGMENT_COUNT = 6` is duplicated between `cli/turn_flow.py` and `web/routes_events.py` by necessity (layer boundary) — flagged in the plan as a known cross-cutting concern to resolve once EXP-01/M1 scenario data exists.
- No character-select screen, action-input row, or confirm/reject card exist yet — those are explicitly out of scope for 04-01 per the plan (04-03/04-UI-SPEC.md Screen Inventory items 1 and 4).

---
*Phase: 04-experiment-tool*
*Completed: 2026-08-03*

## Self-Check: PASSED

All 9 created files found on disk; all 4 commit hashes (`1f4d50e`, `20faa72`, `cca0195`, `59183c3`) found in git history.

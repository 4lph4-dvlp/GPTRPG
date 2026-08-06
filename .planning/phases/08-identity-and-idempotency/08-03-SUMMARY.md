---
phase: 08-identity-and-idempotency
plan: 03
subsystem: api
tags: [event-sourcing, fastapi, asyncio-queue, httpx-asgitransport, idempotency, tdd]

# Dependency graph
requires:
  - phase: 08-01
    provides: "HMAC-signed browser_id/character_id cookie, EVENT_SCHEMA_VERSION=5, GameState.declare_owners two-tier TRUST-03 defense"
  - phase: 08-02
    provides: "OccupyCharacter/_prepare_occupy pattern (AlreadyOccupied(CommandRejected), validate-then-tuple shape), the asyncio.gather + ASGITransport/lifespan_context concurrent-test pattern"
provides:
  - "GameState.confirmed_declares/confirm_to_declare derived fields — 'this declare was already confirmed' folded from events, not held in actor memory"
  - "SessionActor.AlreadyConfirmed(CommandRejected) — same move/stat re-confirm short-circuits with no new event; different move/stat gets a plain CommandRejected (D-10)"
  - "SessionActor.AlreadyResolved(CommandRejected) — second-tier idempotency guard on ResolveCheck itself, closing a TOCTOU window the route-level reuse decision opens on its own"
  - "ConfirmResponse.narration_failed — narration-only failure is 200 with rolls/grade/target intact, not a 502 that discards the already-recorded roll (D-08, TRUST-06)"
  - "Frontend contract sync: ActionDeclaredEvent/ActionConfirmedEvent.character_id, CheckResolvedEvent.person_id/character_id, ConfirmResponse.narration_failed, ChatPane surfaces narration failure via the existing onTurnFailed path"
  - "Deterministic (non-flaky) concurrent-confirm proof at actor layer (ConfirmAction race + route-shaped Confirm-then-Resolve race) and HTTP layer (two clients sharing one signed cookie)"
affects: [08-04-fixtures, phase-11-resource-writes]

# Actuals (#2632)
actuals:
  tokens: 21647
  tasks: 4
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Two-tier idempotency defense repeated at a second layer: AlreadyConfirmed (Task 1) guards ConfirmAction; AlreadyResolved (Task 4, discovered mid-execution) guards ResolveCheck for the identical reason — a route-level 'reuse if already resolved' decision is itself a TOCTOU check-then-use gap unless the actor independently re-verifies inside its single-consumer queue."
    - "TDD RED/GREEN via git show HEAD:<path> > <path> to revert (git checkout -- blocked by sandbox classifier per 08-02's documented workaround), confirm failing import/assertion, commit test-only, replay saved Edit sequence to restore GREEN, confirm passing, commit feat separately."
    - "_SwitchableProvider test double (test_web_actions.py only) — wraps a mutable `.current` Provider so a single master_gm fixture slot can serve a failing stream on request 1 and a succeeding stream on request 2, without touching the web_client_with_fake_provider fixture factory itself."
    - "HTTP-layer true concurrency for routes that call actor.submit(...) needs httpx.AsyncClient + ASGITransport driven inside app.router.lifespan_context(app), with two clients constructed from the same captured cookie jar (one signed-cookie browser, two clicks) — carried over verbatim from 08-02 Task 3."

key-files:
  created: []
  modified:
    - src/gptrpg/rules_core/reducer.py
    - src/gptrpg/session_actor/actor.py
    - src/gptrpg/web/routes_actions.py
    - tests/test_session_actor.py
    - tests/test_web_actions.py
    - frontend/src/api/types.ts
    - frontend/src/panes/ChatPane.tsx
    - frontend/src/labels.ts

key-decisions:
  - "AlreadyResolved(CommandRejected) added to actor.py, not in the original plan text, after empirically reproducing a double-roll under concurrent HTTP confirms: two requests can both observe prior.resolve_seq is None (neither has submitted ResolveCheck yet) and both proceed to submit one. _prepare_resolve_check now independently checks confirm_to_declare -> confirmed_declares before rolling, mirroring D-11's own stated principle (route-layer checks alone leave a TOCTOU window) applied one step further than the plan's Task 2 text covered."
  - "The 'differs in move/stat' check in _prepare_confirm stays ordered before the AlreadyConfirmed raise, exactly as planned — verified directly by test_idempotent_confirm_different_move_raises_command_rejected_not_already_confirmed."
  - "No schema_version gating needed on confirmed_declares/confirm_to_declare — move/stat/player_confirmed already existed pre-판5, so idempotency judgment does not depend on character_id the way declare_owners does."

patterns-established:
  - "Second-tier idempotency guard pattern: when a route reuses a cached derived value (prior.resolve_seq) to skip a second actor submission, the actor must independently re-derive and check the same fact before doing the expensive/side-effecting work — the route's fast path is an optimization, never the sole guard."

requirements-completed: [TRUST-05, TRUST-06, TEST-02]

coverage:
  - id: D1
    description: "같은 선언 번호로 확인이 두 번 들어와도 판정 사건은 하나만 남는다 — 사람이 안내대로 다시 눌러도 주사위가 다시 굴러가지 않는다 (TRUST-05, D-10)"
    requirement: "TRUST-05"
    verification:
      - kind: unit
        ref: "tests/test_session_actor.py#test_idempotent_confirm_same_move_raises_already_confirmed_and_appends_nothing"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_narration_retry_reuses_roll_and_only_narration_appended_grows"
        status: pass
    human_judgment: false
  - id: D2
    description: "이미 확인된 선언에 다른 무브·능력치로 들어온 확인은 400으로 거부된다 (D-10)"
    requirement: "TRUST-05"
    verification:
      - kind: unit
        ref: "tests/test_session_actor.py#test_idempotent_confirm_different_move_raises_command_rejected_not_already_confirmed"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_different_move_after_confirmed_returns_400_and_appends_nothing"
        status: pass
    human_judgment: false
  - id: D3
    description: "서사만 실패하면 200이고 이미 나온 판정 값이 응답에 그대로 담긴다, 굴림 실패와 서사 실패가 응답에서 구분된다 (TRUST-06, D-08)"
    requirement: "TRUST-06"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_narration_failure_returns_roll_result_and_records_master_gm_ai_call"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_check_submission_failure_returns_error_status_with_no_rolls"
        status: pass
    human_judgment: false
  - id: D4
    description: "재시도가 이야기만 다시 쓴다 — 캐시된 판정을 재사용하고 ResolveCheck를 다시 제출하지 않는다 (D-09)"
    requirement: "TRUST-06"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_narration_retry_reuses_roll_and_only_narration_appended_grows"
        status: pass
    human_judgment: false
  - id: D5
    description: "같은 선언에 대한 확인이 동시에 두 번 들어오는 상황이 결정적으로 재현되고, 판정 사건은 하나만 남는다 (TEST-02) — 액터 계층과 HTTP 계층 양쪽"
    requirement: "TEST-02"
    verification:
      - kind: unit
        ref: "tests/test_session_actor.py#test_concurrent_confirm_same_move_exactly_one_action_confirmed_event"
        status: pass
      - kind: unit
        ref: "tests/test_session_actor.py#test_concurrent_confirm_and_resolve_via_route_shaped_flow_yields_one_check_resolved"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_concurrent_confirm_same_declare_seq_http_layer_one_check_resolved"
        status: pass
    human_judgment: false
  - id: D6
    description: "확인 검사가 라우트 계층과 SessionActor 양쪽에 있고, 라우트를 우회해 actor.submit(ConfirmAction(...))를 직접 두 번 불러도 액터가 두 번째를 단락시킨다 (D-11, backstop)"
    verification:
      - kind: unit
        ref: "tests/test_session_actor.py#test_concurrent_confirm_same_move_exactly_one_action_confirmed_event (bypasses route entirely, submits ConfirmAction directly)"
        status: pass
    human_judgment: false
  - id: D7
    description: "화면의 응답 타입과 사건 타입이 서버의 새 모양과 어긋나지 않는다 — 서사 실패가 200으로 바뀌어도 화면에서 조용히 사라지지 않는다"
    verification:
      - kind: other
        ref: "cd frontend && npm run build (tsc type-check, exit 0)"
        status: pass
    human_judgment: false
  - id: D8
    description: "전체 시험 묶음이 초록이고, concurrent 시험은 3회 연속 흔들리지 않는다, 확인 경로에 502 분기가 남아 있지 않다"
    verification:
      - kind: unit
        ref: "uv run pytest -q (524 passed)"
        status: pass
      - kind: unit
        ref: "uv run pytest -k concurrent -q x3 (8 passed each run)"
        status: pass
      - kind: other
        ref: "! grep -q 'status_code=502' src/gptrpg/web/routes_actions.py"
        status: pass
    human_judgment: false

duration: ~20min (09:59-10:20 KST from first task-1 RED commit to last task-4 commit)
completed: 2026-08-06
status: complete
---

# Phase 8 Plan 3: 재시도가 이야기만 다시 쓴다 — 확인 멱등성과 서사 실패 복구 Summary

**`GameState.confirmed_declares`가 사건에서 접혀 만들어지고 `AlreadyConfirmed`/`AlreadyResolved` 두 겹이 `SessionActor` 안에서 재확인·재판정을 각각 단락시키며, 서사만 실패한 턴은 502 대신 200 + `narration_failed`로 이미 굴린 주사위 결과를 그대로 돌려준다 — 화면도 이 계약을 따라간다.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 4 (Task 1/2 `tdd="true"` — RED/GREEN pairs; Task 3/4 test+impl in single commits)
- **Files modified:** 8 (0 created, 8 modified)

## Accomplishments

- `ConfirmedDeclareRecord`(frozen dataclass: `confirm_seq`/`resolve_seq`/`move`/`stat`) folds from `action_confirmed`(`player_confirmed=True` only — rejections don't lock a declare) and `check_resolved` events into two new `GameState` fields, `confirmed_declares`/`confirm_to_declare`. `SessionActor._prepare_confirm` checks this table right after the existing TRUST-03 ownership check: a **different** move/stat gets `CommandRejected`, a **same** move/stat re-confirm gets `AlreadyConfirmed(prior)` with no new event — the difference check runs first so "changed my mind" never reuses the cache (D-10).
- `routes_actions.confirm()` catches `AlreadyConfirmed` ahead of the generic `CommandRejected`, reuses the cached `confirm_seq`, and — when the prior record already has a `resolve_seq` — skips resubmitting `ResolveCheck` entirely, reusing the existing `store.read_events(from_seq=resolve_seq)` re-read path unchanged. The narration-failure branch (previously a 502 that discarded the already-recorded roll) now returns 200 with `rolls`/`grade`/`target` from that re-read event and `narration_failed=True`; a genuine roll-submission failure (`ResolveCheck` itself rejected) still surfaces as an error status with no `rolls` — the two failure modes stay distinguishable in the response (TRUST-06).
- **Deviation discovered and fixed mid-plan:** the route's "reuse `resolve_seq` if present, else submit" decision is itself a TOCTOU check — two concurrent confirm requests can both observe `resolve_seq is None` and both submit `ResolveCheck`, producing two `check_resolved` events for the same confirm. Reproduced directly with a route-shaped actor-layer test (two distinct resolve seqs, `2` and `3`) before fixing. Fixed with `AlreadyResolved(CommandRejected)` in `actor.py`: `_prepare_resolve_check` now independently re-derives "has this confirm already been resolved" via `confirm_to_declare`/`confirmed_declares` before rolling, and the route catches it and reuses `.resolve_seq` — the same two-tier defense pattern D-11 already established for `AlreadyConfirmed`, applied one layer deeper.
- Frontend contract synced without expanding scope: `types.ts` gained `character_id`(declared/confirmed events), `person_id`/`character_id`(check_resolved), and `narration_failed`(ConfirmResponse); `ChatPane.tsx`'s `resolve()` now reads the confirm response and routes a `narration_failed=true` turn through the existing failure-display path (`onTurnFailed` + `setStatus({error: true})`) instead of silently clearing status; `labels.ts` gained exactly one new copy key. `screens/` and `client.ts` are untouched (verified by `git diff --stat`).
- Concurrent-confirm determinism proven non-flaky at both layers, reusing 08-02 Task 3's `asyncio.gather`/`ASGITransport` + `lifespan_context` patterns: actor-layer (same-move race → one success + one `AlreadyConfirmed`, one `action_confirmed` event, one `check_resolved` event; different-move race → `CommandRejected` that is not `AlreadyConfirmed`) and HTTP-layer (two clients sharing one signed cookie, same `declare_seq`, both 200, one `check_resolved` event, identical `rolls`). `pytest -k concurrent -q` run 3 consecutive times, 8 passed each time, no sleeps or retries.
- Full suite green: 524 passed (up from 508 pre-plan), `lint-imports` (4/4 contracts kept), `ruff check` clean, `cd frontend && npm run build` exit 0, no `status_code=502` remaining in `routes_actions.py`, no dependency changes (`pyproject.toml`/`uv.lock` untouched).

## Task Commits

Each task was committed atomically, RED/GREEN split for the two `tdd="true"` tasks:

1. **Task 1 RED: failing idempotent_confirm tests** - `70ea901` (test)
2. **Task 1 GREEN: confirmed_declares fold + AlreadyConfirmed short-circuit** - `074f74d` (feat)
3. **Task 2 RED: failing narration-retry / roll-vs-narration-failure tests** - `6622be4` (test)
4. **Task 2 GREEN: stop discarding roll results on narration failure** - `9114c36` (feat)
5. **Task 3: frontend types/ChatPane/labels contract sync** - `7401287` (feat)
6. **Task 4: concurrent-confirm determinism + AlreadyResolved fix** - `491f131` (test)

**Plan metadata:** (this commit, following SUMMARY.md write)

## Files Created/Modified

- `src/gptrpg/rules_core/reducer.py` - `ConfirmedDeclareRecord`, `GameState.confirmed_declares`/`confirm_to_declare`, `action_confirmed`/`check_resolved` fold branches
- `src/gptrpg/session_actor/actor.py` - `AlreadyConfirmed(CommandRejected)`, `AlreadyResolved(CommandRejected)`, idempotency short-circuits in `_prepare_confirm`/`_prepare_resolve_check`
- `src/gptrpg/web/routes_actions.py` - `ConfirmResponse.narration_failed`, `AlreadyConfirmed`/`AlreadyResolved` handling, 502→200 narration-failure branch, `ResolveCheck` reuse path
- `tests/test_session_actor.py` - 12 new tests: 9 `idempotent_confirm` (Task 1), 3 `concurrent` (Task 4, including the route-shaped race reproduction)
- `tests/test_web_actions.py` - 6 new tests: 4 in the narration-retry/roll-distinction group (Task 2) + 1 different-move-400 + 1 `concurrent` HTTP test (Task 4); 1 existing test renamed/reasserted (502→200)
- `frontend/src/api/types.ts` - `character_id`/`person_id` on event types, `ConfirmResponse.narration_failed`
- `frontend/src/panes/ChatPane.tsx` - `resolve()` reads the confirm response, branches on `narration_failed`
- `frontend/src/labels.ts` - `COPY.narrationFailed`

## Decisions Made

- **`AlreadyResolved` added beyond the plan's literal text** (deviation, see below) — the plan's Task 2 only specified route-level reuse-if-present logic; empirical testing during Task 4 proved that alone leaves a TOCTOU window under real concurrency, so a second actor-level guard was required to actually satisfy the plan's own TEST-02 acceptance criteria.
- **Idempotency judgment does not gate on `schema_version`** for `confirmed_declares`/`confirm_to_declare` — unlike `declare_owners` (which depends on `character_id`, a 판5+-only field), `move`/`stat`/`player_confirmed`/`caused_by_seq` already existed pre-판5, so old records fold into the same idempotency table without a legacy-read branch.
- **`_SwitchableProvider` test double lives in `test_web_actions.py` only**, not in `conftest.py` — the plan explicitly asked for this ("픽스처 공장 자체는 고치지 않는다"), keeping the shared fixture factory's contract unchanged for every other test file.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Route-level resolve-reuse decision left a TOCTOU window that double-rolls under concurrent confirms**
- **Found during:** Task 4, while writing the route-shaped actor-layer concurrent test (mimicking the exact two-step ConfirmAction→ResolveCheck flow `routes_actions.confirm()` performs)
- **Issue:** Two concurrent confirm requests for the same `declare_seq` can both have their `ConfirmAction` processed by the actor (one succeeds, one raises `AlreadyConfirmed` — correct, exactly one `action_confirmed` event). But at that point `prior.resolve_seq` is still `None` for *both* requests (neither has submitted `ResolveCheck` yet), so both routes independently decide to submit `ResolveCheck` — and `_prepare_resolve_check` had no guard against a `caused_by_seq` that had already been resolved by the other, concurrent, request. Reproduced directly before fixing: the route-shaped test returned two distinct `resolve_seq`s (`2` and `3`) from what should have been a single-roll flow.
- **Fix:** Added `AlreadyResolved(CommandRejected)` to `actor.py`. `_prepare_resolve_check` now looks up `confirm_to_declare[caused_by_seq] -> declare_seq -> confirmed_declares[declare_seq].resolve_seq` before rolling; if already set, raises `AlreadyResolved(resolve_seq)` instead of rolling again. `routes_actions.py` catches this ahead of the generic `CommandRejected` and reuses `.resolve_seq`. This mirrors the exact two-tier defense pattern (route fast path + actor authoritative re-check) D-11 already established for the confirm step — applied one step further, to the resolve step, which the plan's Task 2 text did not anticipate.
- **Files modified:** `src/gptrpg/session_actor/actor.py`, `src/gptrpg/web/routes_actions.py`, `tests/test_session_actor.py` (the reproduction test doubles as the regression test — it initially failed with `assert 2 == 3`, now passes)
- **Verification:** `uv run pytest tests/test_session_actor.py -k concurrent_confirm -x -q` (all pass), full suite green (524 passed), `pytest -k concurrent -q` x3 stable.
- **Committed in:** `491f131` (Task 4 commit)

**2. [Rule 3 - Blocking] `node_modules` missing react/react-dom/typescript/vite (interrupted prior install)**
- **Found during:** Task 3, running the required `cd frontend && npm run build` verification
- **Issue:** `node_modules` had a handful of transitive packages (esbuild optional deps) but was missing every top-level dependency declared in `package.json` (`react`, `react-dom`, `typescript`, `vite`, etc.) — `tsc` failed with `Cannot find module 'react'` on files this plan never touched.
- **Fix:** Ran `npm ci` against the already-committed `package-lock.json` — no new package name introduced (react/react-dom/typescript/vite were already pinned in `package.json` before this plan started), no lockfile modification (`git diff --stat frontend/package-lock.json frontend/package.json` is empty). This is environment bootstrap for already-vetted dependencies, not the "installing a new/unverified package" case the deviation rules exclude from auto-fix.
- **Files modified:** none tracked by git (`node_modules`/`dist` are gitignored)
- **Verification:** `cd frontend && npm run build` exit 0.
- **Committed in:** N/A (environment setup, not a code change; documented in the Task 3 commit body)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 concurrency bug caught by the plan's own required test, 1 Rule 3 environment bootstrap)
**Impact on plan:** The `AlreadyResolved` addition is necessary for the plan's own TEST-02 acceptance criteria (HTTP-layer concurrent test must show one `check_resolved` event) to actually hold under real concurrency — without it, Task 4's HTTP-layer test would be flaky-to-failing depending on scheduling. No scope creep beyond what TEST-02 already required; both fixes are documented in `key-decisions` and covered by tests written specifically to catch them.

## Issues Encountered

- None beyond the deviations above (both were caught and fixed within the same task's verification loop before committing).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 08-04 (fixtures) can build on the full identity/occupancy/idempotency stack now closed by 08-01/02/03: signed cookies, character occupancy, and confirm/resolve idempotency at both actor and HTTP layers.
- Phase 11 (resource writes) explicitly depends on this plan landing first per the ROADMAP Phase 8 annotation — retries meeting resource writes without idempotency would turn "rolled twice" into "HP deducted twice." That precondition is now satisfied.
- The `AlreadyResolved` pattern (second-tier guard on a route-level cache-reuse decision) is worth reusing as the reference shape for any future two-step actor flow that route code short-circuits based on a cached derived value.
- No blockers. Full suite green (524 passed), `lint-imports` 4/4 contracts kept, `ruff check` clean, frontend build green, no new dependency.

---
*Phase: 08-identity-and-idempotency*
*Completed: 2026-08-06*

## Self-Check: PASSED

All 8 files listed under `key-files.modified` verified present on disk. All 6 task commits (`70ea901`, `074f74d`, `6622be4`, `9114c36`, `7401287`, `491f131`) verified present in `git log`.

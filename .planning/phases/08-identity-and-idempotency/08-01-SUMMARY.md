---
phase: 08-identity-and-idempotency
plan: 01
subsystem: auth
tags: [hmac, signed-cookies, fastapi, pydantic, event-sourcing, schema-versioning]

# Dependency graph
requires: []
provides:
  - "HMAC-signed `gptrpg_character` cookie (browser_id + character_id, D-01/D-03) replacing unsigned plaintext JSON"
  - "`gptrpg.web.cookie_auth` module: load_or_create_secret, sign_cookie, verify_cookie, new_browser_id, CookieIdentity, read_identity"
  - "EVENT_SCHEMA_VERSION 4->5: CharacterOccupied event, ActionDeclared/ActionConfirmed.character_id (optional), CheckResolved.person_id/character_id (required at schema_version>=5)"
  - "GameState.declare_owners / GameState.occupied_by derived fields + reducer legacy-read path for pre-판5 records"
  - "Route-layer identity cross-check (403, TRUST-02) and SessionActor-layer ownership defense (TRUST-03, survives restart)"
affects: [08-02-occupancy, 08-03-idempotency, 08-04-fixtures]

# Actuals (#2632)
actuals:
  tokens: 19350
  tasks: 4
  commits: 3

tech-stack:
  added: []
  patterns:
    - "HMAC-SHA256 signed cookie via stdlib hmac/hashlib/secrets (no new dependency)"
    - "Two-tier defense: route-layer fast-fail (403) + actor-layer authoritative check (D-11)"
    - "Version-gated schema evolution: EventEnvelope.schema_version + model_validator(mode='after') for conditionally-required fields"

key-files:
  created:
    - src/gptrpg/web/cookie_auth.py
    - tests/test_identity_tracer.py
  modified:
    - src/gptrpg/event_log/schema.py
    - src/gptrpg/rules_core/reducer.py
    - src/gptrpg/web/app.py
    - src/gptrpg/web/routes_characters.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/session_actor/actor.py
    - src/gptrpg/cli/main.py
    - src/gptrpg/cli/turn_flow.py
    - tests/conftest.py
    - tests/test_event_log.py
    - tests/test_web_actions.py
    - tests/test_web_characters.py
    - tests/test_session_actor.py
    - tests/test_measurement.py
    - tests/test_prompt_assembly_scenario.py
    - tests/test_report.py
    - tests/test_session_actor_auto_advance.py
    - tests/test_tracer_d100.py
    - tests/test_web_events.py
    - tests/test_imagery.py

key-decisions:
  - "Task 1 checkpoint (approved-scope) recorded: 판 5 changes four things in one commit — ActionDeclared.character_id, ActionConfirmed.character_id, CheckResolved.person_id/character_id (required from schema_version>=5), and new CharacterOccupied event"
  - "CookieIdentity/read_identity live in cookie_auth.py, not routes_characters.py as the plan literally described — avoids a circular import between routes_characters.py (imports MAX_ID_LEN from routes_actions.py) and routes_actions.py (needs identity lookup)"
  - "ResolveCheck.person_id/character_id are unconditionally required (non-empty) at the actor layer per the plan's explicit action text; CLI call sites (which have no browser-cookie identity concept) were given fixed stand-in identities (args.player reused for `turn`, a fixed 'cli' sentinel for the standalone `roll` subcommand) rather than weakening the actor-level guarantee"

patterns-established:
  - "New event schema fields follow the reducer.py:76-105 legacy-read precedent: optional field + schema_version-gated branch when the field never existed in old records, model_validator when the field is a hard requirement going forward"

requirements-completed: [TRUST-01, TRUST-02, TRUST-03, TRUST-04, QUAL-04, QUAL-05]

coverage:
  - id: D1
    description: "서명 쿠키가 발급·검증되고, 한 글자라도 변조되면 「고른 적 없음」이 된다 (TRUST-01)"
    requirement: "TRUST-01"
    verification:
      - kind: integration
        ref: "tests/test_identity_tracer.py#test_select_character_cookie_is_not_plain_json"
        status: pass
      - kind: integration
        ref: "tests/test_identity_tracer.py#test_tampered_cookie_char_returns_selected_false_not_an_exception"
        status: pass
    human_judgment: false
  - id: D2
    description: "요청의 캐릭터와 쿠키의 캐릭터가 다르면 선언·확인이 403이고 사건이 남지 않는다 (TRUST-02, D-04)"
    requirement: "TRUST-02"
    verification:
      - kind: integration
        ref: "tests/test_web_actions.py#test_declare_identity_mismatch_returns_403"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py#test_confirm_identity_mismatch_returns_403_and_no_confirm_event"
        status: pass
    human_judgment: false
  - id: D3
    description: "선언의 주인이 사건에 남아, 사건을 다시 접은 뒤에도 액터가 소유권을 판정한다 (TRUST-03, D-11)"
    requirement: "TRUST-03"
    verification:
      - kind: integration
        ref: "tests/test_identity_tracer.py#test_actor_level_ownership_check_rejects_bypassing_route"
        status: pass
      - kind: integration
        ref: "tests/test_identity_tracer.py#test_actor_level_ownership_check_survives_actor_restart"
        status: pass
    human_judgment: false
  - id: D4
    description: "check_resolved 사건에 「어느 브라우저가 · 어느 캐릭터로」가 필수로 남는다 (TRUST-04, D-12)"
    requirement: "TRUST-04"
    verification:
      - kind: integration
        ref: "tests/test_identity_tracer.py#test_check_resolved_records_person_id_and_character_id"
        status: pass
    human_judgment: false
  - id: D5
    description: "세션1의 895건이 판 5 코드에서 예외 없이 읽힌다 (D-13)"
    verification:
      - kind: integration
        ref: "tests/test_event_log.py#test_real_events_db_replay_smoke_test_folds_without_exception"
        status: pass
      - kind: unit
        ref: "tests/test_event_log.py#test_legacy_v2_payloads_fold_without_declare_owners_being_guessed"
        status: pass
    human_judgment: false
  - id: D6
    description: "select-character의 캐릭터 식별자에 길이 상한이 걸린다 (QUAL-04)"
    requirement: "QUAL-04"
    verification:
      - kind: integration
        ref: "tests/test_web_characters.py#test_select_character_id_over_max_length_returns_422_and_sets_no_cookie"
        status: pass
    human_judgment: false
  - id: D7
    description: "신원 관련 문구·로그에 자격 증명이 실려 나가지 않는다 (QUAL-05)"
    requirement: "QUAL-05"
    verification:
      - kind: integration
        ref: "tests/test_web_characters.py#test_identity_mismatch_response_has_no_secret_leak"
        status: pass
    human_judgment: false
  - id: D8
    description: "전체 시험 묶음이 초록이다"
    verification:
      - kind: unit
        ref: "uv run pytest -q (484 passed)"
        status: pass
    human_judgment: false

duration: unspecified (session interrupted by usage-limit reset mid-execution; resumed from committed working tree)
completed: 2026-08-06
status: complete
---

# Phase 8 Plan 1: 신원 검증 트레이서 Summary

**HMAC 서명 쿠키(D-01)가 캐릭터 선택부터 판정 기록까지 한 줄기로 돌고, 위조한 쿠키·남의 선언·서버 재시작 셋 다 그 줄기 위에서 막힌다 — 사건 형식은 판 4에서 판 5로 오르며 `CharacterOccupied` 신설과 소유권 칸이 함께 들어갔다.**

## Performance

- **Tasks:** 4 (Task 1 checkpoint pre-resolved by user before this executor was spawned; Task 2/3/4 executed and committed)
- **Files modified:** 20 (2 created, 18 modified — see `key-files`)
- **Commits:** 3 task commits + this metadata commit

## Accomplishments

- New `src/gptrpg/web/cookie_auth.py`: stdlib-only HMAC-SHA256 signed cookie (`hmac.compare_digest` for the comparison), `load_or_create_secret` (env var `GPTRPG_COOKIE_SECRET` takes priority over `.gptrpg/cookie_secret`, D-02), and the single canonical `read_identity(request, session_id)` used by both route modules.
- `EVENT_SCHEMA_VERSION` 4→5 in the same commit as the reducer's `character_occupied` branch (the exact failure mode the ROADMAP Phase 12 comment warned about — schema bump without matching reducer branch permanently locks a session).
- `routes_actions.declare()`/`confirm()` now cross-check the cookie's `character_id` against the request body *before* any `actor.submit(...)` call (TRUST-02, D-04 — no event recorded on mismatch), and `SessionActor._prepare_confirm` independently checks `declare_owners[caused_by_seq]` against the confirming character (TRUST-03) — verified to survive a full actor restart (fresh `SessionRegistry` over the same `EventStore`).
- `.gptrpg/events.db`'s real 895 판 2 records (session1) fold through the 판 5 reducer with zero exceptions and an empty `declare_owners` (ownership is never guessed from `player_id`, D-13) — verified against a copy, original file's mtime unaffected.
- Full test suite (484 tests) green; `lint-imports` (4/4 contracts kept) and `ruff check` clean.

## Task Commits

Each task was committed atomically:

1. **Task 1: checkpoint decision (approved-scope)** — resolved pre-execution by the user directly with the orchestrator; recorded here, no commit of its own.
2. **Task 2: [tracer] signed-cookie identity slice** - `973d415` (feat)
3. **Task 3: legacy-read path for 판 2 records** - `592c127` (test)
4. **Task 4: move whole suite onto identity rules + QUAL-04/05 gates** - `420b3fd` (test)

**Plan metadata:** (this commit, following SUMMARY.md write)

## Files Created/Modified

- `src/gptrpg/web/cookie_auth.py` - HMAC sign/verify, secret loading, `CookieIdentity`/`read_identity`
- `src/gptrpg/event_log/schema.py` - `EVENT_SCHEMA_VERSION=5`, `CharacterOccupied`, three field additions
- `src/gptrpg/rules_core/reducer.py` - `declare_owners`/`occupied_by` derived state, two new `apply_event` branches
- `src/gptrpg/web/app.py` - loads `app.state.cookie_secret` inside `lifespan` (not at import time)
- `src/gptrpg/web/routes_characters.py` - signed-cookie select/read, `browser_id` reuse on reselect, `MAX_ID_LEN` cap
- `src/gptrpg/web/routes_actions.py` - identity cross-check at the top of `declare()`/`confirm()`, identity wired into commands
- `src/gptrpg/session_actor/actor.py` - `character_id`/`person_id` command fields, `_prepare_confirm` ownership check, `_prepare_resolve_check` identity requirement, `CharacterOccupied` registered in `_EVENT_CLASSES`
- `src/gptrpg/cli/main.py`, `src/gptrpg/cli/turn_flow.py` - CLI-side identity stand-ins for `ResolveCheck` (deviation, see below)
- `tests/test_identity_tracer.py` - 12 tests covering the full behavior list (TRUST-01~04, D-02)
- `tests/test_event_log.py` - legacy-fold unit test + real-DB replay smoke test
- Ten further test files updated to keep the full suite green (see Deviations)

## Decisions Made

- **Task 1 checkpoint recorded as resolved (`approved-scope`):** the 판 4→5 bump touches four things in one commit — ① `ActionDeclared.character_id: str | None = None` ② `ActionConfirmed.character_id: str | None = None` ③ `CheckResolved.person_id`/`character_id` required from schema_version ≥ 5 via `@model_validator(mode="after")` ④ new `CharacterOccupied` event. Rationale (from the plan's own `<pros>`): all four in one commit is the only way TRUST-03 survives a server restart, and D-06/D-12/D-13 are satisfied simultaneously. Reversibility: one-way (writing 판 5 records makes rolling back to 판 4 code impossible — new event type blocks it).
- **`CookieIdentity`/`read_identity` placed in `cookie_auth.py`, not `routes_characters.py`:** the plan's own text asked for both (a) `routes_actions.py` importing `CookieIdentity`/`read_identity` from `routes_characters.py`, and (b) `routes_characters.py` importing `MAX_ID_LEN` from `routes_actions.py` — together these form a genuine circular import. Resolved by placing the shared identity type/lookup in `cookie_auth.py` (a module neither route file imports from the other direction), preserving "one verification path" while breaking the cycle.
- **CLI identity stand-ins:** `ResolveCheck.person_id`/`character_id` are unconditionally required (non-empty) at the actor layer, exactly as the plan's action text specifies. Since the CLI has no browser-cookie concept, `cli/turn_flow.py`'s `ResolveCheck` submission reuses `args.player` for both fields (mirrors the pre-split D-42 assumption, which remains valid for this non-web path), and `cli/main.py`'s standalone `submit roll` subcommand (which has no `--player` flag at all) uses a fixed `"cli"` sentinel.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Circular import between `routes_characters.py` and `routes_actions.py`**
- **Found during:** Task 2 (writing `routes_characters.py`)
- **Issue:** The plan's action text for Task 2 (⑥) placed `CookieIdentity`/`read_identity` in `routes_characters.py` for `routes_actions.py` to import, while Task 4 (③) had `routes_characters.py` import `MAX_ID_LEN` from `routes_actions.py` — a genuine two-way circular import once both changes land.
- **Fix:** Moved `CookieIdentity`/`read_identity`/`COOKIE_NAME` into `cookie_auth.py`; both route modules import from there, neither imports the other.
- **Files modified:** `src/gptrpg/web/cookie_auth.py`, `src/gptrpg/web/routes_characters.py`, `src/gptrpg/web/routes_actions.py`
- **Verification:** `uv run lint-imports` (4/4 contracts kept), app imports and runs under `TestClient` normally.
- **Committed in:** `973d415` (Task 2 commit)

**2. [Rule 3 - Blocking] `ResolveCheck.person_id`/`character_id` requirement broke every non-web caller**
- **Found during:** Task 2 verification (running the broader suite before committing)
- **Issue:** Making `person_id`/`character_id` unconditionally required on `ResolveCheck` (per the plan's explicit action text) silently broke the CLI (`cli/main.py`'s `submit roll`, `cli/turn_flow.py`'s `run_turn`) and every test that constructs `ResolveCheck`/`CheckResolved` directly without going through the new web identity flow.
- **Fix:** Added CLI-side identity stand-ins (see Decisions above) and filled `person_id`/`character_id` at every direct `ResolveCheck`/`CheckResolved` construction site across the test suite.
- **Files modified:** `src/gptrpg/cli/main.py`, `src/gptrpg/cli/turn_flow.py`, `tests/test_session_actor.py`, `tests/test_measurement.py`, `tests/test_prompt_assembly_scenario.py`, `tests/test_report.py`, `tests/test_session_actor_auto_advance.py`, `tests/test_tracer_d100.py`, `tests/test_web_events.py`
- **Verification:** `uv run pytest -q` (484 passed).
- **Committed in:** `973d415` (CLI + test_session_actor.py, part of Task 2), `420b3fd` (remaining test files, part of Task 4)

**3. [Rule 3 - Blocking] Declare/confirm now require a cookie, breaking pre-existing HTTP-layer tests**
- **Found during:** Task 4 (explicitly anticipated by the plan itself — "Task 2가 declare/confirm에 쿠키를 요구하게 만들었으므로, 쿠키 없이 도는 기존 시험들이 전부 403을 맞는다")
- **Issue:** `test_web_actions.py`'s declare/confirm helpers, and `test_imagery.py`'s HTTP-level turn helpers, called `declare`/`confirm` without first selecting a character.
- **Fix:** Added a shared `select_character(client, session_id, character_id)` helper to `conftest.py` (real route, no hand-rolled signer) and wired it into `test_web_actions.py`'s `_declare`/`_declare_first` and `test_imagery.py`'s `_run_one_turn`/`test_rejected_confirm_makes_no_illustration`. Two tests whose meaning changed from "unknown character" to "identity mismatch" were renamed and their expected status changed from 400 to 403, per the plan's own guidance.
- **Files modified:** `tests/conftest.py`, `tests/test_web_actions.py`, `tests/test_imagery.py`
- **Verification:** `uv run pytest -q` (484 passed), `-k identity_mismatch` selects both renamed tests.
- **Committed in:** `420b3fd` (Task 4)

**4. [Rule 1 - Bug] `test_actor_level_ownership_check_*` deadlocked when mixing `TestClient` (sync) with `await actor.submit(...)`**
- **Found during:** Task 2, first test run
- **Issue:** `TestClient` runs the ASGI app on a separate thread/portal event loop; awaiting `actor.submit(...)` directly (bound to the pytest-asyncio loop) on an actor whose background task and `asyncio.Queue` were created on the *other* loop hangs indefinitely — confirmed by a 47-minute stuck process, killed manually.
- **Fix:** Rewrote the two affected tests to use `httpx.AsyncClient` + `ASGITransport` and manually drive `app.router.lifespan_context(app)`, keeping HTTP calls and the direct `actor.submit(...)` bypass call on the same event loop (the pattern RESEARCH.md itself documents for TEST-02).
- **Files modified:** `tests/test_identity_tracer.py`
- **Verification:** `uv run pytest tests/test_identity_tracer.py -x -q` completes in well under a second (was hung indefinitely before the fix).
- **Committed in:** `973d415` (Task 2)

---

**Total deviations:** 4 auto-fixed (1 circular-import bug, 2 blocking-ripple fixes from the plan's own explicit design choices, 1 test-infrastructure deadlock bug)
**Impact on plan:** All four were necessary consequences of implementing the plan's Task 2 action text exactly as written (required `person_id`/`character_id`, cookie-gated declare/confirm) or of an internal contradiction in the plan's own two task descriptions. No scope creep beyond what was needed to keep the full test suite green — the CLI identity stand-ins and moved `cookie_auth.py` names are the minimum change that preserves both the plan's security intent (TRUST-02/03/04) and existing CLI behavior.

## Issues Encountered

- Session was interrupted by a usage-limit reset partway through Task 2's initial test run (the `test_identity_tracer.py` deadlock above, background process still running). Resumed from the uncommitted working tree exactly as left — no work was lost or redone. Diagnosed and fixed the deadlock (Deviation 4), then continued through Tasks 2-4 without further interruption.
- No other blocking issues.

## User Setup Required

None - no external service configuration required. `.gptrpg/cookie_secret` is created automatically on first server start (or overridden via `GPTRPG_COOKIE_SECRET`); no manual step needed.

## Next Phase Readiness

- 08-02 (occupancy) can build directly on `GameState.occupied_by`, the `CharacterOccupied` event class, and `_EVENT_CLASSES["character_occupied"]` — all already wired, only the `OccupyCharacter` command and `_prepare_occupy` remain.
- 08-03 (idempotency) can build on `GameState.declare_owners` and the two-tier TRUST-02/03 defense already in place; `AlreadyConfirmed`/`confirmed_declares` are the next layer per RESEARCH.md Pattern 2.
- No blockers. Full suite green, `.gptrpg/events.db`'s real session1 data proven readable under the new schema.

---
*Phase: 08-identity-and-idempotency*
*Completed: 2026-08-06*

## Self-Check: PASSED

All 22 files listed under `key-files` (created + modified) verified present on disk. All 3 task commits (`973d415`, `592c127`, `420b3fd`) verified present in `git log`.

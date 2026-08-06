---
phase: 08-identity-and-idempotency
plan: 04
subsystem: testing
tags: [pytest, fixtures, fastapi, pydantic, identity, secret-hygiene, tdd]

# Dependency graph
requires:
  - phase: 08-01
    provides: "HMAC-signed browser_id/character_id cookie, EVENT_SCHEMA_VERSION=5, TRUST-02 identity-mismatch 403 on declare/confirm, MAX_ID_LEN/MAX_RAW_TEXT_LEN input caps, _CHARACTER_NAMES + character_names param wiring in build_turn_context"
  - phase: 08-02
    provides: "OccupyCharacter/_prepare_occupy, AlreadyOccupied, two-sequential-TestClient pattern for two-browser HTTP tests sharing one app/db_path"
  - phase: 08-03
    provides: "AlreadyConfirmed/AlreadyResolved idempotency guards, ConfirmResponse.narration_failed"
provides:
  - "tests/conftest.py fake_session_log now runs on real characters (bram/nari) instead of the p1/p2 constant that structurally hid the identity bug class session1 hit"
  - "tests/conftest.py four_player_session fixture — all four PLAYER_CHARACTERS (bram/nari/seon/hodu) declare/confirm/resolve once, round-tripped through EventStore"
  - "tests/test_web_actions.py::test_multi_character_names_two_characters_get_distinct_labels / _four_characters_all_appear — regression lock proving two different characters' declared lines carry two DIFFERENT display-name labels in the AI prompt, not just 'a name is present'"
  - "Full web-layer input-cap sweep table (routes_actions.py commit body) plus the four caps it found missing: ConfirmRequest.target (range), DeclareRequest/ConfirmRequest.rulebook_id (length), ConfirmRequest.modifiers (list length + item length)"
  - "tests/test_web_actions.py::test_action_routes_no_secret_leak_across_403_409_400 — action-route-side QUAL-05 gate (403/409/400 response bodies + capsys logs never carry cookie value/secret hex/signature fragment/browser_id), paired with test_web_characters.py's existing no_secret_leak tests"
affects: [phase-9-safety-and-jailbreak, phase-10-resource-writes, phase-11-memory, phase-12-clock, phase-13-final-integration-tests]

# Actuals (#2632)
actuals:
  tokens: 11129
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Non-tautological TDD verification via targeted production-code mutation: for both the multi_character_names test and the no_secret_leak test, temporarily reintroduced the exact historical bug (character_names=None; CommandRejected message embedding the holder browser_id), confirmed the new test fails with the expected symptom, then `git checkout --` to restore and re-confirmed green. Neither test asserts a tautology."
    - "Fixture identity-meaningfulness rule applied literally per plan's scope_decisions: p1/p2 -> bram/nari only where the value structurally represents identity (conftest.py's fake_session_log, test_web_actions.py request bodies, test_session_actor.py's whole file per its acceptance criteria) — test_reducer_*/test_grading*/test_resolution* and test_report.py/test_measurement.py's standalone manually-built events were left untouched since their 'p1' is an opaque token, not identity."
    - "Two independently-created FastAPI apps (via web_client_with_fake_provider's _make() factory, called twice) sharing one tmp_db_path reproduce a server-restart-shaped 'second browser' for occupancy-conflict (409) and multi-character-prompt tests — same EventStore file, same cookie_secret file, fresh SessionActor rebuilt from the persisted event log each time."

key-files:
  created: []
  modified:
    - tests/conftest.py
    - tests/test_reverse_verification.py
    - tests/test_session_actor.py
    - tests/test_web_actions.py
    - src/gptrpg/web/routes_actions.py

key-decisions:
  - "player_id defaults in test_web_actions.py's _declare_body/_confirm_body changed from 'p1' to 'bram' (matching character_id='bram') rather than left independent — production already treats player_id === character_id as an invariant (D-42, frontend/src/screens/SessionScreen.tsx:113), and context.py's speaker-label lookup keys off event.player_id, so this alignment is what actually makes each character's own name attach to their own line. No production code was changed to make this robust against a mismatched player_id — that would contradict D-42's documented convention for this milestone (08-CONTEXT.md D-03: 'still one person = one character', player_id===character_id stays true until M1's real account system)."
  - "ConfirmRequest.target range set to ge=-200, le=200 (not tighter/looser) — covers OpenQuest's d100 skill domain (0-100) stacked with a few difficulty shifts (OPENQUEST_DIFFICULTY: ±50 each) as well as 2d6's low-teens targets, while remaining a meaningfully small bound rather than an effectively-unlimited one (the plan's own prohibition against 'capping large enough to be no cap')."
  - "MAX_MODIFIERS_COUNT=20 / MAX_MODIFIER_LEN=128 introduced as new named constants next to MAX_RAW_TEXT_LEN/MAX_ID_LEN, each with an inline rationale comment, per the plan's requirement that new caps carry their own justification rather than being unexplained magic numbers."
  - "rulebook_id caps on both DeclareRequest and ConfirmRequest reuse MAX_ID_LEN rather than introducing a rulebook-specific constant — it is the same shape of value (an identifier string) as move/stat/character_id."

patterns-established:
  - "Web-layer input-cap sweep as a commit-body artifact: enumerate every request model field/query param/path segment with its before/after cap state in a markdown table inside the commit message, so a future audit doesn't have to re-derive 'was this actually checked exhaustively.'"

requirements-completed: [TEST-01, TEST-02, QUAL-04, QUAL-05]

coverage:
  - id: D1
    description: "신원이 뜻을 갖는 시험 픽스처가 가짜 상수 'p1'이 아니라 실제 캐릭터 넷(bram/nari/seon/hodu)으로 돈다 — 세션1의 버그 클래스가 구조적으로 안 보이던 상태가 사라졌다"
    requirement: "TEST-01"
    verification:
      - kind: unit
        ref: "tests/conftest.py fixture round-trip verified via tests/test_reverse_verification.py::test_fixture_round_trips_a_complete_session_through_the_store"
        status: pass
      - kind: unit
        ref: "tests/test_web_actions.py -k multi_character_names"
        status: pass
    human_judgment: false
  - id: D2
    description: "여러 캐릭터가 번갈아 선언한 세션에서, AI에게 넘어가는 최근 대화에 각자의 발화에 각자의(서로 다른) 이름이 붙는다 — '이름이 있으면 통과'가 아니라 두 발화의 이름표가 서로 다름을 대조한다"
    requirement: "TEST-01"
    verification:
      - kind: unit
        ref: "tests/test_web_actions.py::test_multi_character_names_two_characters_get_distinct_labels"
        status: pass
      - kind: unit
        ref: "tests/test_web_actions.py::test_multi_character_names_four_characters_all_appear"
        status: pass
    human_judgment: false
  - id: D3
    description: "겹치는 요청을 재현하는 시험(TEST-02)이 실제 캐릭터 여러 명으로 계속 돈다 — 픽스처 교체가 기존 동시성 시험을 무력화하지 않았다"
    requirement: "TEST-02"
    verification:
      - kind: unit
        ref: "tests/test_session_actor.py tests/test_web_characters.py -k concurrent"
        status: pass
    human_judgment: false
  - id: D4
    description: "확인 요청의 자유 입력 칸(target·rulebook_id·modifiers 목록과 항목)에 전부 상한이 걸린다 — 전수 훑기로 찾은 빈자리 넷"
    requirement: "QUAL-04"
    verification:
      - kind: unit
        ref: "tests/test_web_actions.py -k max_length"
        status: pass
      - kind: unit
        ref: "tests/test_web_actions.py::test_confirm_target_below_min_returns_422, test_confirm_target_above_max_returns_422, test_confirm_modifiers_list_over_max_count_returns_422"
        status: pass
    human_judgment: false
  - id: D5
    description: "신원·점유·멱등성 경로의 예외 문구·서버 로그에 쿠키 값·비밀 열쇠·서명·browser_id·API 키가 실리지 않는다는 것이 자동 시험으로 잠긴다"
    requirement: "QUAL-05"
    verification:
      - kind: unit
        ref: "tests/test_web_actions.py::test_action_routes_no_secret_leak_across_403_409_400"
        status: pass
      - kind: unit
        ref: "tests/test_web_characters.py::test_identity_mismatch_response_has_no_secret_leak, test_occupancy_409_response_has_no_holder_identity_leak"
        status: pass
    human_judgment: false
  - id: D6
    description: "단계 종료 관문 — 전체 스위트 초록, lint-imports/ruff 통과, .gptrpg/events.db 세션1 기록 895건이 판 5 코드에서도 예외 없이 읽힌다"
    verification:
      - kind: unit
        ref: "uv run pytest -q (534 passed); uv run lint-imports; uv run ruff check src/gptrpg; tests/test_event_log.py::test_real_events_db_replay_smoke_test_folds_without_exception"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-08-06
status: complete
---

# Phase 8 Plan 4: Real-Character Fixtures, Distinct Name Attribution, Input Caps and Secret Hygiene Summary

**Replaced the structurally-blind "p1" test fixture with real characters, added a test that catches the exact 2026-08-04 name-mislabeling incident, closed the last four unbounded web-layer inputs, and locked an automated secret-hygiene gate — the last plan of Phase 8.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-08-06T01:30:44Z (first task commit)
- **Completed:** 2026-08-06T01:43:11Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- `tests/conftest.py`'s `fake_session_log` now runs on `bram`/`nari` instead of `"p1"`/`"p2"` — the exact constant that made session1's identity bug class invisible to CI is gone from every identity-meaningful test location (`tests/conftest.py`, `tests/test_web_actions.py`, `tests/test_session_actor.py` all show 0 occurrences of `"p1"`).
- New `four_player_session` fixture: all four `PLAYER_CHARACTERS` (bram/nari/seon/hodu) declare/confirm/resolve once, round-tripped through a real `EventStore`.
- `test_multi_character_names_two_characters_get_distinct_labels` and `_four_characters_all_appear` prove — via a real HTTP round trip and a real `FakeProvider` capturing the actual assembled prompt — that two different characters' lines carry two *different* display-name labels, not merely "some name is present." Verified non-tautological by temporarily reintroducing the exact regression (`character_names=None`) and confirming the new tests fail with the historical `"플레이어: "` mislabeling before reverting.
- Full input-cap sweep of `routes_actions.py`'s request models found and closed four gaps: `ConfirmRequest.target` (no range -> `ge=-200, le=200`), `DeclareRequest.rulebook_id` and `ConfirmRequest.rulebook_id` (no length cap -> reuse `MAX_ID_LEN`), `ConfirmRequest.modifiers` (no list-length or item-length cap -> new `MAX_MODIFIERS_COUNT=20` / `MAX_MODIFIER_LEN=128` constants, each with an inline rationale comment).
- `test_action_routes_no_secret_leak_across_403_409_400` closes the action-route half of QUAL-05: none of cookie value / secret hex / signature fragment / holder `browser_id` appear in the 403 (identity mismatch), 409 (occupancy conflict), or 400 (idempotent rejection) response bodies or `capsys`-captured server logs. Verified non-tautological by temporarily leaking the actual holder's `browser_id` into `actor.py`'s occupancy-rejection message and confirming the test catches it, then reverting.
- Phase-exit gate re-run and green: full suite (534 passed), `lint-imports` (4 contracts kept), `ruff check` (clean), and the session1 `.gptrpg/events.db` 895-record replay smoke test still folds without exception on schema-5 code.

## Task Commits

Each task was committed atomically:

1. **Task 1: Real-character shared fixtures** - `9b8a560` (test)
2. **Task 2: Multi-character distinct-label regression test (TEST-01)** - `ed43950` (test)
3. **Task 3: Input-cap sweep + secret-hygiene gate + phase-exit gate (QUAL-04/QUAL-05)** - `578d79f` (feat)

**Plan metadata:** (this commit) — `docs(08-04): complete plan`

_TDD note: Task 2 and Task 3's `no_secret_leak` piece each involved a real RED check via temporary production-code mutation (not a separate `test(...)` -> `feat(...)` commit pair, since no production behavior needed to change for Task 2, and Task 3's cap additions and their tests were authored together). Both are documented above and in the individual task commit bodies._

## Files Created/Modified

- `tests/conftest.py` - `fake_session_log` now uses bram/nari; new `four_player_session` fixture
- `tests/test_reverse_verification.py` - fixture round-trip assertion checks bram/nari alternation
- `tests/test_session_actor.py` - all `"p1"` occurrences replaced with `"bram"` (acceptance criteria: 0 file-wide)
- `tests/test_web_actions.py` - `_declare_body`/`_confirm_body` defaults now use `player_id="bram"`; new `multi_character_names`, `max_length`, and `no_secret_leak` tests
- `src/gptrpg/web/routes_actions.py` - four new/reused input caps (`MIN_TARGET`/`MAX_TARGET`, `MAX_MODIFIERS_COUNT`, `MAX_MODIFIER_LEN`, `rulebook_id` reusing `MAX_ID_LEN`)

## Decisions Made

- `player_id` test defaults changed to match `character_id` (both `"bram"`) rather than kept independently arbitrary — matches production's `player_id === character_id` convention (D-42) and is what actually makes `context.py`'s speaker-label lookup (keyed by `event.player_id`) attach the correct display name. No production code was changed to make this robust against a *mismatched* `player_id`/`character_id` pair — that would go beyond this plan's scope and against 08-CONTEXT.md's D-03 note that this milestone still treats one person as one character.
- `ConfirmRequest.target` bounded to `[-200, 200]` — covers both resolution methods' realistic domains (d100 skill 0-100 + stacked OpenQuest difficulty shifts of ±50; 2d6's low-teens targets) without being an effectively-unlimited cap.
- `MAX_MODIFIERS_COUNT=20` / `MAX_MODIFIER_LEN=128` introduced as new named constants (not reused from existing ones) since a "type:value:source" modifier string is a different shape of value than a bare identifier.

## Deviations from Plan

None - plan executed exactly as written. All three tasks matched their described scope; the only judgment calls made (target range, modifier caps, `player_id` alignment) were explicitly left to executor discretion by the plan's own action text ("새 숫자를 만들 때는 왜 그 값인지 옆에 적는다") and are documented above with rationale.

## Issues Encountered

None. Both TDD-flavored tasks (Task 2's multi-character test, Task 3's no-secret-leak test) initially passed without any production code change, since the underlying mechanisms (`_CHARACTER_NAMES` + `character_names` param wiring from a prior phase; `CommandRejected` messages that already omit values) were already correct. Per the fail-fast RED-phase rule, each was independently verified non-tautological by temporarily reintroducing the exact historical bug via `git`-tracked mutation, confirming the new test fails with the expected symptom, then `git checkout --` to restore — see commit bodies for the exact mutations used.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 8 (identity-and-idempotency) is now fully complete: all four plans (08-01 through 08-04) executed, all four of this plan's requirements (TEST-01, TEST-02, QUAL-04, QUAL-05) closed, and the phase-exit gate (full suite + `.gptrpg/events.db` 895-record replay under schema-5 code) is green.
- The test suite's identity fixtures (`fake_session_log`, `four_player_session`) now genuinely exercise multi-character identity, giving the next nine phases (starting with Phase 9, safety/jailbreak) a non-blind foundation to build regression coverage on.
- No blockers. Next roadmap step per STATE.md is Phase 9.

---
*Phase: 08-identity-and-idempotency*
*Completed: 2026-08-06*

## Self-Check: PASSED

- FOUND: `tests/conftest.py`
- FOUND: `.planning/phases/08-identity-and-idempotency/08-04-SUMMARY.md`
- FOUND commit: `9b8a560` (Task 1)
- FOUND commit: `ed43950` (Task 2)
- FOUND commit: `578d79f` (Task 3)

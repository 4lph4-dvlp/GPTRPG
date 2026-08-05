---
phase: 04-experiment-tool
verified: 2026-08-03T08:14:30Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 4: 실험 도구 (experiment-tool) Verification Report

**Phase Goal:** 네 명이 링크 하나로 3~4시간 같은 세션을 보며 플레이할 수 있고, 여섯 가설에 답할 숫자가 그동안 저절로 쌓인다
**Verified:** 2026-08-03T08:14:30Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 링크 하나를 받은 네 명이 같은 세션 화면을 동시에 보고, 한 명이 행동하면 나머지 셋의 화면에도 같은 서사가 나타난다 | ✓ VERIFIED | `frontend/src/main.ts` implements a shared 1.5s poll loop against `GET /api/sessions/{id}/events?from_seq=N`; `routes_actions.py::confirm` submits `ResolveCheck` then streams `AppendNarration` through the single-consumer `SessionActor` (one writer per session, D-09). No client renders its own action result locally — `action.ts`'s confirm/reject handlers never touch the narration DOM, results only arrive via the shared poll loop (04-06-SUMMARY.md Accomplishments). Live human two-tab checkpoint (04-06-SUMMARY.md Task 3, item "cross-tab/judgment-before-narration flow") confirmed this against a real running server with live NIM provider calls, plus a curl repro showing `check_resolved` (seq 5) preceding all `narration_appended` (seq 6-14). |
| 2 | 인터넷이 끊겼다 다시 들어와도 놓친 부분이 이어 붙고 처음부터 다시 시작하지 않는다 | ✓ VERIFIED | `EventStore.read_events(session_id, from_seq)` is inclusive-boundary (`event_log/store.py:96`, `WHERE seq >= ?`); `main.ts:100-102` documents `lastSeq` starting at -1 so the *first* request is `from_seq=0` (full replay), but subsequent polls only ever request `from_seq = lastSeq + 1` — a reconnect after a gap does not restart from 0, it resumes where it left off, and a hard refresh naturally re-issues `from_seq=0` for a true from-scratch replay. Disconnect banner: `DISCONNECT_AFTER_FAILURES` triggers at 7 consecutive poll failures (~10.5s, `main.ts:20-24`), text "연결이 끊겼어요..." shown/hidden per `consecutiveFailures` counter (`main.ts:116-140`), matching D-40. Human checkpoint item 7 ("full-history replay + bottom-scroll on reconnect") passed as-is. |
| 3 | 위협 시계의 현재 칸과 실패 누적 카운터가 화면에 보이고, 실패 3회에 도달하면 시계가 강제로 한 칸 진행된 뒤 카운터가 초기화된다 | ✓ VERIFIED | `rules_core/reducer.py:37,96,101-110`: `fails_since_clock` increments on `check_resolved` failures, resets to 0 on any `clock_advanced` regardless of trigger. `session_actor/actor.py:48,251-284`: `AUTO_ADVANCE_FAILURE_THRESHOLD = 3`, `_maybe_auto_advance` submits a self-recursive `clock_advanced(trigger="fail_counter")` inside the same single-consumer queue (atomic under concurrent submits). `routes_events.py` returns both `clock_segment` and `fails_since_clock` in `GameStateView`; `session_view.ts::renderHeader` renders both plus an explanatory caption. **Behavioral test evidence** (not just presence): `tests/test_session_actor_auto_advance.py::test_third_failure_triggers_exactly_one_clock_advanced_with_fail_counter_trigger` and `::test_after_auto_advance_fails_since_clock_resets_and_can_trigger_again` — both pass in the 388-test suite. A real bug in this exact mechanism (`SessionActor.__init__` not replaying persisted events across process boundaries) was found and fixed during this phase (commit `b2c46e4`), then re-confirmed live via a 3x CLI-failure repro (04-06-SUMMARY.md Deviation #2) and via the human checkpoint's item 9. |
| 4 | 플레이어가 자기 캐릭터 시트를 읽기 전용으로 열어 볼 수 있다 | ✓ VERIFIED | `GET /api/sessions/{id}/characters/{character_id}` returns `CharacterSheetView`; no write handler exists on that path (`routes_characters.py` — only `@router.get` x3 and one `@router.post` for `select-character`, none touch the sheet path with a mutating verb). `tests/test_web_characters.py:60-63` asserts PUT/PATCH/DELETE/POST on the sheet URL all return 405. `frontend/src/character.ts::mountCharacterSheet` renders a collapsible read-only stat list. Human checkpoint confirmed the toggle is reachable after QA round 1's fix (commit `536a557`, which corrected a real disappearing-element bug where the toggle was destroyed by the first poll tick). |
| 5 | 세션이 끝나면 실제 토큰 소모량·실제 턴 수·판정 실패 횟수 대비 시계 진행 횟수가 사람 손을 거치지 않고 집계되어 나온다 | ✓ VERIFIED | `session_actor/report.py::build_report` computes `turn_count`, `total_tokens`, `failure_to_clock_ratio` (null-safe, no div-by-zero) directly from `GameState` with zero filtering (docstring explicitly forbids filtering out failed turns, since that's the exact case MEAS-03 needs to observe). `session_actor/actor.py:248,276-284` (`_write_report_snapshot`) calls `write_report` after **every** processed command inside `SessionActor._process` — no operator action required; a write failure degrades to a one-line stderr warning without blocking event recording (`tests/test_session_actor_auto_advance.py::test_unwritable_report_dir_does_not_block_submit_or_event_recording`). `gptrpg report --db --session` (CLI) offers on-demand read of the same data (D-44) but is not required for the numbers to exist. Human checkpoint item 10 ("`gptrpg report` output") passed as-is. |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/gptrpg/web/app.py`, `routes_events.py` | Polling endpoint + lifespan-scoped store/registry | ✓ VERIFIED | Exists, substantive, wired; `create_app` builds `EventStore`/`SessionRegistry` once in lifespan |
| `frontend/src/main.ts`, `session_view.ts` | Poll loop, disconnect banner, textContent-only rendering | ✓ VERIFIED | 1.5s loop, 7-failure banner threshold, `textContent` discipline confirmed by code review (no innerHTML) |
| `src/gptrpg/session_actor/report.py` | `build_report`/`write_report`, MEAS-01/MEAS-03 numbers | ✓ VERIFIED | 13-field aggregate, null-safe ratio, UTF-8 unescaped JSON (`ensure_ascii=False`) |
| `src/gptrpg/rules_core/reducer.py`, `session_actor/actor.py` | `fails_since_clock`, 3-failure auto-advance | ✓ VERIFIED | Reducer logic + actor hook, both test-covered and live-repro-covered |
| `src/gptrpg/web/characters_data.py`, `routes_characters.py`, `frontend/src/character.ts` | Read-only character sheet, cookie identity | ✓ VERIFIED | 4 hand-authored `Entity` characters, 405-on-write test, cookie-based selection persisted across refresh |
| `src/gptrpg/turn/context.py`, `web/routes_actions.py`, `frontend/src/action.ts` | Declare/confirm HTTP flow, shared turn-context assembler | ✓ VERIFIED | `build_turn_context` used by both `declare` and `confirm`; blocking AI calls via `asyncio.to_thread`; confirm validates all commit-gating fields before writing `ConfirmAction` (CR-01 fix, commit `62f1093`) |
| `README.md` | Operator runbook for experiment day | ✓ VERIFIED | "실험 당일 실행 절차" section with build/serve/agents-select/link/report commands |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `routes_events.poll_events` | `EventStore.read_events` | inclusive `from_seq` query | ✓ WIRED | `seq >= from_seq`, confirmed in `store.py:100` |
| `routes_events.poll_events` | `session_actor.projection.rebuild_state` | shared fold logic | ✓ WIRED | Also used by `SessionActor.__init__` since commit `b2c46e4` — single state-bootstrap implementation |
| `apply_event('check_resolved')`/`clock_advanced` | `GameState.fails_since_clock` | reducer increment/reset | ✓ WIRED | `reducer.py:96,101-110`, test-covered |
| `SessionActor._process` | `session_actor.report.write_report` | auto-save hook after each command | ✓ WIRED | `actor.py:248,276-284` |
| `routes_actions.declare` | `asyncio.to_thread(classify, ...)` | non-blocking AI call | ✓ WIRED | `routes_actions.py:159-167`; store/actor calls stay on the event-loop thread |
| `routes_actions.confirm` | `actor.submit(ResolveCheck)` → then `narrate` | judgment-before-narration ordering | ✓ WIRED | Code-order guaranteed (`routes_actions.py:289-346`), confirmed by curl repro (check seq 5 before narration seq 6-14) |
| `action.ts` confirm button | `POST .../actions/confirm` | sole path to dice roll | ✓ WIRED | No client-side roll simulation; confirmed by human checkpoint |
| `characters_data.get_character(id).stats` | `TurnContext.character_state` | real player stats in AI context | ✓ WIRED | `routes_actions.py:138-145,323-325` passes `character.stats`, not placeholder enemy stats |

### Behavioral Spot-Checks / Test Evidence

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full test suite | `uv run pytest -q` | 388 passed, 2 warnings (unrelated deprecation notices) | ✓ PASS |
| Import layering contract | `uv run lint-imports` | 3 kept, 0 broken | ✓ PASS |
| Third failure triggers exactly one auto-advance with `fail_counter` trigger | named test | pass (part of full-suite run above) | ✓ PASS |
| `fails_since_clock` resets to 0 and can trigger again | named test | pass (part of full-suite run above) | ✓ PASS |
| Sheet URL rejects PUT/PATCH/DELETE/POST with 405 | named test | pass (part of full-suite run above) | ✓ PASS |
| Report snapshot updates after every submitted command, including failures | named test | pass (part of full-suite run above) | ✓ PASS |
| CR-01 fix: malformed confirm leaves no orphaned `action_confirmed` event | named test (`test_confirm_unknown_character_id_leaves_no_orphaned_confirm_event`) | pass (part of full-suite run above) | ✓ PASS |
| `confirm()` validates `modifiers`/`character_id`/`rulebook_id` before submitting `ConfirmAction` | source inspection, `routes_actions.py:245-276` | validation block runs before `actor.submit(ConfirmAction(...))` at line 264 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| RIG-04 | 04-03, 04-06 | 위협 시계 + 실패 카운터 표시, 3회 실패 시 자동 진행 | ✓ SATISFIED | Reducer + actor logic, header display, test + live repro |
| RIG-05 | 04-04, 04-05, 04-06 | 캐릭터 시트 읽기 전용 열람 | ✓ SATISFIED | 405 test, real stats flow to AI context |
| RIG-07 | 04-01, 04-05, 04-06 | 링크 하나로 동시 관전 + 재접속 시 이어붙임 | ✓ SATISFIED | Polling architecture, inclusive `from_seq`, live two-tab checkpoint |
| MEAS-01 | 04-02, 04-03 | 토큰 소모량·턴 수 자동 집계 | ✓ SATISFIED | `build_report`, auto-save hook, no manual step required |
| MEAS-03 | 04-02, 04-03 | 실패 대비 시계 진행 비율 자동 집계 | ✓ SATISFIED | `failure_to_clock_ratio`, null-safe, unfiltered by design (per module docstring) |

No orphaned requirements — REQUIREMENTS.md's traceability table maps exactly these five IDs to Phase 4, and all five appear in at least one plan's `requirements` frontmatter field. REQUIREMENTS.md already marks all five `[x]` complete.

### Anti-Patterns Found

None. Scanned all phase-modified source/frontend/doc files (`web/app.py`, `routes_events.py`, `routes_actions.py`, `routes_characters.py`, `characters_data.py`, `session_actor/report.py`, `session_actor/actor.py`, `rules_core/reducer.py`, `turn/context.py`, `turn/__init__.py`, `main.ts`, `session_view.ts`, `character.ts`, `action.ts`, `README.md`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/"not yet implemented" markers — zero hits.

**Post-phase code review (04-REVIEW.md):** 1 CRITICAL finding (CR-01 — `/actions/confirm` committed the `ConfirmAction` event before validating fields that gate the rest of the turn, leaving orphaned "confirmed" events on validation failure). **This was fixed** in commit `62f1093` prior to this verification, with a regression test added and confirmed passing in the current 388-test suite. 5 WARNING + 1 INFO findings remain open (CLI subcommand can't represent a differing suggestion stat; duplicated session-id regex; unbounded `target`/`modifiers` fields on `ConfirmRequest`; frontend submit control stays enabled during confirm round-trip; unguarded tuple-unpack in CLI turn flow; a docstring understates the character-impersonation trust-model detail). None of these touch this phase's five success criteria — they are scoped as quality/robustness follow-ups by the review itself, not data-integrity blockers.

### Human Verification (Already Completed)

A human already ran a live two-browser-tab checkpoint against this phase's final build (04-06-SUMMARY.md, Task 3), covering all 12 of the plan's checklist items:
- 9 items confirmed as-is (character-select list, grouped-narration readability, full-history replay + bottom-scroll on reconnect, three-failure auto-advance, `gptrpg report` output, literal-text rendering of injected HTML/no XSS, no unwanted auto-scroll jump, plus the general cross-tab/judgment-before-narration flow).
- 3 items required UI fixes, applied in commit `536a557` and re-verified via `tsc --noEmit` + `npm run build`: current-character label was missing; character-sheet toggle was unreachable (real disappearing-element bug, root-caused and fixed); threat-clock/fail-counter numbers had no plain-language explanation.
- 2 items explicitly deferred by the human as known, out-of-scope limitations: per-move rulebook explanation of *why* a roll happens (blocked on a rulebook-neutral data-format addition, correctly deferred per PROJECT.md's "no single-rulebook bias" constraint — this is not RIG-04/05/07/MEAS-01/03 scope), and AI narrative genre/tone drift (an AI-quality question for HYP-01/HYP-02 in Phase 6, not a web-layer structural gap).

No further human verification items are required for this phase's success criteria — all five are either directly test-covered, directly code-inspectable, or already confirmed by the completed live human checkpoint.

### Gaps Summary

No gaps. All five phase success criteria (mapping 1:1 to RIG-04, RIG-05, RIG-07, MEAS-01, MEAS-03) are verified with both static evidence (code paths, passing named tests) and dynamic evidence (a completed live two-tab human checkpoint, re-verified after 3 requested UI fixes). The one code-review BLOCKER (CR-01) was fixed and regression-tested before this verification ran. Full suite (388 tests) and import-linter (3/3 contracts kept) pass. The two items the human explicitly deferred are genuinely out of this phase's scope (rulebook-content design and AI narration quality, both belong to later phases/hypotheses) and do not affect any of the five success criteria.

---

_Verified: 2026-08-03T08:14:30Z_
_Verifier: Claude (gsd-verifier)_

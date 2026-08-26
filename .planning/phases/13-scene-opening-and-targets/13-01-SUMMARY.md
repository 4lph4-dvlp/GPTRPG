---
phase: 13-scene-opening-and-targets
plan: 01
subsystem: gameplay-scene
tags: [scenario-declaration, scene-opening, event-schema, actor-queue, react, fastapi, pydantic]

# Dependency graph
requires:
  - phase: 12.1-character-creation
    provides: "party_roster_locked event (opening only fires after the roster is locked, D-01)"
  - phase: 08-trust-and-identity
    provides: "read_identity cookie-auth pattern reused verbatim by the opening route"
provides:
  - "ScenarioDecl/OpeningDecl declaration format (rules_core/scenario.py) mirroring Rulebook's registration-time validation shape (D-18)"
  - "SCENARIOS registry + validate_registered_scenarios() enforcing the five opening elements at import time (D-07(a))"
  - "First scripted (AI-free) scenario, lamplight_vigil, proving the format accepts both scripted and sketch kinds (D-21)"
  - "scene_opened event kind, EVENT_SCHEMA_VERSION 11->12, reducer branch (session_scenario_id/scene_opened_seq on GameState)"
  - "ClaimGmSlot/ReleaseGmSlot in-queue slot mechanism closing the AI-fires-twice-across-tabs hole (D-02/D-03) — the pattern 13-02 will reuse for the four existing GM calls"
  - "POST /sessions/{id}/opening — third declare_seq-free narration entry point (SCENE-01)"
  - "OpeningCard + StoryPane wiring + SessionScreen auto-fire effect (shouldOpenScene/hasLockedRoster pure functions in openingView.ts)"
affects: [13-02-gm-slot-migration, 13-03-sketch-scenario-generation, 13-06-roster-screen]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 24438
  tasks: 3
  commits: 7

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Declaration-format registry (frozen dataclass + module-level dict + import-time validate_*() call) extended from rulebooks/ to scenarios/ — second real user of the Rulebook pattern"
    - "In-queue slot claim/release (ClaimGmSlot/ReleaseGmSlot, no event, memory-only set) replaces queue-outside-precheck for auto-fired AI calls — the fix for the four-GM-call double-invocation class of bug"
    - "Pure bootstrap-trigger function tested outside the component (shouldOpenScene/hasLockedRoster in openingView.ts) — same place/shape as creationView.ts's shouldAnnounce, because this repo has no RTL and cannot test conditions living inside a component"

key-files:
  created:
    - src/gptrpg/rules_core/scenario.py
    - src/gptrpg/rulebooks/scenarios.py
    - src/gptrpg/rulebooks/lamplight_vigil.py
    - frontend/src/components/OpeningCard.tsx
    - frontend/src/session/openingView.ts
    - frontend/src/session/openingView.test.ts
    - tests/test_scenario.py
    - tests/test_scene_opening.py
  modified:
    - src/gptrpg/event_log/schema.py
    - src/gptrpg/rules_core/reducer.py
    - src/gptrpg/session_actor/actor.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/web/routes_events.py
    - src/gptrpg/rulebooks/threat_clocks.py
    - frontend/src/api/types.ts
    - frontend/src/api/client.ts
    - frontend/src/panes/StoryPane.tsx
    - frontend/src/screens/SessionScreen.tsx
    - frontend/src/labels.ts
    - tests/fixtures/session1_expected_state.json
    - tests/test_event_schema_migration.py
    - frontend/src/session/creationView.test.ts

key-decisions:
  - "Approved deviation — OpeningRequest.scenario_id default is LAMPLIGHT_VIGIL_ID, not the existing well scenario. The plan's own line 225 named the well scenario as default while line 198 assigns that scenario's registration to 13-03 — an internal contradiction. Defaulting to an unregistered id would 400 every real call (no scenario-picker UI exists, planner assumption #5). User approved explicitly. 13-03 MUST re-judge this default when it registers the well scenario."
  - "Bugfix (4c01856): SessionScreen's auto-open effect depended on `feed.state?.party_roster !== null`, which is `true` both when state is absent (`undefined !== null`) and when the roster is already locked — React saw no change across exactly the transition the effect exists to observe, so the effect never re-ran after initial mount and opening never fired for anyone except whoever finishes creation last. Fixed by extracting `hasLockedRoster(state)`, which checks `state !== null` first so the transition reads false->true. Regression test added covering the wiring, not just the predicate — see 'Lesson' below."
  - "D-10 premise correction (6abbccb): the plan originally claimed the creation GM summary line survives to the play screen. It does not — CreationPane unmounts with CreationScreen once the roster locks, and groupTurns discards rootless narration. StatusPane's character name + one_line_intro is what actually satisfies 'who am I' on the play screen; 13-01 added no new banner."
  - "Item 4 of the human verification (late joiner sees opening) was reframed from the plan's literal wording ('open a third browser') to re-attachment (close a tab, reopen the same URL) — character occupation is exclusive and permanent by design (D-05/D-07, _prepare_occupy), so a 4th browser has no seat to take. The plan's original wording was untestable as written; re-attachment is what the check was actually about."
  - "Three defects/requests surfaced during Task 3 UAT were captured as todos and deliberately NOT folded into this plan: .planning/todos/pending/2026-08-26-mobile-status-pane-drawer.md and .planning/todos/pending/2026-08-26-creation-host-transfers-on-timeout.md."

patterns-established:
  - "In-queue GM slot claim/release (ClaimGmSlot/ReleaseGmSlot, try/finally release) — 13-02 migrates the four existing auto-fired GM calls onto this exact mechanism."
  - "Scenario declaration format (ScenarioDecl/OpeningDecl, registration-time five-element validation) — 13-03 migrates the existing well scenario into this registry as its second entry."

requirements-completed: [SCENE-01, SCENE-02]

coverage:
  - id: D1
    description: "판정 없이 장면을 여는 정식 경로 — POST /sessions/{id}/opening이 declare_seq 없이 scene_opened 사건을 남긴다 (SCENE-01)"
    requirement: "SCENE-01"
    verification:
      - kind: integration
        ref: "tests/test_scene_opening.py — skeleton HTTP test (open session, lock roster, POST /opening, assert single scene_opened event)"
        status: pass
    human_judgment: false
  - id: D2
    description: "낭독문형 시나리오는 AI를 안 부르고 저자가 쓴 다섯 칸을 그대로 이어 낸다 — 비용 0, 문장 틀어짐 0 (D-06)"
    requirement: "SCENE-02"
    verification:
      - kind: unit
        ref: "tests/test_scenario.py — render_scripted_opening order/separator/non-blank assertions"
        status: pass
      - kind: integration
        ref: "tests/test_scene_opening.py — text contains hooks[0] and invitation verbatim, source == 'scripted'"
        status: pass
    human_judgment: false
  - id: D3
    description: "다섯 요소 중 하나라도 빈 시나리오는 등록(import) 시점에 결정론적으로 거부된다 (SCENE-02 empty, D-07(a))"
    requirement: "SCENE-02"
    verification:
      - kind: unit
        ref: "tests/test_scenario.py -k invalid — five element-omission branches + hooks=() branch, all raising InvalidOpening"
        status: pass
    human_judgment: false
  - id: D4
    description: "겹친 오프닝 호출이 사건 하나로 수렴하고, 실패해도 GM 슬롯이 영구히 잠기지 않는다 (D-02/D-03)"
    verification:
      - kind: integration
        ref: "tests/test_scene_opening.py — duplicate opening call returns 200/opened=False, event count stays 1"
        status: pass
    human_judgment: false
  - id: D5
    description: "화면이 명단 잠금 직후 스스로 오프닝을 부르고, 문단을 이야기 판 맨 위에 명조 문단 하나로 그리며, 새 CSS를 한 줄도 안 더한다 — 사람이 실제로 빈 화면을 만나지 않는다"
    verification:
      - kind: manual_procedural
        ref: "Task 3 human-verify checkpoint — six-item UAT across multiple browsers, approved 2026-08-26"
        status: pass
    human_judgment: true
    rationale: "Whether the screen 'feels' like it never shows a blank state, whether the paragraph reads well, and whether the screen avoids urging the player are UX-adequacy judgments no test asserts — this is exactly what Task 3's checkpoint exists for. The human explicitly approved all six items (see below)."
  - id: D6
    description: "기존 시험 전부와 층 계약(.importlinter)이 그대로 통과한다 — 회귀 없음"
    verification:
      - kind: unit
        ref: ".venv/bin/python -m pytest -q --tb=short (full suite, run during Task 1/2 execution)"
        status: pass
      - kind: other
        ref: ".venv/bin/python -m lint_imports"
        status: pass
    human_judgment: false
---

# Phase 13 Plan 01: Scenario Declaration Format + Scripted Scene Opening Summary

**A registered scenario-declaration format (mirroring Rulebook's own registration-time validation), a first AI-free scripted scenario, and a third declare_seq-free narration entry point — `POST /sessions/{id}/opening` — that fires exactly once per session even across concurrent tabs, closing the "party finishes creation and stares at an empty screen" gap end to end.**

## Performance

- **Duration:** Not tracked precisely — spans a multi-session window from the first task commit (2026-08-25 02:50) through the D-10 correction commit (2026-08-26 10:06), including an overnight/multi-hour wait for the Task 3 human-verify checkpoint.
- **Started:** 2026-08-25T02:50:09+09:00 (first task commit, `fd85953`)
- **Completed:** 2026-08-26T10:06:47+09:00 (D-10 correction commit, `6abbccb`)
- **Tasks:** 3 (Task 1 tracer, Task 2 auto, Task 3 checkpoint:human-verify — approved)
- **Files modified:** 25 (22 implementation/test files + 1 plan self-correction + 2 UAT-captured todos)

## Accomplishments

- `ScenarioDecl`/`OpeningDecl` (`src/gptrpg/rules_core/scenario.py`) give scenarios their first declaration format, copying `Rulebook`'s frozen-dataclass + registration-time-validation shape field-for-field, including the "empty tuple = no concept" vs "`None` = not declared yet" per-field convention.
- `SCENARIOS` registry + `validate_registered_scenarios()` (`src/gptrpg/rulebooks/scenarios.py`) enforce the five opening elements, the two improv axes, cast-name uniqueness, and opening-kind monotonicity — all at import time, so a malformed scenario cannot be discovered mid-session.
- `lamplight_vigil.py` — a new, short, scripted (AI-free) scenario unrelated to the existing well story, proving the format actually accepts both `scripted` and `sketch` kinds rather than one being a de facto default.
- `scene_opened` event kind lands with `EVENT_SCHEMA_VERSION` 11->12 and the `reducer.py` branch in the same commit (`fd85953`) — `GameState` gains `session_scenario_id`/`scene_opened_seq`.
- `ClaimGmSlot`/`ReleaseGmSlot` — an in-queue (not pre-queue) slot claim mechanism that closes the "AI fires twice across concurrent tabs" hole for the first of what will be five auto-fired GM calls; `finally`-guaranteed release means a failed AI call never permanently locks a session out of its own opening.
- `POST /sessions/{id}/opening` — the third narration entry point that needs no `declare_seq`, reusing `proceed()`'s identity-check shape verbatim, claiming the slot before reading the scenario, and never calling AI for the scripted path.
- Frontend: `OpeningCard` (reuses the existing `.turn` container, no new CSS), `StoryPane` wired for opening/pending/error/retry states matching `CreationScreen`'s established retry visual treatment, and `SessionScreen`'s auto-fire effect driven by the pure, independently-tested `shouldOpenScene`/`hasLockedRoster` functions in `openingView.ts`.
- Bugfix (`4c01856`, found during Task 3 UAT prep): the auto-fire effect's dependency formula collapsed two distinct roster states to the same boolean, so the opening never fired for anyone except whoever finished character creation last. Fixed and regression-tested.
- Task 3 human-verify checkpoint: all six UAT items **approved** (see below).

## Task Commits

Each task was committed atomically:

1. **Task 1: 시나리오 선언 형식 + 낭독문형 오프닝 경로 (요청→사건)** - `fd85953` (feat)
2. **Task 2: 화면 자동 호출 + OpeningCard + StoryPane 렌더** - `f01ed89` (feat)
3. **Bugfix (found during Task 3 UAT prep): 오프닝 자동 발동 effect 의존성 배선 결함** - `4c01856` (fix)
4. **Todo capture (UAT finding, out of scope): mobile status-pane drawer request** - `583d0b2` (docs)
5. **Todo capture (UAT finding, out of scope): creation host-transfer defect** - `72e6339` (docs)
6. **Todo refinement: drawer must keep who-am-I line visible when collapsed** - `5daca48` (docs)
7. **Task 3 checkpoint follow-up: D-10 premise correction** - `6abbccb` (docs)

**Plan metadata:** (this commit — see `git_commit_metadata` step)

## Files Created/Modified

- `src/gptrpg/rules_core/scenario.py` - `ScenarioDecl`/`OpeningDecl` declaration dataclasses + `ThreatClockContent` (moved here from `threat_clocks.py`, re-exported)
- `src/gptrpg/rulebooks/scenarios.py` - `SCENARIOS` registry, `get_scenario`, `validate_registered_scenarios()` (called at module bottom)
- `src/gptrpg/rulebooks/lamplight_vigil.py` - first scripted (AI-free) scenario
- `src/gptrpg/rulebooks/threat_clocks.py` - re-exports `ThreatClockContent` from its new home
- `src/gptrpg/event_log/schema.py` - `SceneOpened` event model, `EVENT_SCHEMA_VERSION` 11->12
- `src/gptrpg/rules_core/reducer.py` - `scene_opened` branch, `GameState.session_scenario_id`/`scene_opened_seq`
- `src/gptrpg/session_actor/actor.py` - `ClaimGmSlot`/`ReleaseGmSlot`/`OpenScene` commands, `_gm_slots_in_flight`, `GmSlotBusy`/`GmSlotClaimed`/`GmSlotReleased`/`SceneAlreadyOpened`
- `src/gptrpg/web/routes_actions.py` - `POST /sessions/{id}/opening` route
- `src/gptrpg/web/routes_events.py` - `GameStateView.scene_opened_seq`
- `frontend/src/api/types.ts` - `SceneOpenedEvent`, `GameStateView.scene_opened_seq`
- `frontend/src/api/client.ts` - `openScene(sessionId, characterId, scenarioId?)`
- `frontend/src/components/OpeningCard.tsx` - new component, reuses `.turn` container
- `frontend/src/panes/StoryPane.tsx` - opening/pending/error/retry render states
- `frontend/src/screens/SessionScreen.tsx` - auto-fire effect calling `shouldOpenScene`
- `frontend/src/session/openingView.ts` - `shouldOpenScene`, `hasLockedRoster` pure functions
- `frontend/src/session/openingView.test.ts` - trigger-condition + wiring regression tests
- `frontend/src/labels.ts` - `COPY.openingWaiting`, `COPY.openingRetry`
- `tests/test_scenario.py` - registry structural + five-element validation tests
- `tests/test_scene_opening.py` - HTTP end-to-end skeleton test
- `tests/fixtures/session1_expected_state.json`, `tests/test_event_schema_migration.py` - regenerated/updated for schema v12
- `.planning/todos/pending/2026-08-26-mobile-status-pane-drawer.md` - UAT finding, deferred
- `.planning/todos/pending/2026-08-26-creation-host-transfers-on-timeout.md` - UAT finding, deferred

## Decisions Made

- **Approved deviation — `OpeningRequest.scenario_id` default.** The plan's own text was internally contradictory (line 225 named the existing well scenario as default; line 198 assigns that scenario's registration to 13-03). Defaulting to an unregistered id would 400 every real call, since no scenario-picker UI exists (planner assumption #5). Default is `LAMPLIGHT_VIGIL_ID`, explicitly approved by the user. **13-03 must re-judge this default when it registers the well scenario** — this is not a permanent choice, it is a placeholder that becomes wrong the moment a second scenario exists and nothing repoints the default.
- **The bugfix, and why the plan's own testing discipline did not catch it.** `openingView.ts`'s docstring states the trigger predicate lives in a pure, independently-tested function precisely so a mis-wired trigger cannot hide behind passing structural tests ("12.3에서 여섯 라운드를 살아남은 결함이 정확히 그 모양이었다"). That discipline still missed this bug, because the defect was in the **effect's dependency array**, not the predicate itself: `feed.state?.party_roster !== null` evaluates to `true` both when `state` is absent (`undefined !== null`) and when the roster is already locked, so React's `Object.is` comparison saw no change across exactly the transition the effect exists to observe. The effect never re-ran after its initial mount, and the opening was never requested. This hit every browser that mounted with the roster already locked — i.e. everyone except whoever completes character creation last. Fixed by extracting `hasLockedRoster(state)`, which checks `state !== null` first so the transition correctly reads `false -> true`. A regression test covering the **wiring** (not just the predicate) is now in `openingView.test.ts`. **Lesson recorded for future plans: the pure-predicate discipline covers correctness of the predicate, not correctness of the effect dependencies that feed it — both need their own test.**
- **D-10 premise correction** (`6abbccb`): Task 3 UAT item 5 found the plan's stated justification for not adding a new "who am I" UI element was factually wrong — the creation-time GM summary line (`creation_gm_spoke`) does not survive to the play screen; `CreationPane` unmounts with `CreationScreen` once the roster locks. `StatusPane`'s character name + `one_line_intro` is what actually satisfies D-10 on the play screen. Consequence for downstream plans: any future plan relying on the creation-time GM line being visible during play is building on a false premise — it must read `StatusPane`, not `creation_gm_spoke`.
- **Item 4's plan wording was untestable as written.** "늦게 들어온 사람이 세 번째 브라우저로 들어가면 오프닝을 본다" cannot be executed literally — character occupation is exclusive and permanent by design (D-05/D-07, `_prepare_occupy`), so a 4th browser has no character seat to take. Re-checked as re-attachment (close a tab, reopen the same URL in the same browser) instead, which is what the check was actually verifying. Recorded here so a future reader does not repeat the same dead end.
- Three defects/requests found during UAT were captured as todos and deliberately **not** folded into this plan (scope discipline — this plan is the thin end-to-end slice, not a catch-all): `.planning/todos/pending/2026-08-26-mobile-status-pane-drawer.md`, `.planning/todos/pending/2026-08-26-creation-host-transfers-on-timeout.md`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `OpeningRequest.scenario_id` default resolved to `LAMPLIGHT_VIGIL_ID` instead of the plan's stated default**
- **Found during:** Task 1
- **Issue:** Plan line 225 specified the existing well scenario as the request default, but plan line 198 explicitly defers that scenario's registration to 13-03 — defaulting to it in this plan would 400 every real call since it is not yet registered.
- **Fix:** Defaulted to `LAMPLIGHT_VIGIL_ID`, the only scenario this plan registers.
- **Files modified:** `src/gptrpg/web/routes_actions.py`
- **Verification:** `tests/test_scene_opening.py` exercises the default path.
- **Committed in:** `fd85953`
- **User approval:** Explicit — see Decisions Made above. **13-03 must re-judge this default.**

**2. [Rule 1 - Bug] Fixed opening auto-fire effect dependency wiring**
- **Found during:** Task 3 UAT prep (pre-checkpoint sanity pass)
- **Issue:** `feed.state?.party_roster !== null` collapsed the "state absent" and "roster already locked" cases to the same `true`, so the effect never re-ran and the opening never fired for late-joining tabs (everyone except the last person to finish creation).
- **Fix:** Extracted `hasLockedRoster(state)` (checks `state !== null` first) and switched the effect dependency to it.
- **Files modified:** `frontend/src/screens/SessionScreen.tsx`, `frontend/src/session/openingView.ts`, `frontend/src/session/openingView.test.ts`
- **Verification:** New regression test reproduces the old formula's collapse and proves the new one distinguishes the transition; full frontend test suite green.
- **Committed in:** `4c01856`

---

**Total deviations:** 2 auto-fixed (1 blocking/approved-scope default, 1 bug). **Impact on plan:** Both were necessary for correctness — the default fix prevents every real call from 400ing, and the bugfix is what makes the opening actually fire for the majority of players (everyone but the last to finish creation). No scope creep; the 13-03 re-judgment obligation is explicitly flagged forward.

## Issues Encountered

- **Known pre-existing full-suite failure, unrelated to this plan:** the local `.gptrpg/events.db` disagrees with a committed test fixture. Verified via `git stash` that this discrepancy pre-dates this plan's work — it is a local-database/fixture drift issue, not a regression introduced here. Flagged so the phase verifier does not attribute it to 13-01.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The `ScenarioDecl`/`SCENARIOS` registration format, the `ClaimGmSlot`/`ReleaseGmSlot` in-queue mechanism, and the `scene_opened` event/schema-v12 plumbing are all in place and human-verified end to end.
- **13-02** can migrate the four existing auto-fired GM calls onto the `ClaimGmSlot`/`ReleaseGmSlot` pattern this plan established.
- **13-03** must: (a) migrate the existing well scenario (`threat_clocks.py` content) into a second `ScenarioDecl` registry entry, which will also trigger `validate_registered_scenarios()`'s "opening_kind must not be monotonic across 2+ scenarios" check for the first time; (b) **re-judge the `OpeningRequest.scenario_id` default**, currently `LAMPLIGHT_VIGIL_ID` as an approved stopgap; (c) build the `sketch` opening-kind's actual AI-narrowing path (this plan's `source="fallback"` branch is the real D-09 fallback it will land in front of, not a placeholder).
- **13-06** still owns the roster-screen "who's here" line in `StatusPane` — out of scope for this plan (see plan's own "아직 안 되는 것").
- Two UAT-sourced todos are open and unscheduled: mobile status-pane drawer, creation host-transfer-on-timeout.

## Self-Check: PASSED

All 8 created files verified present on disk; all 7 commits (`fd85953`, `f01ed89`, `4c01856`, `583d0b2`, `72e6339`, `5daca48`, `6abbccb`) verified present in git log.

---
*Phase: 13-scene-opening-and-targets*
*Completed: 2026-08-26*

---
phase: 13-scene-opening-and-targets
plan: 03
subsystem: gameplay-scene
tags: [scenario-registry, ai-opening, situation-judge, narration-guard, fastapi, nvidia-nim]

# Dependency graph
requires:
  - phase: 13-scene-opening-and-targets (plan 01)
    provides: "ScenarioDecl/OpeningDecl registry, scene_opened event, POST /sessions/{id}/opening route, scripted-opening fallback branch this plan builds the sketch branch in front of"
provides:
  - "우물 아래의 것(WELL_BELOW) migrated into the ScenarioDecl registry as the second entry — opening_kind monotonicity check (D-21) fires for real for the first time"
  - "Three hardcoded single-scenario sites closed: turn/context.py's scene_entities=THREAT_CAST assignment, the threat-clock content it paired with, and imagery/scene_prompt.py's WELL_SCENARIO_SETTING constant — all three now flow through ScenarioDecl (D-18)"
  - "build_opening_situation_prompt / judge_opening_situation — a no-check-premise sibling of build_situation_prompt/judge_situation sharing one parsing helper, so the two contracts cannot drift apart"
  - "inspect_opening_completeness — Task 1's chosen (a) output check: non-empty text + at least one author-declared hook_terms match (NFC-normalized), no length check"
  - "AI-generated openings for sketch-kind scenarios: judge_opening_situation -> build_narration_facts -> narrate(), collected (not streamed), checked, regenerated once on failure, falls back to the author's five fields on repeated failure or provider outage (D-05/D-08/D-09)"
affects: [13-04-three-layer-targets, 13.1-narrative-lead]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 21212
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sibling-function-not-flag branching for opening vs. mid-turn AI prompts (build_opening_situation_prompt next to build_situation_prompt, judge_opening_situation next to judge_situation, sharing a private _parse_situation_response helper) — continues this repo's existing build_classifier_prompt/build_situation_prompt/build_scene_entity_prompt convention of one function per call shape rather than a shared is_opening flag."
    - "Document-level output check as a separate function from narration_guard's sentence-level inspect_sentence — inspect_opening_completeness judges the whole collected text once, not per-sentence, because 'does this opening contain a hook' cannot be answered one sentence at a time."

key-files:
  created: []
  modified:
    - src/gptrpg/rulebooks/threat_clocks.py
    - src/gptrpg/rulebooks/scenarios.py
    - src/gptrpg/turn/context.py
    - src/gptrpg/imagery/scene_prompt.py
    - src/gptrpg/agents/context.py
    - src/gptrpg/agents/prompt_assembly.py
    - src/gptrpg/agents/situation_judge.py
    - src/gptrpg/agents/narration_guard.py
    - src/gptrpg/web/routes_actions.py
    - tests/test_scenario.py
    - tests/test_imagery.py
    - tests/test_scene_opening.py
    - tests/test_situation_judge.py
    - tests/test_narration_isolation.py

key-decisions:
  - "Task 1 (checkpoint:decision, gate=blocking-human) resolved to option (a): registration-time structure check (13-01, unchanged) plus a minimal output check — non-empty generated text and at least one author-declared hook_terms match. The user's stated reasoning: option (b) (a sixth AI call judging all five elements) would require first overturning D-05's own no-new-role lock (this plan's line 45/324 asserted AGENT_ROLES stays put); option (c) (no output check at all) is the 'treat unverified as passed' pattern this project has been burned by repeatedly, including twice earlier in 13-01. Accepted and NOT quietly widened: this check does not verify 'why it matters' or the other three elements — those surface in real play instead. It is a presence check for the single most common real failure (the opening silently drops the hook), not a quality check."
  - "13-01's forward-flagged scenario_id default is now resolved (Task 2, previous executor's commit 8d228e6). OpeningRequest.scenario_id defaults to DEFAULT_SCENARIO_ID = WELL_BELOW_ID, not lamplight_vigil. Rationale re-confirmed at Task 3 time: lamplight_vigil is a minimal format-proof scenario written to satisfy D-21's 'both opening kinds must actually be exercised' requirement; WELL_BELOW is the project's real, previously-played scenario, and with no scenario-picker UI (13-01 assumption 5) the default is what every real session gets."
  - "AGENT_ROLES acceptance criterion is stale against the actual codebase, not against this plan's work. The plan's acceptance criteria assert `len(AGENT_ROLES) == 5`; the actual pre-existing value (verified via `git stash` against the Task-2 commit, before any Task 3 work) is already 7 (`action_classifier, clock_judge, creation_gm, master_gm, outcome_picker, scene_entity_judge, situation_judge`) — outcome_picker and creation_gm were added by earlier phases (12-06, 12.1-03) after this plan's <threat_model>/<planner_assumptions> text was written. The functional intent this criterion actually protects — 'this plan does not add a sixth-or-later new AI role' — holds: the count is identical before and after this plan's commits (7 == 7). No new role was added."
  - "13-02's D-10 premise correction (creation_gm_spoke does not survive to the play screen; StatusPane's character name + one_line_intro carries 'who am I') was checked against this plan's own work: Task 3 does not touch StatusPane, CreationPane, or any creation-time GM summary — no part of the opening implementation relies on the corrected-away premise. Recorded here per the continuation brief's instruction; no code change was needed."

patterns-established:
  - "Two AI calls sharing a parsing contract via a private helper function (_parse_situation_response) rather than one function branching on a flag — the pattern to follow for any future third variant of a judge_* function that must never diverge from an existing one's output contract."

requirements-completed: [SCENE-01, SCENE-02]

coverage:
  - id: D1
    description: "「우물 아래의 것」이 ScenarioDecl로 등록소에 들어가 있고, 세 하드코딩 자리(turn/context.py의 scene_entities 대입, imagery/scene_prompt.py의 WELL_SCENARIO_SETTING)가 전부 등록소를 거친다 (D-18, Task 2)"
    requirement: "SCENE-01"
    verification:
      - kind: unit
        ref: "tests/test_scenario.py — WELL_BELOW.cast is THREAT_CAST identity check, opening_kind monotonicity, threat_clock segment-count / imagery_setting length registration-time checks"
        status: pass
      - kind: unit
        ref: "tests/test_imagery.py — scene_prompt() accepts setting as a parameter, MAX_PROMPT_CHARS unchanged"
        status: pass
    human_judgment: false
  - id: D2
    description: "메모형(sketch) 시나리오에서 상황판단이 시나리오를 읽고 좁혀 서술에 넘기고, 서술은 여전히 시나리오 원문을 못 본다 (D-05, ARCH-02, Task 3)"
    requirement: "SCENE-02"
    verification:
      - kind: unit
        ref: "tests/test_narration_isolation.py::test_opening_path_narration_system_and_messages_exclude_all_five_opening_elements_verbatim"
        status: pass
      - kind: unit
        ref: "tests/test_situation_judge.py — build_opening_situation_prompt has no check-result premise, carries all five OpeningDecl fields labeled, and shares the exact JSON output contract with build_situation_prompt"
        status: pass
      - kind: integration
        ref: "Live run against the real NIM provider (nvidia/nemotron-3-ultra-550b-a55b) at localhost:8001, session live-verify-13-03-1787714456 — see Deviations/Live Verification section below"
        status: pass
    human_judgment: false
  - id: D3
    description: "생성된 오프닝이 다섯 요소를 실제로 담았는지 등록 시점 검사 + 최소 출력 대조로 확인한다(Task 1 결정 (a)) — 걸리면 한 번 재생성, 그래도 안 되면 D-09 폴백으로 저자의 다섯 칸이 그대로 200으로 나간다"
    requirement: "SCENE-02"
    verification:
      - kind: integration
        ref: "tests/test_scene_opening.py::test_sketch_opening_succeeds_records_ai_generated_text_with_sketch_source"
        status: pass
      - kind: integration
        ref: "tests/test_scene_opening.py::test_sketch_opening_fallback_to_authors_five_when_master_gm_provider_fails"
        status: pass
      - kind: integration
        ref: "tests/test_scene_opening.py::test_sketch_opening_regenerates_exactly_once_then_falls_back_when_hook_term_missing (asserts exactly 2 provider.stream() calls)"
        status: pass
      - kind: integration
        ref: "tests/test_scene_opening.py::test_sketch_opening_returns_503_and_records_nothing_when_provider_not_configured"
        status: pass
    human_judgment: false
  - id: D4
    description: "AI 역할이 다섯 그대로다(D-05) — 새 역할을 안 만들었다. NarrationFacts에 칸이 안 늘었다(ARCH-02)"
    verification:
      - kind: unit
        ref: "AGENT_ROLES count identical before/after this plan's commits (7 == 7, see key-decisions AGENT_ROLES note) — the literal '==5' acceptance criterion is stale against pre-existing codebase state, not against this plan"
        status: pass
      - kind: unit
        ref: "git diff HEAD~1 -- src/gptrpg/agents/context.py shows no new NarrationFacts field and no new class declaration"
        status: pass
    human_judgment: false
  - id: D5
    description: "기존 시험 전부와 층 계약(.importlinter)이 그대로 통과한다 — 회귀 없음"
    verification:
      - kind: unit
        ref: ".venv/bin/python -m pytest -q --tb=short (full suite, 1453 passed, 1 pre-existing unrelated failure documented below)"
        status: pass
      - kind: other
        ref: ".venv/bin/lint-imports (4 kept, 0 broken)"
        status: pass
    human_judgment: false

# Metrics
duration: unspecified (continuation session — resumed after a checkpoint pause; Task 2's wall-clock time belongs to the prior executor's session)
completed: 2026-08-26
status: complete
---

# Phase 13 Plan 03: Sketch-Scenario AI Opening + Scenario Registry Completion Summary

**「우물 아래의 것」이 시나리오 등록소의 두 번째 항목이 되어 시나리오 단수 가정을 걷어내고, 메모형 시나리오에서 상황판단이 시나리오를 읽어 좁힌 뒤 서술이 그 좁혀진 것만으로 실제 AI 오프닝을 쓴다 — 실마리 낱말 대조 하나로 최소 검사하고, 실패하면 저자의 다섯 칸이 화면에 오류 없이 그대로 나간다.**

## Performance

- **Tasks:** 3 (Task 1 checkpoint:decision — resolved by user before this session; Task 2 auto — completed by the prior executor, commit `8d228e6`; Task 3 auto — completed this session, commit `5302984`)
- **Files modified:** 14 (7 by Task 2, 8 by Task 3, one overlap: `src/gptrpg/rules_core/scenario.py` was read but not modified by either — see Files Created/Modified below for the exact per-task split)

## Accomplishments

- **Task 1 (decision, resolved before this session):** the user chose option (a) — registration-time structure check (already built in 13-01) plus a minimal generated-output check (non-empty + at least one `hook_terms` match). Full reasoning and accepted limitation recorded under Decisions Made.
- **Task 2 (`8d228e6`, prior executor):** `WELL_BELOW` (「우물 아래의 것」) is now a `ScenarioDecl` in the registry alongside `LAMPLIGHT_VIGIL`, reusing `THREAT_CAST`/`M0_THREAT_CLOCK` by identity (not copied — `WELL_BELOW.cast is THREAT_CAST`). The registry now has one `scripted` and one `sketch` scenario, so 13-01's "opening_kind must not be monotonic across 2+ scenarios" check fires for real for the first time. `build_turn_context(..., scenario=...)` gained the parameter that lets any call site (Task 3 is the first real caller) source scene entities and threat-clock content from a scenario instead of the module-level constants. `imagery/scene_prompt.py`'s `WELL_SCENARIO_SETTING` constant is gone; its value now lives on `WELL_BELOW.imagery_setting` and flows in as a parameter. Two new registration-time checks: threat-clock segment count must match `THREAT_CLOCK_SEGMENT_COUNT`, and `imagery_setting` must not exceed the imagery layer's 300-char prompt budget.
- **Task 3 (`5302984`, this session):** the `sketch` opening branch that 13-01 wired to fall through to the D-09 fallback now actually runs AI. `agents/context.py` gained `OPENING_CHECK_SUMMARY`, a platform-fixed stand-in for `NO_CHECK_SUMMARY` that does not imply an action happened. `agents/prompt_assembly.py` gained `build_opening_situation_prompt`, a sibling of `build_situation_prompt` with no check-result premise and the same closed JSON output contract, carrying `OpeningDecl`'s five fields as labeled `messages` content instead of a check result. `agents/situation_judge.py` gained `judge_opening_situation`, sharing a new private `_parse_situation_response` helper with `judge_situation` so the two functions' parsing/truncation contracts cannot drift apart. `agents/narration_guard.py` gained `inspect_opening_completeness` (Task 1's option (a), implemented literally: empty-text check + NFC-normalized `hook_terms` substring match, deliberately no length check per the 2026-08-24 decision). `web/routes_actions.py`'s `opening()` route now calls a new `_open_sketch_scene()` helper for the `sketch` branch: resolves character/rulebook (400 on failure) and the `situation_judge`/`master_gm` providers (503 on failure, before any judgment runs) — `gather_turn_judgments` is bypassed entirely, since clock-signal/entity/outcome judgments do not apply to an opening — calls `judge_opening_situation` once, collects `narrate()`'s output into one string (no streaming, per `<planner_assumptions>` 2), checks it, regenerates once on failure using the same `facts`, and falls back to `render_scripted_opening(scenario.opening)` on repeated failure or provider outage. `RecordAiCall` is submitted for both `situation_judge` and `master_gm` on every path (success, content-check failure, or provider exception), matching `proceed()`'s MEAS-02 discipline.
- **Live verification against real providers (not just the fake-provider test suite):** ran a full end-to-end session against the local verification server (port 8001, NIM/`nvidia/nemotron-3-ultra-550b-a55b`) — created a 3-person party, locked the roster, and called `POST /sessions/{id}/opening` with `scenario_id=well_below`. Result: `source: "sketch"`, a coherent multi-paragraph Korean opening naming all four scenario cast members (촌장 담녹, 우물지기 이슬, 순찰대장 곽서리, 홀린 아이 나울) and containing the hook term "우물" multiple times, generated on the first attempt (no regeneration needed). Both `ai_invoked` events (`situation_judge`, `master_gm`) recorded successfully with real token counts. Full transcript preserved in this session's scratchpad output (session id `live-verify-13-03-1787714456`).

## Task Commits

1. **Task 1: AI가 만든 오프닝의 다섯 요소를 무엇으로 검사할지 정한다 (D-08)** — decision only, no commit (resolved by the user before this session; recorded above)
2. **Task 2: 「우물 아래의 것」을 등록소로 옮기고, 시나리오를 직접 읽던 세 자리를 전부 그 한 줄기로 모은다** - `8d228e6` (feat, prior executor's session)
3. **Task 3: 메모형 시나리오에서 오프닝이 나온다 — 상황 판단이 좁혀 넘기고, 실패하면 원문이 그대로 나간다** - `5302984` (feat, this session)

**Plan metadata:** (this commit — see `git_commit_metadata` step)

## Files Created/Modified

**Task 2 (`8d228e6`):**
- `src/gptrpg/rulebooks/threat_clocks.py` - adds `WELL_BELOW`/`WELL_BELOW_ID`
- `src/gptrpg/rulebooks/scenarios.py` - registers `WELL_BELOW`, adds `DEFAULT_SCENARIO_ID`, two new registration-time checks
- `src/gptrpg/turn/context.py` - `build_turn_context(..., scenario=None)` parameter
- `src/gptrpg/imagery/scene_prompt.py` - removes `WELL_SCENARIO_SETTING`, accepts `setting` as a parameter
- `src/gptrpg/web/routes_actions.py` - default-scenario-id wiring, `_illustrate_scene` now passes `WELL_BELOW.imagery_setting`
- `tests/test_scenario.py`, `tests/test_imagery.py` - registration/format tests

**Task 3 (`5302984`):**
- `src/gptrpg/agents/context.py` - `OPENING_CHECK_SUMMARY`
- `src/gptrpg/agents/prompt_assembly.py` - `build_opening_situation_prompt`
- `src/gptrpg/agents/situation_judge.py` - `judge_opening_situation`, shared `_parse_situation_response`
- `src/gptrpg/agents/narration_guard.py` - `inspect_opening_completeness`, `_normalize_for_hook_match`
- `src/gptrpg/web/routes_actions.py` - `_open_sketch_scene`, `_collect_narration_text`, wired into `opening()`
- `tests/test_scene_opening.py` - four HTTP tests for the sketch/fallback/regenerate/503 branches
- `tests/test_situation_judge.py` - prompt-contract and `judge_opening_situation` unit tests
- `tests/test_narration_isolation.py` - opening-path isolation test

## Decisions Made

- **Task 1 checkpoint resolved to option (a).** See key-decisions in frontmatter for the full reasoning. Restated plainly here per this plan's own `<verification>` requirement: the user's choice and reasoning are recorded, `inspect_opening_completeness` implements exactly that check (presence + one hook term, NFC-normalized, no length limit), and **this check verifies hook presence only — it does not and cannot verify "why it matters," "who I am," or the other three D-07 elements.** Those elements are enforced structurally at registration time (13-01) and surface qualitatively in real play; this plan does not claim otherwise anywhere in code comments or tests.
- **13-01's scenario_id default is resolved** (by Task 2, prior to this session): `DEFAULT_SCENARIO_ID = WELL_BELOW_ID`. Documented above under key-decisions with the re-confirmed rationale.
- **AGENT_ROLES stale-acceptance-criterion deviation** (documented in key-decisions and Coverage D4): the plan's literal `== 5` check is wrong against the current codebase (actual pre-existing value: 7), independent of this plan's work. The functional guarantee — no new role added by this plan — is verified and holds.
- **13-02's D-10 premise correction was checked against this plan's scope and found not to apply** — Task 3 touches no creation-screen or StatusPane code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test naming] Renamed a test so the plan's literal `-k fallback`/`-k regenerat` verification commands actually select it**
- **Found during:** Task 3, writing `tests/test_scene_opening.py`
- **Issue:** initial test name used `falls_back` (with underscore split), which does not contain the substring `fallback` that the plan's acceptance criteria pass to `pytest -k`.
- **Fix:** renamed to `test_sketch_opening_fallback_to_authors_five_when_master_gm_provider_fails`.
- **Files modified:** `tests/test_scene_opening.py`
- **Verification:** `pytest -k fallback` and `pytest -k regenerat` both now select exactly one matching test each, per plan.
- **Committed in:** `5302984`

**2. [Rule 3 - Blocking, documented not fixed] `AGENT_ROLES == 5` acceptance criterion is stale**
- See key-decisions and Coverage D4 above. Not a code fix — the acceptance criterion text in `13-03-PLAN.md` predates two later-phase role additions (`outcome_picker`, 12-06; `creation_gm`, 12.1-03). No action needed beyond documenting it here, since the functional requirement it protects (no new role from this plan) is independently verified.

---

**Total deviations:** 1 auto-fixed (test naming), 1 documented pre-existing plan/code drift (not this plan's defect). **Impact on plan:** Neither affects correctness or scope. No AI role was added; no acceptance criterion's *functional intent* failed.

## Live Verification Evidence (AI quality note)

**What was and was not verified by the automated test suite:** the automated tests in `tests/test_scene_opening.py`/`test_situation_judge.py`/`test_narration_isolation.py` use `FakeProvider` (deterministic, canned responses) exclusively. They verify **contract and control flow** — prompt shape, isolation, retry/regeneration counting, fallback wiring, HTTP status codes — and cannot and do not verify **narrative quality or judgment** (whether a real model's opening actually reads well, actually captures "why it matters," etc.). This limitation is inherent to a fake provider, not specific to this plan.

**What was additionally verified with a real provider, in this session:** a full live HTTP run against the `verify-13-01.db` server (port 8001) using the project's actual `.gptrpg/agents.json` configuration (`nim`/`nvidia/nemotron-3-ultra-550b-a55b` for both `master_gm` and, via `ROLE_FALLBACKS`, `situation_judge`). A real 3-person party was created and its roster locked, then `POST /sessions/{id}/opening` was called with `scenario_id=well_below`. The model produced a coherent multi-paragraph Korean opening on the first attempt (no regeneration triggered), correctly naming and characterizing all four scenario cast members and containing the hook term "우물" (well) — `inspect_opening_completeness` passed without needing the D-08 regeneration path. Both `RecordAiCall` events recorded real, non-zero token counts. This is real evidence that the wiring works end-to-end against production models, not just against the fake provider — but it is a single successful run, not a systematic quality evaluation, and does not substitute for actual multi-session play observation.

## Issues Encountered

- **Known pre-existing full-suite failure, unrelated to this plan:** `tests/test_event_schema_migration.py::test_events_db_v2_records_fold_without_exception_under_schema_6` fails because the untracked local `.gptrpg/events.db` disagrees with its committed fixture. Orchestrator independently confirmed this fails identically at commit `3f7458b`, before any Phase 13 work. Not introduced or affected by this plan.

## User Setup Required

None - no external service configuration required (the local `.gptrpg/agents.json` used for live verification already existed and is untracked/local by design).

## Next Phase Readiness

- The scenario registry is complete for M0's purposes: two scenarios, both `opening_kind` values exercised, all three former hardcoding sites closed.
- `judge_opening_situation`/`inspect_opening_completeness` are in place and live-verified for `well_below`; any future third scenario of `opening_kind="sketch"` gets the same AI path with no new code.
- **13-04** (three-layer targets) can build on `build_turn_context(..., scenario=...)` — the parameter Task 2 added is now actually exercised by a real call site (Task 3's opening route), not just plumbed through.
- The two todos explicitly out of scope for this plan remain open and untouched: `.planning/todos/pending/2026-08-26-mobile-status-pane-drawer.md`, `.planning/todos/pending/2026-08-26-creation-host-transfers-on-timeout.md`.

## Self-Check: PASSED

- All modified files verified present on disk with the expected new symbols (`build_opening_situation_prompt`, `judge_opening_situation`, `inspect_opening_completeness`, `_open_sketch_scene` all grep-confirmed at exactly count 1).
- Commits `8d228e6` and `5302984` verified present in `git log --oneline`.
- Full test suite: 1453 passed, 1 pre-existing unrelated failure (documented above), 0 newly introduced failures.
- `lint-imports`: 4 contracts kept, 0 broken.
- Live HTTP run against a real provider completed successfully (session `live-verify-13-03-1787714456`, evidence above).

---
*Phase: 13-scene-opening-and-targets*
*Completed: 2026-08-26*

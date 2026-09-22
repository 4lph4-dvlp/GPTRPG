---
phase: 09-agent-architecture
verified: 2026-08-09T13:31:04Z
status: human_needed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "[carried forward from 09-04 Task 2 checkpoint, already accepted by human] 연속 다섯 턴을 더 돌려 위협 시계가 4/4(마지막 칸)에 닿는지 확인 (T-09-20 페이싱 안전그물)"
    expected: "다섯 턴 안에 시계가 마지막 칸에 닿지 않는다 — 닿으면 clock_judge 조건 판단 프롬프트가 너무 헐겁다는 신호"
    why_human: "LLM 판단의 실제 보정(calibration)은 목업 provider로 도는 단위/통합 시험이 대신할 수 없다 — 09-01의 시험은 '판단이 없으면 없는 대로 진행한다'는 계약만 증명하고, '판단 기준이 적절히 빡빡한지'는 증명하지 않는다"
  - test: "[carried forward from 09-04 Task 2 checkpoint, already accepted by human] clock_judge 역할을 존재하지 않는 모델로 바꾼 뒤 실제 살아있는 앱(CLI 또는 웹)에서 한 턴을 돌려 D-05가 실전에서도 조용히 지켜지는지 확인"
    expected: "턴이 정상적으로 끝나고 서사가 그대로 나오며, 실패 문구는 표준오류에만 뜬다"
    why_human: "09-01의 코드 수준 단위/통합 시험(FakeProvider)이 이미 이 계약을 커버하지만, '실제로 설정 파일을 실제 CLI로 돌렸을 때도' 똑같이 동작하는지는 살아있는 프로세스에서만 확인 가능하다"
  - test: "[carried forward from 09-04 Task 2 checkpoint, already accepted by human] `gptrpg replay`로 한 턴의 ai_invoked 사건을 역할별로 확인 (situation_judge/scene_entity_judge/clock_judge 세 역할 모두 나타나는지)"
    expected: "세 역할이 각각 정확히 한 번씩 기록으로 보인다"
    why_human: "replay 명령의 요약 출력이 역할별 세분화를 제공하지 않는 도구 한계 — 시험 코드 수준(test_web_actions.py/test_turn_flow_failure.py)에서는 이미 단언돼 있으므로 이 항목은 CLI 관측성 도구의 한계이지 기능 결함이 아니다"
  - test: "[carried forward from 09-04 Task 2 checkpoint, already accepted by human] 브라우저 경로에서 서사에 지시문 유출이 없는지, 시계 머리띠 표시가 튀지 않는지 육안 확인"
    expected: "서사에 진행자 지시문·시나리오 원문이 안 보이고, 시계 표시가 정상 범위에서만 움직인다"
    why_human: "육안 UX 확인 — 자동 시험(test_narration_isolation.py)이 구조적 노출면은 이미 없앴지만, 실제 브라우저 렌더링에서의 육안 검증은 별개다"
---

# Phase 9: 에이전트 구조 재편 Verification Report

**Phase Goal:** 진행자가 「상황 판단」과 「서술」로 나뉘고, 사람이 기다리지 않는 작업을
배경으로 돌리는 자리가 구조로 생기며, 어떤 에이전트가 무엇을 받는지가 코드에 명시된다
**Verified:** 2026-08-09T13:31:04Z
**Status:** human_needed (see note below — this reflects a *previously accepted, carried-forward*
checkpoint gap, not a newly discovered blocking issue)
**Re-verification:** No — initial verification

## IMPORTANT: Read this before treating `status: human_needed` as a blocker

All 5 ROADMAP success criteria are **VERIFIED** against the actual codebase with passing
automated tests (629/629, `lint-imports` 4/4, `ruff check src` clean). There are **zero new
gaps**. The `human_needed` status exists solely because 09-04-SUMMARY.md's Task 2
(`checkpoint:human-verify`, gate="blocking") was closed by an **explicit, informed human
decision** to proceed with several live-app sub-checks left unverified
("미확인 항목은 남겨두고 넘어가자") — recorded faithfully in 09-04-SUMMARY.md's
"Verification Gaps" table and in STATE.md's Blockers/Concerns. Per this verification run's
instructions, that decision is **not re-litigated or treated as a new blocking gap** — it is
re-surfaced here (per the protocol's `human_verification` slot) so it stays visible in the
phase's paper trail rather than silently disappearing. A human/orchestrator reviewing this
report should treat these four items as **already-waived, carried-forward risk**, not as new
work blocking phase completion.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 서사를 쓰는 에이전트가 진행자 지시문·규칙·시나리오 원문을 받지 않는다 | ✓ VERIFIED | `narrate()` signature is `(provider, model, facts, rulebook_display_name, stall_timeout_s)` — no `ctx`/`check_summary` param (confirmed via `inspect.signature` at HEAD). `NarrationFacts` dataclass fields: `character_state, check_summary, facts, new_entities, recent_turns, scene_entities, scene_summary` — no `clock_state` slot. `tests/test_narration_isolation.py` (6 tests, all pass) directly imports `M0_THREAT_CLOCK`/`THREAT_CAST` and asserts none of `.identity`/`.wants`/`.catastrophe`/`.segment_descriptions` nor any `_format_clock_state` output line appears in narration's assembled `system` string. |
| 2 | 배경 작업(위협 시계 조건 검사)이 사람을 안 기다리게 하고, 그 산출물도 사건으로 기록되어 재생하면 같은 상태가 나온다 | ✓ VERIFIED | `turn/clock_condition.run_clock_condition_check` is the single function both `web/routes_actions.py` (`BackgroundTasks`, post-response) and `cli/turn_flow.py` (`await` before `actor.stop()`) call. It goes through `actor.submit(AdvanceClock(trigger="condition", ...))` — the sole write path (no direct EventStore writes). `tests/test_clock_condition_web.py::test_confirm_advances_clock_via_condition_trigger_and_replays` and `::test_replayed_clock_segment_is_one_after_condition_advance`, plus `tests/test_clock_condition_cli.py::test_cli_turn_advances_clock_via_condition_trigger_after_process_exits` all pass — clock_segment==1 after `rebuild_state` replay. `EVENT_SCHEMA_VERSION` confirmed still `5` at HEAD (DP-04: existing `ClockAdvanced(trigger="condition")` reused, no new event kind, `rules_core/reducer.py` untouched). |
| 3 | 무엇을 병렬로 돌릴지 런타임에 판단하는 코드가 없다 — 의존 관계가 정적으로 박혀 있다 | ✓ VERIFIED | `turn/judgments.gather_turn_judgments` contains exactly one `asyncio.gather(...)` call with exactly 3 positional args, each an `asyncio.to_thread(...)` call, and no `if`/ternary anywhere in the function body — confirmed by direct source read and by `tests/test_parallel_judgment.py`'s `ast`-based structural tests (`test_gather_turn_judgments_body_has_no_if_or_ternary`, `test_gather_turn_judgments_has_exactly_one_gather_call_with_three_positional_args`, `test_gather_turn_judgments_all_three_gather_args_are_to_thread_calls`), all passing. A timing-overlap test (`test_three_judgments_actually_overlap_in_time`) and 4-distinct-input behavioral tests also pass. |
| 4 | 병렬 참조 수집 중 하나가 늦어도 턴이 멈추지 않는다 — 타임아웃이 있고 "없으면 없는 대로 진행"이 정상 경로다 | ✓ VERIFIED | Timeouts declared per role in `agents/invoke.py`: `CLOCK_JUDGE_TIMEOUT_S=5.0`, `SITUATION_TIMEOUT_S=15.0`, `SCENE_ENTITY_TIMEOUT_S=5.0`, all wrapped by the pre-existing `call_with_one_retry` (max 2 attempts). D-05 quiet-failure contract locked at three layers with passing tests: function layer (`tests/test_clock_judge.py`, `tests/test_scene_entity_judge.py`, `tests/test_situation_judge.py` — never-raise contracts), route layer (`tests/test_clock_condition_web.py::test_clock_judge_always_raising_still_returns_200_and_records_no_clock_event`, `::test_deep_judgment_raising_still_returns_200_and_records_no_clock_event`), CLI layer (`tests/test_clock_condition_cli.py::test_clock_judge_always_raising_still_exits_zero_with_narration_recorded`, `::test_clock_judge_failure_notice_only_on_stderr_never_stdout`). **CR-01 (provider-construction crash bypassing D-05) verified fixed** — see "Code Review Fix Verification" below. |
| 5 | 에이전트별로 무엇을 받는지가 코드에 명시되고 각자 상한이 있다 | ✓ VERIFIED | Four distinct, type-declared context value objects at HEAD: `TurnContext` (4 fields, all of them), `ClockJudgeContext` (4 fields, no character/scene-entity slot), `EntityJudgeContext` (3 fields, no clock/character-state slot), `NarrationFacts` (7 fields, no `clock_state` slot). Each enforces its own cap in `__post_init__` (`TooMuchContext`/`ContextCapExceeded`), confirmed by `tests/test_agent_context_caps.py` (16 tests, all pass) including a session-length-independence proof (doubling stored event count does not grow derived `recent_turns` counts) and a direct re-assertion that no module under `gptrpg.agents` imports `gptrpg.event_log`/`gptrpg.session_actor` (confirmed independently via `grep`, zero matches). |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/gptrpg/agents/clock_judge.py` | `ClockSignal`/`ClockConditionVerdict` + `judge_clock_signal`/`judge_clock_condition`, never-raise | ✓ VERIFIED | Present, substantive, wired into `turn/judgments.py` and `turn/clock_condition.py`; 11 unit tests pass |
| `src/gptrpg/agents/json_parsing.py` | Shared `try_parse_json_array` leaf util | ✓ VERIFIED | Present; used by `action_classifier.py`, `clock_judge.py`, `situation_judge.py`, `scene_entity_judge.py` |
| `src/gptrpg/turn/clock_condition.py` | `build_clock_judge_context`, `run_clock_condition_check` — shared web/CLI background entrypoint | ✓ VERIFIED | Present; single call site pattern confirmed in both `web/routes_actions.py` and `cli/turn_flow.py` |
| `src/gptrpg/agents/situation_judge.py` | `SituationJudgment` + `judge_situation`, absorbs GM persona/judgment instructions | ✓ VERIFIED | Present, substantive; 15 tests in `tests/test_situation_judge.py` all pass |
| `src/gptrpg/agents/scene_entity_judge.py` | `NewEntity`/`EntityJudgment` + `judge_new_entity` | ✓ VERIFIED | Present, substantive; 14 tests in `tests/test_scene_entity_judge.py` all pass |
| `src/gptrpg/turn/judgments.py` | `TurnJudgments`, `gather_turn_judgments`, `build_narration_facts`, `empty_turn_judgments` | ✓ VERIFIED | Present; single unconditional 3-coroutine `asyncio.gather`; wired into both web and CLI turn flows |
| `src/gptrpg/agents/context.py` (additions) | `ClockJudgeContext`, `NarrationFacts`, `EntityJudgeContext`, `ContextCapExceeded`, cap constants | ✓ VERIFIED | All present with `__post_init__` cap enforcement; confirmed via live `dataclasses.fields()` introspection |
| `src/gptrpg/agents/config.py` (additions) | `AGENT_ROLES` (5), `STRICT_AGENT_ROLES`, `ROLE_FALLBACKS` | ✓ VERIFIED | Confirmed live: `AGENT_ROLES=('action_classifier','master_gm','situation_judge','scene_entity_judge','clock_judge')`, `STRICT_AGENT_ROLES=('action_classifier','master_gm')`, `ROLE_FALLBACKS` maps all 3 new roles |
| `tests/test_clock_judge.py`, `tests/test_clock_condition_web.py`, `tests/test_clock_condition_cli.py`, `tests/test_situation_judge.py`, `tests/test_narration_isolation.py`, `tests/test_scene_entity_judge.py`, `tests/test_parallel_judgment.py`, `tests/test_agent_context_caps.py` | Full regression-net test suite for the four ARCH requirements | ✓ VERIFIED | All 86 tests in this group pass; full suite 629/629 passes |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `clock_judge.judge_clock_signal` | `turn.clock_condition.run_clock_condition_check` → `SessionActor.submit(AdvanceClock)` → `clock_advanced` event | Direct call chain, code-read + tests | ✓ WIRED | Confirmed by source read (`turn/clock_condition.py`) and passing replay tests |
| `web/routes_actions.confirm()`'s `background.add_task` registration | `cli/turn_flow._turn_flow`'s explicit `await` | Both call the same `run_clock_condition_check` | ✓ WIRED | CLI/web asymmetry documented in code comments; both paths tested independently and produce identical recorded events |
| `situation_judge.judge_situation` → `NarrationFacts` → `build_gm_prompt` → `narrate` | `build_narration_facts` (turn/judgments.py) | ✓ WIRED | Confirmed by source read; `build_narration_facts` assembles `scene_summary`/`facts` from `judgments.situation`, `new_entities` from `judgments.entity` |
| `prompt_assembly.build_situation_prompt` ↔ `build_gm_prompt` | Scenario content moved from the latter to the former | ✓ WIRED | `tests/test_narration_isolation.py` and `tests/test_situation_judge.py` both assert the split (exclusion in narration `system`, inclusion in situation `system`) using live scenario data, not re-typed strings |
| `turn/judgments.gather_turn_judgments` | `web/routes_actions.confirm` + `cli/turn_flow._turn_flow` | Single shared helper, no per-path duplication | ✓ WIRED | Confirmed by source read of both call sites — same function, same argument shape |

### Code Review Fix Verification (09-REVIEW.md CR-01 / CR-02)

The 09-REVIEW.md code review (2026-08-09) found 2 Critical issues. Both are claimed fixed in
commits `334aa05` and `0ab0605`. **Independently re-verified against current source (not
trusting the commit messages):**

| Finding | Claimed Fix | Verified in Source? | Notes |
|---------|-------------|----------------------|-------|
| **CR-01**: unguarded provider construction for the 3 new judgment roles could crash the turn *after* the dice roll was already recorded, violating D-05/ARCH-05 | commit `334aa05` — moved provider construction inside the existing `try/except`, falls back to `empty_turn_judgments()` | ✓ CONFIRMED | Read `web/routes_actions.py:466-510` and `cli/turn_flow.py:296-345` directly — all three `provider_resolver`/`resolve_provider` calls for `situation_judge`/`scene_entity_judge`/`clock_judge` now sit inside the same `try` block that wraps `gather_turn_judgments`; `except` sets `judgments = empty_turn_judgments()` and defensively sets `clock_provider = None`, and the downstream background-task registration is guarded with `if judgments.clock.should_check and clock_provider is not None:` in both files |
| **CR-02**: CLI reused a stale (pre-`ResolveCheck`) `TurnContext` for the 3 parallel judgments and background clock check, unlike the web path which rebuilds after resolve | commit `0ab0605` — CLI now rebuilds `ctx` after `ResolveCheck`, before it's threaded into `gather_turn_judgments`/`build_narration_facts`/`run_clock_condition_check` | ✓ CONFIRMED | Read `cli/turn_flow.py:279-295` directly — `ctx = _build_turn_context(store, args.session, args.rulebook)` now sits right after `check_summary` is computed (post-`ResolveCheck`) and before the `gather_turn_judgments` call, mirroring the web handler's rebuild placement exactly |
| **Regression check** | Both fix commits claim `uv run pytest` 629 passed, `lint-imports` 4/4, `ruff check` clean | ✓ CONFIRMED | Independently re-ran at HEAD: `uv run pytest` → 629 passed; `uv run lint-imports` → 4/4 kept; `uv run ruff check src` → all checks passed |

### Known Open Issues — Not Blocking (per explicit user decision)

The two Warnings from 09-REVIEW.md remain **intentionally unfixed**, confirmed still present
in current source:

| Finding | Status | Verified Present in Source |
|---------|--------|------------------------------|
| **WR-01**: same-process race — two concurrent background `run_clock_condition_check` calls (multi-player, near-simultaneous confirms) can both read the same `actor.state.clock_segment` before either submits, producing duplicate `clock_advanced` events at the same segment index | OPEN (by design decision) | Confirmed: `turn/clock_condition.py:91-102` reads `actor.state.clock_segment` for the upper-bound check and again for `segment_index=actor.state.clock_segment + 1`, with an `await asyncio.to_thread(judge_clock_condition, ...)` in between — no lock added |
| **WR-02**: `judge_new_entity` doesn't dedupe within a single model response — the same "new" entity name returned twice by the model both survive the existing-name filter | OPEN (by design decision) | Confirmed: `scene_entity_judge.py:111-114` filters against `ctx.scene_entities` (`existing_names`) but has no `seen`/self-dedupe set — matches the review's described gap exactly |

Both are Warning-severity (not Critical), are multi-player-concurrency/cosmetic-display edge
cases respectively, were not part of this phase's must-haves, and the user explicitly chose to
leave them as known follow-up issues rather than fix them in this phase. Not a blocker per this
verification pass.

### Minor Info Nit (not part of CR fixes, non-blocking)

`uv run ruff check src tests` reports one pre-existing F401 (unused import `Entity` in
`tests/test_agent_context_caps.py:31`, present since commit `e21b385`, 09-03 Task 3 — unrelated
to the CR-01/CR-02 fix commits). `uv run ruff check src` (source only, matching the fix commits'
own verification scope) is clean. Test-file-only lint nit, non-blocking.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|--------------|-----------------|--------------|--------|----------|
| ARCH-02 | 09-02, 09-04 | 서술이 진행자 지시문·규칙·시나리오 원문을 받지 않는다 | ✓ SATISFIED | `narrate()`/`NarrationFacts` type-level exclusion + `test_narration_isolation.py` |
| ARCH-03 | 09-01, 09-04 | 배경층이 구조로 있고 산출물이 사건으로 기록되어 재생된다 | ✓ SATISFIED | `run_clock_condition_check` + replay tests |
| ARCH-04 | 09-03, 09-04 | 병렬 실행 여부를 런타임에 판단하지 않는다 | ✓ SATISFIED | `gather_turn_judgments` ast-verified single unconditional gather |
| ARCH-05 | 09-01, 09-02, 09-03, 09-04 | 하나가 늦어도 턴이 멈추지 않는다 | ✓ SATISFIED | D-05 tests at function/route/CLI layers; CR-01 fix closes the provider-construction gap |
| ARCH-06 | 09-01, 09-02, 09-03, 09-04 | 에이전트별 문맥 + 각자 상한 | ✓ SATISFIED | 4 typed value objects, `test_agent_context_caps.py` |

**No orphaned requirements.** `REQUIREMENTS.md` maps only ARCH-02 through ARCH-06 to Phase 9
(ARCH-01 was completed in Phase 7); all 5 are claimed across the four plans' `requirements`
frontmatter and independently confirmed `[x]` in `REQUIREMENTS.md`.

### Anti-Patterns Found

None. Scanned all 14 source files touched by this phase (`agents/clock_judge.py`,
`agents/json_parsing.py`, `agents/situation_judge.py`, `agents/scene_entity_judge.py`,
`agents/context.py`, `agents/config.py`, `agents/invoke.py`, `agents/prompt_assembly.py`,
`agents/master_gm.py`, `turn/clock_condition.py`, `turn/judgments.py`,
`web/routes_actions.py`, `cli/turn_flow.py`, `cli/main.py`) for `TBD`/`FIXME`/`XXX`/`TODO`/
`HACK`/`PLACEHOLDER` — zero matches.

### Behavioral Spot-Checks / Probe Execution

Not applicable in the traditional sense — this phase's own test suite already constitutes the
behavioral evidence (ast-based structural test for ARCH-04, timing-overlap test for concurrency,
D-05 quiet-failure contract tests at three layers, replay-based state-transition tests for
ARCH-03). Ran the full suite once (`uv run pytest`, 629 passed) rather than re-running
per-must-have subsets. `uv run lint-imports` (4/4 contracts kept) and `uv run ruff check src`
(clean) independently re-run at HEAD, not merely trusted from SUMMARY.md.

### Human Verification Required (carried forward, already accepted — see note above)

These four items are copied from 09-04-SUMMARY.md's "Verification Gaps" table. They were
**already resolved by an explicit human decision to proceed** during Phase 9 execution
("미확인 항목은 남겨두고 넘어가자") and are recorded in STATE.md's Blockers/Concerns as open
follow-up risk. They are re-surfaced here per this verification pass's own frontmatter
`human_verification` slot so the phase's paper trail doesn't lose them — **not** as new
requirements blocking Phase 9's completion.

1. **5-turn threat-clock pacing probe** (T-09-20) — never run. Real open risk: whether
   `clock_judge`'s condition-judgment prompt is too loose for real play pacing.
2. **D-05 live degrade-gracefully probe** — never run against the live app (code-level tests
   already cover this at the function/route/CLI layers per 09-01).
3. **`ai_invoked` per-role replay breakdown** — blocked by a `gptrpg replay` tooling gap (no
   per-role breakdown in its summary output), not a demonstrated functional failure.
4. **Browser-path leak/clock-display checks** — explicitly not checked by the human
   ("확인 안 함"/"확인 못함").

## Gaps Summary

**Zero new gaps.** All 5 ROADMAP success criteria are structurally and behaviorally verified
against current source with a fully passing automated test suite (629/629), both Critical
code-review findings (CR-01, CR-02) are independently confirmed fixed in the current codebase
(not merely trusted from commit messages), and both Warning-severity findings (WR-01, WR-02)
are confirmed still open exactly as the user's explicit, informed decision described.

The only reason this report's `status` is `human_needed` rather than `passed` is the protocol's
mechanical rule that a non-empty `human_verification` section always routes to `human_needed`
— even when, as here, every item in that section is a previously-accepted, already-waived
checkpoint gap rather than a newly discovered one. Treat this phase as **functionally complete
for the purpose of proceeding to Phase 10**; the four carried-forward items above remain
recommended (not required) follow-up UAT work, per 09-04-SUMMARY.md's own "Next Phase
Readiness" section.

---

_Verified: 2026-08-09T13:31:04Z_
_Verifier: Claude (gsd-verifier)_

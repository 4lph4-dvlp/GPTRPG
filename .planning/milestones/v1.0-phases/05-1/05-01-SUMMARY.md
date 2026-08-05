---
phase: 05-1
plan: 01
subsystem: ai
tags: [prompt-assembly, dataclass, threat-clock, scenario-content, korean-trpg]

requires:
  - phase: 04-experiment-tool
    provides: "SessionActor auto-advance, EventStore/rebuild_state, prompt caching layout (permanent/session/turn), web poll endpoint showing clock_segment_count"

provides:
  - "src/gptrpg/rulebooks/threat_clocks.py — self-authored M0 scenario (name/identity/wants/4 segments/catastrophe + 4-member cast) as the only content source for the threat clock"
  - "ClockState widened with five defaulted scenario fields, TurnContext unchanged at 4 fields"
  - "build_turn_context wired to threat_clocks module instead of the 6-segment placeholder / EXAMPLE_SINGLE_STAT_FOE stand-in"
  - "_format_clock_state renders name/identity/wants/passed-segments/next-segment, catastrophe only once the clock fully advances"
  - "CLOCK_SEGMENT_COUNT (renamed from PLACEHOLDER_CLOCK_SEGMENT_COUNT) as the single source feeding both the prompt denominator and the web UI's clock_segment_count"
  - "Regression tests proving no observability-metric leak into the prompt and no code-level cap on clock advancement"

affects: [05-2, 05-3, 06-gate]

actuals:
  tokens: 5842
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Hand-authored scenario content lives in a rulebooks-adjacent data module (threat_clocks.py), following openquest_creatures.py's docstring convention (provenance / deliberately-omitted fields / decision references)"
    - "ClockState absorbs scenario content fields rather than TurnContext, preserving the TURN_CONTEXT_FIELD_NAMES=4 lock (D-31)"
    - "Formatter fallback-for-empty idiom extended to _format_clock_state: empty threat_name collapses to the pre-existing one-line format, byte-for-byte"

key-files:
  created:
    - src/gptrpg/rulebooks/threat_clocks.py
    - tests/test_prompt_assembly_scenario.py
  modified:
    - src/gptrpg/agents/context.py
    - src/gptrpg/turn/context.py
    - src/gptrpg/agents/prompt_assembly.py
    - src/gptrpg/web/routes_events.py
    - tests/test_session_actor_auto_advance.py

key-decisions:
  - "Split scenario authoring across Task 1 (thin one-entity/four-short-line pipe to prove the wire works) and Task 2 (full 4-member cast, trace-bearing segment descriptions) exactly as the plan structured it — two separate atomic commits with the tracer feedback gate between them"
  - "Catastrophe line is appended to _format_clock_state's output only when segment_index >= segment_count (i.e. the clock has fully advanced) — never shown early, so the AI doesn't know the ending in advance"
  - "PLACEHOLDER_CLOCK_SEGMENT_COUNT renamed to CLOCK_SEGMENT_COUNT in Task 3 only, per the plan's explicit sequencing — Task 1/2 kept the old name to avoid mixing a rename with content changes"

patterns-established:
  - "Formatter for structured game-state content (name/identity/wants/progress/next-step/conditional-ending) built entirely from f-strings, no template engine — matches the file's existing caching-safety convention"

requirements-completed: [EXP-01]

coverage:
  - id: D1
    description: "Threat clock content (name, identity, wants, 4 segment descriptions, catastrophe) flows from a new data module through ClockState -> build_turn_context -> _format_clock_state into the actual system prompt text"
    requirement: "EXP-01"
    verification:
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_scenario_name_identity_wants_appear_in_session_block"
        status: pass
    human_judgment: false
  - id: D2
    description: "Same-segment prompt caching invariant holds after scenario injection — session block is byte-identical across repeated calls in the same clock segment"
    requirement: "EXP-01"
    verification:
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_session_block_is_byte_identical_across_two_calls_in_same_segment"
        status: pass
    human_judgment: false
  - id: D3
    description: "Session block changes when the clock advances a segment; scene_entities returned by build_turn_context equals THREAT_CAST"
    requirement: "EXP-01"
    verification:
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_session_block_changes_after_clock_advances_a_segment"
        status: pass
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_build_turn_context_scene_entities_is_threat_cast"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full scenario authored: 4-member cast (1 combat-capable, 3 talk/explore-facing), 4 segment descriptions (each with a lasting trace, >=20 chars), catastrophe text, DUNGEONWORLD_LIKE_MOVES unchanged at 10"
    requirement: "EXP-01"
    verification:
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_cast_has_three_to_four_members_with_combat_and_non_combat"
        status: pass
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_all_four_segments_are_non_empty_and_reasonably_long"
        status: pass
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_catastrophe_is_non_empty"
        status: pass
  - id: D5
    description: "Content diversity and self-authorship judgment: no single-tone story, all four approaches (combat/talk/explore/persuade) viable, no borrowed IP, no scoped-out sensitive content (D-46 constraints)"
    human_judgment: true
    rationale: "Whether the scenario genuinely reads as open to multiple tones and approaches, and whether the content is appropriate for verbal-consent-only safety (M0 has no safety-tool UI), requires a human read of the actual Korean prose — not something a unit test can certify."
  - id: D6
    description: "Observability metrics (clock_advances, fails_since_clock) never leak into the assembled prompt even when failures have accumulated; the threat clock has no code-level cap past its 4 segments (D-47)"
    requirement: "EXP-01"
    verification:
      - kind: unit
        ref: "tests/test_prompt_assembly_scenario.py#test_session_block_does_not_leak_accumulated_failure_count"
        status: pass
      - kind: unit
        ref: "tests/test_session_actor_auto_advance.py#test_advancing_clock_past_segment_count_is_never_rejected"
        status: pass
    human_judgment: false
  - id: D7
    description: "CLOCK_SEGMENT_COUNT rename propagated to its only external consumer (web/routes_events.py); .importlinter contracts and full test suite still pass"
    verification:
      - kind: unit
        ref: "uv run pytest -q (397 passed)"
        status: pass
      - kind: other
        ref: "uv run lint-imports (3 kept, 0 broken)"
        status: pass
    human_judgment: false

duration: ~23min
completed: 2026-08-04
status: complete
---

# Phase 5 Plan 1: Threat Clock Scenario Content Summary

**Self-authored threat clock scenario ("우물 아래의 것" — a warped guardian spirit beneath a village well) threaded end-to-end from a new `rulebooks/threat_clocks.py` data module through `ClockState`, `build_turn_context`, and `_format_clock_state` into the actual cached system prompt, with tests proving byte-identical caching within a segment, no observability-metric leakage, and no code-level cap on clock advancement.**

## Performance

- **Duration:** ~23 min (base commit 01:05:44 KST → final task commit 01:27:50 KST)
- **Completed:** 2026-08-04
- **Tasks:** 3/3 completed
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments

- New `src/gptrpg/rulebooks/threat_clocks.py`: `THREAT_CLOCK_SEGMENT_COUNT = 4`, frozen `ThreatClockContent` dataclass, `M0_THREAT_CLOCK` instance (name/identity/wants/4 trace-bearing segment descriptions/catastrophe), and `THREAT_CAST` — a 4-member cast (촌장 담녹, 우물지기 이슬, 순찰대장 곽서리 with combat stats, 홀린 아이 나울) satisfying D-46's "every approach must be viable" requirement by composition rather than a single storyline branch.
- `ClockState` widened with five defaulted fields (`threat_name`, `threat_identity`, `threat_wants`, `segment_descriptions`, `catastrophe_text`); `TurnContext` untouched at exactly 4 fields (`TURN_CONTEXT_FIELD_NAMES` lock, D-31).
- `build_turn_context` now reads `M0_THREAT_CLOCK`/`THREAT_CAST` instead of the 6-segment placeholder and `EXAMPLE_SINGLE_STAT_FOE` single-entity stand-in.
- `_format_clock_state` exposes name/identity/wants/current-vs-total segment/passed-segment descriptions/next-segment description, appending the catastrophe line only once the clock has fully advanced (`segment_index >= segment_count`) — never spoiling the ending early. Empty `threat_name` (existing call sites with a bare `ClockState(...)`) still falls back byte-for-byte to the old one-line `"threat: 0/4"` format.
- `PLACEHOLDER_CLOCK_SEGMENT_COUNT` renamed to `CLOCK_SEGMENT_COUNT` (Task 3), propagated to its only external consumer `web/routes_events.py` — the web UI's clock denominator now reads "N/4" without touching `frontend/src/session_view.ts`.
- Two new regression tests lock in the two most safety-critical invariants of this plan: (1) accumulated check failures never change the assembled session block (T-05-02, H2/MEAS-03 measurement integrity), (2) five `AdvanceClock` submissions past the 4-segment count are all accepted with no rejection (D-47 — catastrophe is an observed endpoint, never a code-enforced one).

## Task Commits

Each task was committed atomically:

1. **Task 1: 시나리오 한 조각이 데이터에서 프롬프트 텍스트까지 한 경로로 관통한다** - `73ad444` (feat) — thin one-entity, four-short-line pipe proving the wire works end to end
2. **Task 2: 시나리오 본편을 짓는다 — 캐스트·칸 넷·파국** - `6ad8bb6` (feat) — full 4-member cast, trace-bearing segment descriptions, catastrophe
3. **Task 3: 자리표시자 이름을 정리하고 계측·상한선 경계를 테스트로 못박는다** - `82376a7` (refactor) — rename + no-leak/no-cap regression tests

**Plan metadata:** commit pending (this SUMMARY + REQUIREMENTS.md, per worktree parallel-executor protocol — STATE.md/ROADMAP.md are updated by the orchestrator after merge)

## Files Created/Modified

- `src/gptrpg/rulebooks/threat_clocks.py` - New scenario data module: segment count constant, `ThreatClockContent` dataclass, `M0_THREAT_CLOCK` instance, `THREAT_CAST` tuple
- `src/gptrpg/agents/context.py` - `ClockState` widened with five defaulted scenario-content fields
- `src/gptrpg/turn/context.py` - `build_turn_context` wired to the new scenario module; `PLACEHOLDER_CLOCK_SEGMENT_COUNT` renamed to `CLOCK_SEGMENT_COUNT`
- `src/gptrpg/agents/prompt_assembly.py` - `_format_clock_state` extended to render scenario content with progressive segment reveal and conditional catastrophe
- `src/gptrpg/web/routes_events.py` - Import/usage updated to `CLOCK_SEGMENT_COUNT`
- `tests/test_prompt_assembly_scenario.py` - New test file: 11 tests covering the data->prompt pipe, cache byte-identity, segment-change reactivity, scene_entities identity, scenario shape assertions, and metric-leak prevention
- `tests/test_session_actor_auto_advance.py` - New test: five `AdvanceClock` submissions past segment count all accepted, no code cap

## Decisions Made

- Followed the plan's explicit two-stage authoring split (Task 1 thin pipe / Task 2 full content) rather than writing the complete scenario in one commit — this kept the tracer commit small and separately verifiable before investing in full prose, and matched the plan's own task boundary.
- Catastrophe reveal condition implemented as `segment_index >= segment_count` (not `== segment_count - 1`) — this means the catastrophe text only appears once all four segment events have already occurred, consistent with "다음 칸" showing `(다음 칸 없음)` at that point and D-47's framing of catastrophe as the natural endpoint the clock reaches, not a state it announces in advance.
- Kept `character_state`'s existing default of `EXAMPLE_SINGLE_STAT_FOE.stats` unchanged per the plan's explicit instruction — this default is for the not-yet-character-selected CLI path and is unrelated to the scenario cast.

## Deviations from Plan

None — plan executed exactly as written. One documentation discrepancy noted but not a code deviation: the plan's acceptance criteria cite "Phase 4 종료 시점 402개 테스트" as the full-suite baseline (sourced from 05-RESEARCH.md, written 2026-08-03). The actual baseline at this plan's start commit (`c7923ed`) was 388 tests (`392 - 4` new tests added in Task 1), and Phase 4's own final SUMMARY (`04-06-SUMMARY.md`) records 387 passed after its last fix — not 402. This is a pre-existing staleness in Phase 4/5 documentation, not a regression introduced by this plan: the full suite went from 388 (implicit baseline) to 397 (final), a net increase of 9 new tests, zero failures throughout.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- EXP-01's code half is closed: the threat clock's 4-segment scenario content is real data and actually reaches the AI GM's system prompt (both CLI and web paths, since both share `build_turn_context`).
- `TurnContext` remains exactly 4 fields (D-31 untouched); prompt caching contract holds (byte-identical session block within a segment, verified by test); observability metrics (`clock_advances`/`fails_since_clock`) confirmed to never leak into the prompt (T-05-02/H2); no code-level cap on the threat clock (D-47).
- Remaining Phase 5 plans (character replacement for 선/호두 per D-49, verbal character-creation script per D-50, operational prep) are unaffected by and do not block on this plan's scope.
- No blockers for downstream plans or the Phase 6 gate.

---
*Phase: 05-1*
*Completed: 2026-08-04*

## Self-Check: PASSED

All created/modified files verified present on disk; all four commits (`73ad444`, `6ad8bb6`, `82376a7`, `c144480`) verified in `git log`.

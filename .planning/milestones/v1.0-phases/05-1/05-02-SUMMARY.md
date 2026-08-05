---
phase: 05-1
plan: 02
subsystem: experiment-content
tags: [character-data, verbal-script, experiment-prep, korean-trpg]

requires:
  - phase: 05-1
    plan: 01
    provides: "src/gptrpg/rulebooks/threat_clocks.py — M0_THREAT_CLOCK ('우물 아래의 것') as the scenario world bram/nari's archetypes and the script's opening question must connect to"

provides:
  - "src/gptrpg/web/characters_data.py — NEW_CHARACTER_STAT_NAMES/STAT_ARRAY/HP_BASE/HP_PER_CON constants: the single source for the new-character spec (stat array sorted [-1,0,0,1,1,2], HP = 16 + CON*2), scoped explicitly to seon/hodu only (D-49)"
  - "bram/nari CHARACTER_ARCHETYPES one-liners rewritten to connect to the 05-01 well scenario; their StatEntry values byte-for-byte unchanged"
  - "seon/hodu placeholders brought into spec conformance (seon HP 14->16, hodu INT 0->1) so the spec-conformance test is green from day one"
  - "docs/experiment/character-creation-script.md — a facilitator read-aloud script for building one non-experienced participant's character in <=30 minutes with no screen"
  - "tests/test_web_characters.py — two new regression tests: bram/nari pinned-value assertion (D-49 guard) and seon/hodu spec-conformance assertion (session-day edit guard)"

affects: [05-03, 05-04, 06-gate]

actuals:
  tokens: 4523
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "New-character spec declared as named module-level constants (NEW_CHARACTER_STAT_NAMES/STAT_ARRAY/HP_BASE/HP_PER_CON) at the top of characters_data.py so the script (Task 2) and the code (Task 1) share a single numeric source instead of two independently-typed copies drifting apart"
    - "Spec-conformance test pattern: sorted(actual six stat values) == sorted(spec array) rather than a positional match — the spec is a value pool to be placed into six slots by the participant, not a fixed per-stat assignment"
    - "Facilitator script separates read-aloud lines from parenthetical facilitator-only stage directions, matching the plan's explicit read/direction split"

key-files:
  created:
    - docs/experiment/character-creation-script.md
  modified:
    - src/gptrpg/web/characters_data.py
    - tests/test_web_characters.py

key-decisions:
  - "seon kept STR=-1/DEX=0/CON=0/INT=2/WIS=1/CHA=1 unchanged (already sorts to [-1,0,0,1,1,2]) and only its HP was fixed 14->16 — minimal edit that brings it into spec without touching flavor"
  - "hodu's INT changed 0->1 (all other stats unchanged) — smallest single-field edit that makes sorted(hodu's six stats) match sorted(NEW_CHARACTER_STAT_ARRAY); HP was already 16/16 so no HP edit needed"
  - "bram/nari's StatEntry tuples were not read-modified-written at all in this plan — only CHARACTER_ARCHETYPES two string values changed, verified by a dedicated pinned-value test asserting exact (name,current,max,depleted_effect_ref) tuples for both characters"
  - "Script's opening choice ('당신은 위험을 어떻게 마주합니까?') offers four options mapped to the four D-46 diversity approaches (combat/stealth/knowledge/persuasion) rather than re-deriving new archetypes, keeping the newcomer's recommended stat table small and traceable back to NEW_CHARACTER_STAT_ARRAY"
  - "Three of the seven design-plan.md 6.1 creative actions (②list-multi-pick, ③point-buy, ⑤roll-and-fill) are explicitly declared as 'not used by this ruleset' with a one-line substitute note, per the plan's own escape hatch for actions this ruleset doesn't use"

requirements-completed: [EXP-01, EXP-04, MEAS-06]

coverage:
  - id: D1
    description: "bram/nari StatEntry values (six stats, HP, bram's armor) are byte-for-byte unchanged from before this plan; only their CHARACTER_ARCHETYPES one-liner changed"
    requirement: "EXP-01"
    verification:
      - kind: unit
        ref: "tests/test_web_characters.py#test_bram_and_nari_stats_are_pinned_by_d49"
        status: pass
    human_judgment: false
  - id: D2
    description: "seon/hodu placeholders satisfy the new-character spec: sorted six stats == sorted(NEW_CHARACTER_STAT_ARRAY), HP == 16 + CON*2, current==max, depleted_effect_ref set"
    requirement: "EXP-01"
    verification:
      - kind: unit
        ref: "tests/test_web_characters.py#test_seon_and_hodu_placeholders_satisfy_new_character_spec"
        status: pass
    human_judgment: false
  - id: D3
    description: "New-character spec constants declared as named module-level values (NEW_CHARACTER_STAT_NAMES/STAT_ARRAY/HP_BASE/HP_PER_CON)"
    requirement: "EXP-01"
    verification:
      - kind: unit
        ref: "acceptance_criteria one-liner (uv run python -c '... assert tuple(N)==...')"
        status: pass
    human_judgment: false
  - id: D4
    description: "bram/nari's stat-count asymmetry (bram has an eighth 방어구 stat, nari does not) is preserved — the existing different-stat-counts-same-shape web test still exercises this pair"
    requirement: "EXP-01"
    verification:
      - kind: unit
        ref: "tests/test_web_characters.py#test_different_stat_counts_produce_same_shaped_response"
        status: pass
    human_judgment: false
  - id: D5
    description: "Facilitator script exists, contains the MEAS-06 attachment question verbatim once, covers all seven design-plan.md 6.1 creative actions, budgets each step in minutes summing to <=30, names all six stat abbreviations with a 'good at' sentence each, and its field-mapping table names display_name/CHARACTER_ARCHETYPES/depleted_effect_ref/dungeonworld_like.hp_depleted and scopes edits to seon/hodu only"
    requirement: "EXP-04, MEAS-06"
    verification:
      - kind: unit
        ref: "grep-based acceptance criteria: attachment question x1, ①-⑦ markers x7, six stat names x3-5 each, field-map strings x1 each, player.seon/player.hodu x1 each, scenario name '우물 아래의 것' x1"
        status: pass
  - id: D6
    description: "bram's and nari's CHARACTER_ARCHETYPES one-liners connect to the 05-01 well scenario ('우물 아래의 것') rather than the pre-scenario placeholder text, while staying consistent with each character's stat-implied approach (bram STR-highest -> combat/patrol framing, nari DEX-highest -> stealth/lockpicking framing)"
    human_judgment: true
    rationale: "Whether the new one-line archetypes genuinely read as connected to the well scenario and consistent with the underlying stats is a prose-quality judgment call, not something a unit test can certify."
  - id: D7
    description: "Full test suite (399 tests) still passes after both tasks; no regression introduced by the characters_data.py edits or the new script's absence of code changes"
    verification:
      - kind: unit
        ref: "uv run pytest -q (399 passed)"
        status: pass
    human_judgment: false

duration: ~9min
completed: 2026-08-04
status: complete
---

# Phase 5 Plan 2: Final Characters and Character-Creation Script Summary

**Bram/nari confirmed as-is per D-49 (only their one-line archetypes now point at the 05-01 well scenario), seon/hodu placeholders brought into a newly-declared numeric spec (stat array, HP formula) that the new facilitator script cites directly, and a 30-minute read-aloud character-creation script written for the two non-experienced participants with the MEAS-06 attachment question wired in verbatim.**

## Performance

- **Duration:** ~9 min (base commit 01:31:53 KST -> final task commit 01:40:35 KST)
- **Completed:** 2026-08-04
- **Tasks:** 2/2 completed
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `src/gptrpg/web/characters_data.py`: declared `NEW_CHARACTER_STAT_NAMES`, `NEW_CHARACTER_STAT_ARRAY = (2, 1, 1, 0, 0, -1)`, `NEW_CHARACTER_HP_BASE = 16`, `NEW_CHARACTER_HP_PER_CON = 2` as the single numeric source for the new-character spec, with a docstring scoping it explicitly to seon/hodu per D-49.
- Fixed seon's HP (14/14 -> 16/16, matching `16 + CON(0)*2`) and hodu's INT (0 -> 1, so `sorted(hodu's six stats) == sorted(NEW_CHARACTER_STAT_ARRAY)`) — the two smallest edits that bring both placeholders into spec conformance without touching their other flavor values.
- Rewrote `CHARACTER_ARCHETYPES["bram"]`/`["nari"]` one-liners to connect to 05-01's "우물 아래의 것" scenario, keeping each consistent with its dominant stat (bram STR-highest -> patrol/combat framing, nari DEX-highest -> stealth/lockpicking framing). Bram/nari's `StatEntry` tuples were not touched at all.
- Module docstring rewritten to state the current confirmed/placeholder split and point to this plan's script for the session-day swap procedure.
- Two new regression tests added to `tests/test_web_characters.py`: a pinned-value assertion locking bram/nari's exact stat tuples (D-49 guard — breaking this test means D-49 broke), and a spec-conformance assertion for seon/hodu that will catch any session-day hand-edit that drifts outside the declared spec.
- `docs/experiment/character-creation-script.md`: a new facilitator read-aloud script — 6 steps (who-are-you -> stat placement -> auto-calculated HP/armor -> name/appearance -> read-back -> attachment question), budgeted 5+10+3+5+2+3=28 minutes (under the 30-minute cap), covering all seven design-plan.md §6.1 creative actions (three of which this ruleset explicitly doesn't use, each noted with a one-line substitute), the MEAS-06 question verbatim with no-lead/no-paraphrase instructions, and a closing field-mapping table that scopes all session-day edits to the `seon`/`hodu` keys only.

## Task Commits

Each task was committed atomically:

1. **Task 1: 신규 캐릭터 규격을 코드 상수로 세우고 브람·나리 한 줄 소개를 시나리오 세계에 맞춘다** - `4822f27` (feat) — spec constants declared, seon/hodu placeholders fixed, bram/nari archetypes rewritten, two new tests
2. **Task 2: 비경험자용 캐릭터 만들기 구두 안내 대본을 쓴다** - `725db2b` (docs) — facilitator script written

**Plan metadata:** commit pending (this SUMMARY + REQUIREMENTS.md, per worktree parallel-executor protocol — STATE.md/ROADMAP.md are updated by the orchestrator after merge)

## Files Created/Modified

- `src/gptrpg/web/characters_data.py` - New-character spec constants added; seon HP and hodu INT fixed to satisfy the spec; bram/nari archetypes rewritten; module docstring updated to describe the confirmed/placeholder split
- `tests/test_web_characters.py` - Two new tests: `test_bram_and_nari_stats_are_pinned_by_d49`, `test_seon_and_hodu_placeholders_satisfy_new_character_spec`
- `docs/experiment/character-creation-script.md` - New facilitator script (created; directory `docs/experiment/` did not previously exist)

## Decisions Made

- Chose the smallest possible per-character edits to reach spec conformance (one field each for seon and hodu) rather than redesigning either placeholder's flavor, keeping the diff auditable against the "D-49 doesn't apply to seon/hodu, only bram/nari" boundary.
- The script's opening "how do you face danger" question offers four options mapped 1:1 to the D-46 diversity requirement (combat/stealth/knowledge/persuasion) with a recommended-but-changeable stat-placement table per option, keeping the facilitator's on-the-day cognitive load low while still letting the participant override.
- Verified `NEW_CHARACTER_STAT_ARRAY` is a value *pool* to be placed into six slots (not a fixed per-stat mapping) — the spec-conformance test uses `sorted(...)` comparison rather than positional equality, matching the plan's explicit wording ("어느 자리에 어느 값을 놓을지는 참가자가 고른다").

## Deviations from Plan

None — plan executed exactly as written. All acceptance-criteria one-liners from the plan (D-49 pinned-value check, spec-constant check, seon/hodu conformance check, stat-count asymmetry check, key/archetype non-empty check, identifier-unchanged check, `grep -c "D-49"` and `grep -c "character-creation-script.md"` counts) were run manually and passed before committing Task 1.

## Issues Encountered

None. Full test suite (399 tests) passed after each task and again after both.

## User Setup Required

None - no external service configuration required. The script itself is the artifact a human facilitator will read aloud during the actual session; no code-side setup is needed before then.

## Next Phase Readiness

- EXP-01's remaining half (선·호두 자리 규격 + 대본) is now in place, alongside 05-01's threat-clock content — all of EXP-01's stated preparation items exist.
- EXP-04's artifact (a screen-free, 30-minute character-creation script) exists and is verifiable by a human read-through.
- MEAS-06's exact question text is in the script, with the answer destination (05-03's observation log template) explicitly cited — 05-03 is expected to create that template file next.
- 05-04 (준비물 검수) still needs to manually verify the entrance screen shows all four characters in declaration order with bram/nari's new one-liners visible, and read the script aloud once to confirm the 30-minute budget holds in practice — both explicitly deferred to 05-04 by this plan's own `<verification>` section.
- No blockers for downstream plans or the Phase 6 gate.

---
*Phase: 05-1*
*Completed: 2026-08-04*

## Self-Check: PASSED

All created/modified files verified present on disk (`docs/experiment/character-creation-script.md`, `src/gptrpg/web/characters_data.py`, `tests/test_web_characters.py`, `.planning/phases/05-1/05-02-SUMMARY.md`); all three commits (`4822f27`, `725db2b`, `578a90a`) verified in `git log`.

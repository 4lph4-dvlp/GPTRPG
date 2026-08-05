---
phase: 02-two-rulebooks-one-vessel
plan: 03
subsystem: rules-core
tags: [dataclass, entities, openquest, srd, dungeonworld, d21, d20]

# Dependency graph
requires:
  - phase: 02-01
    provides: rulebooks/openquest.py (OPENQUEST_ID), rulebooks/dungeonworld_like.py (DUNGEONWORLD_LIKE_ID), rules_core module conventions (frozen dataclass + exception-on-invalid)
provides:
  - "rules_core/entities.py: Entity/StatEntry frozen dataclasses — the rulebook-neutral container for foe/NPC state (D-20, D-21)"
  - "rulebooks/openquest_creatures.py: real OpenQuest SRD goblin/skeleton stat blocks (ten stats each)"
  - "rulebooks/dungeonworld_like.py: EXAMPLE_SINGLE_STAT_FOE — a labeled self-authored one-stat example"
  - "structural proof that one-stat and ten-stat foes share one Entity class with zero rulebook branching"
affects: [02-04-interface-changes, M1 effect DSL (D7) that will interpret depleted_effect_ref]

actuals:
  tokens: 4865
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Entity/StatEntry container: frozen dataclass + __post_init__ validation replaces pydantic's extra=forbid/frozen=True strictness inside rules_core (which cannot import pydantic)"
    - "Field-set-equality test (dataclasses.fields -> exact set comparison, not subset) as a structural tripwire against future rulebook-concept creep into platform dataclasses"
    - "depleted_effect_ref is an uninterpreted reference string — platform opens the slot, rulebook/M1 D7 fills the meaning"

key-files:
  created:
    - src/gptrpg/rules_core/entities.py
    - src/gptrpg/rulebooks/openquest_creatures.py
  modified:
    - src/gptrpg/rulebooks/dungeonworld_like.py
    - tests/test_entities.py
    - LICENSES.md

key-decisions:
  - "StatEntry/Entity fields fixed at exactly four each (D-20/D-21) — no hp/damage/tag fields, no cap on stats tuple length"
  - "Negative current is valid (0 아래로 깎인 값의 뜻은 룰북이 정한다) — only max<0, empty name, empty non-None depleted_effect_ref, and duplicate stat names inside one Entity are rejected"
  - "OpenQuest goblin/skeleton stat values copied verbatim from SRD creature pages (creatures-g/creatures-s), not the main rulebook — cited in module docstring + LICENSES.md"
  - "EXAMPLE_SINGLE_STAT_FOE explicitly labeled self-authored (not from any rulebook text) to avoid the self-invented-mini-rulebook pitfall D-18 excludes"

requirements-completed: [RIG-08]

coverage:
  - id: D1
    description: "StatEntry/Entity frozen dataclasses with exactly four fields each, validated in __post_init__, raising InvalidStatEntry/InvalidEntity on bad declarations"
    requirement: "RIG-08"
    verification:
      - kind: unit
        ref: "tests/test_entities.py (18 tests covering field-set equality, frozen-ness, valid/invalid stat and entity construction)"
        status: pass
    human_judgment: false
  - id: D2
    description: "OpenQuest goblin and skeleton as Entity instances with ten SRD-accurate stats each; zero-value stats (skeleton's INT/POW/CHA/Magic Points) accepted"
    requirement: "RIG-08"
    verification:
      - kind: unit
        ref: "tests/test_entities.py::test_openquest_creatures_have_ten_stats_each, test_openquest_creatures_hit_points_and_magic_points_match_srd, test_openquest_skeleton_int_pow_cha_and_magic_points_are_zero_and_valid, test_openquest_hit_points_have_depleted_effect_ref_but_ability_scores_do_not"
        status: pass
    human_judgment: false
  - id: D3
    description: "A one-stat Dungeonworld-like example foe and ten-stat OpenQuest creatures coexist in one tuple and are summed via name lookup with zero rulebook-specific branching"
    requirement: "RIG-08"
    verification:
      - kind: unit
        ref: "tests/test_entities.py::test_example_single_stat_foe_has_exactly_one_stat, test_mixed_stat_count_entities_iterate_without_branching"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-08-01
status: complete
---

# Phase 02 Plan 03: Two-Rulebooks-One-Vessel — Entity Container Summary

**Frozen `Entity`/`StatEntry` dataclasses in `rules_core` hold both a real 10-stat OpenQuest SRD creature and a 1-stat Dungeonworld-like example with zero code branching, proving D-21's "no count limit" and D-20's "no rulebook-specific fields" as executable structure rather than prose.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-01T15:15:23Z
- **Completed:** 2026-08-01T15:40:00Z
- **Tasks:** 2
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- `StatEntry`/`Entity` frozen dataclasses with exactly four fields each (`name, current, max, depleted_effect_ref` / `entity_id, display_name, rulebook_id, stats`) — field-set-equality tests (`dataclasses.fields`, full-match not subset) lock this so any future `hp`/`damage`/`tag` field addition trips a test immediately
- Validation lives in `__post_init__` and always fails loud (`InvalidStatEntry`, `InvalidEntity`) — negative `max`, blank names, blank non-`None` `depleted_effect_ref`, and duplicate stat names inside one entity are rejected; negative/zero `current` is explicitly accepted (the ruleset decides what a negative or zero stat means)
- Real OpenQuest SRD creatures: `OPENQUEST_GOBLIN` (STR10/CON10/DEX17/SIZ7/INT11/POW10/CHA7, HP 9, MP 10, AP 2) and `OPENQUEST_SKELETON` (STR13/CON4/DEX11/SIZ11/INT0/POW0/CHA0, HP 8, MP 0, AP 2) — ten stats each, no invented numbers, sourced from the SRD creature pages (not the main rulebook)
- `EXAMPLE_SINGLE_STAT_FOE` in `dungeonworld_like.py` — a single-stat foe explicitly labeled as self-authored (not from any rulebook text), proving the vessel accepts one stat as readily as ten
- A test iterates `(goblin, skeleton, single_stat_foe)` and sums each entity's stats purely by name lookup — no `if len(stats) == 1` branch anywhere, the structural proof D-21 required

## Task Commits

Each task followed RED/GREEN (tdd="true"):

1. **Task 1: 상태값 그릇의 모양과 그 검증 (D-20, D-21)**
   - `da7b3be` (test) — failing tests for Entity/StatEntry shape
   - `feaeea0` (feat) — Entity/StatEntry implementation, tests green
2. **Task 2: 두 룰북의 적을 실제 SRD 수치로 같은 그릇에 담는다 (D-18, 성공조건 4)**
   - `a6d6274` (test) — failing tests for OpenQuest creatures + single-stat foe
   - `e5dba7f` (feat) — openquest_creatures.py, dungeonworld_like.py addition, LICENSES.md update, tests green

**Plan metadata:** committed separately after this SUMMARY

## Files Created/Modified

- `src/gptrpg/rules_core/entities.py` - `Entity`/`StatEntry` frozen dataclasses, `InvalidStatEntry`/`InvalidEntity` exceptions, field-name-set constants
- `src/gptrpg/rulebooks/openquest_creatures.py` - `OPENQUEST_GOBLIN`, `OPENQUEST_SKELETON`, `OPENQUEST_CREATURES` tuple — real SRD stat blocks
- `src/gptrpg/rulebooks/dungeonworld_like.py` - added `EXAMPLE_SINGLE_STAT_FOE` (self-authored, labeled)
- `tests/test_entities.py` - 25 tests covering both tasks' `<behavior>` lists
- `LICENSES.md` - added `openquest_creatures.py` to the CC BY 4.0 content list

## Decisions Made

- Chose frozen dataclass + `__post_init__` validation over pydantic to preserve `rules_core`'s existing constraint (typing/dataclasses/collections.abc only, enforced by `test_boundaries.py`); this reproduces pydantic's `extra="forbid", frozen=True` strictness without the dependency
- `stats` is `tuple[StatEntry, ...]`, following the existing `CheckOutcome.modifiers` convention that ordered immutable bundles inside `rules_core` are tuples, not lists
- Hit Points and Magic Points get a `depleted_effect_ref` (e.g. `"openquest.hit_points_depleted"`); the seven ability scores and Armour Points do not — this is the OpenQuest rulebook's own declaration of what "runs out," not a platform rule
- Kept stat names in the rulebook's own vocabulary (`STR`, `Hit Points`, `Magic Points`, English SRD terms; `체력` for the self-authored Dungeonworld-like example) rather than inventing a canonical cross-rulebook naming scheme

## What the platform code was tempted to add but did not (for 02-04)

This is the evidence 02-04's `02-INTERFACE-CHANGES.md` should weigh most heavily:

- **A dedicated `hp`/`current_hp`/`max_hp` field on `Entity` or `StatEntry`.** Resisted — "hit points" is just a string in `name`; a rulebook without hit points (or with three different depletable resources) needs nothing special from the platform. Doing this would have been the exact D32 violation the plan exists to prevent.
- **A cap or `max_stats` validation on the `stats` tuple.** Resisted — D-21 requires no count limit; adding any check (even a generous one like "at most 50") would silently reintroduce a limit that a future rulebook could exceed.
- **Making `max` required on `StatEntry`.** Resisted — ability scores and Armour Points have no meaningful ceiling in OpenQuest; forcing a `max` would require inventing a number the SRD never states.
- **Making `depleted_effect_ref` required (or auto-inferring it from a "this is a resource" flag).** Resisted — most stats (ability scores) never deplete in the platform's sense; forcing a reference for all of them would manufacture meaning the rulebook never declared.
- **A special "ability score" vs. "resource" subtype/enum inside `rules_core`.** Resisted — that distinction lives entirely in which stats a rulebook chooses to give a `depleted_effect_ref`; encoding it as a platform type would be layer ③ (rulebook rules) leaking into layer ① (platform).
- **Rejecting negative `current` as a general validation rule.** Resisted per D32 — "0 아래로 깎인 값의 뜻은 룰북이 정한다"; the platform only rejects structurally invalid declarations (empty name, negative max), never rulebook-meaningful values.

## Deviations from Plan

None — plan executed exactly as written. One process note: `src/gptrpg/rules_core/entities.py` and `tests/test_entities.py` already existed as **untracked** files in the working tree at the start of this execution (apparently written in an earlier, uncommitted attempt at this same plan). Their content was verified against every `<behavior>` item and `<acceptance_criteria>` grep in Task 1 before being accepted; to preserve an honest RED→GREEN commit history rather than landing pre-written code in one commit, `entities.py` was temporarily moved aside, the test suite was re-run to confirm a genuine import-error RED state, then restored for the GREEN commit. No content was altered from what was already on disk.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `Entity`/`StatEntry` are ready for 02-04's interface-changes review — the "tempted but resisted" list above is exactly what that document should scrutinize
- `depleted_effect_ref` is an open reference slot; M1's D7 effect DSL is the next thing that will give it real behavior — nothing in this plan wires it to any computation yet
- `rules_core/entities.py` has zero references to `gptrpg.rulebooks` (verified: `grep -c "gptrpg.rulebooks" src/gptrpg/rules_core/entities.py` = 0) — the vessel still doesn't know its own contents

## Self-Check: PASSED

All created files exist on disk (`src/gptrpg/rules_core/entities.py`, `src/gptrpg/rulebooks/openquest_creatures.py`, `tests/test_entities.py`, this SUMMARY.md) and all four task commits (`da7b3be`, `feaeea0`, `a6d6274`, `e5dba7f`) are present in git log.

---
*Phase: 02-two-rulebooks-one-vessel*
*Completed: 2026-08-01*

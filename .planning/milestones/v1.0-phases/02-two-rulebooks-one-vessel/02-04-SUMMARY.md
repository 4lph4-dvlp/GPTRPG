---
phase: 02-two-rulebooks-one-vessel
plan: 04
subsystem: cli
tags: [cli, rulebooks, openquest, d100, documentation, hyp-03, d-22]

# Dependency graph
requires:
  - phase: 02-01
    provides: rulebooks/openquest.py, rulebooks/dungeonworld_like.py, resolve_d100/resolve_2d6 sharing CheckOutcome
  - phase: 02-02
    provides: Modifier four types (FLAT/TARGET_SHIFT/BONUS_DICE/PUSH) via type:str, push_d100
  - phase: 02-03
    provides: Entity/StatEntry container, OpenQuest goblin/skeleton creatures
provides:
  - "cli/main.py: `roll --rulebook <id>` flag (default dungeonworld_like, imported not re-typed) — Phase 1 usage unbroken"
  - "02-INTERFACE-CHANGES.md: the single human-readable record of what platform code had to change vs. was resisted, closing D-22 / ROADMAP success criterion 5"
  - "human verdict on HYP-03 (rulebooks can be represented as data) — approved"
affects: [phase-6-hypothesis-scoring, M1-third-rulebook-onboarding]

actuals:
  tokens: 8000
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "CLI flag default sourced from the rulebook module constant (DUNGEONWORLD_LIKE_ID), never re-typed as a string literal in cli/main.py"
    - "Existing CommandRejected/SequenceConflict exception-to-exit-code path reused for unknown rulebook ids — no new exception handling added"
    - "Interface-change document written post-hoc from actual `git diff` + prior SUMMARYs, never from speculation"

key-files:
  created:
    - .planning/phases/02-two-rulebooks-one-vessel/02-INTERFACE-CHANGES.md
  modified:
    - src/gptrpg/cli/main.py
    - tests/test_cli.py

key-decisions:
  - "--target argument reused unchanged for both 2d6 (add-under) and d100 (roll-under) resolution — one help-text line disambiguates the two meanings instead of adding a second flag"
  - "_parse_modifier left with zero body changes — this plan's own CLI roundtrip test is the physical evidence that a new modifier type needs no parser change"
  - "02-INTERFACE-CHANGES.md's '참은 곳' (resisted) section is written longer and more concrete than its '고친 곳' (changed) section, per D-22's explicit priority"
  - "EVENT_SCHEMA_VERSION 1->2 bump judgment made explicit with reasoning (new required field, not just a widened Literal) and the legacy-v1 interpretation path location named"
  - "Human verdict on HYP-03: approved — the document reads as honest self-assessment, resisted-section is longer/more concrete than changed-section, and 4 limitations are disclosed undisguised"

requirements-completed: [RIG-08, HYP-03]

coverage:
  - id: D1
    description: "roll --rulebook <id> lets a user pick between dungeonworld_like and openquest from the command line; --rulebook omitted behaves exactly like Phase 1 (no regressions)"
    requirement: "RIG-08"
    verification:
      - kind: unit
        ref: "tests/test_cli.py (openquest roll+replay roundtrip, no-flag Phase 1 parity, unknown-rulebook one-line stderr + exit 1)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A new d100 modifier type (target_shift) is usable via --modifier target_shift:20:난이도 with zero changes to _parse_modifier's body"
    requirement: "RIG-08"
    verification:
      - kind: unit
        ref: "tests/test_cli.py::test_submit_roll_with_new_d100_modifier_type_needs_no_parser_change"
        status: pass
    human_judgment: false
  - id: D3
    description: "02-INTERFACE-CHANGES.md records, in one human-readable document, every file actually changed (10, cross-checked against git diff) and every place platform code was tempted to change but instead held as data (7 items), with the resisted section weighted heavier per D-22"
    requirement: "HYP-03"
    verification:
      - kind: other
        ref: "02-INTERFACE-CHANGES.md sections ①-⑥; acceptance-criteria greps (headings present, resisted-section line count > changed-section line count, EVENT_SCHEMA_VERSION section present) all pass"
        status: pass
    human_judgment: false
  - id: D4
    description: "A human read 02-INTERFACE-CHANGES.md and judged whether it honestly and legibly answers ROADMAP success criterion 5 / HYP-03 (whether the second rulebook forced platform code changes)"
    human_judgment: true
    rationale: "Success criterion 5's own wording ('명확히 기록된다') is a human-judgment predicate — no automated check can certify honesty or clarity of a self-assessment document. This is exactly Task 3's checkpoint."
    verification:
      - kind: manual_procedural
        ref: "Task 3 checkpoint:human-verify — user read the document, walked through the four-point verification (upfront admission, resisted-vs-changed concreteness/weight, per-file recurrence answers, undisguised limitations), verdict: approved"
        status: pass

duration: ~10min (tasks) + human verification pause across a session boundary
completed: 2026-08-02
status: complete
---

# Phase 02 Plan 04: Two-Rulebooks-One-Vessel — CLI Rulebook Selection + Interface Changes Record Summary

**Command-line `--rulebook` selection makes the second rulebook (OpenQuest d100) actually reachable from outside test code, and `02-INTERFACE-CHANGES.md` closes Phase 2's only remaining homework by recording — in one human-approved document — exactly which platform files had to change and, more heavily, which ones didn't.**

## Performance

- **Duration:** Task 1 ~3min, Task 2 ~5min (per commit timestamps 00:21→00:29 KST), then a human-verification checkpoint pause spanning a session boundary before Task 3's verdict was recorded.
- **Tasks:** 3 (2 auto + 1 checkpoint:human-verify)
- **Files modified:** 3 (`src/gptrpg/cli/main.py`, `tests/test_cli.py`, `.planning/phases/02-two-rulebooks-one-vessel/02-INTERFACE-CHANGES.md`)

## Accomplishments

- `roll --rulebook <id>` flag added to the CLI, defaulting to `DUNGEONWORLD_LIKE_ID` imported from `rulebooks.dungeonworld_like` (never re-typed as a string) — Phase 1's existing usage is byte-identical when the flag is omitted
- `_parse_modifier` untouched (zero body diff) — a real CLI roundtrip test (`--rulebook openquest --modifier target_shift:20:난이도`) proves a brand-new modifier type needs no parser change, the physical evidence D-22 asked for
- Unknown rulebook ids fall through the existing `CommandRejected`/`SequenceConflict` → one-line stderr + exit code 1 path — no new exception handling was added
- `02-INTERFACE-CHANGES.md` written and cross-checked against `git diff 5e025b4..HEAD -- src/ tests/ .importlinter`: 10 changed files (only `session_actor/actor.py`'s `_RESOLVERS` dispatch table recurs per future rulebook), 7 resisted-and-held-as-data items (weighted heavier per D-22), an explicit `EVENT_SCHEMA_VERSION` 1→2 judgment with reasoning, 4 honestly disclosed remaining limitations, and a self-score against all 5 Phase 2 success criteria
- **Human verdict on HYP-03: approved.** The user confirmed the document reads as honest self-assessment — the resisted section is longer and more concrete than the changed section, and the 4 limitations are disclosed plainly rather than hidden. This confirms HYP-03 ("rulebooks can be represented as data") for Phase 6's scoring input.

## Task Commits

1. **Task 1: 명령줄에서 룰북을 고른다** (tdd="true", implemented as a single combined commit — behavior + tests together, matching existing `test_cli.py` conventions rather than a strict separate RED/GREEN pair)
   - `21d827a` (feat) — `--rulebook` flag, `--target` help-text disambiguation, four new CLI tests (openquest roundtrip, no-flag parity, new-modifier-type passthrough, unknown-rulebook error)
2. **Task 2: 고친 곳과 참은 곳을 한 문서에 기록한다 (D-22)**
   - `5b119dd` (docs) — `02-INTERFACE-CHANGES.md` written and cross-checked against actual diff and prior three SUMMARYs
3. **Task 3: 사람이 기록을 읽고 이 단계의 답을 판정한다 (checkpoint:human-verify, gate="blocking")**
   - No code commit — this is the human verdict itself, recorded below and in this SUMMARY's `coverage` (D4)

**Plan metadata:** committed separately after this SUMMARY

## Files Created/Modified

- `src/gptrpg/cli/main.py` - `--rulebook` argument on the `roll` subparser (default from `rulebooks.dungeonworld_like.DUNGEONWORLD_LIKE_ID`), `--target` help-text now names both resolution methods' meaning of the value
- `tests/test_cli.py` - added: OpenQuest roll+replay roundtrip test, no-`--rulebook`-flag Phase-1-parity test, new-d100-modifier-type-needs-no-parser-change test, unknown-rulebook one-line-stderr+exit-1 test; zero existing tests changed (`git diff --stat` shows additions only)
- `.planning/phases/02-two-rulebooks-one-vessel/02-INTERFACE-CHANGES.md` - the D-22 / success-criterion-5 / HYP-03 record: one-line answer, resisted-vs-changed sections (resisted weighted heavier), `EVENT_SCHEMA_VERSION` judgment, honest remaining-limitations section, five-success-criteria self-score table

## Decisions Made

- Reused `--target` unchanged across both resolution methods rather than adding a second flag — the shared argument shape is itself evidence for success criterion 1 ("same check-request shape")
- `_parse_modifier`'s zero-diff status is treated as this plan's own physical proof of D-22's "held the line with data" claim, backed by a dedicated roundtrip test rather than just an assertion in prose
- Interface-changes document written strictly from `git diff` + the three prior plans' SUMMARY.md "changed/resisted" sections — no speculative content, verified acceptance-criteria greps (heading presence, resisted-section-longer-than-changed, `EVENT_SCHEMA_VERSION` mention) before Task 3
- `session_actor/actor.py`'s `_RESOLVERS` dispatch table is honestly classified as "limited but recurring" (not "resisted") — RESEARCH.md Pitfall 2 called this out in advance, and the document preserves that classification rather than softening it
- Human verdict (Task 3): **approved**, without requested changes to the document

## Known Stubs

None — this plan produced a CLI flag (fully wired, no placeholder behavior) and a documentation artifact (not executable code), so no stub-pattern scan applies.

## Deviations from Plan

None — plan executed exactly as written. Task 1 combined the `<behavior>` test additions and implementation into a single commit rather than plan's stated RED-then-GREEN two-commit TDD sequence; this matches the existing `test_cli.py` file's established one-commit-per-CLI-feature convention (see 01-06's precedent) and every `<behavior>` item and `<acceptance_criteria>` grep was verified passing before commit. No test was weakened or skipped to make this work.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Checkpoint Resolution (Task 3)

**Type:** checkpoint:human-verify, gate="blocking"
**What was verified:** Whether `02-INTERFACE-CHANGES.md` honestly and clearly records what platform code had to change vs. what was successfully avoided, per ROADMAP success criterion 5 and HYP-03.

**Verdict: Approved.** After a plain-language walkthrough of what to look for — does it admit changes upfront, are the "resisted temptation" examples concrete rather than vague self-praise, are remaining limitations honestly disclosed — the user confirmed the document reads as honest self-assessment: the "resisted" section is longer and more concrete than the "changed" section, and 4 limitations are disclosed at the end without being hidden.

**Consequence:** HYP-03 ("rulebooks can be represented as data") is confirmed by this record. This verdict is the input Phase 6's six-hypothesis scoring table will read for HYP-03 — no further verification of this claim is expected before Phase 6.

## Next Phase Readiness

- Phase 2 is now fully complete — all 4 plans (02-01 through 02-04) executed and summarized
- `02-INTERFACE-CHANGES.md` is the artifact Phase 6's HYP-03 scoring will read directly
- Remaining limitations flagged for future phases (all disclosed, none hidden): `_RESOLVERS` dispatch table will grow by one entry per future resolution method; `grading.py`'s `grade_for_total` body still contains the three Dungeonworld-like grade-name literals (deferred until a third rulebook forces the move); the reducer's v1-interpretation branch (`_legacy_v1_counts_as_failure`) is permanent by design (D-12), not technical debt; `NUMERIC_BAND_RULEBOOK_BANDS`' numeric-band `GradeBand` shape is proven structurally in tests only, not yet shipped as a real third rulebook
- Nothing in Phase 2 blocks Phase 3 (a full turn loop) from starting

## Self-Check: PASSED

- `src/gptrpg/cli/main.py` — FOUND
- `tests/test_cli.py` — FOUND
- `.planning/phases/02-two-rulebooks-one-vessel/02-INTERFACE-CHANGES.md` — FOUND
- `21d827a` — FOUND in git log
- `5b119dd` — FOUND in git log

---
*Phase: 02-two-rulebooks-one-vessel*
*Completed: 2026-08-02*

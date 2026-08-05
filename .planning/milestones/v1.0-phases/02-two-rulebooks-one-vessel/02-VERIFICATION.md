---
phase: 02-two-rulebooks-one-vessel
verified: 2026-08-01T16:28:35Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "문서('02-INTERFACE-CHANGES.md')의 '고친 곳' 목록이 실제 git diff와 일치한다 — commit b1281b4 added item 11 (tests/conftest.py, tests/test_event_log.py, tests/test_session_actor.py); independently re-diffed against `git diff 5e025b4..HEAD -- src/ tests/ .importlinter` (25 files total) and confirmed every single file now appears by name in the document."
  gaps_remaining: []
  regressions: []
---

# Phase 2: 두 번째 룰북을 같은 그릇에 (Two Rulebooks, One Vessel) Verification Report

**Phase Goal:** 판정 방식이 서로 다른 룰북 두 개와 그 룰북들의 적이, 플랫폼 코드를 고치지 않고 데이터로만 들어간다
**Verified:** 2026-08-01T16:28:35Z
**Status:** passed
**Re-verification:** Yes — after gap closure (previous run: 02-VERIFICATION.md, status gaps_found, 5/6, dated 2026-08-02)

## What Changed Since the Previous Run

Two items were open: one blocking gap (doc completeness) and one human-decision item (CR-01, disposition undecided). Both are now closed:

1. **Doc completeness gap** — commit `b1281b4` added item 11 to `02-INTERFACE-CHANGES.md` §3, naming `tests/conftest.py`, `tests/test_event_log.py`, `tests/test_session_actor.py` and explaining why each changed (fixture updates forced by the `EVENT_SCHEMA_VERSION` 1→2 / `miss_count`→`failure_count` changes).
2. **CR-01 human-decision item** — user decided to fix now. Commit `cfc8a47` (RED: `tests/test_session_actor.py::test_rulebook_with_incomplete_grade_bands_is_rejected_not_a_raw_traceback`), commit `a28e101` (GREEN: `except NoMatchingGradeBand` added to `session_actor/actor.py`'s `_prepare_resolve_check`), commit `b1281b4` (doc: recorded the post-checkpoint fix under `actor.py`'s existing §3 item 5, with an honest "사후 추가 수정" note).

## Independent Re-Verification (not just reading commit messages)

### 1. Doc-completeness re-check against a fresh diff

Ran `git diff --name-only 5e025b4..HEAD -- src/ tests/ .importlinter` myself (independent of the plan/summary claims) — 25 files total:

```
.importlinter, src/gptrpg/cli/main.py, src/gptrpg/event_log/replay_roller.py,
src/gptrpg/event_log/schema.py, src/gptrpg/rulebooks/__init__.py,
src/gptrpg/rulebooks/dungeonworld_like.py, src/gptrpg/rulebooks/openquest.py,
src/gptrpg/rulebooks/openquest_creatures.py, src/gptrpg/rules_core/dice.py,
src/gptrpg/rules_core/entities.py, src/gptrpg/rules_core/grading.py,
src/gptrpg/rules_core/reducer.py, src/gptrpg/rules_core/resolution.py,
src/gptrpg/rules_core/resolution_d100.py, src/gptrpg/rules_core/rulebook.py,
src/gptrpg/session_actor/actor.py, src/gptrpg/session_actor/live_roller.py,
tests/conftest.py, tests/test_cli.py, tests/test_entities.py,
tests/test_event_log.py, tests/test_grading_d100.py,
tests/test_reducer_failure_count.py, tests/test_resolution_d100.py,
tests/test_session_actor.py, tests/test_tracer_d100.py
```

Then, for each of the 25 filenames, checked it is named by basename somewhere in `02-INTERFACE-CHANGES.md` (not trusting the document's own self-report). Result: **25/25 present** (each file's basename found 1-6 times in the document — either in §3 "고친 곳", the "새로 생긴 파일" subsection, or cited as test evidence elsewhere in §②/§③/§⑤). No file in the diff scope is silently missing from the document. The previously-missing three (`tests/conftest.py`, `tests/test_event_log.py`, `tests/test_session_actor.py`) are now item 11 in §3, each with a fixed/reason/재발여부 structure matching the rest of the section.

### 2. CR-01 fix — code, test, and live reproduction

- **Code inspected directly** (`src/gptrpg/session_actor/actor.py:296-300`): a new `except NoMatchingGradeBand as exc: raise CommandRejected(...) from exc` clause now sits alongside the pre-existing `UnsupportedModifier`/`AttributeError` handlers in `_prepare_resolve_check`. This is a real behavioral change, not a doc-only fix.
- **Named regression test run directly** (not just cited from the commit message):
  ```
  uv run pytest tests/test_session_actor.py::test_rulebook_with_incomplete_grade_bands_is_rejected_not_a_raw_traceback -v
  → 1 passed in 0.19s
  ```
- **Independent live reproduction** (own script, not reusing the test file): registered a throwaway rulebook with an incomplete `GradeBand` declaration (only a `margin_at_least=0` band, no catch-all), constructed a scripted percentile roller producing `tens=9, units=9` (margin=-89, unmatched by the sole band), and submitted a real `ResolveCheck` through a real `SessionActor.submit()` call. Result: `CommandRejected` raised cleanly with a descriptive Korean message (`"룰북 'gapped_test_rulebook'의 등급 밴드 선언이 이 판정 결과를 덮지 않는다: margin=-89, is_doubles=True에 맞는 등급 밴드가 없다"`) — no raw traceback, no uncaught exception. This directly falsifies the "still crashes" hypothesis; the fix is genuine and reachable via the same registration extension point 02-REVIEW.md's CR-01 flagged.

### 3. Full regression suite, import layering, lint

| Check | Command | Result | Status |
|-------|---------|--------|--------|
| Full test suite | `uv run pytest -q` | 213 passed in 1.30s (was 212 in the previous run — +1 for the new CR-01 regression test) | PASS |
| Named CR-01 regression test | `uv run pytest tests/test_session_actor.py::test_rulebook_with_incomplete_grade_bands_is_rejected_not_a_raw_traceback -v` | 1 passed | PASS |
| Import layering contract | `uv run lint-imports` | "rules_core는 시간·무작위·파일·네트워크·비동기를 모른다 KEPT"; "cli -> session_actor -> rulebooks -> (rules_core \| event_log) KEPT"; 2 kept, 0 broken | PASS |
| Lint | `uv run ruff check .` | All checks passed! | PASS |
| Debt markers in all 25 phase-diff files | `grep -nE "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` across each file | No matches in any file | PASS |
| Working tree clean re: phase files | `git status --short` | No uncommitted changes to any phase-2 source/test/doc file | PASS |

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 2d6 등급식 룰북과 d100 롤언더 룰북이 같은 판정 요청·판정 결과 형태 위에서 돈다 | ✓ VERIFIED | Unchanged since previous run (not touched by the two fix commits) — `resolve_d100` returns `resolution.CheckOutcome` unmodified; `ResolveCheck.rulebook_id` is the only new field; `tests/test_tracer_d100.py` + `tests/test_cli.py` pass in the current 213-test run. |
| 2 | 결과 등급이 코드에 박혀 있지 않다 — 룰북이 자기 등급 집합을 선언하고, 이름 목록/수치 구간을 둘 다 받는다 | ✓ VERIFIED | Unchanged — `GradeBand` structurally unifies both; `tests/test_grading_d100.py::test_numeric_band_rulebook_passes_through_resolve_d100_without_code_change` passes. |
| 3 | 수정치 네 유형(숫자 가감/주사위 추가·제거/목표값 변경/재굴림)이 모두 표현된다 | ✓ VERIFIED | Unchanged — `FLAT`/`TARGET_SHIFT`/`BONUS_DICE`/`PUSH` all drive real computation; `tests/test_resolution_d100.py` passes in full. |
| 4 | 두 룰북의 적과 NPC가 같은 그릇에 들어간다 — 플랫폼 코드에 체력·피해·태그 개념이 없다 | ✓ VERIFIED | Unchanged — `Entity`/`StatEntry` remain exactly 4 fields each; `tests/test_entities.py` passes. |
| 5 | 두 번째 룰북을 넣으면서 플랫폼 코드를 고쳐야 했는지 아닌지가 명확히 기록된다 | ✓ VERIFIED | Gap closed: independently re-diffed 25 changed files against `02-INTERFACE-CHANGES.md` and confirmed all 25 are named (see above). Document's own self-imposed acceptance criterion now holds. |

**Score:** 6/6 (5 ROADMAP success criteria + the plan's explicit doc-completeness must-have, now all passing)

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `session_actor.actor._prepare_resolve_check` | `rulebooks.get_rulebook` → `resolution_method` → `resolve_2d6`\|`resolve_d100` | `_RESOLVERS` dict dispatch | ✓ WIRED | Unchanged from previous run — confirmed again via full suite pass. |
| `resolve_d100` grade string | `require_band(rulebook.grade_bands, grade)` → `counts_as_failure` → `reducer.failure_count` | Post-check band re-lookup in `actor.py` | ✓ WIRED | Unchanged. |
| `.importlinter` layers contract | `rules_core` ↛ `rulebooks` | Mechanical import-linter check | ✓ WIRED | Re-run: "2 kept, 0 broken". |
| CLI `roll --rulebook` | `ResolveCheck.rulebook_id` | argparse → command construction | ✓ WIRED | Unchanged. |
| `session_actor.actor._prepare_resolve_check` exception handling | `NoMatchingGradeBand` (from `grade_for_margin` inside `resolve_d100`) | try/except in `_prepare_resolve_check` | ✓ WIRED (previously ✗ NOT WIRED) | **This is the one link that changed.** Re-verified by direct code read, named-test run, and independent live reproduction (see section 2 above). No longer crashes — converts cleanly to `CommandRejected`. |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| RIG-08 | 02-01, 02-02, 02-03, 02-04 | 판정 방식이 서로 다른 룰북 두 개(2d6/d100)와 그 룰북들의 적이 코드 수정 없이 데이터로만 들어간다 | ✓ SATISFIED | SC1-4 verified above; unchanged from previous run. |
| HYP-03 | 02-01, 02-04 | 룰북을 데이터로 표현할 수 있다 (전략 가설) | ✓ SATISFIED | Previously flagged "SATISFIED WITH CAVEAT" because the record (`02-INTERFACE-CHANGES.md`) had a completeness gap and predated the CR-01 discovery. Both are now resolved and the document itself records the post-checkpoint CR-01 fix honestly (§3 item 5's "사후 추가 수정" note). The record HYP-03 rests on is now internally consistent. |

No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/gptrpg/rulebooks/openquest.py` | 41-53 (`difficulty_modifier`) | Bare `KeyError` on unknown difficulty name | Info | Pre-existing (WR-03), not wired to any CLI flag today — carried forward from previous run, not a new finding, not blocking. |
| `src/gptrpg/session_actor/actor.py` | 157, 210 | `SessionActor.state` computed but never read | Info | Pre-existing (WR-04), carried forward, not blocking. |

No debt markers (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) in any of the 25 diff-scoped files. The `NoMatchingGradeBand` gap previously listed under Anti-Patterns is now resolved (see Key Link Verification above) and removed from this list.

### Human Verification Required

None. The one previously-open human-decision item (CR-01 disposition) has been resolved by an explicit user decision (fix now), and the fix has been independently verified above — not merely accepted on the strength of the decision.

### Gaps Summary

None remaining. Both items from the previous verification run are closed:

1. The `02-INTERFACE-CHANGES.md` file-list completeness gap is closed — re-verified against a fresh, independently-run `git diff --name-only 5e025b4..HEAD -- src/ tests/ .importlinter`, confirming all 25 changed/new files are named in the document (not just the 3 that were flagged missing).
2. CR-01 (uncaught `NoMatchingGradeBand`) is fixed, not merely documented as fixed — verified via direct code inspection, a passing named regression test, and an independent live reproduction through a real `SessionActor.submit()` call that confirms the crash no longer occurs and `CommandRejected` is raised instead.

Full regression suite (213 tests), import-layering contract, and lint all pass. Phase 2's goal — two rulebooks with different resolution mechanics running through one shared vessel, with the platform/rulebook boundary honestly documented — is achieved.

---

_Verified: 2026-08-01T16:28:35Z_
_Verifier: Claude (gsd-verifier)_

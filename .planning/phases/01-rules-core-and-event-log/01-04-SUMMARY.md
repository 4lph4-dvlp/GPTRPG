---
phase: 01-rules-core-and-event-log
plan: 04
subsystem: rules-engine
tags: [grading, resolution, frozen-dataclass, hypothesis, edge-tests]

requires:
  - phase: 01-02
    provides: "Tracer cast to the end: resolve_2d6 / Modifier / CheckOutcome / Roller Protocol and grade_for_total — the judgment slice this plan widens into a complete 2d6 grade resolution with modifier origins, strict typing, and append-style reroll"
provides:
  - "Complete 2d6 grade resolution. grade_for_total boundary rule is now explicit in its docstring: >=target -> strong_hit, >=target-WEAK_HIT_BAND -> weak_hit, else miss. FLAT modifiers are summed; any non-FLAT modifier type raises UnsupportedModifier (carrying type+source) instead of being silently dropped, so a wrong total can never land in the record that Phase 6 reads."
  - "reroll_2d6(roller, previous) appends two freshly-rolled eyes to the prior rolls tuple WITHOUT erasing the originals and recomputes total/grade from only the new pair — structural prevention of the 'roll-then-overwrite' path (D-16/D-17 become code, not convention). modifiers and target are inherited verbatim from the prior outcome."
  - "Edge + property-based suite (tests/test_resolution_edges.py): five branches (boundary, adjacency, empty, ordering, integerness) under the test_edge_* prefix, with hypothesis on adjacency + integer (default example counts, no inflation). The whole suite runs <1s, keeping the regression suite at <1s — far inside the 15s budget."
affects: [01-05, 01-06, Phase 2, Phase 6]

tech-stack:
  added: []
  patterns:
    - "FLAT modifier-type constant + UnsupportedModifier(modifier_type, source): a non-FLAT type is a hard failure, never a silent skip — the wrong total that would silently enter the event log and be read by Phase 6 is structurally impossible now (T-1-09 mitigated)"
    - "reroll_2d6 computes total/grade from ONLY the new pair while concatenating new_rolls onto previous.rolls — the original eyes stay in the record, making 'roll-then-overwrite-because-I-didn't-like-it' structurally impossible (T-1-10 mitigated)"
    - "Edge tests use a tiny in-test ScriptedRoller (structurally typed via PEP 544, no Roller subclass) and leave hypothesis at default example counts; the test-only file imports only rules_core, so the import-linter boundary contract is untouched"

key-files:
  created:
    - tests/test_resolution_edges.py
  modified:
    - src/gptrpg/rules_core/grading.py
    - src/gptrpg/rules_core/resolution.py
    - tests/test_grading.py

key-decisions:
  - "Task 2 is test-only and explicitly must NOT change judgment code. All 9 edge tests passed on the first run against the Task-1 implementation — that green-on-first-contact is the blessed signal that Task 1 was correct, so no fix(01-04) was needed and grading.py/resolution.py were left untouched in Task 2."
  - "Integer-edge test asserts `type(outcome.total) is int` (exact) AND `total == eye_a + eye_b + sum(mod_values)` — it directly expresses 'no float/division/rounding can be involved' instead of approximating correctness; modifiers range to +-10000 so totals are pushed well outside 2..12 and grade_for_total is still exercised exception-free."
  - "Adjacency change-point test scans target-(WEAK_HIT_BAND+8)..target+8, comfortably wrapping both grade-change points (target and target-WEAK_HIT_BAND). It would surface off-by-one boundary drift, not just confirm the two-point claim — so it earns the 'intervals are contiguous and disjoint' wording in the plan's truths."
  - "test_grading.py (Task 1) owns the seven main behaviors; test_resolution_edges.py (Task 2) owns ONLY the corners and deliberately does not duplicate the behavior tests — per the plan's read-first guidance ('겹치지 않게 — 본 동작이 아니라 모서리만 다룬다')."

patterns-established:
  - "Two test files split by intent: behavior tests (test_grading.py) vs edge/property tests (test_resolution_edges.py). Phase 2's second resolution method can mirror this split without the two files colliding."
  - "hypothesis at default example counts is enough for structural invariants here — the full suite is 106 tests in <1s, leaving huge headroom under the 15s gate even as later plans add more."

requirements-completed: [RIG-02]

coverage:
  - id: D1
    description: "2d6 grade boundaries are locked: at target=10 the four points 6(miss)/7(weak_hit)/9(weak_hit)/10(strong_hit) are each directly asserted, and the straddle (6 vs 7, 9 vs 10) confirms the grade just below differs from the grade just above each boundary."
    requirement: "RIG-02"
    verification:
      - kind: unit
        ref: "tests/test_resolution_edges.py::test_edge_boundary_target_10_four_points"
        status: pass
      - kind: unit
        ref: "tests/test_resolution_edges.py::test_edge_boundary_straddle_points_split_grades"
        status: pass
    human_judgment: false
  - id: D2
    description: "Grade intervals are contiguous and disjoint over a generous integer range: every total maps to exactly one of the three grades with no exception, and as total rises by 1 the grade changes at exactly two points which are target and target-WEAK_HIT_BAND."
    requirement: "RIG-02"
    verification:
      - kind: unit
        ref: "tests/test_resolution_edges.py::test_edge_adjacency_every_total_maps_to_exactly_one_grade (hypothesis: target -200..200, total -50000..50000)"
        status: pass
      - kind: unit
        ref: "tests/test_resolution_edges.py::test_edge_adjacency_grade_changes_at_exactly_two_points (hypothesis: target -200..200)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Empty and single-modifier inputs resolve without exception: empty -> total == sum of two eyes and modifiers == (); single flat modifier preserved with its value and source in order."
    requirement: "RIG-02"
    verification:
      - kind: unit
        ref: "tests/test_resolution_edges.py::test_edge_empty_modifiers_yield_sum_of_eyes_and_empty_tuple, ::test_edge_empty_single_modifier_preserved_in_order"
        status: pass
    human_judgment: false
  - id: D4
    description: "Roll order is preserved: a repeated same-value list (three consecutive 6s then a 1) comes back in insertion order with no sorting, reroll APPENDS to the prior rolls with the prefix equal to the original (never overwrites), and the same eye list produces byte-identical outcomes on two runs."
    requirement: "RIG-02"
    verification:
      - kind: unit
        ref: "tests/test_resolution_edges.py::test_edge_ordering_repeated_values_preserve_insertion_order, ::test_edge_ordering_same_eyes_twice_give_identical_outcomes"
        status: pass
    human_judgment: false
  - id: D5
    description: "Integerness: total is always exactly int and equals the eyes' sum plus the flat modifiers' sum; very large positive/negative modifiers (up to +-10000) push total far outside 2..12 and grade_for_total still returns one of the three grades with no exception."
    requirement: "RIG-02"
    verification:
      - kind: unit
        ref: "tests/test_resolution_edges.py::test_edge_integer_total_is_exact_sum_of_eyes_and_flat_modifiers (hypothesis)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Task 1 behaviors: boundary main cases (incl. target-shift to 11), roll-order + flat-sum, multi-modifier value/source preservation, frozen CheckOutcome mutation rejection, reroll appends+recomputes, and UnsupportedModifier for a non-FLAT type — all green and unchanged in Task 2."
    requirement: "RIG-02"
    verification:
      - kind: unit
        ref: "tests/test_grading.py (9 tests, incl. test_check_outcome_attributes_cannot_be_reassigned, test_reroll_2d6_appends_new_rolls_and_recomputes_from_them, test_unsupported_modifier_type_raises)"
        status: pass
    human_judgment: false

duration: ~16min (resumed Task 2; Task 1 RED+GREEN were committed in an earlier pass of this phase)
completed: 2026-07-31
status: complete
---

# Phase 01-04: 2d6 Grade Resolution + Edge/Property Tests Summary

**2d6 grade resolution is now a complete first real resolution method: flat modifiers are summed with strict typing that raises UnsupportedModifier for anything non-FLAT, reroll appends (never overwrites) and recomputes from the new pair, the CheckOutcome remains frozen — and the boundary/adjacency/empty/order/integerness corners are nailed by nine edge tests that passed on the first run, confirming Task 1 was correct.**

## Performance

- **Duration:** ~16 min for the resumed Task 2 (Task 1's RED + GREEN commits predate this resume)
- **Started (this resume):** 2026-07-31T11:10:43Z
- **Completed:** 2026-07-31T11:26:47Z
- **Tasks:** 2/2 completed (Task 1 done in an earlier pass; Task 2 done here)
- **Files:** 4 (1 created by Task 2; 2 modified + 1 created by Task 1)
- **Test suite:** 106 passed (97 prior-wave + 9 new edge tests) in 0.90s — comfortably under the 15s gate.

## Accomplishments

### Task 1 — grading boundaries + modifier origins + append reroll (committed earlier)

- **grading.py:** `grade_for_total`'s docstring now states the boundary rule explicitly (>=target -> strong_hit, >=target-WEAK_HIT_BAND -> weak_hit, else miss). `DEFAULT_TARGET=10`, `WEAK_HIT_BAND=3` and the `Grade` Literal are stable from 01-02; Task 1 only fixed the rule in prose, behavior was already correct.
- **resolution.py:** added `FLAT` modifier-type constant and `UnsupportedModifier(modifier_type, source)` exception — a non-FLAT `Modifier` reaching `_flat_total` raises instead of being silently summed-as-zero or skipped, so the recorded total can never silently diverge. `resolve_2d6` rolls twice via the injected roller (preserving insertion order, no sorting), sums flat modifiers, calls `grade_for_total`, and returns a frozen `CheckOutcome`. `reroll_2d6(roller, previous)` rolls two more and builds a new `CheckOutcome` whose `rolls` is `previous.rolls + new_rolls` (append, never overwrite) and whose `total`/`grade` are recomputed from ONLY the new pair — `modifiers` and `target` are inherited from the prior outcome. No function in this module draws randomness itself; the roller is always an argument (D-15).
- **test_grading.py:** nine behavior tests (RED -> GREEN) covering the boundary main cases, target shift to 11, roll-order + flat total, multi-modifier value/source preservation, frozen-object mutation rejection, append-style reroll, and the non-FLAT exception.

### Task 2 — edge + property-based tests (this resume)

- **tests/test_resolution_edges.py:** nine `test_edge_*` tests across the five branches mandated by the plan:
  - **boundary** — `test_edge_boundary_target_10_four_points` asserts 6/7/9/10 directly; `test_edge_boundary_straddle_points_split_grades` asserts the grade just below differs from just above each of the two boundary points.
  - **adjacency (hypothesis)** — `test_edge_adjacency_every_total_maps_to_exactly_one_grade` over target -200..200 and total -50000..50000 (so totals well outside 2..12 from modifier push are covered); `test_edge_adjacency_grade_changes_at_exactly_two_points` scans a window around each target and asserts the only two change points are `target - WEAK_HIT_BAND` and `target` — i.e. the three grade intervals are contiguous and disjoint.
  - **empty** — `test_edge_empty_modifiers_yield_sum_of_eyes_and_empty_tuple` and `test_edge_empty_single_modifier_preserved_in_order` cover both the empty-list and single-modifier cases.
  - **ordering** — `test_edge_ordering_repeated_values_preserve_insertion_order` feeds `[6,6,6,1]` (three-consecutive-same-value list) and asserts rolls come back in insertion order and reroll APPENDS with the original prefix intact; `test_edge_ordering_same_eyes_twice_give_identical_outcomes` runs the same eye list twice and asserts `CheckOutcome` equality.
  - **integer (hypothesis)** — `test_edge_integer_total_is_exact_sum_of_eyes_and_flat_modifiers` draws two 1..6 eyes and up to five integer modifiers in -10000..10000, asserts `type(outcome.total) is int` and `outcome.total == eye_a + eye_b + sum(mod_values)` exactly, and that the grade is one of the three with no exception even when the total is pushed far outside 2..12.
- All nine passed on the first run — the plan's blessed signal that Task 1 was correct. No judgment code was changed.

## Task Commits

The plan's TDD split landed across three atomic commits (Task 1 RED+GREEN done earlier, Task 2 test added here):

| # | Task | Message | Hash |
|---|------|---------|------|
| 1 | Task 1 (RED) | `test(01-04): add failing tests for grading boundaries and modifier/reroll tracking` | `61a3323` |
| 2 | Task 1 (GREEN) | `feat(01-04): resolve flat modifiers with strict typing, add reroll` | `d7edf8f` |
| 3 | Task 2 (test) | `test(01-04): add edge and property-based tests for resolution` | `436b54d` |

## Files Created/Modified

- `src/gptrpg/rules_core/grading.py` (Task 1) — boundary rule made explicit in the `grade_for_total` docstring
- `src/gptrpg/rules_core/resolution.py` (Task 1) — `FLAT`, `UnsupportedModifier`, `_flat_total`, completed `resolve_2d6`, new `reroll_2d6` (+51/-2)
- `tests/test_grading.py` (Task 1) — 9 behavior tests (+94)
- `tests/test_resolution_edges.py` (Task 2) — 9 edge/property tests across 5 branches (+171)

## Decisions Made

- **No Task-1 defect needed a fix.** The plan explicitly states Task 2 tests must not change judgment code, and that an edge test failing would be a signal to fix `grading.py`/`resolution.py` with a one-line note. The nine edge tests passed on the first run, so Task 1 was correct and no `fix(01-04)` commit was made. This is the plan's explicitly blessed outcome, not a skip.
- **`type(outcome.total) is int` (exact identity) over `isinstance`** in the integer test, to directly express "no float/division/rounding is involved" — a `bool` cannot reach `total` here anyway, so identity is the cleanest statement of integerness.
- **Adherence to the plan's test-name artifact list.** Branches use `test_edge_boundary_*`, `test_edge_adjacency_*`, `test_edge_empty_*`, `test_edge_ordering_*`. The plan's artifact table named the integerness branch `test_edge_precision_*`; this summary's branch uses `test_edge_integer_*` to match the behavior section's "정수성" (integerness) literally and the resume spec's "integer" — same branch, clearer name, still under the mandated `test_edge_` prefix.

## Deviations from Plan

None that change behavior. Two minor, documented choices (no judgment code touched):
- **`test_edge_integer_*` naming** (see Decisions above) — the plan's artifact table wrote `test_edge_precision_*` for the integerness branch; the behavior section calls it "정수성" and the resume spec says "integer". Both satisfy the mandated `test_edge_` prefix and the success criterion "hypothesis on adjacency+integer".
- **Resume split.** Task 1's RED+GREEN commits were produced in an earlier pass of this phase and verified intact at the start of this resume (`uv run pytest tests/test_grading.py -x` -> 9 passed); this resume executed only Task 2 and the SUMMARY.

## Auth Gates

None — no authentication surfaces in this plan (pure rules-core only).

## Known Stubs

None. The plan produces real resolution behavior and real edge tests; no placeholder text, empty wired data, or unimplemented branches were introduced. `UnsupportedModifier` deliberately does not handle non-FLAT types — that is correct behavior (the plan's `<objective>` scope note: only FLAT is computed this wave, the other three modifier types land in Phase 2 / RIG-08), not a stub.

## Threat Flags

None new. Task 2 is test-only and adds no trust-boundary surface. The plan's threat register (T-1-02/09/10/11) is fully mitigated by Task 1's code, verified by the green test suite.

## Next Phase Readiness

- The 2d6 grade-resolution method is now a real, complete first resolution method — Phase 2's test of "did adding a second resolution method force platform-code changes?" has its first method as the substance to compare against.
- `CheckOutcome` (frozen, with `rolls`/`modifiers`/`target`/`grade`) is the shape `check_resolved` events copy verbatim (01-03's schema already locks those field names); reroll now appends rather than overwrites, so a `check_resolved` with multiple roll pairs is a real, recordable shape.
- The test split (behavior vs edge/property) is established for Phase 2's second method to mirror.
- Baseline held for downstream plans: `uv run pytest` (106 passed, 0.90s), `uv run lint-imports` (2 kept, 0 broken), `uv run ruff check .` (clean).

---
*Phase: 01-rules-core-and-event-log*
*Completed: 2026-07-31*

## Self-Check: PASSED

All 5 plan files verified present on disk (`tests/test_resolution_edges.py`, `grading.py`, `resolution.py`, `tests/test_grading.py`, and this SUMMARY); all three 01-04 commits (`61a3323`, `d7edf8f`, `436b54d`) verified present in `git log --oneline --all`; `uv run pytest tests/test_resolution_edges.py -q` re-verified green (9 passed) after the Task-2 commit. Full regression baseline re-verified at SUMMARY time: `uv run pytest` (106 passed, 0.90s), `uv run lint-imports` (2 kept, 0 broken), `uv run ruff check .` (clean).

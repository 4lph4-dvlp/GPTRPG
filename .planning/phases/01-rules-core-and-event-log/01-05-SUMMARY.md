---
phase: 01-rules-core-and-event-log
plan: 05
subsystem: testing
tags: [event-log, reverse-verification, pytest, D-11, MEAS-01, MEAS-02, MEAS-03, MEAS-04]

requires:
  - phase: 01-02
    provides: "caused_by_seq envelope field (option-a) — the causal pointer this plan's ③④ latency assertions and adjacent-seq-vs-causal comparison depend on"
  - phase: 01-03
    provides: "The six locked event types (action_declared, action_confirmed, check_resolved, narration_appended, clock_advanced, ai_invoked) and their required fields — this plan's fixture and assertions use these names verbatim without renaming"
provides:
  - "fake_session_log pytest fixture (tests/conftest.py): a fabricated, fully-formed 14-event session covering all six event types, two players interleaved at seq 0-3 (declare/declare/confirm/confirm) to make adjacent-seq pairing provably wrong, one 4-roll reroll, one narration split into chunk 0/1, one clock advance, two ai_invoked calls with distinct roles/models — appended to and read back from a real EventStore, with a fixed base timestamp so recorded_at never depends on wall-clock time."
  - "tests/test_reverse_verification.py: nine tests proving all six MEAS numbers (D-11) are derivable from event-log data alone — token spend, turn count, declare->confirm latency, confirm->narration latency, failure/clock counts, and (raw_text, suggestion, confirmed) triples — each a separate assertion with a number-naming failure message, plus a causal-vs-adjacent-seq comparison test and an integer-ms-only type assertion."
affects: [Phase 4, Phase 6]

actuals:
  tokens: 5668
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Reverse-verification gate: before building real aggregation code (Phase 4), fabricate one complete session and prove every number the eventual killer-criteria decision (Phase 6) needs can be derived from the event log alone. A number that can't be derived here is a missing schema field caught before two irrecoverable week-apart M0 sessions run, not after."
    - "Causal-vs-adjacent-seq differential test: instead of just asserting the causal-paired latency values, the test also computes the same latencies via 'previous seq' pairing and asserts the two lists differ — proving caused_by_seq does real work in a fixture built so multiple players' events interleave in seq order."

key-files:
  created:
    - tests/test_reverse_verification.py
  modified:
    - tests/conftest.py

key-decisions:
  - "caused_by_seq already existed from 01-02 (option-a) and schema.py already carried every field needed to compute all six numbers — the plan's schema-fix branch (bump EVENT_SCHEMA_VERSION, widen 01-03's schema tests) was not needed. All nine tests passed on the first run, which is the correct/expected outcome per the plan's own note that this fixture was built specifically to satisfy these assertions."
  - "_ms_diff lives only in tests/test_reverse_verification.py (not in src/), per the plan's explicit instruction that this is Phase 4's aggregation-code slot, not a library concern yet."
  - "Resume note: this plan was executed as a resume after a prior executor attempt crashed on an upstream 429 rate-limit mid-Task-2, before any commit. Task 1's fixture (tests/conftest.py) survived uncommitted in the working tree from that crashed attempt; it was read and independently re-verified against every Task 1 acceptance criterion (round-trip through a real EventStore, all six event types with required counts, seq 0-3 interleaving, one 4-roll reroll, fixed base timestamp) before being committed as-is — no defects found, no rewrite needed. Task 2's file (tests/test_reverse_verification.py) was corrupted garbage from the same crash (a scrambled _ms_diff referencing undefined names, an invalid isinstance(e, GameEvent) check, zero of the six required assertions) and was discarded and rewritten from scratch."

patterns-established:
  - "Six-numbers-as-six-assertions: each MEAS-01~04 (D-11) number gets its own test function with a number-naming failure message (①~⑥), so a single missing/broken field fails loudly and specifically instead of silently passing or failing an unrelated-looking assertion."

requirements-completed: [RIG-06]

coverage:
  - id: D1
    description: "fake_session_log fixture appends a fabricated 14-event session (all six event types, two players interleaved at seq 0-3, one 4-roll reroll, narration split chunk 0/1, one clock advance, two distinct ai_invoked calls) through a real EventStore and reads it back — not an in-memory object list."
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_reverse_verification.py::test_fixture_round_trips_a_complete_session_through_the_store"
        status: pass
    human_judgment: false
  - id: D2
    description: "① Real token spend: sum of ai_invoked.prompt_tokens + completion_tokens across all such events is > 0 and equals the fixture's expected total (330)."
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_reverse_verification.py::test_reverse_verification_token_spend"
        status: pass
    human_judgment: false
  - id: D3
    description: "② Real turn count: count of action_declared events equals the fixture's expected count (3) and is > 1."
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_reverse_verification.py::test_reverse_verification_turn_count"
        status: pass
    human_judgment: false
  - id: D4
    description: "③ Declare -> confirm latency: each action_confirmed is paired with the action_declared its caused_by_seq points to, ms-diff computed and equal to the fixture's expected values ([250,250,250]); a second test proves pairing by adjacent seq instead of the causal field yields a DIFFERENT (wrong) result, since the fixture interleaves two players at seq 0-3."
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_reverse_verification.py::test_reverse_verification_declare_confirm_latency_ms, ::test_causal_pairing_differs_from_adjacent_seq_pairing"
        status: pass
    human_judgment: false
  - id: D5
    description: "④ Confirm -> narration-first-token latency: for narration_appended where chunk_index == 0 only, paired via caused_by_seq to its action_confirmed, ms-diff equals the fixture's expected value ([1700])."
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_reverse_verification.py::test_reverse_verification_confirm_narration_latency_ms"
        status: pass
    human_judgment: false
  - id: D6
    description: "⑤ Check-failure count and clock-advance count: check_resolved events with grade == miss count to the fixture's expected value (2); clock_advanced events count to the fixture's expected value (1) — each with its own naming failure message."
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_reverse_verification.py::test_reverse_verification_failure_and_clock_counts"
        status: pass
    human_judgment: false
  - id: D7
    description: "⑥ (raw_text, system_suggestion, player_confirmed) triples: every action_declared.raw_text is non-empty, every action_confirmed.system_suggestion is non-empty and player_confirmed is a bool; the actual triple list is built by pairing declared<->confirmed via caused_by_seq and its length equals turn_count (3)."
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_reverse_verification.py::test_reverse_verification_declared_suggestion_confirmation_triples"
        status: pass
    human_judgment: false
  - id: D8
    description: "The ms-diff helper's return type is exactly int (no float/rounding path exists) — final assertion after all six numbers."
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_reverse_verification.py::test_ms_diff_returns_int"
        status: pass
    human_judgment: false

duration: ~20min (resume after 429 crash; Task 1 predates this session)
completed: 2026-08-01
status: complete
---

# Phase 01-05: Reverse-Verification Gate (D-11) Summary

**Nine pytest assertions prove all six Phase-6 killer-criteria numbers (real token spend, real turn count, two response-latency measurements paired by the causal field rather than seq adjacency, failure/clock counts, and the (raw_text, suggestion, confirmed) triples) are derivable from a single fabricated event-log session round-tripped through a real EventStore.**

## Performance

- **Duration:** ~20 min (this resume; Task 1's fixture predates this session and was inherited uncommitted from a crashed prior attempt)
- **Started:** 2026-08-01 (this resume)
- **Completed:** 2026-08-01
- **Tasks:** 2/2 completed
- **Files modified:** 2 (`tests/conftest.py` modified, `tests/test_reverse_verification.py` created)

## Accomplishments

- **Task 1 (verified, not rewritten):** `fake_session_log` fixture in `tests/conftest.py` — a fabricated 14-event session with all six event types, two players interleaved at seq 0-3 (p1 declare / p2 declare / p1 confirm / p2 confirm) so that adjacent-seq pairing is provably wrong, one check with a 4-roll reroll, one narration split into chunk 0 and chunk 1, one clock advance, two `ai_invoked` calls with distinct roles/models and non-zero tokens. Appends every event through a real `EventStore` and reads them back via `read_events` — never returns the in-memory object list directly. Uses a fixed base timestamp (`2026-01-01T00:00:00.000Z` + millisecond offsets), so `recorded_at` never depends on wall-clock time.
- **Task 2 (rewritten from scratch):** `tests/test_reverse_verification.py` — nine tests: one fixture round-trip check, six tests each proving one of D-11's numbered measurements, one differential test proving causal pairing differs from (and is correct instead of) adjacent-seq pairing, and one final test proving the ms-diff helper's return type is exactly `int`.
- All nine tests passed on the first run — expected, since the fixture was purpose-built to satisfy these assertions and `caused_by_seq` already existed from 01-02 (option-a). No schema change was needed.

## Task Commits

Each task was committed atomically:

1. **Task 1: fake_session_log fixture** - `ff58282` (feat) — Task 1's work was inherited uncommitted from a crashed prior attempt; verified sound against every Task 1 acceptance criterion before committing as-is.
2. **Task 2: six-number reverse-verification assertions** - `43ecb80` (test) — file was corrupted garbage from the same crash; discarded and rewritten from scratch per the Task 2 spec.

**Plan metadata:** (this commit, see below)

_Note: this plan is `type="auto"` for Task 1 (verify+commit) and `type="auto" tdd="true"` for Task 2; the plan's own TDD note anticipates immediate green since the fixture was built to satisfy the assertions, which is what happened._

## Files Created/Modified

- `tests/conftest.py` — adds `fake_session_log` fixture, `FakeSession` frozen dataclass, `_make_fake_events`, `_env`, `_t` helpers (+230 lines; inherited from crashed attempt, verified sound, committed unchanged)
- `tests/test_reverse_verification.py` — nine tests + `_ms_diff`, `_by_seq`, `_find_caused_by` helpers (+298 lines; written fresh this session)

## Decisions Made

- **Verified rather than blindly trusted Task 1's inherited fixture.** Read `tests/conftest.py` in full and cross-checked every Task 1 acceptance criterion from `01-05-PLAN.md` (fixture-only `pytest -k fixture -x` returns 0, all six event types present with required counts, seq 0-3 interleaving, 4-roll reroll present, chunk_index 0 and 1 both present, store round-trip, deterministic `recorded_at`). All satisfied — no defect found, no rewrite performed.
- **caused_by_seq already existed (01-02 option-a) — no schema-fix branch triggered.** The plan's Task 2 has two conditional escape hatches: (a) if a number can't be produced, fix `schema.py` and bump `EVENT_SCHEMA_VERSION`; (b) if `caused_by_seq` doesn't exist at all, stop and report to the user rather than redesigning the schema. Neither applied — `caused_by_seq` is a locked envelope field since 01-02, and all six numbers were producible with the existing schema.
- **`_ms_diff` kept test-file-local**, per the plan's explicit instruction that this is Phase 4's aggregation-code slot, not a library concern to build now.
- **`_SIX_TYPES` tuple pattern reused from conftest.py's own workaround** instead of `isinstance(e, GameEvent)` — `GameEvent` is `Annotated[Union[...]]` and cannot be used with `isinstance`; the corrupted prior version of this file used the invalid pattern, which was corrected in the rewrite.

## Deviations from Plan

None — plan executed exactly as written, no auto-fixes needed, no architectural changes, no schema changes.

### Resume Context (not a deviation, documented per objective instructions)

A prior executor attempt on this plan crashed on an upstream 429 rate-limit mid-Task-2, before any commit landed. On resume:
- `tests/conftest.py` (Task 1's fixture) survived uncommitted in the working tree and was verified sound — kept as-is, committed unchanged.
- `tests/test_reverse_verification.py` (Task 2's file) was untracked and corrupted: a scrambled `_ms_diff` helper referencing undefined `events`/`delta` names in its body, and a single leftover round-trip test using the invalid `isinstance(e, GameEvent)` pattern. It contained zero of Task 2's six required numbered assertions. This file's contents were discarded entirely and rewritten from scratch per the Task 2 specification.

---

**Total deviations:** 0 auto-fixed
**Impact on plan:** None — resume proceeded cleanly with no forced fixes.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None. All six numbers are computed from real fixture data through real assertions; no placeholder values or unwired data paths were introduced.

## Threat Flags

None new. This plan's own threat register (T-1-12, T-1-13, T-1-03) is the mitigation target and is fully addressed:
- **T-1-12** (loosening assertions to force green): not applicable — all nine assertions passed honestly on the fixture's real computed values, none were loosened.
- **T-1-13** (adjacent-seq vs causal pairing): directly mitigated by `test_causal_pairing_differs_from_adjacent_seq_pairing`.
- **T-1-03** (fixture's store round-trip): directly mitigated — `fake_session_log` appends through a real `EventStore` and reads back via `read_events`, verified by `test_fixture_round_trips_a_complete_session_through_the_store`.

## Next Phase Readiness

- **D-11's gate is now closed.** All six MEAS-01~04 numbers (D-11's list) are proven derivable from event-log data alone, before any real M0 experiment session runs — the plan's entire purpose (catching a missing field before an irrecoverable week-apart session, not after).
- **Phase 4's aggregation code has a proven blueprint.** The six assertions and the `_ms_diff` helper in this test file are, per the plan's objective, "Phase 4's aggregation feature effectively half-built" — Phase 4 can lift this logic into real library code with the causal-pairing approach already validated.
- **Phase 6 can rely on `caused_by_seq`.** The causal-vs-adjacent-seq differential test is now a permanent regression guard: if a future change silently breaks causal pairing, this test catches it before Phase 6's real killer-criteria computation runs on real session data.
- Full regression baseline held: `uv run pytest` (115 passed), `uv run lint-imports` (2 kept, 0 broken), `uv run ruff check .` (clean).

---
*Phase: 01-rules-core-and-event-log*
*Completed: 2026-08-01*

## Self-Check: PASSED

Both files verified present on disk (`tests/conftest.py`, `tests/test_reverse_verification.py`); both 01-05 commits (`ff58282`, `43ecb80`) verified present in `git log --oneline --all`. Full regression re-verified at SUMMARY time: `uv run pytest tests/test_reverse_verification.py -x` (9 passed), `uv run pytest -q` (115 passed), `uv run lint-imports` (2 kept, 0 broken), `uv run ruff check .` (clean).

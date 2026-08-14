---
phase: 10-ai
reviewed: 2026-08-14T00:00:00Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - src/gptrpg/agents/action_classifier.py
  - src/gptrpg/agents/json_parsing.py
  - src/gptrpg/agents/master_gm.py
  - src/gptrpg/agents/narration_guard.py
  - src/gptrpg/agents/prompt_assembly.py
  - src/gptrpg/cli/main.py
  - src/gptrpg/cli/turn_flow.py
  - src/gptrpg/event_log/schema.py
  - src/gptrpg/rules_core/reducer.py
  - src/gptrpg/session_actor/actor.py
  - src/gptrpg/turn/context.py
  - src/gptrpg/web/routes_actions.py
  - tests/test_action_classifier.py
  - tests/test_adversarial_fence.py
  - tests/test_agents_retry.py
  - tests/test_cli.py
  - tests/test_clock_condition_cli.py
  - tests/test_clock_condition_web.py
  - tests/test_event_schema_migration.py
  - tests/test_master_gm.py
  - tests/test_narration_guard.py
  - tests/test_narration_isolation.py
  - tests/test_prompt_assembly_scenario.py
  - tests/test_providers.py
  - tests/test_safety_flag_pipeline.py
  - tests/test_turn_flow_failure.py
  - tests/test_turn_tracer.py
  - tests/test_web_actions.py
findings:
  critical: 0
  warning: 3
  info: 0
  total: 3
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-08-14T00:00:00Z
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

## Summary

Read `10-CONTEXT.md` first and judged the diff against its locked decisions (D-01 through
D-12), so deliberate choices — output-only filtering (D-09), `character_break`/
`corrupted_glyph` passing through as `flagged` (D-03), the `EVENT_SCHEMA_VERSION` staying at 6
for the new `corrupted_glyph` reason value (D-04 note in `schema.py`), the max-3-stream-call
contract (`MAX_ATTEMPTS=2` + one regeneration) — are **not** flagged as defects here; they are
exactly what the phase intended and the accompanying test suite (`test_master_gm.py`,
`test_safety_flag_pipeline.py`, `test_adversarial_fence.py`, `test_event_schema_migration.py`)
locks each of them in with a dedicated regression test.

I traced the streaming/retry/regeneration state machine in `master_gm.narrate()` end to end
(the `for _attempt in range(MAX_ATTEMPTS)` loop, `_drive()`, `_consume_narration_stream()`,
`_drain_with_stall_timeout()`, and the regeneration branch) against the documented "3 stream
calls max" and "stall is never retried" invariants that trace back to the real 22-minute-hang
incident. I did not find a path where retries and regeneration compound, and the CLI/web
mirrored submission loops (`_submit_narration_chunk`) stay in lockstep. I also verified the
`EVENT_SCHEMA_VERSION`-stays-6 reasoning explicitly: `rules_core/reducer.py`'s `safety_flagged`
branch ignores `reason` entirely, and `session_actor/actor.py`'s `_VALID_SAFETY_FLAG_REASONS`
is the only place `reason` is validated (a write-time check, not a read-time schema
constraint) — so the reasoning holds and I am not raising it as a defect.

What I did find are three data-integrity/robustness gaps, none of which cause an incorrect
`blocked`/`flagged` decision or a player-visible leak, but all of which degrade the operator
telemetry the phase exists to provide (T-10-03's whole purpose is "count how many times this
leaked" — these findings make the numbers behind that count untrustworthy in specific cases) or
leave a safety-relevant constant unenforced. No `critical` findings.

## Warnings

### WR-01: `MAX_REGENERATIONS` constant is declared but never enforced

**File:** `src/gptrpg/agents/master_gm.py:42`
**Issue:** `MAX_REGENERATIONS = 1` is introduced by this phase with an elaborate docstring
explaining that it is what pins the per-turn provider-stream-call ceiling to 3 (2 normal-path
attempts + 1 regeneration) — directly referencing the 22-minute hang incident this phase is
guarding against. However, the constant is never read anywhere in the function body. The
"exactly one regeneration" behavior is achieved purely *structurally*, by having a single
`if blocked_avoid_text is not None: ... _drive(regen_messages, ...)` block with no loop, not by
checking a counter against `MAX_REGENERATIONS`. Grep confirms the only occurrences of the name
outside its own declaration are in comments/docstrings:
```
$ grep -n MAX_REGENERATIONS src/gptrpg/agents/master_gm.py
42:MAX_REGENERATIONS = 1
399:    일어난다(`MAX_REGENERATIONS`).**  ...
520:    #         (MAX_REGENERATIONS) ----
```
This means the constant currently documents a guarantee it does not enforce. If a future change
turns the regeneration block into a loop (e.g. "let's try regenerating twice for hard cases"),
nothing in the code will stop it from silently exceeding the 3-call ceiling this exact constant
claims to protect — reintroducing the class of bug that caused the original incident, with no
test or runtime check catching it, only a comment that nobody re-reads.
**Fix:** Either wire the constant into an actual guard (e.g. a `for _regen in range(MAX_REGENERATIONS):` loop, even though it currently only executes once, so a future change to the loop bound is the only way to change the behavior — making intent and enforcement the same line), or remove the constant and let the docstring reference the structural fact directly ("this block runs exactly once because it is not a loop") instead of a name that implies runtime enforcement it doesn't have.

### WR-02: `matched_len` can exceed `subject_len` for `source_overlap`, corrupting the operator-facing severity metrics

**File:** `src/gptrpg/agents/narration_guard.py:142-185` (`find_source_overlap`), consumed at
`narration_guard.py:258` (`subject_len = len(sentence)`) and reported via
`master_gm.py:206-212` (stderr excerpt) and `event_log/schema.py:249-286` (`SafetyFlagged`
event fields, permanently recorded).
**Issue:** `subject_len` is documented and computed as `len(sentence)` — the *current* held
sentence only. But `find_source_overlap` builds `joined = h + n` where `n` is the *next*
sentence's normalized text, and the matched window's `end` is allowed to extend past `len(h)`
into `n` (this is intentional — it's exactly how D-01's "leak spans a sentence boundary" case
gets caught). The reported `matched_len` is `end - start` over this joined text, so when most of
the matched overlap comes from `next_sentence` rather than `sentence`, `matched_len` can be
**larger than `subject_len`** — i.e. the recorded event claims more characters matched than the
sentence being judged actually contains. Reproduced directly against the real `build_gm_prompt`
permanent block:
```
$ python3 -c "... (see below) ..."
hit True matched_len 40 raw subject_len(sentence) 1
verdict.disposition blocked matched_len 40 subject_len 1
```
(constructed by putting 1 char of a 40-char source run into `sentence` and the remaining 39
into `next_sentence` — a realistic shape for a leak that starts at the very end of one streamed
sentence and continues into the next). This value pair (`matched_len=40, subject_len=1`) is what
gets permanently written to the `safety_flagged` event (`event_log/schema.py`'s
`SafetyFlagged.matched_len`/`subject_len`) and to the stderr line in `master_gm._judge_sentence`
(`겹친글자수={verdict.matched_len} 문장길이={verdict.subject_len}` — "chars matched" bigger than
"sentence length" reads as nonsensical to an operator debugging a leak). T-10-03 and D-04 exist
specifically so these numeric fields can be used later (explicitly cross-referenced for Phase 14
reporting) to gauge leak severity — a metric that can silently exceed its own denominator
undermines that goal. The same `_judge_sentence` stderr excerpt (`sentence[:STDERR_EXCERPT_CHARS]`,
`master_gm.py:206`) compounds this: it only ever slices `sentence`, so when the bulk of a
cross-boundary leak lives in `next_sentence`, the printed "발췌" doesn't actually show the
matched text at all.
**Fix:** Either (a) redefine `subject_len` for the `source_overlap` reason to reflect the actual
matched span (`len(sentence) + len(next_sentence or "")` when the match extends past the
sentence, or simply report the joined length), or (b) cap `matched_len` at `min(matched_len,
subject_len)` when populating `GuardVerdict` for `source_overlap` and document that cross-boundary
matches are truncated to the current sentence's contribution for reporting purposes. Either way,
add a regression test asserting `matched_len <= subject_len` (or an explicit alternate invariant)
for the cross-sentence-boundary case that `test_find_source_overlap_across_sentence_boundary_is_blocked`
already exercises but doesn't currently check this relationship for.

### WR-03: `SafetyFlagged`/`RecordSafetyFlag` never cross-validates `source` against `reason`

**File:** `src/gptrpg/event_log/schema.py:271-275` (`SafetyFlagged.source`/`reason` Literals),
`src/gptrpg/session_actor/actor.py:213-217` (`_VALID_SAFETY_FLAG_SOURCES`/
`_VALID_SAFETY_FLAG_REASONS`), `src/gptrpg/session_actor/actor.py:741-766`
(`_prepare_safety_flag`)
**Issue:** `source` (`"narration" | "classifier"`) and `reason` (`"think_block" |
"source_overlap" | "character_break" | "unknown_move" | "corrupted_glyph"`) are validated
independently, both in the pydantic `Literal`s on `SafetyFlagged` and in `_prepare_safety_flag`'s
membership checks. Nothing rejects a nonsensical combination such as
`source="classifier", reason="think_block"` or `source="narration", reason="unknown_move"` — in
reality only `source="classifier"` pairs with `reason="unknown_move"`, and `source="narration"`
pairs with the other four reasons; that invariant lives only in the two call sites
(`action_classifier.py`/`narration_guard.py` wiring), not in the schema or the actor's
validation. This is exactly the kind of state/schema consistency the phase's focus area calls
out (narration_guard.py ↔ event_log/schema.py ↔ session_actor/actor.py). Today it causes no
observable bug because both call sites happen to be correct, but there is no guard rail if a
future change (e.g. adding a new reason to one source's vocabulary without updating the other)
introduces a silently-wrong combination into the permanent, append-only event log — and unlike
most other validation in this file (see `CheckResolved._require_identity_from_schema_5`), there
is no `model_validator` doing this cross-check.
**Fix:** Add a `model_validator(mode="after")` on `SafetyFlagged` (mirroring the pattern already
used by `CheckResolved`) that asserts `reason == "unknown_move"` iff `source == "classifier"`,
and mirror the same check in `SessionActor._prepare_safety_flag` so a bad command is rejected
before it can reach `_store.append(...)`.

---

_Reviewed: 2026-08-14T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

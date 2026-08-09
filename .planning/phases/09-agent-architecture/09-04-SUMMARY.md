---
phase: 09-agent-architecture
plan: 04
subsystem: docs
tags: [documentation, decision-record, roadmap, pipeline-docs, human-verify-checkpoint]

# Dependency graph
requires:
  - phase: 09-agent-architecture (plan 01)
    provides: clock_judge agent role, turn/clock_condition.run_clock_condition_check, five-role AGENT_ROLES/ROLE_FALLBACKS
  - phase: 09-agent-architecture (plan 02)
    provides: situation_judge/narrate() split, NarrationFacts, turn/judgments.gather_turn_judgments (two-coroutine start)
  - phase: 09-agent-architecture (plan 03)
    provides: scene_entity_judge as gather_turn_judgments's third coroutine, ARCH-04/06 regression nets
provides:
  - "D-68 decision record in PROJECT.md's Key Decisions table, in D-63's four-column pattern: CLOCK-01 minimum pulled from Phase 15 into Phase 9, relationship-ledger (MEM-02) and context-compaction (MEM-03) rolled back to Phase 14 including their minimum slices"
  - "ROADMAP.md Phase 15's Depends-on + success criterion 1 resynced to assume the condition-check minimum already exists; Phase 14 section left byte-identical"
  - "docs/PIPELINE.md resynced with actual Phase 9 code: layer diagram, A-2 confirm-flow steps, prompt-assembly (5 functions, system-prompt scenario removal), CLI/web background-execution asymmetry"
  - "README.md agent-setup step documents five roles, ROLE_FALLBACKS stderr notice, and per-role `agents set --role` usage"
  - "A checkpoint:human-verify (gate=blocking) resolved by explicit human decision to proceed with known, named verification gaps rather than a clean pass — recorded here rather than papered over"
affects: [phase-14-relationship-memory-context-compaction, phase-15-clock-confirmation-screen, future-uat-passes]

actuals:
  tokens: 7299
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Checkpoint resolution with partial/waived verification: when a human explicitly chooses to proceed past unfinished how-to-verify sub-checks (rather than approving cleanly or rejecting), the SUMMARY must record each unresolved sub-check individually with its own risk note, not summarize the checkpoint as a pass or a fail"

key-files:
  created: []
  modified:
    - .planning/PROJECT.md
    - .planning/ROADMAP.md
    - docs/PIPELINE.md
    - README.md
    - .planning/STATE.md

key-decisions:
  - "D-68: CLOCK-01's minimum (threat-clock condition check) stays pulled forward into Phase 9 as the background layer's first content; the relationship-ledger (MEM-02) and context-compaction (MEM-03) work — including their own minimum slices — is rolled all the way back to Phase 14, unchanged from 09-CONTEXT.md's D-01"
  - "Human explicitly accepted the Task 2 checkpoint with five of its six how-to-verify sub-checks only partially run or entirely skipped (checks 2/3/4-②③/5), instructing the executor to leave them unverified and move the plan forward rather than re-running them or blocking on them"

patterns-established: []

requirements-completed: [ARCH-02, ARCH-03, ARCH-04, ARCH-05, ARCH-06]

coverage:
  - id: D1
    description: "D-01's pull-forward decision and its two-reason rationale recorded in PROJECT.md's Key Decisions table in D-63's four-column pattern (decision/rationale/impact)"
    requirement: ARCH-02
    verification:
      - kind: other
        ref: "grep -c \"D-68\" .planning/PROJECT.md (returns 2)"
        status: pass
    human_judgment: false
  - id: D2
    description: "ROADMAP.md Phase 15 resynced to assume the condition-check minimum exists; git diff on ROADMAP.md touches only the Phase 15 section, Phase 14 untouched"
    verification:
      - kind: other
        ref: "git show 57f2670 -- .planning/ROADMAP.md (diff confined to ### Phase 15)"
        status: pass
    human_judgment: false
  - id: D3
    description: "docs/PIPELINE.md resynced with real code: situation_judge/scene_entity_judge/clock_judge/gather_turn_judgments/run_clock_condition_check all present and traceable to src"
    verification:
      - kind: other
        ref: "for n in situation_judge scene_entity_judge clock_judge gather_turn_judgments run_clock_condition_check; do grep -q \"$n\" docs/PIPELINE.md || echo MISSING $n; done (empty output)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A human actually ran a turn end-to-end (CLI + browser) and confirmed the pipeline restructuring did not break play — but ONLY partially: checks 0/1/4-① passed by direct inspection, checks 2 (role-level replay breakdown), 3 (five-turn clock-runaway probe), 4-②③ (browser leak/clock-tick check), and 5 (D-05 live degrade-gracefully probe) were explicitly left unverified by the human's own informed choice ('미확인 항목은 남겨두고 넘어가자')"
    requirement: ARCH-03
    verification: []
    human_judgment: true
    rationale: "This is a checkpoint the human deliberately resolved with known gaps rather than a full pass. Automation cannot substitute for the human's judgment call to accept those gaps, and the gaps themselves (esp. clock-runaway pacing and D-05 live degrade-gracefully) are exactly the kind of play-feel/safety judgment this checkpoint existed to catch — a future verifier must see this as an open item, not a proven one."
    coverage_note: "See '## Verification Gaps (Task 2 checkpoint)' below for the itemized list."

duration: ~15min active work (Task 1 already committed in a prior session; this session resolves the Task 2 checkpoint and closes the plan)
completed: 2026-08-09
status: complete
---

# Phase 9 Plan 4: Decision Record, Pipeline Docs Resync, Human-Verified Turn Summary

**D-68 recorded in PROJECT.md (CLOCK-01 minimum pulled into Phase 9, relationship-ledger/context-compaction rolled back to Phase 14), docs/PIPELINE.md and README.md resynced with the actual five-role agent architecture, and the plan's blocking human-verify checkpoint closed by an explicit, only-partially-verified human decision to proceed.**

## Performance

- **Duration:** ~15 min active work this session (Task 1's doc/decision work was committed in a prior session; this session's work is resolving and recording the Task 2 checkpoint outcome)
- **Completed:** 2026-08-09
- **Tasks:** 2/2
- **Files modified:** 5 (`.planning/PROJECT.md`, `.planning/ROADMAP.md`, `docs/PIPELINE.md`, `README.md`, `.planning/STATE.md`)

## Accomplishments

- `D-68` added to `PROJECT.md`'s Key Decisions table in `D-63`'s four-column pattern: the CLOCK-01 minimum (threat-clock condition check) stays pulled into Phase 9 as the background layer's first content; the relationship-ledger (MEM-02) and context-compaction (MEM-03) work — including their own minimum slices — is rolled all the way back to Phase 14. Rationale carries both of `09-CONTEXT.md` D-01's reasons (document-trail tolerance for staged consistency loss vs. the greater risk of stacking unverified change into one step — the exact failure mode of Session 1) and the schema-reuse fact (`EVENT_SCHEMA_VERSION` stayed at 5 because `ClockAdvanced(trigger="condition")` was reusable)
- `.planning/PROJECT.md`'s `Last updated:` line rolled forward, prior entry preserved after "이전 기록:" per the file's existing convention
- `ROADMAP.md`'s `### Phase 15` section resynced — Depends-on now names the condition-check judgment function, background lane, and auto-fire `AdvanceClock(trigger="condition")` path as already existing; success criterion 1 gained a parenthetical noting Phase 9 already built the minimum and Phase 15's remaining job is the confirm screen + "why it fired" display. `### Phase 14` section is untouched (verified by `git diff` scope)
- `docs/PIPELINE.md` resynced with the actual code: the A-2 confirm-flow steps now show the three-judgment `asyncio.gather`, `NarrationFacts` assembly, and the conditional background clock-check lane; §5 documents five prompt-assembly functions and the removal of scenario content from the narration `system` prompt; §7 documents the CLI/web background-execution asymmetry (`BackgroundTasks` post-response on web vs. explicit `await` before `actor.stop()` on CLI); §1's layer diagram gained the three new agent modules plus `turn/clock_condition.py` and `turn/judgments.py`; §9-A/§9-B updated with what Phase 9 closed (GM-instruction/scenario leak path into narration) and what it still leaves open (situation-judge summary as a residual leak path Phase 10 must close)
- `README.md`'s agent-setup step now documents five roles, the `ROLE_FALLBACKS` stderr notice for unset new roles, and `gptrpg agents set --role <role> --provider <name> --model <id>` for per-role configuration
- **Task 2's `checkpoint:human-verify` (gate="blocking") resolved** — see "Verification Gaps" below for the accurate, non-papered-over accounting of what was and was not actually confirmed

## Task Commits

1. **Task 1: 결정과 파이프라인을 문서에 남긴다** - `57f2670` (docs) — D-68 recorded, ROADMAP Phase 15 resynced (Phase 14 untouched), `docs/PIPELINE.md`/`README.md` resynced with real code
2. **Task 2: 사람이 실제로 한 턴을 돌려 확인한다** - checkpoint, no code commit (human-verify tasks produce no diff of their own); resolved this session by explicit human decision to proceed with the gaps below left open

**Plan metadata:** this commit (docs: complete 09-04 plan)

## Files Created/Modified

- `.planning/PROJECT.md` - `D-68` Key Decisions row, `D-64`/`D-66` structure-filled note, `Last updated:` rolled forward
- `.planning/ROADMAP.md` - `### Phase 15` Depends-on + success criterion 1 + closing note resynced; `### Phase 14` untouched
- `docs/PIPELINE.md` - §1 layer diagram, §2 A-2 confirm flow, §5 prompt assembly, §7 CLI path, §9-A/§9-B resynced with Phase 9's actual code
- `README.md` - agent setup step: five roles, fallback notice, `agents set --role` usage
- `.planning/STATE.md` - plan pointer advanced, checkpoint-resolution decision recorded, two open follow-up risks flagged

## Decisions Made

See `key-decisions` in frontmatter. Two decisions this plan is responsible for recording/making:

1. **D-68** (documentation of a decision already made in `09-CONTEXT.md` D-01, not newly decided here) — recorded in `PROJECT.md` per the plan's Task 1 action item.
2. **Checkpoint resolution decision** (made by the human this session, not by the executor) — the human ran checks 0, 1, and 4-① of Task 2's six how-to-verify sub-checks, found them passing, and explicitly instructed the executor to leave the remaining items (2 partial, 3 unrun, 4-②③ unrun, 5 unrun) unverified and close the plan: **"미확인 항목은 남겨두고 넘어가자"** ("let's leave the unverified items as-is and move on"). This is recorded as a deliberate, informed decision to accept named open risk — not as a clean pass.

## Deviations from Plan

None in the Rule 1-4 sense (no bug fixes, no missing-critical additions, no blocking fixes, no architectural changes were needed to close this plan). The only deviation from a "textbook" plan close is procedural: Task 2's checkpoint was resolved with **partial verification by explicit human choice**, rather than either a clean "승인" or a rejection requiring rework. That is not a deviation from the plan's rules — the plan's own `<resume-signal>` explicitly anticipates a non-approval response ("위 다섯 항목 중 어긋난 것을 구체적으로 알려 주세요") — but it is a deviation from the *default* clean-pass framing, and is called out here so it is not mistaken for one.

## Verification Gaps (Task 2 checkpoint)

Task 2 ("사람이 실제로 한 턴을 돌려 확인한다") specified six how-to-verify sub-checks (numbered 0–5 in `09-04-PLAN.md`). The human ran some fully, some partially, and explicitly skipped others, then instructed the executor to close the checkpoint anyway. Recorded faithfully, item by item:

| # | Check | Status | Note |
|---|-------|--------|------|
| 0 | 역할 설정 확인 (`agents show`, 5 roles + fallback stderr notices) | **PASS** | Ran; all 5 roles shown, fallback notices for situation_judge/scene_entity_judge/clock_judge appeared on stderr as designed |
| 1 | CLI 한 턴 (roll-before-narration order, natural Korean, no instruction leak, no failure phrase on stdout) | **PASS (by transcript inspection)** | Ran and transcript inspected; all four criteria held on inspection. Human did not separately narrate an explicit pass/fail verdict for this step, so this is inspection-based confirmation rather than a human-stated judgment call — noted here for accuracy |
| 2 | 사건 기록 확인 — `ai_invoked` events show situation_judge/scene_entity_judge/clock_judge individually | **UNVERIFIED (tooling gap)** | `gptrpg replay` was run, but its summary output only exposes aggregate counts (사건 수, 턴 수, AI 호출 수, 시계 칸/진행 횟수) — it does not break `ai_invoked` down by role name, so the check as literally specified could not be confirmed via this command's output. This is a CLI observability gap, not a demonstrated functional failure. Recommend `replay` gain a per-role `ai_invoked` breakdown as a follow-up |
| 3 | 시계 폭주 검사 — 5 more turns, must not reach 4/4 | **UNVERIFIED — NOT RUN** | Explicitly skipped by human decision. This is the plan's own designated safety net for an over-loose clock-judgment prompt (T-09-20 in the plan's threat register: "자동 시험으로는 잡히지 않는 종류라 Task 2의 사람 확인 3)단계가 유일한 그물이다"). Real open risk — pacing could break in actual play if the judge is too eager. **Recommended as a required follow-up UAT item before relying on this pacing in a longer session** |
| 4-① | 브라우저 경로 — 체감 지연 (parallel judgment gather doesn't add noticeable latency) | **PASS** | Human explicitly reported no noticeable added latency over a full declare→confirm HTTP turn |
| 4-② | 브라우저 경로 — 서사 지시문 유출 여부 | **UNVERIFIED — NOT CHECKED** | Human explicitly reported "확인 안 함" |
| 4-③ | 브라우저 경로 — 시계 머리띠 표시 이상 유무 | **UNVERIFIED — NOT CHECKED** | Human explicitly reported "확인 못함" |
| 5 | 판단이 죽었을 때 (`clock_judge`를 존재하지 않는 모델로 바꾸고 한 턴 — D-05 end-to-end degrade) | **UNVERIFIED — NOT RUN** | Explicitly skipped by human decision. This is the most safety-critical of the skipped checks — it's the only *live, running-app* confirmation of the D-05 quiet-failure contract; `09-01`'s unit/integration test suite already covers this at the code level (function/route/CLI layers, per `09-01-SUMMARY.md`'s D2 coverage entry), so this gap is redundant-but-not-worthless rather than a first-time-untested claim, but it is still a real gap in the "the whole running system degrades gracefully" claim |

**Human's resume decision:** "미확인 항목은 남겨두고 넘어가자" — an explicit, informed instruction to close this checkpoint and proceed with items 2 (partial/tooling-limited), 3, 4-②③, and 5 left open. This is recorded here so the gap is visible to future work, not silently lost. Items 3 and 5 in particular are flagged in `STATE.md` as open follow-up risks worth a dedicated future UAT pass — they do not block Phase 9's completion (the human explicitly waived them), but they are real, named, unresolved risk.

## Issues Encountered

**`gptrpg replay`'s summary output has no per-role breakdown of `ai_invoked` events.** This blocked check 2 from being confirmed as literally specified in the plan. Not a bug introduced by this plan — the `replay` command's aggregate-only summary predates Phase 9 — but Phase 9 is the first plan whose verification actually needed a role-level breakdown, so it's surfaced here as a concrete tooling gap for a future small fix (not in this plan's scope to fix; `docs/PIPELINE.md`/`replay` improvements are not among this plan's `files_modified`).

## User Setup Required

None beyond what `09-04-PLAN.md`'s `user_setup` block already described (choosing providers/models for the three new roles via `gptrpg agents select` or `agents set --role`) — this is an operator action outside the executor's scope, already documented in `README.md` per Task 1.

## Next Phase Readiness

- Phase 9 is complete: ARCH-02 through ARCH-06 are all `[x]` in `REQUIREMENTS.md`, and the decision trail (`D-68`) is in place for Phase 14/15 to read before they start.
- **Phase 15** can now start from "the condition-check minimum already exists" — its `Depends on` and success criterion 1 in `ROADMAP.md` reflect that; its remaining scope is CLOCK-02~05 (confirm screen + "why it fired" display + the rest of CLOCK-01's observability).
- **Phase 14** is unaffected — its section in `ROADMAP.md` was not touched, matching `09-CONTEXT.md`'s explicit instruction that Phase 14's scope not be edited to fit this plan's outcome.
- **Two open, named risks carried forward from Task 2's checkpoint (not phase-blocking, but should be picked up before this pacing/failure-mode is trusted in longer sessions):**
  1. Clock-pacing runaway risk (check 3, never run) — whether five turns can push the threat clock to its last segment (4/4), which would indicate the `clock_judge` condition-judgment prompt is too loose.
  2. D-05 live degrade-gracefully risk (check 5, never run) — whether the running app (not just its test suite) actually degrades silently to stderr-only when `clock_judge`'s configured model doesn't exist.
- No blockers to closing Phase 9. `EVENT_SCHEMA_VERSION` remains 5; no schema-migration risk carried forward.

---
*Phase: 09-agent-architecture*
*Completed: 2026-08-09*

## Self-Check: PASSED (with recorded verification gaps — see above)

Files verified present on disk: `.planning/PROJECT.md` (contains `D-68`, grep count 2), `.planning/ROADMAP.md` (Phase 15 section resynced, Phase 14 untouched per `git show 57f2670`), `docs/PIPELINE.md` (all five required symbol names present), `README.md` (agent setup step updated), this SUMMARY.md. Commit `57f2670` verified present in `git log`. Task 2 produced no independent commit (checkpoint-only task); its resolution is recorded above and in `.planning/STATE.md` rather than as a self-check pass/fail, since the checkpoint itself was closed with explicit, human-accepted open items rather than a full pass.

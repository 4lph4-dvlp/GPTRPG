---
phase: 05-1
plan: 03
subsystem: experiment-ops
tags: [operational-docs, korean-trpg, hand-filled-forms, openrouter-free-tier]

requires:
  - phase: 05-1
    provides: "05-01's M0_THREAT_CLOCK scenario (\"우물 아래의 것\") and 4-member cast, used as the worked example in the recap template and the dry-run smoke test"

provides:
  - "docs/experiment/observation-log-template.md — session-meta block, participant table (pseudonym-only), MEAS-06 attachment-question rows, single tagged (몰입/마찰/억지/사고) in-session note table, intervention self-check, session-close block with subjective completion criteria (D-53)"
  - "docs/experiment/session-recap-template.md — 3-5 sentence recap rule, the four mandatory MEAS-05 elements, blank template + a filled example set in 05-01's scenario, session-2 continuation-check procedure"
  - "docs/experiment/dry-run-checklist.md — seven-item pre-session checklist covering model/key verification, scenario-in-prompt smoke test with an isolated GPTRPG_DB, OpenRouter free-tier daily-limit arithmetic (20 RPM / 50 vs 1000 RPD / ~80 calls per session), first live 90s stall-watchdog check, reasoning-response spot check, report-file confirmation, and a materials checklist"
  - "README.md 실험 준비물 section linking all four docs/experiment/ documents (character-creation-script, observation-log-template, session-recap-template, dry-run-checklist)"

affects: [05-04, 05-05, 05-06, 06-gate]

actuals:
  tokens: 3500
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Hand-filled experiment paperwork lives under docs/experiment/, one file per artifact, each self-contained enough to print and use without cross-referencing code"
    - "Single tagged table over separate per-category tables for in-session note-taking — avoids the hand-hesitation cost of picking which table to write in mid-session (established for the observation log, applies to any future live-note UI)"

key-files:
  created:
    - docs/experiment/observation-log-template.md
    - docs/experiment/session-recap-template.md
    - docs/experiment/dry-run-checklist.md
  modified:
    - README.md

key-decisions:
  - "Used 05-01's actual scenario content (\"우물 아래의 것\", 촌장 담녹/우물지기 이슬/순찰대장 곽서리/홀린 아이 나울) for both the recap template's worked example and the dry-run checklist's smoke-test description, rather than inventing placeholder content — keeps the docs concretely checkable against what the code actually generates"
  - "Dry-run checklist's rate-limit math (80 calls/session vs 50 RPD ceiling) is stated as arithmetic derived from the plan's own figures (40 actions x 2 calls), not re-researched — 05-RESEARCH.md's Common Pitfall #2 is the sole source, carried forward verbatim with the same 2026-08-03 snapshot caveat"

patterns-established:
  - "Session-close judgment calls (completion vs. petered-out) are recorded as a value + a mandatory one-line justification, never a bare checkbox — keeps subjective calls auditable without pretending they're objective (D-53)"

requirements-completed: [EXP-02, EXP-03, MEAS-05, MEAS-06]

coverage:
  - id: D1
    description: "Observation log template exists with session-meta block, 4-row participant table (pseudonym-only, no real names/contact/affiliation fields), the exact MEAS-06 attachment question printed verbatim with an answer row per participant, a single 몰입/마찰/억지/사고 tagged note table, an intervention self-check block, and a session-close block with completion judgment + one-line rationale + no-fixed-time-threshold statement (D-53)"
    requirement: "EXP-02"
    verification:
      - kind: other
        ref: "grep -c '당신 캐릭터 어떤 사람이에요?' docs/experiment/observation-log-template.md (=1) && grep -c '몰입\\|마찰\\|억지\\|사고' docs/experiment/observation-log-template.md (=4)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Observation log has a completion/petered-out judgment field and one-line rationale field, with the no-preset-time-threshold statement present, satisfying EXP-03's 'record whether the session was completed' requirement"
    requirement: "EXP-03"
    verification: []
    human_judgment: true
    rationale: "Whether the wording of the completion-judgment block actually reads as usable mid-session under time pressure (not just grep-present) requires a human to skim the filled-form ergonomics, not a unit test."
  - id: D3
    description: "Session recap template: 3-5 sentence rule stated, all four mandatory elements (progress/clock-N-of-4/unresolved threats/next intents) individually enumerated, blank template plus a filled example set in 05-01's actual scenario (3-5 sentences, scenario name present), explicit M0-out-of-scope statement for auto-generation, and a session-2 continuation-check procedure"
    requirement: "MEAS-05"
    verification:
      - kind: other
        ref: "grep -c '3~5' docs/experiment/session-recap-template.md (=3); manual count of the filled example = 4 sentences"
        status: pass
    human_judgment: false
  - id: D4
    description: "Dry-run checklist contains all seven items (①-⑦), the three command strings (agents show / gptrpg report / OPENROUTER_API_KEY), the four required numbers (20/50/1000/80) for the daily-limit math, an isolated-GPTRPG_DB instruction for the dry run, a 90-second watchdog check with a retry-guidance response, the 2026-08-03 snapshot date plus a re-check-before-each-session instruction, and the D-58 caveat (free model muddies H1 attribution, H5 unaffected)"
    requirement: "MEAS-06"
    verification:
      - kind: other
        ref: "grep checks in execution transcript: agents show(1), gptrpg report(2), OPENROUTER_API_KEY(2), 20 RPM/50 RPD/1000 RPD/80회(all present), GPTRPG_DB(2), 2026-08-03(3), 90초(3), D-58(1)"
        status: pass
    human_judgment: false
  - id: D5
    description: "README.md has a new 실험 준비물 section linking all four docs/experiment/ files without restating the실험 당일 실행 절차 commands"
    verification:
      - kind: other
        ref: "grep -c 'docs/experiment/' README.md (=4, one row per document)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full pytest suite regression check (this plan touches no code)"
    verification:
      - kind: unit
        ref: "uv run pytest -q (397 passed)"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-08-04
status: complete
---

# Phase 5 Plan 3: 실험 준비물 3종(관찰 기록·리캡·드라이런) + README 연결 Summary

**Three hand-filled experiment documents (observation log, session recap, dry-run checklist) and a README section linking them — the paper half of EXP-02/03 and MEAS-05/06 that Phase 5's code changes cannot supply.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-08-04
- **Tasks:** 3/3 completed
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments

- `docs/experiment/observation-log-template.md`: a single-page, hand-filled-per-session form — session meta, 4-row participant table (pseudonym-only, no name/contact/affiliation fields), MEAS-06 attachment-question rows with the exact "당신 캐릭터 어떤 사람이에요?" wording, a single 몰입/마찰/억지/사고-tagged note table (deliberately not split by category, to avoid hesitation mid-session), an intervention self-check block (H1 contamination tracking), and a session-close block requiring both a completion/petered-out call and a one-line rationale (D-53 — no preset time threshold).
- `docs/experiment/session-recap-template.md`: the 3-5-sentence recap rule, the four elements a recap must carry (progress / clock N-of-4 + its trace / unresolved threats / each player's next intent), an explicit statement that auto-generation is out of M0 scope (citing ROADMAP/PROJECT.md), a blank template, and a filled 4-sentence example set in 05-01's actual scenario ("우물 아래의 것", 이슬/나울/곽서리/담녹) so the observer can calibrate tone and length against something real.
- `docs/experiment/dry-run-checklist.md`: seven checklist items, each phrased as "type this → pass if you see this → otherwise do this." Item ③ carries the arithmetic core of D-58's operational-risk caveat: ~80 AI calls per session against a 50-request/day ceiling for accounts with <$10 lifetime OpenRouter spend (vs. 1000/day at ≥$10), sourced from 05-RESEARCH.md's Pitfall #2 and restated with a 2026-08-03 snapshot warning to re-check before each of the two sessions. Item ④ turns Phase 3's skipped stream-stall-watchdog verification into this dry run's first live check.
- README.md gained a new "실험 준비물" section (placed before "실험 당일 실행 절차") linking all four `docs/experiment/` documents — including 05-02's `character-creation-script.md`, which this plan does not create but does link — without duplicating any of the실행 절차 commands.
- Full pytest suite (397 tests) re-run as the plan's only code-adjacent verification — this plan created zero Python symbols, so the run confirms no accidental regression from the doc changes.

## Task Commits

Each task was committed atomically:

1. **Task 1: 세션 중에 한 줄씩 적는 관찰 기록 양식** - `f235a51` (docs)
2. **Task 2: 손으로 쓰는 리캡 템플릿 (MEAS-05)** - `b60b9bd` (docs)
3. **Task 3: 본 세션 전 사전 점검(드라이런) 체크리스트와 README 연결** - `be5a0b7` (docs)

**Plan metadata:** commit pending (this SUMMARY + REQUIREMENTS.md, per worktree parallel-executor protocol — STATE.md/ROADMAP.md are updated by the orchestrator after merge)

## Files Created/Modified

- `docs/experiment/observation-log-template.md` - Hand-filled per-session observation form (meta, participants, attachment answers, tagged notes, intervention self-check, close-out)
- `docs/experiment/session-recap-template.md` - Hand-written 3-5 sentence recap template with blank form and a filled worked example
- `docs/experiment/dry-run-checklist.md` - Seven-item pre-session operational checklist with the OpenRouter free-tier daily-limit arithmetic
- `README.md` - New "실험 준비물" section linking all four `docs/experiment/` documents

## Decisions Made

- Grounded the recap template's worked example and the dry-run checklist's smoke-test description in 05-01's actual authored scenario content ("우물 아래의 것" and its 4-member cast) rather than generic placeholder text — makes both documents concretely checkable against what the running system will actually produce.
- Kept the dry-run checklist's rate-limit math as a direct carry-forward of 05-RESEARCH.md's Common Pitfall #2 figures (40 actions/session x 2 calls = ~80, 20 RPM / 50 vs 1000 RPD) rather than re-deriving or re-researching them — the plan's acceptance criteria required these exact numbers to appear verbatim, and 05-RESEARCH.md is the single sourced origin for them.
- Followed the plan's explicit instruction to keep in-session observation notes in one tagged table rather than four category-specific tables, since the plan itself flagged that splitting tables would cost hand-hesitation time mid-session — no deviation, but worth recording as an established UI/paperwork pattern for any future live-note tooling.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. (The dry-run checklist itself instructs the user to verify `OPENROUTER_API_KEY` and OpenRouter account payment history before the actual sessions, but that is the checklist's documented purpose, not a setup requirement of this plan's execution.)

## Next Phase Readiness

- EXP-02/EXP-03's "recorded" requirement now has a physical container: attendance, completion/petered-out judgment (with rationale), and intervention disclosure all have a designated place to be written by hand during and after each session.
- MEAS-05's recap template exists with a filled example; MEAS-06's answer slots exist with the question wording matching 05-02's script verbatim (05-02 was not yet executed in this worktree at plan-03 execution time — 05-03 depends only on 05-01 per its `depends_on` frontmatter — but the question wording is sourced independently from ROADMAP.md/REQUIREMENTS.md/M0-decisions.md, all of which agree on the exact phrase, so no drift risk from 05-02 landing later).
- D-58's operational risk is now a concrete number-bearing checklist item, ready to run before either live session; its final response decision (what to do if the daily limit is at risk) is explicitly deferred to 05-04 Task 2's decision checkpoint, per this plan's own scope boundary.
- No blockers for downstream plans (05-04/05-05/05-06) or the Phase 6 gate. This plan produced zero code changes; the 397-test suite is unchanged from 05-01's baseline.

---
*Phase: 05-1*
*Completed: 2026-08-04*

## Self-Check: PASSED

All created/modified files verified present on disk (`docs/experiment/observation-log-template.md`, `docs/experiment/session-recap-template.md`, `docs/experiment/dry-run-checklist.md`, `README.md`); all three task commits (`f235a51`, `b60b9bd`, `be5a0b7`) verified in `git log`.

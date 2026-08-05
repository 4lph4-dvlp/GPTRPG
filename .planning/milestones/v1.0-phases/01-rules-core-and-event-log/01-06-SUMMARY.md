---
phase: 01-rules-core-and-event-log
plan: 06
subsystem: session-actor
tags: [asyncio, event-sourcing, cli, argparse, single-writer]

requires:
  - phase: 01-rules-core-and-event-log (01-02, 01-03, 01-04)
    provides: SessionActor/queue skeleton (01-02), six-event schema + EventStore (01-03), resolve_2d6/UnsupportedModifier (01-04)
provides:
  - SessionActor widened to all six commands with a shared validate->resolve->next_seq->append pipeline
  - SessionRegistry.get_or_create — one live actor per session id, first layer of D-09①
  - Finalized cli submit {declare,confirm,roll,narrate,clock,ai} / replay subcommands
  - Human-verified, byte-identical replay output with ten Korean-labeled GameState fields
affects: [phase-02-rulebook-data, phase-03-ai-turn, phase-05-experiment-tooling]

actuals:
  tokens: 9122
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Command validation fully precedes seq acquisition (validate -> rules-core -> next_seq -> append) so a rejected command never consumes a seq or appends a partial event"
    - "SequenceConflict is propagated to the caller via a per-command asyncio.Future, never caught-and-discarded — a broken single-writer assumption must be visible, not silently retried"
    - "CLI submit prints the recorded event's seq as the sole stdout line, which becomes the next command's --caused-by by hand — this is the mechanism that lets a human build a complete session from the command line"
    - "replay output omits wall-clock/duration values by construction so repeat replays of the same db are byte-identical"

key-files:
  created: []
  modified:
    - src/gptrpg/session_actor/actor.py
    - src/gptrpg/session_actor/projection.py
    - src/gptrpg/cli/main.py
    - tests/test_session_actor.py
    - tests/test_cli.py
    - tests/test_tracer.py

key-decisions:
  - "SessionActor built on an asyncio queue + single consumer task, not threads — see Phase 3 carry-forward note below"
  - "'틱(tick)' is not a named platform-wide primitive; this game mode's clock concept is represented as '위협 시계 현재 칸' / '시계 진행 횟수' at the ruleset level, so a future ruleset without a threat-clock shape isn't forced into a platform vocabulary it doesn't have"

patterns-established:
  - "Four-step command processing procedure (validate, rules-core if applicable, next_seq, append) reused identically across all six commands"
  - "CLI has zero game-rule logic — it only turns args into Command objects, calls the actor, and turns GameState into text"

requirements-completed: [RIG-06]

coverage:
  - id: D1
    description: "SessionActor processes all six commands through one queue + one consumer, enforcing single-writer per session"
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_session_actor.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "SessionRegistry.get_or_create returns the same actor for a repeated session id, a new one for a different id"
    verification:
      - kind: unit
        ref: "tests/test_session_actor.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Rejected commands (CommandRejected) append zero events; SequenceConflict is forwarded to the caller, never swallowed"
    verification:
      - kind: unit
        ref: "tests/test_session_actor.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "CLI submit's six subcommands each build a complete session by hand; replay renders it as ten labeled, human-readable lines"
    requirement: "RIG-06"
    verification:
      - kind: unit
        ref: "tests/test_cli.py"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 checkpoint: human ran the plan's exact six-submit + double-replay CLI sequence against a fresh temp db, confirmed byte-identical repeat output via diff, and approved (\"승인\" / \"그래 넘어가자\") after a clarifying Q&A about tick terminology"
        status: pass
    human_judgment: true
    rationale: "\"재생 출력이 읽히는가\"는 판단의 문제라 테스트로 단언할 수 없다 (plan's own words) — this is exactly why Task 3 was a checkpoint:human-verify gate rather than an automated assertion"

duration: 65min
completed: 2026-08-01
status: complete
---

# Phase 1 Plan 6: Session Actor and CLI Summary

**Session actor widened to all six event-sourcing commands with a shared validate-then-append pipeline enforcing single-writer-per-session, and a finalized `submit`/`replay` CLI that a human confirmed produces byte-identical, readable replay output.**

## Performance

- **Duration:** 65 min
- **Tasks:** 3 (2 auto+tdd, 1 checkpoint:human-verify)
- **Files modified:** 6

## Accomplishments

- `SessionActor` now processes `DeclareAction`, `ConfirmAction`, `ResolveCheck`, `AppendNarration`, `AdvanceClock`, `RecordAiCall` — all six event types — through one queue and one consumer task per session, via a uniform four-step pipeline (validate → rules-core if applicable → `next_seq` → `append`) that guarantees a rejected command leaves zero trace in the log.
- `SessionRegistry.get_or_create(session_id)` guarantees a single live actor per session id within a process (D-09① first layer); the event store's sequence uniqueness constraint is the second layer, valid across process boundaries.
- `SequenceConflict` is never caught and silently retried — it propagates through a per-command `asyncio.Future` all the way to the caller, surfacing a genuinely broken single-writer assumption instead of hiding it.
- The CLI's `submit` subcommand now covers all six commands (`declare`, `confirm`, `roll`, `narrate`, `clock`, `ai`) sharing `--db`/`--session`, and prints the recorded event's seq as its only stdout line — the mechanism that lets a human hand-build a complete session from the shell, feeding one command's output into the next command's `--caused-by`.
- `replay` renders `GameState` as ten Korean-labeled lines (session id, db path, event count, turn count, check count, miss count, clock segment, clock advances, narration count, AI call count, token total, last grade) with no wall-clock or duration values, so repeat replays of the same db are byte-identical by construction — verified twice, once by the executor during Task 2 and once independently by the orchestrator immediately before the Task 3 checkpoint was presented to the human.
- Task 3 (checkpoint:human-verify, gate=blocking) was resolved by direct human approval after the orchestrator re-ran the plan's exact six-`submit`-then-double-`replay` sequence against a fresh temp db and presented the byte-identical output for judgment.

## Task Commits

Each task was committed atomically:

1. **Task 1: 세션 액터를 여섯 종류 명령으로 넓히고, 쓰기 주체가 하나임을 강제한다** - `2d5534e` (test, RED), `ce6d5d8` (feat, GREEN)
2. **Task 2: 명령줄로 완결된 한 세션을 만들고, 재생 출력을 사람이 읽을 수 있게 마감한다** - `aa88526` (test, RED), `126883a` (feat, GREEN — includes a Rule-1 fix to `tests/test_tracer.py`)
3. **Task 3: 재생 출력이 정말 읽히는지 사람이 확인** - checkpoint:human-verify, gate=blocking. Resolved by direct human approval; no code commit (no code changed by this task — see Checkpoint Resolution below). Bookkeeping commit: `4e127e3` (checkpoint marker, prior to resolution)

**Plan metadata:** (this commit) `docs(01-06): complete session actor and cli plan`

_Note: Both TDD tasks followed RED → GREEN; neither required a REFACTOR commit._

## Files Created/Modified

- `src/gptrpg/session_actor/actor.py` - Six frozen-dataclass commands (`DeclareAction`, `ConfirmAction`, `ResolveCheck`, `AppendNarration`, `AdvanceClock`, `RecordAiCall`), the `Command` union, `SessionActor`'s four-step `_process`/`_prepare` pipeline, `CommandRejected`, `SessionRegistry`
- `src/gptrpg/session_actor/projection.py` - `rebuild_state` finalized as a pure, read-only fold over the full event log (no intermediate storage — every replay re-derives state from scratch, per D-08)
- `src/gptrpg/cli/main.py` - `submit {declare, confirm, roll, narrate, clock, ai}` and `replay` subcommands finalized; zero game-rule logic, only arg → Command → actor → text
- `tests/test_session_actor.py` - Order guarantee, single-actor-per-session, validation rejection (zero events appended), sequence-conflict propagation, `rebuild_state` read-only-ness
- `tests/test_cli.py` - All six `submit` branches, a full hand-built session via CLI only, ten-label replay output assertion, byte-identical repeat-replay assertion, nonexistent-session zero-event replay, bad-argument non-zero exit
- `tests/test_tracer.py` - Rule-1 deviation: four argv lists and two label assertions updated to the finalized `roll` subcommand shape and renamed labels ("판정 횟수"→"판정 수", "마지막 등급"→"마지막 판정 등급"), replacing the pre-01-06 `--command roll` interface this task's action text explicitly superseded

## Decisions Made

- SessionActor stays on an asyncio queue + single consumer task rather than threads, per D-09① and the prior tracer research confirming order survives interleaved waits (see Phase 3 carry-forward note below for the assumption this rests on).
- `SequenceConflict` is a hard propagate-never-catch boundary — the one place a "single writer" claim could quietly become false, so it must be loud if it ever happens.
- Checkpoint Q&A resolution (see below): "틱(tick)" is deliberately not promoted to a platform-wide primitive name; it stays expressed as this ruleset's own "위협 시계" vocabulary.

## Checkpoint Resolution (Task 3)

The Task 3 checkpoint (`checkpoint:human-verify`, `gate="blocking"`) was resolved via direct human approval, not re-execution by this agent. Summary of what happened:

1. The orchestrator independently re-ran the plan's exact `<how-to-verify>` sequence — six `uv run gptrpg submit ...` commands (declare → confirm → roll → narrate → clock → ai) against a fresh temp db, followed by `uv run gptrpg replay ...` twice.
2. Results matched the plan's `acceptance_criteria` exactly: all six submits exited 0 with sequential seq numbers 0–5; the two replay runs produced byte-for-byte identical output (verified via `diff`, zero differences); a replay of a nonexistent session (`--session ghost`) exited 0 with all-zero counts rather than erroring.
3. The observed replay output (ten labeled lines: 세션, 기록 파일, 사건 수, 턴 수, 판정 수, 판정 실패 수, 위협 시계 현재 칸, 시계 진행 횟수, 서사 조각 수, AI 호출 수, 토큰 합계, 마지막 판정 등급) was presented to the human.
4. The human asked a clarifying question: whether the TRPG concepts discussed during planning — 세션/사건/턴/틱 (session/event/turn/tick) — were all adequately represented, specifically whether "틱" needed its own labeled line.
5. The orchestrator explained the mapping: 세션→"세션:", 사건→"사건 수:", 턴→"턴 수:", and the "tick" concept is already represented by "위협 시계 현재 칸"/"시계 진행 횟수" — this game mode's specific clock implementation — deliberately *not* named "틱" as a shared platform primitive, because a future ruleset added to this platform might not have a "위협 시계"-shaped clock at all. Keeping the name at the ruleset level (not baking it into shared platform code) avoids forcing a vocabulary that may not fit later rulebooks (relevant to Phase 2's two-rulebook goal).
6. The human accepted the explanation and replied "그래 넘어가자" (let's move on) — the resume-signal equivalent of "승인" (approved) per the plan's `<resume-signal>`.

No code changes resulted from this discussion. `src/gptrpg/cli/main.py`'s replay output format was not modified — the ten labeled lines stand as implemented and approved.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated `tests/test_tracer.py` to match the finalized `roll` subcommand shape**
- **Found during:** Task 2 (CLI submit/replay finalization)
- **Issue:** `tests/test_tracer.py`'s pre-existing tests used the old `--command roll` CLI shape and old field labels ("판정 횟수", "마지막 등급"), both of which this task's own action text explicitly replaced with the finalized `submit roll` subcommand and renamed labels ("판정 수", "마지막 판정 등급").
- **Fix:** Updated four argv lists and two label assertions in `tests/test_tracer.py` to the finalized interface.
- **Files modified:** `tests/test_tracer.py`
- **Verification:** `uv run pytest -q` green (142 passed)
- **Committed in:** `126883a` (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for correctness — the old tracer tests would otherwise assert against an interface this plan's own action text says is superseded. No scope creep.

## Issues Encountered

None beyond the documented deviation above.

## Phase 3 Carry-Forward Note (조사의 미확인 전제 A1)

Per the plan's explicit instruction, this premise is copied forward verbatim so Phase 3 does not miss it:

조사 문서가 남긴 전제 A1: **Phase 3에서 쓸 AI 제공자 도구가 비동기 방식을 기본으로 제공할 것이다.** 이 전제 때문에 세션 액터를 스레드가 아니라 비동기 큐로 짰다. 전제가 틀리면(동기 전용 도구나 별도 프로세스 방식을 쓰게 되면) 액터 안에서 동기 호출을 감싸는 작업이 추가로 필요하다. **구조 자체(큐 + 소비자 하나)는 바뀌지 않으므로 다시 쓸 분량은 작다.**

Phase 3을 시작할 때 실제 도구를 보고 이 전제를 한 번 확인하고, 결과를 그 단계의 문서에 한 줄로 남긴다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 1's Success Criteria 1 (state fully reconstructable from the event log) and 5 (single writer per session enforced by code structure) are both now closed and human-verified. All six event types flow exclusively through `SessionActor` — no code path calls the event store directly. The CLI is a real, usable hand-tool for building sessions, which Phase 5 will reuse to prepare experiment materials without a screen or server. Phase 3 must confirm the async-provider-tool assumption (A1, above) before building on `SessionActor`'s queue shape. This is the last plan in Phase 1 (6/6) — phase-level completion (verification, `phase.complete`) is the orchestrator's next step, not part of this SUMMARY.

---
*Phase: 01-rules-core-and-event-log*
*Completed: 2026-08-01*

## Self-Check: PASSED

All 6 key files confirmed present on disk; all 5 referenced commit hashes (`2d5534e`, `ce6d5d8`, `aa88526`, `126883a`, `4e127e3`) confirmed present in `git log --oneline --all`.

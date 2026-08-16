---
phase: 11-rulebook-vocabulary
plan: 06
subsystem: ai
tags: [fastapi, pydantic, react, typescript, vitest, action-classifier, narration, story-view]

# Dependency graph
requires:
  - phase: 11-05
    provides: "ProposalTier 네 값(single/several/no_check/unclear) — NO_CHECK_SIGNAL 예약 신호, Proposal.tier 우선순위(unknown_move>후보>신호>나머지). 이 계획 시점에는 no_check가 아직 unclear와 같은 화면(다시 쓰기)이었다"
  - phase: 11-03
    provides: "frontend/src/labels.ts·types.ts·ChatPane.tsx의 그 시점 상태, StoryPane.tsx/groupTurns.ts/TurnCard.tsx의 턴 카드 구조(이 계획이 처음 손댐)"
provides:
  - "POST /sessions/{id}/proceed — 판정 없이 서술로 잇는 웹 라우트(ProceedRequest/ProceedResponse)"
  - "cli/turn_flow.py의 no_check 전용 갈래 — _proceed_without_check()"
  - "NO_CHECK_SUMMARY(agents/context.py) — check_summary 자리의 플랫폼 고정 문장, 플레이어 원문 울타리 우회 방지"
  - "frontend/src/panes/ChatPane.tsx의 세 갈래 화면(unclear/no_check/single·several)"
  - "groupTurns.isVisibleTurn — 확인 사건 없이도(proceed 경로) 서사가 있으면 이야기 화면에 카드로 올라간다"
  - "이 저장소 최초의 프론트엔드 단위 시험 틀(vitest) + groupTurns.test.ts"
affects: [11-07, phase-12]

# Actuals (#2632)
actuals:
  tokens: 18025
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: [vitest]
  patterns:
    - "웹/CLI 두 호출부 동시 반영 관례(10-05가 세움)를 proceed()에도 적용 — routes_actions.py·turn_flow.py가 Task 1 한 커밋(790f17e)에 함께 들어간다"
    - "proceed()가 confirm()의 판정 이후 구간을 거울처럼 복제하되 ConfirmAction/ResolveCheck를 제출하지 않는다 — caused_by_seq가 confirm_seq/resolve_seq 대신 declare_seq 하나로 고정된다"
    - "이야기 화면 가시성 판단(isVisibleTurn)이 사건 모양(「선언+서사, 확인 없음」)만으로 턴 자격을 판단 — 새 이벤트 타입 없이도 화면이 새 경로를 표현한다"

key-files:
  created:
    - frontend/src/session/groupTurns.test.ts
  modified:
    - src/gptrpg/agents/context.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/cli/turn_flow.py
    - src/gptrpg/turn/judgments.py
    - tests/test_web_actions.py
    - tests/test_cli.py
    - frontend/src/labels.ts
    - frontend/src/api/types.ts
    - frontend/src/api/client.ts
    - frontend/src/panes/ChatPane.tsx
    - frontend/src/session/groupTurns.ts
    - frontend/src/panes/StoryPane.tsx
    - frontend/src/components/TurnCard.tsx
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "proceed()의 caused_by_seq를 전부 declare_seq로 고정했다 — 이 경로엔 confirm_seq/resolve_seq가 없다(결정 1, PLAN.md). 배경 시계 조건 검사(AdvanceClock)의 caused_by_seq도 declare_seq를 가리킨다"
  - "check_summary 자리에 NO_CHECK_SUMMARY 고정 문장을 쓴다 — 판정이 없으므로 판정 요약이 없고, 플레이어 원문을 넣으면 SAFE-03의 원문 울타리를 우회하는 경로가 생긴다"
  - "화면에서 no_check 갈래에 「다시 쓰기」 버튼을 두지 않는다(결정 2, PLAN.md) — 정식 경로를 예외처럼 보이게 만들지 않기 위해서다"
  - "[Task 3 사람 확인 관문에서 발견된 결함, Rule 2 - Missing Critical] groupTurns.isConfirmedTurn을 isVisibleTurn으로 넓혔다 — 아래 Deviations 참조"
  - "이 저장소 최초의 프론트엔드 단위 시험을 위해 vitest를 devDependency로 추가했다 — 아래 Deviations 참조"

patterns-established:
  - "화면 가시성 판단과 사건 존재 여부를 분리 — `isVisibleTurn`이 `turn.confirmed`(판정 경로)와 `turn.narration.length`(무판정 경로) 두 독립 신호를 or로 묶어, 새 이벤트 종류 없이 새 턴 모양을 화면이 표현하게 한다"
  - "TurnCard가 '이미 보이는 턴' 전제 위에서 confirmed===null을 '판정이 원래 없는 턴'으로 해석 — 대기 상태(판정을 기다리는 중)와 무판정 상태를 구조적으로 구분한다"

requirements-completed: [RULE-15]

coverage:
  - id: D1
    description: "굴릴 필요가 없다고 분류된 행동에서 진행자가 실제로 서술을 내고 이야기가 이어진다 — 「인식된 행동이 없어요, 다시 말해 보세요」로 턴이 죽지 않는다(D-10, RULE-15)"
    requirement: "RULE-15"
    verification:
      - kind: unit
        ref: "tests/test_web_actions.py::test_proceed_narrates_without_resolve_check"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py::test_no_check_tier_produces_narration_without_check"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 사람 확인 관문 — 사장님이 실제 브라우저에서 「문을 연다」→[이대로 진행]→서사 전문이 실제로 나옴을 확인"
        status: pass
    human_judgment: false
  - id: D2
    description: "unclear만 「다시 쓰기」로 간다 — no_check는 다른 화면(안내 + [이대로 진행] 버튼 하나)으로 간다(D-11)"
    requirement: "RULE-15"
    verification:
      - kind: other
        ref: "grep -c 'tier === \"unclear\"'/'tier === \"no_check\"' frontend/src/panes/ChatPane.tsx (둘 다 1건 이상)"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 사람 확인 관문 — 「asdf 랄라 뿅뿅」은 여전히 「인식된 행동이 없어요」+[다시 쓰기], 「문을 연다」는 「굴릴 필요 없는 행동이에요」+[이대로 진행]로 서로 다른 화면임을 확인"
        status: pass
    human_judgment: false
  - id: D3
    description: "판정 없이 진행한 턴의 사건 기록이 「선언만 있고 아무것도 없는 턴」과 구조적으로 구분된다 — 선언 + 서사가 있고 확인·판정이 없는 모양이다"
    requirement: "RULE-15"
    verification:
      - kind: unit
        ref: "tests/test_web_actions.py::test_proceed_does_not_submit_confirm_action, ::test_proceed_narrates_without_resolve_check"
        status: pass
      - kind: unit
        ref: "frontend/src/session/groupTurns.test.ts — \"판정 없이 진행한 턴(선언 + 서사, 확인 없음)이 보인다\""
        status: pass
    human_judgment: false
  - id: D4
    description: "판정 없이 진행하는 경로가 ResolveCheck를 제출하지 않는다 — 주사위를 굴리지 않는 것이 실제로 굴리지 않는 것이다"
    requirement: "RULE-15"
    verification:
      - kind: other
        ref: "python -c \"import inspect; from gptrpg.web import routes_actions as r; s=inspect.getsource(r.proceed); print('Resolve'+'Check(' in s)\" -> False"
        status: pass
    human_judgment: false
  - id: D5
    description: "웹과 CLI가 같은 커밋에서 같은 의미의 판정 없는 서술 경로를 갖는다"
    requirement: "RULE-15"
    verification:
      - kind: other
        ref: "git show --stat 790f17e — src/gptrpg/web/routes_actions.py와 src/gptrpg/cli/turn_flow.py가 같은 커밋에 있음"
        status: pass
    human_judgment: false
  - id: D6
    description: "진행자에게 넘어가는 사실 묶음의 check_summary 자리에 플레이어 원문이 아니라 플랫폼이 정한 고정 문장(NO_CHECK_SUMMARY)이 들어간다 — 울타리 밖으로 원문이 새지 않는다"
    requirement: "RULE-15"
    verification:
      - kind: unit
        ref: "tests/test_web_actions.py::test_proceed_passes_fixed_summary_not_player_text"
        status: pass
    human_judgment: false
  - id: D7
    description: "후보가 여럿일 때 화면이 모델이 낸 순서를 유지하고, no_check 화면에는 후보 버튼이 하나도 없다(RULE-15 ordering)"
    requirement: "RULE-15"
    verification:
      - kind: other
        ref: "frontend/src/panes/ChatPane.tsx — no_check 분기에 candidates.map 호출이 없음(코드 리뷰 확인), single/several 분기는 11-05 이전부터 있던 순서 유지 로직 무변경"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 사람 확인 관문 — no_check 화면에 후보 버튼이 없음을 확인"
        status: pass
    human_judgment: false
  - id: D8
    description: "[버그·수정] proceed 턴이 이야기 화면(StoryPane)에 실제로 나타난다 — Task 3 사람 확인 관문에서 처음 발견된 결함(계획서 files_modified 밖의 프론트엔드 파일 3개가 원인)"
    verification:
      - kind: unit
        ref: "frontend/src/session/groupTurns.test.ts — 4개 테스트 전부(proceed 턴 보임 / 서사 실패 확인 턴 회귀 방지 / 선언만 한 턴 회귀 방지 / end-to-end 필터)"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 재확인 — 사장님이 실제 브라우저에서 [이대로 진행] 클릭 후 서사 전문이 화면에 나타남을 확인, 「판정을 기다리는 중」 가짜 대기 표시도 안 나타남을 확인"
        status: pass
    human_judgment: false
  - id: D9
    description: "「판정 없이 진행」 화면이 사람에게 막다른 길이 아니라 정상 경로로 읽히는지는 자동 단언 대상이 아니다 — Task 3의 사람 확인 관문이 그 자리를 맡는다"
    verification: []
    human_judgment: true
    rationale: "문구·어조가 사람에게 어떻게 읽히는지는 자동 시험으로 가릴 수 있는 성질이 아니다(계획서 must_haves의 명시적 백스톱 진술). 사장님이 실제 브라우저에서 확인하고 승인했다."

# Metrics
duration: ~3시간20분 (Task 3 사람 확인 대기 + 재작업 왕복 포함, 순수 실행 시간은 더 짧다)
completed: 2026-08-17
status: complete
---

# Phase 11 Plan 06: 「굴리지 않는다」를 막다른 길에서 정식 경로로 바꾼다 Summary

**`POST /sessions/{id}/proceed`(웹)와 `turn_flow.py`의 `no_check` 갈래(CLI)가 같은 커밋에서 판정 없이 서술로 잇는 경로를 열었고, 화면 세 곳(확인 화면·이야기 화면·화면 시험)이 함께 갈라졌다 — 사람 확인 관문에서 실제 브라우저로 통과했다**

## Performance

- **Duration:** ~3시간20분 (Task 3 사람 확인 대기·재작업 왕복 포함)
- **Completed:** 2026-08-17
- **Tasks:** 3 (Task 1·2 자동, Task 3 사람 확인 관문) + 관문에서 드러난 결함 1건 수정
- **Files modified:** 15개 (신규 파일 1개: `frontend/src/session/groupTurns.test.ts`)

## Accomplishments

- `src/gptrpg/web/routes_actions.py`에 `POST /sessions/{session_id}/proceed`가 신설됐다 — `confirm()`의 판정 이후 구간(병렬 세 판단 → `RecordAiCall` → `narrate()` 스트림 → 조각 제출 → 배경 시계 조건 검사)을 거울처럼 따라가되 `ConfirmAction`/`ResolveCheck`를 제출하지 않는다. `caused_by_seq`는 전부 `declare_seq` 하나로 고정된다 — 이 경로엔 확인·판정 사건이 없다(결정 1, PLAN.md).
- `src/gptrpg/cli/turn_flow.py`의 `no_check` 갈래가 `unclear`에서 분리됐다 — `_proceed_without_check()`가 CLI 방식으로 같은 순서를 밟아 서사를 화면에 찍는다. 두 파일은 **같은 커밋**(`790f17e`)에 들어갔다(10-05가 세운 웹/CLI 동시 반영 관례).
- `src/gptrpg/agents/context.py`에 `NO_CHECK_SUMMARY` 상수가 신설됐다 — 판정이 없는 턴의 `check_summary` 자리에 플레이어 원문 대신 플랫폼 고정 문장을 넣어 SAFE-03의 원문 울타리 우회 경로를 막는다.
- `frontend/src/panes/ChatPane.tsx`가 확인 화면을 세 갈래로 나눴다 — `unclear`(다시 쓰기), `no_check`(안내 + [이대로 진행] 하나, 후보·다시 쓰기 버튼 없음), `single`/`several`(기존 후보 버튼). 파일 상단 도크스트링도 "판정으로 가는 통로 하나 + 판정 없이 이어지는 통로 하나"로 갱신됐다.
- **Task 3 사람 확인 관문에서 실제 결함 1건이 드러나 고쳤다** — 상세는 아래 Deviations. `frontend/src/session/groupTurns.ts`의 `isVisibleTurn`(옛 `isConfirmedTurn`)이 확인 사건 없이도 서사가 있는 턴(=proceed 경로)을 이야기 화면에 올리도록 넓어졌고, `frontend/src/components/TurnCard.tsx`가 그 턴에서 「판정을 기다리는 중」 가짜 대기 표시를 안 그리도록 고쳐졌다. 이 저장소 최초의 프론트엔드 단위 시험(`vitest`)이 함께 들어왔다.
- **사람 확인 관문(Task 3)이 재작업 뒤 실제 브라우저로 통과했다** — 「문을 연다」→[이대로 진행]→서사 전문이 실제로 나옴, 「asdf 랄라 뿅뿅」→여전히 「다시 쓰기」, 「판정을 기다리는 중」 가짜 대기 없음, 이 세 가지를 사장님이 직접 확인했다.

## Task Commits

각 태스크를 개별 커밋했다:

1. **Task 1: 판정 없이 서술로 가는 경로를 웹과 CLI에 같은 커밋으로 낸다** — `790f17e` (feat)
2. **Task 2: 화면에서 「판정 없이 진행」과 「다시 쓰기」를 가른다** — `217e618` (feat)
3. **Task 3: 「문을 연다」를 실제로 쳐 보고 이야기가 이어지는지 확인** — 사람 확인 관문, 코드 변경 없음. 1차 확인에서 이야기 화면 결함을 발견해 재작업으로 이어짐(아래 참조)

재작업(Task 3 관문에서 드러난 결함 수정) — `8a4aaac` (fix)

**Plan metadata:** 이 커밋(SUMMARY.md 등)

참고: `af68c15`·`a971461`(docs)은 오케스트레이터가 Task 3 확인 과정에서 별도로 조사·기록한 모델 설정 관련 발견 문서다 — 이 계획의 태스크 커밋이 아니며, 아래 "확인 과정에서 드러난 계획 범위 밖 사항"이 그 내용을 요약한다.

## Files Created/Modified

- `src/gptrpg/agents/context.py` - `NO_CHECK_SUMMARY` 상수 신설
- `src/gptrpg/web/routes_actions.py` - `ProceedRequest`/`ProceedResponse`/`proceed()` 라우트 신설, 모듈 도크스트링 갱신
- `src/gptrpg/cli/turn_flow.py` - `no_check`를 `unclear`에서 분리, `_proceed_without_check()` 신설
- `src/gptrpg/turn/judgments.py` - `gather_turn_judgments`/`build_narration_facts` 도크스트링에 `NO_CHECK_SUMMARY` 사용처 한 줄 추가(시그니처 무변경)
- `tests/test_web_actions.py` - `proceed()` 시험 5건 신설(판정 없이 서사/확인 미제출/신원 불일치/서사 실패 플래그/고정 요약)
- `tests/test_cli.py` - `test_no_check_tier_produces_narration_without_check` 신설, 기존 `test_no_check_tier_ends_turn_without_indexerror`를 새 동작(더 이상 "끝납니다"가 아님)에 맞게 갱신
- `frontend/src/labels.ts` - `noCheckNeeded`/`proceedWithoutCheck` 문구 추가
- `frontend/src/api/types.ts` - `ProceedResponse` 인터페이스 신설(백엔드와 칸 이름 동일)
- `frontend/src/api/client.ts` - `proceed(...)` 호출 함수 신설
- `frontend/src/panes/ChatPane.tsx` - 확인 화면 세 갈래 분기, 도크스트링 갱신
- `frontend/src/session/groupTurns.ts` - `isConfirmedTurn` → `isVisibleTurn`(뜻 확장, 아래 Deviations)
- `frontend/src/panes/StoryPane.tsx` - 필터 함수 이름 갱신(호출부 한 곳)
- `frontend/src/components/TurnCard.tsx` - `CheckLine`이 무판정 턴에서 "판정을 기다리는 중"을 그리지 않도록 수정
- `frontend/src/session/groupTurns.test.ts` (신규) - `isVisibleTurn` 회귀 시험 4건
- `frontend/package.json`/`package-lock.json` - `vitest` devDependency 추가, `test` 스크립트 신설

## Decisions Made

- **`proceed()`의 `caused_by_seq`를 전부 `declare_seq`로 고정했다** — 이 경로엔 `confirm_seq`/`resolve_seq`가 없다(결정 1, PLAN.md). 배경 시계 조건 검사(`AdvanceClock`)의 `caused_by_seq`도 `declare_seq`를 가리킨다.
- **`check_summary` 자리에 `NO_CHECK_SUMMARY` 고정 문장을 쓴다** — 판정이 없으므로 판정 요약이 없고, 플레이어 원문을 넣으면 SAFE-03의 원문 울타리를 우회하는 경로가 생긴다(결정 3, PLAN.md).
- **`no_check` 화면에 「다시 쓰기」 버튼을 두지 않는다**(결정 2, PLAN.md) — 정식 경로를 예외처럼 보이게 만들지 않기 위해서다.
- **`isConfirmedTurn`을 `isVisibleTurn`으로 이름·뜻을 넓혔다** — 확인됨(player_confirmed) **또는** 서사가 있음(narration.length > 0) 둘 중 하나면 이야기 화면에 카드로 올라간다. 「사람이 누른 것만 서사로 간다」(D-10 결정 2)는 두 경로 다 지켜진다 — `narration`이 채워지는 유일한 통로가 `confirm()`/`proceed()`이고 둘 다 사람이 버튼을 눌러야 서버가 부른다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical, Task 3 사람 확인 관문에서 발견] `proceed` 턴이 이야기 화면에 아예 안 보였다**
- **Found during:** Task 3 사람 확인 관문 1차 확인 — 사장님이 [이대로 진행]을 눌렀는데 화면에 아무 것도 안 나타남
- **Issue:** `frontend/src/session/groupTurns.ts`의 `isConfirmedTurn`이 `turn.confirmed !== null && turn.confirmed.player_confirmed`만 참으로 쳤다. `proceed()`는 설계상(결정 1, PLAN.md) `action_confirmed` 사건을 절대 제출하지 않으므로, 서버가 서사 사건을 정확히 남겼는데도(`GET /events` → `narration_appended`×5 확인됨) `StoryPane.tsx`가 그 턴을 통째로 걸러냈다. 이 계획의 백엔드 설계 결정(선언+서사, 확인 없음이 정상 모양)이 그것을 그리는 화면 두 파일(`StoryPane.tsx`/`groupTurns.ts`)까지 안 이어진 계획 단계의 누락이다 — `11-06-PLAN.md`의 `files_modified`에 이 두 파일이 없었다.
- **Fix:** `isConfirmedTurn`을 `isVisibleTurn`으로 이름·뜻을 넓혔다(위 Decisions 참조). 부수적으로 `frontend/src/components/TurnCard.tsx`의 `CheckLine`도 고쳤다 — `confirmed === null`(=proceed 턴)에서 `check === null`이 영원히 참이라 "판정을 기다리는 중"이 계속 떠 있던 것을, 판정 자체가 없는 턴은 판정 줄을 아예 안 그리도록 바꿨다(이 결함은 첫 결함을 고치는 과정에서 함께 드러났다 — 첫 결함이 가려서 안 보이던 것이 화면에 뜨자마자 눈에 띄었다).
- **Files modified:** `frontend/src/session/groupTurns.ts`, `frontend/src/panes/StoryPane.tsx`(호출부 이름 갱신), `frontend/src/components/TurnCard.tsx`
- **Verification:** `frontend/src/session/groupTurns.test.ts` 4건 신설 후 통과(아래 2번 참조), 사람 확인 관문 재확인 — 사장님이 실제 브라우저에서 [이대로 진행] 클릭 후 서사 전문이 화면에 나타남을 확인, 「판정을 기다리는 중」도 안 나타남을 확인
- **Committed in:** `8a4aaac`

**2. [Rule 2 - Missing Critical] 이 저장소 최초의 프론트엔드 단위 시험을 위해 `vitest`를 devDependency로 추가했다**
- **Found during:** 위 1번 결함을 고정할 회귀 시험을 붙이려던 중 — 이 저장소에 프론트엔드 단위 시험 틀이 없었다(11-03 SUMMARY.md가 이미 이 공백을 기록해 둠)
- **Issue:** `isVisibleTurn`의 새 규칙(확인 또는 서사)과 회귀 두 건(서사 실패한 확인 턴은 계속 보임 / 선언만 한 턴은 계속 안 보임)을 코드 리뷰만으로는 재발 방지가 안 된다
- **Fix:** `npm view vitest version`으로 실제 npm 레지스트리에 있는 정식 패키지임을 먼저 확인(Vite 생태계 표준 시험 러너, 이미 의존 중인 `vite`와 같은 팀이 관리)한 뒤 `npm install --save-dev vitest`, `npm audit fix`(설치 직후 뜬 `nanoid` 취약점 1건을 해소, 0 vulnerabilities로 확인), `package.json`에 `"test": "vitest run"` 스크립트 추가. `frontend/src/session/groupTurns.test.ts` 신설(4건)
- **Files modified:** `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/session/groupTurns.test.ts`(신규)
- **Verification:** `cd frontend && npx vitest run` → 4 passed. 오케스트레이터가 별도로 변이 시험(`isVisibleTurn`을 옛 조건으로 되돌림)까지 돌려 새 시험 2건이 정확히 실패하고 회귀 보호 시험 2건은 계속 통과함을 확인 — 시험이 실제로 그 성질을 잡고 있다는 근거
- **Committed in:** `8a4aaac`

---

**Total deviations:** 2 auto-fixed (둘 다 Rule 2 - Missing Critical, 같은 커밋 `8a4aaac`)
**Impact on plan:** 둘 다 계획서 자신의 목표(Task 3 "이야기가 이어지는지 확인")를 실제로 충족시키는 데 구조적으로 불가피했다 — 범위 이탈이 아니라, 계획 단계에서 빠졌던 화면 쪽 배선을 채운 것이다.

## Issues Encountered

### 확인 과정에서 드러난 계획 범위 밖 사항

**① 서사에 외국어가 섞이는 문제 — 모델 문제, 해결됨(이 계획의 결함 아님).** 사장님이 Task 3 재확인 중 읽은 서사에 키릴 문자(`стоящий`)·조어(`silenziously`)·영어가 섞여 있었다. 오케스트레이터가 사건 기록 719조각을 측정한 결과 `nemotron-3-super-120b`(서사 담당)의 오염률이 40%(15/37)였고, 같은 코드·같은 프롬프트로 `nemotron-3-ultra-550b`를 재측정하니 0%(0/20)였다 — `master_gm` 모델이 언젠가 550b에서 120b로 내려간 것이 원인이었다. 사장님 결정으로 550b로 되돌렸다(근거: `.planning/phases/11-rulebook-vocabulary/11-NARRATION-LANGUAGE-FINDING.md`, 커밋 `a971461`). 부수 사실: `agents/narration_guard.py`의 「깨진 글자」 검사는 `�`(U+FFFD)만 세므로 이 오염을 원리적으로 못 잡는다 — 언어 이탈 검사는 미결로 남았다.

**② 「문을 부순다」 무브 선택이 불안정 — 미해결, 이 계획과 무관, 별도 조사 대상.** 새 세션 2회 중 1회, 대화 쌓인 세션 3회 중 1회만 올바른 무브가 나왔다. 반면 이 계획이 만든 「문을 연다」→`no_check` 경로는 새 세션 5회 중 5회 전부 정확했다 — 이 계획이 만든 경로는 안정적이고, 흔들리는 것은(이 계획과 무관한) 무브 선택 정확도다.

## User Setup Required

None - 외부 서비스 설정 불필요. (참고: `.gptrpg/agents.json`의 모델 설정과 `.env.local`은 사장님이 정한 값 그대로 두었다 — 이 계획이 건드리지 않았다.)

## Next Phase Readiness

- RULE-15가 이 계획으로 완전히 끝났다 — REQUIREMENTS.md를 `[x]`/`Complete`로 갱신했다(RULE-11은 이 계획의 `requirements` 범위 밖이라 손대지 않았다).
- `isVisibleTurn`이 세운 패턴("확인 또는 서사가 있으면 보인다")은 앞으로 판정 없이 진행하는 다른 경로가 생겨도 재사용 가능하다.
- 이 저장소에 프론트엔드 단위 시험 틀(`vitest`)이 처음 들어왔다 — 후속 계획이 화면 로직을 고칠 때 같은 방식(순수 함수 추출 + `*.test.ts`)을 재사용할 수 있다.
- 관측된 별도 결함 2건(위 참조)은 이 계획 범위 밖이며 사장님/오케스트레이터가 처리 방향을 이미 정했다.
- 블로커 없음 — Phase 11의 다음 계획(11-07)으로 바로 이어갈 수 있다.

## Self-Check: PASSED

- 파일 존재: `src/gptrpg/agents/context.py`, `src/gptrpg/web/routes_actions.py`, `src/gptrpg/cli/turn_flow.py`, `src/gptrpg/turn/judgments.py`, `tests/test_web_actions.py`, `tests/test_cli.py`, `frontend/src/labels.ts`, `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/panes/ChatPane.tsx`, `frontend/src/session/groupTurns.ts`, `frontend/src/panes/StoryPane.tsx`, `frontend/src/components/TurnCard.tsx`, `frontend/src/session/groupTurns.test.ts` 전부 확인됨
- 커밋 존재: `790f17e`, `217e618`, `8a4aaac` 전부 `git log --oneline --all`에서 확인됨
- 인용한 시험 함수 이름 전부 `grep`으로 실재 확인됨(`test_proceed_*`, `test_no_check_tier_*`, `groupTurns.test.ts`의 4개 `it(...)`)
- 마감 전 재검증: `uv run pytest -q` 902 passed, `uv run lint-imports` 4 kept/0 broken, `cd frontend && npx tsc --noEmit` 종료 코드 0, `cd frontend && npx vitest run` 4 passed

---
*Phase: 11-rulebook-vocabulary*
*Completed: 2026-08-17*

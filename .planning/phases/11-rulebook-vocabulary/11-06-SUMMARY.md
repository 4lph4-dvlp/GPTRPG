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
  - "ActionClassified 사건(판 7) + GameState.declare_no_check — 분류 결정을 사건에서 다시 접어 확인하는 durable 표"
  - "SessionActor.VerifyProceedEligibility/ProceedEligible — proceed()·CLI no_check 갈래 전용 서버 쪽 이중 검사(소유권+tier), T-11-29"
affects: [11-07, phase-12]

# Actuals (#2632)
actuals:
  tokens: 27090
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: [vitest]
  patterns:
    - "웹/CLI 두 호출부 동시 반영 관례(10-05가 세움)를 proceed()에도 적용 — routes_actions.py·turn_flow.py가 Task 1 한 커밋(790f17e)에 함께 들어간다"
    - "proceed()가 confirm()의 판정 이후 구간을 거울처럼 복제하되 ConfirmAction/ResolveCheck를 제출하지 않는다 — caused_by_seq가 confirm_seq/resolve_seq 대신 declare_seq 하나로 고정된다"
    - "이야기 화면 가시성 판단(isVisibleTurn)이 사건 모양(「선언+서사, 확인 없음」)만으로 턴 자격을 판단 — 새 이벤트 타입 없이도 화면이 새 경로를 표현한다"
    - "라우트 계층 검사(신원)만으로는 부족한 자리에 액터 계층 이중 검사를 추가하는 관례(_prepare_confirm의 declare_owners 검사)를 proceed()에도 확장 — 성공을 예외(ProceedEligible)로 표현해 사건을 안 남기는 「확인만 하는 명령」 패턴을 AlreadyOccupied/AlreadyConfirmed에서 세 번째로 재사용"

key-files:
  created:
    - frontend/src/session/groupTurns.test.ts
  modified:
    - src/gptrpg/agents/context.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/cli/turn_flow.py
    - src/gptrpg/turn/judgments.py
    - src/gptrpg/event_log/schema.py
    - src/gptrpg/rules_core/reducer.py
    - src/gptrpg/session_actor/actor.py
    - tests/test_web_actions.py
    - tests/test_cli.py
    - tests/test_session_actor.py
    - tests/test_turn_tracer.py
    - tests/test_event_schema_migration.py
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
  - "[코드 리뷰에서 발견된 차단 결함, Rule 1 - Bug] tier를 ActionDeclared에 얹지 않고 새 사건 ActionClassified(판 7)로 분리했다 — DeclareAction은 classify() 호출 전에 이미 제출되므로(MEAS-04, 분류가 실패해도 원문은 남는다) tier를 그 사건 자신에 담을 수 없다. AiInvoked에 끼워 넣는 대안 대신 단일 목적 사건을 새로 만들었다(이 저장소가 SceneIllustrated/CharacterOccupied/SafetyFlagged에서 반복한 관례) — 아래 Deviations에 상세 근거"
  - "옛 기록(action_classified 사건이 없는 declare_seq) 처리: declare_owners의 '모르면 통과' 관례를 따르지 않고 '모르면 거부'를 택했다 — 통과시키면 이 수정이 막으려는 구멍(판정이 필요한 선언을 판정 없이 진행)이 판 7 이전 기록·미분류 기록에 대해 그대로 다시 열린다. GameState.declare_no_check와 SessionActor._prepare_verify_proceed_eligibility 도크스트링에 근거를 명시했다"

patterns-established:
  - "화면 가시성 판단과 사건 존재 여부를 분리 — `isVisibleTurn`이 `turn.confirmed`(판정 경로)와 `turn.narration.length`(무판정 경로) 두 독립 신호를 or로 묶어, 새 이벤트 종류 없이 새 턴 모양을 화면이 표현하게 한다"
  - "TurnCard가 '이미 보이는 턴' 전제 위에서 confirmed===null을 '판정이 원래 없는 턴'으로 해석 — 대기 상태(판정을 기다리는 중)와 무판정 상태를 구조적으로 구분한다"
  - "새 안전 검사가 필요로 하는 신호(no_check 여부)만 딱 사건에 담고 화면이 이미 아는 값(tier 전체)은 서버 상태에 중복해서 안 담는다 — ActionClassified가 boolean 하나만 갖는 이유"

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
  - id: D10
    description: "[차단 결함·수정] 판정이 필요한 것으로 분류된 선언(tier != no_check)에 /proceed(웹)·CLI no_check 갈래를 불러도 판정을 건너뛸 수 없다 — 사건-접은 declare_no_check 표가 서버 재시작 뒤에도 이 판단을 지킨다(T-11-29)"
    verification:
      - kind: unit
        ref: "tests/test_session_actor.py::test_proceed_on_declare_that_needed_a_check_is_rejected_and_appends_nothing, ::test_proceed_on_never_classified_declare_is_rejected_and_appends_nothing"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py::test_proceed_on_declare_that_needed_a_check_returns_400_and_appends_nothing (오케스트레이터가 재현한 정확한 시나리오)"
        status: pass
      - kind: other
        ref: "실제 서버(포트 8000, .env.local)에 라이브 재현 — declare(\"적을 칼로 벤다\") 후 tier=single, 그 declare_seq로 /proceed 호출 -> 400 \"이 선언은 판정이 필요해 판정 없이 진행할 수 없다\"(수정 전에는 200)"
        status: pass
    human_judgment: false
  - id: D11
    description: "[차단 결함·수정] 다른 캐릭터가 낸 선언에는(설령 no_check로 분류됐어도) 진행할 수 없다 — 라우트 계층의 신원 대조(「내 캐릭터인가」)만으로는 못 잡던 우회를 액터의 declare_owners 재확인이 막는다"
    verification:
      - kind: unit
        ref: "tests/test_session_actor.py::test_proceed_on_another_characters_declare_is_rejected_and_appends_nothing"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py::test_proceed_on_another_characters_declare_returns_400_and_appends_nothing"
        status: pass
    human_judgment: false
  - id: D12
    description: "정상 경로(no_check + 본인 선언)는 새 이중 검사가 들어간 뒤에도 계속 통과한다 — 안전 검사가 정상 흐름을 막지 않는다"
    verification:
      - kind: unit
        ref: "tests/test_session_actor.py::test_proceed_eligible_for_own_no_check_declare_raises_proceed_eligible"
        status: pass
      - kind: integration
        ref: "tests/test_web_actions.py::test_proceed_on_own_no_check_declare_still_returns_200, ::test_proceed_narrates_without_resolve_check(재확인)"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py::test_no_check_tier_produces_narration_without_check(재확인 — CLI no_check 경로도 새 검사와 함께 계속 통과)"
        status: pass
    human_judgment: false

# Metrics
duration: ~4시간 (Task 3 사람 확인 대기 + 재작업 두 왕복 포함, 순수 실행 시간은 더 짧다)
completed: 2026-08-17
status: complete
---

# Phase 11 Plan 06: 「굴리지 않는다」를 막다른 길에서 정식 경로로 바꾼다 Summary

**`POST /sessions/{id}/proceed`(웹)와 `turn_flow.py`의 `no_check` 갈래(CLI)가 같은 커밋에서 판정 없이 서술로 잇는 경로를 열었고, 화면 세 곳이 함께 갈라졌으며, 사후 코드 리뷰에서 나온 「판정 건너뛰기」 차단 결함을 서버 쪽 이중 검사(사건-접은 소유권+분류 결과)로 막았다 — 사람 확인 관문에서 실제 브라우저로 통과했다**

## Performance

- **Duration:** ~4시간 (Task 3 사람 확인 대기 + 재작업 두 왕복 포함)
- **Completed:** 2026-08-17
- **Tasks:** 3 (Task 1·2 자동, Task 3 사람 확인 관문) + 관문에서 드러난 화면 결함 1건 + 사후 코드 리뷰에서 드러난 차단 결함 1건, 총 2건 수정
- **Files modified:** 21개 (신규 파일 1개: `frontend/src/session/groupTurns.test.ts`)

## Accomplishments

- `src/gptrpg/web/routes_actions.py`에 `POST /sessions/{session_id}/proceed`가 신설됐다 — `confirm()`의 판정 이후 구간(병렬 세 판단 → `RecordAiCall` → `narrate()` 스트림 → 조각 제출 → 배경 시계 조건 검사)을 거울처럼 따라가되 `ConfirmAction`/`ResolveCheck`를 제출하지 않는다. `caused_by_seq`는 전부 `declare_seq` 하나로 고정된다 — 이 경로엔 확인·판정 사건이 없다(결정 1, PLAN.md).
- `src/gptrpg/cli/turn_flow.py`의 `no_check` 갈래가 `unclear`에서 분리됐다 — `_proceed_without_check()`가 CLI 방식으로 같은 순서를 밟아 서사를 화면에 찍는다. 두 파일은 **같은 커밋**(`790f17e`)에 들어갔다(10-05가 세운 웹/CLI 동시 반영 관례).
- `src/gptrpg/agents/context.py`에 `NO_CHECK_SUMMARY` 상수가 신설됐다 — 판정이 없는 턴의 `check_summary` 자리에 플레이어 원문 대신 플랫폼 고정 문장을 넣어 SAFE-03의 원문 울타리 우회 경로를 막는다.
- `frontend/src/panes/ChatPane.tsx`가 확인 화면을 세 갈래로 나눴다 — `unclear`(다시 쓰기), `no_check`(안내 + [이대로 진행] 하나, 후보·다시 쓰기 버튼 없음), `single`/`several`(기존 후보 버튼). 파일 상단 도크스트링도 "판정으로 가는 통로 하나 + 판정 없이 이어지는 통로 하나"로 갱신됐다.
- **Task 3 사람 확인 관문에서 화면 결함 1건이 드러나 고쳤다** — 상세는 아래 Deviations. `frontend/src/session/groupTurns.ts`의 `isVisibleTurn`(옛 `isConfirmedTurn`)이 확인 사건 없이도 서사가 있는 턴(=proceed 경로)을 이야기 화면에 올리도록 넓어졌고, `frontend/src/components/TurnCard.tsx`가 그 턴에서 「판정을 기다리는 중」 가짜 대기 표시를 안 그리도록 고쳐졌다. 이 저장소 최초의 프론트엔드 단위 시험(`vitest`)이 함께 들어왔다.
- **사람 확인 관문(Task 3)이 재작업 뒤 실제 브라우저로 통과했다** — 「문을 연다」→[이대로 진행]→서사 전문이 실제로 나옴, 「asdf 랄라 뿅뿅」→여전히 「다시 쓰기」, 「판정을 기다리는 중」 가짜 대기 없음, 이 세 가지를 사장님이 직접 확인했다.
- **마감 후 코드 리뷰에서 차단(blocking) 등급 결함이 드러나 고쳤다** — 상세는 아래 Deviations. `POST /proceed`가 라우트 계층 신원 대조(「내 캐릭터인가」)만 하고 「이 선언이 실제로 이 캐릭터가 낸 것인가」·「이 선언이 실제로 no_check로 분류됐는가」는 확인하지 않아, 판정이 필요한 행동을 선언한 뒤 판정을 통째로 건너뛸 수 있었다. `ActionClassified` 사건(판 7)이 분류 결정을 사건에 durable하게 남기고, `SessionActor.VerifyProceedEligibility`가 사건에서 접은 `declare_owners`/`declare_no_check` 두 표로 서버 재시작 뒤에도 성립하는 이중 검사를 한다 — `_prepare_confirm`의 소유권 검사와 같은 근거(D-11).

## Task Commits

각 태스크를 개별 커밋했다:

1. **Task 1: 판정 없이 서술로 가는 경로를 웹과 CLI에 같은 커밋으로 낸다** — `790f17e` (feat)
2. **Task 2: 화면에서 「판정 없이 진행」과 「다시 쓰기」를 가른다** — `217e618` (feat)
3. **Task 3: 「문을 연다」를 실제로 쳐 보고 이야기가 이어지는지 확인** — 사람 확인 관문, 코드 변경 없음. 1차 확인에서 이야기 화면 결함을 발견해 재작업으로 이어짐(아래 참조)

재작업 1(Task 3 관문에서 드러난 이야기 화면 결함 수정) — `8a4aaac` (fix)
재작업 2(마감 후 코드 리뷰에서 드러난 「판정 건너뛰기」 차단 결함 수정) — `da0a758` (fix)

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
- `src/gptrpg/event_log/schema.py` - `EVENT_SCHEMA_VERSION` 6→7, `ActionClassified` 사건 신설(`no_check` 불리언 하나)
- `src/gptrpg/rules_core/reducer.py` - `GameState.declare_no_check` 표 신설, `action_classified` 분기(같은 커밋, 08-CONTEXT.md D-06 관례)
- `src/gptrpg/session_actor/actor.py` - `RecordActionClassification`/`VerifyProceedEligibility` 명령, `ProceedEligible` 예외, 두 `_prepare_*` 신설
- `tests/test_session_actor.py` - 액터 계층 회귀 시험 5건(`..._is_rejected_and_appends_nothing` 관례 포함)
- `tests/test_turn_tracer.py` - 사건 인과 사슬 시험이 `action_classified`를 포함하도록 인덱스 갱신
- `tests/test_event_schema_migration.py` - `EVENT_SCHEMA_VERSION == 7` 고정 시험으로 갱신(옛 6 고정 취지는 유지, 실제 값만 갱신)

## Decisions Made

- **`proceed()`의 `caused_by_seq`를 전부 `declare_seq`로 고정했다** — 이 경로엔 `confirm_seq`/`resolve_seq`가 없다(결정 1, PLAN.md). 배경 시계 조건 검사(`AdvanceClock`)의 `caused_by_seq`도 `declare_seq`를 가리킨다.
- **`check_summary` 자리에 `NO_CHECK_SUMMARY` 고정 문장을 쓴다** — 판정이 없으므로 판정 요약이 없고, 플레이어 원문을 넣으면 SAFE-03의 원문 울타리를 우회하는 경로가 생긴다(결정 3, PLAN.md).
- **`no_check` 화면에 「다시 쓰기」 버튼을 두지 않는다**(결정 2, PLAN.md) — 정식 경로를 예외처럼 보이게 만들지 않기 위해서다.
- **`isConfirmedTurn`을 `isVisibleTurn`으로 이름·뜻을 넓혔다** — 확인됨(player_confirmed) **또는** 서사가 있음(narration.length > 0) 둘 중 하나면 이야기 화면에 카드로 올라간다. 「사람이 누른 것만 서사로 간다」(D-10 결정 2)는 두 경로 다 지켜진다 — `narration`이 채워지는 유일한 통로가 `confirm()`/`proceed()`이고 둘 다 사람이 버튼을 눌러야 서버가 부른다.
- **tier를 `ActionDeclared`에 얹지 않고 새 사건 `ActionClassified`로 분리했다.** `DeclareAction`은 `classify()` 호출 **전에** 이미 제출된다(MEAS-04 — 분류가 실패해도 플레이어 원문은 이미 기록돼 있어야 한다, `declare()` 도크스트링의 기존 규율). 그래서 tier는 애초에 `action_declared` 사건 자신에 담을 수 없다 — 분류가 끝난 뒤 별도 사건으로 남겨야 한다. `AiInvoked`(분류기 호출 텔레메트리)에 `tier` 필드를 끼워 넣는 대안도 고려했으나, 그 사건의 뜻(호출 계측)과 이 사건의 뜻(도메인 분류 결정)이 다르고, 이 저장소가 `SceneIllustrated`/`CharacterOccupied`/`SafetyFlagged`에서 반복해 온 관례(단일 목적 사건을 새로 연다)를 따르는 편이 더 정직하다고 판단했다. 사건에는 `no_check` 불리언 하나만 남긴다 — `single`/`several`/`unclear`의 구분은 이미 웹 응답의 `tier` 칸이 하고 있어 서버 상태에 중복해서 담을 이유가 없다(YAGNI).
- **옛 기록(`action_classified` 사건이 없는 `declare_seq`)은 거부한다 — `declare_owners`의 "모르면 통과" 관례와 반대다.** `declare_owners`가 소유자를 모르면 통과시키는 이유는 캐릭터 개념이 아예 없던 호출부(CLI 등)의 정당한 「모른다」이기 때문이다. 이 표의 "모른다"는 뜻이 다르다 — "이 선언이 실제로 `no_check`로 분류됐다는 증거가 없다"는 뜻이고, 이것을 통과시키면 이 수정이 막으려는 구멍(판정이 필요한 선언을 판정 없이 진행)이 판 7 이전 기록이나 (`get_character`가 400을 내는 등) 분류가 끝나기 전에 요청이 끊긴 드문 경로에 대해 그대로 다시 열린다. 안전 쪽으로 기울인 명시적 선택이다.

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

**3. [Rule 1 - Bug, 마감 후 코드 리뷰에서 발견 — 차단(blocking) 등급] `POST /proceed`로 판정을 통째로 건너뛸 수 있었다**
- **Found during:** 11-06 마감 후 코드 리뷰. 오케스트레이터가 실제 서버로 재현: `POST /actions/declare {"raw_text":"적을 칼로 벤다"}` → `tier: "single"`(판정 필요) → 그 `declare_seq`로 `POST /proceed` → HTTP 200, 서사 6조각. 주사위 없이 결과만 받아갔다.
- **Issue:** 두 갈래 원인이 겹쳐 있었다. ① `proceed()`는 액터에 명령을 제출하지 않으므로 `_prepare_confirm`이 하는 선언 소유권 검사(`declare_owners` 대조)를 통째로 건너뛴다 — 라우트 계층의 `identity.character_id != body.character_id` 검사는 「내가 이 캐릭터의 주인인가」만 보고 「이 선언을 이 캐릭터가 냈는가」는 안 본다. ② `action_declared` 사건 payload에 `tier`가 없어, 서버가 어떤 `declare_seq`가 정말 `no_check`로 분류됐는지 확인할 자체 수단이 없었다 — 클라이언트가 보낸 `declare_seq` 하나만 믿는 구조였다.
- **Fix:** `ActionClassified` 사건(판 7, `no_check` 불리언 하나)을 신설해 `declare()`(웹)·`_turn_flow()`(CLI) 둘 다 분류기 `RecordAiCall` 바로 뒤에 제출한다. `GameState.declare_no_check`가 이를 접어 durable 표로 남긴다(서버 재시작에도 살아남는다, `declare_owners`와 같은 이유). `SessionActor.VerifyProceedEligibility`(성공 시 사건을 안 남기는 「확인만 하는 명령」 — `ProceedEligible` 예외로 성공을 알린다, `AlreadyOccupied`/`AlreadyConfirmed`와 같은 패턴)가 `declare_owners`(소유권)와 `declare_no_check`(tier) 둘 다 확인한 뒤에야 `proceed()`/CLI `_proceed_without_check`가 이어진다. 옛 기록·미분류 기록(`declare_no_check`에 없음)은 **거부**한다 — `declare_owners`의 "모르면 통과" 관례와 반대 방향의 명시적 선택이다(위 Decisions 참조, 이유 포함).
- **Files modified:** `src/gptrpg/event_log/schema.py`, `src/gptrpg/rules_core/reducer.py`, `src/gptrpg/session_actor/actor.py`, `src/gptrpg/web/routes_actions.py`, `src/gptrpg/cli/turn_flow.py`, `tests/test_session_actor.py`(신규 시험 5건), `tests/test_web_actions.py`(신규 시험 3건), `tests/test_turn_tracer.py`, `tests/test_event_schema_migration.py`
- **Verification:** `uv run pytest -q` 927 passed(902→919→927, 재작업마다 시험 추가), `uv run lint-imports` 4 kept/0 broken. 실제 서버(포트 8000, `.env.local`, `nemotron-3-ultra-550b`)에 라이브 재현 — 수정 전 시나리오를 그대로 다시 돌려 `declare` → `tier: "single"` 확인 후 그 `declare_seq`로 `/proceed` → **400** `"이 선언은 판정이 필요해 판정 없이 진행할 수 없다"`(수정 전에는 200)를 직접 확인했다.
- **Committed in:** `da0a758`

---

**Total deviations:** 3 auto-fixed (Rule 2 - Missing Critical 2건 `8a4aaac`, Rule 1 - Bug 1건 `da0a758`)
**Impact on plan:** 셋 다 계획서 자신의 목표(판정 없이 이어지는 정식 경로를 안전하게 연다)를 실제로 충족시키는 데 구조적으로 불가피했다 — 범위 이탈이 아니라, 계획 단계·1차 구현이 빠뜨린 것을 채운 것이다. 특히 3번은 계획서 자신의 위협 모델(T-11-20~T-11-24)이 신원 대조는 다뤘지만 "선언 소유권"·"분류 결과 보존" 두 갈래를 별도로 짚지 않았던 간극이다.

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
- `EVENT_SCHEMA_VERSION`이 7이다 — 후속 계획이 사건 스키마를 또 바꾸면 8로 올리고 같은 관례(옛 판 해석 경로 + `rules_core/reducer.py` 분기 같은 커밋)를 따른다.
- `SessionActor.VerifyProceedEligibility`/`ProceedEligible` 패턴("사건을 안 남기는 확인 명령은 예외로 성공을 알린다")이 세 번째 사례가 됐다 — 앞으로 비슷한 "검증만 하고 쓰지 않는" 명령이 필요하면 이 관례를 그대로 재사용할 수 있다.
- 관측된 별도 결함 2건(서사 언어 오염·무브 선택 정확도, 위 참조)은 이 계획 범위 밖이며 사장님/오케스트레이터가 처리 방향을 이미 정했다.
- 블로커 없음 — Phase 11의 다음 계획(11-07, 이미 병렬로 완료됨)으로 바로 이어갈 수 있다.

## Self-Check: PASSED

- 파일 존재: `src/gptrpg/agents/context.py`, `src/gptrpg/web/routes_actions.py`, `src/gptrpg/cli/turn_flow.py`, `src/gptrpg/turn/judgments.py`, `src/gptrpg/event_log/schema.py`, `src/gptrpg/rules_core/reducer.py`, `src/gptrpg/session_actor/actor.py`, `tests/test_web_actions.py`, `tests/test_cli.py`, `tests/test_session_actor.py`, `tests/test_turn_tracer.py`, `tests/test_event_schema_migration.py`, `frontend/src/labels.ts`, `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/panes/ChatPane.tsx`, `frontend/src/session/groupTurns.ts`, `frontend/src/panes/StoryPane.tsx`, `frontend/src/components/TurnCard.tsx`, `frontend/src/session/groupTurns.test.ts` 전부 확인됨
- 커밋 존재: `790f17e`, `217e618`, `8a4aaac`, `da0a758` 전부 `git log --oneline --all`에서 확인됨
- 인용한 시험 함수 이름 전부 `grep`으로 실재 확인됨(`test_proceed_*`, `test_no_check_tier_*`, `groupTurns.test.ts`의 4개 `it(...)`, `test_session_actor.py`의 신규 5개 `async def test_*`)
- 마감 전 재검증: `uv run pytest -q` 927 passed, `uv run lint-imports` 4 kept/0 broken, `cd frontend && npx tsc --noEmit` 종료 코드 0, `cd frontend && npx vitest run` 4 passed

---
*Phase: 11-rulebook-vocabulary*
*Completed: 2026-08-17*

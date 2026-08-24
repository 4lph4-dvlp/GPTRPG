# Phase 13: 장면 — 오프닝과 대상 - Research

**Researched:** 2026-08-24
**Domain:** 내부 백엔드(에이전트 파이프라인) + 프런트엔드 연동 — 외부 라이브러리 도입 없음
**Confidence:** HIGH (전부 실제 코드를 이 세션에서 직접 읽고 확인함, 신규 패키지 없음)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**오프닝이 뜨는 순간**

- **D-01:** 오프닝은 전원 동의로 파티 명단이 잠기는 순간에 뜬다 — `party_roster_locked`
  사건이 그 신호다. 「첫 사람이 완성한 순간」이 아니다. 동의 직후 빈 화면이 생기는 틈이 없다는
  것이 이 선택의 핵심 이득이다.
- **D-02:** 오프닝 AI 호출은 화면이 부르고 서버가 중복을 막는다 — Phase 12.3의 D-12와 같은
  모양. **서버가 스스로 부르지 않는다**(배경에서 혼자 도는 장치를 만들지 않는다).
- **D-03:** 「겹친 요청이 AI를 두 번 부른다」를 이 단계에서 같이 닫는다(접힌 할 일). 큐 밖
  사전 검사를 큐 안 검사로 대체하거나 세션당 뮤텍스로 좁힌다 — 네 경로가 전부 같은 모양이라
  한 자리를 고치면 넷 다 닫힌다(라우트마다 가드를 하나씩 다는 방식은 쓰지 않는다). 채택하지
  않는 것: 「방장 탭만 부른다」는 프런트엔드 완화책(사장님이 2026-08-23에 거부). —
  Reversibility: costly.
- **D-04:** 늦게 접속했거나 잠시 나갔다 돌아온 사람은 기록을 올려 오프닝을 본다. 재생·강조
  장치를 만들지 않는다.

**오프닝 글을 누가 쓰나 — ARCH-02 벽을 넘는 법**

- **D-05:** 상황만 적혀 있는 시나리오에서는, 상황 판단 담당이 시나리오를 읽고 좁혀 서술
  담당에게 넘긴다. 서술 담당은 시나리오 원문을 계속 못 본다 — 지금 판정 턴이 이미 돌아가는
  방식 그대로다(`situation_judge` → `scene_summary`/`facts` → `master_gm.narrate`).
  채택하지 않은 둘: ① 서술 담당에게 예외를 준다(타입 차원에서 막아 둔 문을 다시 여는 일) ②
  오프닝 전용 역할 신설(AI 역할이 다섯에서 여섯으로 늘어남). ⚠️ 조사·계획이 반드시 풀 것:
  오프닝에는 직전 장면이 없다 — `situation_judge`는 「이번 판정으로 확정된 사실」을 뽑는
  구조라 좁힐 재료 자체가 다르다. 오프닝용 입력 묶음을 따로 만들어야 한다. — Reversibility:
  costly.
- **D-06:** 완성된 낭독문이 적혀 있는 시나리오는 그대로 띄우고 AI를 아예 안 부른다 — 비용
  0, 문장 틀어질 위험 없음. 낭독문형(고전 D&D 모듈, *Call of Cthulhu*)과 메모형(던전월드
  전선, OSR 샌드박스)이 각각 D-06·D-05로 갈린다 — 어느 한쪽을 기본값으로 강제하지 않는다.
- **D-07:** 낭독문의 다섯 요소는 시나리오를 등록하는 시점에 검사하고, 안 담았으면 등록을
  거부한다 — D-06이 AI를 안 부르므로 플레이 중에는 다시 만들 수단이 없다. 본이 이미 있다:
  `validate_registered_rulebooks`. 다섯 요소: 내가 누구인지 / 지금 보이고 들리는 구체적인
  것 / 지금이 왜 중요한지 / 잡을 수 있는 실마리 최소 하나 / 규칙 용어 없는 열린 초대. ⚠️
  조사가 판단할 것: 이 다섯을 기계가 어떻게 검사하는가 — ⓐ 시나리오 선언에 칸을 나눠 적게
  하고 칸이 비었는지만 본다(기계적, 확실) ⓑ 등록 시점에 AI가 한 번 읽고 판정한다(유연,
  등록이 AI에 의존). ⓐ가 D-18의 「룰북과 같은 모양」과 정합한다.
- **D-08:** AI가 만든 오프닝은 나가기 전에 다섯 요소를 검사한다 — 서사가 이미 거치는 네
  갈래 검사(`agents/narration_guard.py`)에 한 갈래를 더한다. 걸리면: 한 번 다시 만들고,
  그래도 안 되면 D-09로 떨어진다.
- **D-09:** 오프닝 AI 호출이 실패하면 시나리오 원문을 그대로 띄운다 — 이 단계의 목표가
  「빈 화면에서 시작하지 않는다」다. 12.3 D-13과의 관계: 오프닝은 폴백이 있으므로 세 실패
  중 ①(AI가 이상하게 답함)만 안내가 아니라 원문 표시로 끝난다. ②(설정 없음, 503)·③(연결
  끊김)은 12.3 처리를 그대로 따른다.
- **D-10:** 「내가 누구인지」는 새 장치를 만들지 않는다 — 동의 직전 진행자의 「당신은
  …입니다」 한 문장 정리(12.1 D-10, CHAR-03)가 오프닝 바로 위 화면에 이미 있다.

**장면의 수명**

- **D-11:** 「장면 전환」 개념을 이 단계에서 만들지 않는다 — 세션 전체를 한 장면으로 본다.
  「나와서 확정된 것」은 세션 내내 쌓이기만 한다. SCENE-03의 「이번 장면에서 이미 등장해
  확정된 것」은 이 결정 아래에서 「이번 세션에서 등장해 확정된 것」이 된다. SCENE-05는 이
  결정과 충돌하지 않는다 — 명부는 D-14~D-16이 따로 만들고, 장면 전환이 없어도 명부는
  필요하다. 미룬 것은 잃은 것이 아니다 — 장면 전환은 Deferred Ideas에 남긴다.
- **D-12:** 확정 목록은 기록에 전부 남기되, AI에게 넘기는 것은 최근 것으로 상한을 둔다 —
  D31·D-66의 「에이전트별 각자 상한」 규율. **Claude's Discretion**: 상한값 자체와 「최근」의
  기준(등장 순서인가 마지막 언급 순서인가).

**세 층 밖의 것을 지목했을 때**

- **D-13:** 「이건 어느 층에도 없다」를 굴리기 전과 뒤 둘 다 판단한다. ① 굴리기 전(분류
  시점): 행동을 분류할 때 「누구를·무엇을 상대로」를 함께 고르게 한다 — 본이 이미 있다:
  소지품 사용(`item_use`, RULE-16, 12-06 Task 3)이 새 AI 역할 없이 분류기 출력에 칸 하나를
  더한 방식. ② 굴린 뒤: 이미 있는 `scene_entity_judge`의 결과를 받아서 확정 목록에 쌓는다 —
  지금은 판단만 하고 아무도 안 받아 버려지고 있다. 왜 둘 다인가: ①만 하면 서술이 만든
  인물이 목록 밖에 남아 다음 턴에 「없는 사람」이 된다. ②만 하면 플레이어가 없는 사람을
  지목하는 것을 여전히 아무도 확인하지 않는다. — Reversibility: costly — 분류기 출력
  형식과 사건 기록이 함께 움직인다.
- **D-14:** 「즉흥 허용」 시나리오에서는 AI가 그 자리에서 만들고 확정 목록에 쌓는다. 사람에게
  되묻지 않는다 — 아포클립스 월드 계열에서 이것이 정상 플레이다. 쌓이는 것이 핵심이다 —
  「주목을 부른다」로 생긴 주목이 다음 턴에도 거기 있다. 매번 확인을 안 받는 이유: 지목할
  때마다 물으면 이야기 흐름이 끊긴다.
- **D-15:** 「즉흥 금지」 시나리오에서는 세계가 이야기로 돌려보낸다. 「여기 그런 건
  없습니다」도, 있는 것 목록을 꺼내 고르게 하는 것도 하지 않는다. 예: 「그쪽을 더듬지만
  손에 잡히는 건 젖은 돌뿐이었다」 — 시스템이 거절하는 느낌이 안 들고, 무엇이 없는지는
  알게 된다. ⚠️ 계획이 반드시 풀 것: 돌려보내는 문장을 쓰려면 AI가 「이건 없다」를 알아야
  한다 — D-13①의 판단 결과가 서술까지 흘러야 한다(D-05의 「상황 판단이 좁혀 넘긴다」 경로
  위에 실린다). 이것을 「대가가 붙는 사실」로 넘길지 별도 칸으로 넘길지가 설계 지점이다.
- **D-16:** 「즉흥 허용 / 금지」는 사람과 사물을 따로 선언한다 — 「없던 물건은 나와도
  되지만 없던 사람은 안 된다」가 실재하는 선언이다(미스터리물·폐쇄된 무대). 대가: 시나리오
  선언 칸이 하나에서 둘로 늘고, 저자가 둘 다 채워야 한다.

**만난 사람 명부**

- **D-17:** 명부에는 이름·종류(사람/사물)·처음 나온 곳만 남긴다. 경계 — Phase 14와의
  분업: 「그 인물과 무슨 일이 있었는지」는 넣지 않는다(Phase 14 MEM-02). 「명부는 하나,
  출생만 표시」: 시나리오가 미리 적은 인물과 도중에 생긴 인물을 같은 목록에 두고 어디서
  왔는지만 칸 하나로 구분한다. ⚠️ 조사가 볼 것: 지금 시나리오 등장인물은 `Entity`로
  표현되고 `THREAT_CAST`에 하드코딩되어 있다. 명부가 `Entity`를 그대로 쓸지 다른 모양일지는
  계획이 판단하되, 상태값 개수에 상한을 두지 않는다(D-21)는 규율을 지킬 것.
- **D-18:** 시나리오 선언 형식을 룰북과 같은 모양으로 만든다 — dataclass 선언 + 등록 시점
  검사. `Rulebook`이 이미 그 본이다. 담을 것: 오프닝(낭독문형/메모형) · 즉흥 허용 여부
  (사람/사물 따로) · 등장인물 · 위협 시계 내용. 지금 상태: `threat_clocks.py`의
  `M0_THREAT_CLOCK` + `THREAT_CAST`가 모듈 상수로 박혀 있고, `scene_prompt.py:45`의
  `WELL_SCENARIO_SETTING`이 「두 번째 시나리오가 생기면 상수를 하나 더 만들어 web이 골라
  넘긴다」고 예고해 뒀다 — 이 단계가 그 예고를 실행한다. — Reversibility: costly.
- **D-19:** 목록에 이미 있으면 AI는 그 목록에서 고른다. 이름을 자유롭게 짓는 것은 「어느
  층에도 없는 것」일 때뿐이다 — 「우물지기 이슬」과 「이슬」이 갈라지는 것을 구조로 막는다.
  본이 이미 있다: 판정에서 무브 이름을 닫힌 목록에서만 고르게 하고, 목록 밖 이름을 내면
  잡아 기록에 남긴다(`UnknownMove`, SAFE-07). `scene_entity_judge`가 이미 절반을 한다 —
  `existing_names`로 이름이 겹치는 것을 거른다. 그 규율을 분류 시점(D-13①)까지 넓힌다.
- **D-20:** 명부가 커져도 매 턴 AI에게 통째로 들어가지 않는다 — 지금 장면에 있는 것만
  넘긴다(D-12와 같은 규율).

**새 시나리오 저작**

- **D-21:** 짧은 시나리오 한 편을 실제로 쓴다 — 「우물 아래의 것」과 무관한, 낭독문형.
  형식이 두 종류를 다 받는다는 것을 실제로 확인하려면 낭독문형 시나리오가 하나는 있어야
  한다. 범위: 짧게 — D-06(낭독문 그대로 띄우기)과 D-07(등록 시점 검사)이 실제로 동작하는지
  보이는 최소.

**「이 개념 안 쓴다」 선언 범위**

- **D-22:** 시나리오는 「대상 검사를 안 쓴다」를 선언할 수 있다. 「오프닝을 안 쓴다」는
  선언할 수 없다 — 오프닝을 끄면 빈 화면 문제가 그대로 돌아온다(이야기는 어떻게든 어디서
  시작한다). 대상 검사는 「누구를 상대로」가 아예 안 중요한 이야기가 실재하므로 끌 수 있다
  (관계·감정 중심 계열). D-67의 「네 항목 전부 안 쓴다를 선언할 수 있어야 한다」를 이 항목에서
  좁힌다 — 오프닝만 예외. 선언하면 관련 화면과 판정 훅이 완전히 사라진다는 규약은 대상
  검사에 그대로 적용한다.

**Folded Todos**

- `.planning/todos/pending/2026-08-23-gm-call-fires-twice-across-tabs.md` — 「겹친 요청이
  AI를 두 번 부른다 — 사전 검사를 큐 안으로 옮긴다」(severity: major). 원 문제: 만들기 화면의
  GM 호출 네 곳(안내·지목·되묻기·정리)이 AI를 부르기 전에 큐 밖에서 「이미 말했나」를 본다.
  두 요청이 겹치면 둘 다 통과해 둘 다 AI를 부른다. 큐 안 재검사(`AlreadyGmSpoken`)가 사건은
  하나로 막아 주지만 AI 호출 비용과 지연이 샌다. 12.3-14가 첫 안내를 자동 발동으로 바꾼 뒤
  참가자 넷이면 네 번이 기본값이 됐다. 왜 이 단계인가: 오프닝(D-01·D-02)이 정확히 같은
  모양의 다섯 번째 자동 발동 호출이다. 파일: `web/routes_creation.py:787·860·993·1129`,
  `session_actor/actor.py:_prepare_gm_spoke`. 설계 잠금과의 관계: 12.3 D-12의 결과(사건
  하나)는 지금 코드가 지키지만 문언(호출 한 번)은 못 지키고 있다.

### Claude's Discretion

- 오프닝을 어떤 사건 종류로 기록하는가 — 기존 `narration_appended`를 그대로 쓸지 새 종류를
  만들지. 새로 만들면 `EVENT_SCHEMA_VERSION`을 올리고 `reducer.py` 분기를 같은 커밋에 낸다
  (이 사고가 `reducer.py` 244~282행에 세 번 주석으로 기록되어 있다).
- 확정 목록·명부를 어디에 담는가 — 사건으로 접어 만들지 별도 상태로 둘지. 단 「상태는
  사건에서 접어 만든다」는 되돌릴 수 없는 구조를 따를 것.
- AI에게 넘기는 상한값들(D-12·D-20)과 「최근」의 기준.
- 다섯 요소 검사를 구조 검사로 할지 AI 판정으로 할지(D-07의 ⓐ/ⓑ) — ⓐ를 권하는 근거는
  D-07에 적었으나 최종 판단은 조사·계획이 한다.
- 분류기의 대상 칸 모양 — 하나만 고르게 할지 여럿 허용할지, 「대상 없음」을 어떻게 표현할지.
- 명령줄(CLI) 대응 여부 — 이 저장소는 「웹과 CLI를 같은 커밋에서 닫는다」가 관례다. 오프닝은
  세션 시작이고 CLI에는 캐릭터 선택·신원 개념이 아예 없다(`cli/turn_flow.py:257-258`).
  12.1·12.3이 이미 같은 예외 판단을 했다. 계획서에 왜 예외인지 근거를 적을 것 — 조용히
  한쪽만 고치는 것이 이 저장소의 알려진 실패 모양이다. 단 대상 검사(D-13)는 판정 턴 안이라
  CLI에도 있다 — 오프닝과 대상은 이 점에서 갈린다.
- 이 단계를 몇 개의 계획으로 쪼갤지.

### Deferred Ideas (OUT OF SCOPE)

- **장면 전환 개념**(D-11이 미룸) — 「무엇이 장면을 넘기는가」. 후보 셋: 상황 판단 담당이
  「장소를 옮겼다」를 판단 / 위협 시계가 한 칸 돌 때 / 사람이 명시적으로 선언. 이 단계가
  만드는 확정 목록의 수명이 그때 세션 단위에서 장면 단위로 좁아진다. 지금 정하면 틀릴
  확률이 높다는 것이 미룬 이유이지, 필요 없다는 것이 아니다.
- **「즉흥 허용/금지」를 장면마다 다르게 선언**(D-16이 사람/사물 축까지만 열었다) — 장면
  축은 D-11이 장면 개념 자체를 미뤘으므로 함께 미뤄진다.
- **오프닝을 캐릭터에 맞춰 손질하기**(D-06이 안 하기로 함) — 낭독문을 재료로 이번 파티에
  맞춰 다시 쓰는 것. 저자의 문장을 지우게 되어 채택하지 않았다.
- **명부에 「있었던 일」까지 남기기**(D-17이 경계를 그음) — Phase 14(관계 장부, MEM-02).
- **화면에 「당신은 OO」 상시 띠**(D-10이 안 하기로 함) — 필요해지면 화면 단독 작업이라
  언제든 붙는다.

**Reviewed Todos (not folded):**
- `2026-08-18-narration-blind-to-resource-change.md` — 판정 뒤 서술의 문제라 오프닝(판정
  없는 서술)과 다른 자리다. Phase 14 쪽.
- `2026-08-18-no-clock-for-good-progress.md` — Phase 15(CLOCK) 소관.
- `2026-08-14-game-breaking-input-sanction.md` — 진행자가 이야기를 미는 문제라 Phase 13.1
  쪽에 가깝다.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCENE-01 | 판정 없이 장면을 여는 경로가 정식 경로로 있다 — 서사 함수의 세 번째 진입점(실제로는 두 번째가 이미 있음, `proceed()`) | `proceed()`(`web/routes_actions.py:1470`)를 본으로 삼아 `declare_seq` 의존을 제거한 변형을 만드는 것이 최소 변경 경로임을 확인(Architecture Patterns "재사용 대상") |
| SCENE-02 | 오프닝이 비경험자용 다섯 요소를 담는다 | D-06(낭독문형, AI 미호출)/D-05(메모형, situation_judge 좁히기) 이원 경로 확인, D-07ⓐ(등록 시점 구조 검사)가 `Rulebook`/`validate_registered_rulebooks` 패턴으로 실제 구현 가능함을 코드로 확인(Architecture Patterns "Rulebook 패턴") |
| SCENE-03 | 3층 대상 관리(시나리오/확정/그 밖) | `turn/context.py:130`의 `scene_entities = THREAT_CAST` 하드코딩 위치를 정확히 특정, `Entity` 그릇 재사용 가능성 확인(Architecture Patterns "Entity — D-17") |
| SCENE-04 | 3층 밖 지목의 결정론적 처리(open/closed) | D-13①(`action_classifier.Proposal.item_use` 선례로 대상 칸 추가), D-13②(`scene_entity_judge.judge_new_entity`가 이미 완성되어 있고 받는 코드만 없음)를 코드로 확인(Architecture Patterns, Don't Hand-Roll) |
| SCENE-05 | 재등장 인물이 명부에서 같은 인물로 인식됨 | `Entity`/`UnknownMove` 패턴을 D-17/D-19의 본으로 확인(Code Examples, Architecture Patterns) |

</phase_requirements>

## Summary

이 단계는 새 프레임워크·라이브러리를 도입하지 않는다. 13-CONTEXT.md가 이미 결정 22건을
확정해 뒀고, 이 문서의 역할은 그 결정들이 실제로 부딪힐 코드 표면을 이 세션에서 직접 읽어
확인하고, CONTEXT.md가 "⚠️ 조사가 반드시 풀 것"으로 남긴 다섯 개의 기술적 공백
(D-05·D-07·D-08·D-15·D-17)에 실제 코드 근거를 붙이는 것이다.

가장 중요한 발견은 D-05다. `situation_judge`(`agents/prompt_assembly.py:587-627`)의 영구
고정 지시문은 "판정 결과와 지금까지의 장면·위협 시계 상태를 보고 ... 이미 정해진 값을 그대로
반영한다"고 명시하고 "시나리오 원문을 그대로 옮겨 적지 않는다"고 못박는다 — 이것은 오프닝이
정확히 반대로 필요로 하는 것이다(D-06 메모형 오프닝은 시나리오 원문을 **좁혀서** 넘겨야
한다). `TurnContext`/`judge_situation`의 **자료구조**는 재사용 가능하지만(빈
`recent_turns`, 자리표시자 `check_summary`), **지시문 텍스트**는 오프닝 전용 갈래가 필요하다
— D-05가 "실제 작업량"이라 부른 것이 바로 이 지시문 분기다.

두 번째 중요한 발견은 D-03이다. `web/routes_creation.py`의 GM 호출 네 곳(`announce_creation`
등)이 이미 "큐 밖 사전 검사 → AI 호출 → 큐 안 재검사(`AlreadyGmSpoken`)" 구조로 되어 있고,
**AI 호출 자체가 큐 제출보다 먼저 일어난다**(`announce_creation`: 806-809행 사전 조회 →
816행 AI 호출 → 818행 큐 제출) — 이것이 겹친 탭이 AI를 두 번 부르는 정확한 지점이다. 이
단계가 오프닝을 다섯 번째 자동 발동 호출로 추가하면 같은 구멍이 다시 뚫린다. 이미 파운 할
일 문서가 해법 방향("큐 밖 사전 검사를 큐 안 검사로 대체하거나, 세션당 뮤텍스로 좁힌다")을
적어 뒀다.

세 번째는 D-18/D-07이다. `rules_core/rulebook.py`의 `Rulebook` dataclass +
`rulebooks/__init__.py`의 `validate_registered_rulebooks()`가 정확히 D-18이 모방하려는
"선언 dataclass + 등록 시점(모듈 import 시점) 검사" 패턴의 실물이다 — 이 패턴이 이미
"빈 값 = 개념 없음"과 "빈 값 = 아직 선언 안 함"을 필드마다 구분하는 관례까지 포함하고 있어
그대로 옮겨 쓸 수 있다.

**Primary recommendation:** 시나리오 선언을 `Rulebook`과 같은 모양(`ScenarioDecl` frozen
dataclass + `SCENARIOS` 등록 딕셔너리 + `validate_registered_scenarios()`)으로 만들고,
오프닝 경로는 `proceed()`(`web/routes_actions.py:1470`)를 본으로 삼되 `declare_seq`
의존과 시나리오 원문 노출 오프닝 지시문 갈래를 새로 얹는다. 대상 3층은
`turn/context.py:130`의 `scene_entities = THREAT_CAST` 하드코딩 자리에 시나리오 선언 +
확정 목록을 합쳐 넣고, 대상 지목(D-13①)은 `action_classifier.Proposal.item_use`
(RULE-16의 선례)와 정확히 같은 모양으로 분류기 출력에 칸 하나를 더한다.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 오프닝 트리거 판단(언제 부를지) | Browser/Client | API/Backend | D-02 — 화면이 부르고 서버가 중복을 막는다. `party_roster_locked` 사건을 프런트가 감지(`CreationScreen`이 이미 이 패턴을 씀, `Notices.tsx:54-58`)해서 `SessionScreen` 마운트 시 호출한다 |
| 오프닝 서술 생성(낭독문형/메모형) | API/Backend | — | `situation_judge`(메모형 좁히기) + `master_gm.narrate`(D-06 메모형만 호출, 낭독문형은 AI 호출 없음) — 순수 백엔드 에이전트 파이프라인 |
| 오프닝 다섯 요소 검사 | API/Backend | — | D-07/D-08 — 등록 시점(구조 검사, ⓐ) 또는 생성 시점(narration_guard류, ⓑ) 둘 다 백엔드. 화면은 검사 결과를 모른다 |
| 3층 대상 관리(시나리오/확정/그 밖) | API/Backend | Database/Storage | `turn/context.py`가 조립, 확정 목록은 사건으로 영속화(Claude's Discretion — 사건 vs 별도 상태) |
| 대상 지목 분류(굴리기 전) | API/Backend | — | `action_classifier`에 칸 추가 — AI 호출 안 늘림(D-13①) |
| 즉흥 판단(굴린 뒤) | API/Backend | — | 이미 있는 `scene_entity_judge` — 이 단계가 받는 쪽만 만든다(D-13②) |
| 명부 화면 표시 | Browser/Client | API/Backend | 명부 자체는 백엔드 상태, 화면은 조회만(스코프 안이라면 — CONTEXT.md는 화면 자체를 이 단계 필수로 못박지 않음, UI hint: yes) |
| GM 호출 중복 방지 | API/Backend | — | D-03 — `session_actor/actor.py` 큐 안(단일 소비자) — 이미 `AlreadyGmSpoken`류 패턴이 존재하는 자리 |

## Standard Stack

**이 단계는 새 외부 패키지를 설치하지 않는다.** 순수 백엔드 dataclass·에이전트 함수·프런트
React 컴포넌트 확장이다. `npm view`/`pip index` 검증 대상 자체가 없다.

### 재사용할 기존 구성요소 (신규 의존성 아님)
| 구성요소 | 파일 | 역할 |
|---|---|---|
| `Rulebook` + `validate_registered_rulebooks` | `rules_core/rulebook.py:635-671`, `rulebooks/__init__.py:62-100+` | D-18 시나리오 선언 형식의 본 |
| `TurnContext`/`NarrationFacts`/`EntityJudgeContext` | `agents/context.py` | 값 객체 패턴 — 오프닝 전용 값 객체가 필요하면 같은 관례(상한 상수 + `__post_init__` 검사)를 따른다 |
| `scene_entity_judge.judge_new_entity` | `agents/scene_entity_judge.py:71-116` | D-13② "받는 쪽"이 소비할 기존 판단 |
| `Proposal.item_use` 패턴 | `agents/action_classifier.py:95-99, 203-229` | D-13① "대상 칸 추가"의 정확한 선례 |
| `UnknownMove`/`UnknownItemFromAI` 흡수 패턴 | `agents/action_classifier.py:44-66, 331-346` | D-19 "닫힌 목록 밖 이름 처리"의 본 |
| `RecordGmSpoke`/`AlreadyGmSpoken` | `session_actor/actor.py:201-215, 1934-1966` | D-02/D-03 중복 호출 방지의 기존 자리 — 그러나 **이 패턴 자체가 지금 겹침을 못 막는다**(아래 Pitfall 1) |
| `narration_guard.inspect_sentence` | `agents/narration_guard.py:218-263` | D-08의 본이지만 **문장 단위** 검사라 다섯 요소(문서 단위 완결성) 검사와 모양이 다르다(아래 Open Questions) |

## Package Legitimacy Audit

**해당 없음 — 이 단계는 외부 패키지를 설치하지 않는다.** 신규 npm/pip 패키지가 없으므로
레지스트리 검증·SLOP/SUS 판정 대상이 없다.

## Architecture Patterns

### System Architecture Diagram

```
[프런트: CreationScreen 폴링]
        │ party_roster_locked 사건 감지 (기존 패턴, Notices.tsx:54-58)
        ▼
[프런트: App.tsx Gate "ready" → SessionScreen 마운트]  (App.tsx:76-86)
        │ 오프닝 아직 없음 감지 (narration_appended 0건)
        ▼
[POST /sessions/{id}/opening]  (신설 — proceed()를 본으로 삼되 declare_seq 없음)
        │
        ├─ 서버: 세션당 오프닝 호출 겹침 방지 (D-03, 큐 안 재검사 필요 — Pitfall 1 참조)
        │
        ▼
[시나리오 선언 조회]  (D-18, SCENARIOS[scenario_id] — Rulebook과 같은 등록소 패턴)
        │
        ├─ 낭독문형(D-06)? ──Yes──▶ 저자 원문을 그대로 narration_appended로 기록, AI 호출 없음
        │
        No (메모형, D-05)
        ▼
[situation_judge 오프닝 갈래]  (build_situation_prompt의 오프닝 전용 지시문 — 신설 필요)
        │  입력: TurnContext(scene_entities=시나리오 캐스트, party_state=잠긴 파티,
        │        recent_turns=(), clock_state=초기 상태)
        ▼
[NarrationFacts 조립]  (build_narration_facts — 기존 함수 재사용, check_summary 자리에
        │                오프닝 표시 상수)
        ▼
[master_gm.narrate()]  (기존 함수 그대로 — NarrationFacts만 받으므로 ARCH-02 안 건드림)
        │
        ▼
[다섯 요소 검사]  (D-07/D-08 — 등록 시점 구조 검사 ⓐ 권장, 생성 시점 검사는 별도 자리 필요)
        │
        ▼
[narration_appended 사건 기록]  (기존 청크 스트리밍 경로 재사용)


[판정 턴 별도 흐름 — 대상 지목]
[action_classifier.classify()]
        │ 기존 칸 + 대상 칸 추가 (D-13①, item_use와 같은 자리)
        ▼
[3층 대조: 시나리오 선언 / 확정 목록 / 그 밖]  (turn/context.py:130 scene_entities 조립부)
        │
        ├─ 목록 안 ──▶ 그 대상으로 판정 진행 (D-19, UnknownMove류 흡수 아님 — 정상 매칭)
        │
        └─ 목록 밖 ──▶ 시나리오의 open/closed 선언(D-16, 사람/사물 축 분리) 확인
                ├─ open ──▶ 정상 진행, scene_entity_judge 결과(D-13②)가 확정 목록에 쌓임
                └─ closed ──▶ 결정론적 되돌림 문장 (D-15 — situation_judge가 "없음"
                              사실을 서술에 넘기는 채널 필요, 아래 Open Questions)
```

### 재사용 대상 — `proceed()`를 본으로 삼는 이유

`web/routes_actions.py:1470`의 `proceed()`(CONTEXT.md가 `_proceed_without_check`로 부르는
함수)가 이미 "판정 없이 서술까지 가는" 전체 파이프라인을 완성해 뒀다:

```python
# 출처: src/gptrpg/web/routes_actions.py:1499-1521 (신원 검증 + 소유권 재확인)
identity = read_identity(request, session_id)
if identity is None or identity.character_id != body.character_id:
    raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")
...
try:
    await actor.submit(
        VerifyProceedEligibility(
            declare_seq=body.declare_seq,
            character_id=identity.character_id,
        )
    )
except ProceedEligible:
    pass  # 검증 통과 — 그대로 진행한다.
```

```python
# 출처: src/gptrpg/web/routes_actions.py:1581-1599 (병렬 판단 묶음 호출)
judgments = await gather_turn_judgments(
    situation_provider=situation_provider,
    ...
    ctx=ctx,
    check_summary=NO_CHECK_SUMMARY,
    rulebook_display_name=rulebook.display_name,
    outcome_list=OutcomeList(categories=()),
    grade_band=_NO_CHECK_GRADE_BAND,
    resource_axes=rulebook.resource_axes,
)
```

```python
# 출처: src/gptrpg/web/routes_actions.py:1660-1676 (서술 조립·호출)
facts = build_narration_facts(ctx=ctx, check_summary=NO_CHECK_SUMMARY, judgments=judgments)
narration_iter = narrate(
    provider=gm_provider,
    model=gm_choice.model,
    facts=facts,
    rulebook_display_name=rulebook.display_name,
    resource_axes=rulebook.resource_axes,
)
```

**오프닝 경로가 이 함수와 다른 지점은 정확히 셋이다:**
1. `body.declare_seq` 의존 제거 — 오프닝에는 앞선 선언 사건이 없다.
2. `ctx` 조립 시 `recent_turns=()`가 자연히 나온다(`build_turn_context`가 `action_declared`/
   `narration_appended` 사건에서 텍스트를 뽑는데, 오프닝 시점엔 둘 다 없다) — 이건 코드
   변경 없이 이미 성립한다.
3. **`gather_turn_judgments` 내부 `judge_situation` 호출이 쓰는 지시문(`build_situation_prompt`)이
   "판정 결과를 반영하라"는 전제로 쓰여 있다** — 이것이 D-05가 "실제 작업량"이라 부른 부분이다
   (아래 Open Questions #1).

### Rulebook 패턴 — D-18/D-07ⓐ가 그대로 모방할 본

```python
# 출처: src/gptrpg/rules_core/rulebook.py:635-671 (필드 기본값 관례 확인)
@dataclass(frozen=True)
class Rulebook:
    rulebook_id: str
    display_name: str
    resolution_method: str
    grade_bands: tuple[GradeBand, ...]
    resource_axes: tuple[ResourceAxisDecl, ...]
    check_trigger_mode: CheckTriggerMode
    difficulty_levels: tuple[DifficultyLevelDecl, ...] = ()
    """... 기본값 빈 튜플이 「이 룰북에는 그 개념이 없다」다 ..."""
    outcome_list: OutcomeList = OutcomeList(categories=())
    """... 기본값(빈 목록)이 「이 룰북에는 그 개념이 없다」다 ..."""
    creation_steps: tuple[CreationStepDecl, ...] = ()
    """... 기본값 빈 튜플의 뜻은 **「아직 선언하지 않았다」**이고
    「이 룰북에는 그 개념이 없다」가 아니다 ..."""
    party_size_range: PartySizeRange | None = None
    """... 기본값 `None`의 뜻은 **「아직 선언하지 않았다」**이고
    「이 룰북에는 그 개념이 없다」가 **아니다** ..."""
```

```python
# 출처: src/gptrpg/rulebooks/__init__.py:22-26, 62-100 (등록소 + 등록 시점 검사)
RULEBOOKS: dict[str, Rulebook] = {
    DUNGEONWORLD_LIKE_ID: DUNGEONWORLD_LIKE,
    OPENQUEST_ID: OPENQUEST,
    CAIRN_ID: CAIRN,
}

def validate_registered_rulebooks() -> None:
    """... 위반이 있으면 이 모듈이 임포트되는 순간 예외로 죽는다. ..."""
    for rulebook_id, rulebook in RULEBOOKS.items():
        ...
        if not rulebook.creation_steps:
            raise InvalidCreationStep(
                f"룰북 {rulebook_id!r}이 creation_steps를 선언하지 않았다"
            )
```

D-18이 시나리오에도 같은 두 관례를 그대로 쓸 수 있다: **① 필드마다 "빈 값=개념 없음" vs
"빈 값=아직 선언 안 함"을 도크스트링으로 구분해 적는다.** ② `validate_registered_scenarios()`
를 시나리오 패키지 `__init__.py`(또는 `rulebooks/__init__.py`와 나란한 새 `scenarios/`
패키지)의 import 시점에 걸어, D-07의 다섯 요소·D-16의 open/closed 두 축이 채워졌는지를
**모듈 로드 시점**에 강제한다. D-07의 ⓐ(구조 검사)를 선택하면, "실마리 최소 하나"는 예를 들어
`hooks: tuple[str, ...]`을 필수 비-빈 튜플로 선언하고 `validate_registered_scenarios`가
`if not scenario.hooks: raise InvalidScenario(...)`로 검사하는 식이 된다 — `Rulebook`의
`creation_steps` 검사와 정확히 같은 모양이다.

### Entity — D-17 명부가 재사용할 그릇

```python
# 출처: src/gptrpg/rules_core/entities.py:166-193 (D-17이 검토할 그릇)
@dataclass(frozen=True)
class Entity:
    """적/NPC 하나 — 상태값 개수에 코드가 상한을 두지 않는다 (D-21)."""
    entity_id: str
    display_name: str
    rulebook_id: str
    stats: tuple[StatEntry, ...] = ()

    def __post_init__(self) -> None:
        if not self.entity_id.strip():
            raise InvalidEntity("entity_id가 비었다", entity_id=self.entity_id)
        ...
```

`Entity`는 이미 `entity_id`/`display_name`/`rulebook_id`/`stats`뿐이다 — "출생"(시나리오가
적었나/이번 세션에서 즉흥으로 생겼나) 칸이 없다. D-17이 "명부는 하나, 출생만 표시"를
요구하므로, 두 가지 길이 있다: **① `Entity`를 그대로 쓰고 출생은 명부(별도 dict/사건)의
메타데이터로만 붙인다**(Entity 자체는 안 바뀜, 룰북 축 검증 등 기존 경로 무영향) **②
`Entity`에 `origin: Literal["scenario", "emerged"]` 필드를 추가한다**(모든 기존
`Entity(...)` 호출부·`ENTITY_FIELD_NAMES` 고정 시험이 깨진다 — `THREAT_CAST`의 네 인물
생성 코드까지 포함). ①이 "칸을 늘리지 않는다"는 이 저장소 관례(CHAR-04 "그릇 절반은 칸을
늘리지 않는다")와 정합하고 파급이 훨씬 작다 — **계획은 ①을 기본으로 검토할 것.**

### D-13① — 대상 칸을 분류기에 추가하는 정확한 선례

```python
# 출처: src/gptrpg/agents/action_classifier.py:95-99 (Proposal의 기존 확장 칸)
item_use: ItemUseClaim = ItemUseClaim(item=None, kind="none")
"""이 행동이 소지품 중 무엇을 쓰는지(RULE-16, 12-06 Task 3) — 새 AI
역할을 만들지 않고 이 분류기 출력에 칸 하나를 더한 것이다 ..."""
```

```python
# 출처: src/gptrpg/agents/action_classifier.py:203-229 (닫힌 목록 대조 + 예외 흡수)
def _parse_item_use(raw_text: str, allowed_items: frozenset[str]) -> ItemUseClaim:
    ...
    if value in allowed_items:
        return ItemUseClaim(item=value, kind="held")
    raise UnknownItemFromAI(value)
```

대상도 같은 모양(예: `TargetClaim(target: str | None, kind: Literal["known", "unknown", "none"])`)
으로 `Proposal`에 한 칸 더하고, `classify()` 안에서 `UnknownItemFromAI`와 같은 방식으로
목록 밖 이름을 흡수하면 D-13①이 새 AI 역할 없이 닫힌다. `allowed_items`에 해당하는 것이
D-13①에서는 "3층 중 1층+2층"(시나리오 선언 + 확정 목록)이다.

### D-13② — 이미 있지만 버려지는 판단을 받는 자리

```python
# 출처: src/gptrpg/agents/scene_entity_judge.py:78-116
def judge_new_entity(...) -> EntityJudgment:
    """... 이번 턴 장면에 새로 등장한 대상을 얻는다. ...
    이미 장면에 있는 대상(`ctx.scene_entities`의 `display_name`)과 이름이
    겹치는 원소는 결과에서 뺀다 ... `NEW_ENTITY_LIMIT`개로 자른다 ..."""
    ...
    existing_names = frozenset(entity.display_name for entity in ctx.scene_entities)
    new_entities = tuple(
        entity for entity in parsed_entities if entity.name not in existing_names
    )[:NEW_ENTITY_LIMIT]
    return EntityJudgment(entities=new_entities, ai=result)
```

이 함수는 **이미 완성돼 있고 이미 매 턴 불린다** — `web/routes_actions.py:1572-1573`,
`1625-1634`가 `entity_judge_choice`/`RecordAiCall(agent_role="scene_entity_judge", ...)`로
호출·계측까지 하고 있다. 지금 코드에서 **비어 있는 것은 오직 하나** — 이 결과
(`judgments.entity.entities`)를 사건으로 적립하는 코드가 없다(모듈 도크스트링 스스로 "장면
대상·캐릭터 상태 관리는 Phase 11·12 소관"이라 적어 뒀는데 둘 다 안 받았다). 계획은 **새 AI
호출을 만들 필요가 없다** — `judgments.entity.entities`를 사건(신규 종류 또는 기존 종류
확장, Claude's Discretion)으로 제출하는 코드만 `proceed()`/`confirm()` 양쪽에 추가하면 된다.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 시나리오 선언 검증 | 커스텀 JSON 스키마 검증기 | `Rulebook`/`validate_registered_rulebooks`와 같은 frozen dataclass + import-시점 함수 | 이미 이 저장소의 검증 관례이고, 12.1-02가 같은 패턴을 검증까지 마쳤다 |
| 대상 닫힌 목록 위반 처리 | 새 예외 계층 | `UnknownMove`/`UnknownItemFromAI`와 같은 모양의 `UnknownTarget` | SAFE-07이 이미 이 패턴을 "계약 위반은 조용히 통과 대신 흡수" 규율로 굳혀 뒀다 |
| AI 호출 중복 방지 | 프런트엔드 방장-탭 판별 | 큐 안(`SessionActor` 단일 소비자) 재검사 또는 세션당 뮤텍스 | 사장님이 2026-08-23에 프런트 완화책을 이미 거부했다(D-03) — 백엔드 해법만 유효 |
| 명부 별도 저장 형식 | 새 ORM 모델/테이블 | 사건에서 접어 만드는 상태(`GameState`의 새 필드, 기존 `party_roster`/`created_characters`와 같은 패턴) | "상태는 사건에서 접어 만든다"가 M0의 유일한 되돌릴 수 없는 결정이다 |

**Key insight:** 이 단계가 새로 만들어야 하는 것은 실제로 매우 적다 — `scene_entity_judge`·
`action_classifier`·`Rulebook`·`narration_guard`·`proceed()` 다섯이 전부 필요한 조각을
이미 갖고 있고, 빠진 것은 **연결**(judge 결과를 사건으로 적는 코드, 분류기 출력에 대상 칸,
시나리오를 선언 형식으로 옮기는 것, 오프닝 전용 지시문 갈래)뿐이다.

## Common Pitfalls

### Pitfall 1: GM 호출 중복 방지 패턴이 이미 있지만 실제로는 안 막는다

**무슨 일이 벌어지는가:** `announce_creation()`(D-02/D-12의 기존 구현)을 그대로 오프닝에
복붙하면 D-03이 막으려는 문제가 그대로 재현된다.

```python
# 출처: src/gptrpg/web/routes_creation.py:806-826
key = _gm_dedupe_key("announce", actor.state)
already_said = actor.state.creation_gm_said.get(key)
if already_said is not None:
    return AnnounceCreationResponse(message=already_said.say, seq=already_said.seq)
# ↑ 여기까지가 큐 밖 사전 검사. 겹친 요청 둘 다 여기를 통과한다.

message = await asyncio.to_thread(announce_requirements, rulebook, provider, model)
# ↑ AI 호출이 여기서 일어난다 — 이미 늦었다. 겹친 두 요청이 둘 다 AI를 부른다.

try:
    seq = await actor.submit(
        RecordGmSpoke(kind="announce", say=message, target_character_id=None, dedupe_key=key)
    )
except AlreadyGmSpoken as exc:
    # ↑ 여기서 두 번째 요청이 잡히지만, AI는 이미 두 번 불린 뒤다.
    return AnnounceCreationResponse(message=exc.prior.say, seq=exc.prior.seq)
```

**왜 일어나는가:** 큐 안 재검사(`AlreadyGmSpoken`)는 **사건**이 두 번 쌓이는 것만 막는다 —
AI 제공자 호출(비용·지연)은 큐 밖에서 이미 일어난 뒤다.

**어떻게 피하는가:** `.planning/todos/pending/2026-08-23-gm-call-fires-twice-across-tabs.md`가
이미 방향을 적어 뒀다 — "큐 밖 사전 검사를 큐 안 검사로 대체하거나(예: `SessionActor`에
`RequestGmSlot`류 명령을 먼저 제출해 슬롯을 얻은 뒤에만 AI를 부른다), 세션당 뮤텍스로
좁힌다." **네 기존 GM 호출 자리(announce/nominate/follow_up/wrap_up)와 오프닝 한 자리가
전부 같은 모양이므로, 한 자리를 고치면 다섯 다 닫힌다** — 계획은 개별 라우트 가드를
반복하지 말 것(D-03이 명시적으로 금지).

**경고 신호:** 네 명이 동시에 세션에 들어와 오프닝이 뜰 때 서버 로그에 `RecordAiCall(agent_role="master_gm", ...)`가 세션 하나당 한 번을 넘게 찍히면 이 문제다.

### Pitfall 2: situation_judge를 오프닝에 그대로 재사용하면 지시문이 틀린 말을 한다

**무슨 일이 벌어지는가:** `build_situation_prompt`의 영구 고정 지시문(`agents/prompt_assembly.py:616-627`)은 "판정 결과와 지금까지의 장면·위협 시계 상태를 보고 ... **이미 정해진 값을 그대로 반영한다**"고 말하고, JSON 계약 예시가 "이번 판정으로 확정된 사실"만 담으라고 못박는다. 오프닝에는 판정이 없다 — 이 지시문 그대로 부르면 모델이 "판정 결과가 없다"에 당황하거나, 있지도 않은 판정을 지어내 반영할 위험이 있다.

**왜 일어나는가:** `situation_judge`는 지금까지 "판정 뒤 상황 정리" 역할 하나로만 설계됐다 — D-05가 지적한 "직전 장면이 없다"는 정확히 이 지점이다.

**어떻게 피하는가:** `build_situation_prompt`에 `is_opening: bool`(또는 별도 함수
`build_opening_situation_prompt`)을 추가해 영구 고정 지시문을 오프닝 전용 문장("판정 결과가
아니라 시나리오가 적어 둔 상황을 읽고, 서술이 첫 장면을 열 때 필요한 것만 뽑는다 —
시나리오 원문을 옮겨 적지 말고 좁혀서 전달한다")으로 바꾼다. `judge_situation()` 함수
시그니처(`ctx: TurnContext, check_summary: str`)는 그대로 재사용 가능 — `check_summary`
자리에 `NO_CHECK_SUMMARY`류 플랫폼 고정 문장의 오프닝판(예: `OPENING_CHECK_SUMMARY = "이번은
장면을 여는 오프닝이다."`)을 넣으면 된다. `NarrationFacts` 자체는 무변경.

**경고 신호:** 오프닝 실측에서 모델이 "판정 결과가 없어서..." 같은 메타 발언을 섞으면 이 지시문이 원인이다.

### Pitfall 3: `EVENT_SCHEMA_VERSION`을 안 올리고 새 사건 종류를 추가

**무슨 일이 벌어지는가:** 확정 목록·명부를 새 사건 종류(`scene_entity_confirmed`류)로 만들기로
하면 `event_log/schema.py`의 `EVENT_SCHEMA_VERSION`(현재 11, `event_log/schema.py:19`)을
올리고 `rules_core/reducer.py`의 `apply_event` 분기를 **같은 커밋**에 추가해야 한다.

**왜 일어나는가:** `reducer.py`의 `UnknownEventType`(`rules_core/reducer.py:250-262`)이
"모르는 사건 종류가 오면 조용히 넘어가지 않는다"를 강제하므로, 판을 안 올리고 사건만 내보내면
재생(`apply_event`)이 즉시 예외를 던진다 — 이 사고가 이미 세 번 주석으로 기록돼 있다
(`reducer.py:297` 등, `EVENT_SCHEMA_VERSION` 4→5 판올림 언급).

**어떻게 피하는가:** Claude's Discretion 절이 이미 이 위험을 적어 뒀다 — "새로 만들면
`EVENT_SCHEMA_VERSION`을 올리고 `reducer.py` 분기를 같은 커밋에 낸다." 대안(기존
`narration_appended` 재사용, 또는 확정 목록을 `GameState`의 새 필드로 접되 새 event_type 없이
기존 `resource_changed`류처럼 payload만 확장)도 검토할 것 — 새 종류가 꼭 필요한지부터
판단한다.

### Pitfall 4: `inspect_sentence`의 "네 갈래" 구조는 문장 단위다 — 다섯 요소 검사와 안 맞을 수 있다

**무슨 일이 벌어지는가:** D-08은 "서사가 이미 거치는 네 갈래 검사에 한 갈래를 더한다"고
적었지만, `narration_guard.inspect_sentence`(`agents/narration_guard.py:218-263`)의 네
갈래(생각 블록/원문 겹침/캐릭터 이탈/깨진 글자)는 전부 **한 문장**을 판정하는 함수다 —
`sentence: str, next_sentence: str | None`을 받는다. D-07의 다섯 요소(내가 누구인지 / 보이고
들리는 것 / 왜 중요한지 / 실마리 / 열린 초대)는 **문서(오프닝 전체) 단위 완결성**이라 문장
하나로는 판단할 수 없다 — "실마리가 있는가"는 오프닝 전체를 다 봐야 안다.

**왜 일어나는가:** narration_guard는 안전 검사(유출·이탈) 도구로 설계됐지, 콘텐츠 완결성
검사 도구가 아니다.

**어떻게 피하는가:** 계획은 두 가지 중 하나를 명시적으로 골라야 한다 — **① 오프닝은
문장 스트림이 끝난 뒤 전체 텍스트를 모아 별도 함수(`inspect_sentence`가 아닌 새 함수, 예:
`inspect_opening_completeness`)로 검사한다.** 이러면 "네 갈래에 한 갈래를 더한다"는
CONTEXT.md 표현과 문자 그대로는 안 맞지만(별도 함수), **자리**(서사 청크가 나가기 전, D-08의
의도)는 지킨다. **② D-07ⓐ(등록 시점 구조 검사)를 택하면 이 문제 자체가 사라진다** — 낭독문형은
등록 시점에 다섯 칸이 채워졌는지만 보면 되고(AI 생성 자체가 없다, D-06), 메모형은
`situation_judge`가 좁혀 넘긴 사실에 시나리오가 이미 등록 시점에 검증된 다섯 요소가 포함되어
있다는 것을 **신뢰**하면 된다(생성 시점 재검사 불필요). D-07 도크스트링이 이미 "ⓐ가 D-18의
「룰북과 같은 모양」과 정합한다"고 적어 D-07ⓐ 쪽으로 기울어 있다 — 계획은 D-07ⓐ를 택하면
D-08의 "네 갈래에 한 갈래를 더한다"는 표현을 "등록 시점 검사로 대체한다"로 재해석해야 한다는
점을 명시적으로 적을 것.

### Pitfall 5: CLI가 캐릭터 선택 개념이 없다는 것을 다시 확인하지 않고 웹만 고친다

**무슨 일이 벌어지는가:** 오프닝·명부는 CLI에 조용히 빠질 수 있다.

**왜 일어나는가:** `cli/turn_flow.py:257-268`의 기존 주석이 근거를 이미 적어 뒀다:

```python
# 출처: src/gptrpg/cli/turn_flow.py:257-268
# **캐릭터 만들기(Phase 12.1)를 명령줄에 넣지 않는다 — 이 저장소의 「웹과
# CLI를 같은 커밋에서 닫는다」 관례의 명시적 예외다.** 만들기는 서명 쿠키
# 신원(누가 말하고 있나)과 차례 지목(누가 지금 차례인가) 둘을 전제하는데,
# 명령줄에는 그 두 개념이 아예 없다 ...
```

**어떻게 피하는가:** 오프닝은 이 선례를 그대로 상속할 수 있다(세션 시작 = 캐릭터 선택
개념과 묶여 있으므로) — 명부는 CLI에도 있다(CONTEXT.md Claude's Discretion 절이 이미
"대상 검사는 판정 턴 안이라 CLI에도 있다"고 구분해 뒀다). 계획서에 **왜** 오프닝이 예외이고
대상 검사는 아닌지 근거를 반드시 적을 것(CONTEXT.md가 이미 이 지점을 "조용히 한쪽만 고치는
것이 이 저장소의 알려진 실패 모양"이라 경고했다).

## Code Examples

### 파티 명단 잠금 사건 — D-01 트리거의 정확한 모양

```python
# 출처: src/gptrpg/rules_core/reducer.py:558-561
if event_type == "party_roster_locked":
    # 명단 잠금(판 9, D-08) — party_roster가 None에서 튜플로 바뀐다.
    # 이 이후로는 이 칸이 다시 None으로 돌아가지 않는다(푸는 사건이 없다).
    return replace(state, last_seq=seq, party_roster=tuple(payload["character_ids"]))
```

`LockPartyRoster` 커맨드는 `session_actor/actor.py:172`에 선언되어 있고, 실제 발동은
`actor.py:735` 부근에서 `LockPartyRoster(character_ids=tuple(self.state.created_characters))`
형태로 이미 조립되고 있다(12.1의 전원 동의 완료 시점). 오프닝은 이 사건을 프런트가
폴링으로 감지하는 자리(D-02)를 새로 추가하면 된다 — `Notices.tsx:54-58`의 `CreationScreen`이
이미 이 정확한 패턴("폴링에서 `party_roster_locked` 사건을 보면 이 안내로 갈아탄다")을
쓰고 있다.

### 프런트 게이트 전환 — 오프닝 호출을 걸 정확한 자리

```typescript
// 출처: frontend/src/App.tsx:76-86
case "creating":
  return (
    <CreationScreen
      sessionId={sessionId}
      onEntered={(characterId) => setGate({ kind: "ready", characterId })}
    />
  );
case "ready":
  return (
    <SessionScreen key={gate.characterId} sessionId={sessionId} characterId={gate.characterId} />
  );
```

`SessionScreen`(`frontend/src/screens/SessionScreen.tsx:52-`)은 지금 마운트 시 캐릭터
목록·시트만 불러온다(`fetchCharacters`/`fetchCharacterSheet`, 63-77행) — 오프닝 호출은 이
`useEffect` 옆에 추가되거나, `narration_appended` 사건이 0건일 때만 발동하는 별도
`useEffect`로 추가되어야 한다. `CreationScreen`이 GM 호출 네 곳에 쓰는 폴링 기반
"이미 말했으면 다시 안 부른다" 패턴(D-02)을 그대로 상속할 수 있다.

## State of the Art

이 저장소 안에서의 "state of the art"만 해당한다(외부 생태계 변화 없음, 순수 내부 리팩터링).

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| 서사 함수가 `check_summary`(판정 결과)를 필수로 받음 | Phase 11-06이 `proceed()`로 판정 없는 서술 경로를 이미 열었다(`NO_CHECK_SUMMARY`) | 11-06 | 오프닝은 "두 번째"가 아니라 "세 번째" 진입점이다(CONTEXT.md ①) — `declare_seq`만 없는 변형 |
| `scene_entity_judge` 결과가 서술용 사실로만 쓰이고 버려짐 | 이 단계가 사건으로 적립하는 첫 소비자가 된다(D-13②) | 09-03 이후 계속 미해결 | 새 AI 호출 불필요, 연결 코드만 필요 |
| `TurnContext.scene_entities`가 `THREAT_CAST` 하드코딩 통째로 | 이 단계가 3층(시나리오 선언 + 확정 목록)으로 대체한다 | 04-01(`WELL_SCENARIO_SETTING` 예고) 이후 미실행 | `turn/context.py:130` 한 자리만 바뀌면 되지만, 시나리오가 하나뿐이라 "두 번째 시나리오" 분기 검증이 이 단계에서 처음 실측된다(D-21의 낭독문형 시나리오 신설) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `situation_judge`의 오프닝 지시문 분기를 별도 함수/플래그로 추가하는 것이 `NarrationFacts` 타입을 안 건드리는 최소 변경이라는 판단 — 코드로 실제 프롬프트 A/B 테스트는 이 세션에서 안 함 | Pitfall 2, Architecture Patterns | 실제 생성 결과가 기대한 만큼 시나리오 원문을 잘 좁히지 못하면 계획 단계에서 프롬프트를 더 다듬어야 함(구현 비용, 설계 오류는 아님) |
| A2 | D-08의 다섯 요소 검사를 `narration_guard.inspect_sentence`가 아닌 별도 문서-단위 함수로 만드는 것을 권장 — 이것이 CONTEXT.md의 "네 갈래에 한 갈래를 더한다" 표현과 문자적으로 다를 수 있음 | Pitfall 4 | 계획이 이 해석 차이를 사장님께 확인 없이 넘기면, "narration_guard에 다섯 번째 갈래를 추가"라는 문언과 실제 구현(별도 함수)이 어긋난 채 진행될 위험 — discuss-phase에서 이미 확정된 결정이 아니라면 계획 단계 checkpoint로 확인 필요 |
| A3 | D-17 명부는 `Entity`를 그대로 쓰고 출생 표시는 별도 메타데이터로 붙이는 쪽(①)이 `Entity` 필드 확장(②)보다 파급이 작다는 비교 — 실제 명부 데이터 모델 설계는 계획 몫 | Architecture Patterns "Entity — D-17" | ②를 택해야 하는 요구사항이 나중에 나오면(예: 명부 화면이 "출생"으로 정렬·필터해야 함) ①로는 부족할 수 있음 |

## Open Questions

1. **`build_situation_prompt`의 오프닝 지시문을 어떻게 분기하는가 — 새 매개변수(`is_opening: bool`)인가, 완전히 별도 함수(`build_opening_situation_prompt`)인가?**
   - 무엇을 아는가: 두 함수가 값 객체(`TurnContext`, `check_summary: str`)를 그대로 공유할 수 있다는 것은 확인됨.
   - 무엇이 불확실한가: 이 저장소의 관례상 `build_classifier_prompt`/`build_situation_prompt`/`build_scene_entity_prompt`가 각각 독립 함수다(공유 플래그로 분기하는 선례가 없음) — 별도 함수 쪽이 관례에 더 맞을 가능성.
   - 권장: 계획 단계에서 별도 함수(`build_opening_situation_prompt`)를 기본으로 검토 — 기존 함수 관례와 정합.

2. **D-15의 "즉흥 금지" 되돌림 문장은 어느 채널로 서술에 전달되는가 — `NarrationFacts.facts`(문자열 사실)인가, 새 칸인가?**
   - 무엇을 아는가: `NarrationFacts.facts`는 이미 `SITUATION_FACTS_LIMIT`(5개) 상한이 있는 문자열 튜플이고(`agents/context.py:213-260`), situation_judge가 이미 "이번 판정으로 확정된 사실"을 이 칸에 담는다.
   - 무엇이 불확실한가: "이 대상은 여기 없다"는 판정 결과가 아니라 분류 시점(D-13①)의 사실이라 situation_judge가 자연스럽게 안다고 보기 어렵다 — `facts`에 억지로 우겨 넣으면 situation_judge가 그 사실을 다시 스스로 "판단"해야 하는 이상한 경로가 생긴다.
   - 권장: `NarrationFacts`에 칸을 늘리는 대신(ARCH-02 위반 소지 없음 — 이 칸은 시나리오 원문이 아니라 이번 턴의 사실이므로), `NO_CHECK_SUMMARY`처럼 **플랫폼이 조립하는 고정 문장** 하나(예: "지목한 대상은 이 장면에 없다")를 `situation_judge` 호출 전에 직접 만들어 `facts`에 미리 채워 넣는 방식(코드가 만들고 AI가 다시 판단하지 않음)을 검토. CONTEXT.md D-15가 이미 "대가가 붙는 사실로 넘길지 별도 칸으로 넘길지가 설계 지점"이라 적어 뒀다 — 계획이 결정.

3. **오프닝 중복 호출 방지(D-03/Pitfall 1)를 어떤 구체적 메커니즘으로 닫는가 — 큐 안 사전 검사 명령을 새로 만드는가, `SessionActor`에 세션당 asyncio.Lock을 추가하는가?**
   - 무엇을 아는가: 두 방향 다 할 일 문서(`.planning/todos/pending/2026-08-23-gm-call-fires-twice-across-tabs.md`)에 방향으로만 적혀 있고 구체 구현은 없다.
   - 무엇이 불확실한가: 뮤텍스 접근은 `SessionActor`가 이미 단일 소비자 큐(`asyncio.Queue`)라는 것과 개념적으로 겹친다 — 락을 어디(라우트 핸들러 vs 액터 내부)에 거는지가 "AI 호출 자체를 큐 안으로 옮긴다"는 더 근본적인 재설계와 어떻게 다른지 계획이 판단해야 한다.
   - 권장: 계획은 이 할 일을 별도 Task로 명시적으로 떼어(D-03이 이미 "이 단계에서 같이 닫는다"고 확정) 네 기존 GM 호출 자리 + 오프닝 한 자리를 한 커밋에서 같이 고치는 순서를 짤 것 — 되돌릴 수 없는 구조(Reversibility: costly, D-03 명시)이므로 설계를 먼저 굳히고 다섯 자리에 동시 적용.

## Environment Availability

해당 없음 — 이 단계는 코드/설정 변경만이고 외부 서비스·툴 의존성이 없다 (기존 AI 제공자
설정은 이미 이전 단계에서 검증됨).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (`pyproject.toml:51-53`, `asyncio_mode = "auto"`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`, `testpaths = ["tests"]` |
| Quick run command | `.venv/bin/python -m pytest -q --tb=short -k <keyword>` |
| Full suite command | `.venv/bin/python -m pytest -q --tb=short` (config.json의 `workflow.test_command`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCENE-01 | `declare_seq` 없이 오프닝이 발동하고 `narration_appended`가 기록됨 | integration | `pytest tests/test_web_actions.py -k opening -x` | ❌ Wave 0 — 새 테스트 필요(기존 `test_web_actions.py`가 `proceed()` 계열 패턴 보유) |
| SCENE-02 | 다섯 요소가 오프닝에 담김(등록 시점 검사 ⓐ 채택 시) | unit | `pytest tests/test_rulebook.py -k scenario -x` 또는 신설 `test_scenario.py` | ❌ Wave 0 — `test_rulebook.py`가 구조 모델(D-18) |
| SCENE-03 | 3층 조립 — `turn/context.py`의 `scene_entities`가 시나리오+확정 목록을 합침 | unit | `pytest tests/test_turn_context.py -x` (파일명 추정 — 존재 확인 필요) | 확인 필요 — `turn/` 전용 테스트 파일 존재 여부 재확인 |
| SCENE-04 | open/closed 결정론적 처리 — 같은 입력에 같은 결과 | unit | `pytest tests/test_action_classifier.py -k target -x` | ❌ Wave 0 — 기존 `test_action_classifier.py`(item_use 패턴 보유)에 대상 케이스 추가 |
| SCENE-05 | 명부 재등장 인식 — 같은 이름이 같은 `entity_id`로 매칭 | integration | `pytest tests/test_scene_entity_judge.py -k registry -x` | ❌ Wave 0 — 기존 `test_scene_entity_judge.py`에 추가 |

`turn/context.py`용 기존 테스트 파일명은 이 세션에서 확인하지 못했다 — 계획 Wave 0에서
`ls tests/ | grep turn_context` 등으로 먼저 확인할 것.

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest -q --tb=short -k <관련 모듈>`
- **Per wave merge:** `.venv/bin/python -m pytest -q --tb=short`
- **Phase gate:** 전체 스위트 초록 + `validate_registered_rulebooks()`류 신설 `validate_registered_scenarios()`가 모듈 import 시점에 예외 없이 통과(등록 시점 검사가 D-07ⓐ로 결정될 경우)

### Wave 0 Gaps
- [ ] `tests/test_scenario.py`(또는 `test_rulebook.py` 확장) — `ScenarioDecl`/`validate_registered_scenarios` 구조 검사(SCENE-02·D-07·D-18)
- [ ] 오프닝 엔드투엔드 테스트(`test_web_actions.py` 확장) — `party_roster_locked` 이후 오프닝 호출, 중복 호출 방지(D-03) 재현 시험
- [ ] `test_action_classifier.py` 확장 — 대상 칸(D-13①) 파싱 + `UnknownTarget`류 흡수
- [ ] `test_scene_entity_judge.py` 확장 또는 신규 — D-13②(사건 적립), D-19(기존 이름 재사용) 재현
- [ ] 프런트 테스트 — `SessionScreen`의 오프닝 호출 트리거(폴링 기반 "이미 있으면 다시 안 부른다") 재현. 기존 `CreationScreen` 테스트 패턴(`test_creation_*.py`류가 백엔드 쪽만 커버 — 프런트 자체 시험 프레임워크 존재 여부는 Wave 0에서 `frontend/` 하위 확인 필요)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 이 단계는 새 인증 개념을 안 만든다 — 기존 서명 쿠키(`cookie_auth.py`) 재사용 |
| V3 Session Management | no | 세션 식별자 처리 무변경 |
| V4 Access Control | yes | `proceed()`가 이미 하는 신원 대조(`identity.character_id != body.character_id`)와 `VerifyProceedEligibility` 이중 검증을 오프닝 라우트도 그대로 상속해야 함 |
| V5 Input Validation | yes | 대상 지목의 닫힌 목록 대조(D-13①/D-19)는 기존 `UnknownMove`/`UnknownItemFromAI` 패턴(예외 흡수, 부분 신뢰 금지)을 그대로 따른다 — AI가 낸 자유 문자열을 신뢰하지 않고 항상 코드가 재대조한다(`action_classifier.py:203-229`의 `value in allowed_items` 완전 일치 규율) |
| V6 Cryptography | no | 해당 없음 |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 프롬프트 인젝션(플레이어가 대상 이름에 지시문을 섞어 냄) | Tampering | 기존 `fence_player_text`(SAFE-05) 울타리가 이미 `action_declared.raw_text` 전체를 감싼다 — 대상 칸 추가가 이 경로를 우회하지 않는지 확인(대상은 raw_text에서 파생되지 않고 AI가 별도로 고른 후보이므로 별도 울타리 불필요, 다만 목록 대조 시 서버 쪽 값과 항상 재대조하는 기존 규율 유지) |
| 시나리오 원문 유출(오프닝 메모형 경로에서 situation_judge가 다 옮겨 적음) | Information Disclosure | ARCH-02가 `NarrationFacts`에 원문 칸 자체를 안 둠으로써 타입 차원에서 막는다 — 오프닝 지시문 신설 시에도 이 벽을 유지(situation_judge만 원문을 읽고, master_gm은 여전히 좁혀진 것만 받음) |
| 대상 닫힌 목록 우회(AI가 목록 밖 대상을 "있는 척" 서술에 섞어 냄) | Spoofing(허구 내 엔티티) | D-13①(굴리기 전 대상 분류) + D-13②(굴린 뒤 판단 적립) 이중 확인이 SAFE-07과 같은 이중 방어 구조 — 어느 한쪽만 만들면 세션1 문제가 재현된다(CONTEXT.md D-13 "왜 둘 다인가") |

## Sources

### Primary (HIGH confidence — 이 세션에서 직접 읽고 확인)
- `src/gptrpg/agents/context.py` — `TurnContext`/`NarrationFacts`/`EntityJudgeContext` 등 값 객체 전체
- `src/gptrpg/agents/master_gm.py` — `narrate()` 전체
- `src/gptrpg/agents/scene_entity_judge.py` — `judge_new_entity()` 전체
- `src/gptrpg/agents/action_classifier.py` — `Proposal`/`classify()`/`_parse_item_use()` 전체
- `src/gptrpg/agents/situation_judge.py` — `judge_situation()` 전체
- `src/gptrpg/agents/prompt_assembly.py:587-627` — `build_situation_prompt()` 지시문 원문
- `src/gptrpg/agents/narration_guard.py:90-360` — `inspect_sentence()` 여섯 갈래 전체
- `src/gptrpg/web/routes_actions.py:1470-1730` — `proceed()` 전체 흐름
- `src/gptrpg/web/routes_creation.py:740-829` — `announce_creation()`, GM 호출 중복 버그의 실제 코드
- `src/gptrpg/turn/context.py` — `build_turn_context()` 전체
- `src/gptrpg/rulebooks/threat_clocks.py` — `M0_THREAT_CLOCK`/`THREAT_CAST` 전체
- `src/gptrpg/imagery/scene_prompt.py:45-51` — `WELL_SCENARIO_SETTING` 원문
- `src/gptrpg/rules_core/rulebook.py:560-730` — `Rulebook`, `validate_party_size`, `narrow_party_size_range`
- `src/gptrpg/rulebooks/__init__.py` — `RULEBOOKS`, `validate_registered_rulebooks()`
- `src/gptrpg/rules_core/entities.py:140-199` — `Entity`, `StatEntry` 검증
- `src/gptrpg/rules_core/reducer.py:230-300, 540-580` — `apply_event`, `party_roster_locked` 처리
- `src/gptrpg/event_log/schema.py:19` — `EVENT_SCHEMA_VERSION = 11`
- `src/gptrpg/session_actor/actor.py:172, 201-215, 1787-1966` — `LockPartyRoster`, `RecordGmSpoke`, `_prepare_gm_spoke`
- `src/gptrpg/cli/turn_flow.py:240-270` — CLI 캐릭터 만들기 제외 근거
- `frontend/src/App.tsx`, `frontend/src/screens/Notices.tsx:53-72`, `frontend/src/screens/SessionScreen.tsx:1-90` — 화면 전환·폴링 패턴
- `.planning/todos/pending/2026-08-23-gm-call-fires-twice-across-tabs.md` — D-03의 근거 문서
- `.planning/research/SCENARIO-SURVEY.md:28, 73, 100-147` — SCENE-04/D-67의 원 조사
- `.planning/PROJECT.md:348` — D-67 원문
- `.planning/REQUIREMENTS.md` — SCENE-01~05 원문
- `.planning/phases/13-scene-opening-and-targets/13-CONTEXT.md` — 이 단계의 사용자 결정 22건

### Secondary (MEDIUM confidence)
- 없음 — 이 단계는 외부 문서·웹 검색이 필요 없는 순수 내부 리서치였다(신규 라이브러리 없음, 기존 저장소 구조를 확인하는 작업).

### Tertiary (LOW confidence)
- `turn/context.py` 전용 테스트 파일 존재 여부(Validation Architecture 절 표시) — 이 세션에서 `ls`로 직접 확인하지 못함, 계획 Wave 0에서 확인 필요.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — 신규 의존성 없음
- Architecture: HIGH — 전체 파이프라인(`proceed()`, `judge_situation`, `scene_entity_judge`, `action_classifier`, `Rulebook`)을 이 세션에서 직접 읽고 인용
- Pitfalls: HIGH — 다섯 개 함정 모두 실제 코드(파일:행)로 재현 근거를 확인함, 특히 Pitfall 1(GM 호출 중복)은 실제 버그 재현 코드까지 인용

**Research date:** 2026-08-24
**Valid until:** 이 단계 계획·실행이 끝날 때까지 유효 — 이 저장소는 빠르게 변하므로(같은 날
STATE.md에 12.3만 20개 계획) 30일 상한은 사실상 무의미하고, **다음 코드 변경 전까지**로
본다.

# Project Research Summary

**Project:** GPTRPG — v1.1 "돌아가는 프로토타입" 하드닝 마일스톤
**Domain:** 이벤트 소싱 기반 Python(FastAPI) + React AI-GM TRPG 플랫폼
**Researched:** 2026-08-05
**Confidence:** MEDIUM-HIGH (아키텍처·핏폴은 실제 코드 1차 근거로 HIGH, 스택·기능은 외부 사례 교차확인으로 MEDIUM)

## Executive Summary

이 마일스톤은 새 제품을 만드는 게 아니라, 2026-08-04 세션1 실전 사고에서 드러난 여섯 개 구멍(신원 미검증, AI 출력 미검증, 탈옥, 능력치 미반영, confirm 비멱등, 기억 유지 실패)을 기존 이벤트 소싱 아키텍처와 5-어댑터 Provider 프로토콜을 건드리지 않고 메우는 작업이다. 네 명의 리서처가 독립적으로 도달한 결론은 놀랍도록 일치한다 — 새로 설치할 라이브러리는 사실상 `itsdangerous` 하나뿐이고, 나머지는 전부 `prompt_assembly.py`·`routes_actions.py`·`session_actor/actor.py`·`rules_core/reducer.py` 안의 설계·배관 문제다. LangChain류 프레임워크, 탐지형 프롬프트 인젝션 방어 라이브러리(`llm-guard`/`rebuff`), `tiktoken` 기반 정밀 토큰 카운팅은 전부 명시적으로 기각됐다 — 각각 D-17(에이전트 4개 고정)을 무효화하거나, 이 프로젝트의 최근 10턴 상시 주입 구조에서 정확도가 떨어지거나, 다섯 제공자 중 넷에는 근사치일 뿐이라는 이유다.

권장 접근은 다음 순서를 따른다: 신원 검증(TRUST)을 가장 먼저 끝내고, confirm 멱등성을 능력치 쓰기 경로보다 먼저 고치고, D-20(캐릭터 시트 쓰기 경로)과 D-31(턴당 컨텍스트 슬롯 개수)을 코드보다 먼저 재논의로 확정한다. 이 두 재논의는 네 명의 리서처가 각자 독립적으로 "코드 이전에 반드시 풀어야 한다"고 지적한 유일한 두 항목이다. 그 다음에야 AI 출력 검증·탈옥 방어, 능력치 반영, 관계 장부·문맥 압축기, 위협 시계 진행 규칙 확장을 순서대로 쌓는다.

가장 큰 위험은 두 가지이며 둘 다 "완전히 해결"이 불가능하다는 점을 정직하게 인정해야 한다. 첫째, 관계 장부(D-11)와 캐릭터 자원 변화(D-20)를 세션 고정 프롬프트 층에 넣는 순간, "장면이 바뀔 때만 갱신된다"던 캐싱 전제가 "상태가 바뀔 때마다 갱신된다"로 사실상 낮아져 프롬프트 캐싱의 3.7배 원가 이점이 부분적으로 침식된다 — 이건 완화할 수 있을 뿐 없앨 수 없다. 둘째, 프롬프트 인젝션/탈옥 방어는 구분자+무효화 선언(Spotlighting 기법)으로 성공률을 크게 낮출 수는 있어도 0%로 만들 수는 없다는 것이 업계 컨센서스다 — 이 프로젝트가 이미 D-12("완벽 방어가 아니라 투명성")로 정확한 목표를 잡아 둔 것이 그래서 중요하다. "탈옥 방지됨"이라고 보고하는 순간 이미 잘못된 신호다.

## Key Findings

### Recommended Stack

신규 패키지는 `itsdangerous`(서명 쿠키, C1 신원 검증용) 하나뿐이다. Starlette `SessionMiddleware`는 매 요청 재서명 부작용 사례가 보고돼 있고 이벤트 로그 밖의 두 번째 상태 저장소 개념을 만들기 때문에 채택하지 않는다 — 라우트 함수 안에서 `itsdangerous`를 직접 호출하는 편이 더 정확하다. AI 출력 검증(C2)은 어댑터별 reasoning 필드 처리(Anthropic·Gemini·NIM은 안전, OpenRouter 스트리밍은 신뢰 불가) + `<think>` 정규식 백스톱 이중 방어로 새 패키지 없이 해결한다. 탈옥 방어(C3)는 라이브러리가 없다는 것이 정직한 결론이며, Microsoft Spotlighting 연구(성공률 50%→2%, 프로덕션 검증)를 따라 구분자+무효화 선언을 `prompt_assembly.py` 문자열 조립으로 구현한다. 기억 유지(MEM)는 LangChain/LlamaIndex를 명시적으로 기각하고 D-17이 예정해 둔 `context_summarizer`를 기존 `action_classifier.py` 패턴 그대로 신설한다. 다인원 동시성 테스트는 이미 dev dependency인 `httpx`(`ASGITransport`) + `pytest-asyncio` + `hypothesis`(적대적 퍼징)로 충분하다.

**Core technologies:**
- `itsdangerous 2.2.0`: 신원 서명 쿠키 — starlette가 내부적으로 쓰는 표준 선택, 순수 파이썬 의존성 0개
- `httpx.AsyncClient(transport=ASGITransport(app=app))`: 다인원 동시성 회귀 테스트 — 실제 uvicorn 없이 여러 가짜 플레이어를 동시에 찌른다
- `hypothesis`(기존): 적대적 입력 퍼징 — 탈옥 방어가 특정 문구에만 과적합되지 않았는지 검증
- (신규 없음) 프롬프트 구조 방어(구분자+무효화 선언), `<think>` 정규식 백스톱, `difflib.SequenceMatcher` — 전부 표준 라이브러리 또는 문자열 조립만으로 해결

### Expected Features

층 구분(① 플랫폼 / ② 표현 어휘 / ③ 룰북 규칙)을 지키는 것이 이번 리서치의 반복되는 핵심이다. 특히 "체력"을 플랫폼 코드에 하드코딩하면 D32(적·NPC 숫자는 룰북이 선언)를 캐릭터 쪽에서 위반하는 것과 같으므로, 자원은 항상 제네릭 슬롯(이름·현재·최대는 룰북 선언)으로 표현해야 한다.

**Must have (v1.1 없이는 "돌아가는 프로토타입"이 성립하지 않음):**
- 서버 측 신원 검증(쿠키↔character_id, confirm↔declare 소유자 대조) — TRUST
- AI 서사 출력의 `<think>`/시스템 프롬프트 유사 텍스트 필터링 + 구분자·탈옥 방지 지시문 — SAFE
- 필터링/이탈 발생 시 시스템 배너 안내(침묵 삭제 금지, Character.AI 패턴) — SAFE
- D-20 재논의 → 능력치의 판정 보정치 자동 대입 + 캐릭터 자원 슬롯 변화가 화면에 보임 — RULE
- 파티 전원의 자원 상태가 AI에게 보임(지금은 행동한 사람 한 명만) — RULE
- 관계 장부(인물별 최근 사건 색인) + context_summarizer(오래된 대화 압축) — MEM
- 위협 시계 조건 트리거 + AI 선택(제안-확인 절차) + 시계 수동 진행의 웹 경로 — CLOCK

**Should have (v1.x, 검증 후 추가):**
- 필터링 자동 재생성 1회 시도, 압축 전/후 비교 로그, 자원 임계값 시각 강조, 시계 진행 이유 배너

**Defer (v2+, 명시적으로 범위 밖):**
- 검색 기반 기억 주입(RAG) — "검색 품질이라는 실패 지점을 추가하면 재미있나를 못 잰다"로 REQUIREMENTS.md가 이미 배제
- 가드레일 전용 LLM 이중 검증 — 지연시간·원가 상한과 충돌, 낯선 사람 매칭(M2) 전까지 과함
- 좌표계·전술 그리드 — D9가 M4로 이미 미룸

### Architecture Approach

기존 층 구조(`cli`/`web` → `turn` → `agents` → `session_actor` → `rulebooks` → `rules_core`/`event_log`)와 다섯 불변식(append-only+fold / 세션당 쓰기 주체 하나 / 규칙 코어는 시간을 모름 / LLM은 주사위 수학에 안 닿음 / 프롬프트 조립은 영구→세션→턴 순서)을 그대로 유지한 채 8개 항목을 끼워 넣는다. 신규 사건 종류(`CharacterResourceChanged`, `ContextSummarized`)가 최소 두 개 추가되므로 `EVENT_SCHEMA_VERSION`을 4에서 6까지 순차적으로 올려야 하고, 신규 사건 종류마다 `reducer.py::apply_event`에 분기를 같은 커밋으로 반드시 동반해야 한다 — 빠뜨리면 `UnknownEventType`으로 세션이 영구히 안 열리는 사고가 재발한다(`SceneIllustrated`가 이미 이 경고를 남겨 둠).

**Major components:**
1. `agents/output_guard.py`(NEW) — AI 서사 출력의 사고 블록/프롬프트 유출 검사, `master_gm.narrate()`가 문장을 커밋하기 전에 통과시킴
2. `session_actor/actor.py`의 `_prepare_confirm`(MODIFIED) — 신원 소유권 검증 + 멱등성 판정을 세션당 유일한 직렬화 지점에서 원자적으로 처리
3. `rules_core/reducer.py::GameState`(MODIFIED) — `character_resources`, `confirmed_declare_seqs` 등 파생 칸 추가. 매번 fold로 재구성되므로 마이그레이션 불필요(사건 스키마와 달리 자유롭게 재설계 가능)
4. `agents/context_summarizer.py`(NEW) — `action_classifier.py`/`master_gm.py`와 동일한 순수 텍스트 변환 패턴, `event_log`/`session_actor` import 금지 계약 유지

### Critical Pitfalls

1. **신원 검증을 라우트 계층에만 붙이고 `SessionActor` 내부(단일 쓰기 직렬화 지점)에는 안 둔다** — TOCTOU 우회 경로가 남는다. 쿠키↔character_id 대조와 confirm↔declare 소유자 대조는 서로 다른 두 검사이며 둘 다 필요하다.
2. **AI 출력 필터를 `narrate()` 레벨 텍스트 정규식 하나로 통일 처리한다** — 추론 모델의 사고 블록 유출은 대부분 스트리밍 청크 경계 문제(`<thi`+`nk>`가 서로 다른 청크)라서, 프로바이더 어댑터 경계에서 정규화하지 않으면 일부만 잡힌다. 필터의 에러 메시지에 원문 일부를 포함시키면 필터 자체가 새 유출 경로가 된다.
3. **가변 상태(HP류)를 이벤트 소싱에 붙이면서 "폴드는 이벤트만의 순수 함수"라는 불변식을 깬다** — 파생 상태를 인메모리에만 반영하거나, `reducer.py`가 `seq` 단조 증가를 검증하지 않는 기존 결함(M3)이 HP 도입 시 순서 오류를 생사 수준의 문제로 키운다. session1의 실제 이벤트 로그를 리플레이 회귀 픽스처로 반드시 써야 한다.
4. **멱등성 키를 "같은 declare_seq면 무조건 성공 재반환"이라는 단일 불리언으로 단순화한다** — confirm은 굴림/서사 두 단계이므로 부분 실패 구간을 놓치면 재시도가 "HP를 두 번 깎는" 문제로 악화된다. 멱등성이 없는 채로 자원 쓰기부터 들어가면 실패 모드가 훨씬 나빠지므로, 멱등성을 반드시 자원 쓰기보다 먼저 고쳐야 한다.
5. **관계 장부·문맥 압축기가 프롬프트 캐싱을 조용히 깨뜨리는데 그걸 캐시 히트율 계측 없이 그냥 삽입한다** — 캐싱 유무가 원가를 3.7배 가르는데, 이 침식은 완전히 없앨 수 없고 계측으로 감시하며 완화하는 수밖에 없다.

## Implications for Roadmap

리서치 4건이 만장일치로 도달한 결론: 거버넌스 재논의(D-20, D-31) → 신원 검증 → 멱등성 → 출력검증/탈옥방어 → 능력치 반영(읽기 다음 쓰기) → 파티 가시성 → 기억 유지 → 위협 시계의 순서가 실제 코드 의존관계에서 강제된다. 아래는 이 순서를 그대로 phase 구조로 옮긴 것이며, Phase 번호는 7부터 시작한다(Phase 1~6은 이전 마일스톤에서 이미 검증 완료).

### Phase 7: 거버넌스 재논의 — D-20, D-31 (코드 없음 또는 최소)
**Rationale:** 아키텍처·기능 리서치 모두가 독립적으로 이 두 결정이 "코드보다 먼저" 필요하다고 지적했다. D-20(캐릭터 시트 쓰기 경로 허용 여부, 특히 HP류 자원 변화량을 순수 코드 표로 정할지 재량 판정으로 정할지)과 D-31(관계 장부를 담을 다섯 번째 TurnContext 슬롯을 열지, `scene_entities`에 흡수시킬지) 둘 다 잠금 결정을 코드가 조용히 우회하지 않는다는 프로젝트 규약상 공식 재논의가 선행돼야 한다.
**Delivers:** PROJECT.md에 D-20/D-31 재논의 결과가 취소선+사유로 기록됨. 이후 phase의 설계가 이 결정에 의존.
**Addresses:** RULE, MEM 요구사항의 전제조건
**Avoids:** Pitfall 4(가변 상태 도입 시 불변식 침해), Pitfall 6(6-a 충돌, TurnContext 4칸 강제)

### Phase 8: 신원 검증 (TRUST)
**Rationale:** 다른 모든 신뢰 관련 항목(멱등성, CheckResolved.player_id 신뢰성)의 기반. 아무것도 의존하지 않으므로 가장 먼저 코드로 착수 가능.
**Delivers:** `itsdangerous` 서명 쿠키, `routes_actions.py`의 declare/confirm 쿠키 대조, `session_actor/actor.py::_prepare_confirm`의 소유자 대조(SessionActor 레벨, 라우트 레벨만으로 끝내지 않음)
**Uses:** `itsdangerous 2.2.0`(유일한 신규 패키지)
**Avoids:** Pitfall 1(라우트 계층 한정 검증)

### Phase 9: confirm 멱등성 (TRUST/QUAL 경계 — PROJECT.md 8버킷에 명시적 배정 없음, 로드맵에서 명시적으로 배정 필요)
**Rationale:** 4번(자원 쓰기)보다 반드시 먼저. 멱등성 없이 자원 쓰기가 들어가면 재시도가 "주사위 두 번"에서 "HP 두 번 깎기"로 실패 모드가 악화된다.
**Delivers:** `GameState.confirmed_declare_seqs`, 굴림/서사 단계별 부분 실패 처리, 프론트엔드 proposal 대기 중 재제출 차단(M5류 프론트 레이스 수정)
**Avoids:** Pitfall 5(멱등성 단순화)

### Phase 10: AI 출력 검증 + 탈옥 방어 (SAFE)
**Rationale:** `master_gm.py`·`prompt_assembly.py` 같은 파일을 묶어 효율적이고, 이후 phase(context_summarizer)가 과거 텍스트를 압축해 영구 재주입하기 시작하기 전에 신뢰 가능해야 한다.
**Delivers:** `agents/output_guard.py`(프로바이더 경계 정규화 + `narrate()` 레벨 백스톱), 구분자+무효화 선언(Spotlighting 기법), 필터링 시 시스템 배너(침묵 삭제 금지)
**Implements:** `agents/output_guard.py`(NEW), `prompt_assembly.py` 문자열 조립 변경
**Avoids:** Pitfall 2(청크 경계 유출), Pitfall 3(탈옥 방어 과신)

### Phase 11: 능력치 반영 — 읽기 (RULE 일부)
**Rationale:** 작고 독립적, D-20 재논의 없이도 시작 가능(변환 공식은 순수 코드 배관). 신원 검증(정확한 캐릭터) 이후 아무 때나.
**Delivers:** 룰북 표 기반 스탯→보정치 변환, `confirm()`이 `ResolveCheck.modifiers`에 대입

### Phase 12: 캐릭터 자원 쓰기 (RULE 나머지)
**Rationale:** Phase 7(거버넌스), 8(신원), 9(멱등성) 전부 선행 완료 후에만 안전.
**Delivers:** `CharacterResourceChanged` 신규 사건(EVENT_SCHEMA_VERSION v4→v5), `reducer.py` 분기(같은 커밋 필수), 캐릭터 시트 GET에 세션 상태 병합
**Avoids:** Pitfall 4(리플레이 발산), 필수: session1 실제 로그 회귀 픽스처

### Phase 13: 파티 전원 상태 가시성 (RULE 겸 FE)
**Rationale:** Phase 12의 `GameState.character_resources` 병합 로직을 그대로 재사용하므로 직후. 먼저 만들면 나중에 다시 손대야 한다.
**Delivers:** `turn/context.py::build_turn_context`가 `scene_entities`에 파티원 포함

### Phase 14: 기억 유지 — 관계 장부 + context_summarizer (MEM)
**Rationale:** Phase 10(구분자·출력검증)이 끝난 뒤 — 오염된 텍스트가 요약에 녹아들어 영구 재주입되는 것을 막기 위해. 두 하위 항목(관계 장부, context_summarizer)은 서로 다른 프롬프트 층에 들어가 병행 가능.
**Delivers:** `TurnContext` 5번째 필드(D-31 재논의 결과에 따름), `agents/context_summarizer.py`(NEW), `ContextSummarized` 신규 사건(v5→v6)
**Avoids:** Pitfall 6(캐시 파괴, 요약 드리프트) — 캐시 히트율 MEAS 계측과 함께 배치

### Phase 15: 위협 시계 — 수동 웹 경로 + 조건/AI 선택 트리거 (CLOCK)
**Rationale:** 수동 웹 경로(7-a)는 언제나 넣어도 되는 독립 항목이지만, 조건 트리거(7-b)는 Phase 14와 같은 "주기적 에이전트 호출→web이 명령 조립" 패턴을 재사용하므로 그 직후.
**Delivers:** `POST /sessions/{id}/clock/advance`(CLI 프로세스 경합 제거), `clock_advanced.trigger`에 `"manual"` 추가, 조건 판단 전용 에이전트(서사 텍스트 파싱 금지 — 42f83aa가 막은 유출 재개방 방지)
**Avoids:** Pitfall 7(죽은 지표 재생산, AI-선택 유출 재개방)

### Phase 16: 프론트엔드 재감사 + 회귀 테스트 (FE, TEST)
**Rationale:** 모든 백엔드 phase가 만드는 새 경로(신원, 멱등성, 자원 변화, 시계)를 검증할 픽스처가 필요하므로, 실제로는 Phase 8과 병행 착수해 픽스처 자체를 먼저 고쳐야 한다(Pitfall 9). React 재작성은 M2/M5/M7/L8~L10을 파일 단위로 개별 재검증하고, 2개 이상 동시 클라이언트로 감사한다.
**Delivers:** `player_id` 다중화 픽스처, declare_seq 재사용/충돌 테스트, 내용 기반 적대적 출력 대역, `asyncio.gather` 비동기 겹침 테스트

### Phase Ordering Rationale

- 거버넌스(D-20/D-31)가 최우선인 이유: PROJECT.md 자신이 "코드는 그 뒤에 손댄다"고 명시했고, 아키텍처·기능 리서치 둘 다 독립적으로 같은 결론에 도달했다.
- 신원 검증이 다른 모든 신뢰 항목의 기반인 이유: `CheckResolved.player_id`도, 멱등성 판정도, 결국 "누가 요청했나"가 조작 불가능해야 의미가 있다.
- 멱등성이 자원 쓰기보다 먼저인 이유: 실패 모드의 심각도가 "주사위 두 번"에서 "HP 두 번 깎기"로 뒤바뀌기 때문 — 아키텍처와 핏폴 리서치가 동일하게 이 순서를 지목했다.
- 출력검증이 기억 압축보다 먼저인 이유: 압축된 텍스트는 이후 모든 턴에 재주입되므로, 오염된 원문이 요약에 녹아들면 "영구히 재생되는 유출"이 된다.
- 테스트 픽스처는 병행이 아니라 선행에 가깝게 다뤄야 하는 이유: 기존 스위트의 `player_id="p1"` 고정이 구조적으로 신원 버그 클래스를 볼 수 없게 만들고 있어(H2), 다른 모든 phase의 검증이 이 픽스처 위에서 돈다.

### Research Flags

Phase 7(거버넌스 재논의)은 리서치가 아니라 프로젝트 의사결정 세션이 필요 — `/gsd-plan-phase`가 아니라 사용자와의 직접 논의로 처리하는 편이 맞을 수 있다.

Phase 12(캐릭터 자원 쓰기)와 Phase 14(기억 유지)는 계획 단계에서 `--research-phase`로 한 번 더 들여다볼 가치가 있다 — 둘 다 신규 사건 종류·`EVENT_SCHEMA_VERSION` 증가·reducer 분기가 얽히고, 특히 Phase 14는 캐시 침식이라는 미해결 트레이드오프를 안고 있어 구체 구현 시점에 재확인이 필요하다.

Phase 8(신원 검증), 9(멱등성), 10(출력검증/탈옥방어), 15(위협 시계)는 아키텍처 리서치가 파일:함수 단위로 이미 구체 통합 지점을 확정해 뒀으므로 표준 패턴으로 취급하고 추가 리서치를 생략해도 된다.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | 라이브러리 조사는 버전·이슈 트래커 교차확인(HIGH급 출처 다수)이지만, 추론 모델 스트리밍 reasoning 필드 안정성은 제공자별 편차가 커 LOW~MEDIUM |
| Features | MEDIUM(업계 사례) / HIGH(이 프로젝트 코드 진단) | 비교 대상 제품(AI Dungeon, Foundry VTT, Character.AI) 조사는 다수 출처 교차확인, 코드 대조는 session1-code-review.md 근거로 HIGH |
| Architecture | HIGH | 전부 실제 소스 파일을 함수·줄 번호 단위로 직접 읽고 확인. 단, 줄 번호는 2026-08-05 시점이라 이후 편집으로 밀릴 수 있음 |
| Pitfalls | HIGH(코드베이스 근거) / MEDIUM(외부 업계 사례) | session1-code-review.md·실제 테스트 픽스처 코드가 1차 근거, 멱등성 설계·추론 모델 유출 패턴은 웹 검색 보강 |

**Overall confidence:** MEDIUM-HIGH — 아키텍처·핏폴은 실측 코드 근거라 신뢰도가 높고, 스택·기능은 업계 사례 기반이라 상대적으로 낮지만 네 문서가 서로 독립적으로 같은 결론(D-20/D-31 선행, itsdangerous만 신규 설치, 프레임워크 기각, 캐시 침식 불가피)에 도달했다는 점이 신뢰도를 보강한다.

### Gaps to Address

- **캐시 침식의 실제 크기가 측정되지 않았다.** 관계 장부·자원 변화가 세션 고정 프롬프트 층에 들어가면 캐시 히트율이 얼마나 떨어지는지는 실측 전까지 모른다. Phase 14 착수 시 도입 전/후 MEAS 비교를 명시적으로 계획에 넣어야 한다. PROJECT.md도 원가 실측 자체가 "캐시 0% 상태였을 가능성"을 이미 인정하고 있어, 이중으로 불확실하다.
- **D-20 재논의의 실제 결론이 아직 없다.** 이 SUMMARY와 하위 리서치 4건 모두 "권장안 (i): 순수 코드 표 기반"을 제시했지만, 이건 리서치의 권고이지 확정된 결정이 아니다. Phase 7에서 사용자 승인을 받아야 한다.
- **`trigger` 리터럴에 `"manual"`을 추가하는 것이 EVENT_SCHEMA_VERSION을 올릴 만한 변경인지 이 프로젝트에 선례가 없다.** 기존 관례는 "사건 종류가 늘면" 올린다고만 되어 있고 "허용값이 늘면"은 다뤄본 적이 없어, Phase 15 계획 단계에서 명시적으로 정해야 한다.
- **멱등성 항목이 PROJECT.md의 8개 버킷(TRUST/SAFE/RULE/MEM/CLOCK/FE/QUAL/TEST) 어디에도 명시적으로 없다.** 핏폴 리서치가 지적한 대로, 로드맵 작성 시 TRUST 또는 QUAL 중 하나에 명시적으로 배정해야 한다(위 Phase 9로 이미 반영).
- **한국어 탈옥 공격에 대한 방어 검증 사례가 없다.** Spotlighting 등 참고 연구는 대부분 영어 벤치마크 기준이라, 실제 배포 후 한국어 파라프레이즈 공격에 대한 라이브 재테스트가 필요하다.

## Sources

### Primary (HIGH confidence)
- `/home/alpha-pi/GPTRPG/src/gptrpg/**` 전체 — 아키텍처·핏폴 리서치의 1차 근거, 함수·줄 번호 단위 직접 확인
- `docs/session1-code-review.md` — C1~C4, H1~H2, M1~M8 세션1 실전 사고 감사 원본
- `.planning/PROJECT.md` — D1~D33, D-59~D-63 잠금 결정, 다섯 아키텍처 불변식
- Extended thinking / Streaming messages — Claude Platform Docs (platform.claude.com/docs/en/build-with-claude/extended-thinking)
- Async Tests — FastAPI 공식 문서 (fastapi.tiangolo.com/advanced/async-tests/)
- Defending Against Indirect Prompt Injection Attacks With Spotlighting — arXiv 2403.14720
- Designing robust and predictable APIs with idempotency (Stripe blog)

### Secondary (MEDIUM confidence)
- starlette/starlette/middleware/sessions.py — GitHub, Kludex/starlette#2019 — SessionMiddleware 미채용 근거
- Reasoning models — OpenAI API docs, Reasoning Tokens — OpenRouter Docs, Gemini thinking docs — 제공자별 reasoning 필드 안정성
- AI Dungeon 멀티플레이어 UX, Character.AI 탈옥 방어 구조 분석 — splx.ai, Foundry VTT/Roll20 문서 — 비교 대상 제품 패턴
- 장기 기억 아키텍처 — arxiv 2510.07925, Blades in the Dark — Progress Clocks 공식 설명
- Designing for the inevitable: System prompt leakage — AWS Security Blog, Prompt Leakage effect — arXiv 2404.16251
- litellm Issue #29518, #26326 — 추론 모델 스트리밍 유출이 청크/필드 경계 문제라는 근거(다수 프로바이더 반복 관찰)

### Tertiary (LOW confidence)
- I Tested Reasoning Tokens on 5 LLMs via OpenRouter — Medium — 개인 블로그, 교차검증 안 됨

---
*Research completed: 2026-08-05*
*Ready for roadmap: yes*

# Phase 9: 에이전트 구조 재편 - Research

**Researched:** 2026-08-07
**Domain:** 인프로세스 에이전트 파이프라인 재편 (LLM 호출 분리 · asyncio 기반 병렬 판단 · 배경 작업 레인) — Python 3.11 백엔드, 외부 프레임워크 없음
**Confidence:** HIGH (전부 리포지토리 코드를 이번 세션에 직접 읽어 확인. 외부 라이브러리 리서치가 필요한 항목이 없다 — asyncio는 표준 라이브러리다)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** 배경 작업 자리에는 **위협 시계 조건 검사 최소판 하나만** 만든다(원래 Phase
  15/CLOCK-01 예정). 관계 기록·문맥 압축은 원래 계획대로 Phase 14로 되돌린다. 경위: 1차
  논의에서는 셋(시계·관계·압축) 전부를 최소판으로 당기기로 했으나, "한 단계에 검증 안 된
  변화량을 몰아넣는 위험"(세션1의 원인)을 피하기 위해 재검토로 되돌렸다. 시계만 남긴
  이유는 기존 `ClockAdvanced` 사건 종류를 재사용할 수 있어 새 사건 스키마가 필요 없기
  때문이다(가장 독립적이고 작음). PROJECT.md에 이 결정(당김 자체 + 관계·압축은 뺀다는 것)을
  D-63과 같은 패턴으로 기록해야 한다. Reversibility: costly — Phase 15가 이 최소판 위에 얹힌다.
- **D-02:** 위협 시계 조건 검사 최소판이 기존 `ClockAdvanced` 사건 종류로 표현 가능한지
  계획 단계에서 먼저 확인한다. 새 필드가 필요해 `EVENT_SCHEMA_VERSION`을 올려야 한다면
  `rules_core/reducer.py`의 분기를 **같은 커밋에** 반드시 동반한다.
- **D-03:** 판정 하나가 끝난 뒤 **두 조각을 병렬로 판단**한다 — (a) 이 결과가 장면에 새
  대상(인물·사물)을 등장시키는가 (b) 이 결과가 위협 시계에 영향을 주는가. 두 조각은
  서로의 출력을 쓰지 않으므로 동시에 돌 수 있다(ARCH-04). 관계 영향 판단은 뺐다(관계
  기록 배경 작업 자체가 Phase 14로 돌아갔으므로 받을 곳이 없다).
- **D-04:** (a)는 서술이 그 인물/사물을 언급해야 하므로 턴 안에서 끝나야 한다 — 서술 호출
  전에 결과를 받아 반영한다. (b)는 서술이 끝난 뒤에도 반영될 수 있다 — 배경 작업(D-01)으로
  이어져 이번 턴 서사에는 굳이 안 나와도 되고, 다음 턴부터 보이면 된다. **정직하게 남는
  미결정(계획 단계에서 풀 것):** (b)가 "턴 안 병렬 판단 → 배경 작업이 그 판단을 이어받아
  처리"라는 2단 구조인지, 배경 작업 자체가 판단부터 반영까지 통째로 맡아서 (b)의 병렬
  조각은 그 배경 작업을 "이번 턴엔 확인할 필요가 있는가"만 빠르게 거르는 문지기 역할인지는
  사용자가 특정하지 않았다.
- **D-05:** 병렬 참조 수집 중 하나가 타임아웃되면 **플레이어 화면엔 티를 내지 않는다** —
  운영자 로그에만 남긴다(ARCH-05). "없으면 없는 대로 진행"이 조용한 정상 경로다.
  `agents/invoke.py`의 `call_with_one_retry`가 이미 이 패턴(두 시도 다 실패하면 stderr에
  한 줄 찍고 실패 껍데기를 돌려준다)을 갖고 있다 — 새 규칙이 아니라 기존 규칙의 확장이다.
- **D-06:** 서술 담당에게 넘기는 것이 **판정 결과 한 줄**(`check_summary`)에서 **위 두
  조각의 판단 결과까지 포함하도록 넓어진다.** 단, **서술 담당은 여전히 진행자
  지시문·규칙·시나리오 원문 자체를 받지 않는다**(ARCH-02, 잠금 요구사항) — 넘기는 것은
  "이미 상황판단이 정한 사실"뿐이지, 그 사실을 정하는 데 쓴 지시문·규칙 원문이 아니다.

### Claude's Discretion

- **병렬 판단 조각의 실제 호출 모양** — (a)(b) 둘을 각자 독립된 작은 LLM 호출로 쪼갤지,
  한 번의 호출에서 JSON 두 칸으로 한꺼번에 받아올지는 비용·지연 트레이드오프 문제다.
  프롬프트 캐싱 구조(영구 고정 → 세션 고정 → 턴마다 변함)를 둘로 쪼갤 때도 유지할 방법을
  리서치가 확인해야 한다.
- **위협 시계 최소판이 CLOCK-02(AI 제안 → 사람 확인 화면)의 확인 게이트를 이번 단계에서
  만들지, 배경에서 자동 반영으로 갈지.** 단 D14(AI가 판정·수치에 안 닿는다)는 넘을 수
  없다 — 시계 칸 이동은 결국 코드가 확정한다.
- **`AGENT_ROLES` 확장 방식** — 새 역할 이름·모델 선택 UX(`gptrpg agents select`)를 몇
  개까지 늘릴지는 계획 단계 판단.
- 함수·모듈 이름, HTTP 응답 모양(웹 경로가 CLI와 같은 흐름을 미러링하므로 두 곳 다 고쳐야
  한다는 것만 못박는다).

### Deferred Ideas (OUT OF SCOPE)

- CLOCK-02~05 완성형(AI 제안-확인 화면, 진행자 수동 조작 화면, "왜 돌았는지" 표시, 관측
  지표 회복) → Phase 15.
- MEM-02~07 전체(관계 기록·문맥 압축, 최소판 포함 전부) → Phase 14.
- 서술 출력 검증·탈옥 방어 필터("서술이 지시문을 안 받는다"는 구조까지만 이 단계, 새는지
  검증하는 필터는 Phase 10) → Phase 10.
- 결과 카테고리 닫힌 목록(RULE-13) → Phase 12.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARCH-02 | 진행자가 「상황 판단」과 「서술」로 나뉜다 — 서술 담당은 진행자 지시문·규칙·시나리오 원문을 받지 않는다 | `master_gm.narrate()`(142~241줄)와 `prompt_assembly.build_gm_prompt`(130~166줄)의 정확한 현재 결합 지점을 확인했다. `permanent` 블록(146~157줄)이 페르소나 지시문 전체다 — 이것을 새 상황판단 호출로 옮기고 서술의 `permanent`를 최소 지시문으로 재작성하는 것이 핵심 작업. 아래 Architecture Patterns §1 참조 |
| ARCH-03 | 배경층이 구조로 있고, 산출물도 사건으로 기록되어 재생 시 같은 상태가 나온다 | `web/routes_actions.py`의 `_illustrate_scene`(576~640줄) + `BackgroundTasks.add_task`(553~563줄) + `RecordSceneIllustration` 사건 제출이 이미 "응답 후 배경 실행 → 사건으로 기록" 패턴을 완성된 형태로 갖고 있다 — 새로 발명할 필요 없이 그대로 복제한다. CLI에는 이 패턴이 없다는 것도 확인했다(중요 격차, 아래 Common Pitfalls §1 참조) |
| ARCH-04 | 병렬 실행 여부를 런타임에 판단하지 않는다 — 의존 관계가 코드에 정적으로 박힌다 | (a)(b) 두 조각은 서로 출력에 의존하지 않는다는 것이 D-03에 이미 명시됐다 — `asyncio.gather`로 정적으로 두 코루틴을 나열하면 "병렬로 돌릴지 판단하는 코드"가 아예 존재하지 않는다(분기 없음). 아래 Architecture Patterns §2 참조 |
| ARCH-05 | 병렬 참조 수집에 타임아웃이 있고 하나가 늦어도 턴이 멈추지 않는다 | `agents/invoke.py`의 `call_with_one_retry`(49~121줄)가 이미 "두 시도 다 실패해도 예외를 던지지 않고 실패 껍데기를 돌려준다"는 정확히 이 계약을 갖고 있다 — 새 타임아웃 프리미티브가 필요 없다. 아래 Don't Hand-Roll §1 참조 |
| ARCH-06 | 에이전트별로 무엇을 받는지가 코드에 명시되고 각자 상한이 있다 | `agents/context.py`의 `TurnContext`(52~62줄)가 지금 두 에이전트가 공유하는 단일 모양이다. `AGENT_ROLES`(`config.py:26`)를 확장하고 역할별 문맥 객체를 어떻게 가를지가 이 단계의 설계 결정 — 아래 Architecture Patterns §4에서 두 갈래(확장 vs 병렬 값 객체)를 비교했다 |
</phase_requirements>

## Summary

이번 리서치의 가장 큰 발견은 **위협 시계 조건 검사(CLOCK-01 최소판, D-01/D-02)가 스키마
차원에서 이미 완성되어 있다**는 것이다. `event_log/schema.py`의 `ClockAdvanced` 사건은
`trigger: Literal["fail_counter", "condition", "ai_choice"]`를 이미 선언하고 있고
[VERIFIED: src/gptrpg/event_log/schema.py:161-172], `session_actor/actor.py`의
`AdvanceClock` 명령과 `_prepare_clock`도 `condition`을 이미 검증된 값으로 받아들이며
[VERIFIED: src/gptrpg/session_actor/actor.py:132-139,620-638], CLI에는
`gptrpg submit clock --trigger condition`이라는 수동 진입점이 이미 존재한다
[VERIFIED: src/gptrpg/cli/main.py:514-520]. `tests/test_session_actor_auto_advance.py:209-227`도
`trigger="condition"`으로 actor를 직접 부르는 테스트를 이미 갖고 있다. 즉 **D-02가 묻는
질문("새 필드가 필요한가")의 답은 "아니오"다** — `EVENT_SCHEMA_VERSION`을 올릴 필요도
`reducer.py`에 새 분기를 낼 필요도 없다. 이 단계가 실제로 만들어야 하는 것은 이 기존 경로를
**AI 판단으로 자동으로 두드리는 코드**뿐이다 — 사건 종류나 저장 계층이 아니라 "언제
`AdvanceClock(trigger="condition")`을 제출할지"를 판단하고 실행하는 자리.

두 번째 발견은 **배경 실행 레인의 정확한 참조 구현이 이미 코드에 있다**는 것이다.
`web/routes_actions.py`의 `_illustrate_scene`(FastAPI `BackgroundTasks`로 응답 후 실행,
실패해도 예외를 위로 던지지 않고 stderr 경고만 남기고, 산출물을 `actor.submit(...)`으로
사건 기록에 편입)이 ARCH-03이 요구하는 모양과 정확히 같다. 새 패턴을 설계하는 대신 이
패턴을 위협 시계 조건 검사에 그대로 옮겨 적용하는 것이 가장 낮은 위험의 경로다. 단, 이
패턴은 **웹 전용**이다 — CLI(`gptrpg turn`)는 `asyncio.run()`으로 명령 하나당 프로세스
하나가 뜨고 끝나는 구조라[VERIFIED: src/gptrpg/cli/main.py:448] "응답을 보낸 뒤 배경에서"라는
개념 자체가 없다. 이 격차를 계획 단계가 명시적으로 풀어야 한다(Common Pitfalls §1).

세 번째 발견은 **병렬 판단의 타임아웃·재시도·"없으면 없는 대로" 계약이 이미
`call_with_one_retry`에 구현돼 있다**는 것이다 — 이 함수는 두 시도가 다 실패해도 예외를
던지지 않고 `ok=False` 실패 껍데기를 돌려주며 stderr에 한 줄만 남긴다
[VERIFIED: src/gptrpg/agents/invoke.py:49-121]. ARCH-05가 요구하는 것을 이 함수가 이미
만족시키므로, 이 단계가 새로 만들 것은 "이 함수를 감싼 두 호출을 asyncio로 동시에 굴리는
것"뿐이다 — 새 타임아웃 예외 클래스나 새 재시도 규칙이 필요 없다.

네 번째 발견은 **레이어 계약이 이미 "어디에 무엇을 두어야 하는가"를 강제하고 있다**는
것이다. `.importlinter` contract:2/3이 `gptrpg.agents`(그리고 co-equal `gptrpg.imagery`)를
`gptrpg.session_actor` 위 계층에 두고, `gptrpg.agents`가 `event_log`/`session_actor`를
import하는 것을 금지한다[VERIFIED: /home/alpha-pi/GPTRPG/.importlinter:9-33]. 그 결과 새
판단 조각(장면 신규 대상 판단·시계 영향 판단)은 `agents` 패키지 안에 "판단만 하고 값을
돌려주는" 함수로 살아야 하고, 그 판단 결과를 실제 `AdvanceClock`/`AppendNarration` 등의
명령으로 바꿔 `actor.submit()`하는 코드는 지금 `RecordSceneIllustration`이 그렇듯
`cli/turn_flow.py`·`web/routes_actions.py`(또는 그 사이 공유 층 `gptrpg.turn`)에 있어야
한다. 이 경계는 이미 강제되고 있으므로 계획이 어길 수 없다 — CI가 잡는다.

**Primary recommendation:** 새 사건 스키마·새 타임아웃 프리미티브·새 배경 실행 프레임워크
중 어느 것도 만들지 마라. `AdvanceClock(trigger="condition")`·`call_with_one_retry`·
`_illustrate_scene`+`BackgroundTasks` 세 가지 기존 자산을 그대로 재사용하고, 이 단계가 새로
쓰는 코드는 (1) `master_gm.narrate()`를 상황판단/서술 두 함수로 쪼개는 것 (2) 상황판단이
끝난 뒤 `asyncio.gather(asyncio.to_thread(...), asyncio.to_thread(...))`로 (a)(b) 두 판단을
동시에 굴리는 것 (3) (b)의 신호를 받아 배경 조건 검사를 실행하고 `actor.submit`으로
기록하는 자리를 여는 것 (4) `AGENT_ROLES`와 `TurnContext`를 역할별로 확장하는 것, 이
넷으로 좁혀진다.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 상황 판단(check_summary → 구조화된 사실) | `gptrpg.agents` (신규 함수, `master_gm.py` 또는 신설 모듈) | — | 페르소나 지시문·규칙 원문을 읽는 것이 이 함수의 유일한 자리 — ARCH-02가 서술에서 이 자리를 뺏는 대신 여기로 옮긴다 |
| 서술(narrate) | `gptrpg.agents` (`master_gm.narrate`, 시그니처 변경) | — | 스트리밍·문장 청크 분할(`chunk_sentences`)은 그대로 재사용, 입력만 "사실 묶음"으로 좁아진다 |
| 장면 신규 대상 판단 (a) | `gptrpg.agents` (신규 함수) | — | LLM 호출 + 닫힌 판단이므로 agents 계층. `action_classifier.py`의 닫힌 목록 패턴을 참고 |
| 시계 영향 판단 (b, 턴 내 빠른 게이트) | `gptrpg.agents` (신규 함수) | — | 같은 이유 |
| 병렬 실행 오케스트레이션(asyncio.gather) | `gptrpg.cli`/`gptrpg.web` (turn_flow.py/routes_actions.py) | `gptrpg.turn` (공유 헬퍼로 내릴 수 있음) | agents 함수들을 부르는 "여러 개를 동시에 부른다"는 순서 제어는 CLI/웹의 turn-flow 소관 — 이미 두 파일이 분류→확인→판정→서사 순서를 각자 소유하고 있다 |
| 시계 조건 검사(배경, 최소판) | `gptrpg.cli`/`gptrpg.web` (신규 판단 로직, agents 호출 포함) + `gptrpg.session_actor` (AdvanceClock 제출) | — | 조건 검사 자체(LLM 판단)는 agents 계층 함수를 부르지만, 그 결과를 사건으로 확정하는 것은 반드시 `SessionActor.submit`을 거쳐야 한다(D3, 세션당 단일 쓰기 주체) — `_illustrate_scene`이 이 경계를 정확히 지키는 기존 예시 |
| `AGENT_ROLES`/제공자 선택 확장 | `gptrpg.agents.config` | `gptrpg.cli.main` (agents select/set/show CLI) | 기존 자리 그대로, 항목 수만 늘어난다 |
| `TurnContext`/역할별 문맥 상한 | `gptrpg.agents.context` (값 객체 선언) | `gptrpg.turn.context` (조립) | 값 객체는 agents 계층(레이어 계약상 가장 아래), 저장소를 읽어 채우는 조립 로직은 그 위인 `turn` 계층 — 지금 구조와 동일한 분리를 새 역할에도 반복 |

## Standard Stack

### Core

이 단계는 **새 외부 패키지를 설치하지 않는다.** 필요한 동시성 도구는 Python 3.11 표준
라이브러리 `asyncio`(이미 `pyproject.toml`의 `requires-python = ">=3.11"`
[VERIFIED: /home/alpha-pi/GPTRPG/pyproject.toml:9]과 프로젝트 전역의 `async def` 구조에
이미 쓰이고 있다)로 전부 해결된다.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `asyncio` (표준 라이브러리) | Python 3.11+ 내장 | `asyncio.gather` + `asyncio.to_thread`로 동기 `Provider.complete()` 호출 두 개를 동시에 굴린다 | 이미 `cli/turn_flow.py`·`web/routes_actions.py` 전체가 `async def`이고, 웹 경로는 이미 `asyncio.to_thread`로 막는 AI 호출을 작업 스레드로 내보내고 있다[VERIFIED: src/gptrpg/web/routes_actions.py:234-242,482,500] — 같은 패턴의 확장일 뿐 새 개념이 아니다 |
| `fastapi.BackgroundTasks` (기존 의존성) | `fastapi>=0.141.1`[VERIFIED: /home/alpha-pi/GPTRPG/pyproject.toml:12] | 응답을 보낸 뒤 배경에서 시계 조건 검사를 실행 | 이미 `_illustrate_scene`이 정확히 이 용도로 쓰고 있다[VERIFIED: src/gptrpg/web/routes_actions.py:551-563] — 새 의존성이 아니라 기존 것의 두 번째 사용처 |

### Supporting

새로 추가할 라이브러리 없음. `agents/invoke.py`의 `call_with_one_retry`, `agents/envelope.py`의
`AgentResult`, `agents/action_classifier.py`의 `_try_parse_json_array` 강건 파싱을 그대로
재사용한다(아래 Don't Hand-Roll 참조).

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncio.gather` + `asyncio.to_thread` | `concurrent.futures.ThreadPoolExecutor` 직접 관리 | asyncio가 이미 이벤트 루프를 쥐고 있는 상태(cli/web 둘 다 `async def` 안)에서 별도 executor를 만들면 `SessionActor`의 큐 소비 태스크와 스레드 풀 두 개의 동시성 모델이 한 프로세스에 공존해 디버깅이 어려워진다. `asyncio.to_thread`는 내부적으로 기본 executor를 재사용하므로 충돌이 없다 |
| `asyncio.wait_for`로 감싼 타임아웃 | `call_with_one_retry`의 기존 `timeout_s` 파라미터(제공자 자신이 끊음) | `call_with_one_retry`는 이미 제공자 레벨 타임아웃 + 재시도 1회 + "실패해도 예외 안 던짐"을 갖고 있다. `asyncio.wait_for`를 추가로 씌우면 이중 타임아웃이 되어 어느 쪽이 실제로 끊었는지 진단이 어려워진다 — 새 타임아웃 값을 추가하지 않는다 |
| `AGENT_ROLES` 확장으로 새 provider/model 축 추가 | 병렬 판단 두 조각을 별도 역할로 안 만들고 `master_gm`이 한 호출에서 JSON 세 칸(사실+장면판단+시계판단)을 한 번에 받기 | 프롬프트 캐싱 순서(영구→세션→턴)와 "무엇을 병렬로 돌릴지 정적으로 박는다"는 ARCH-04 취지를 생각하면, 하나로 합치면 캐싱 안정 블록에 판단 지시문 두 개가 얹혀 캐시 무효화 위험이 커지고 무엇보다 "병렬"이라는 구조 자체가 사라진다(단일 호출은 병렬이 아니다) — Claude's Discretion 항목이지만 별도 호출을 권장 |

**Installation:** 없음 — 표준 라이브러리 + 기존 의존성만 사용.

**Version verification:** 새 패키지가 없으므로 레지스트리 확인 생략. `fastapi>=0.141.1`는
이미 `pyproject.toml`에 고정된 기존 의존성이다.

## Package Legitimacy Audit

**이 단계는 새 외부 패키지를 설치하지 않는다.** `pyproject.toml`의 기존 여섯 개 의존성
(`anthropic`, `fastapi`, `google-genai`, `openai`, `pydantic`, `uvicorn`)과 표준 라이브러리
`asyncio`만으로 충분하다[VERIFIED: /home/alpha-pi/GPTRPG/pyproject.toml:10-17]. Package
Legitimacy Gate 프로토콜은 스킵한다 — 검사할 신규 패키지가 없다.

**Packages removed due to [SLOP] verdict:** 없음 (신규 패키지 없음)
**Packages flagged as suspicious [SUS]:** 없음 (신규 패키지 없음)

## Architecture Patterns

### System Architecture Diagram

```
                    ① 임계 경로 (순차 고정, D-64)
플레이어 문장
   │
   ▼
DeclareAction 제출 ──▶ SessionActor(단일 쓰기 주체) ──▶ action_declared 사건
   │
   ▼
action_classifier.classify()  (기존, 안 바뀜)
   │
   ▼
사람 확인 (세 갈래 화면, 기존)
   │
   ▼
ResolveCheck 제출 ──▶ SessionActor ──▶ check_resolved 사건 (판정 결과 확정)
   │
   ▼
┌──────────────────────────────────────────────────────────┐
│ ② 참조 수집 (병렬 가능, ARCH-04 — 의존관계 정적으로 고정)      │
│                                                              │
│  situation_judge()          judge_new_entity()  judge_clock_signal() │
│  (상황판단, 지시문/규칙 O)      (a, 장면 신규대상)   (b, 시계 영향 신호)  │
│         │                        │  asyncio.gather(         │
│         │                        │    to_thread(judge_a),   │
│         │                        │    to_thread(judge_b))   │
│         │                        │  각각 call_with_one_retry로 │
│         │                        │  감싸 개별 타임아웃 —      │
│         │                        │  하나 실패해도 "없으면    │
│         │                        │  없는대로" 진행(ARCH-05)  │
│         ▼                        ▼                          │
│      facts 묶음 = {check_summary, 신규대상 판단, 시계신호}    │
└──────────────────────────────────────────────────────────┘
   │
   ▼
narrate(facts)  — 페르소나 지시문·규칙·시나리오 원문 없음(ARCH-02)
   │  (chunk_sentences로 문장 단위 스트리밍, 기존 로직 그대로)
   ▼
AppendNarration 제출 ──▶ SessionActor ──▶ narration_appended 사건들
   │
   ▼
응답 반환 (웹: HTTP 응답 / CLI: 화면 출력)
   │
   ▼
┌──────────────────────────────────────────────────────────┐
│ ③ 배경 (턴 밖, D-64) — 웹: BackgroundTasks / CLI: 반드시 await │
│                                                              │
│  (b)의 신호가 "가능성 있음"이면:                              │
│    check_threat_clock_condition()  — 시계 segment_descriptions │
│    대비 실제 조건 충족 여부를 더 깊이 판단(LLM 또는 룰 기반)      │
│         │ 조건 충족이면                                       │
│         ▼                                                    │
│    actor.submit(AdvanceClock(trigger="condition", ...))       │
│         ▼                                                    │
│    clock_advanced 사건 (기존 스키마 그대로, 새 필드 불필요)      │
└──────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
src/gptrpg/agents/
├── master_gm.py          # narrate()만 남기고 좁힌다 — 스트리밍/청크 로직 그대로
├── situation_judge.py     # 신설: 상황판단(페르소나+규칙+판정결과 → 구조화 사실), narrate에 넘길 facts 조립
├── scene_entity_judge.py  # 신설: 판단 (a) — 닫힌 판단, action_classifier의 강건 JSON 파싱 재사용
├── clock_signal_judge.py  # 신설: 판단 (b) — 턴 내 빠른 게이트 신호
├── prompt_assembly.py     # build_gm_prompt를 좁히고 build_situation_prompt를 추가 — 캐싱 순서 규약 유지
├── context.py             # TurnContext 유지 + 역할별 문맥 값 객체(필요 시) 추가
├── config.py              # AGENT_ROLES 확장
└── invoke.py              # 그대로, 새 역할의 타임아웃 상수만 추가

src/gptrpg/session_actor/
└── actor.py               # 변경 없음 — AdvanceClock/trigger="condition" 이미 완성

src/gptrpg/cli/turn_flow.py       # ②③ 오케스트레이션 추가 (asyncio.gather, 배경 await)
src/gptrpg/web/routes_actions.py  # ②③ 오케스트레이션 추가 (asyncio.gather, BackgroundTasks)
```

### Pattern 1: 상황판단/서술 분리 — narrate()의 정확한 현재 결합 지점

**What:** `master_gm.narrate()`는 지금 `build_gm_prompt(rulebook_display_name, ctx,
check_summary)`를 호출해 `system`(permanent+session 두 캐시 블록)과 `messages`(turn 블록)를
한 번에 만들고 스트리밍한다[VERIFIED: src/gptrpg/agents/master_gm.py:186-188]. `permanent`
블록은 다음 지시문 전체를 담는다(그대로 인용):

> "너는 {rulebook_display_name} 룰북을 쓰는 TRPG의 진행자다. 판정 결과를 받아 다음에 무슨
> 일이 일어나는지 서술한다. 수치나 판정 결과를 새로 정하지 않는다 — 이미 정해진 값을
> 그대로 반영해서 서술만 한다. 위협 시계가 다음 칸으로 넘어갔는지도 네가 정하지 않는다 —
> 그건 판정 실패가 쌓이면 시스템이 자동으로 결정하고..."
[VERIFIED: src/gptrpg/agents/prompt_assembly.py:146-158]

이 블록 자체는 이미 "너는 진행자다" 수준의 역할 지시문이지 시나리오 원문·규칙 표는 아니다
— `_session_block_text`가 장면 대상/캐릭터 상태/시계 상태를 별도 캐시 블록으로 붙인다
[VERIFIED: src/gptrpg/agents/prompt_assembly.py:97-102]. ARCH-02가 막으려는 유출은 이보다
더 위험한 것 — **진행자 판단 지시문(무엇을 언제 판단할지, 어떤 닫힌 목록을 쓰는지 등
"상황판단" 몫으로 옮겨갈 지시문)과 시나리오 원문(`M0_THREAT_CLOCK`의 정체·원하는 것·칸
설명 전체)**이 지금 `_format_clock_state`를 통해 서술 프롬프트에 그대로 들어가고 있다는
점이다[VERIFIED: src/gptrpg/agents/prompt_assembly.py:51-88,159]. 세션1 사고(지시문 유출)의
실제 원인이 여기다.

**When to use:** 이번 단계 필수 작업. `narrate()`의 새 시그니처는 `check_summary: str`
대신 구조화된 "사실 묶음"(D-06)을 받아야 하고, `build_gm_prompt`의 `permanent` 블록에서
현재 `_session_block_text`가 통째로 넣는 시나리오 내용(`_format_clock_state`의 정체/원하는
것/지나온 칸/파국 텍스트)을 서술 쪽에서 제거하거나 최소화해야 한다 — 그 시나리오 판단은
상황판단 쪽으로 옮기고, 서술에는 "지금 이 칸에서 무슨 일이 벌어지는가"의 한 줄 요약만
넘긴다.

**Example (현재 서명, 변경 대상):**
```python
# Source: src/gptrpg/agents/master_gm.py:142-149 (VERIFIED, 이번 세션에 읽음)
def narrate(
    *,
    provider: Provider,
    model: str,
    ctx: TurnContext,
    check_summary: str,  # ← 이 한 줄짜리 문자열이 D-06이 요구하는 "사실 묶음"으로 넓어져야 한다
    rulebook_display_name: str,
    stall_timeout_s: float = STREAM_STALL_TIMEOUT_S,
) -> Iterator[str]:
```

**주의:** `chunk_sentences`·`_drain_with_stall_timeout`·스톨 재시도 3갈래 로직
[VERIFIED: src/gptrpg/agents/master_gm.py:114-241]은 전부 스트리밍 메커니즘이지 프롬프트
내용과 무관하다 — 이 단계에서 손대지 않는다. 바뀌는 것은 `build_gm_prompt`가 받는 입력과
그 안에서 조립하는 텍스트뿐이다.

### Pattern 2: 병렬 판단 — asyncio.gather + asyncio.to_thread로 정적 병렬화

**What:** ARCH-04는 "무엇을 병렬로 돌릴지 런타임에 판단하지 않는다"를 요구한다. 코드
차원에서 이것은 "if 분기로 병렬 여부를 정하지 않는다"는 뜻이다 — `asyncio.gather`에
코루틴 두 개를 **항상** 나열하면 그 자체로 요구사항이 충족된다(무엇을 병렬로 할지 정하는
런타임 분기가 아예 없다, 항상 둘 다 부른다). 지금 프로젝트에 `asyncio.gather`나
`asyncio.wait_for` 사용례가 하나도 없다(grep 결과 0건) — 이 단계가 이 패턴을 처음
도입한다. 다만 `asyncio.to_thread`로 동기 함수를 작업 스레드로 내보내는 패턴은 이미 웹
경로에 있다[VERIFIED: src/gptrpg/web/routes_actions.py:234-242].

**When to use:** 판정 결과(check_resolved)가 확정된 직후, 서술 호출 전. (a)(b) 두 판단이
서로의 출력에 의존하지 않는다는 것이 D-03에 이미 명시되어 있으므로 이 지점이 유일한
후보다.

**Example (신규 패턴, 이 단계가 작성):**
```python
# 개념 예시 — 정확한 함수 시그니처는 계획 단계가 정한다.
# call_with_one_retry가 이미 "실패해도 예외 없이 ok=False 껍데기"를 보장하므로
# asyncio.wait_for 같은 추가 타임아웃 레이어가 필요 없다(Don't Hand-Roll §1 참조).
import asyncio

async def gather_parallel_judgments(
    *, provider_a, model_a, provider_b, model_b, ctx, check_summary,
) -> tuple[EntityJudgment, ClockSignal]:
    entity_result, clock_result = await asyncio.gather(
        asyncio.to_thread(judge_new_entity, provider=provider_a, model=model_a,
                           ctx=ctx, check_summary=check_summary),
        asyncio.to_thread(judge_clock_signal, provider=provider_b, model=model_b,
                           ctx=ctx, check_summary=check_summary),
    )
    return entity_result, clock_result
```

**Anti-pattern:** `if should_run_parallel(...): asyncio.gather(...) else: sequential(...)`
같은 조건부 병렬화 — ARCH-04가 명시적으로 금지하는 모양이다. 항상 `gather`로 두 개를
부르고, 결과가 "빈 판단"(실패 껍데기)이면 그 결과 자체를 정상 경로로 처리한다.

### Pattern 3: 배경 실행 레인 — 기존 `_illustrate_scene` 패턴을 그대로 복제

**What:** `web/routes_actions.py`의 `confirm()` 라우트는 성공한 턴에서만, **응답을 만든
뒤** `background.add_task(_illustrate_scene, ...)`를 건다
[VERIFIED: src/gptrpg/web/routes_actions.py:548-563]. `_illustrate_scene`은:
1. 렌더링(느린 작업)을 `asyncio.to_thread`로 작업 스레드에 내보낸다.
2. 실패하면(`RendererUnavailable` 또는 그 외 `Exception`) **예외를 위로 던지지 않고**
   stderr에 경고 한 줄만 남기고 조용히 끝낸다
   [VERIFIED: src/gptrpg/web/routes_actions.py:617-622].
3. 성공하면 사건 제출은 이벤트 루프로 돌아와 `actor.submit(RecordSceneIllustration(...))`로
   한다[VERIFIED: src/gptrpg/web/routes_actions.py:624-639] — 그림 층(`imagery`)은
   `session_actor`를 import할 수 없으므로(contract:4) `web`이 값을 받아 명령으로
   조립하는 것이 유일한 통로라고 모듈 docstring이 명시한다
   [VERIFIED: src/gptrpg/session_actor/actor.py:165-169].

이 세 단계가 정확히 ARCH-03이 요구하는 것과 같다 — "사람이 안 기다리는 작업을 배경으로
돌리고, 그 산출물도 사건으로 기록되어 재생하면 같은 상태가 나온다."

**When to use:** 시계 조건 검사의 웹 경로 구현에 그대로 복제한다 — `_illustrate_scene`을
`_check_threat_clock_condition`으로 이름만 바꾼 자매 함수로 만들고, 렌더링 대신 조건 판단
LLM 호출(또는 룰 기반 검사)을 작업 스레드로 보내고, 성공 시 `actor.submit(AdvanceClock(
trigger="condition", clock_id=..., segment_index=state.clock_segment + 1))`로 마친다.

**Anti-pattern — 이 단계에서 반드시 피해야 할 것:** 배경 태스크 안에서 `SessionActor`를
우회하는 별도 쓰기 경로를 만드는 것. `session_actor/actor.py`의 canonical_refs가 이미 이를
"절대 금지"로 못박았다(D3 위반) — 배경 작업도 반드시 `actor.submit(...)`을 거쳐야 한다.

### Pattern 4: `AGENT_ROLES`/`TurnContext` 확장 — 두 갈래 비교

**What:** 지금 `AGENT_ROLES: tuple[str, ...] = ("action_classifier", "master_gm")`
[VERIFIED: src/gptrpg/agents/config.py:26]이고, `TurnContext`는 두 에이전트가 완전히 같은
네 칸(`scene_entities`, `character_state`, `clock_state`, `recent_turns`)을 공유한다
[VERIFIED: src/gptrpg/agents/context.py:51-58]. D-66은 "칸 위치는 캐싱에 영향이 없다,
진짜 레버는 갱신 빈도"라고 이미 결론 내렸다(PROJECT.md) — 즉 **역할마다 완전히 다른
dataclass를 만들 필요는 없다**. 두 갈래:

| 갈래 | 방식 | 장점 | 단점 |
|------|------|------|------|
| A. `TurnContext` 그대로 재사용 + 역할별 프롬프트 조립 함수가 필요한 칸만 골라 쓴다 | 새 값 객체 없음, `build_xxx_prompt`마다 `ctx`에서 다른 부분집합을 읽음 | 최소 변경, 기존 `_format_*` 헬퍼 재사용 그대로 | "각자 상한이 있다"(ARCH-06)를 코드로 강제하기 약함 — 문서화된 관례에 의존 |
| B. 역할별 문맥 dataclass(`SituationContext`, `EntityJudgeContext`, `ClockJudgeContext`) 신설, 각각 필요한 칸만 필드로 선언 | ARCH-06을 타입 시스템이 강제 — 안 쓰는 칸은 애초에 그 dataclass에 없다 | `build_turn_context`(turn/context.py)가 여러 값 객체를 만들어야 해 조립 코드가 늘어난다 |

**Recommendation:** B를 권장한다 — `TurnContext.__post_init__`이 이미 `RECENT_TURNS_LIMIT`
초과를 예외로 강제하는 것과 같은 스타일로, "이 역할은 이 칸만 받는다"를 타입으로
강제하는 것이 ARCH-06의 "코드에 명시되고 각자 상한이 있다"는 문구에 더 직접적으로
부합한다. 단, 이것은 Claude's Discretion 항목이므로 계획 단계가 최종 결정한다.

**Example (D-32/`resolve_provider`의 기존 확장 지점, 그대로 재사용):**
```python
# Source: src/gptrpg/agents/config.py:26-27 (VERIFIED)
AGENT_ROLES: tuple[str, ...] = ("action_classifier", "master_gm")
"""D-32가 요구하는 두 에이전트 역할 — 각자 따로 제공자·모델을 고른다."""
# → ("action_classifier", "master_gm", "scene_entity_judge", "clock_signal_judge")
#   형태로 확장. load_config/save_config/resolve_provider는 AGENT_ROLES를 순회하므로
#   (config.py:82, 124) 이 튜플만 늘리면 나머지는 자동으로 새 역할을 인식한다.
```

### Anti-Patterns to Avoid

- **배경 태스크를 CLI에서 `asyncio.create_task`로 던지고 안 기다리기:** `gptrpg turn`은
  `asyncio.run(run_turn(store, args))`로 명령 하나당 프로세스 하나가 뜨고 끝난다
  [VERIFIED: src/gptrpg/cli/main.py:448]. `asyncio.run()`이 반환하는 순간 이벤트 루프가
  닫히므로, await하지 않은 태스크는 실행되다 말거나 아예 스케줄되지 않은 채 프로세스가
  죽는다 — ARCH-03이 요구하는 "산출물이 사건으로 기록된다"가 CLI 경로에서 조용히
  깨진다. 자세한 내용은 Common Pitfalls §1.
- **병렬 판단 결과를 서술 프롬프트의 `permanent`(영구 고정) 블록에 넣기:** 판단 결과는
  턴마다 다른 값이므로 `session`/`turn` 블록에 들어가야 한다 — `permanent`에 넣으면
  프롬프트 캐싱이 매 턴 깨진다(원가 3.7배 차이, `prompt_assembly.py:1-15` 규약).
- **`_prepare_clock`이 이미 하는 검증을 새 코드에서 중복하기:** `trigger`가
  `_VALID_CLOCK_TRIGGERS`(`{"fail_counter", "condition", "ai_choice"}`) 안에 있는지,
  `segment_index >= 0`인지는 이미 액터가 검증한다[VERIFIED:
  src/gptrpg/session_actor/actor.py:192,620-628] — 배경 조건 검사 코드가 이 검증을
  또 하지 않는다(D-11이 확립한 "검증은 액터가 최종 방어선" 원칙과 같은 이유).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| 병렬 참조 수집 타임아웃 + "없으면 없는 대로 진행" | 새 `TimeoutError` 서브클래스, 새 재시도 데코레이터 | `agents/invoke.py`의 `call_with_one_retry(fn, timeout_s=...)` | 이미 "제공자 타임아웃 + 재시도 1회 + 실패해도 예외 없이 `(AgentResult(ok=False,...), error_text)` 반환 + stderr 경고"를 전부 갖추고 있다[VERIFIED: src/gptrpg/agents/invoke.py:49-121]. 판단 (a)(b) 각각을 이 함수로 감싸기만 하면 ARCH-05가 이미 만족된다 |
| 배경 작업 실행 인프라(웹) | 커스텀 태스크 큐, Celery류 도입 | `fastapi.BackgroundTasks` (이미 `_illustrate_scene`이 씀) | 이미 검증된 in-process 배경 실행 경로가 존재한다. 새 인프라를 들이면 REQUIREMENTS.md의 Out of Scope("LangChain·LlamaIndex 류 프레임워크 도입" — 같은 정신으로 무거운 인프라 회피)와 어긋난다 |
| 위협 시계 조건 검사용 새 사건 종류 | `ClockConditionChecked` 같은 신규 이벤트 클래스 | 기존 `ClockAdvanced`(`trigger="condition"`) | 스키마가 이미 이 값을 받는다[VERIFIED: src/gptrpg/event_log/schema.py:161-172]. 새 이벤트를 만들면 `EVENT_SCHEMA_VERSION`을 올려야 하고(D-02가 명시적으로 막으려는 것), Phase 8이 반복 경고한 "reducer 분기 누락 시 세션 영구 잠김" 위험을 다시 만든다 |
| 강건한 JSON 응답 파싱(추론형 모델의 `<think>` 블록·코드펜스 처리) | 새 정규식/파서 | `action_classifier._try_parse_json_array`(77~116줄)를 공유 유틸로 승격하거나 그대로 import | 이미 3단계 파싱(원문 그대로 → think 블록 제거+코드펜스 벗기기 → 실패 시 빈 목록)이 검증돼 있다[VERIFIED: src/gptrpg/agents/action_classifier.py:77-116] — 판단 (a)(b)도 JSON을 돌려받을 가능성이 높으므로 그대로 재사용 |
| 역할별 provider/model 설정 저장·해석 | 새 설정 파일 포맷, 새 CLI 서브커맨드 구조 | `agents/config.py`의 `AGENT_ROLES`/`load_config`/`resolve_provider` (튜플만 확장) | `load_config`/`save_config`/`resolve_provider` 전부 `AGENT_ROLES`를 순회하는 제네릭 코드다 — 튜플에 이름만 추가하면 CLI(`agents select/set/show`)가 자동으로 새 역할을 인식한다 |

**Key insight:** 이 단계의 위험은 "무엇을 새로 만들 것인가"가 아니라 "이미 있는 것을
다시 만들지 않는 것"이다. D-64/D-66이 연 구조적 자리(배경층, 병렬 판단, 조건 트리거)를
실제로 채우는 것이 처음이라는 CONTEXT.md의 서술은 맞지만, 그 자리를 채울 때 쓸 하부
부품(타임아웃, 배경 실행, 조건 트리거 이벤트)은 이미 다른 목적(스톨 워치독, 삽화 생성,
실패 카운터 진행)으로 만들어져 검증된 채 있다.

## Common Pitfalls

### Pitfall 1: CLI의 "배경" 작업이 프로세스 종료로 유실된다

**What goes wrong:** 웹 경로의 `BackgroundTasks`를 그대로 흉내 내 CLI에서
`asyncio.create_task(check_threat_clock_condition(...))`를 걸고 기다리지 않으면, `run_turn`이
반환하고 `asyncio.run()`이 이벤트 루프를 닫는 순간 그 태스크는 실행되다 말거나 아예
스케줄되지 못한 채 사라진다.

**Why it happens:** CLI `turn` 서브커맨드는 명령 하나당 새 파이썬 프로세스가 뜨는
구조다[VERIFIED: src/gptrpg/cli/main.py:448, `asyncio.run(run_turn(store, args))`] — 웹
서버(uvicorn, 세션 내내 살아있는 프로세스)와 근본적으로 다른 생명주기다. 웹의
"응답 후 배경"이라는 개념 자체가 "요청-응답 사이에 서버 프로세스는 계속 산다"는 전제에서만
성립한다.

**How to avoid:** CLI 경로에서는 시계 조건 검사를 진짜 "배경"으로 만들지 말고, 서사
스트리밍이 끝난 뒤 **`actor.stop()`을 부르기 전에 명시적으로 `await`**하는 형태로
설계한다 — 순서상으로는 여전히 "임계 경로 밖"(서사 다음에 옴, 응답 지연에 영향 없음)이지만
CLI 프로세스가 죽기 전에는 반드시 끝나야 한다. 웹은 `BackgroundTasks`(진짜 논블로킹), CLI는
"순서는 배경이지만 실행은 동기적으로 await"라는 비대칭을 계획 문서에 명시적으로 적어야
한다 — 그렇지 않으면 실행 단계에서 "CLI가 왜 배경 작업을 안 기다리냐"는 잘못된 대칭
가정으로 버그가 난다.

**Warning signs:** CLI로 여러 턴을 연속 실행했을 때 시계가 조건 트리거로는 전혀 안
도는데 웹에서는 도는 비대칭 동작.

### Pitfall 2: 서술 프롬프트에서 시나리오 원문을 "빼는 것"과 "요약해서 넣는 것"을 혼동

**What goes wrong:** ARCH-02를 "서술이 `_format_clock_state`를 아예 안 부르게 한다"로
해석하면, 서술이 지금 칸에서 무슨 일이 일어나는지 전혀 모르는 채로 서사를 쓰게 되어 품질이
무너진다. 반대로 지금처럼 정체·원하는 것·지나온 칸 전체·파국 문장까지 그대로 다 넘기면
ARCH-02가 막으려던 유출면이 그대로 남는다.

**Why it happens:** "지시문·규칙·시나리오 원문을 안 받는다"는 요구사항이 "아무 것도 안
받는다"가 아니라 "**상황판단이 이미 걸러낸 사실만** 받는다"는 뜻이라는 것이 D-06에
명시돼 있다("넘기는 것은 이미 상황판단이 정한 사실뿐이지, 그 사실을 정하는 데 쓴
지시문·규칙 원문이 아니다"). 이 구분이 프롬프트 조립 코드 수준에서는 미묘하다 — 지금
`_format_clock_state`가 하는 일(정체/원하는 것/지나온 칸 전체를 텍스트로 펼침)은 사실
"시나리오 원문 그대로 노출"에 가깝다.

**How to avoid:** 상황판단 단계가 `_format_clock_state`가 만드는 전체 텍스트를 **읽고**,
"지금 이 칸에서 서술에 필요한 한두 문장"만 뽑아 서술에 넘긴다. 시나리오 원문 자체
(정체·원하는 것·파국 텍스트 전체)는 상황판단의 `system`(캐싱 대상, 서술에는 넘어가지 않음)
안에만 머문다.

**Warning signs:** 서술 프롬프트의 `system`/`messages`를 로그로 찍었을 때 시나리오의
"정체"·"원하는 것" 원문 문자열이 그대로 보이면 실패.

### Pitfall 3: 병렬 판단이 `check_resolved` 사건 없이도 돌 수 있다고 가정

**What goes wrong:** (a)(b) 두 판단을 `ResolveCheck` 제출 직후가 아니라 `DeclareAction`
직후처럼 이른 시점에 걸면, 아직 확정되지 않은 판정 결과를 놓고 판단하게 되어 "장면에 새
대상이 등장하는가"가 실제 판정 결과(성공/실패)와 안 맞을 수 있다.

**Why it happens:** D-03이 "판정 하나가 끝난 뒤"라고 명시했지만, 코드 구조상 판정 결과
줄(`check_summary`)이 만들어지는 지점(`cli/turn_flow.py:289`,
`web/routes_actions.py:436`)과 서술 호출 지점(`cli/turn_flow.py:313`,
`web/routes_actions.py:475`) 사이에 여러 갈래(재사용 판정, 실패 처리)가 있어 삽입 지점을
잘못 고르기 쉽다.

**How to avoid:** 병렬 판단 삽입 지점을 정확히 `check_event`/`check_summary`가 확정된
직후, `narrate(...)` 호출 직전으로 고정한다 — CLI는 289~291줄 사이, 웹은 436~453줄 사이.

**Warning signs:** 판정이 실패로 끝났는데 (a) 판단이 "성공했다"는 전제로 이야기를 짓는 경우.

## Code Examples

### 기존 타임아웃/재시도 계약 재사용 (변경 없이 그대로 import)

```python
# Source: src/gptrpg/agents/invoke.py:49-121 (VERIFIED, 이번 세션에 읽음)
def call_with_one_retry(
    fn: Callable[[], AgentResult], *, timeout_s: float
) -> tuple[AgentResult, str | None]:
    """`fn`을 최대 `MAX_ATTEMPTS`번 부른다 — 첫 시도 + 재시도 한 번, 그것으로 끝.
    ...
    두 시도가 모두 실패하면 예외를 밖으로 던지지 않고 실패 껍데기를
    돌려준다 ...
    """
```
병렬 판단 (a)(b) 각각을 `lambda: provider.complete(...)` 형태로 감싸 이 함수에 넘기면
ARCH-05가 요구하는 "타임아웃 있음 + 하나 실패해도 턴이 안 멈춤"이 추가 코드 없이 충족된다.

### 기존 배경 실행 패턴 (그대로 복제할 대상)

```python
# Source: src/gptrpg/web/routes_actions.py:548-563 (VERIFIED)
imagery_config: ImageryConfig = request.app.state.imagery_config
if imagery_config.enabled:
    background.add_task(
        _illustrate_scene,
        actor=actor,
        renderer=request.app.state.renderer,
        config=imagery_config,
        session_id=session_id,
        resolve_seq=resolve_seq,
        move=body.move,
        grade=check_event.grade,
        clock_segment=ctx.clock_state.segment_index,
    )
```
시계 조건 검사의 웹 구현은 `_illustrate_scene` 대신 `_check_threat_clock_condition`을
`background.add_task`로 걸고, `renderer` 대신 판단용 provider/model을 넘긴다.

### 이미 검증된 조건 트리거 진입점 (CLI 수동 경로, 자동화의 참조 모양)

```python
# Source: src/gptrpg/cli/main.py:514-520 (VERIFIED)
clock_parser = submit_subparsers.add_parser("clock")
clock_parser.add_argument("--clock-id", required=True)
clock_parser.add_argument("--segment", type=int, required=True)
clock_parser.add_argument(
    "--trigger", required=True, choices=["fail_counter", "condition", "ai_choice"]
)
clock_parser.add_argument("--caused-by", type=int, default=None)
```
```python
# Source: tests/test_session_actor_auto_advance.py:209-227 (VERIFIED)
async def test_advancing_clock_past_segment_count_is_never_rejected(tmp_db_path):
    store, actor = _make_actor(tmp_db_path, values=[])
    try:
        for segment_index in range(1, 6):
            await actor.submit(
                AdvanceClock(clock_id="threat", segment_index=segment_index, trigger="condition")
            )
    finally:
        await actor.stop()
    state = rebuild_state(store, "s1")
    assert state.clock_segment == 5
```
이 테스트가 이미 `trigger="condition"`이 액터 레벨에서 완전히 동작함을 증명한다. 이
단계가 새로 만들 코드는 이 `actor.submit(AdvanceClock(...))` 호출을 **AI 판단으로 자동
발동시키는** 부분뿐이다. 주의: `_prepare_clock`은 `segment_count` 상한을 검사하지 않는다
[VERIFIED: src/gptrpg/session_actor/actor.py:620-638] — 상한 검사(`state.clock_segment >=
self._clock_segment_count`)는 `_maybe_auto_advance`에만 있다
[VERIFIED: src/gptrpg/session_actor/actor.py:384-389]. 새 조건 검사 코드가 직접
`AdvanceClock`을 제출할 때는 이 상한을 스스로 검사해야 한다.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `master_gm.narrate()` 하나가 페르소나+시나리오+판정결과를 전부 받아 서술까지 한 호출로 처리 | 상황판단(페르소나·규칙·시나리오 O)과 서술(사실 묶음만) 두 호출로 분리 | 이번 단계(ARCH-02) | 지시문 유출 표면이 구조적으로 줄어든다 — 서술 프롬프트에 애초에 유출할 지시문이 없다 |
| 위협 시계는 실패 카운터(`fail_counter`)로만 자동 진행 | `condition` 트리거를 AI 판단이 자동으로 발동 | 이번 단계(ARCH-03/CLOCK-01 최소판) | `failure_to_clock_ratio`가 항상 3.0에 고정되던 문제(H2 관측 지표 죽음, D-60)가 CLOCK-05로 가는 첫걸음을 뗀다 — 단 이번 단계는 로직·배경 자리까지만, 관측 지표 회복은 Phase 15 |
| 에이전트 둘(`action_classifier`, `master_gm`), 순차 호출만 | 에이전트 넷 이상, 순차+병렬+배경 3층 | Phase 7(D-64)이 구조를 열었고 이번 단계가 처음 채운다 | D17(에이전트 10개→4개 축소)이 판단 쪽으로는 되살아나고 연산 쪽으로는 안 되살아난다(D14 경계 유지) |

**Deprecated/outdated:** 없음 — 이 단계가 대체하는 대상은 미완성 자리(D-64/D-66이 구조만
열어둔 것)이지 폐기해야 할 기존 구현이 아니다.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | D-04의 미결정("2단 구조" vs "배경이 통째로 맡고 (b)는 문지기")에 대해, 후자(배경이 실제 조건 판단+제출을 맡고 (b)는 "이번 턴 확인이 필요한가"만 거르는 빠른 게이트)를 권장했다 — 원가를 이번 milestone 판단 기준에서 뺀다는 D-64 공통 전제와는 별개로, 중복 LLM 판단을 피하고 "배경 작업 자리 = 시계 조건 검사 그 자체"라는 D-01의 문구와 더 정확히 부합한다는 추론에 근거한다 | Architecture Patterns §2, Summary | 계획 단계가 반대로(진짜 2단계 판단, (b)도 완전한 조건 판단) 선택하면 이 리서치의 함수 분할 제안(judge_clock_signal vs check_threat_clock_condition)의 경계가 다시 그려져야 한다 — 코드량에는 큰 영향 없음, 설계 문서 수정 정도 |
| A2 | `TurnContext`를 역할별 dataclass로 쪼개는 것(Pattern 4의 갈래 B)을 권장했다 — 기존 코드에 유사 사례가 없어(지금 유일한 값 객체 `TurnContext`는 두 역할이 완전히 공유) 순수 설계 추론이다 | Architecture Patterns §4 | 계획이 갈래 A(공유 유지)를 선택해도 기능적으로는 동일하게 동작한다 — ARCH-06 충족 여부를 코드로 강제하는 정도만 달라진다 |
| A3 | 병렬 판단 (a)(b)를 "각자 독립된 작은 LLM 호출"로 만드는 것을 암묵적으로 전제하고 asyncio.gather 예시를 작성했다 — CONTEXT.md의 Claude's Discretion 항목("독립 호출 vs 한 호출 JSON 두 칸")은 실제로 열려 있다 | Architecture Patterns §2, Standard Stack 표 | 계획이 "한 호출에서 JSON 두 칸"을 선택하면 asyncio.gather 패턴 자체가 불필요해지고 ARCH-04("병렬 실행")의 구현 방식이 완전히 달라진다(단일 호출은 정의상 병렬이 아니므로, 이 경우 ARCH-04를 어떻게 만족시킬지 계획 단계가 별도로 정당화해야 한다) |

## Open Questions

1. **위협 시계 조건 검사의 실제 판단 방식 — LLM 호출인가 규칙 기반인가?**
   - What we know: CONTEXT.md는 "조건 검사"라고만 부르고, `threat_clocks.py`의
     `segment_descriptions`는 자연어 텍스트다(구조화된 트리거 조건 필드가 없다)
     [VERIFIED: src/gptrpg/rulebooks/threat_clocks.py:26-39, `ThreatClockContent`에
     `segment_descriptions: tuple[str, ...]` 뿐, 조건 필드 없음].
   - What's unclear: 자연어 칸 설명과 이번 턴 서사를 비교해 "조건이 맞았는가"를 판단하려면
     결국 LLM 호출이 필요해 보인다 — 그렇다면 이것도 `call_with_one_retry`로 감싸야
     하고 별도 provider/model 역할이 필요한가, 아니면 (b) 판단이 이미 그 역할을 겸하는가?
   - Recommendation: 계획 단계에서 `ThreatClockContent`에 조건 관련 필드를 추가할지
     여부를 먼저 정한다(CONTEXT.md canonical_refs가 이미 "조건 진행 최소판을 만들려면
     `ThreatClockContent`에 조건 관련 필드를 **추가**해야 한다"고 명시했다) — 이 필드
     추가는 `event_log`가 아니라 `rulebooks` 계층의 변경이므로 D-02가 막으려는
     "EVENT_SCHEMA_VERSION 상승"과는 무관하다.

2. **배경 조건 검사가 매 턴 도는가, (b)의 신호가 있을 때만 도는가?**
   - What we know: D-04의 미결정이 정확히 이 질문이다.
   - What's unclear: "매 턴 돈다"를 택하면 사실상 병렬 판단 (b) 자체가 무의미해진다(항상
     배경이 다시 판단하므로) — 반대로 "신호 있을 때만"을 택하면 (b)가 빠른 게이트
     역할을 실제로 한다.
   - Recommendation: Assumptions Log A1 참조. 계획 단계에서 확정.

## Environment Availability

이 단계는 외부 서비스·CLI 도구에 새 의존성을 만들지 않는다 — 기존 다섯 LLM 제공자
(anthropic/openai/gemini/nim/openrouter, `agents/providers/__init__.py:18-24`
[VERIFIED])와 기존 `.gptrpg/agents.json` 설정 파일 메커니즘을 그대로 재사용한다. 새 역할이
추가되면 운영자가 `gptrpg agents select`로 그 역할의 제공자·모델을 한 번 더 골라야 한다는
점만 운영 절차에 추가된다 — 코드가 아니라 운영 문서 갱신 대상.

## Validation Architecture

`.planning/config.json`에 `workflow.nyquist_validation` 키가 없으므로 기본값(활성)을
따른다[VERIFIED: /home/alpha-pi/GPTRPG/.planning/config.json 전체 — `workflow` 아래
`_auto_chain_active`만 있고 `nyquist_validation` 키 없음].

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1+ / pytest-asyncio 1.4.0+ (`asyncio_mode = "auto"`) [VERIFIED: /home/alpha-pi/GPTRPG/pyproject.toml:46-47,53] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`) [VERIFIED: /home/alpha-pi/GPTRPG/pyproject.toml:51-52] |
| Quick run command | `uv run pytest tests/test_master_gm.py tests/test_action_classifier.py tests/test_session_actor_auto_advance.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|-------------|
| ARCH-02 | 서술 프롬프트의 `system`에 페르소나 지시문·시나리오 원문이 없다 | unit | `pytest tests/test_prompt_assembly_scenario.py -x` (기존 파일 확장) | ✅ 기존, 확장 필요 |
| ARCH-02 | `narrate()`가 구조화된 사실 묶음을 받는다 | unit | `pytest tests/test_master_gm.py -x` (기존, 시그니처 변경 반영 필요) | ✅ 기존, 확장 필요 |
| ARCH-03 | 배경 시계 조건 검사 산출물이 사건으로 기록되고 재생 시 같은 상태 | integration | `pytest tests/test_web_actions.py -x` (기존, `_illustrate_scene` 자매 테스트 패턴 추가) | ✅ 기존, 확장 필요 |
| ARCH-03 | CLI 경로에서도 배경 조건 검사 산출물이 유실 없이 기록됨(Pitfall 1 회귀 방지) | integration | `pytest tests/test_turn_flow_failure.py -x` (기존, 새 케이스 추가) | ✅ 기존, 확장 필요 |
| ARCH-04 | 병렬 판단 두 조각이 항상 함께 호출됨(조건부 병렬화 없음) — 코드 리뷰 성격이 강하나, 한쪽만 호출되는 회귀를 잡는 테스트 | unit | 신규 `tests/test_parallel_judgment.py` | ❌ Wave 0 |
| ARCH-05 | 한쪽 판단이 타임아웃/실패해도 턴이 끝까지 진행됨 | unit | 신규, `FakeProvider`가 예외를 던지도록 설정해 `call_with_one_retry` 경로 확인(`tests/test_agents_retry.py` 패턴 재사용) | ❌ Wave 0 (기존 패턴 확장) |
| ARCH-06 | 각 역할이 정해진 문맥 칸만 받고 상한을 넘지 않음 | unit | 신규 `tests/test_agent_context_caps.py` 또는 기존 `test_master_gm.py`/`test_action_classifier.py`에 케이스 추가 | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_master_gm.py tests/test_action_classifier.py tests/test_session_actor_auto_advance.py tests/test_session_actor.py -x`
- **Per wave merge:** `uv run pytest` (전체)
- **Phase gate:** 전체 통과 + `import-linter`(`.importlinter` 계약, 새 코드가 레이어를 어기지 않는지) — 기존 CI가 이미 이 검사를 갖고 있을 가능성이 높다(계획 단계에서 CI 설정 확인).

### Wave 0 Gaps

- [ ] `tests/test_parallel_judgment.py` — ARCH-04(정적 병렬 호출) 회귀 방지
- [ ] `tests/test_agent_context_caps.py` — ARCH-06(역할별 상한) 회귀 방지
- [ ] `tests/test_web_actions.py`/`tests/test_turn_flow_failure.py`에 시계 조건 검사 배경
      경로 케이스 추가 — ARCH-03의 "재생하면 같은 상태" 보장
- [ ] Framework install: 불필요 — pytest/pytest-asyncio 이미 dev 의존성에 있음

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V1 Architecture | yes | 이 단계 자체가 아키텍처 경계 강화다 — `.importlinter` 계약(agents는 event_log/session_actor를 모른다)이 이미 "AI가 저장소를 직접 훑을 수 없다"는 D-66 취지를 코드로 강제한다. 새 역할도 이 경계를 벗어나지 않아야 한다 |
| V4 Access Control | no (이 단계 범위 밖) | 신원 검증(TRUST-01~06)은 Phase 8에서 이미 완료 — 이 단계가 추가하는 새 에이전트 호출은 기존 `SessionActor`의 신원 검증 경로를 그대로 통과하므로 새 접근 제어 로직이 필요 없다 |
| V5 Input Validation | yes | 병렬 판단 (a)(b)의 LLM 출력은 `action_classifier._try_parse_json_array`와 같은 강건 파싱 + 닫힌 목록/스키마 검증을 거쳐야 한다 — AI 출력을 검증 없이 사건 페이로드로 바로 흘려보내지 않는다(`UnknownMove` 패턴과 동일한 정신) |
| V6 Cryptography | no | 이 단계는 암호화 관련 변경이 없다 |
| V8 Data Protection (프로젝트 자체 정의: 지시문 유출 방지, ARCH-02) | yes | 서술 프롬프트에서 페르소나/규칙/시나리오 원문을 구조적으로 제거하는 것 자체가 이 단계의 핵심 통제다 — "유출할 것을 애초에 안 준다"는 CONTEXT.md의 표현이 정확히 V8의 최소 권한/필요 최소 노출 원칙과 일치한다 |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| 진행자 지시문·시나리오 원문 유출(세션1 실제 사고) | Information Disclosure | ARCH-02 — 서술 호출의 `system`에서 페르소나/규칙/시나리오 원문 자체를 제거(주는 것 자체를 없앰). 탈옥 방어 필터(받은 것 안에서 새는지 검사)는 Phase 10, 이 단계 범위 밖 |
| AI가 시계 칸 이동·판정 수치를 직접 결정 | Elevation of Privilege(경계 위반) | D14(절대 결정) — `condition` 트리거로 배경 작업이 `AdvanceClock`을 제출하더라도, 실제로 사건을 기록하고 상태를 바꾸는 것은 여전히 `SessionActor`/코드다. AI는 "조건이 맞았다"는 판단(닫힌 신호)만 내고, 칸 번호·상한 검사는 코드가 한다 |
| 배경 작업이 `SessionActor`를 우회해 별도로 상태를 쓰는 경로 | Tampering(단일 진실 우회) | D3(세션당 단일 쓰기 주체) — 모든 배경 산출물은 반드시 `actor.submit(...)`을 거친다. `_illustrate_scene` 패턴이 이미 이 통제를 구현한 참조 사례 |

## Sources

### Primary (HIGH confidence — 전부 이번 세션에 Read 도구로 직접 읽음)

- `src/gptrpg/agents/master_gm.py` (전체) — narrate()/chunk_sentences/스톨 워치독 구조
- `src/gptrpg/agents/prompt_assembly.py` (전체) — 캐싱 순서 규약, build_gm_prompt/build_classifier_prompt
- `src/gptrpg/agents/context.py` (전체) — TurnContext, RECENT_TURNS_LIMIT
- `src/gptrpg/agents/invoke.py` (전체) — call_with_one_retry, 타임아웃 상수
- `src/gptrpg/agents/config.py` (전체) — AGENT_ROLES, load_config/resolve_provider
- `src/gptrpg/agents/action_classifier.py` (전체) — 강건 JSON 파싱, 닫힌 목록 패턴
- `src/gptrpg/agents/envelope.py`, `src/gptrpg/agents/providers/base.py`, `src/gptrpg/agents/providers/__init__.py` — Provider 프로토콜, 다섯 제공자
- `src/gptrpg/cli/turn_flow.py` (전체) — CLI 턴 흐름, 삽입 지점 정확한 줄 번호
- `src/gptrpg/web/routes_actions.py` (전체) — 웹 턴 흐름, `_illustrate_scene` 배경 패턴
- `src/gptrpg/turn/context.py` (전체) — build_turn_context, CLI/웹 공유 층
- `src/gptrpg/event_log/schema.py` (전체) — ClockAdvanced, EVENT_SCHEMA_VERSION=5
- `src/gptrpg/rules_core/reducer.py` (전체) — clock_advanced 리듀서 분기
- `src/gptrpg/session_actor/actor.py` (전체) — AdvanceClock, _prepare_clock, _VALID_CLOCK_TRIGGERS
- `src/gptrpg/rulebooks/threat_clocks.py` (전체) — ThreatClockContent, segment_descriptions
- `src/gptrpg/cli/main.py` (grep + 발췌) — `submit clock --trigger`, `asyncio.run(run_turn(...))`
- `tests/test_session_actor_auto_advance.py` (발췌) — trigger="condition" 실제 통과 테스트
- `.importlinter` (전체) — 레이어 계약 4건
- `pyproject.toml` (발췌) — 의존성, pytest 설정
- `.planning/phases/09-agent-architecture/09-CONTEXT.md` (전체)
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/PROJECT.md` (전체)

### Secondary (MEDIUM confidence)

- 없음 — 이번 리서치는 외부 문서 조회가 필요 없었다(순수 인프로세스 재구조화, 표준
  라이브러리만 사용).

### Tertiary (LOW confidence)

- 없음.

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — 새 패키지 없음, 전부 리포지토리에서 검증된 기존 자산
- Architecture: HIGH — 배경 실행/타임아웃/조건 트리거 세 핵심 패턴 모두 코드에서 직접 확인
- Pitfalls: HIGH — CLI 프로세스 생명주기 문제는 `cli/main.py:448`을 직접 읽어 확인한 구조적 사실
- 미결정 영역(D-04, TurnContext 분할 방식): MEDIUM — 코드가 답을 정해주지 않는 순수 설계
  판단이라 권장안을 냈으나 계획 단계 확정 필요(Assumptions Log 참조)

**Research date:** 2026-08-07
**Valid until:** 코드베이스가 안정적인 내부 프로젝트이므로 60일(다음 마일스톤 전까지)로
넉넉히 잡는다 — 단, 이 리서치가 인용한 정확한 줄 번호는 이 단계 실행 전에 다른 단계가
먼저 해당 파일을 건드리면 즉시 stale해진다. 계획 단계 착수 직전에 이 파일들의 최신 상태를
다시 한 번 대조할 것을 권장.

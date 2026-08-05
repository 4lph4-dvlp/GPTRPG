# Phase 5: 실험 실행 — 두 번, 1주 간격 - Research

**Researched:** 2026-08-03
**Domain:** (a) 기존 코드베이스의 정확한 확장 지점(시나리오 데이터 → 프롬프트 주입), (b) TRPG "위협 시계/Front" 콘텐츠 저작, (c) 실험 운영(참가자·일정·무료 모델 리스크)
**Confidence:** HIGH (코드 확장 지점) / MEDIUM (시나리오 저작 관례, OpenRouter 요금제) / 해당없음(운영 항목은 코드가 아니므로 "확인/검증"이 아니라 "절차 준비"가 산출물)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-46:** 시나리오 내용(이름·위협의 정체·그것이 원하는 것·캐스트·시계 칸 4개·파국)은 **Claude가 초안을 짓는다** — "최대한 다양한 시나리오와 플레이가 나올 수 있도록" 짓는 것이 사용자의 명시적 요청이다. 특정 톤(진지/코믹/호러) 하나로 좁히지 않고, 플레이어의 다양한 접근(전투/대화/탐색/설득 등)이 전부 말이 되도록 개방적으로 설계한다.
- **D-47:** 위협 시계가 4칸(파국)까지 도달하면 그것이 세션의 자연스러운 종료점이다. 코드로 상한선을 강제하지 않고, 파국 이후에도 즉흥으로 계속 진행하지도 않는다.
- **D-48:** 장면에 등장하는 대상(`scene_entities`)은 시나리오 전체 캐스트를 매 턴 고정 주입한다. "현재 국면에 등장한 인물만 골라 보여주는" 추적 로직은 새로 짜지 않는다.
- **후속 기술 확인:** `turn/context.py`의 `PLACEHOLDER_CLOCK_SEGMENT_COUNT = 6`은 EXP-01이 요구하는 "4칸"과 숫자가 안 맞는다 — 시나리오 데이터로 교체하는 작업에서 4로 바뀌어야 한다.
- **D-49:** 브람·나리는 그대로 유지(경험자 2명용). 선·호두 자리는 비경험자 2명이 구두 안내로 새로 만든 캐릭터 데이터로 교체한다.
- **D-50:** 비경험자용 캐릭터 만들기 구두 안내 대본은 Claude가 미리 써둔다 — `design-plan.md` §6.1의 "7가지 동작"을 던전월드 계열 캐릭터에 맞게 구체적인 질문지 형태로 만든다. 진행자가 현장에서 그대로 읽으며 진행한다.
- **D-51:** 애착 질문("당신 캐릭터 어떤 사람이에요?", MEAS-06) 대답은 진행자(관찰자)가 손으로 적는다.
- **D-52:** 세션 중 관찰 기록(몰입도 신호, 자유 텍스트 마찰 사례 등)도 손으로(종이·메모) 남긴다.
- **D-53:** 2세션 "완주 대 흐지부지"(EXP-03) 판정은 참석 인원 수 + 끝까지 있었는지를 관찰자가 주관적으로 판단한다. 엄격한 기준 시간은 사전에 정하지 않는다.
- **D-54:** 1세션 종료 후 리캡(MEAS-05)은 관찰자가 세션 직후 손으로 3~5줄 요약을 써서 메신저로 공유한다. "사건 기록을 자동 집계해 요약을 시스템이 생성"하는 아이디어는 명시적 스코프 크립으로 확인됨 — M1 백로그로 이관.
- **D-55:** 참가자는 진짜 4명(TRPG 경험자 2 + 비경험자 2)이고, 사용자 본인이 그 4명 중 한 명으로 참여한다.
- **D-56:** 사용자가 플레이어로 참여하므로, 별도 전담 관찰자 없이 사용자가 플레이하면서 틈틈이 메모를 남긴다.
- **D-57:** 세션 일정은 3~4시간 · 정확히 1주 간격 · 저녁 8시경 시작이라는 구조만 확정하고, 정확한 캘린더 날짜는 미정(참가자 모집 후 사용자가 직접 잡는다).
- **D-58:** 실행에 쓸 AI 모델은 OpenRouter의 무료 티어 모델(Nvidia Nemotron 계열)이다. D18("M0은 최상급 모델 고정")의 취지가 완전히 충족되지 않는다는 캐비어트가 붙는다. 무료 티어는 분당 요청 제한이 있을 수 있어 3~4시간 세션 도중 막힐 수 있다 — 본 세션 전 짧은 사전 점검(드라이런)을 권장한다.

### Claude's Discretion

- 시나리오 데이터의 정확한 파일 형식/위치(예: `rulebooks/moves.py`와 나란한 새 모듈 vs 다른 구조) — 룰북 파일 목차(D9/§4.2)나 시나리오 형식(D9/§4.8) 컨벤션을 참고해 계획 단계가 정한다
- `위협 시계 상태` 프롬프트 블록에 시나리오 내용을 정확히 어떤 문구로 넣을지(`_format_clock_state`/`_session_block_text` 확장 방식) — D-31("매 턴 넣는 것은 네 가지로 고정")을 어기지 않는 선에서, 기존 "위협 시계 상태" 슬롯 안에 내용을 채우는 형태가 유력
- 비경험자 캐릭터 만들기 구두 대본의 정확한 문구·순서
- 새로 만든 두 캐릭터(선·호두 자리)를 실제 코드 데이터로 옮겨 적는 시점과 방법(세션 시작 직전 수동 편집)
- 사용자가 4명 중 어느 캐릭터를 플레이할지
- 무료 모델 사전 점검(드라이런)의 정확한 절차

### Deferred Ideas (OUT OF SCOPE)

- **리캡(요약) 자동 생성 기능** — 세션 종료 시 스토리 진행 요약과 수치/인벤토리 요약을 나눠 시스템이 자동 생성하는 기능. ROADMAP·PROJECT.md가 M0 범위 밖으로 명시했고, M1 로드맵이 아직 안 쓰였으므로 M1에 넣을지는 미정 — 후보로만 남긴다.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXP-01 | 실험 준비물이 손으로 만들어져 있다 — 위협 시계 1개(4칸) / 룰북 1개(판정 종류 10개 남짓) / 캐릭터 4개 중 절반 | 룰북·캐릭터 그릇은 이미 존재함을 코드로 확인(§Reusable Assets). 새로 만들 것은 시계 콘텐츠 데이터 모듈 하나뿐 — §Architecture Patterns가 정확한 확장 지점과 Front 저작 구조를 제공 |
| EXP-02 | 참가자 4명(경험자 2+비경험자 2) 모집, 관찰만 함 | 코드 산출물 없음 — §Runtime/운영 체크리스트가 준비물 목록만 제공 |
| EXP-03 | 1세션→1주 간격→2세션 실제 진행, 완주 여부 기록 | 코드 산출물 없음. §Common Pitfalls의 OpenRouter 무료 티어 한도가 "완주"에 직접 위협이 되는 리스크로 연결됨 |
| EXP-04 | 비경험자 2명이 화면 없이 30분 안에 캐릭터 생성 | design-plan.md §6.1 "7가지 동작"을 §Architecture Patterns에서 던전월드 계열 스탯(STR/DEX/CON/INT/WIS/CHA + 체력)에 맞게 구체화 |
| MEAS-05 | 1세션 종료 리캡을 손으로 써서 2세션이 이어할 수 있다 | design-plan.md §7.3 "파티 리캡 3~5문장" 관례를 §Architecture Patterns에서 인용 |
| MEAS-06 | 캐릭터 생성 직후 애착 질문 기록 | 코드 산출물 없음 — 질문 문구만 대본에 포함 |

</phase_requirements>

## Summary

이 단계는 전형적인 "기능 구현" 단계가 아니다. `EXP-02/03`(참가자 모집·실제 세션 진행)과 `MEAS-05/06`(손으로 쓴 리캡·애착 질문 기록)은 코드가 만들 수 없는 운영 활동이고, ROADMAP·PROJECT.md·REQUIREMENTS.md Out of Scope 절이 이미 "캐릭터 만들기 화면 없음", "리캡 자동 생성 없음"을 명시적으로 못박아뒀다. 실제 코드 표면은 좁고 정확히 5개 파일에 걸쳐 있다: `turn/context.py`(시계 칸 수 6→4, 시나리오 데이터를 읽어 `TurnContext`를 채우는 지점), `agents/context.py`(`ClockState` — 지금은 칸 번호/전체 칸 수만 담는 빈 그릇), `agents/prompt_assembly.py`(`_format_clock_state`/`_session_block_text` — 캐싱 순서를 지키며 시나리오 내용을 문자열로 펼치는 지점), `rulebooks/dungeonworld_like.py`(자리표시자 `EXAMPLE_SINGLE_STAT_FOE` 교체), `web/characters_data.py`(`PLAYER_CHARACTERS`의 선·호두 값 교체).

가장 중요한 기술적 발견은 **`TurnContext`는 정확히 4칸으로 코드 수준에서 고정되어 있고(`TURN_CONTEXT_FIELD_NAMES`), `ClockState`는 지금 `clock_id`/`segment_index`/`segment_count` 세 칸뿐**이라는 것이다. 시나리오 콘텐츠(이름·위협 정체·원하는 것·시계 칸 4개의 설명·파국)를 주입할 다섯 번째 `TurnContext` 필드를 새로 만드는 방향은 이 파일이 스스로 건 잠금("칸이 정확히 넷임을 코드로도 고정한다")과 정면으로 부딪힌다. CONTEXT.md의 Claude's Discretion이 이미 옳은 방향을 짚었다 — **콘텐츠는 `ClockState` 자체를 확장해서 담아야 한다.** `ClockState`가 "위협 시계 상태"라는 네 번째 칸의 유일한 담지자이므로, 그 안에 필드를 추가하는 것은 D-31("매 턴 넣는 것은 네 가지로 고정")을 어기지 않는다. `scene_entities`(캐스트, D-48)는 이미 `TurnContext`의 첫 번째 칸이므로 새 필드가 필요 없고, `build_turn_context`에서 `EXAMPLE_SINGLE_STAT_FOE` 자리에 캐스트 `Entity` 튜플을 채우기만 하면 된다.

시나리오 콘텐츠는 `rulebooks/openquest_creatures.py`가 이미 세운 관례(룰북 본체가 아니라 룰북 옆에 나란히 두는 손으로 쓴 데이터 모듈, `Entity`/`StatEntry` 재사용)를 그대로 따르는 것이 가장 안전하다. 던전월드/Apocalypse World Front 구조(Danger + Impulse + Cast + Grim Portents + Impending Doom)와 이 프로젝트의 `design-plan.md` §5/D21 데이터 구조가 거의 1:1로 대응하므로, 저작 가이드는 새로 만들 필요 없이 그대로 재사용할 수 있다.

**운영 리스크 중 하나가 새로 발견됐다:** OpenRouter 공식 문서(`openrouter.ai/docs/api-reference/limits`, 이번 세션에 직접 확인)에 따르면 `:free` 모델은 분당 20요청은 고정이지만, **일평생 10달러 이상 결제한 적이 없는 계정은 하루 50요청**으로 묶인다(10달러 이상 결제 이력이 있으면 하루 1000요청). 세션당 플레이어 행동이 약 40개(§12.2 "실제 입력 문장 약 160개"를 두 세션·네 명으로 나누면 세션당 약 40개), 매 행동마다 분류(action_classifier) + 서사(master_gm) 최소 2회 AI 호출이 발생하므로 세션 하나만으로도 하루 80회를 넘길 수 있다. 이는 D-58이 이미 적어둔 "운영 위험" 캐비어트를 구체적인 숫자로 확인한 것이며, 드라이런/사전 점검 항목에 "결제 이력 10달러 이상 확보"를 넣을 근거가 된다.

**Primary recommendation:** 새 모듈 `src/gptrpg/rulebooks/threat_clocks.py`(가칭)에 Front 구조를 그대로 옮긴 dataclass 하나(예: `ThreatClockContent`)와 캐스트 `Entity` 튜플을 손으로 선언하고, `ClockState`에 그 내용을 담을 필드를 추가한 뒤, `build_turn_context`가 이 모듈을 읽어 `ClockState`/`scene_entities`를 채우도록 확장한다. `_format_clock_state`는 이 확장된 `ClockState`를 받아 이름·위협 정체·원하는 것·현재 칸까지의 진행 상황·다음 칸 설명을 한 텍스트 블록으로 펼치면 된다(캐싱 계층은 그대로 "세션 고정"에 남는다 — 장면이 바뀔 때만, 즉 칸이 넘어갈 때만 값이 바뀌기 때문).

## Architectural Responsibility Map

이 프로젝트는 일반적인 브라우저/SSR/API/CDN/DB 4~5계층이 아니라 자체 계층 모델(`gptrpg.web|gptrpg.cli` → `gptrpg.turn` → `gptrpg.agents` → `gptrpg.rulebooks`/`gptrpg.rules_core`/`gptrpg.event_log`/`gptrpg.session_actor`, `.importlinter`로 강제)을 쓴다. 아래 표는 이 프로젝트 고유의 계층으로 매핑했다 — 표준 웹 계층 용어를 억지로 끼워 맞추면 오히려 오배치를 유발한다.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 시나리오 콘텐츠 선언(이름/위협정체/원하는것/캐스트/칸 4개/파국) | `gptrpg.rulebooks`-인접 데이터 모듈(신규) | — | D-46·D8·D5 — 시나리오는 룰북과 독립 계층이지만 "데이터, 코드 아님" 원칙은 동일. `rules_core`(계산)에 콘텐츠가 새면 안 됨 |
| 시나리오 데이터를 매 턴 상태로 조립 | `gptrpg.turn.build_turn_context` | — | CLI·웹이 공유하는 유일한 조립 지점(04-05가 확정). 저장소(`EventStore`)를 읽을 수 있는 유일한 위치 |
| `ClockState`/`TurnContext` 그릇 확장 | `gptrpg.agents.context` | — | 그릇의 칸 정의 권한이 여기에만 있음. `event_log`/`session_actor`를 import할 수 없음(contract:3) — 콘텐츠를 여기서 저장소로 조회하면 안 됨, `build_turn_context`가 채워서 넘겨야 함 |
| 시계 상태를 프롬프트 텍스트로 렌더 | `gptrpg.agents.prompt_assembly` | — | "세션 고정" 캐싱 층 소유자. 여기 벗어나면 캐싱 계약(원가 3.7배) 깨짐 |
| 캐릭터 데이터 교체(선·호두) | `gptrpg.web.characters_data` | — | 캐릭터 그릇 선언이 존재하는 유일한 자리. `Entity`/`StatEntry` 재사용, 칸 추가 금지 |
| 캐릭터 만들기 구두 대본, 애착 질문 문구 | 운영 문서(코드 밖) | — | 화면이 없다(EXP-04). 콘텐츠 자체는 코드 계층이 아님 |
| 참가자 모집·일정·세션 진행·관찰 기록·리캡 작성 | 운영(코드 밖) | — | D-55~D-57 — 코드가 할 수 없는 영역, PROJECT.md Out of Scope가 이미 확정 |
| 위협시계 칸/실패카운터 화면 표시 | 이미 완료(Phase 4, RIG-04) — **변경 없음** | — | Phase 5는 이 표시가 읽는 숫자의 "내용"만 채운다. `frontend/src/session_view.ts`의 렌더 로직 자체는 이 단계가 손댈 필요 없음 |

## Standard Stack

이 단계는 **새 외부 패키지를 설치하지 않는다.** 기존 스택(Python 3.13 + `uv`, FastAPI, TypeScript/Vite 프런트엔드)을 그대로 쓰며, 새로 만드는 것은 전부 순수 데이터 선언(Python dataclass/상수)이다.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| (신규 의존성 없음) | — | — | 시나리오 콘텐츠는 `dataclasses`(표준 라이브러리)로만 표현 — Phase 1~4가 이미 세운 관례(`Entity`/`StatEntry`/`ClockState` 전부 `@dataclass(frozen=True)`) |

**Installation:** 해당 없음 — `pyproject.toml` 변경 불필요.

**Version verification:** 새 패키지가 없으므로 레지스트리 검증 대상 없음. 기존 런타임만 재확인: `python3 --version` → `Python 3.13.5` [VERIFIED: 이번 세션 `python3 --version` 실행], `uv --version` → `uv 0.11.28` [VERIFIED: 이번 세션 `uv --version` 실행].

## Package Legitimacy Audit

**이 단계는 외부 패키지를 설치하지 않으므로 이 게이트가 적용되지 않는다.** 새로 만드는 파일은 전부 프로젝트 내부 Python 모듈(시나리오 데이터 선언)이며, `npm`/`pip`/`uv add` 설치 명령이 계획에 들어갈 이유가 없다. 계획 단계에서 만약 새 패키지 설치가 실제로 필요해진다면(현재로선 근거 없음), 그때 이 게이트를 다시 실행해야 한다.

**Packages removed due to [SLOP] verdict:** 없음 (검사 대상 없음)
**Packages flagged as suspicious [SUS]:** 없음 (검사 대상 없음)

## Architecture Patterns

### System Architecture Diagram

```
[신규] threat_clocks.py (시나리오 데이터, Front 구조)
   이름 / 위협의 정체 / 원하는 것 / 캐스트(Entity 튜플) / 시계 칸 4개(설명·흔적) / 파국
        │
        │  (EXAMPLE_SINGLE_STAT_FOE를 대체)
        ▼
turn/context.py :: build_turn_context(store, session_id, rulebook_id, character_stats=None)
   ├─ rebuild_state(store, session_id) → GameState.clock_segment (현재 몇 칸째인지, 이미 존재)
   ├─ [신규] 시나리오 모듈에서 이름/정체/원하는 것/칸 설명/파국 읽기
   ├─ ClockState(clock_id, segment_index, segment_count=4, [신규 필드들]) 조립
   └─ scene_entities = 시나리오 캐스트 Entity 튜플 (D-48, 매 턴 고정)
        │
        ▼  TurnContext(scene_entities, character_state, clock_state, recent_turns) — 정확히 4칸, 변경 없음
        │
agents/prompt_assembly.py
   ├─ _session_block_text(ctx)  ← "세션 고정" 캐시 층
   │     _format_scene_entities(ctx.scene_entities)   (캐스트 이름+상태, 이미 존재)
   │     _format_character_state(ctx.character_state) (이미 존재)
   │     [확장] _format_clock_state(ctx.clock_state)  ← 이름·위협정체·원하는것·현재칸 설명·파국을 여기서 펼침
   └─ build_gm_prompt / build_classifier_prompt → system(영구 고정+세션 고정, cache_control) + messages(턴마다 변함)
        │
        ▼
   OpenRouter :free 모델(D-58) → action_classifier / master_gm
```

**AI가 손댈 수 없는 것:** 시계가 몇 칸째인지는 여전히 `rebuild_state`가 이벤트 로그에서 계산한 `GameState.clock_segment`가 유일한 출처다. 시나리오 모듈은 "각 칸에서 무슨 일이 일어나는가(서사 내용)"만 제공하고, "지금 몇 칸째인가(진행 여부)"는 여전히 판정 결과·실패 카운터가 결정한다 — 이 분리를 시나리오 데이터 설계가 침범하면 안 된다(RIG-02, "주사위와 판정 계산이 순수 코드로만 일어난다").

### Recommended Project Structure

```
src/gptrpg/rulebooks/
├── dungeonworld_like.py      # 기존 — EXAMPLE_SINGLE_STAT_FOE만 이 단계에서 교체
├── moves.py                   # 기존 — 변경 없음 (이미 무브 10개 완성)
├── openquest.py / openquest_creatures.py  # 기존 — 손대지 않음, 캐스트 데이터 관례의 선례
└── threat_clocks.py           # [신규, 가칭] Front 구조 시나리오 콘텐츠
    ├─ THREAT_CAST: tuple[Entity, ...]           # D-48 scene_entities로 그대로 흘러감
    ├─ THREAT_SEGMENTS: tuple[str, ...] (길이 4)  # 각 칸의 "무슨 일이 일어나나" 한두 문장
    └─ ThreatClockContent(dataclass) 또는 평범한 모듈 상수 4~5개
        (이름, 위협의 정체, 원하는 것, 파국 — 전부 D21 데이터 구조 그대로)
```

**파일 위치 근거:** `rulebooks/openquest_creatures.py`가 이미 "룰북 본체가 아니지만 룰북 옆에 두는 손으로 쓴 콘텐츠 데이터 모듈" 선례를 세웠다 [VERIFIED: src/gptrpg/rulebooks/openquest_creatures.py:1-40, 도크스트링 "OpenQuest System Resource Document(CC BY 4.0)의 크리처 두 종을 실제 수치 그대로 옮긴다"]. 시나리오는 `rulebook_id`("dungeonworld_like")에 종속되지 않는 독립 계층(D8)이지만, 지금 M0에는 룰북이 사실상 하나뿐이므로 같은 디렉터리에 나란히 두는 것이 가장 단순하다. 계획 단계가 이 파일명/디렉터리를 확정한다(discretion 항목).

### Pattern 1: `ClockState` 확장 — TurnContext 4칸 잠금을 지키며 콘텐츠 주입

**What:** `TurnContext`는 정확히 4개 필드로 코드 수준에서 잠겨 있다.

```python
# Source: src/gptrpg/agents/context.py:41-57 (이번 세션에 직접 읽음)
@dataclass(frozen=True)
class TurnContext:
    """매 턴 에이전트에게 넘기는 것 딱 네 가지 — 그 이상도 이하도 아니다."""

    scene_entities: tuple[Entity, ...]
    character_state: tuple[StatEntry, ...]
    clock_state: ClockState
    recent_turns: tuple[str, ...]
    ...

# 칸이 정확히 넷임을 코드로도 고정한다 — `entities.py`의 `ENTITY_FIELD_NAMES`
# 관례를 그대로 따른다.
TURN_CONTEXT_FIELD_NAMES = frozenset(f.name for f in fields(TurnContext))
```

같은 파일의 `ClockState`는 지금 세 필드뿐이다:

```python
# Source: src/gptrpg/agents/context.py:32-38 (이번 세션에 직접 읽음)
@dataclass(frozen=True)
class ClockState:
    """위협 시계 상태 한 조각 — 몇 번째 칸인지와 전체 칸 수."""

    clock_id: str
    segment_index: int
    segment_count: int
```

**When to use:** 시나리오 콘텐츠(이름·위협 정체·원하는 것·칸 설명·파국)를 주입해야 하는 지금 이 단계에서.

**권장 확장 방향:** `TurnContext`에 5번째 필드를 추가하지 말고(그러면 위 잠금 주석의 취지를 정면으로 깨고 `TURN_CONTEXT_FIELD_NAMES`가 코드 리뷰에서 즉시 눈에 띄는 불일치를 낳는다), `ClockState`에 필드를 추가한다. `ClockState`가 "위협 시계 상태"라는 네 칸 중 하나의 유일한 담지자이므로, 그 안을 넓히는 것은 D-31의 "매 턴 넣는 것은 네 가지" 규칙을 어기지 않는다 — CONTEXT.md의 discretion 절이 이미 이 방향을 "유력"하다고 짚어뒀다. 예:

```python
@dataclass(frozen=True)
class ClockState:
    clock_id: str
    segment_index: int
    segment_count: int
    # [신규] 시나리오 콘텐츠 — 전부 str/tuple[str, ...]로 충분, 계산에 안 쓰임
    threat_name: str = ""
    threat_identity: str = ""
    threat_wants: str = ""
    segment_descriptions: tuple[str, ...] = ()
    catastrophe_text: str = ""
```

기본값(빈 문자열/빈 튜플)을 주면 `EXAMPLE_SINGLE_STAT_FOE` 자리표시자를 쓰던 기존 CLI 트레이서 테스트(`tests/test_turn_tracer.py`)가 이 필드들을 몰라도 깨지지 않는다.

**Example — `_format_clock_state` 확장 지점:**
```python
# Source: src/gptrpg/agents/prompt_assembly.py:51-52 (이번 세션에 직접 읽음, 현재 구현)
def _format_clock_state(clock) -> str:
    return f"{clock.clock_id}: {clock.segment_index}/{clock.segment_count}"
```
이 함수가 유일한 확장 지점이다 — `_session_block_text`가 이 함수의 반환값을 그대로 "세션 고정" 캐시 블록에 넣는다(`prompt_assembly.py:61-66`, 이번 세션에 직접 읽음: `f"위협 시계: {_format_clock_state(ctx.clock_state)}"`). 새 구현은 이름·위협 정체·원하는 것·**현재 칸까지 진행된 것 + 다음 칸 설명**(파국까지 전부 미리 보여줄지, 다음 칸만 보여줄지는 계획 단계 판단 — 다음 칸까지만 보여주는 쪽이 "AI가 결말을 미리 다 알고 서사가 뻔해지는" 위험을 줄인다)을 한 텍스트 블록으로 조립하면 된다.

### Pattern 2: `scene_entities`에 캐스트 고정 주입 (D-48)

**What:** `build_turn_context`가 지금 `scene_entities = (EXAMPLE_SINGLE_STAT_FOE,)`로 하드코딩되어 있다.

```python
# Source: src/gptrpg/turn/context.py:79 (이번 세션에 직접 읽음)
scene_entities = (EXAMPLE_SINGLE_STAT_FOE,)
```

**When to use:** 시나리오 캐스트를 매 턴 고정 주입할 때(D-48 — 국면별 필터링 로직은 만들지 않는다).

**Example:** `EXAMPLE_SINGLE_STAT_FOE` 자리에 새 시나리오 모듈의 `THREAT_CAST` 튜플을 그대로 대입한다. `Entity`는 `stats: tuple[StatEntry, ...] = ()`가 기본값이므로[VERIFIED: src/gptrpg/rules_core/entities.py:64-77, `stats: tuple[StatEntry, ...] = ()`], 전투 능력이 없는 NPC(대화·정보 제공용)는 `stats=()`로 선언해도 유효하다 — `InvalidEntity`는 `entity_id`/`display_name`/`rulebook_id`가 빈 문자열일 때만 던져진다[VERIFIED: src/gptrpg/rules_core/entities.py:79-90].

### Anti-Patterns to Avoid

- **`TurnContext`에 5번째 필드 추가:** `TURN_CONTEXT_FIELD_NAMES`가 "정확히 넷"이라는 잠금을 코드로 표명한다[VERIFIED: src/gptrpg/agents/context.py:55-57, `# 칸이 정확히 넷임을 코드로도 고정한다 ... TURN_CONTEXT_FIELD_NAMES = frozenset(f.name for f in fields(TurnContext))`]. 콘텐츠는 `ClockState` 안으로 넣는다(Pattern 1).
- **`clock_advances`/`fails_since_clock`을 시나리오 콘텐츠와 함께 프롬프트에 흘려보내기:** `build_turn_context`의 도크스트링이 이미 명시적으로 금지한다[VERIFIED: src/gptrpg/turn/context.py:57-61, "시계 정보는 「지금 몇 번째 칸인가」까지만 넣는다 ... 둘 다 「AI가 봐주고 있는가」를 사후에 재는 관측 지표이고, AI가 그 지표를 보면 지표를 만족시키는 쪽으로 서사와 제안을 바꿔서 계측 자체가 무의미해진다"]. 시나리오 콘텐츠를 추가할 때 이 경계를 실수로 넘지 않는다.
- **`Entity`/`StatEntry`에 칸 추가:** `ENTITY_FIELD_NAMES`/`STAT_ENTRY_FIELD_NAMES`가 같은 방식으로 잠겨 있다[VERIFIED: src/gptrpg/rules_core/entities.py:93-96]. 캐스트 NPC의 "역할"이나 "장면 태그" 같은 메타데이터가 필요하면 `characters_data.py`의 `CHARACTER_ARCHETYPES` 관례(딕셔너리를 `Entity` 밖에 따로 둔다)를 그대로 따른다.
- **위협 시계에 코드 상한선 강제:** D-47이 명시적으로 거부했다 — 4칸(파국) 도달은 관찰자가 판단하는 자연스러운 종료점이지, `AdvanceClock`을 막는 코드 조건이 아니다.
- **국면별 캐스트 필터링 로직 신설:** D-48이 명시적으로 거부했다 — "현재 등장한 인물만" 추적하는 로직을 만들지 않는다.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| 위협 시계 콘텐츠 구조 | 자체 스키마 새로 설계 | Front 구조(Danger+Impulse+Cast+Grim Portents+Impending Doom) — 이미 `design-plan.md` §5/D21이 확정한 데이터 구조와 1:1 대응 | D9가 M0 포맷으로 이미 "전선/시계(Fronts)"를 지정했다. 새 스키마를 설계하면 D9와 어긋난다 |
| 캐릭터 만들기 대본 구조 | 자체 질문 흐름 새로 설계 | design-plan.md §6.1의 "7가지 동작"(목록 하나 고르기/여러 개 고르기/숫자 나눠 담기/정해진 숫자 배치/주사위 굴려 채우기/자유롭게 쓰기/자동 계산) | 어떤 룰북이든 이 7가지 조합으로 표현된다는 것이 이미 검증된 설계 전제(D22) — 던전월드 계열 스탯(STR/DEX/CON/INT/WIS/CHA)에 맞게 구체화만 하면 됨 |
| 리캡(요약) 형식 | 자동 요약 로직 | 손으로 3~5문장(design-plan.md §7.3 "파티 리캡") | D-54로 명시적으로 스코프 크립 확인·M1 이관됨. 이 단계는 대본/템플릿 한 장이면 충분 |
| 시계 진행 로직 | 새 진행 규칙 | 기존 `SessionActor`의 실패 카운터 자동 진행(Phase 4에서 이미 완성, `AUTO_ADVANCE_FAILURE_THRESHOLD=3`) | RIG-04가 이미 구현·검증됨. 시나리오 데이터는 "칸에서 무슨 일이 일어나는가"만 제공하고 "언제 넘어가는가"는 손대지 않는다 |

**Key insight:** 이 단계에서 "직접 만들어야 하는 것"은 콘텐츠(글)뿐이지 메커니즘이 아니다. 메커니즘(시계 진행 규칙, 판정, 이벤트 기록, 캐릭터 그릇)은 Phase 1~4가 전부 완성해뒀다.

## Common Pitfalls

### Pitfall 1: 프롬프트 캐싱 순서를 깨는 콘텐츠 주입

**What goes wrong:** `_format_clock_state`를 확장하며 세션마다 바뀌지 않는 척하지만 실은 매 API 호출마다 문자열이 미세하게 달라지는 값(예: 타임스탬프, 세션 ID, 정확한 남은 시간 계산)을 섞어 넣으면 그 뒤로 캐시가 매번 깨진다.
**Why it happens:** "위협 시계 상태"에 콘텐츠를 추가하다 보면 "지금 몇 분 지났다" 같은 부가 정보를 넣고 싶어지는 유혹이 생긴다.
**How to avoid:** `_session_block_text`/`_format_clock_state`에 들어가는 모든 값은 **장면(칸)이 바뀔 때만** 바뀌어야 한다는 규칙을 지킨다[VERIFIED: src/gptrpg/agents/prompt_assembly.py:1-10, 파일 도크스트링 "시각·플레이어 표시 이름·세션 식별자·추적 번호처럼 호출마다 달라지는 값은 `system` 안에 한 글자도 넣지 않는다 — 넣는 순간 그 뒤로는 캐시가 매번 깨진다"].
**Warning signs:** 같은 칸에서 두 번 연속 호출했는데 시스템 프롬프트 텍스트가 한 글자라도 다르면 캐싱이 깨진 것이다.

### Pitfall 2: OpenRouter 무료 티어 일일 한도가 세션 하나로 소진됨

**What goes wrong:** 3~4시간 세션 도중 429(Too Many Requests)를 맞아 세션이 중단된다.
**Why it happens:** OpenRouter 공식 문서에 따르면 `:free` 모델은 분당 20요청은 공통이지만, **평생 결제 이력이 10달러 미만인 계정은 하루 50요청**으로 묶인다(10달러 이상이면 하루 1000요청)[CITED: openrouter.ai/docs/api-reference/limits, 이번 세션에 직접 확인]. 세션당 플레이어 행동이 4명 기준 약 40개(§12.2 "실제 입력 문장 약 160개"를 두 세션·네 명으로 나눈 값), 행동 하나당 최소 2회 AI 호출(분류+서사)이 나가므로 **세션 하나만으로 하루 80회를 쉽게 넘는다** — 50요청 한도라면 세션이 30분도 안 돼 막힐 수 있다.
**How to avoid:** 첫 세션 전에 OpenRouter 계정에 10달러를 결제해 하루 1000요청 한도로 올려둔다(사용량 자체는 0원 모델만 쓰므로 실제 소모되지 않고, 결제 이력만 확보하면 한도가 영구히 완화된다는 것이 문서의 요지 — "평생 결제 이력" 기준). 이 확인 절차를 D-58이 이미 요청한 "본 세션 전 짧은 사전 점검(드라이런)"의 항목으로 넣는다.
**Warning signs:** 드라이런 중 429 응답을 한 번이라도 받으면, 실제 세션 전에 결제 이력부터 확인한다.

### Pitfall 3: Nemotron 추론형 응답·스트림 정지 (Phase 3 실측 이력)

**What goes wrong:** 분류 응답이 `<think>`/코드펜스로 감싸져 파싱이 실패하거나, 서사 스트림이 응답 없이 멈춘다.
**Why it happens:** Phase 3 실측(03-UAT.md)에서 NIM Nemotron 계열 모델이 추론형(`<think>`) 응답을 낸 사례가 실제로 있었고[VERIFIED: .planning/phases/03-ai/03-UAT.md:30-33, "추론형 모델(NIM Nemotron)의 <think>/코드펜스로 감싼 JSON 응답이 파싱 안 되던 문제를 강건 파서로 수정"(03-04 deviation 인용)], 실제 22분 무한 정지가 재현된 적도 있다[VERIFIED: .planning/phases/03-ai/03-UAT.md:122, "narrate()에 90초 스트림 정지 워치독(_drain_with_stall_timeout) 추가 — 실제 ~22분 터미널 행 재현됨"].
**How to avoid:** 이미 코드로 수정됐다(강건 파서 + 90초 워치독) — 이 단계가 새로 만들 것은 없다. 다만 **90초 워치독의 "실제 네트워크 정지 상황에서의 재발동"은 03-UAT에서 검증이 스킵된 채 남아있다**[VERIFIED: .planning/phases/03-ai/03-UAT.md:25-28, "3. NIM 스트림 90초 정지 워치독 실제 발동 확인" 항목 status: skipped, "사용자가 잔여 위험으로 받아들이기로 결정(WINDOWS.md id 4, waived)"] — 실제 참가자 4명 앞에서 처음 실전 검증되는 셈이다. 드라이런에 "의도적으로 네트워크를 잠깐 끊거나 느리게 만들어 워치독이 90초 안에 실패로 낙하하고 이미 나온 문장이 보존되는지"를 확인하는 항목을 넣을 가치가 있다.
**Warning signs:** 서사가 스트리밍 도중 멈춘 채 90초 넘게 아무 반응이 없으면 워치독이 아직 발동 전이므로, 그 이상은 기다리지 말고 재시도 안내를 준비해둔다.

### Pitfall 4: 시나리오 캐스트의 HP/상태가 기계적으로 소모되지 않는다

**What goes wrong:** 저작자가 "폐광의 존재"에게 체력 5를 주고, 판정으로 피해를 입히면 자동으로 줄어들 거라 가정한다.
**Why it happens:** `scene_entities`의 `Entity.stats`는 프롬프트에 보여주기 위한 값일 뿐 — `rules_core/reducer.py`, `session_actor/*.py` 어디에도 `scene_entities`나 적/NPC `StatEntry.current`를 감소시키는 코드가 없다[VERIFIED: `grep -n "scene_entities|entity_id|StatEntry|depleted" src/gptrpg/rules_core/reducer.py`가 이번 세션에 아무 결과도 반환하지 않음]. 캐릭터(플레이어) 체력만 게임 상태에 남고, 적/NPC 상태는 AI가 서사로 일관되게 "기억"해야 한다.
**How to avoid:** 시나리오 저작 시 "적의 체력이 자동으로 깎인다"를 전제하지 않는다. 위협 시계의 4칸 자체가 진행 상태를 담는 유일한 기계적 추적 장치라는 것을 인지하고, 캐스트 NPC의 상태 변화(다쳤다/사라졌다 등)는 시계 칸 설명(흔적)이나 `recent_turns`(최근 10턴)에 기대야 한다 — 이는 3~4시간 세션에서 오래된 사건이 밀려나갈 수 있다는 뜻이므로, 저작 시 "칸이 넘어갈 때 세상에 남는 흔적"(D21 데이터 구조의 필드)에 그 사실을 명시적으로 적어두는 것이 사실상 유일한 장기 기억 장치다.
**Warning signs:** 세션 중 "아까 그 적 체력이 왜 그대로냐"는 질문이 나오면 이 한계를 관찰자가 미리 알고 있어야 한다.

## Code Examples

### `build_turn_context` 현재 시그니처 (변경 대상)
```python
# Source: src/gptrpg/turn/context.py:29-45 (이번 세션에 직접 읽음)
def build_turn_context(
    store: EventStore,
    session_id: str,
    rulebook_id: str,
    *,
    character_stats: tuple[StatEntry, ...] | None = None,
) -> TurnContext:
    ...
    state = rebuild_state(store, session_id)
    ...
    clock_state = ClockState(
        clock_id="threat",
        segment_index=state.clock_segment,
        segment_count=PLACEHOLDER_CLOCK_SEGMENT_COUNT,   # 6 → 4로, 그리고 시나리오 필드 추가
    )
    scene_entities = (EXAMPLE_SINGLE_STAT_FOE,)          # → 시나리오 캐스트 튜플로 교체
```
CLI(`cli/turn_flow.py:185`)와 웹(`web/routes_actions.py`) 양쪽이 이 함수 하나를 호출하므로[VERIFIED: cli/turn_flow.py:36,99,185에서 `from gptrpg.turn.context import build_turn_context` / `_build_turn_context = build_turn_context` / `ctx = _build_turn_context(store, args.session, args.rulebook)`], 여기 한 곳만 고치면 두 경로 모두에 반영된다 — 이는 CONTEXT.md의 서술과 정확히 일치한다.

### `PLACEHOLDER_CLOCK_SEGMENT_COUNT`는 이미 한 곳으로 모여있다
```python
# Source: src/gptrpg/turn/context.py:17 (이번 세션에 직접 읽음)
PLACEHOLDER_CLOCK_SEGMENT_COUNT = 6
```
04-05가 세 군데 중복 선언(`cli/turn_flow.py`, `web/routes_events.py`, 자기 자신)을 이미 한 곳으로 모았다[VERIFIED: .planning/phases/04-experiment-tool/04-05-SUMMARY.md, "`PLACEHOLDER_CLOCK_SEGMENT_COUNT` collapsed from three separate declarations ... into `gptrpg.turn.context`"]. `web/routes_events.py`가 이 상수를 `GameStateView.clock_segment_count`로 화면에 그대로 노출하므로[VERIFIED: src/gptrpg/web/routes_events.py:25,88, `from gptrpg.turn.context import PLACEHOLDER_CLOCK_SEGMENT_COUNT` / `clock_segment_count=PLACEHOLDER_CLOCK_SEGMENT_COUNT`], **이 값을 6에서 4로 바꾸는 것만으로 프런트엔드 화면("위협 시계 N/6" 표시)도 자동으로 "N/4"가 된다** — `frontend/src/session_view.ts`를 별도로 고칠 필요가 없다.

### 캐스트 NPC 선언 관례 (재사용할 선례)
```python
# Source: src/gptrpg/rulebooks/openquest_creatures.py:17-30 (이번 세션에 직접 읽음)
OPENQUEST_GOBLIN = Entity(
    entity_id="openquest.goblin",
    display_name="Goblin",
    rulebook_id=OPENQUEST_ID,
    stats=(
        StatEntry(name="STR", current=10),
        ...
        StatEntry(name="Hit Points", current=9, max=9,
                  depleted_effect_ref="openquest.hit_points_depleted"),
    ),
)
```
새 시나리오 캐스트도 이 형태(`Entity` + `StatEntry` 튜플, 전투 능력 없는 NPC는 `stats=()`)를 그대로 따르면 된다.

## State of the Art

이 단계는 오래된/새로운 접근법 비교가 의미 있는 영역이 아니다(외부 라이브러리 마이그레이션이 없음). 유일하게 시간에 따라 바뀔 수 있는 것은 OpenRouter의 요금제/한도 정책이다 — 아래는 이번 세션(2026-08-03)에 확인한 스냅샷이며, 실제 세션 직전에 재확인할 가치가 있다.

| 확인 시점 | 항목 | 값 |
|---|---|---|
| 2026-08-03 | `:free` 모델 분당 한도 | 20 RPM (결제 이력 무관, 고정) |
| 2026-08-03 | `:free` 모델 일일 한도 (평생 결제 <$10) | 50 RPD |
| 2026-08-03 | `:free` 모델 일일 한도 (평생 결제 ≥$10) | 1000 RPD |

**Deprecated/outdated:** 해당 없음.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 세션당 AI 호출량이 "행동당 최소 2회(분류+서사)"라는 계산 근거로 "하루 80회 초과" 리스크를 추정했다 — 재시도(`call_with_one_retry`)나 확인 거절로 인한 재분류까지 더하면 실제로는 더 많을 수 있다 | Common Pitfalls #2 | 실제 호출량이 이 추정보다 많으면 50 RPD 한도는 훨씬 더 빨리 소진된다 — 사전 결제 확보의 필요성이 더 커질 뿐, 방향은 안 바뀐다 |
| A2 | `ClockState`를 확장하고 `TurnContext`는 그대로 두는 것이 D-31을 지키는 유일한 설계라고 결론지었다 — CONTEXT.md의 discretion 문구("유력")를 근거 삼았지만, 계획 단계가 실제로 이 방향을 채택할지는 아직 확정이 아니다 | Architecture Patterns, Pattern 1 | 계획 단계가 다른 구조(예: `ClockState`를 그대로 두고 `_session_block_text`가 별도 모듈을 직접 import해 텍스트를 조립)를 택해도 D-31을 어기지 않을 수 있다 — 이 경우 Pattern 1의 구체적 필드 목록은 참고용으로만 쓰인다 |
| A3 | Front(Danger+Impulse+Cast+Grim Portents+Impending Doom) 저작 가이드 요약은 WebSearch 결과(공식 SRD 사이트 포함, 다만 단일 재확인 교차검증은 안 거침)에서 왔다 | Common Pitfalls 상단 Summary, Don't Hand-Roll | 저작 세부 관례(칸 개수별 권장치 등)가 실제 공식 문서와 미세하게 다를 수 있다 — 다만 이 프로젝트의 D21/§5가 이미 "4~6칸" 등 자체 규격을 확정해뒀으므로 영향은 제한적이다 |
| A4 | OpenRouter "평생 결제 이력 10달러 이상 시 하루 1000요청"이 실제로 D-58의 "무료 모델밖에 못 쓴다"는 예산 제약과 충돌하지 않는다고 가정했다 — $10 일회성 결제 후 사용량 자체는 계속 무료 모델(0원)만 쓰면 된다는 전제 | Common Pitfalls #2 | 사용자가 정말 $10조차 지출할 수 없다면 이 완화책은 쓸 수 없고, 하루 50요청 한도 안에서 세션을 여러 날에 걸쳐 쪼개거나 유료 모델로 전환하는 대안이 필요해진다 — 계획/실행 전 사용자 확인 필요 |

## Open Questions

1. **`ClockState`에 콘텐츠 필드를 몇 개, 어떤 이름으로 추가할지**
   - What we know: D21 데이터 구조(이름/분량/위협의 정체/원하는 것/등장인물/시계 칸별 순번+무슨 일이 일어나나+상태+진행조건+흔적/파국/시작 칸)가 원 소스다.
   - What's unclear: 이 전체를 다 `ClockState`에 넣을지, 프롬프트에 실제로 필요한 부분집합만 넣을지(예: "진행 조건"·"상태(대기/진행됨/무효화됨)"는 애초에 코드가 자동으로 관리하는 `segment_index`로 이미 표현되므로 별도 필드가 필요 없을 수 있다).
   - Recommendation: 계획 단계에서 "이미 `segment_index`가 대신하는 필드"를 제외하고 최소 집합(이름/정체/원하는것/각 칸 한 줄 설명 4개/파국)만 추가하는 것을 권장 — 최소화가 프롬프트 토큰 비용(D-58 무료 모델 제약)에도 유리하다.

2. **캐스트 캐릭터 4개 중 실제로 "손으로 준비"해야 하는 절반이 무엇을 의미하는지**
   - What we know: EXP-01은 "캐릭터 4개 중 절반"이 손으로 준비되어 있으면 된다고 적혀 있고, D-49는 브람·나리 유지·선·호두 교체를 확정했다.
   - What's unclear: "절반"이 정확히 "선·호두 2개"를 가리키는지(가장 자연스러운 해석), 아니면 "4개 모두 재검토"의 다른 의미인지.
   - Recommendation: D-49가 이미 "선·호두만 교체"로 명시적으로 답했으므로 이 해석을 그대로 채택 — 계획 단계에서 재논의 불필요.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | 시나리오 데이터 모듈 작성·테스트 | ✓ | 3.13.5 [VERIFIED: 이번 세션 `python3 --version`] | — |
| uv | 의존성/테스트 실행 | ✓ | 0.11.28 [VERIFIED: 이번 세션 `uv --version`] | — |
| Node/npm | 프런트엔드(변경 없음이지만 회귀 확인용) | ✓ | node v22.23.1, npm 12.0.1 [VERIFIED: 이번 세션 `node --version`/`npm --version`] | — |
| OpenRouter API 키 + `.gptrpg/agents.json` 설정 | 드라이런·실제 세션 두 번 모두 | 확인 불가(로컬 `.env.local`은 이번 세션에서 열람 권한 없음) | — | 세션 시작 전 `agents select`/`agents show`(Phase 3에서 완성된 CLI)로 OpenRouter 무료 모델이 실제로 선택돼 있는지 사람이 직접 확인 |

**Missing dependencies with no fallback:** 없음.
**Missing dependencies with fallback:** OpenRouter API 키 상태 확인 — 코드로 자동 검증하는 대신, 드라이런 체크리스트에 "agents show로 provider=openrouter, 무료 모델 id 확인"을 사람이 직접 하는 항목으로 넣는다.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥9.1.1 + pytest-asyncio ≥1.4.0 [VERIFIED: pyproject.toml:31-32] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_turn_tracer.py tests/test_web_actions.py -q` |
| Full suite command | `uv run pytest -q` (Phase 4 종료 시점 402개 테스트 전체 통과 확인됨) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXP-01 (시계 칸 수 4, 캐스트 주입) | `PLACEHOLDER_CLOCK_SEGMENT_COUNT == 4`, `build_turn_context`가 시나리오 캐스트를 `scene_entities`로 돌려줌 | unit | `uv run pytest tests/test_turn_tracer.py -q` (기존 파일 확장) | ✅ 기존 파일 확장 — 신규 assert만 추가 |
| EXP-01 (룰북/캐릭터 그릇) | 이미 충족(코드 변경 없음) | — | 해당 없음 | 해당 없음 |
| EXP-01 (프롬프트에 시나리오 내용 실제로 들어감) | `_format_clock_state`/`_session_block_text` 출력에 시나리오 이름·정체가 포함됨, "세션 고정" 캐시 블록이 같은 칸에서 두 번 호출해도 byte-identical | unit | 신규 `tests/test_prompt_assembly_scenario.py` (가칭) | ❌ Wave 0에서 신설 필요 |
| EXP-04 (캐릭터 만들기 대본) | 코드 산출물 없음 — 대본 문서 자체가 산출물 | manual-only | — | 자동화 불가, 대본을 사람이 직접 실행하는 방식으로만 검증 |
| MEAS-05/06 (리캡·애착 질문) | 코드 산출물 없음 | manual-only | — | 자동화 불가 |
| EXP-02/03 (참가자·일정·완주) | 코드 산출물 없음 | manual-only | — | 자동화 불가, 관찰 기록이 유일한 "검증" |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_turn_tracer.py tests/test_web_actions.py -q` (변경 파일 관련 테스트만)
- **Per wave merge:** `uv run pytest -q` (전체 402개+ 테스트)
- **Phase gate:** 실제 두 세션이 코드가 아니라 운영 활동이므로, "Full suite green"은 **코드 변경분에 대해서만** 게이트다 — EXP-02/03/04, MEAS-05/06는 세션 자체가 게이트(사람이 직접 확인)

### Wave 0 Gaps
- [ ] `tests/test_prompt_assembly_scenario.py`(가칭) — 시나리오 콘텐츠가 실제로 프롬프트 텍스트에 반영되고 캐싱 불변성(같은 칸에서 두 번 호출 시 byte-identical)이 깨지지 않는지 확인. `tests/test_turn_tracer.py:160`의 기존 패턴(`test_classifier_system_prompt_is_byte_identical_across_calls_with_different_text`)[VERIFIED: tests/test_turn_tracer.py, 함수명 확인]을 그대로 재사용 가능
- [ ] `tests/test_turn_tracer.py` 확장 — `PLACEHOLDER_CLOCK_SEGMENT_COUNT`가 4로 바뀐 뒤에도 기존 트레이서 테스트가 여전히 통과하는지(칸 수 하드코딩 여부 확인)
- Framework install: 불필요 — 이미 설치됨

## Security Domain

`security_enforcement` 설정이 `.planning/config.json`에 없으므로 기본값(활성)을 따른다. 다만 이 단계는 **새로운 사용자 입력 경로나 신뢰 경계를 추가하지 않는다** — 시나리오 데이터는 Claude가 직접 작성하는 정적 콘텐츠이고, 캐릭터 만들기 구두 대본은 코드가 아니다. 아래는 그럼에도 점검할 가치가 있는 항목이다.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 이 단계는 인증 경로를 만들지 않음 |
| V3 Session Management | no | 세션 식별자 검증(`validate_session_id`)은 Phase 4에서 이미 완성, 변경 없음 |
| V4 Access Control | no | 해당 없음 |
| V5 Input Validation | 부분적 | 시나리오 데이터 자체는 정적 상수라 "입력"이 아니지만, `ClockState`에 새 `str`/`tuple[str, ...]` 필드를 추가할 때 빈 문자열/빈 튜플을 프롬프트에 그대로 흘려보내면 `_format_clock_state`가 이상한 문자열("위협 시계: : 1/4")을 만들 수 있다 — 기본값과 실제 필드 채움 사이의 불일치를 막는 방어적 처리(빈 값일 때 자리표시자 문구로 대체) 권장 |
| V6 Cryptography | no | 해당 없음 |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 시나리오 콘텐츠(자유 텍스트)를 프롬프트에 이어붙이며 프롬프트 인젝션 유사 문구가 섞여 들어감 | Tampering(자체적) | 위험 낮음 — Claude가 직접 작성하는 신뢰된 콘텐츠이고 사용자 입력이 아니다. 다만 텍스트에 `{`/`}` 같은 포맷 문자가 들어가면 f-string 조합 시 오류가 날 수 있으므로, `_format_clock_state` 구현 시 일반 문자열 연결(f-string)만 쓰고 `.format()`/템플릿 엔진을 새로 들이지 않는다(기존 관례와 일치) |
| 캐릭터 만들기 구두 대본을 통해 참가자가 부적절한 캐릭터명·설명을 자유 기재 | 해당 없음(코드 보안 이슈 아님, 운영 이슈) | 실험 참가자 4명 한정 소규모 진행이므로 콘텐츠 검열 로직 불필요(MEAS-04/EXP-04가 이미 요구하지 않음) |

## Sources

### Primary (HIGH confidence)
- `src/gptrpg/turn/context.py`, `src/gptrpg/agents/context.py`, `src/gptrpg/agents/prompt_assembly.py`, `src/gptrpg/rulebooks/dungeonworld_like.py`, `src/gptrpg/rulebooks/openquest_creatures.py`, `src/gptrpg/rulebooks/moves.py`, `src/gptrpg/rules_core/entities.py`, `src/gptrpg/web/characters_data.py`, `src/gptrpg/web/routes_events.py`, `src/gptrpg/cli/turn_flow.py` — 전부 이번 세션에 `Read`로 직접 확인
- `.planning/phases/05-1/05-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md` — 이번 세션에 직접 확인
- `.planning/phases/04-experiment-tool/04-01-SUMMARY.md`, `04-03-SUMMARY.md`, `04-05-SUMMARY.md` — 이번 세션에 직접 확인, "시나리오 데이터는 EXP-01/Phase 5의 일"이라는 명시적 열린 자리 재확인
- `.planning/phases/03-ai/03-UAT.md` — 이번 세션에 직접 확인, Nemotron 실측 이력
- `docs/GPTRPG-design-plan.md` §5(위협 시계), §6.1(캐릭터 만들기), §7.3(리캡), §12.2~12.3(실험 설계·최소 도구 범위) — 이번 세션에 직접 확인
- `docs/GPTRPG-M0-decisions.md` D9(시나리오 포맷), D21(위협 시계 데이터 구조), D31(기억 주입 규칙) — 이번 세션에 직접 확인
- `openrouter.ai/docs/api-reference/limits` — 이번 세션 `WebFetch`로 직접 확인 [CITED]

### Secondary (MEDIUM confidence)
- (없음 — 위 openrouter.ai 문서는 공식 1차 문서라 Primary로 분류)

### Tertiary (LOW confidence)
- Dungeon World Fronts 저작 가이드(WebSearch 요약, `dungeonworldsrd.com`/`spoutinglore.blogspot.com` 등 포함) [CITED, 단일 검색·교차검증 없음]
- Blades in the Dark clock 저작 원칙(WebSearch 요약, `bladesinthedark.com` 공식 사이트 포함) [CITED, 단일 검색·교차검증 없음]

## Metadata

**Confidence breakdown:**
- 코드 확장 지점(Standard Stack/Architecture Patterns 핵심부): HIGH — 전부 이번 세션에 실제 파일을 읽어 확인, 라인 번호와 원문 인용 포함
- Front/시계 저작 가이드: MEDIUM — 프로젝트 자체 문서(D9/D21/§5)가 1차 근거이고, 외부 TRPG 이론(Apocalypse World/Blades in the Dark)은 보강 자료로만 사용
- OpenRouter 요금제 리스크: MEDIUM-HIGH — 공식 문서를 이번 세션에 직접 확인했으나, 요금제는 변경될 수 있으므로 세션 직전 재확인 권장
- 운영 항목(참가자 모집·일정·관찰): 해당 없음 — 코드/문서 검증 대상이 아님, 절차 준비가 산출물

**Research date:** 2026-08-03
**Valid until:** 코드 확장 지점은 다음 코드 변경 전까지 유효(안정적). OpenRouter 요금제 스냅샷은 7일(세션 직전 재확인 권장) — 첫 세션과 2세션 사이 1주 간격 동안 정책이 바뀔 수 있으므로, 2세션 직전에도 한 번 더 확인할 가치가 있다.

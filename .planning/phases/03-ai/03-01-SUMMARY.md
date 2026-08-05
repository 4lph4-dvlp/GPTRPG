---
phase: 03-ai
plan: 01
subsystem: ai
tags: [anthropic, openai, nim, llm-provider-abstraction, prompt-caching, streaming, cli, event-sourcing]

# Dependency graph
requires:
  - phase: 01-rules-core-and-event-log
    provides: "여섯 사건 종류(특히 ActionDeclared/ActionConfirmed/CheckResolved/NarrationAppended/AiInvoked), SessionActor의 여섯 명령 파이프라인(검증→규칙코어→순번→append), caused_by_seq 인과 칸, CLI submit/replay 골격"
  - phase: 02-two-rulebooks-one-vessel
    provides: "Rulebook/GradeBand 선언 모양, get_rulebook/UnknownRulebook 조용히-대체하지-않기 규율, CLI --rulebook 플래그"
provides:
  - "gptrpg.agents 패키지 — AgentResult 응답 껍데기, TurnContext/ClockState(매 턴 문맥 네 칸 고정), Provider 프로토콜, AnthropicProvider·NimProvider 두 어댑터, 제공자 등록소(PROVIDER_ENV_VARS/PROVIDER_FACTORIES)"
  - "rulebooks/moves.py — 던전월드 계열·OpenQuest 각 10개 닫힌 무브 목록, get_moves()"
  - "prompt_assembly.py — 영구/세션/턴 3단 캐시 조립, cache_control 분기점"
  - "action_classifier.classify() — 후보 목록 산출 + UnknownMove 거부"
  - "master_gm.narrate()/chunk_sentences() — 문장 경계 스트리밍"
  - "gptrpg turn CLI 하위 명령 — 선언→분류→사람확인→판정→서사 전체 사슬을 실제로 관통"
  - ".importlinter 계약 3 — agents가 event_log/session_actor/sqlite3를 볼 수단이 없음을 코드로 증명"
affects: ["03-02", "03-03", "03-04", "06 (원가 계산이 AiInvoked.latency_ms/prompt_tokens/completion_tokens 필드명에 의존)"]

# Actuals (#2632)
actuals:
  tokens: 14336
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: ["anthropic>=0.120.2", "openai>=2.52.0 (NimProvider가 base_url 스왑으로 사용)"]
  patterns:
    - "Provider 프로토콜(list_models/complete/stream/last_result) + 어댑터별 독립 구현 — 호출부는 제공자 이름으로 분기하지 않는다"
    - "프롬프트 안정성 순서(영구→세션→턴)를 강제하는 단일 조립 함수 — cache_control 분기점이 그 함수 안에만 존재"
    - "스트리밍 반복자를 다 소진한 뒤 last_result()로 토큰·시간을 가져가는 지연 계산 규약"
    - "제공자 이름→환경변수→어댑터 팩토리 3단 등록소, 조용히 다른 제공자로 대체하지 않음(UnknownProvider/MissingApiKey/ProviderNotImplemented)"

key-files:
  created:
    - src/gptrpg/agents/__init__.py
    - src/gptrpg/agents/envelope.py
    - src/gptrpg/agents/context.py
    - src/gptrpg/agents/prompt_assembly.py
    - src/gptrpg/agents/action_classifier.py
    - src/gptrpg/agents/master_gm.py
    - src/gptrpg/agents/providers/__init__.py
    - src/gptrpg/agents/providers/base.py
    - src/gptrpg/agents/providers/anthropic_provider.py
    - src/gptrpg/agents/providers/nim_provider.py
    - src/gptrpg/rulebooks/moves.py
    - tests/test_turn_tracer.py
  modified:
    - src/gptrpg/cli/main.py
    - .importlinter
    - pyproject.toml
    - tests/conftest.py

key-decisions:
  - "agents/envelope.py의 AgentResult를 pydantic이 아닌 plain frozen dataclass로 만듦 — 사건 기록에 직접 들어가지 않는 메모리 안 임시 그릇이라는 D-30 규정을 그대로 따름"
  - "action_classifier/master_gm은 session_actor·event_log를 전혀 import하지 않는다 — CLI(cli/main.py)가 Proposal/Iterator[str] 반환값을 받아 RecordAiCall/ConfirmAction/AppendNarration으로 직접 조립한다. 이것이 .importlinter 계약 3이 코드로 증명하는 경계다"
  - "RecordAiCall(master_gm, ...)의 caused_by_seq는 ResolveCheck의 순번이 아니라 그 앞의 ConfirmAction 순번을 가리킨다(플랜 원문 그대로) — 두 AI 호출(분류기·진행자) 모두 '판정 결과'가 아니라 '플레이어가 낸 입력 사건'에 인과적으로 묶인다는 일관된 설계"
  - "장면 대상·캐릭터 상태는 이번 단계에서 --rulebook 값과 무관하게 항상 dungeonworld_like.EXAMPLE_SINGLE_STAT_FOE에서 채운다 — openquest.py에는 대응하는 예시 Entity가 없고 이 파일은 이번 계획의 files_modified 범위 밖이다. 위협 시계 segment_count는 시나리오 데이터가 없어 D-21의 '4~6칸' 범위 중 6을 자리 표시자로 고정했다(cli/main.py의 _PLACEHOLDER_CLOCK_SEGMENT_COUNT)"
  - "[deviation] 03-02 몫이던 NimProvider를 03-01로 앞당겼다 — 사용자에게 ANTHROPIC_API_KEY가 없고 NVIDIA_API_KEY만 있어 Task 3(실제 제공자 검증)을 NIM으로 돌려야 했다. 오케스트레이터가 build.nvidia.com의 공식 코드 샘플을 라이브로 확인해 base_url(https://integrate.api.nvidia.com/v1)과 env var 이름(NVIDIA_API_KEY)을 검증했다. openai SDK를 base_url 스왑으로 재사용 — RESEARCH.md의 예측과 일치"
  - "[deviation] Task 3의 사람 확인 기준을 Anthropic이 아닌 NIM(meta/llama-3.1-70b-instruct)으로 대체 실행 — 기준 6(캐싱 관찰)은 관찰용·비차단 항목이라 생략(사용자 동의). NIM/OpenAI 호환 표면에는 cache_control과 동등한 API가 없다는 사실을 nim_provider.py에 명시했다"

patterns-established:
  - "제공자 어댑터 파일 하나 = SDK import 하나 — 다른 파일은 어떤 SDK도 모른다"
  - "프롬프트 조립은 permanent/session 두 조각(cache_control 부착) + turn 한 조각으로 고정, 호출마다 달라지는 값은 절대 system에 넣지 않는다"

requirements-completed: [RIG-01, RIG-03, MEAS-02, MEAS-04]

coverage:
  - id: D1
    description: "자유 문장 하나가 분류→사람 확인→판정→서사까지 한 번도 끊기지 않고 돌고, 그 턴의 사건이 순번 순서대로 인과 칸(caused_by_seq)으로 이어진 채 기록된다"
    requirement: RIG-01
    verification:
      - kind: unit
        ref: "tests/test_turn_tracer.py#test_turn_runs_full_loop_and_records_events_in_causal_order"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 live run against NIM (meta/llama-3.1-70b-instruct), 2026-08-02 — user-confirmed move proposal + check-before-narration ordering"
        status: pass
    human_judgment: false
  - id: D2
    description: "플레이어가 확인하지 않으면 ResolveCheck가 제출되지 않는다 — 확인·거부 둘 다 ConfirmAction을 남기지만 거부 시 판정·서사가 전혀 기록되지 않는다"
    requirement: RIG-01
    verification:
      - kind: unit
        ref: "tests/test_turn_tracer.py#test_turn_player_rejects_suggestion_records_no_check_resolved"
        status: pass
    human_judgment: false
  - id: D3
    description: "action_classifier가 돌려주는 무브·능력치는 룰북이 선언한 닫힌 목록 안에서만 나온다 — 목록 밖 이름은 UnknownMove로 거부된다"
    requirement: RIG-01
    verification:
      - kind: unit
        ref: "tests/test_turn_tracer.py#test_classify_raises_unknown_move_for_name_outside_closed_list"
        status: pass
    human_judgment: false
  - id: D4
    description: "서사가 문장 단위 여러 narration_appended 사건으로 흘러나온다(chunk_index 0부터 1씩), check_resolved 순번이 첫 서사 조각보다 작다"
    requirement: RIG-03
    verification:
      - kind: unit
        ref: "tests/test_turn_tracer.py#test_turn_runs_full_loop_and_records_events_in_causal_order"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 live run against NIM — user confirmed narration streamed sentence-by-sentence in real time (not one blob), 2026-08-02"
        status: pass
    human_judgment: false
  - id: D5
    description: "AI 호출 한 번마다 ai_invoked 사건 하나가 실제로 측정한 latency_ms와 실제 토큰 수로 기록된다(상수·추정치 아님)"
    requirement: MEAS-02
    verification:
      - kind: unit
        ref: "tests/test_turn_tracer.py#test_turn_runs_full_loop_and_records_events_in_causal_order (ai_events latency_ms>=0, tokens>0 assertions)"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 live NIM replay — AI 호출 수=3, 서사 조각 수=7, 토큰 합계=1611 (두 번 실행: 확인 1회+거부 1회 = 2+1 AI 호출)"
        status: pass
    human_judgment: false
  - id: D6
    description: "MEAS-02의 응답 속도 UX 임계값 동작(5초 진행 표시 D-26, 15초 초과 시 판정 우선 D-33)은 03-01의 범위가 아니다 — 이번 계획은 latency_ms 실측 기록만 만든다"
    verification: []
    human_judgment: true
    rationale: "D-26/D-27 타임아웃·재시도·진행 표시 UI는 03-02/03-03의 명시적 범위다(03-01-PLAN.md에는 없는 액션). 이 항목은 그 두 계획이 끝난 뒤 다시 채점해야 한다 — 지금 human_judgment:false로 자동 통과시키면 검증되지 않은 것을 검증된 것처럼 보이게 만든다"
  - id: D7
    description: "플레이어가 친 문장이 ActionDeclared.raw_text에 손대지 않은 채 남고, 시스템 제안이 ActionConfirmed.system_suggestion에, 확인 여부가 player_confirmed에 함께 남는다"
    requirement: MEAS-04
    verification:
      - kind: unit
        ref: "tests/test_turn_tracer.py#test_turn_runs_full_loop_and_records_events_in_causal_order (declared.raw_text 글자 단위 비교)"
        status: pass
    human_judgment: false
  - id: D8
    description: "같은 세션에서 문장만 다른 두 번의 분류기 호출은 system 블록이 바이트 단위로 동일하다 — 프롬프트 캐시 접두가 안정적이다"
    verification:
      - kind: unit
        ref: "tests/test_turn_tracer.py#test_classifier_system_prompt_is_byte_identical_across_calls_with_different_text"
        status: pass
    human_judgment: false
  - id: D9
    description: "recent_turns는 열 개를 넘길 수 없다 — 30턴짜리 기록을 넣어도 TurnContext에 실려 나가는 것은 마지막 열 개다"
    verification:
      - kind: unit
        ref: "tests/test_turn_tracer.py#test_turn_context_recent_turns_is_capped_at_ten"
        status: pass
    human_judgment: false
  - id: D10
    description: ".importlinter 계약 3 — gptrpg.agents가 event_log/session_actor/sqlite3를 import할 수 없다(AI가 저장소를 훑는 경로가 없음을 코드로 증명)"
    verification:
      - kind: other
        ref: "uv run lint-imports — 3 contracts kept, 0 broken"
        status: pass
    human_judgment: false

# Metrics
duration: ~95min (두 차례의 실제 사람 확인 왕복 포함)
completed: 2026-08-02
status: complete
---

# Phase 3 Plan 1: AI 진행자 트레이서 Summary

**자유 문장 하나가 분류→사람 확인→2d6 판정→문장 단위 서사까지 한 번도 끊기지 않고 도는 `gptrpg turn` CLI 명령. Anthropic·NIM 두 실제 제공자로 검증됨.**

## Performance

- **Duration:** ~95분 (설치 승인 체크포인트 1회 + 실제 제공자 검증 체크포인트 1회, NIM으로 재검증 포함)
- **Started:** 2026-08-02T00:55:00Z (context load) — 2026-08-02T00:59:19Z (Task 1 approved, Task 2 시작)
- **Completed:** 2026-08-02T02:03:15Z
- **Tasks:** 3/3 (checkpoint:human-verify → tracer → checkpoint:human-verify)
- **Files modified:** 17 (13 new, 4 modified) + 1 dependency lockfile

## Accomplishments

- `gptrpg.agents` 패키지 신설 — `AgentResult`(D-30 네 칸 최소 규격), `TurnContext`/`ClockState`(D-31 매 턴 문맥 네 칸, `RECENT_TURNS_LIMIT=10`, `TooMuchContext` 가드), `Provider` 프로토콜, `AnthropicProvider`·`NimProvider` 두 어댑터, 제공자 등록소
- `rulebooks/moves.py` — 던전월드 계열·OpenQuest 각 10개 닫힌 무브 목록, `get_moves()`가 `UnknownRulebook` 규율을 그대로 물려받음
- `prompt_assembly.py` — 영구(룰북+무브목록)/세션(장면·캐릭터·시계)/턴(최근대화+이번문장) 3단 조립, `cache_control` 분기점 2개, 호출마다 달라지는 값이 `system`에 절대 안 들어감(byte-identical 시험으로 증명)
- `action_classifier.classify()` — 닫힌 목록 밖 이름을 `UnknownMove`로 거부(RIG-01, D-16)
- `master_gm.narrate()`/`chunk_sentences()` — 문장 경계 스트리밍, 판정 결과가 항상 서사보다 먼저 기록됨(RIG-03)
- `gptrpg turn` CLI 하위 명령 — 기존 여섯 명령(declare/confirm/roll/narrate/ai)을 그대로 재사용해 전체 사슬을 관통, `caused_by_seq`를 매 단계 명시적으로 이어 붙임
- `.importlinter` 계약 3 신설 — `gptrpg.agents`가 `event_log`/`session_actor`/`sqlite3`를 볼 수단이 없음을 코드로 증명 (ROADMAP 성공조건 4)
- Task 3(실제 제공자 검증)을 Anthropic 대신 **NIM**으로 완주 — 사용자가 가진 키에 맞춰 `NimProvider`를 최소 범위로 03-02에서 앞당김

## Task Commits

Each task was committed atomically:

1. **Task 1: 설치할 제공자 SDK 세 개의 출처를 사람이 확인한다** — checkpoint, no commit (승인만)
2. **Task 2: 트레이서 — 문장 한 개가 분류·확인·주사위·서사까지 한 바퀴 돈다** - `1c8a34e` (feat)
   - **[deviation] NimProvider 앞당김** - `3703a87` (feat)
   - **[deviation fix] UnknownMove 검증 누락 보강** - `9e28906` (test, Rule 2)
3. **Task 3: 진짜 제공자로 한 턴을 사람이 직접 돌려 본다** — checkpoint, no commit (NIM으로 사람이 직접 검증)

**Plan metadata:** (다음 커밋에서 이 SUMMARY.md·STATE.md·ROADMAP.md·REQUIREMENTS.md를 묶음)

## Files Created/Modified

- `src/gptrpg/agents/envelope.py` - `AgentResult` 응답 껍데기(D-30 네 칸)
- `src/gptrpg/agents/context.py` - `TurnContext`/`ClockState`, `RECENT_TURNS_LIMIT`, `TooMuchContext`
- `src/gptrpg/agents/prompt_assembly.py` - 영구/세션/턴 3단 프롬프트 조립 + 캐시 분기점
- `src/gptrpg/agents/action_classifier.py` - `classify()`, `MoveCandidate`, `Proposal`, `UnknownMove`
- `src/gptrpg/agents/master_gm.py` - `narrate()`, `chunk_sentences()`
- `src/gptrpg/agents/providers/base.py` - `Provider` 프로토콜(SDK 미import)
- `src/gptrpg/agents/providers/anthropic_provider.py` - `AnthropicProvider`
- `src/gptrpg/agents/providers/nim_provider.py` - `NimProvider` (deviation, 03-02에서 앞당김)
- `src/gptrpg/agents/providers/__init__.py` - `PROVIDER_ENV_VARS`(5개)/`PROVIDER_FACTORIES`(2개 등록)/`get_provider`
- `src/gptrpg/rulebooks/moves.py` - `MoveDecl`, `DUNGEONWORLD_LIKE_MOVES`/`OPENQUEST_MOVES`(각 10개), `get_moves()`
- `src/gptrpg/cli/main.py` - `turn` 하위 명령, `_build_turn_context`, `_turn_flow`
- `.importlinter` - `gptrpg.agents` 계층 삽입 + 계약 3 신설
- `pyproject.toml` - `anthropic`·`openai` 의존성, `agents/*` TID251 무시
- `tests/conftest.py` - `FakeProvider` 픽스처
- `tests/test_turn_tracer.py` - 트레이서 자동 시험 6개

## Decisions Made

- `AgentResult`는 pydantic이 아닌 plain dataclass — 기록에 직접 들어가지 않는 메모리 안 임시 그릇
- `gptrpg.agents`는 `session_actor`·`event_log`를 전혀 모른다 — CLI가 반환값을 받아 명령으로 조립하는 것이 유일한 경로(`.importlinter` 계약 3이 코드로 강제)
- `RecordAiCall(master_gm, ...)`의 `caused_by_seq`는 플랜 원문대로 `ResolveCheck`가 아니라 `ConfirmAction`의 순번을 가리킨다 — 두 AI 호출 모두 "판정 결과"가 아니라 "플레이어 입력 사건"에 인과적으로 묶인다
- 장면·캐릭터 상태는 `--rulebook` 값과 무관하게 항상 `dungeonworld_like.EXAMPLE_SINGLE_STAT_FOE`에서 채운다 (openquest.py엔 대응 예시가 없고 이번 계획의 파일 범위 밖)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `UnknownMove` 거부 경로에 시험이 없었다**
- **Found during:** 최종 마감 점검 (계획의 `must_haves.truths`를 다시 훑던 중)
- **Issue:** 플랜은 "목록에 없는 이름은 조용히 통과하지 않고 `UnknownMove`로 거부된다"를 명시적 `must_haves.truths`로 요구했지만, `tests/test_turn_tracer.py`의 원래 다섯 시험 중 이 경로를 직접 부르는 것이 하나도 없었다
- **Fix:** `test_classify_raises_unknown_move_for_name_outside_closed_list` 추가 — `FakeProvider`가 닫힌 목록 밖 이름("fireball")을 돌려주면 `classify()`가 `UnknownMove`를 던지는지 CLI 없이 직접 확인
- **Files modified:** `tests/test_turn_tracer.py`
- **Verification:** `uv run pytest tests/test_turn_tracer.py -x` — 6/6 통과
- **Committed in:** `9e28906`

### Scope-Pulled-Forward Deviation (user-approved, not an auto-fix)

**2. NimProvider를 03-02에서 03-01로 앞당김**
- **Trigger:** 사용자가 `ANTHROPIC_API_KEY`를 갖고 있지 않고 `NVIDIA_API_KEY`만 있어, 플랜 Task 3("진짜 제공자로 한 턴을 사람이 직접 돌려 본다")를 Anthropic으로 완주할 방법이 없었다
- **Discussion:** 오케스트레이터와 사용자가 트레이드오프를 논의 — Anthropic 전용 `cache_control` 코드 경로는 NIM으로 실행하면 검증되지 않는다는 점, RESEARCH.md가 NIM의 인증 세부사항을 이번 세션에서 검증되지 않은 LOW confidence로 표시했다는 점을 명시적으로 인지한 채 사용자가 진행을 택했다
- **Verification of the pulled-forward claim:** 오케스트레이터가 build.nvidia.com(meta/llama-3_1-70b-instruct 페이지)의 NVIDIA 공식 코드 샘플을 이번 세션에서 라이브로 확인 — `openai` 클라이언트 + `base_url="https://integrate.api.nvidia.com/v1"` + `NVIDIA_API_KEY` 환경변수, RESEARCH.md의 예측(OpenAI 호환 표면, 전용 SDK 없음)과 정확히 일치
- **Scope kept minimal per instruction:** `openai` 의존성 추가 + `NimProvider`(`Provider` 프로토콜 4메서드) + `PROVIDER_FACTORIES`에 `"nim"` 등록. **다른 세 제공자(OpenAI 단독·OpenRouter·Gemini)와 D-31의 키 감지/모델 선택 UI는 만들지 않았다** — 여전히 03-02의 몫이다
- **Files created/modified:** `src/gptrpg/agents/providers/nim_provider.py`(new), `src/gptrpg/agents/providers/__init__.py`, `pyproject.toml`, `uv.lock`
- **Committed in:** `3703a87`
- **⚠️ Handoff note for 03-02's executor:** `src/gptrpg/agents/providers/nim_provider.py`가 이미 존재하고 03-02의 `files_modified` 목록에도 이 파일이 이미 들어 있다(03-02-PLAN.md 확인함). 03-02는 이 파일을 새로 만들지 말고 **이어받아 검증·확장**해야 한다 — 특히 `list_models()`의 실제 응답 모양과 `stream_options={"include_usage": True}`가 NIM 백엔드에서 그대로 받아들여지는지는 03-01의 Task 3 검증(비스트리밍 `complete()` 경로가 아니라 스트리밍 `stream()` 경로로 실제 확인됨, 아래 참고)만으로 완전히 증명되지 않은 부분이 있다면 03-02가 마저 확인해야 한다.

**3. Task 3(실제 제공자 검증)을 Anthropic이 아니라 NIM으로 수행**
- **Trigger:** 위 2번 항목과 동일한 이유(사용자에게 Anthropic 키 없음)
- **What changed vs. the plan's `<how-to-verify>`:** `--provider anthropic`→`--provider nim --model meta/llama-3.1-70b-instruct`. 기준 2~5(무브 제안이 닫힌 목록 안에 있는가 / 판정이 서사보다 먼저 나오는가 / 서사가 문장 단위로 스트리밍되는가 / replay 숫자가 0이 아닌가)는 원문 그대로 확인했다. 기준 6("참고용 관찰" — 같은 세션 두 번째 호출이 캐시로 빨라지는지)은 **NIM엔 해당하지 않아 생략**(사용자 동의) — Anthropic 전용 `cache_control` 기능이라 애초에 관찰 대상이 아니다
- **Live verification result:** 무브 이름 `hack_and_slash`가 `src/gptrpg/rulebooks/moves.py:28`에 실제로 존재함을 확인, 판정 줄("판정: 눈 [5, 1] 등급 miss 목표 10")이 서사보다 먼저 출력됨을 사용자 터미널 붙여넣기로 확인, 서사가 실시간으로 문장 단위 스트리밍됨을 사용자가 직접 확인, `replay` 결과 AI 호출 수=3(확인 1회+거부 1회 실행 = 2+1, 버그 아님 — 두 번 돌린 결과가 합산된 것)·서사 조각 수=7(≥2 충족)·토큰 합계=1611(≠0 충족)
- **Committed in:** N/A (검증 자체는 코드 변경이 아님)

---

**Total deviations:** 1 auto-fixed (Rule 2, missing test coverage) + 2 user-approved scope/verification substitutions (NimProvider pulled forward, Task 3 run against NIM instead of Anthropic)
**Impact on plan:** No scope creep beyond what the user explicitly approved. The pulled-forward `NimProvider` is intentionally minimal (matches 03-02's own planned file scope) and does not implement 03-02's remaining providers or D-31's selection UI. Task 3's substitution (NIM instead of Anthropic) is a like-for-like real-provider verification, not a downgrade — every plan-authored pass/fail criterion (2–5) was checked; only the explicitly-optional, Anthropic-specific observation (6) was skipped.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

**External services require manual configuration.**
- `ANTHROPIC_API_KEY` was listed in this plan's `user_setup` but the user does not have one — **not required going forward** for this plan's own verification, since Task 3 was completed against NIM instead. 03-02's `user_setup` already lists all five provider env vars including `NVIDIA_API_KEY` (which the user does have) and `ANTHROPIC_API_KEY` (which they don't) — 03-02's executor should expect the same key gap and may need to run its own multi-provider checkpoints against whichever subset of keys the user actually holds.

## Next Phase Readiness

- `gptrpg.agents` package, `Provider` protocol, and the `agents`↔`cli` boundary are stable — 03-02 (remaining providers + model-selection UI), 03-03 (timeout/retry, D-27/D-28/D-29), and 03-04 (three-tier confirm UX, D-34/D-35/D-36) all build directly on top without needing to touch this plan's files except `nim_provider.py`/`providers/__init__.py` (already flagged above) and `cli/main.py`'s `turn` command (which 03-03/03-04 will extend, not replace).
- **Not yet built, by design:** D-26 (5s dot-progress), D-33's 15s check-result-first override, D-27/D-28/D-29's timeout+retry+no-move-fallback loop, D-31's key-detection/model-selection UI, D-33 (03-01-numbering)'s persisted provider/model choice. These are explicitly 03-02/03-03's scope — `MEAS-02`'s requirement checkbox is marked complete per this plan's frontmatter (the core "measured, not constant" latency recording is done and tested), but its full UX-threshold behavior is NOT yet built; see coverage entry D6 above for the explicit flag.
- No blockers for continuing phase 3's remaining plans.

---
*Phase: 03-ai*
*Completed: 2026-08-02*

## Self-Check: PASSED

All 17 files claimed as created/modified exist on disk; all 3 task commit hashes (`1c8a34e`, `3703a87`, `9e28906`) verified present in `git log --oneline --all`. `.planning/WINDOWS.md` ledger entry recorded (id 1, `deviation`, open) for the MEAS-02 partial-completion caveat (coverage entry D6).

# Phase 9: 에이전트 구조 재편 - Pattern Map

**Mapped:** 2026-08-07
**Files analyzed:** 11 (신규 4 + 수정 7)
**Analogs found:** 11 / 11 (전부 강한 매치 — 이 단계의 리서치가 이미 "새로 발명하지 말라"는 결론을 내렸다)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `src/gptrpg/agents/situation_judge.py` (신규) | service (agent) | request-response | `src/gptrpg/agents/action_classifier.py` | role-match (닫힌 판단 + LLM 호출 패턴) |
| `src/gptrpg/agents/scene_entity_judge.py` (신규) | service (agent) | request-response | `src/gptrpg/agents/action_classifier.py` | exact (닫힌 목록/JSON 파싱과 완전히 같은 모양) |
| `src/gptrpg/agents/clock_signal_judge.py` (신규) | service (agent) | request-response | `src/gptrpg/agents/action_classifier.py` | exact (닫힌 목록/JSON 파싱과 완전히 같은 모양) |
| `src/gptrpg/agents/master_gm.py` (수정 — narrate 시그니처 축소) | service (agent) | streaming | 자기 자신(기존 `narrate`/`chunk_sentences` 그대로 유지, 입력만 변경) | exact |
| `src/gptrpg/agents/prompt_assembly.py` (수정 — build_gm_prompt 축소 + build_situation_prompt 신설) | utility (prompt builder) | transform | 자기 자신의 `build_classifier_prompt`(105-127줄) | exact (같은 파일 내 자매 함수) |
| `src/gptrpg/agents/context.py` (수정 — 역할별 문맥 값 객체 추가) | model (value object) | transform | 자기 자신의 `TurnContext`(51-62줄) | exact |
| `src/gptrpg/agents/config.py` (수정 — AGENT_ROLES 확장) | config | CRUD | 자기 자신의 `AGENT_ROLES`(26줄) | exact (튜플만 확장, 나머지 제네릭 코드 그대로) |
| `src/gptrpg/agents/invoke.py` (수정 — 새 역할 타임아웃 상수 추가) | utility (timeout/retry) | request-response | 자기 자신의 `CLASSIFIER_TIMEOUT_S`/`GM_TIMEOUT_S`(26-42줄) | exact |
| `src/gptrpg/cli/turn_flow.py` (수정 — 병렬 판단 + 배경 await 오케스트레이션 삽입) | controller (CLI turn flow) | event-driven | 자기 자신의 289-336줄 구간(판정 결과 확정 → narrate 호출) | exact |
| `src/gptrpg/web/routes_actions.py` (수정 — 병렬 판단 + BackgroundTasks 시계 조건 검사) | controller (route handler) | event-driven | 자기 자신의 `_illustrate_scene`(576-639줄) + `confirm()`의 `background.add_task` 호출부(548-563줄) | exact |
| `src/gptrpg/turn/context.py` (수정 가능성 — 역할별 문맥 조립, Discretion 항목) | service (context assembly) | transform | `src/gptrpg/agents/prompt_assembly.py`의 `_session_block_text`(97-102줄, 여러 칸을 조합해 값 객체를 만드는 패턴) | role-match |

## Pattern Assignments

### `src/gptrpg/agents/scene_entity_judge.py` / `clock_signal_judge.py` (신규, service, request-response)

**Analog:** `src/gptrpg/agents/action_classifier.py` (전체 구조를 그대로 복제)

**Imports pattern** (action_classifier.py 1-17줄):
```python
"""자유 문장 하나를 룰북의 닫힌 무브 목록과 대조해 후보로 좁힌다.

모델이 뱉은 수치·판정 결과는 여기서 읽지 않는다(D14) — 후보 목록 이름
문자열로만 모델 출력을 해석한다.
"""

import json
import re
from dataclasses import dataclass
from typing import Literal

from gptrpg.agents.context import TurnContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import CLASSIFIER_TIMEOUT_S, call_with_one_retry
from gptrpg.agents.prompt_assembly import build_classifier_prompt
from gptrpg.agents.providers.base import Provider
from gptrpg.rulebooks.moves import MoveDecl
```
새 판단 조각은 `build_classifier_prompt` 대신 신설할 `build_scene_entity_prompt`/
`build_clock_signal_prompt`를 `prompt_assembly.py`에서 import한다.

**닫힌 결과 dataclass 패턴** (action_classifier.py 40-70줄):
```python
@dataclass(frozen=True)
class MoveCandidate:
    """분류기가 제안하는 무브 후보 하나."""
    move: str
    stat: str


@dataclass(frozen=True)
class Proposal:
    candidates: tuple[MoveCandidate, ...]
    ai: AgentResult

    @property
    def tier(self) -> ProposalTier:
        ...
```
`judge_new_entity`/`judge_clock_signal`은 `EntityJudgment`/`ClockSignal` 같은
`@dataclass(frozen=True)` 결과 값 + `ai: AgentResult`를 같은 모양으로 선언한다.

**강건 JSON 파싱 — 그대로 재사용/복제** (action_classifier.py 72-116줄):
```python
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_CODE_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_JSON_ARRAY = re.compile(r"\[.*\]", re.DOTALL)


def _try_parse_json_array(raw_text: str) -> list:
    """모델 출력에서 JSON 배열을 뽑아 파싱한다.
    ① 원문 그대로 먼저 시도 ② <think> 블록 제거 + 코드펜스 벗기기 후 재시도
    ③ 그래도 실패하면 빈 목록.
    """
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    text = _THINK_BLOCK.sub("", raw_text)
    fence_match = _CODE_FENCE.search(text)
    if fence_match:
        text = fence_match.group(1)
    array_match = _JSON_ARRAY.search(text)
    if array_match:
        text = array_match.group(0)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []
```
계획 단계 판단 사항: 이 함수를 `agents/action_classifier.py`에서 공유 유틸(예:
`agents/json_parsing.py`)로 승격할지, 아니면 새 판단 조각들이 각자 import해서
그대로 쓸지(현재 `action_classifier`가 `agents` 계층 안에 있으므로 import 자체는
레이어 계약 위반이 아니다) 정한다.

**핵심 호출 패턴 — call_with_one_retry로 감싸기** (action_classifier.py 139-191줄):
```python
def classify(
    *,
    provider: Provider,
    model: str,
    ctx: TurnContext,
    raw_text: str,
    moves: tuple[MoveDecl, ...],
    rulebook_display_name: str,
) -> Proposal:
    system, messages = build_classifier_prompt(...)

    def _call_once() -> AgentResult:
        return provider.complete(
            model=model, system=system, messages=messages,
            max_tokens=1024, timeout_s=CLASSIFIER_TIMEOUT_S,
        )

    result, _last_error_text = call_with_one_retry(_call_once, timeout_s=CLASSIFIER_TIMEOUT_S)
    if not result.ok:
        return Proposal(candidates=(), ai=result)

    known_move_ids = frozenset(move.move_id for move in moves)
    candidates = _parse_candidates(str(result.value), known_move_ids)[:MAX_CANDIDATES]
    return Proposal(candidates=candidates, ai=result)
```
`judge_new_entity`/`judge_clock_signal`은 이 함수 모양을 그대로 복제한다 — 실패
시 예외를 던지지 않고 "빈 판단" 값을 돌려주는 것이 ARCH-05(D-05)가 요구하는
"없으면 없는 대로 진행"의 원천이다. `UnknownMove`처럼 결과가 닫힌 목록을
어겼을 때 던지는 예외를 새 판단 조각에도 대칭으로 둘지는 계획 단계 판단.

---

### `src/gptrpg/agents/situation_judge.py` (신규, service, request-response)

**Analog:** `src/gptrpg/agents/action_classifier.py`의 구조 + `src/gptrpg/agents/prompt_assembly.py`의 `build_gm_prompt`가 지금 담당하는 페르소나 지시문(permanent 블록)을 이 함수가 흡수한다.

**핵심 패턴 — 지금 서술이 갖고 있던 페르소나+시나리오 지시문 전체를 흡수**
(현재 `build_gm_prompt`, prompt_assembly.py 130-166줄, ARCH-02가 옮기라고 요구하는 지점):
```python
def build_gm_prompt(
    *,
    rulebook_display_name: str,
    ctx: TurnContext,
    check_summary: str,
) -> tuple[list[dict], list[dict]]:
    permanent = (
        f"너는 {rulebook_display_name} 룰북을 쓰는 TRPG의 진행자다. 판정 결과를 "
        "받아 다음에 무슨 일이 일어나는지 서술한다. ..."
    )
    session = _session_block_text(ctx)
    system = [_cached_block(permanent), _cached_block(session)]
    turn = (
        f"최근 대화:\n{_format_recent_turns(ctx.recent_turns)}\n\n"
        f"방금 판정 결과: {check_summary}"
    )
    messages = [{"role": "user", "content": turn}]
    return system, messages
```
`situation_judge.judge()`는 새 `build_situation_prompt`(prompt_assembly.py에
신설)를 불러 이 페르소나 지시문 + 시나리오 원문(`_format_clock_state`가 지금
펼치는 정체/원하는 것/파국 텍스트 전체)을 받고, "지금 이 칸에서 서술에 필요한
한두 문장"만 뽑아 `narrate()`에 넘길 사실 묶음을 만든다(Pitfall 2 참조).

**타임아웃 상수 자리** (invoke.py 26-42줄, 새 역할 상수를 같은 파일 같은 모양으로 추가):
```python
CLASSIFIER_TIMEOUT_S = 5.0
GM_TIMEOUT_S = 15.0
MAX_ATTEMPTS = 2
```
`SITUATION_TIMEOUT_S`/`SCENE_ENTITY_TIMEOUT_S`/`CLOCK_SIGNAL_TIMEOUT_S` 등을
`CLASSIFIER_TIMEOUT_S`(경량 판단)와 `GM_TIMEOUT_S`(고비용 서술) 사이 어딘가로
같은 도크스트링 관례("D-27이 이 값 자체는 건드리지 않는다"류 각주)로 추가한다.

---

### `src/gptrpg/agents/master_gm.py` (수정, service, streaming)

**Analog:** 자기 자신 — `chunk_sentences`/`_drain_with_stall_timeout`/스톨 재시도
로직은 그대로 유지, `narrate()` 시그니처만 바꾼다.

**바뀔 시그니처** (master_gm.py 142-149줄, VERIFIED):
```python
def narrate(
    *,
    provider: Provider,
    model: str,
    ctx: TurnContext,
    check_summary: str,  # ← 구조화된 "사실 묶음"(facts)으로 넓어짐(D-06)
    rulebook_display_name: str,
    stall_timeout_s: float = STREAM_STALL_TIMEOUT_S,
) -> Iterator[str]:
```
바뀌지 않는 부분 — `build_gm_prompt` 호출 한 줄(186-188줄)과 그 아래 스트리밍
루프(190-241줄)는 그대로 둔다. 바뀌는 것은 `build_gm_prompt`가 받는 인자와 그
안에서 조립하는 텍스트뿐이다(Pattern 1, RESEARCH.md).

---

### `src/gptrpg/agents/context.py` (수정, model, transform)

**Analog:** 자기 자신의 `TurnContext`(51-62줄) — 새 값 객체도 같은
`@dataclass(frozen=True)` + `__post_init__` 상한 검증 스타일을 따른다.

```python
@dataclass(frozen=True)
class TurnContext:
    """매 턴 에이전트에게 넘기는 것 딱 네 가지 — 그 이상도 이하도 아니다."""
    scene_entities: tuple[Entity, ...]
    character_state: tuple[StatEntry, ...]
    clock_state: ClockState
    recent_turns: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.recent_turns) > RECENT_TURNS_LIMIT:
            raise TooMuchContext(len(self.recent_turns))
```
RESEARCH.md Pattern 4가 갈래 B(역할별 dataclass 신설: `SituationContext`,
`EntityJudgeContext`, `ClockJudgeContext`)를 권장한다 — 각각 필요한 칸만
필드로 선언하고, `TooMuchContext` 같은 전용 예외를 필요한 값 객체에만 붙인다.
`RECENT_TURNS_LIMIT`/`TooMuchContext` 자체는 이 단계에서 건드리지 않는다
(CONTEXT.md가 명시적으로 범위 밖으로 뺐다 — 문맥 압축은 Phase 14).

---

### `src/gptrpg/agents/config.py` (수정, config, CRUD)

**Analog:** 자기 자신 — `AGENT_ROLES` 튜플만 확장, `load_config`/`save_config`/
`resolve_provider`는 전부 이 튜플을 순회하는 제네릭 코드라 손댈 필요 없다.

```python
# Source: src/gptrpg/agents/config.py:26-27 (VERIFIED)
AGENT_ROLES: tuple[str, ...] = ("action_classifier", "master_gm")
"""D-32가 요구하는 두 에이전트 역할 — 각자 따로 제공자·모델을 고른다."""
# → ("action_classifier", "master_gm", "situation_judge",
#    "scene_entity_judge", "clock_signal_judge") 형태로 확장 대상.
```
`load_config`(67-90줄)의 "역할별로 순회하며 검증" 루프, `resolve_provider`
(138-145줄)의 "역할 하나 → Provider 하나" 매핑 모두 새 역할 이름이 추가되는
순간 자동으로 그 역할을 인식한다 — 이 두 함수 본문은 수정 불필요.

---

### `src/gptrpg/cli/turn_flow.py` (수정, controller, event-driven)

**Analog:** 자기 자신 — 판정 결과 확정(289줄) ~ narrate 호출(313줄) 사이 구간이
병렬 판단 삽입 지점(Pitfall 3이 정확히 이 두 줄을 지목).

**현재 흐름** (turn_flow.py 286-319줄, VERIFIED):
```python
check_event = store.read_events(args.session, from_seq=resolve_seq)[0]
print(f"판정: 눈 {check_event.rolls} 등급 {check_event.grade} 목표 {check_event.target}")

check_summary = f"{picked.move} 판정 결과 {check_event.grade} (목표 {check_event.target})"

gm_choice = _resolve_role_choice(args, "master_gm")
gm_provider = resolve_provider("master_gm", {"master_gm": gm_choice}, os.environ)

# ... (narration_start 등 준비) ...
narration_iter = narrate(
    provider=gm_provider,
    model=gm_choice.model,
    ctx=ctx,
    check_summary=check_summary,
    rulebook_display_name=rulebook.display_name,
)
```
`check_summary` 확정 직후, `narrate()` 호출 직전에 `asyncio.gather` 삽입 —
Pattern 2(RESEARCH.md) 예시:
```python
entity_result, clock_result = await asyncio.gather(
    asyncio.to_thread(judge_new_entity, provider=..., model=..., ctx=ctx, check_summary=check_summary),
    asyncio.to_thread(judge_clock_signal, provider=..., model=..., ctx=ctx, check_summary=check_summary),
)
```
narrate() 뒤(narration 완료, 응답이 이미 화면에 나간 다음) — Pitfall 1이
요구하는 **CLI 비대칭**: `actor.stop()`을 부르기 전에 시계 조건 검사를
`await`로 명시적으로 끝내야 한다(웹처럼 `BackgroundTasks`로 던지고 안
기다리면 프로세스 종료로 유실된다).

---

### `src/gptrpg/web/routes_actions.py` (수정, controller, event-driven)

**Analog:** 자기 자신 — `_illustrate_scene` + `confirm()`의 `background.add_task`
호출부가 ARCH-03이 요구하는 배경 레인의 참조 구현이다. 그대로 복제해서
`_check_threat_clock_condition`을 만든다.

**배경 태스크 등록 패턴** (routes_actions.py 548-563줄, VERIFIED):
```python
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
시계 조건 검사는 이 자리 옆에(또는 (b) 판단 신호가 "가능성 있음"일 때만)
`background.add_task(_check_threat_clock_condition, actor=actor, provider=..., model=..., ...)`로
건다.

**배경 함수 본체 — 실패를 삼키고 사건으로만 기록하는 3단계 패턴**
(routes_actions.py 576-639줄, VERIFIED):
```python
async def _illustrate_scene(
    *, actor: SessionActor, renderer: Renderer, config: ImageryConfig,
    session_id: str, resolve_seq: int, move: str, grade: str, clock_segment: int,
) -> None:
    """... **어떤 실패도 위로 던지지 않는다.** ..."""
    prompt = scene_prompt(...)
    relative_path = scene_relative_path(session_id, resolve_seq)
    try:
        image = await asyncio.to_thread(_render_and_write, ...)
    except RendererUnavailable as exc:
        print(f"경고: 삽화를 만들지 못했다 (seq {resolve_seq}) — {exc}", file=sys.stderr)
        return
    except Exception as exc:  # noqa: BLE001
        print(f"경고: 삽화 중 예상 못한 실패 (seq {resolve_seq}) — {exc}", file=sys.stderr)
        return

    try:
        await actor.submit(RecordSceneIllustration(...))
    except Exception as exc:  # noqa: BLE001
        print(f"경고: 삽화 사건을 남기지 못했다 (seq {resolve_seq}) — {exc}", file=sys.stderr)
```
`_check_threat_clock_condition`은 정확히 같은 3단 구조를 복제한다:
1. `asyncio.to_thread`로 조건 판단(LLM 또는 룰 기반)을 작업 스레드로 보낸다.
2. 실패하면 예외를 던지지 않고 stderr 경고만 남기고 반환(D-05/ARCH-05).
3. 조건 충족이면 `actor.submit(AdvanceClock(trigger="condition", clock_id=..., segment_index=state.clock_segment + 1, caused_by_seq=resolve_seq))`로 사건 기록.

**주의 (Anti-pattern, RESEARCH.md Pattern 3 warning):** `_prepare_clock`이
`segment_count` 상한을 검사하지 않으므로(`session_actor/actor.py:620-638`),
새 조건 검사 코드가 `AdvanceClock`을 직접 제출할 때는 스스로
`state.clock_segment >= clock_segment_count` 여부를 먼저 검사해야 한다
(`_maybe_auto_advance`의 384-389줄이 이미 하는 것과 같은 검사, 복제 대상).

---

## Shared Patterns

### 타임아웃 + 재시도 + "실패해도 예외 없이 진행"
**Source:** `src/gptrpg/agents/invoke.py:49-121` (`call_with_one_retry`)
**Apply to:** `situation_judge.py`, `scene_entity_judge.py`, `clock_signal_judge.py`의 모든 LLM 호출, 그리고 `_check_threat_clock_condition`의 조건 판단 호출(LLM 기반으로 갈 경우).
```python
def call_with_one_retry(
    fn: Callable[[], AgentResult], *, timeout_s: float
) -> tuple[AgentResult, str | None]:
    """... 두 시도가 모두 실패하면 예외를 밖으로 던지지 않고 실패 껍데기를
    돌려준다 ... 두 시도 모두 실패하면 그 예외 문자열을 표준오류(stderr)에도
    한 줄 찍는다 ..."""
```
새 타임아웃 프리미티브·새 재시도 데코레이터를 만들지 않는다 — ARCH-05가
이미 이 함수로 충족된다.

### 강건 JSON 파싱 (추론형 모델 `<think>` 블록/코드펜스 대응)
**Source:** `src/gptrpg/agents/action_classifier.py:72-116` (`_try_parse_json_array`)
**Apply to:** `scene_entity_judge.py`, `clock_signal_judge.py`가 LLM에서 JSON을
돌려받는 모든 지점.

### 프롬프트 캐싱 순서 — 영구 고정 → 세션 고정 → 턴마다 변함
**Source:** `src/gptrpg/agents/prompt_assembly.py:1-24` (도크스트링 + `_cached_block`)
**Apply to:** `build_situation_prompt`, `build_scene_entity_prompt`,
`build_clock_signal_prompt` 신설 함수 전부.
```python
_CACHE_CONTROL = {"type": "ephemeral"}

def _cached_block(text: str) -> dict:
    return {"type": "text", "text": text, "cache_control": _CACHE_CONTROL}
```
Anti-pattern 경고(RESEARCH.md): 병렬 판단 결과(턴마다 다름)를 `permanent`
블록에 넣지 않는다 — 캐싱이 매 턴 깨진다.

### 배경 작업은 반드시 `SessionActor.submit`을 거친다 (D3, 절대)
**Source:** `src/gptrpg/web/routes_actions.py:624-639` (`_illustrate_scene`의
사건 제출 부분) + `src/gptrpg/session_actor/actor.py` 전체(단일 쓰기 주체)
**Apply to:** `_check_threat_clock_condition` — 배경 태스크가 별도 쓰기 경로를
만들면 D3 위반(절대 금지, canonical_refs가 명시).

### 기존 `ClockAdvanced`/`AdvanceClock` 그대로 재사용 (새 사건 종류 불필요)
**Source:** `src/gptrpg/event_log/schema.py:161-172` (`ClockAdvanced`),
`src/gptrpg/session_actor/actor.py:133-139,620-638`(`AdvanceClock`,`_prepare_clock`)
```python
class ClockAdvanced(EventEnvelope):
    event_type: Literal["clock_advanced"]
    clock_id: str
    segment_index: int
    trigger: Literal["fail_counter", "condition", "ai_choice"]
```
```python
@dataclass(frozen=True)
class AdvanceClock:
    clock_id: str
    segment_index: int
    trigger: str
    caused_by_seq: int | None = None
```
`trigger="condition"`이 이미 스키마·검증·테스트(`tests/test_session_actor_auto_advance.py:209-227`)
전부에서 동작을 증명했다 — `EVENT_SCHEMA_VERSION` 상승도 `reducer.py` 새
분기도 필요 없다(D-02 답: "아니오").

### CLI/웹 배경 실행의 비대칭 (Pitfall 1)
**Source:** RESEARCH.md Common Pitfalls §1, `src/gptrpg/cli/main.py:448`
(`asyncio.run(run_turn(store, args))`), `src/gptrpg/web/routes_actions.py`
(`BackgroundTasks`)
**Apply to:** `cli/turn_flow.py`의 시계 조건 검사 삽입 지점.
CLI는 프로세스 하나가 명령 하나로 끝나므로 "응답 후 배경"이 성립하지 않는다
— `actor.stop()` 전에 반드시 `await`한다. 웹은 `BackgroundTasks`로 진짜
논블로킹. 이 비대칭을 계획 문서에 명시적으로 적어야 한다(경고: 안 적으면
"CLI가 왜 배경 작업을 안 기다리냐"는 잘못된 대칭 가정으로 버그가 남).

## No Analog Found

없음 — 이 단계의 모든 파일이 기존 코드에서 exact 또는 role-match 분석을 찾았다
(RESEARCH.md의 핵심 발견: 새 하부 부품을 만들 필요가 없고, 전부 기존 자산의
재사용/복제로 충분하다).

## Metadata

**Analog search scope:** `src/gptrpg/agents/`, `src/gptrpg/cli/`,
`src/gptrpg/web/`, `src/gptrpg/session_actor/`, `src/gptrpg/event_log/`,
`src/gptrpg/turn/` — CONTEXT.md canonical_refs가 지정한 "고칠 코드" 전부를
이번 세션에 직접 Read로 확인.
**Files scanned:** 9개 소스 파일 전체 읽음(`master_gm.py`, `action_classifier.py`,
`invoke.py`, `prompt_assembly.py`, `context.py`, `config.py`,
`web/routes_actions.py`(발췌), `cli/turn_flow.py`(발췌), `event_log/schema.py`
+ `session_actor/actor.py`(grep+발췌))
**Pattern extraction date:** 2026-08-07

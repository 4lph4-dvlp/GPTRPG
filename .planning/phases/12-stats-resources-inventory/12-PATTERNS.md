# Phase 12: 능력치 · 자원 변화 · 소지품 - Pattern Map

**Mapped:** 2026-08-17
**Files analyzed:** 21 (신규 1 · 수정 20)
**Analogs found:** 21 / 21 (전부 구조적 유사 모듈이 존재 — "새 파일이라 분석 불가"인 것은 없음)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/gptrpg/rules_core/entities.py` (칸 추가 가능성) | model | transform | 자기 자신(기존 `StatEntry`) | exact — 이미 있는 규율만 따르면 됨 |
| `src/gptrpg/rules_core/reducer.py` (`resource_changed` 분기 + 델타 표) | model/service | event-driven | 자기 자신의 `character_occupied`/`action_classified` 분기(252-282행) | exact |
| `src/gptrpg/rules_core/resource_change.py` (신규) | service (순수 함수) | transform | `rules_core/resolution.py`(`_flat_total`/`UnsupportedModifier`의 순수 계산 + 예외 스타일) | role-match — 신규 모듈이므로 "가장 가까운 형제 모듈" 매칭 |
| `src/gptrpg/rules_core/rulebook.py` (`stat_usage`·`GradeBand.costs` 신설) | model | CRUD(선언 검증) | 자기 자신의 `ResourceAxisDecl`/`GradeBand`/`grade_for_margin`/`require_band` | exact |
| `src/gptrpg/rules_core/dice.py` (`roll_die` 신설) | utility(Protocol) | transform | 자기 자신의 `Roller`/`PercentileRoller` — "기존 프로토콜은 한 글자도 안 고친다, 새 Protocol만 나란히 추가" 관례 | exact |
| `src/gptrpg/event_log/replay_roller.py` (`roll_die` 구현) | utility | streaming(반복자) | 자기 자신의 `roll_tens`/`roll_units`(`_next_roll()` 위임 패턴) | exact |
| `src/gptrpg/session_actor/live_roller.py` (`roll_die` 구현) | utility | event-driven(무작위 생성) | 같은 파일의 기존 `roll_d6`/`roll_tens` 구현(미확인 — 아래 참고) | role-match |
| `src/gptrpg/event_log/schema.py` (판 7→8, `ResourceChanged` 모델) | model/config | event-driven | 자기 자신의 판 6→7 절(`ActionClassified` 도입) — 도크스트링 서술 관례 그대로 | exact |
| `src/gptrpg/session_actor/actor.py` (`ResolveCheck.stat`, 새 Command) | controller(내부) | request-response | 자기 자신의 `ConfirmAction`/`ResolveCheck`/`_EVENT_CLASSES`/`_prepare_resolve_check` | exact |
| `src/gptrpg/web/routes_actions.py` (`ConfirmRequest`에서 `modifiers`/`target` 제거, `confirm()` 보정치 조립) | controller(route) | request-response | 자기 자신(`confirm()` 396-514행, `_parse_modifier` 132행) | exact — 자기 자신을 고치는 계획이므로 "분석 후 삭제/변형" |
| `src/gptrpg/cli/turn_flow.py` (`_parse_modifier` 폐기, `--modifier` 인자 정리) | controller(CLI) | request-response | `web/routes_actions.py`의 대응 구간(짝 파일, 10-05 관례) | exact — 반드시 같은 커밋 |
| `src/gptrpg/web/characters_data.py` (시작값 상수 — 대체로 무변경) | config | CRUD | 자기 자신 | exact |
| `src/gptrpg/rulebooks/dungeonworld_like.py` (stat_usage·결과 목록 선언) | config(룰북 데이터) | CRUD | 자기 자신(`DUNGEONWORLD_RESOURCE_AXES`, `DUNGEONWORLD_GRADE_BANDS`) | exact |
| `src/gptrpg/rulebooks/openquest.py` (stat_usage·결과 목록 선언) | config(룰북 데이터) | CRUD | 자기 자신(`difficulty_modifier()`, 73행 — 이름→숫자 변환 기존 패턴) | exact |
| `src/gptrpg/rulebooks/cairn.py` (소지품 대조 대상 선언) | config(룰북 데이터) | CRUD | 자기 자신(`named_slots`, 45행) | exact |
| `src/gptrpg/rulebooks/openquest_creatures.py` | config(룰북 데이터) | CRUD | `rulebooks/openquest.py` | role-match |
| `src/gptrpg/rulebooks/moves.py` (`default_stat=None` 처리) | model | transform | 자기 자신 | exact |
| `src/gptrpg/turn/context.py` (`build_turn_context`에 `party_state` 신설) | service(조립) | request-response | 자기 자신(`character_stats` 단일 인자 처리부, 35행 부근) | exact |
| `src/gptrpg/agents/prompt_assembly.py` (파티 포맷터 신설) | utility(렌더) | transform | 자기 자신의 `_format_character_state`(196-247행) + `_format_scene_entities`(185-193행) | exact |
| `src/gptrpg/web/routes_characters.py` (지금 값 = 시작값+델타 결합) | controller(route) | CRUD | 자기 자신(`_visible_stats()`, `StatEntryView`) | exact |
| `tests/fixtures/session1_events.jsonl` (신규, TEST-04) | test fixture | batch | `tests/test_event_schema_migration.py`의 `skipif(not path.is_file())` 로컬 DB 스모크 패턴 | role-match — "커밋된 사본" 버전을 새로 만듦 |
| `frontend/src/panes/StatusPane.tsx` (변화 강조 표시, D-19) | component | request-response(폴링) | 자기 자신의 `form` 여섯 분기(87-135행) | exact |
| `frontend/src/panes/ChatPane.tsx` (자원 변화 확인 UI) | component | request-response | 기존 `proposal` 상태 기반 확인 UI(제안 화면 재사용) | role-match |
| `frontend/src/api/types.ts` / `frontend/src/labels.ts` | config(타입/문구) | transform | 기존 `StatEntryView` 대응 타입 · 기존 라벨 사전 | exact |

## Pattern Assignments

### `src/gptrpg/rules_core/reducer.py` (model/service, event-driven)

**Analog:** 자기 자신 — `character_occupied`(252-259행) / `action_classified`(270-282행) 분기

**핵심 패턴 — "표 하나를 딕셔너리로 복사→갱신→`replace`"** (`reducer.py:252-259`):
```python
if event_type == "character_occupied":
    # 점유를 요청하는 명령 자체는 08-02가 만든다 — 이 갈래는 사건 종류만
    # 먼저 열어 둔다. **이 갈래를 빠뜨리면 점유 사건이 하나라도 있는
    # 세션은 폴링마다 UnknownEventType을 맞고 영구히 안 열린다**
    occupied_by = dict(state.occupied_by)
    occupied_by[payload["character_id"]] = payload["browser_id"]
    return replace(state, last_seq=seq, occupied_by=occupied_by)
```
`resource_changed` 분기도 이 모양을 그대로 따른다 — `character_resource_ops: dict[tuple[str, str], tuple[ResourceOp, ...]]`를 `dict(state.character_resource_ops)`로 복사 → `(character_id, axis_name)` 키에 새 연산을 튜플로 이어 붙임 → `replace(state, ..., character_resource_ops=new_dict)`.

**"조용히 넘어가지 않는다" 규율의 근거 주석 (반드시 계획에 인용할 것, `reducer.py:270-276`):**
```python
if event_type == "action_classified":
    # ...
    # **그래도 분기가 있어야 한다:** 이 분기가 없으면 이 종류가 하나라도 있는
    # 세션이 폴링마다 UnknownEventType을 맞고 영구히 안 열린다(08-CONTEXT.md
    # D-06, 이미 여러 번 난 사고 — 이 판 올리기와 이 분기는 반드시 같은 커밋).
```
이 정확한 사고가 244-282행에 **세 번**(`scene_illustrated`, `character_occupied`, `action_classified`) 주석으로 기록되어 있다 — `resource_changed`가 네 번째다. **`schema.py`의 `EVENT_SCHEMA_VERSION` 8 올리기와 이 분기는 반드시 같은 커밋.**

**`UnknownEventType` — 마지막 방어선** (`reducer.py:283`):
```python
raise UnknownEventType(event_type)
```

**`fold()`의 "중간 저장 없음" 규율** (`reducer.py:286-294`, D-08의 "지금 값을 어떻게 만드나" 재량이 이 규율 안에서 움직여야 함):
```python
def fold(session_id: str, pairs: Iterable[tuple[str, Mapping]]) -> GameState:
    """... 중간 저장을 쓰지 않는다 — 언제나 initial_state에서 다시 시작한다 (D-08)."""
    state = initial_state(session_id)
    for event_type, payload in pairs:
        state = apply_event(state, event_type, payload)
    return state
```

---

### `src/gptrpg/rules_core/resource_change.py` (신규, service — 순수 함수)

**Analog:** `rules_core/resolution.py`(`_flat_total`/`UnsupportedModifier`/`Modifier`)

**Import discipline** (`resolution.py:1-7`) — `rules_core` 계층이 실제로 import하는 것은 형제 모듈뿐:
```python
"""2d6 판정 계산 — 순수 함수. 무작위는 Roller를 통해서만 얻는다."""

from collections.abc import Sequence
from dataclasses import dataclass

from gptrpg.rules_core.dice import Roller
from gptrpg.rules_core.grading import DEFAULT_TARGET, Grade, grade_for_total
```
`resource_change.py`도 이 패턴을 그대로 따른다 — `from gptrpg.rules_core.dice import Roller`만, `re`(표준 라이브러리, `.importlinter` contract:1이 금지하지 않음) 외 신규 의존 없음.

**예외 스타일** (`resolution.py:12-20`) — "조용히 건너뛰지 않고 예외로 멈춘다", 사유·식별자를 속성으로 노출:
```python
class UnsupportedModifier(Exception):
    """계산에 반영할 수 없는 수정치 유형이 들어왔을 때 던진다.
    조용히 건너뛰면 합계가 틀린 채로 판정이 끝나고, 그 틀린 값이 기록에
    남아 이후 어디서도 복원되지 않는다 — 그래서 예외로 실패시킨다.
    """
    def __init__(self, modifier_type: str, source: str, resolver: str = "resolve_2d6") -> None:
        super().__init__(...)
        self.modifier_type = modifier_type
        self.source = source
```
신규 `InvalidResourceChange(reason, amount)` 예외도 같은 모양(사유+원본 값을 속성으로).

**튜플 관례** (`resolution.py:39-47`) — `CheckOutcome.modifiers: tuple[Modifier, ...]`처럼, 「축·동작·양」 목록도 `tuple[ResourceChangeDecl, ...]`.

**주사위식 적용 순수 함수 스케치** (RESEARCH.md Code Examples 절, 계획이 그대로 시작점으로 쓸 것):
```python
_DICE_EXPR = re.compile(r"^(?P<sign>[+-]?)(?P<count>\d+)d(?P<sides>\d+)(?P<flat>[+-]\d+)?$")

def roll_amount(roller: Roller, amount: int | str) -> tuple[int, tuple[int, ...]]:
    if isinstance(amount, int):
        return amount, ()
    match = _DICE_EXPR.match(amount)
    if match is None:
        raise InvalidResourceChange(f"주사위식을 해석할 수 없다: {amount!r}")
    ...
    rolls = tuple(roller.roll_die(sides) for _ in range(count))
    return sign * (sum(rolls) + flat), rolls
```

---

### `src/gptrpg/rules_core/dice.py` (utility/Protocol, transform)

**Analog:** 자기 자신 — `PercentileRoller`를 `Roller` 옆에 나란히 추가한 기존 커밋 관례

**패턴** (`dice.py:1-16`):
```python
class Roller(Protocol):
    """1~6 사이 눈 하나를 돌려주는 도구가 갖춰야 할 구조.
    구조적 타이핑(PEP 544)이라 이 클래스를 상속할 필요가 없다 ...
    """
    def roll_d6(self) -> int: ...
```
도크스트링이 스스로 "기존 `Roller`는 한 글자도 고치지 않는다(확장이지 변경이 아니다)"라고 선언한다(`dice.py:21-25`) — `roll_die(sides: int) -> int`는 `Roller` 안에 새 메서드로 추가하거나, `PercentileRoller`와 같은 모양으로 나란히 둘 것.

---

### `src/gptrpg/event_log/replay_roller.py` (utility, streaming)

**Analog:** 자기 자신 — `roll_tens`/`roll_units`가 `roll_d6`과 같은 반복자를 공유하는 패턴

```python
def roll_tens(self) -> int:
    """... `roll_d6`과 **같은 반복자**에서 꺼낸다 — `rolls_from_events`가 만든
    평평한 목록이 기록된 순서 그대로 되먹여져야 하므로, 판정 방식에
    따라 소비 자리를 나누지 않는다."""
    return self._next_roll()
```
`roll_die(sides)`도 **면수를 무시하고** `return self._next_roll()` 한 줄로 끝난다(RESEARCH.md Pattern 3이 이미 확인) — `ReplayRoller`는 구조 변경이 필요 없다.

---

### `src/gptrpg/rules_core/rulebook.py` (model, CRUD)

**Analog:** 자기 자신 — `GradeBand`/`ResourceAxisDecl`/`require_band`

**GradeBand에 세 번째 독립 칸 추가(D-13/D-14)** — 기존 모양(`rulebook.py:37-49`):
```python
@dataclass(frozen=True)
class GradeBand:
    """룰북이 선언하는 등급 밴드 하나 — 이름과 그 이름이 적용되는 조건."""
    name: str
    counts_as_failure: bool
    margin_at_least: int | None = None
    margin_at_most: int | None = None
    requires_doubles: bool | None = None
```
`costs: bool` 신규 칸을 `counts_as_failure`와 나란히(둘 다 독립, D-14) 추가 — 기본값 없이 필수로 두어 "모르는 것을 조용히 기본값으로 넘기지 않는다" 규율을 지킬지, 기존 세 룰북 데이터 전부를 즉시 고칠지는 계획이 판단(마이그레이션 비용 vs 무성의한 기본값의 트레이드오프).

**이름으로 밴드 재조회 — D-13이 안전한 이유** (`rulebook.py:294-299` 부근, `require_band`):
```python
def require_band(bands: tuple[GradeBand, ...], grade_name: str) -> GradeBand:
    """이름으로 밴드를 찾는다. 없으면 `UnknownGradeName`."""
    for band in bands:
        if band.name == grade_name:
            return band
    raise UnknownGradeName(grade_name)
```
이 함수가 `resolve_2d6`(하드코딩 등급 산출)과 `resolve_d100`(룰북 선언 등급 산출)의 차이를 흡수한다 — RESEARCH.md Pattern 4/Pitfall 6이 이미 "이번 단계에서 이 어긋남은 고치지 않는다"고 결론 냈다. 계획에도 이 근거를 그대로 남길 것.

---

### `src/gptrpg/event_log/schema.py` (model/config, event-driven)

**Analog:** 자기 자신 — 판 6→7 절(`ActionClassified` 도입) 서술 관례

```python
EVENT_SCHEMA_VERSION = 7
"""판 6 -> 판 7: `proceed()`(웹)/CLI `no_check` 갈래의 서버 쪽 안전 검사(11-06
rework, T-11-29 — ...)가 사건 형식에 닿았다. 새 사건 종류가 하나 늘었다 —
`ActionClassified`(...). ... 기존 아홉 종류의 칸은 하나도 바뀌지 않았으므로
판 1~6으로 쓰인 기록은 글자 그대로 다시 읽힌다(늘어난 것이 「새 종류」일
뿐이라 옛 기록에는 그 종류의 사건이 없다) — `rules_core/reducer.py`의
`action_classified` 분기는 이 판 올리기와 반드시 같은 커밋이다(08-CONTEXT.md
D-06)."""
```
판 7→8 절도 이 문단 구조(무엇이 바뀌었나 → 새 종류 이름 → 하위 호환 근거 → reducer.py 분기 동일 커밋 선언)를 그대로 복제한다. `GameEvent = Annotated[Union[..., ResourceChanged], Field(discriminator="event_type")]`에 새 클래스를 반드시 추가(Pattern 2 체크리스트 항목 2).

---

### `src/gptrpg/session_actor/actor.py` (controller 내부, request-response)

**Analog:** 자기 자신 — `ConfirmAction`/`ResolveCheck`/`_EVENT_CLASSES`/`_prepare_resolve_check`

`ResolveCheck`에 `stat: str` 신규 칸을 추가(현재 102-122행에 `move`·`modifiers`·`target`·`rulebook_id`·`person_id`·`character_id` 여섯 칸만 있음 — RESEARCH.md가 코드로 확인). `_prepare_resolve_check`가 확인된 캐릭터의 `StatEntry`를 찾아 룰북 `stat_usage`에 따라 `Modifier`/`target`을 조립하는 신규 로직이 이 함수 안에 들어간다(신원·소유권 검증이 이미 이 함수 안에 있으므로 자연스러운 위치, RESEARCH.md Architectural Responsibility Map).

새 `resource_changed` 사건을 내는 Command(예: `RecordResourceChange`)는 `_EVENT_CLASSES` 딕셔너리(253-264행 부근)에 등록하고 `AlreadyResolved`류 멱등 가드 패턴을 재사용 — "재시도가 자원을 두 번 깎으면 안 된다"(D-10 재사용 근거).

---

### `src/gptrpg/web/routes_actions.py` (controller/route, request-response) — D-02의 핵심 지점

**Analog:** 자기 자신(`confirm()`, `_parse_modifier`)

**폐기할 통로 — `_parse_modifier`** (`routes_actions.py:132-146`):
```python
def _parse_modifier(raw: str) -> Modifier:
    """'유형:값:출처' 형태의 수정치 문자열 하나를 `Modifier`로 바꾼다.
    `cli/turn_flow.py`의 `_parse_modifier`와 같은 형식이다 ...
    """
    parts = raw.split(":", 2)
    if len(parts) != 3:
        raise ValueError(f"modifier 형식은 '유형:값:출처'여야 한다: {raw!r}")
    mod_type, raw_value, source = parts
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"modifier 값은 정수여야 한다: {raw!r}") from exc
    return Modifier(type=mod_type, value=value, source=source)
```
**D-02는 이 함수와 `ConfirmRequest.modifiers`/`ConfirmRequest.target`(브라우저가 직접 보내는 자유 숫자, 366-380행)을 닫는 것이 목표다.** 남기는 것은 이름 목록(예: 난이도 이름)뿐 — `_parse_modifier` 자체를 지우고, `ConfirmRequest`에 `difficulty` 같은 닫힌 이름 칸으로 대체.

**신원 대조가 맨 앞 — D-10이 재사용할 자리** (`routes_actions.py:423-425` 부근):
```python
identity = read_identity(request, session_id)
if identity is None or identity.character_id != body.character_id:
    print("경고: 신원 검증 실패 — confirm 거부", file=sys.stderr)
    raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")
```
자원 변화 확인도 **같은 자리·같은 모양**으로 이 검사를 통과한 뒤에만 진행한다.

**멱등성 가드(재사용 판단) — 자원 변화 확인이 올라탈 구조** (`routes_actions.py:461-480` 부근):
```python
try:
    confirm_seq = await actor.submit(ConfirmAction(...))
except AlreadyConfirmed as exc:
    prior_confirm = exc.prior
    confirm_seq = prior_confirm.confirm_seq
except CommandRejected as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
except SequenceConflict as exc:
    raise HTTPException(status_code=409, detail=str(exc)) from exc
```
동일한 `try/except AlreadyResolved/CommandRejected/SequenceConflict` 삼중 구조를 새 `RecordResourceChange` 제출에도 재사용.

---

### `src/gptrpg/cli/turn_flow.py` — 반드시 `routes_actions.py`와 같은 커밋 (Pitfall 2)

**Analog:** `web/routes_actions.py`의 `_parse_modifier`/`confirm()` 대응 구간 (짝 파일)

```python
def _parse_modifier(raw: str) -> Modifier:
    """'유형:값:출처' 형태의 --modifier 문자열 하나를 Modifier로 바꾼다."""
    parts = raw.split(":", 2)
    if len(parts) != 3:
        raise ValueError(f"modifier 형식은 '유형:값:출처'여야 한다: {raw!r}")
    mod_type, value, source = parts
    return Modifier(type=mod_type, value=int(value), source=source)
```
(59행) — 웹 쪽 함수와 도크스트링에서 서로를 명시적으로 지목한다("`cli/turn_flow.py`의 `_parse_modifier`와 같은 형식이다"). `--modifier` 인자(558행 부근, `args.modifier`)도 같은 커밋에서 정리 — **10-05가 세운 "웹과 CLI 두 호출부가 같은 자리·같은 조건으로 움직인다" 관례를 어기면 한쪽만 닫힌 채 남는다는 것이 Pitfall 2의 정확한 서술.**

CLI 신원 모델도 참고: `person_id=args.player, character_id=args.player`(브라우저 쿠키 신원 개념이 없어 두 칸에 같은 값) — D-01/D-02가 CLI 쪽에서도 `stat` 칸을 받되 신원 검증 없이 그대로 캐릭터 데이터를 신뢰하는 기존 전제를 유지.

---

### `src/gptrpg/turn/context.py` (service, request-response) — D-17/D-18

**Analog:** 자기 자신 — `build_turn_context(character_stats=...)`

```python
def build_turn_context(
    store: EventStore,
    session_id: str,
    rulebook_id: str,
    *,
    character_stats: tuple[StatEntry, ...] | None = None,
    character_names: dict[str, str] | None = None,
) -> TurnContext:
    """... 캐릭터 상태는 `character_stats`가 주어지면 그것으로, 아니면
    `EXAMPLE_SINGLE_STAT_FOE.stats`로 채운다 ... 웹 경로는 행동한 사람의
    실제 캐릭터 상태값을 여기로 넘긴다(RIG-05 연장)."""
```
`party_state: tuple[Entity, ...] | None = None` 신규 키워드 인자를 같은 모양(옵션, 기본값 있음)으로 추가 — `character_stats`(행위자 1인)는 그대로 유지하고 `party_state`(넷)를 나란히 둔다(RESEARCH.md Pattern 5 권고).

---

### `src/gptrpg/agents/prompt_assembly.py` (utility/렌더, transform) — D-17/D-18의 실제 분기점

**Analog:** 자기 자신 — `_format_character_state`(196-247행) + `_format_scene_entities`(185-193행)

**여섯 형태 렌더러 — 그대로 재사용, 새로 안 만든다:**
```python
def _format_character_state(stats: tuple) -> str:
    """... 여섯 형태 중 무엇을 어떤 모양으로 넘기고 무엇을 안 넘기는가 ...
    | numeric | "이름 현재값" | ...
    | clock | "이름 현재/최대칸" | ...
    | named_slots | 채워진 칸 이름 나열 + "(빈 칸 N개)" 요약 | 빈 칸 자체 |
    | tag_list | 태그 쉼표 나열 | ...
    | usage_die | "이름 dN", 0이면 "이름 소진" | ...
    | none | 아예 건너뛴다 | 전부(T-11-25) |
    """
    if not stats:
        return "(캐릭터 상태 없음)"
    parts: list[str] = []
    for stat in stats:
        if stat.form == "none":
            continue
        elif stat.form == "numeric":
            parts.append(f"{stat.name} {stat.current}")
        ...
```
**엔티티 여러 개를 이름과 함께 이어 붙이는 기존 모양** (`prompt_assembly.py:185-193`):
```python
def _format_scene_entities(entities: tuple) -> str:
    if not entities:
        return "(장면에 등장한 대상 없음)"
    lines = []
    for entity in entities:
        stats = ", ".join(f"{stat.name} {stat.current}" for stat in entity.stats)
        lines.append(f"- {entity.display_name} ({entity.entity_id}): {stats}")
    return "\n".join(lines)
```
**신규 파티 렌더러**는 이 두 함수를 합친 모양 — 캐릭터마다 `_format_character_state(character.stats)`를 불러 이름과 함께 줄로 잇는다(`_format_scene_entities`가 하는 것과 같은 패턴). `build_classifier_prompt`(367행)와 `build_situation_prompt`(509행)가 지금 **같은 함수** `_session_block_text(ctx)`를 공유하므로, 분류기는 이 함수를 그대로 쓰고 `build_situation_prompt`만 새 `_session_block_text_with_party` 류를 쓰도록 분기(D-17 — "코드가 명시적으로 안 읽는다" 방식, RESEARCH.md A3 확인 필요 사항).

---

### `frontend/src/panes/StatusPane.tsx` (component, request-response/폴링) — D-19

**Analog:** 자기 자신 — 여섯 `form` 분기(87-135행)

```typescript
if (stat.form === "numeric") { ... }
...
if (stat.form === "clock") { ... }
if (stat.form === "named_slots") { ... }
if (stat.form === "tag_list") { ... }
if (stat.form === "usage_die") { ... }
// stat.form === "none": 서버가 이 축을 응답에서 이미 뺐으므로
```
D-19의 변화 강조 표시는 **이 여섯 분기 각각에 조건부 스타일/뱃지를 얹는 방식**으로 구현 — 새 렌더 갈래를 만들지 않는다(RESEARCH.md "기존 여섯 형태 렌더 갈래가 이미 있다, 새 갈래가 아니라 변화 강조만 얹는다"). `stat.form === "none"`은 서버가 `_visible_stats()`로 응답에서 이미 뺀다는 것이 코드 주석으로 확인됨 — 변화 표시 로직도 이 필터 뒤에서만 동작.

## Shared Patterns

### 사건 종류 추가 시 `reducer.py` 분기 동시 커밋 (전 사건 관련 파일에 적용)
**Source:** `src/gptrpg/rules_core/reducer.py:244-283` (세 개의 기존 사고 기록 주석)
**Apply to:** `event_log/schema.py`, `rules_core/reducer.py`, `session_actor/actor.py`
```python
# reducer.py 244-250 — 정확한 문구를 계획 문서에 인용할 것
# 그림 기능을 끄면 낫는 종류의 고장이 아니다 — 이미 기록된 삽화 사건은
# 사라지지 않으므로, 한 번 켰던 세션은 영구히 열리지 않게 된다.
```
계획의 "완료 조건"에 "schema.py diff와 reducer.py diff가 같은 커밋에 있는가"를 리뷰 체크리스트 항목으로 명시할 것(Pitfall 1).

### 웹·CLI 짝 수정 (D-02, 10-05 관례)
**Source:** `web/routes_actions.py:132-146`(`_parse_modifier`) ↔ `cli/turn_flow.py:53-60`(`_parse_modifier`)
**Apply to:** `ConfirmRequest`/CLI `--modifier` 인자를 만지는 모든 계획 태스크
```python
# 두 파일의 _parse_modifier는 도크스트링에서 서로를 직접 지목한다 —
# "cli/turn_flow.py의 _parse_modifier와 같은 형식이다" (routes_actions.py:136)
```
한쪽만 고치는 커밋은 Pitfall 2가 정확히 경고하는 실패 모양이다.

### 신원·점유 재사용 (D-10)
**Source:** `web/routes_actions.py:423-425`
```python
identity = read_identity(request, session_id)
if identity is None or identity.character_id != body.character_id:
    raise HTTPException(status_code=403, detail="캐릭터를 다시 선택해 주세요")
```
**Apply to:** 자원 변화 확인 게이트를 여는 모든 신규 라우트/커맨드 — 새 권한 개념을 만들지 않는다.

### `rules_core` 층 제약 (`.importlinter` contract:1)
**Source:** `rules_core/resolution.py:1`("무작위는 Roller를 통해서만 얻는다"), `rules_core/dice.py`(Protocol만 정의, 구현은 밖)
**Apply to:** `resource_change.py`, `reducer.py` 확장 전체 — `time`/`random`/`secrets`/파일/네트워크 import 금지, 무작위는 반드시 `Roller` 매개변수로 주입받는다.

### 예외는 조용히 넘어가지 않는다 — 사유·식별자를 속성으로
**Source:** `rules_core/entities.py:25-35`(`InvalidStatEntry`), `resolution.py:12-20`(`UnsupportedModifier`), `reducer.py:114-120`(`UnknownEventType`)
```python
class InvalidStatEntry(Exception):
    def __init__(self, reason: str, name: str | None = None) -> None:
        super().__init__(f"상태값 선언이 유효하지 않다: {reason} (name={name!r})")
        self.reason = reason
        self.name = name
```
**Apply to:** `InvalidResourceChange`, `OutOfOrderEvent`(QUAL-01), `CorruptEventRecord`(QUAL-02) 신규 예외 전부 이 모양을 따를 것.

## No Analog Found

없음 — 신규 제안 모듈(`resource_change.py`)도 `resolution.py`를 구조적 형제로 확인했고, 나머지 전부 기존 파일의 확장이라 전 항목에 분석 가능한 코드 근거가 있다.

## Metadata

**Analog search scope:** `src/gptrpg/rules_core/`, `src/gptrpg/event_log/`, `src/gptrpg/session_actor/`, `src/gptrpg/web/`, `src/gptrpg/cli/`, `src/gptrpg/rulebooks/`, `src/gptrpg/turn/`, `src/gptrpg/agents/`, `frontend/src/panes/`, `frontend/src/api/`
**Files scanned (직접 열람):** `reducer.py`, `entities.py`, `dice.py`, `replay_roller.py`, `rulebook.py`, `resolution.py`, `schema.py`, `actor.py`(부분), `routes_actions.py`, `turn_flow.py`(부분), `turn/context.py`(부분), `prompt_assembly.py`(부분), `StatusPane.tsx`(grep)
**Pattern extraction date:** 2026-08-17

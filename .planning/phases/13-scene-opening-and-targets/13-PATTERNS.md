# Phase 13: 장면 — 오프닝과 대상 - Pattern Map

**Mapped:** 2026-08-25
**Files analyzed:** 21 (신규 8 · 수정 13)
**Analogs found:** 21 / 21 — 이 단계는 13-RESEARCH.md가 이미 "이 저장소가 필요한 조각을
전부 갖고 있고 빠진 것은 연결뿐"이라고 확인했다(Don't Hand-Roll 절). 그래서 새 파일 대부분도
"형제 모듈"이 아니라 **자기 자신이 될 파일의 옆자리 기존 모듈**을 그대로 본으로 삼는다.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/gptrpg/web/routes_actions.py` (오프닝 라우트, `declare_seq` 없는 변형) | controller(route) | request-response | 자기 자신 — `proceed()`(1470-1730행) | exact — 세 지점만 다름(위 Pitfall 참고) |
| `src/gptrpg/rules_core/scenario.py` (신규, `ScenarioDecl` frozen dataclass) | model | CRUD(선언 검증) | `rules_core/rulebook.py`의 `Rulebook`(636행~) | exact — D-18이 명시적으로 "같은 모양"을 요구 |
| `src/gptrpg/rulebooks/__init__.py` 또는 신규 `scenarios/__init__.py` (`SCENARIOS` 등록소 + `validate_registered_scenarios`) | config/service(등록시점 검사) | CRUD | `rulebooks/__init__.py`(`RULEBOOKS` 22-25행, `validate_registered_rulebooks` 62행~) | exact |
| `src/gptrpg/rulebooks/threat_clocks.py` → 신규 시나리오 선언 파일로 이관(현재 시나리오) + D-21 신규 낭독문형 시나리오 파일 | config(데이터) | CRUD | `rulebooks/dungeonworld_like.py`류 룰북 데이터 파일(12-PATTERNS.md가 이미 이 role을 "config(룰북 데이터), exact"로 확정) | exact |
| `src/gptrpg/agents/prompt_assembly.py` (`build_opening_situation_prompt` 신설) | utility(프롬프트 조립) | transform | 자기 자신 — `build_situation_prompt`(587-627행) | exact — 별도 함수로 분기(Open Question #1 권장안) |
| `src/gptrpg/turn/context.py` (`scene_entities` 3층 조립 — `THREAT_CAST` 하드코딩 대체) | service(조립) | request-response | 자기 자신 — `party_state` 신설부(12-PATTERNS.md가 이미 "35행 부근, exact"로 확정) | exact — 같은 파일이 12단계에서도 같은 자리를 확장한 전례 |
| `src/gptrpg/agents/action_classifier.py` (`TargetClaim`/`UnknownTarget`, `Proposal`에 대상 칸 추가) | service(AI 출력 파싱) | transform | 자기 자신 — `ItemUseClaim`/`item_use` 칸(95행), `_parse_item_use`(203-229행), `UnknownItemFromAI`(56행) | exact — D-13①의 정확한 선례 |
| `src/gptrpg/agents/scene_entity_judge.py` (변경 없음 — 소비자만 새로 만든다) | service(AI 판단) | transform | 해당 없음 — 이 파일 자체는 완성돼 있다(D-13②) | exact — "고칠 필요 없음"이 곧 분석 결과 |
| `src/gptrpg/web/routes_actions.py` / `session_actor/actor.py` (`judgments.entity.entities`를 사건으로 적립하는 코드, D-13②의 "받는 쪽") | controller/model(event-driven) | event-driven | `rules_core/reducer.py`의 `character_occupied`(402행~)/`action_classified`(420행~) "표를 복사→갱신→replace" 패턴 | exact |
| `src/gptrpg/rules_core/reducer.py` (새 사건 분기 — 명부/확정 목록 적립, Claude's Discretion) | model/service | event-driven | 자기 자신 — `party_roster_locked`(558행), `character_occupied`(402행), `action_classified`(420행) 세 선례 + `UnknownEventType`(246행) 마지막 방어선 | exact |
| `src/gptrpg/event_log/schema.py` (`EVENT_SCHEMA_VERSION` 판올림, 새 사건 종류를 만들 경우) | model/config | event-driven | 자기 자신 — 이전 판올림 절(12-PATTERNS.md가 이미 이 role을 "exact"로 확정, 판 6→7/7→8 서술 관례) | exact |
| `src/gptrpg/rules_core/entities.py` (D-17 옵션① 채택 시 — 변경 없음, 명부는 별도로 둠) | model | transform | `Entity`(166-193행) — 옵션①이면 이 파일 자체는 무변경, 명부는 새 상태 필드/사건으로 | exact(무변경 시) |
| `src/gptrpg/session_actor/actor.py` (오프닝 GM 호출 큐 안 사전검사 신설 — D-03, 기존 네 자리와 함께 고침) | controller(내부) | event-driven | 자기 자신 — `RecordGmSpoke`/`AlreadyGmSpoken`(201-215행 부근), `_prepare_gm_spoke`, `LockPartyRoster`(172행) | exact — 단 "지금 패턴을 복붙하면 D-03이 못 막는다"(Pitfall 1) 주의 |
| `src/gptrpg/web/routes_creation.py` (기존 네 GM 호출 자리 — D-03 수정 대상, 오프닝과 같은 커밋) | controller(route) | request-response | 자기 자신 — `announce_creation()`(740-829행) | exact — 다섯 자리 동시 수정 |
| `src/gptrpg/agents/narration_guard.py` 또는 신규 별도 함수 `inspect_opening_completeness`(D-07/D-08, ⓐ 채택 시 이 파일은 무변경) | service | transform | `inspect_sentence`(218-263행) — Pitfall 4가 "문장 단위 vs 문서 단위"로 구분을 요구 | role-match — D-07ⓐ 채택 시 사용 안 함 |
| `frontend/src/screens/SessionScreen.tsx` (오프닝 호출 트리거 — 마운트 시 `narration_appended` 0건이면 호출) | component | request-response(폴링) | `frontend/src/screens/CreationScreen.tsx`의 GM 호출 폴링 패턴 + `Notices.tsx:54-58`의 `party_roster_locked` 감지 | exact |
| `frontend/src/components/OpeningCard.tsx` (신규 — `.turn` 컨테이너 재사용, `.turn__head`/`.turn__quote` 없이 `.narration p`만) | component | static-content | `frontend/src/components/TurnCard.tsx`(단, `rawText` 필수 전제라 그대로 재사용 못 함 — UI-SPEC "Component Notes" 명시) | role-match — 의도적으로 그대로 안 쓴다 |
| `frontend/src/components/Waiting.tsx` (변경 없음 — `label={COPY.openingWaiting}`로 재사용) | component | static-content | 자기 자신 | exact(무변경) |
| `frontend/src/panes/StatusPane.tsx` (명부 접힌 블록, D-23~D-26) | component | request-response(폴링) | 자기 자신 — 「세션 기록 (진행자용)」 `<details>`(333-355행) + `.party-row`(316-331행) | exact |
| `frontend/src/labels.ts` (`COPY.openingWaiting`/`openingRetry`/명부 관련 문구) | config(문구) | transform | 자기 자신 — 기존 `COPY.creationAnnounceRetry`/`emptyHeading` 대응 항목 | exact |
| `frontend/src/api/types.ts` (오프닝 응답/명부 타입) | config(타입) | transform | 기존 `StatEntryView` 대응 타입(12-PATTERNS.md 선례) | role-match |
| `tests/test_web_actions.py`, `tests/test_action_classifier.py`, `tests/test_scene_entity_judge.py`, 신규 `tests/test_scenario.py` | test | batch | 각 대상 모듈의 기존 테스트 파일(아래 Shared Patterns 「테스트」 참고) | exact |

## Pattern Assignments

### `src/gptrpg/web/routes_actions.py` (오프닝 라우트) — controller, request-response

**Analog:** 자기 자신 — `proceed()`

**신원 검증 + 소유권 재확인 패턴** (`routes_actions.py:1499-1521`):
```python
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
오프닝 라우트는 이 신원 검증을 그대로 상속하되 `declare_seq` 의존(`VerifyProceedEligibility`)을 제거한 변형을 쓴다 — ASVS V4 요구사항(RESEARCH Security Domain)이 이 상속을 명시적으로 요구한다.

**병렬 판단 묶음 호출** (`routes_actions.py:1581-1599`):
```python
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
오프닝은 `check_summary` 자리에 `OPENING_CHECK_SUMMARY`(신설, `NO_CHECK_SUMMARY`와 같은 플랫폼 고정 문자열 상수)를 넣는다.

**서술 조립·호출** (`routes_actions.py:1660-1676`):
```python
facts = build_narration_facts(ctx=ctx, check_summary=NO_CHECK_SUMMARY, judgments=judgments)
narration_iter = narrate(
    provider=gm_provider, model=gm_choice.model, facts=facts,
    rulebook_display_name=rulebook.display_name, resource_axes=rulebook.resource_axes,
)
```
`build_narration_facts`/`narrate` 둘 다 무변경 — `NarrationFacts` 타입을 안 건드리는 것이 ARCH-02를 지키는 핵심(Pitfall 2).

**오프닝이 `proceed()`와 다른 지점은 정확히 셋** (RESEARCH "재사용 대상" 절):
1. `body.declare_seq` 의존 제거
2. `ctx` 조립 시 `recent_turns=()`가 코드 변경 없이 자연히 나온다
3. `gather_turn_judgments` 내부 `judge_situation` 호출의 지시문만 오프닝 전용 갈래로 분기(아래 `prompt_assembly.py` 절)

---

### `src/gptrpg/rules_core/scenario.py` (신규, `ScenarioDecl`) — model, CRUD(선언 검증)

**Analog:** `rules_core/rulebook.py`의 `Rulebook`

**필드 기본값 관례** (`rulebook.py:636-671`):
```python
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
    party_size_range: PartySizeRange | None = None
    """... 기본값 `None`의 뜻은 **「아직 선언하지 않았다」**이고
    「이 룰북에는 그 개념이 없다」가 **아니다** ..."""
```
`ScenarioDecl`은 이 "빈 튜플=개념 없음 vs None=미선언" 구분을 그대로 물려받는다. D-18이 담을 칸: 오프닝(낭독문형/메모형 — `opening_kind: Literal["scripted", "sketch"]`), 즉흥 허용 여부(사람/사물 따로, D-16 — `improv_allowed_people: bool`, `improv_allowed_things: bool`), 등장인물(`Entity` 튜플), 위협 시계 내용. D-22(오프닝은 끌 수 없음, 대상 검사는 끌 수 있음)는 대상 검사 칸에만 `None`/끔 옵션을 둔다.

---

### `src/gptrpg/rulebooks/__init__.py` 대응 (`SCENARIOS` 등록소 + `validate_registered_scenarios`) — config/service

**Analog:** `rulebooks/__init__.py`

```python
# 출처: src/gptrpg/rulebooks/__init__.py:22-25
RULEBOOKS: dict[str, Rulebook] = {
    DUNGEONWORLD_LIKE_ID: DUNGEONWORLD_LIKE,
    OPENQUEST_ID: OPENQUEST,
    CAIRN_ID: CAIRN,
}
```
```python
# 출처: src/gptrpg/rulebooks/__init__.py:62-
def validate_registered_rulebooks() -> None:
    """`RULEBOOKS`에 등록된 각 룰북에 여섯 검사를 돌린다 ...
    위반이 있으면 이 모듈이 임포트되는 순간 예외로 죽는다.
    """
```
`SCENARIOS: dict[str, ScenarioDecl]` + `validate_registered_scenarios()`를 같은 모양으로 만든다 — import 시점 검사(모듈 로드 즉시 실패)가 D-07ⓐ(다섯 요소 등록 시점 구조 검사)의 정확한 메커니즘이다. `imagery/scene_prompt.py:45`의 `WELL_SCENARIO_SETTING` 주석이 이미 "두 번째 시나리오가 생기면 상수를 하나 더 만들어 web이 골라 넘긴다"고 예고해 뒀다 — 이 등록소가 그 예고를 실행한다.

---

### `src/gptrpg/turn/context.py` (3층 대상 조립) — service(조립), request-response

**Analog:** 자기 자신 — `character_stats`/`party_state` 처리부

`scene_entities = THREAT_CAST`(하드코딩, `turn/context.py:130`)를 `SCENARIOS[scenario_id].cast + 확정 목록`(1층+2층)으로 대체한다. 12-PATTERNS.md가 이미 이 파일의 관례("단일 인자 처리부를 확장할 때 기존 함수 시그니처에 새 파라미터를 더한다")를 "exact"로 확정해 뒀다 — `party_state` 신설과 같은 방식으로 `confirmed_entities: tuple[Entity, ...]` 파라미터를 `build_turn_context`에 추가한다.

---

### `src/gptrpg/agents/action_classifier.py` (대상 칸) — service, transform

**Analog:** 자기 자신 — `ItemUseClaim`/`item_use`

**기존 확장 칸** (`action_classifier.py:95`):
```python
item_use: ItemUseClaim = ItemUseClaim(item=None, kind="none")
"""이 행동이 소지품 중 무엇을 쓰는지(RULE-16, 12-06 Task 3) — 새 AI
역할을 만들지 않고 이 분류기 출력에 칸 하나를 더한 것이다 ..."""
```

**닫힌 목록 대조 + 예외 흡수** (`action_classifier.py:203-228`):
```python
def _parse_item_use(raw_text: str, allowed_items: frozenset[str]) -> ItemUseClaim:
    ...
    if value in allowed_items:
        return ItemUseClaim(item=value, kind="held")
    raise UnknownItemFromAI(value)
```

**`Proposal` 조립부의 흡수 처리** (`action_classifier.py:313-347`):
```python
item_use = ItemUseClaim(item=None, kind="none")
try:
    item_use = _parse_item_use(str(result.value), allowed_items)
except UnknownItemFromAI as exc:
    ...
    item_use = ItemUseClaim(item=None, kind="none")
...
return Proposal(candidates=candidates, ai=result, no_check=no_check, item_use=item_use)
```

`TargetClaim(target: str | None, kind: Literal["known", "unknown", "none"])`을 같은 모양으로 만들고, `allowed_items` 자리에 "3층 중 1층+2층"(시나리오 캐스트 + 확정 목록의 `display_name` 집합)을 넣는다. 목록 밖 이름은 `UnknownItemFromAI`와 같은 자리에서 `UnknownTarget`으로 흡수한다 — **AI가 낸 자유 문자열을 신뢰하지 않고 항상 코드가 재대조한다**는 V5 규율(RESEARCH Security Domain)이 이 패턴의 핵심이다.

---

### `src/gptrpg/rules_core/reducer.py` (명부/확정 목록 사건 분기) — model/service, event-driven

**Analog:** 자기 자신 — `character_occupied`/`action_classified`/`party_roster_locked` 세 분기

**"표 하나를 딕셔너리로 복사→갱신→replace" 패턴** (`reducer.py:402-`):
```python
if event_type == "character_occupied":
    occupied_by = dict(state.occupied_by)
    occupied_by[payload["character_id"]] = payload["browser_id"]
    return replace(state, last_seq=seq, occupied_by=occupied_by)
```

**"조용히 넘어가지 않는다" 규율의 근거 주석** (`reducer.py:420-`, 반드시 계획에 인용할 것):
```python
if event_type == "action_classified":
    ...
    # **그래도 분기가 있어야 한다:** 이 분기가 없으면 이 종류가 하나라도 있는
    # 세션이 폴링마다 UnknownEventType을 맞고 영구히 안 열린다(08-CONTEXT.md
    # D-06, 이미 여러 번 난 사고 — 이 판 올리기와 이 분기는 반드시 같은 커밋).
```
이 사고가 이 파일에 이미 **네 번**(`scene_illustrated`/`character_occupied`/`action_classified`/`resource_changed`, 12-PATTERNS.md 확인) 주석으로 기록돼 있다 — 새 명부/확정 목록 사건이 다섯 번째다.

**단순 잠금형 사건의 본** (`reducer.py:558`, D-01 트리거와 같은 모양):
```python
if event_type == "party_roster_locked":
    return replace(state, last_seq=seq, party_roster=tuple(payload["character_ids"]))
```

**마지막 방어선** (`reducer.py:597`):
```python
raise UnknownEventType(event_type)
```
새 사건 종류를 만들면 `event_log/schema.py`의 `EVENT_SCHEMA_VERSION`을 올리고 이 분기를 **같은 커밋**에 낸다(Pitfall 3).

---

### `src/gptrpg/session_actor/actor.py` (오프닝 GM 호출 중복 방지, D-03) — controller(내부), event-driven

**Analog:** 자기 자신 — `RecordGmSpoke`/`AlreadyGmSpoken`/`LockPartyRoster`

**⚠️ 그대로 복붙하면 D-03이 못 막는 패턴** (`web/routes_creation.py:806-826`, 반면교사):
```python
key = _gm_dedupe_key("announce", actor.state)
already_said = actor.state.creation_gm_said.get(key)
if already_said is not None:
    return AnnounceCreationResponse(message=already_said.say, seq=already_said.seq)
# ↑ 큐 밖 사전 검사 — 겹친 요청 둘 다 통과한다.
message = await asyncio.to_thread(announce_requirements, rulebook, provider, model)
# ↑ AI 호출이 여기서 일어난다 — 이미 늦었다.
try:
    seq = await actor.submit(RecordGmSpoke(kind="announce", ...))
except AlreadyGmSpoken as exc:
    # ↑ 사건 중복은 막지만 AI는 이미 두 번 불린 뒤다.
    return AnnounceCreationResponse(message=exc.prior.say, seq=exc.prior.seq)
```
D-03이 요구하는 해법: 큐 밖 사전 검사를 큐 안 검사로 대체(예: `RequestGmSlot`류 명령을 먼저 제출해 슬롯을 얻은 뒤에만 AI를 부른다) 또는 세션당 뮤텍스. **네 기존 GM 호출 자리(announce/nominate/follow_up/wrap_up, `routes_creation.py:787·860·993·1129`) + 오프닝 한 자리가 전부 같은 모양이므로 한 자리를 고치면 다섯 다 닫힌다** — 라우트마다 가드를 반복하지 않는다.

---

### `src/gptrpg/agents/prompt_assembly.py` (`build_opening_situation_prompt`) — utility(프롬프트), transform

**Analog:** 자기 자신 — `build_situation_prompt`

`build_situation_prompt`(587-627행)의 영구 고정 지시문은 "판정 결과와 지금까지의 장면·위협 시계 상태를 보고 ... 이미 정해진 값을 그대로 반영한다"고 명시한다 — 오프닝에는 판정이 없으므로 이 지시문을 그대로 쓰면 안 된다(Pitfall 2). 별도 함수 `build_opening_situation_prompt`를 만들어 지시문만 "판정 결과가 아니라 시나리오가 적어 둔 상황을 읽고, 서술이 첫 장면을 열 때 필요한 것만 뽑는다 — 시나리오 원문을 옮겨 적지 말고 좁혀서 전달한다"로 바꾼다. `judge_situation()` 시그니처(`ctx: TurnContext, check_summary: str`)는 무변경 — `check_summary` 자리에 `OPENING_CHECK_SUMMARY` 상수를 넣는다.

---

## Shared Patterns

### 인증/신원 검증
**Source:** `web/routes_actions.py:1499-1521`(`proceed()`의 `read_identity` + `character_id` 대조 + `VerifyProceedEligibility`)
**Apply to:** 오프닝 라우트(SCENE-01) — 기존 서명 쿠키(`cookie_auth.py`) 재사용, 새 인증 개념 없음(ASVS V2 no, V4 yes)

### 사건 기반 상태(reducer) 패턴
**Source:** `rules_core/reducer.py:402-597`(`character_occupied`/`action_classified`/`party_roster_locked` + `UnknownEventType` 마지막 방어선)
**Apply to:** 명부/확정 목록 사건 분기(SCENE-03/05), 오프닝 기록 사건(SCENE-01) 모두. **"상태는 사건에서 접어 만든다"가 M0의 유일한 되돌릴 수 없는 결정**(Don't Hand-Roll) — 새 상태를 사건 없이 직접 만들지 않는다.

### 닫힌 목록 + 예외 흡수 (AI 출력 검증)
**Source:** `agents/action_classifier.py:56, 203-228, 313-347`(`UnknownItemFromAI`/`_parse_item_use`/`Proposal` 조립부)
**Apply to:** 대상 지목(SCENE-04, `TargetClaim`/`UnknownTarget`), 명부 재사용(SCENE-05, D-19의 "닫힌 목록에서만 고르게 하고 밖이면 잡는다"). SAFE-07이 이미 이 패턴을 저장소 규율로 굳혔다 — 새 예외 계층을 만들지 않고 같은 모양만 반복한다.

### 등록 시점(import-time) 구조 검사
**Source:** `rules_core/rulebook.py:636-671`(필드 기본값 관례) + `rulebooks/__init__.py:22-25, 62-`(등록소 + `validate_registered_rulebooks`)
**Apply to:** `ScenarioDecl`/`SCENARIOS`/`validate_registered_scenarios`(SCENE-02, D-07ⓐ/D-18) — 모듈 import 시점에 위반이 있으면 즉시 예외로 죽는다. 커스텀 JSON 스키마 검증기를 만들지 않는다(Don't Hand-Roll).

### GM 호출 중복 방지 — 큐 안 재검사만으로는 부족함
**Source:** `web/routes_creation.py:806-826`(반면교사 — 사건 중복은 막되 AI 호출 중복은 못 막음) + `.planning/todos/pending/2026-08-23-gm-call-fires-twice-across-tabs.md`
**Apply to:** 오프닝 호출(SCENE-01) + 기존 네 GM 호출 자리. 프런트엔드 완화책(방장 탭만 호출)은 사장님이 명시적으로 거부했다 — 백엔드(큐 안 사전 검사 또는 세션당 뮤텍스) 해법만 유효.

### 프런트 폴링 기반 게이트 전환
**Source:** `frontend/src/App.tsx:76-86`(`"creating"` → `"ready"` 게이트) + `frontend/src/screens/Notices.tsx:54-58`(`party_roster_locked` 감지)
**Apply to:** `SessionScreen`의 오프닝 호출 트리거 — 마운트 시 `narration_appended` 0건이면 오프닝을 부르는 `useEffect`를 기존 `fetchCharacters`/`fetchCharacterSheet`(63-77행) 옆에 추가.

### 기존 CSS/문구 시스템 재사용 (신규 토큰 없음)
**Source:** `frontend/src/styles.css`(어두운 판 토큰 체계), `frontend/src/panes/StatusPane.tsx:316-355`(「세션 기록」 details + `.party-row`), `frontend/src/components/Waiting.tsx`, `frontend/src/labels.ts::COPY`
**Apply to:** 오프닝 카드(`.turn` + `.narration p`만, `.turn__head`/`.turn__quote` 제외), 오프닝 대기(`Waiting` 그대로), 재시도 단추(`.btn--primary`, `CreationScreen.tsx:492-499`와 동일), 명부 블록(`<details className="status-block">` + `.party-row`). 13-UI-SPEC.md의 Component Notes 절이 이미 이 대응을 확정했다 — 새 CSS 클래스·새 컴포넌트 체계를 만들지 않는다.

### 테스트
**Source:** 기존 `tests/test_web_actions.py`(`proceed()` 계열 패턴), `tests/test_rulebook.py`(구조 모델 검사), `tests/test_action_classifier.py`(item_use 패턴), `tests/test_scene_entity_judge.py`
**Apply to:** SCENE-01~05 각각의 신설/확장 테스트 — 13-RESEARCH.md "Wave 0 Gaps" 절이 이미 다섯 개 구체 파일을 지정해 뒀다(`test_scenario.py` 신설 포함). `pytest -q --tb=short -k <키워드>`가 표준 실행 명령.

## No Analog Found

없음 — RESEARCH.md의 "Don't Hand-Roll" 절이 이미 확인한 대로, 이 단계가 새로 만들어야 하는
모든 조각(`ScenarioDecl`, 대상 칸, 명부 사건, 오프닝 지시문 분기)이 저장소 안에 구조적으로
동일한 선례를 가진다. `frontend/src/components/OpeningCard.tsx`만 "새 컴포넌트 파일"이지만
그 내부 마크업조차 기존 `.turn`/`.narration` CSS를 그대로 쓰므로 role-match로 분류했다(위
표 참고) — "분석 불가"로 남긴 파일은 없다.

## Metadata

**Analog search scope:** `src/gptrpg/{web,rules_core,rulebooks,agents,turn,session_actor,event_log,cli}`, `frontend/src/{screens,components,panes,api}`, `tests/`
**Files scanned:** 13-RESEARCH.md의 Sources 절(HIGH confidence, 이 세션에서 직접 읽고 확인한 20+ 파일) 재사용 + 이 세션에서 `rules_core/rulebook.py`·`rulebooks/__init__.py`·`agents/action_classifier.py`·`rules_core/reducer.py`의 실제 줄 번호 재확인(grep)
**Pattern extraction date:** 2026-08-25

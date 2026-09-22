# Phase 11: 룰북 표현 어휘 확장 — 패턴 지도

**Mapped:** 2026-08-15
**Files analyzed:** 21
**Analogs found:** 19 / 21

> 이 문서는 CONTEXT.md/RESEARCH.md가 이미 상세히 확인한 코드 사실을 계획이 바로 오려 쓸 수
> 있는 "분석 대상 파일 ↔ 붙일 패턴" 형태로 재배열한다. RESEARCH.md § Architecture Patterns가
> 이미 코드 근거를 깊게 파놨으므로 이 문서는 중복 설명을 반복하지 않고 **패턴 소스 파일의
> 정확한 위치와 발췌**, 그리고 RESEARCH.md에는 없는 몇 개 파일(`labels.ts`, `routes_characters.py`
> `StatEntryView`, `test_entities.py` 전체 등)의 발췌를 채운다.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/gptrpg/rules_core/rulebook.py` (`ResourceAxisDecl` 신설 + 가려짐/구멍 검증 함수 신설) | model | CRUD(선언 검증) | `GradeBand`/`grade_for_margin` (같은 파일) | exact — 확장 대상 자체가 분석 대상 |
| `src/gptrpg/rules_core/entities.py` (`StatEntry` 6폼 확장) | model | CRUD(값 그릇) | 자기 자신의 현재 `StatEntry`/`InvalidStatEntry` | exact |
| `src/gptrpg/rulebooks/__init__.py` (등록 시점 검증 호출) | service/registry | request-response(조회) | 자기 자신의 `get_rulebook`/`UnknownRulebook` | exact |
| `src/gptrpg/rulebooks/moves.py` (변경 없음 또는 `default_stat` 대조 추가) | config/registry | CRUD | 자기 자신의 `get_moves`/`UnknownRulebook` | exact |
| `src/gptrpg/rulebooks/dungeonworld_like.py` (`resource_axes` 선언 추가) | config | CRUD | `src/gptrpg/rulebooks/openquest.py` (같은 역할, 형제 파일) | exact |
| `src/gptrpg/rulebooks/openquest.py` (`resource_axes` 선언 추가) | config | CRUD | `dungeonworld_like.py` | exact |
| `src/gptrpg/rulebooks/openquest_creatures.py` (`StatEntry` 새 시그니처로 재작성) | config | CRUD | `web/characters_data.py` (같은 `Entity`/`StatEntry` 리터럴 관례) | exact |
| `src/gptrpg/rulebooks/cairn_like.py` (신규, 세 번째 룰북) | config | CRUD | `openquest.py` + `openquest_creatures.py` (판정 방식 다르지만 선언 형식 동일) | role-match |
| `src/gptrpg/web/characters_data.py` (4캐릭터 재작성) | config/service | CRUD | 자기 자신 (D-49 보존 규율 포함) | exact |
| `src/gptrpg/agents/action_classifier.py` (`ProposalTier` 4값) | service | event-driven(LLM 분류) | 자기 자신의 `ProposalTier`/`Proposal`/`classify()` | exact |
| `src/gptrpg/agents/prompt_assembly.py` (D-08 영구 고정 블록 추가) | service | transform(프롬프트 조립) | 자기 자신의 `build_classifier_prompt`의 `permanent` 블록 | exact |
| `src/gptrpg/agents/context.py` (상한 상수 검토) | service | transform | 자기 자신의 기존 `*_LIMIT` 상수들 | exact |
| `src/gptrpg/turn/judgments.py` (`build_narration_facts` 확장) | service | transform | 자기 자신의 `NarrationFacts.check_summary` 조립부 | exact |
| `src/gptrpg/turn/context.py` (D-08 문맥 전달) | service | transform | `agents/context.py`의 상한 규율 | role-match |
| `src/gptrpg/web/routes_actions.py` (`declare`/`confirm` 4값 처리) | controller/route | request-response | 자기 자신의 `declare()`/`confirm()` | exact |
| `src/gptrpg/web/routes_characters.py` (`StatEntryView` 6폼 확장) | controller/route | request-response | 자기 자신의 `StatEntryView`/`CharacterSheetView` | exact |
| `src/gptrpg/cli/turn_flow.py` (`tier` 4값 처리) | controller(CLI) | request-response | `routes_actions.py`의 동형 분기 (짝을 이루는 두 호출부) | exact |
| `frontend/src/panes/StatusPane.tsx` (6폼 렌더링) | component | transform(렌더) | 자기 자신의 `StatRows` 두 갈래 분기 + `ThreatClock.tsx` | exact |
| `frontend/src/components/ThreatClock.tsx` (변경 없음, 재사용) | component | transform(렌더) | — (재사용 대상 자체) | exact |
| `frontend/src/panes/ChatPane.tsx` (tier 4값 UI) | component | event-driven(UI 상태) | 자기 자신의 `tier === "none"` 분기(183행) | exact |
| `frontend/src/labels.ts` (신규 문구) | config(i18n) | — | 자기 자신의 `COPY` 객체(100·104행) | exact |
| `frontend/src/api/types.ts` (`StatEntry`/`tier` 타입 확장) | model(type decl) | — | 자기 자신의 현재 선언(145·171행) | exact |
| `tests/test_rulebook.py` (신규) | test | — | `tests/test_entities.py` (같은 저장소의 순수 도메인 모델 테스트 관례) | role-match — 파일 자체는 신설 |
| `tests/test_entities.py` (재고정) | test | — | 자기 자신의 `test_stat_entry_field_names_are_exactly_four`(25행) | exact |
| `tests/test_action_classifier.py` (4갈래 확장) | test | — | 자기 자신의 기존 tier 테스트(64-88행) | exact |
| `tests/test_web_characters.py` (RULE-12 없음-축 제외 검증, 존재 여부 계획 단계가 재확인) | test | — | 미확인 — 없음 대안: `test_entities.py` | 없음(파일 존재 미확인) |

## Pattern Assignments

### `src/gptrpg/rules_core/rulebook.py` — `ResourceAxisDecl` 신설 + 밴드 가려짐/구멍 검증

**Analog:** 같은 파일의 `GradeBand`/`grade_for_margin`/`NoMatchingGradeBand`

**판별 필드 + 선택적 페이로드 패턴** (`rulebook.py:19-31`):
```python
@dataclass(frozen=True)
class GradeBand:
    name: str
    counts_as_failure: bool
    margin_at_least: int | None = None
    margin_at_most: int | None = None
    requires_doubles: bool | None = None
```
`ResourceAxisDecl`은 이 모양을 그대로 따른다 — `name`(룰북 어휘) + `form`(판별 필드, 6종 enum) + 폼별 선택 필드.

**예외 관례 — "조용히 넘기지 않고 그 자리에서 예외"** (`rulebook.py:44-56`, `58-66`):
```python
class NoMatchingGradeBand(Exception):
    """어느 밴드의 제약도 만족하지 않는 margin/doubles 조합이 나왔을 때 던진다.

    조용히 None이나 기본 등급을 돌려주면 틀린 등급이 기록에 남고 이후 어디서도
    복원되지 않는다 — `UnsupportedModifier`/`UnknownEventType`이 세운 규율과
    같은 이유로 예외로 실패시킨다.
    """
    def __init__(self, margin: int, is_doubles: bool) -> None:
        super().__init__(f"margin={margin}, is_doubles={is_doubles}에 맞는 등급 밴드가 없다")
        self.margin = margin
        self.is_doubles = is_doubles
```
D-15의 등록 시점 「가려짐/구멍」검증도 이 이름 짓기 관례(`~하지 않으면 무슨 예외`)와 독스트링에
"왜 예외로 멈추는가"를 한 문장 박아 넣는 관례를 그대로 따른다.

**선언 순서 = 우선순위 (D-15 근거 원문)** (`rulebook.py:69-84`):
```python
def grade_for_margin(margin: int, is_doubles: bool, bands: tuple[GradeBand, ...]) -> GradeBand:
    for band in bands:
        if band.margin_at_least is not None and margin < band.margin_at_least:
            continue
        if band.margin_at_most is not None and margin > band.margin_at_most:
            continue
        if band.requires_doubles is not None and is_doubles != band.requires_doubles:
            continue
        return band
    raise NoMatchingGradeBand(margin, is_doubles)
```
가려짐/구멍 검증 함수는 이 "첫 매치 승리" 규칙을 정확히 재현하는 스윕 알고리즘이어야 한다
(구체 알고리즘·2세계 분해·기존 두 룰북 손 시뮬레이션 결과는 RESEARCH.md § Pattern 3 참조 —
이미 통과 확인됨, 재확인 불필요).

**신설 `StatEntry` 6폼 확장 모양** (RESEARCH.md § Pattern 1이 이미 구체 코드로 제시):
```python
StatEntryForm = Literal["numeric", "clock", "named_slots", "tag_list", "usage_die", "none"]

@dataclass(frozen=True)
class StatEntry:
    name: str
    form: StatEntryForm
    current: int | None = None
    max: int | None = None
    depleted_effect_ref: str | None = None
    slot_values: tuple[str | None, ...] | None = None
    tags: tuple[str, ...] | None = None
    none_kind: Literal["discretionary", "absent"] | None = None
```

---

### `src/gptrpg/rules_core/entities.py` — 현재 4칸 `StatEntry`/`InvalidStatEntry`

**Analog:** 자기 자신 (D-03 재고정 대상)

**현재 전문** (`entities.py:39-61`):
```python
@dataclass(frozen=True)
class StatEntry:
    name: str
    current: int
    max: int | None = None
    depleted_effect_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidStatEntry("name이 비었거나 공백뿐이다", name=self.name)
        if self.max is not None and self.max < 0:
            raise InvalidStatEntry("max가 음수다", name=self.name)
        if self.depleted_effect_ref is not None and not self.depleted_effect_ref.strip():
            raise InvalidStatEntry("depleted_effect_ref가 빈 문자열이다", name=self.name)
```
**신설 검증 패턴(Pitfall 1 대응):** `__post_init__`을 확장해 "지금 `form`에 허용되지 않은
필드가 채워져 있으면 `InvalidStatEntry`"를 추가한다 — 새 예외 클래스를 만들지 않고 기존
`InvalidStatEntry(reason, name)` 시그니처를 그대로 재사용.

**고정 상수(재고정 대상)** (`entities.py:93-96`):
```python
STAT_ENTRY_FIELD_NAMES = frozenset(f.name for f in fields(StatEntry))
ENTITY_FIELD_NAMES = frozenset(f.name for f in fields(Entity))
```

---

### `src/gptrpg/rulebooks/__init__.py` — 등록소 + 예외 관례

**Analog:** 자기 자신

**현재 전문** (`rulebooks/__init__.py:1-31`):
```python
RULEBOOKS: dict[str, Rulebook] = {
    DUNGEONWORLD_LIKE_ID: DUNGEONWORLD_LIKE,
    OPENQUEST_ID: OPENQUEST,
}

class UnknownRulebook(Exception):
    def __init__(self, rulebook_id: str) -> None:
        super().__init__(f"등록되지 않은 룰북: {rulebook_id!r}")
        self.rulebook_id = rulebook_id

def get_rulebook(rulebook_id: str) -> Rulebook:
    rulebook = RULEBOOKS.get(rulebook_id)
    if rulebook is None:
        raise UnknownRulebook(rulebook_id)
    return rulebook
```
**중요:** `RULEBOOKS` 딕셔너리는 **모듈 임포트 시점에 정적으로 구성**된다 — "등록 함수"를 부르는
자리가 따로 없다(RESEARCH.md 확인). D-02(`resource_axes` 필수 필드)는 `Rulebook(...)` 생성자
호출 자체에서 `TypeError`로 강제되므로 이 파일을 고칠 필요가 없을 수 있다. D-15(가려짐/구멍
검증)는 이 딕셔너리 구성 직후 검증 루프를 돌리거나, `register_rulebook()` 명시적 함수로
바꾸는 두 갈래 중 계획이 선택해야 한다(RESEARCH.md Pattern 3 끝부분).

---

### `src/gptrpg/rulebooks/moves.py` — `MoveDecl`/`get_moves` (변경 최소, 대조 참고용)

**Analog:** 자기 자신

**전문 발췌** (`moves.py:16-24`, `163-168`):
```python
@dataclass(frozen=True)
class MoveDecl:
    move_id: str
    display_name: str
    default_stat: str
    trigger: str

def get_moves(rulebook_id: str) -> tuple[MoveDecl, ...]:
    moves = MOVE_CATALOGS.get(rulebook_id)
    if moves is None:
        raise UnknownRulebook(rulebook_id)
    return moves
```
`default_stat`은 문자열로 자원 축을 가리킬 뿐 대조하지 않는다(RESEARCH.md Integration Points) —
`resource_axes` 목록이 생기면 등록 시점에 `default_stat`이 실재하는 축 이름인지 대조할 수 있다.
이 대조를 이번에 넣을지는 계획의 판단.

---

### `src/gptrpg/rulebooks/dungeonworld_like.py` / `openquest.py` / `openquest_creatures.py`

**Analog:** 서로가 서로의 analog — 같은 형식의 형제 파일들

RESEARCH.md § Pattern 3에 두 룰북의 `GradeBand` 선언 전문이 이미 있다:
```python
# dungeonworld_like.py:19-23
DUNGEONWORLD_GRADE_BANDS: tuple[GradeBand, ...] = (
    GradeBand(name="strong_hit", counts_as_failure=False, margin_at_least=0),
    GradeBand(name="weak_hit", counts_as_failure=False, margin_at_least=-WEAK_HIT_BAND),
    GradeBand(name="miss", counts_as_failure=True),
)
```
```python
# openquest.py:15-20
OPENQUEST_GRADE_BANDS: tuple[GradeBand, ...] = (
    GradeBand(name="critical", counts_as_failure=False, margin_at_least=0, requires_doubles=True),
    GradeBand(name="success", counts_as_failure=False, margin_at_least=0),
    GradeBand(name="fumble", counts_as_failure=True, margin_at_most=-1, requires_doubles=True),
    GradeBand(name="failure", counts_as_failure=True),
)
```
`resource_axes` 신규 선언을 이 옆에 같은 파일, 같은 위치(밴드 선언 다음)에 추가한다.
`openquest_creatures.py`의 크리처 `Entity`/`StatEntry` 리터럴은 아래 `characters_data.py`
패턴을 analog로 삼는다(같은 리터럴 선언 관례).

---

### `src/gptrpg/rulebooks/cairn_like.py` (신규 — 세 번째 룰북)

**Analog:** `openquest.py` + `openquest_creatures.py` (선언 형식은 동일, 판정 방식만 다름)

D-14가 요구하는 것은 "플랫폼 코드를 안 고치고 데이터만으로 등록"이다 — 즉 이 파일은 기존
두 룰북과 **정확히 같은 `Rulebook`/`GradeBand`/`MoveDecl`/`Entity` 조합**으로 짜여야 하고,
`move_triggers`(`MOVE_CATALOGS`)는 **빈 튜플**을 등록해 RULE-15(빈 목록이 정상값)를 실증한다.
`resource_axes`는 `named_slots` 폼(10슬롯 인벤토리)을 최소 하나 포함해야 한다(RESEARCH.md
Cairn SRD 조사 결과).

---

### `src/gptrpg/web/characters_data.py` — `Entity`/`StatEntry` 리터럴 재작성

**Analog:** 자기 자신 (D-49 보존 규율)

**현재 전문 발췌 — bram** (`characters_data.py:48-71`):
```python
"bram": Entity(
    entity_id="player.bram",
    display_name="브람",
    rulebook_id=DUNGEONWORLD_LIKE_ID,
    stats=(
        StatEntry(
            name="체력",
            current=20,
            max=20,
            depleted_effect_ref="dungeonworld_like.hp_depleted",
        ),
        StatEntry(name="STR", current=2),
        ...
        StatEntry(name="방어구", current=2),
    ),
),
```
재작성 시 `current=20, max=20` 같은 수치는 그대로 두고 `form="numeric"`만 추가하는 것이
D-49("수치를 그대로 보존한다")를 지키는 최소 변경이다. 이 파일 도크스트링(1-19행)이 이미
"수치를 다시 계산하거나 재배치하지 않는다"를 명시하고 있으므로 같은 규율 문장을 새 필드
추가 커밋 메시지/주석에도 반복한다.

---

### `src/gptrpg/agents/action_classifier.py` — `ProposalTier` 4값 확장

**Analog:** 자기 자신

RESEARCH.md § Pattern 2에 이미 검증된 확인 사항:
```python
# action_classifier.py:19-21 (현재)
ProposalTier = Literal["single", "several", "none"]
```
`Proposal.tier`는 `len(self.candidates)`만으로 계산되는 읽기 전용 property(`68-76행`) — 4값
확장 시 `no_check`/`unclear` 두 신호를 후보 개수만으로는 구분 못하므로 별도 필드(모델이 낸
"판정 불필요" 신호, 또는 `disposition` 필드)와 조합해 파생시켜야 한다.

**SAFE-07 흡수 경로 — `"unclear"`로만 가야 하는 근거** (`action_classifier.py:169-183`):
```python
Proposal(candidates=(), ai=result, unknown_move=exc.move_id)
```
`candidates=()`이므로 자동으로 `"unclear"`(구 `"none"`)가 되어야 한다 — 절대 `"no_check"`와
혼동되면 안 된다(RESEARCH.md 명시).

---

### `src/gptrpg/agents/prompt_assembly.py` — D-08 영구 고정 블록

**Analog:** 자기 자신의 `build_classifier_prompt`

RESEARCH.md § Pattern 4가 이미 정확한 위치를 특정: `permanent` 문자열, `_format_moves(moves)`가
붙는 바로 그 층(`build_classifier_prompt`는 `prompt_assembly.py:222`,
`f"무브 목록:\n{_format_moves(moves)}\n\n{NOT_AN_INSTRUCTION_LINE}"`). D-08 문장은 이 옆에
같은 영구 고정 블록(`_cached_block(permanent)`)에 추가한다 — 세션/턴 고정 블록에 넣지 않는다
(캐싱 순서 규약 위반).

---

### `src/gptrpg/web/routes_actions.py` / `src/gptrpg/cli/turn_flow.py` — 두 호출부 나란히 비교

**Analog:** 서로가 서로의 analog (10-05가 세운 "같이 안 바뀌면 사고" 관례)

**웹 — `declare()`/`confirm()`** (`routes_actions.py:332-336`, `339-352`, `495-496`):
```python
# tier 그대로 전달
DeclareResponse.tier: str  # proposal.tier

# confirm()은 move/stat을 필수로 요구
class ConfirmRequest(BaseModel):
    move: str = Field(min_length=1, ...)
    stat: str = Field(min_length=1, ...)

# check_summary는 ResolveCheck 이후에만 만들어진다
check_event = store.read_events(session_id, from_seq=resolve_seq)[0]
check_summary = f"{body.move} 판정 결과 {check_event.grade} (목표 {check_event.target})"
```

**CLI — `_turn_flow()`** (`turn_flow.py:284-289`):
```python
if tier == "none":
    print("무브 없음 — 판정 없이 진행합니다. ...")
    return 0  # narrate() 호출 없이 함수 종료
```

**결론(계획이 반드시 알아야 함):** 오늘 CLI/웹 둘 다 "판정 없이 서술이 이어진다"를 실제로
구현하지 않는다 — CLI는 메시지만 찍고 끝내고, 웹은 확인 버튼(`ChatPane.tsx`)이 「다시 쓰기」로
빠진다. `no_check` 갈래를 만들려면 `confirm()`의 move/stat 필수 요구, `check_summary`의
`ResolveCheck` 전제, 두 호출부 전부를 **같은 커밋에서** 함께 바꿔야 한다.

---

### `src/gptrpg/web/routes_characters.py` — `StatEntryView` 확장

**Analog:** 자기 자신

**현재 전문** (`routes_characters.py:57-72`):
```python
class StatEntryView(BaseModel):
    """`StatEntry`의 네 칸 그대로 — 칸 이름을 한 글자도 다르게 짓지 않는다."""
    name: str
    current: int
    max: int | None = None
    depleted_effect_ref: str | None = None

class CharacterSheetView(BaseModel):
    """`Entity`의 네 칸 그대로 — 칸 이름을 한 글자도 다르게 짓지 않는다."""
    entity_id: str
    display_name: str
    rulebook_id: str
    stats: list[StatEntryView]
```
"칸 이름을 한 글자도 다르게 짓지 않는다"는 관례를 그대로 지켜 6폼 필드를 pydantic으로 옮긴다.
**Pitfall 2 대응(RULE-12 성공 기준 2):** `form == "none"`인 축은 이 응답 조립 단계 —
`CharacterSheetView`를 만드는 곳(이 파일의 캐릭터 시트 핸들러) — 에서 **제외**해야 한다.
프론트엔드가 숨기는 방식이면 안 된다(서버가 안 보내야 "완전히 사라진다"가 검증 가능).

---

### `frontend/src/panes/StatusPane.tsx` — 두 갈래 렌더 → 여섯 갈래로 확장

**Analog:** 자기 자신의 `StatRows` + `frontend/src/components/ThreatClock.tsx`

**현재 두 갈래 분기 전문** (`StatusPane.tsx:28-58`):
```tsx
function StatRows({ sheet }: { sheet: CharacterSheet }) {
  return (
    <>
      {sheet.stats.map((stat) =>
        stat.max === null ? (
          <div className="stat-row" key={stat.name}>
            <span className="stat-row__name">{statLabel(stat.name)}</span>
            <span className="stat-row__value">
              {stat.current > 0 ? `+${stat.current}` : stat.current}
            </span>
          </div>
        ) : (
          <div className="stat-gauge" key={stat.name}>
            <div className="stat-gauge__head">
              <span className="stat-row__name">{statLabel(stat.name)}</span>
              <span className="stat-row__value">
                {stat.current}/{stat.max}
              </span>
            </div>
            <div className="gauge">
              <div
                className="gauge__fill"
                style={{
                  width: `${Math.max(0, Math.min(100, (stat.current / stat.max) * 100))}%`,
                }}
              />
            </div>
          </div>
        ),
      )}
    </>
  );
}
```
현재 분기는 `stat.max === null`이라는 **암묵적** 판별(상한 없으면 숫자, 있으면 게이지)이다 —
6폼 확장 후에는 명시적 `stat.form` 판별 필드로 바뀐다. `stat.max === null` 갈래가
`form === "numeric"`, `stat.max`가 있는 갈래는 그대로 유지, 나머지 넷(`clock`/`named_slots`/
`tag_list`/`usage_die`)이 새 분기로 추가된다. `form === "none"`은 **서버가 이미 안 보냈으므로
프론트는 이 분기를 아예 만들 필요가 없다**(Pitfall 2 참조).

**세그먼트 원 재사용 — `ThreatClock.tsx` props** (`ThreatClock.tsx:12-17`):
```tsx
interface ThreatClockProps {
  segment: number;
  segmentCount: number;
  size?: number;
  pulsing?: boolean;
}
```
`form === "clock"`일 때 `stat.current`/`stat.max`를 그대로 `segment`/`segmentCount`에
매핑하면 새 컴포넌트 없이 재사용 가능(RESEARCH.md가 이미 확인).

---

### `frontend/src/panes/ChatPane.tsx` — `tier === "none"` 분기 확장

**Analog:** 자기 자신 (183행)

**현재 전문** (`ChatPane.tsx:181-198`):
```tsx
{proposal !== null ? (
  <div className="proposal">
    {proposal.tier === "none" ? (
      <>
        <p className="t-label">{COPY.noActionRecognized}</p>
        <button type="button" className="btn btn--ghost btn--wide" onClick={() => setProposal(null)}>
          {COPY.reject}
        </button>
      </>
    ) : (
      <>
        <p className="t-caps">
          {proposal.tier === "single" ? "이 판정으로 진행할까요" : "어느 쪽인가요"}
        </p>
        {proposal.candidates.slice(0, 3).map((candidate) => (
          ...
        ))}
      </>
    )}
  </div>
) : null}
```
4값 확장 후: `tier === "unclear"`만 지금의 `"none"` 분기(다시 쓰기)로 가고, `tier === "no_check"`는
새 분기 — 후보 버튼 없이 "판정 없이 진행" 안내 + 진행 버튼(또는 자동 진행)으로 간다. 파일 상단
독스트링(8행 근처 "확인 버튼을 누르는 것만이 판정으로 가는 유일한 통로다")도 `no_check` 갈래를
반영해 갱신 필요.

---

### `frontend/src/labels.ts` — 새 문구

**Analog:** 자기 자신의 `COPY` 객체

**현재 관련 항목** (`labels.ts:100`, `104`):
```typescript
noActionRecognized: "인식된 행동이 없어요. 다른 문장으로 다시 말해 보세요",
...
reject: "다시 쓰기",
```
같은 `COPY` 객체 안에 `no_check`용 새 키(예: `noCheckNeeded: "판정 없이 진행합니다"`)를
같은 스타일(짧은 안내문, 존댓말 종결)로 추가한다.

---

### `frontend/src/api/types.ts` — `StatEntry`/`tier` 타입 확장

**Analog:** 자기 자신

**현재 선언** (`types.ts:145`, `171`):
```typescript
export interface StatEntry {
  // 145행 인근, 4칸
}
...
tier: "none" | "single" | "several";
```
`tier`를 `"none" | "single" | "several" | "no_check" | "unclear"`(또는 `"none"`을 완전히
`"unclear"`로 리네임)로 넓히고, `StatEntry`는 `form` 판별 필드 + 6폼 선택 필드로 넓힌다 —
백엔드 `StatEntryView`(pydantic)와 필드명이 한 글자도 다르지 않아야 한다(저장소 관례).

---

### `tests/test_entities.py` — 고정 시험 재작성 (D-03 필수)

**Analog:** 자기 자신 (25행)

**현재 전문 — 재작성 대상** (`test_entities.py:25-28`):
```python
def test_stat_entry_field_names_are_exactly_four():
    """체력·피해·태그 같은 칸이 하나도 없다는 구조적 증거 — 완전 일치, 부분집합이 아니다."""
    names = {f.name for f in dataclasses.fields(StatEntry)}
    assert names == {"name", "current", "max", "depleted_effect_ref"}
```
재작성 방향(RESEARCH.md § Validation Architecture가 이미 확정): 함수명을
`test_stat_entry_field_names_are_exactly_eight`로 바꾸고 8칸 집합(`{"name","form","current",
"max","depleted_effect_ref","slot_values","tags","none_kind"}`)을 단언한다. **삭제하지
않는다** — 이 시험의 목적은 "몰래 칸이 늘면 즉시 드러난다"이지 칸 개수 자체가 아니다.
`test_entity_field_names_are_exactly_four`(31행)는 `Entity`가 안 바뀌므로 그대로 둔다.

---

### `tests/test_rulebook.py` (신규)

**Analog:** `tests/test_entities.py` (같은 저장소의 "순수 도메인 모델 + import는 `dataclasses`/
`pytest`/`rules_core`/`rulebooks`만" 관례)

이 파일은 현재 존재하지 않는다(`grep -n "def test_" tests/test_grading_d100.py`가 밴드 시험을
간접적으로만 갖고 있다는 것을 RESEARCH.md가 확인). `test_entities.py`의 import 스타일
(`from gptrpg.rules_core.entities import ...`, `from gptrpg.rulebooks.dungeonworld_like import ...`)
과 함수명 패턴(`test_<subject>_<condition>`)을 그대로 따른다. RESEARCH.md § Validation
Architecture 표가 이 파일에 들어갈 정확한 테스트 함수 이름 목록(`missing_resource_axes`,
`empty_move_list_is_valid`, `existing_rulebooks_pass_validation`, `shadowed_band_rejected`,
`hole_rejected`, `simple_overlap_is_legal`, `third_rulebook`)을 이미 확정했다.

---

## Shared Patterns

### 예외 우선 검증 (조용히 기본값으로 넘기지 않는다)
**Source:** `src/gptrpg/rules_core/rulebook.py:44-66`(`NoMatchingGradeBand`, `UnknownGradeName`),
`src/gptrpg/rulebooks/__init__.py:13-22`(`UnknownRulebook`), `src/gptrpg/rules_core/entities.py:13-36`
(`InvalidStatEntry`, `InvalidEntity`)
**Apply to:** `rulebook.py`의 신규 D-02/D-15 검증, `entities.py`의 `StatEntry.__post_init__` 확장
```python
class SomeNewError(Exception):
    def __init__(self, ...) -> None:
        super().__init__(f"...")
        self.field = value
```
모든 새 검증 실패는 이 이름 짓기(`Unknown*`/`Invalid*`/`NoMatching*`)와 독스트링에 "조용히
넘기면 무엇이 망가지는가"를 한 문장 적는 관례를 따른다.

### 웹/CLI 두 호출부 동시 반영
**Source:** `src/gptrpg/web/routes_actions.py`, `src/gptrpg/cli/turn_flow.py`
**Apply to:** `action_classifier.py`의 4값 tier를 소비하는 모든 지점
같은 조건(`tier == "..."`)이 두 파일에 각각 등장하면 반드시 같은 커밋에서 함께 바뀐다 — 이
저장소의 알려진 실패 모양(10-05가 세운 관례).

### 이름/형태 분리 — "룰북 어휘" vs "플랫폼 어휘"
**Source:** `src/gptrpg/rules_core/rulebook.py:1-3` 도크스트링, `GradeBand.name` vs
`margin_at_least`/`margin_at_most`
**Apply to:** `ResourceAxisDecl.name`(룰북이 짓는 이름) vs `.form`(플랫폼이 아는 6종 enum) —
`rules_core`는 "체력"이라는 이름을 몰라야 한다.

### 순수 데이터클래스 + 수제 `__post_init__` (외부 검증 라이브러리 금지)
**Source:** `rules_core` 전역(`entities.py`, `rulebook.py`)
**Apply to:** 신규 `ResourceAxisDecl`, `StatEntry` 확장 — pydantic 등 새 의존 도입 금지
(`.importlinter` contract:1, `rules_core`는 시간·무작위·파일·네트워크 불가).

### 「칸 이름을 한 글자도 다르게 짓지 않는다」— 응답 계약 정합
**Source:** `src/gptrpg/web/routes_characters.py:58`, `67` 독스트링
**Apply to:** `StatEntryView`(pydantic) ↔ `frontend/src/api/types.ts`의 `StatEntry` — 필드명이
백엔드/프론트엔드에서 완전히 동일해야 한다.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `src/gptrpg/rulebooks/cairn_like.py` | config | CRUD | 세 번째 룰북 데이터 자체는 신규 콘텐츠(Cairn SRD 번역) — 형식은 `openquest.py`를 analog로 쓰되 내용은 새로 조사한 SRD 수치이므로 "정확한 analog"는 없음 |
| `tests/test_web_characters.py` | test | request-response | 이 파일의 실존 여부와 현재 커버리지를 이번 세션에서 직접 확인하지 못했다(RESEARCH.md Wave 0 Gaps가 동일하게 명시) — 계획 단계가 먼저 `ls tests/test_web_characters.py`로 확인할 것 |

## Metadata

**Analog search scope:** `src/gptrpg/rules_core/`, `src/gptrpg/rulebooks/`, `src/gptrpg/web/`,
`src/gptrpg/cli/`, `src/gptrpg/agents/`, `src/gptrpg/turn/`, `frontend/src/panes/`,
`frontend/src/components/`, `frontend/src/api/`, `tests/`
**Files scanned:** 이번 세션 직접 Read 12개(`entities.py`, `rulebook.py`, `rulebooks/__init__.py`,
`moves.py`, `characters_data.py`, `routes_characters.py`(부분), `StatusPane.tsx`(부분),
`ChatPane.tsx`(부분), `labels.ts`(grep), `api/types.ts`(grep), `test_entities.py`(부분)) +
RESEARCH.md가 이전에 직접 읽어 `[VERIFIED]`로 인용한 나머지(`action_classifier.py`,
`prompt_assembly.py`, `context.py`, `routes_actions.py`, `turn_flow.py`, `dungeonworld_like.py`,
`openquest.py`, `ThreatClock.tsx`)
**Pattern extraction date:** 2026-08-15

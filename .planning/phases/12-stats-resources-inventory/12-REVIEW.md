---
phase: 12-stats-resources-inventory
reviewed: 2026-08-18T00:00:00Z
depth: standard
files_reviewed: 34
files_reviewed_list:
  - src/gptrpg/rules_core/rulebook.py
  - src/gptrpg/rules_core/resource_change.py
  - src/gptrpg/rules_core/reducer.py
  - src/gptrpg/rules_core/resolution.py
  - src/gptrpg/rules_core/dice.py
  - src/gptrpg/event_log/schema.py
  - src/gptrpg/event_log/replay_roller.py
  - src/gptrpg/session_actor/actor.py
  - src/gptrpg/session_actor/live_roller.py
  - src/gptrpg/web/routes_actions.py
  - src/gptrpg/web/routes_characters.py
  - src/gptrpg/agents/outcome_picker.py
  - src/gptrpg/agents/context.py
  - src/gptrpg/agents/prompt_assembly.py
  - src/gptrpg/agents/action_classifier.py
  - src/gptrpg/agents/config.py
  - src/gptrpg/turn/context.py
  - src/gptrpg/turn/judgments.py
  - src/gptrpg/rulebooks/dungeonworld_like.py
  - src/gptrpg/rulebooks/openquest.py
  - src/gptrpg/rulebooks/cairn.py
  - src/gptrpg/cli/turn_flow.py
  - src/gptrpg/cli/main.py
  - scripts/export_session_fixture.py
  - frontend/src/api/types.ts
  - frontend/src/api/client.ts
  - frontend/src/labels.ts
  - frontend/src/components/CheckBreakdown.tsx
  - frontend/src/components/ResourceChangeBadge.tsx
  - frontend/src/panes/ChatPane.tsx
  - frontend/src/panes/StatusPane.tsx
  - frontend/src/panes/StoryPane.tsx
  - frontend/src/screens/SessionScreen.tsx
  - pyproject.toml
findings:
  critical: 3
  warning: 1
  info: 3
  total: 7
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-08-18
**Depth:** standard
**Files Reviewed:** 34
**Status:** issues_found

## 검토 범위 메모

이번 페이즈는 소스 69개 파일을 건드렸지만, 이 보고서는 워크플로우가 지정한
34개 소스 파일만 검토했다. 다음은 의도적으로 제외했고, 이유를 여기 남긴다
(범위를 감사 가능하게 하기 위해):

- `tests/` 아래 33개 시험 파일 — 직접 읽지 않고, 그 파일들이 잠그는 동작을
  통해 간접적으로 살폈다(시험 스위트는 1137건 통과 상태로 보고됨).
- `tests/fixtures/session1_events.jsonl`(250KB), `session1_expected_state.json` —
  실제 플레이 세션에서 뽑은 데이터이지 코드가 아니다.
- `tests/fixtures/README.md`, `frontend/src/styles.css` — 산문·스타일 파일.

검토 중 필요에 따라 범위 밖 파일 하나(`src/gptrpg/rules_core/resolution_d100.py`)를
근거 확인용으로만 참고했다 — 아래 CR-02가 왜 사실인지 확인하기 위해서였고,
그 파일 자체에 대한 리뷰는 아니다. `frontend/src/components/DiceModal.tsx`는
같은 계산 패턴을 쓸 가능성이 있다고 `CheckBreakdown.tsx`의 도크스트링이
언급하지만 이번 검토 범위 밖이라 직접 확인하지 않았다 — CR-02를 고칠 때
반드시 함께 확인해야 한다.

## Summary

이번 페이즈는 자원 축(수치·시계·슬롯·태그·소진 다이스)을 판정·능력치·결과
목록에 실제로 연결하는 첫 물줄기다. 룰북 선언 계층(`rules_core/rulebook.py`,
`resource_change.py`)은 「모르는 것을 조용히 기본값으로 넘기지 않는다」는
저장소 규율을 세심하게 지키고 있고, 웹 쪽(`routes_actions.py`)은 2026-08-18
플레이테스트에서 나온 "캐릭터가 안 가진 축을 조용히 깎았다" 결함을
`eligible_categories`/`require_axes_on_character` 두 겹으로 실제로 막았다.

다만 그 방어가 **모든 경로에 고르게 퍼지지 않았다.** 가장 심각한 문제는
"재량 판정"·"소급 선언" 두 기능이 애초에 문자열 값을 필요로 하는 자원 축
(소지품 칸·태그)에는 절대 성공할 수 없는 정수 전용 API로 짜여 있다는
것이다 — 실제로 시도하면 그 순간 사건 기록에 영구히 남고, 그 뒤로는
그 캐릭터의 시트를 읽으려는 모든 요청(그리고 결국 세션 전체의 다음 턴)이
서버 오류로 죽는다. 두 번째로, 새로 만들어진 판정 검산 컴포넌트
(`CheckBreakdown.tsx`)는 d100 판정(OpenQuest)의 눈을 자릿수 그대로 더해
버려 "손으로 검산할 수 있다"는 이 컴포넌트 자신의 존재 이유를 무너뜨린다.
세 번째로, 명령줄 경로(`cli/turn_flow.py`)는 웹 경로가 방금 추가한 축
소유권 검증을 그대로 갖고 있지 않아, 고쳐진 줄 알았던 그 결함이 `gptrpg
turn` 경로로는 여전히 열려 있다.

## Critical Issues

### CR-01: 재량 판정·소급 선언이 문자열 값이 필요한 자원 축(소지품 칸·태그)에서 세션을 영구히 깨뜨린다

**File:** `src/gptrpg/web/routes_actions.py:1146`, `src/gptrpg/web/routes_actions.py:1176-1178`,
`src/gptrpg/event_log/schema.py:386`, `src/gptrpg/rules_core/resource_change.py:192-202`,
`src/gptrpg/rules_core/rulebook.py:748-770`

**Issue:**
자원 변화의 「축 · 동작 · 양」 세 칸 중 `양`은 형태에 따라 뜻이 다르다 —
`numeric`/`clock`/`usage_die`는 정수, `named_slots`/`tag_list`는 **문자열**
(채울 아이템 이름·붙일 태그 이름)이어야 한다. `apply_resource_op`이 실제로
그렇게 검사한다(`resource_change.py:192-202`의 `_require_str_amount`).

그런데 사람이 직접 제안하는 두 경로(재량 판정 `discretionary`, 소급 선언
`retro_declaration_amount`)의 요청 스키마는 **양을 항상 정수로만 받는다**:

```python
# routes_actions.py:1144-1146
class DiscretionaryProposal(BaseModel):
    axis: str = Field(min_length=1, max_length=MAX_ID_LEN)
    operation: str = Field(min_length=1, max_length=32)
    amount: int = Field(ge=-MAX_DISCRETIONARY_AMOUNT, le=MAX_DISCRETIONARY_AMOUNT)

# routes_actions.py:1176-1178
retro_declaration_amount: int | None = Field(
    default=None, ge=-MAX_DISCRETIONARY_AMOUNT, le=MAX_DISCRETIONARY_AMOUNT
)
```

Cairn 룰북은 소지품(`Inventory`, `named_slots`)을 채우는 것 자체가
소급 선언의 유일한 용도로 선언되어 있다(`rulebooks/cairn.py`의
`CAIRN_RETRO_DECLARATION = RetroDeclarationDecl(allowed=True,
cost_axis="Inventory", operation="fill")`) — 즉 "사실 나 그거
챙겨왔었어"라고 선언할 때 실려야 하는 값은 **아이템 이름 문자열**인데,
API는 그 자리에 정수만 받을 수 있다.

이 어긋남을 잡아낼 검증이 어디에도 없다. `routes_actions.py:1259-1268`의
`validate_outcome_list` 호출은 축 이름·`form != "none"`·`operation`이
그 형태에 허용되는지(세 가지)만 보고 **양의 형태는 절대 보지 않는다**
(`rulebook.py:748-770`의 `_check` 함수 시그니처 자체에 `amount` 인자가
없다). `ResourceChangeDecl.__post_init__`(`resource_change.py`)도 `amount`가
`str`일 때만 주사위식을 검사하고, `int`면 그냥 통과시킨다. `roll_amount`도
형태를 모른 채 정수를 그대로 되돌려줄 뿐이다.

그 결과 요청은 다음 단계를 전부 통과해 **사건으로 영구히 기록된다**:

1. `validate_outcome_list` 통과(양을 안 본다)
2. `require_axes_on_character` 통과(축 소유 여부만 본다)
3. `roll_amount` 통과(정수를 그대로 돌려준다)
4. `SessionActor._prepare_record_resource_change`(`session_actor/actor.py:1006-1062`)
   통과 — 이 계층은 `web.characters_data`를 알 수 없어(층 계약) 애초에
   축의 `form`을 볼 수 없다.
5. `ResourceChanged` 사건이 저장소에 append된다.

문제는 6단계에서 터진다 — 이 이벤트를 접어(fold) 「지금 값」을 계산하는
시점(`resolve_character_stats` → `apply_resource_op`,
`resource_change.py:205-305`)에서야 `_require_str_amount`가
`isinstance(op.amount, str)`를 검사해 `InvalidResourceChange`를 던진다.
이 예외를 잡는 코드가 어디에도 없다:

- `web/routes_characters.py`의 `get_character_sheet`는 `_current_stats`를
  try/except 없이 그대로 부른다 → 그 캐릭터의 시트 조회(`GET
  .../characters/{id}`)가 이후 **영구히** 500으로 죽는다.
- `web/routes_actions.py`의 `_current_party_state`는 **세션의 캐릭터
  전원**을 한 번에 접는다 → 파티 중 한 명이라도 이 오염된 이벤트를 가지면
  `declare()`/`confirm()`/`proceed()` 전부가 500으로 죽는다 — 즉 그 캐릭터
  하나가 아니라 **세션 전체가 그 순간부터 못 쓰게 된다.**

사건 기록은 append-only라 이 손상은 되돌릴 수 없다 — DB를 손으로 고치지
않는 한 그 세션은 영구히 열리지 않는다.

프론트엔드가 아직 `discretionary`/`retro_declaration_amount`를 전송하는
UI를 만들지 않았다는 점(`frontend/src/api/client.ts`의
`confirmResourceChange`는 이 두 칸을 안 보낸다)은 위험을 줄이지 않는다 —
엔드포인트 자체는 이미 살아 있고, 이 프로젝트의 다른 모든 확인 관문이
"클라이언트가 보낸 값을 그대로 믿지 않는다"를 원칙으로 삼고 있는데
(`ordered_categories`를 서버가 또 대조하는 이유가 바로 이것이다) 이 자리만
그 원칙이 빠져 있다. 재량 판정/소급 선언 UI가 붙는 순간 이 결함은 정상
사용 흐름에서 곧바로 밟힌다.

더 근본적으로, `ResourceChangeRecord`(`event_log/schema.py:372-390`) 사건
스키마 자체가 `amount: int`로 고정돼 있다 — `rules_core.ResourceOp.amount:
int | str`과 짝이 안 맞는다. 설사 위 API 스키마를 문자열도 받게 고쳐도,
사건을 실제로 쓰는 시점에 pydantic이 `ResourceChanged` 생성 자체를
거부하게 된다. 즉 이 결함은 API 한 자리의 실수가 아니라 **웹 요청
스키마 → 사건 스키마 → 폴딩 로직 세 층이 서로 다른 "양"의 타입을 전제한
구조적 어긋남**이다.

**Fix:**
1. `event_log/schema.py::ResourceChangeRecord.amount`를 `int | str`로
   넓힌다 — `rules_core.ResourceOp.amount`와 짝을 맞춘다.
2. `DiscretionaryProposal.amount`와
   `ConfirmResourceChangeRequest.retro_declaration_amount`를 `int | str`로
   넓히거나(자유 문자열은 다시 위험하므로 권장하지 않음), 최소한 **제출
   전에** 그 축의 `StatEntry.form`을 보고 필요한 타입인지 검사한다:

```python
# confirm_resource_change() 안, require_axes_on_character 직후
axes_by_name = {stat.name: stat for stat in actor_entity.stats}
for decl in decls:
    stat = axes_by_name[decl.axis]  # require_axes_on_character가 이미 존재를 보장
    if stat.form in ("named_slots", "tag_list") and not isinstance(decl.amount, str):
        raise HTTPException(
            status_code=400,
            detail=f"축 {decl.axis!r}({stat.form})은 문자열 값이 필요하다",
        )
```

3. 사건을 쓰기 **전에** `apply_resource_op`을 한 번 "드라이런"으로 불러
   실제로 이 캐릭터의 현재 상태에 적용 가능한지 확인하는 방법도 고려한다
   — 그러면 폴딩 시점의 예외가 쓰기 시점의 400으로 앞당겨진다(이 저장소가
   이미 여러 곳에서 쓰는 "등록/제출 시점에 검증을 앞당긴다"는 관례,
   `ShadowedGradeBand`/`UncoveredOutcomeGap`과 같은 철학).
4. `resolve_character_stats`를 부르는 모든 자리(`routes_characters.py`,
   `routes_actions.py`)에 최소한 방어적 try/except를 추가해, 이미 오염된
   기존 이벤트가 있더라도 캐릭터 하나의 손상이 세션 전체를 죽이지 않게
   막는다(근본 수정과 별개로 필요한 안전망).

---

### CR-02: `CheckBreakdown.tsx`가 d100 판정(OpenQuest)의 눈을 자릿수 그대로 더해 완전히 틀린 합계를 보여준다

**File:** `frontend/src/components/CheckBreakdown.tsx:30-33`

**Issue:**
이 컴포넌트의 존재 이유는 자신의 도크스트링이 말하고 있다: "「사람이
검산할 수 있다」가 이 제품의 약속"이고, 서버가 `total`을 항상 `null`로
보내므로(`ConfirmResponse.total`, 12-01 알려진 갭) 화면이 직접
`rolls`+`modifiers`를 더해 검산 가능한 합계를 만든다.

```typescript
const rollTotal = rolls.reduce((sum, value) => sum + value, 0);
const modifierTotal = modifiers.reduce((sum, modifier) => sum + modifier.value, 0);
const total = rollTotal + modifierTotal;
```

이 계산은 눈을 "더해서" 총합을 만드는 2d6 방식(`resolve_2d6`)에서만 맞다.
d100 롤언더 방식(`resolution_d100.resolve_d100`, OpenQuest 룰북이 씀)은
`rolls`에 **십의 자리·일의 자리 눈**을 담는다(보너스/페널티 다이스가
있으면 버려진 십의 자리 후보까지 포함) — 실제 판정 값은 그 눈들의
합이 아니라 `percentile_value(선택된 십의 자리, 일의 자리) = 십의 자리
× 10 + 일의 자리`다(`resolution_d100.py:44-50`, `:139`, `:146`).

예를 들어 십의 자리 3, 일의 자리 7이 나와 실제 판정값이 37이었다면, 이
컴포넌트는 `3 + 7 = 10`을 "총합"으로 보여준다 — 완전히 다른 숫자다.
보너스/페널티 다이스가 붙으면 `rolls` 길이가 3개 이상이 되어 계산은
더 심하게 틀어진다(버려진 십의 자리까지 다 더해 버린다).

이 화면이 등급 도장(`gradeLabel`/`gradeTone`)과 나란히 뜨는데, 등급 자체는
서버가 올바르게 계산한 값이므로 "등급은 맞는데 검산 숫자는 안 맞는" 모양이
된다 — 검산을 하라고 만든 컴포넌트가 오히려 사람이 스스로 계산해 본 뒤
서버를 의심하게 만드는 역효과를 낸다. `DiceModal.tsx`(이번 검토 범위
밖)도 같은 계산을 한다고 이 파일의 도크스트링이 언급하므로, 고칠 때
함께 확인해야 한다.

**Fix:** 판정 방식별로 다른 표시 계산이 필요하다. 가장 간단한 방법은
서버가 이미 알고 있는 `total`을 프론트가 다시 계산하지 않고 그대로
믿을 수 있도록 `CheckResolved`에 `total` 칸을 추가하는 것(알려진 갭을
메운다)이다. 그때까지의 임시 조치로는 컴포넌트에 판정 방식(또는 최소
"두 자리 결합" 여부)을 알려주는 prop을 추가한다:

```typescript
interface CheckBreakdownProps {
  rolls: number[];
  modifiers: ModifierView[];
  target: number | null;
  resolutionMethod: "2d6" | "d100_roll_under" | "d20_roll_under";
}
// d100_roll_under: rolls의 마지막 원소가 일의 자리, 그 앞이 채택된
// 십의 자리라는 정보가 없으면 프론트에서 재계산 자체가 불가능하다 —
// 버려진 후보까지 rolls에 섞여 있기 때문이다. 서버가 total을 내려주는
// 쪽이 근본 해법이다.
```

---

### CR-03: 명령줄(`gptrpg turn`) 경로는 웹이 방금 추가한 「캐릭터가 안 가진 축」 방어를 갖고 있지 않다

**File:** `src/gptrpg/cli/turn_flow.py:682`, `src/gptrpg/cli/turn_flow.py:756-798`

**Issue:**
2026-08-18 플레이테스트에서 실제로 관측된 결함 — 결과 목록이 가리키는
축을 그 캐릭터가 안 가지고 있으면, `resolve_character_stats`가 그 연산을
조용히 버려 "화면엔 변했다고 뜨는데 실제로는 아무 일도 안 일어난다" —
이 결함을 막으려고 웹 경로(`web/routes_actions.py`)는 두 겹 방어를
추가했다:

1. AI에게 애초에 그 캐릭터가 가진 축만 보여준다
   (`eligible_categories(rulebook.outcome_list, actor_stats(ctx))`,
   `routes_actions.py:897-899`).
2. 사건을 쓰기 직전 마지막 관문에서 다시 확인한다
   (`require_axes_on_character`, `routes_actions.py:1304`).

CLI(`_turn_flow`, `cli/turn_flow.py`)는 **이 둘 중 어느 것도 갖고 있지
않다.** `gather_turn_judgments`에 `rulebook.outcome_list`를 필터링 없이
그대로 넘기고(682줄):

```python
judgments = await gather_turn_judgments(
    ...
    outcome_list=rulebook.outcome_list,   # eligible_categories를 거치지 않는다
    grade_band=grade_band,
    resource_axes=rulebook.resource_axes,
)
```

결과 목록에서 AI가 무엇을 고르든, 그 뒤 자원 변화 확인 절차(756~798줄)는
`require_axes_on_character`에 해당하는 마지막 관문 없이 곧장
`RecordResourceChange`를 제출한다:

```python
try:
    await actor.submit(
        RecordResourceChange(
            character_id=args.player,
            changes=ops,
            source="outcome_list",
            caused_by_seq=resolve_seq,
        )
    )
except AlreadyChanged:
    pass
```

CLI 자체는 실제 캐릭터 시트 개념이 없어(`args.player`는 그냥 문자열
식별자다) 이 결함이 CLI 화면 안에서는 안 보인다. 그러나 `--session`이
가리키는 이벤트 로그는 웹이 서빙하는 것과 **같은 파일**이고,
`--player`에 실제 웹 로스터의 캐릭터 id(예: `bram`)를 주면, 여기서 기록된
`resource_changed` 사건은 나중에 웹이 그 캐릭터의 시트나 파티 상태를 접을
때 똑같이 조용히 버려진다 — 웹에서 고친 줄 알았던 바로 그 결함이 CLI를
거쳐 다시 열린다. `gptrpg turn`은 진행자가 실제 세션을 상대로 디버깅·시연
용도로 쓰도록 설계된 도구이므로(진행 표시·5초 워치독 등 실사용을 겨냥한
UX가 이미 갖춰져 있다) 이 경로가 실제 세션에 닿을 가능성은 낮지 않다.

**Fix:** CLI에도 같은 두 겹을 추가한다. 다만 CLI는 실제 `Entity`/`StatEntry`를
불러올 수단이 없으므로(층 계약상 `web.characters_data`를 모른다), 최소한
2번째 겹(마지막 관문)만이라도 넣을 수 있는 자리를 마련해야 한다 — 예를
들어 `_turn_flow`가 캐릭터 상태를 아는 얕은 인자를 받게 하거나, 최소한
"CLI는 축 소유 여부를 검증하지 않는다"는 사실을 도크스트링에 명시하고
운영 절차 문서에서 실제 세션에 `gptrpg turn`을 함부로 섞어 쓰지 말라고
못박는다. 근본적으로는 CLI가 웹과 같은 캐릭터 데이터 소스를 볼 수 있게
층 경계를 다시 설계하는 편이 안전하다.

## Warnings

### WR-01: 분류기가 AI가 낸 `stat` 이름을 검증하지 않아, 확인은 됐지만 영원히 판정될 수 없는 선언이 생길 수 있다

**File:** `src/gptrpg/agents/action_classifier.py:154-182`

**Issue:** `_parse_candidates`는 `move` 값을 `known_move_ids`와 대조해
목록 밖 이름이면 `UnknownMove`를 던진다(D-12가 요구하는 닫힌 목록
검증). 그런데 같은 후보 원소의 `stat` 값은 검증 없이 그대로 받는다:

```python
candidates.append(MoveCandidate(move=move_id, stat=item.get("stat", "")))
```

모델이 그 룰북에 없는 능력치 이름(예: 오타, 다른 룰북의 영문 축 이름과
헷갈림)을 냈어도 이 시점에서는 걸리지 않는다. 이 후보는 그대로 브라우저에
보이고, 사람이 확인 버튼을 누르면 `action_confirmed` 사건이 먼저 기록된
뒤에야 `_prepare_resolve_check`의 `build_stat_check_input`이 그 이름을
룰북 축 목록에서 못 찾아 `StatNotUsableInChecks` → `CommandRejected` →
400을 던진다.

이때 `action_confirmed` 사건은 이미 기록되어 있고, `_prepare_confirm`의
멱등 로직은 **같은** move/stat로 재확인이 오면 캐시를 재사용한다
(`AlreadyConfirmed`) — 그런데 그 판정은 항상 같은 이유로 다시 실패한다.
**다른** move/stat로 재확인을 시도하면 "이미 다른 무브로 확인된 선언이다"로
거부된다. 즉 이 선언은 확인은 됐지만 판정으로 절대 나아갈 수 없는
막다른 상태에 영구히 갇힌다 — 플레이어는 그 턴을 포기하고 새로 선언하는
것 말고는 빠져나올 방법이 없다.

**Fix:** `_parse_candidates`가 룰북의 자원 축 이름 집합을 함께 받아
`stat`도 닫힌 목록으로 검증한다(`move`와 같은 자리, 같은 무게):

```python
def _parse_candidates(
    raw_text: str, known_move_ids: frozenset[str], known_stat_names: frozenset[str]
) -> tuple[tuple[MoveCandidate, ...], bool]:
    ...
    stat = item.get("stat", "")
    if stat and stat not in known_stat_names:
        raise UnknownMove(move_id)  # 또는 별도 UnknownStat 예외
```

`classify()`가 이미 `unknown_move`를 흡수해 `tier="unclear"`로 부드럽게
떨어뜨리는 경로(SAFE-07/10-05)를 갖고 있으므로, 같은 흡수 경로를 타면
새 상태 코드나 새 화면을 만들 필요가 없다 — "판정 없이 여기서 끝납니다"로
자연스럽게 떨어진다.

## Info

### IN-01: `usage_die`의 `step_down` 동작이 실제로는 방향을 강제하지 않는다

**File:** `src/gptrpg/rules_core/resource_change.py:291-300`

**Issue:** `apply_resource_op`의 `usage_die` 분기는 `step_down` 연산을
받으면 `current`를 그냥 받은 정수로 덮어쓴다 — 이름과 달리 "내려가는지"
검증하지 않는다. `DiscretionaryProposal.amount`가 ±20 범위의 정수를
자유롭게 허용하므로(CR-01이 고쳐진 뒤에는 이 경로도 살아난다), 이론상
"step_down"이라는 이름의 연산으로 소진된 다이스를 더 큰 면수로 되돌리는
것도 가능하다. 다만 지금 등록된 세 룰북(`dungeonworld_like`,
`openquest`, `cairn`) 중 어느 것도 `usage_die` 형태의 축을 선언하지
않았으므로 **현재는 실제로 밟을 수 있는 경로가 없다** — 이 형태를 쓰는
룰북이 추가되는 시점에 다시 짚어야 한다.

**Fix:** `step_down`이 `new_value < stat.current`(또는 최소
`<= stat.current`)를 만족하는지 검사하거나, 이름을 "내려간다"는 뜻을
전제하지 않는 중립적인 이름(예: `set_die`)으로 바꾸는 것을 고려한다.

### IN-02: `ResourceChangeDecl`/`ResourceOp`가 `operation`이 여덟 값 중 하나인지 생성 시점에 검사하지 않는다

**File:** `src/gptrpg/rules_core/resource_change.py:98-106`, `:133-135`

**Issue:** 두 dataclass의 `__post_init__`은 `axis` 비어있음(및 `amount`가
문자열일 때의 주사위식)만 검사하고, `operation`이 `ResourceOperation`
리터럴 여덟 값 중 하나인지는 검사하지 않는다(파이썬 타입 힌트는 런타임
강제력이 없다). 실제로는 `validate_outcome_list`(등록 시점)와
`apply_resource_op`(폴딩 시점)가 하류에서 이를 걸러내므로 현재는 안전망이
있지만, 이 dataclass 자체를 직접 생성하는 새 호출부가 생기면(저장소를
우회하는 시험 코드 등) 그 안전망을 거치지 않을 수 있다.

**Fix:** `__post_init__`에 `operation`이 여덟 값 집합에 있는지 확인하는
줄을 추가해, "생성 시점에 이미 유효하다"를 이 타입 자신의 불변식으로
만든다.

### IN-03: 판정 이후 AI 판단·서사 스트리밍 블록이 세 곳(웹 confirm/proceed, CLI)에 거의 그대로 중복돼 있다

**File:** `src/gptrpg/web/routes_actions.py:844-1132`,
`src/gptrpg/web/routes_actions.py:1466-1658`,
`src/gptrpg/cli/turn_flow.py:230-458`, `src/gptrpg/cli/turn_flow.py:639-939`

**Issue:** 네 판단 병렬 호출(`gather_turn_judgments`) 준비, 네 번의
`RecordAiCall` 제출, 서사 스트리밍 루프(첫 조각 대기 → 이어받기 →
`narration_failed` 처리), 배경 시계 조건 검사 등록까지 이어지는 약
150~200줄짜리 블록이 `confirm()`/`proceed()`(웹)와
`_turn_flow`/`_proceed_without_check`(CLI) 네 함수에 사실상 그대로
반복된다. 주석들이 "한 곳만 고치면 갈린다"는 위험을 스스로 인지하고
있고(`web/routes_actions.py`의 "웹 안에서도 호출부가 둘이라는 것이 이
함정이다" 등), 실제로 이번 검토에서 CR-03(CLI가 웹의 최신 방어를
못 따라간 것)이 바로 이 중복 구조 때문에 벌어진 사고다.

**Fix:** 즉시 액션 항목은 아니지만, 이 블록을 (판정 유무·caused_by_seq
값 정도만 매개변수로 받는) 공유 헬퍼로 뽑아내면 CR-03류의 "한쪽만
고쳐서 갈리는" 사고를 구조적으로 막을 수 있다. 다만 웹과 CLI가 스레드
모델이 다르다는 점(웹은 `asyncio.to_thread`로 서사를 내보내고, CLI는
진행 표시 스레드를 따로 쓴다)을 헬퍼 설계에서 반드시 반영해야 한다.

---

_Reviewed: 2026-08-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

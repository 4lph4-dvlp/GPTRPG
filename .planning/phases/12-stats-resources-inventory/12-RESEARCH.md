# Phase 12: 능력치 · 자원 변화 · 소지품 - Research

**Researched:** 2026-08-17
**Domain:** 규칙 코어 상태 폴딩 설계(`GameState`) · 사건 스키마 확장 · 효과 표현(D7) 첫 원자 연산 · AI 문맥 분기(에이전트별 상한) · 회귀 픽스처
**Confidence:** MEDIUM-HIGH — 코드 사실 확인(우선순위 1·2·4·5·6)은 전부 실제 파일을 열어 확인해 HIGH, 신규 설계 제안(GameState 폴딩 모양·D-05 선언 형식·주사위식 파서·closed-list 저장 형식)은 저장소 관례에서 도출한 권고이므로 MEDIUM, 실제 출간작 룰북 비교(우선순위 7)는 이미 저장소에 있는 `RULEBOOK-SURVEY.md`를 재확인한 것이라 그 문서의 신뢰도([확인됨]/[일반지식] 표시)를 그대로 물려받는다.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** 룰북이 「이 숫자를 판정에 어떻게 쓰는가」를 쓰임 이름으로 고르고, 필요한 룰북만 값→보정치 구간표를 덧붙인다. 두 층 다 만든다. 쓰임 **이름**은 플랫폼 어휘, **어느 능력치를 쓰는지·얼마로 바꾸는지**는 룰북 것. Reversibility: costly.
- **D-02:** 보정치를 바깥에서 숫자로 받는 통로를 닫는다. 서버가 캐릭터의 `StatEntry`와 룰북 선언만 보고 보정치를 만든다. 바깥에서 받는 것은 「어려움」 같은 닫힌 이름 목록뿐. 웹과 CLI 둘 다 같은 커밋에서 닫는다. Reversibility: costly.
- **D-03:** 룰북이 일부러 능력치를 안 정해 둔 무브는 AI가 제안하고 사람이 확인한다. AI가 고르는 것은 닫힌 목록(그 룰북의 자원 축 이름)에서만이다.
- **D-04:** 「주사위 7 + 힘 2 = 9, 목표 10」이 기록과 화면 둘 다에 보인다.
- **D-05:** 변화량 선언은 「축 이름 · 동작 · 양」 세 칸짜리 항목의 목록이다. Reversibility: one-way — D7의 나머지 원자 연산이 이 위에 쌓인다.
- **D-06:** 양은 고정값과 주사위 둘 다 된다. `rules_core/dice.py::Roller`와 `event_log/replay_roller.py`를 그대로 탄다 — 새 무작위 경로를 만들지 않는다.
- **D-07:** 변화량은 결과 목록(D-11)의 항목에 붙는다. 결과 목록이 없는 룰북은 판정만으로는 숫자가 안 변하고 재량 판정(D-09)으로 넘어간다.
- **D-08:** 자원이 0에 닿으면 룰북이 선언한 「바닥나면」 고리를 부른다 — 부르는 데까지가 이번 몫. 최대치는 코드가 자른다(QUAL-06).
- **D-09:** AI가 고르는 닫힌 목록에 「이번엔 숫자가 안 변한다」가 항목으로 들어간다. AI는 여전히 수치를 직접 못 바꾼다.
- **D-10:** 자원 변화 확인은 그 캐릭터를 잡고 있는 사람이 누른다 — Phase 8의 점유·신원 검증을 재사용한다.
- **D-11:** AI가 닫힌 목록에서 고르고 곧바로 서술한다. 목록 선택 자체에는 사람 확인이 안 붙는다 — 숫자가 실제로 변할 때만 D-09/D-10의 확인이 붙는다. 「무엇이 일어나는 종류」는 데이터가 되지만 「이 장면 이 순간의 구체적 문장」은 영원히 재량이다.
- **D-12:** 한 번에 몇 개를 고를 수 있는지는 룰북이 선언한다 — 빈 목록이 정상값.
- **D-13:** 등급 선언에 「대가가 붙는가」 칸을 하나 더 둔다 — 「성공인가」와 두 축. Reversibility: costly.
- **D-14:** 「실패로 세나」는 여전히 별개의 세 번째 칸이다. 등급 하나에 세 칸이 각자 독립: ① 성공했나 ② 대가가 붙나 ③ 실패로 세나.
- **D-15:** AI가 「이 행동은 무엇을 쓰는가」를 뽑고, 실제로 갖고 있는지는 코드가 대조한다. 소지품을 **세는 룰북에만** 태운다(지금은 Cairn `named_slots` 하나).
- **D-16:** 소급 선언은 축은 룰북이, 양은 그때그때 정한다. 비용 표현은 D-05의 「축·동작·양」을 그대로 쓴다.
- **D-17:** 서술하는 진행자(`master_gm`)와 상황 판단자(`situation_judge`)만 파티 전원의 상태를 받는다. 분류기·장면 대상 판단·시계 판단은 안 받는다.
- **D-18:** 전원의 축을 지금 한 명에게 하는 것과 같은 모양으로 넷 다 넣는다 — 요약하지 않는다.
- **D-19:** 자원이 변할 때마다 화면이 알리고, 크기에 따라 표시 세기만 다르게 한다 — 문턱을 정의하지 않는다.

### Claude's Discretion

- 지금 값을 어떻게 만드나 — 사건을 매번 처음부터 접을지, `GameState`에 캐릭터 수치 표를 어떤 모양으로 둘지. 「중간 저장을 쓰지 않는다(D-08)」는 기존 규율 안에서 정한다
- 새 사건 종류의 이름과 개수 — D-05~D-07이 정한 내용을 담을 수 있으면 된다
- QUAL-01(사건 순서 어긋남 감지)·QUAL-02(기록 형식 표시 빠짐 vs 진짜 구버전)의 구현 모양 — 어디서 어떤 예외로 멈출지. `UnknownEventType`·`NoMatchingGradeBand`·`InvalidStatEntry` 규율을 따를 것
- TEST-04 회귀 픽스처의 모양 — 세션1 실기록(895건)을 어디에 두고 무엇을 대조할지
- 이 단계를 몇 개의 계획으로 쪼갤지 — 요구사항 16개이나 같은 파일들(`resolution.py`·`routes_actions.py::confirm`·`reducer.py`·룰북 선언)에 몰려 있어 얇게 나누면 같은 파일을 두 번 연다
- 표시 세기를 어떻게 다르게 할지(D-19) — 색·크기·지속시간 등. Phase 16이 전면 재감사하므로 여기서는 최소로

### Deferred Ideas (OUT OF SCOPE)

- 캐릭터 만들기 절차·화면 — Phase 12.1
- 효과 표현(D7) 원자 연산 목록 전체 — M1 이후. 이번엔 「자원을 얼마나 바꾸는가」 하나만
- 「바닥나면」 고리가 실제로 무엇을 하는지 — 다음 마일스톤. 이번엔 부르는 데까지
- 관계 장부·문맥 압축기 — Phase 14 (D-68로 확정)
- 위협 시계 진행 규칙 ②③ — Phase 15
- 프론트엔드 전면 재감사 — Phase 16
- 되돌리기(진행자의 「방금 그건 잘못 깎였다」 취소) — 후속. 새 권한 개념 필요
- 소지품 화면에서 물건을 손으로 넣고 빼는 조작 — 이 단계는 읽고 대조하는 것까지
- `clock`/`tag_list`/`usage_die`를 실제로 선언하는 룰북 — 이 단계 밖(다만 시험 픽스처는 셋 다 덮을 것)
- 캐릭터 만들기 절차 · 파티 전원 대기 규칙 — Phase 12.1
- 자동화율 계측의 실제 계산 — 규칙만 정해졌고 계측 자체는 이 단계 밖

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RULE-02 | 능력치가 판정 계산에 실제로 반영된다 | Pattern 1 — `ResolveCheck`에 `stat` 칸이 없다는 것을 코드로 확인, 서버가 `StatEntry`를 읽어 `Modifier`/`target`을 만드는 새 경로를 제시 |
| RULE-03 | 능력치→보정치 변환 규칙을 룰북이 선언한다 | Pattern 1 — 「쓰임 이름」 선언(2단계 구조) 권고 모양 |
| RULE-04 | 판정 결과가 자원을 실제로 바꾸고 기록에 남아 재생된다 | Pattern 2·3 — 사건 스키마·`GameState` 폴딩 모양 |
| RULE-05 | 자원 이름·변화량을 AI가 정하지 않는다 — 룰북 선언과 순수 코드가 정한다 | Pattern 3·7 — 결과 목록에 축·동작·양이 붙는 D-05/D-07 형식 |
| RULE-06 | 캐릭터 시트가 지금 상태를 보여준다 | Pattern 2 — 시작값(파이썬 상수) + 폴딩된 변화의 결합 지점 |
| RULE-07 | 자원이 크게 깎이면 화면에서 바로 보인다 | Common Pitfalls, `StatusPane.tsx` 기존 렌더 갈래 재사용 |
| RULE-08 | AI가 파티 전원의 상태를 본다 | Pattern 5 — `TurnContext`/`NarrationFacts` 공유 지점의 분기 필요성 |
| RULE-09 | 변화량 선언 형식이 효과 표현(D7) 첫 원자 연산으로 자랄 모양이다 | Pattern 3 — 「축·동작·양」이 향후 「상태 부여·이동」과 나란히 놓일 수 있는 근거 |
| RULE-10 | 룰북에 선언이 없어도 AI 제안+사람 확인으로 자원이 변한다 | Pattern 7 — 재량 판정 경로가 D-05 형식을 그대로 재사용 |
| RULE-13 | 결과 카테고리를 닫힌 목록에서 먼저 고른다 — 빈 목록이 정상값 | Pattern 7 — GM 대응 목록의 데이터 모양, 빈 목록 처리 |
| RULE-14 | 「성공했는가」·「대가가 붙는가」가 다른 두 축 | Pattern 4 — `GradeBand` 세 번째 독립 칸 |
| RULE-16 | 소지품에 없는 것을 쓰면 재량 판정 — 소급 비용은 룰북이 축을 선언 | Pattern 6 — `named_slots` 대조 경로, D-15/D-16 |
| QUAL-01 | 사건 순서 어긋남이 조용히 넘어가지 않는다 | Pattern 2 — `EventStore.read_events`의 `ORDER BY seq`에만 기대는 현재 상태를 확인, `fold()` 방어 제안 |
| QUAL-02 | 기록 형식 표시 빠짐과 진짜 구버전 기록이 구분된다 | Pattern 2 — `parse_event`/`EventEnvelope.schema_version` 필수 필드 확인, 예외 모양 제안 |
| QUAL-06 | 캐릭터 상태값이 최대치를 넘지 못한다 | Pattern 3 — 폴딩 함수의 clamp 지점 |
| TEST-04 | 세션1 실제 기록을 재생해도 같은 상태가 나오는 회귀 픽스처 | Pattern 8 — `.gptrpg/events.db`(895건, 판 2)의 실제 위치·gitignore 상태·기존 스모크 시험 관례 확인 |

</phase_requirements>

## Summary

이 단계는 여섯 개 파일(`entities.py`·`reducer.py`·`resolution.py`/`resolution_d100.py`·`rulebook.py`·`actor.py`·`routes_actions.py`·`context.py`·`prompt_assembly.py`)에 걸친 16개 요구사항을 하나의 단계로 묶은 이유가 실제 코드에서 확인된다 — 능력치 반영(D-01/D-02)과 자원 변화(D-05~D-08)가 `SessionActor._prepare_resolve_check`라는 같은 함수를 통과하고, 자원 변화와 파티 상태 노출(D-17/D-18)이 `build_turn_context`라는 같은 조립 지점을 공유한다.

**가장 결정적인 발견 — RULE-02가 왜 "전혀 안 됨"인지 코드로 확인했다.** `SessionActor.ResolveCheck`(`session_actor/actor.py:102-122`)에는 `move`·`modifiers`·`target`·`rulebook_id`·`person_id`·`character_id` 여섯 칸만 있고 **`stat` 칸이 없다.** `confirm()`(`web/routes_actions.py:504-514`)이 `ConfirmAction`에는 `body.stat`을 넘기지만 그 아래 `ResolveCheck(...)`을 만들 때는 `stat`을 아예 조립하지 않는다 — `character = get_character(body.character_id)`로 이미 캐릭터를 불러왔는데도(445줄) 그 `Entity.stats`를 판정에 쓸 방법이 구조적으로 없다. 이것이 CONTEXT.md가 짚은 "캐릭터를 불러오긴 하지만 StatEntry 값을 한 번도 안 읽는다"의 정확한 코드 위치다. 또 하나 — `ConfirmRequest.target`(366-380줄)은 **브라우저가 직접 보내는 값**인데 실제 프런트엔드(`api/client.ts:96-115`)는 이 칸을 아예 안 보낸다. 그 결과 지금 웹에서 OpenQuest 판정을 확인하면 `target`은 항상 pydantic 기본값 `DEFAULT_TARGET=10`이 된다 — OpenQuest의 목표값(기술값 0~100)과 무관한 값이 `resolve_d100`의 `skill` 인자로 그대로 들어간다는 뜻이다. RULE-02/RULE-03을 닫으려면 `ResolveCheck`에 `stat` 칸을 더하고, 서버가 확인된 `character.stats`에서 그 칸의 `StatEntry.current`를 찾아 룰북이 선언한 "쓰임"(2d6은 `Modifier(FLAT)`로 더함, d100은 `target`/`skill` 자체로 씀)에 맞게 변환하는 새 함수가 필요하다.

**두 번째 결정적 발견 — `resolve_2d6`과 `resolve_d100`의 등급 산출 경로가 실제로 다르다(CONTEXT.md가 지적한 그대로).** `resolve_2d6`(`resolution.py:61-78`)은 `grading.grade_for_total`을 부른다 — 이 함수는 `WEAK_HIT_BAND=3`이라는 **하드코딩된 던전월드 상수**로 등급 **이름**("strong_hit"/"weak_hit"/"miss")까지 직접 만들어낸다. `resolve_d100`(`resolution_d100.py:72-151`)은 반대로 `rulebook.grade_bands`를 인자로 받아 `grade_for_margin`으로 등급을 산출한다 — 완전히 룰북 선언에서 나온다. 둘 다 최종적으로는 `SessionActor._prepare_resolve_check`가 `require_band(rulebook.grade_bands, outcome.grade)`(`actor.py:664`)로 그 이름을 룰북 선언에서 다시 찾아 `counts_as_failure`(그리고 D-13이 더할 「대가가 붙는가」)를 읽는다 — 이 마지막 조회 단계가 두 판정 방식을 다시 하나로 묶기 때문에, **D-13(등급에 세 번째 독립 칸 추가)은 이 어긋남을 고치지 않고도 안전하게 구현된다.** 다만 어긋남 자체(2d6 룰북은 등급 경계를 절대 자기 것으로 선언할 수 없다 — `grade_for_total`이 모든 2d6 룰북에 `WEAK_HIT_BAND=3`을 강제한다)는 D-01의 정신("룰북이 변환 규칙을 선언한다")과 좁게 어긋나 있는 기존 기술 부채이고, RULE-02~16 어느 것도 이것을 직접 요구하지 않으므로 이번 단계 범위 밖으로 명시적으로 남기는 것을 권고한다.

**세 번째 발견 — 주사위식(dice expression)을 굴리는 인프라가 저장소에 아예 없다.** D-06은 "고정값과 주사위 둘 다"를 요구하지만, `rules_core/dice.py::Roller`는 `roll_d6()`(2d6용)와 `roll_tens()`/`roll_units()`(d100용) 세 메서드뿐이다. 던전월드·Cairn류가 실제로 쓰는 피해 주사위(`1d6`, `1d8` 등 임의 면수)를 굴릴 방법이 없다. 다행히 `ReplayRoller._next_roll()`(`event_log/replay_roller.py:54-59`)은 이미 **면수 무관 평평한 정수 반복자**라서, `Roller`/`ReplayRoller`/`LiveRoller` 셋에 `roll_die(sides: int) -> int` 메서드 하나만 추가하면(`.importlinter` contract:1이 금지하는 모듈을 쓰지 않는 순수 확장) 구조 변경 없이 임의 면수를 지원할 수 있다. `ReplayRoller`도 눈에 확인.

**네 번째 발견 — `ReplayRoller`는 지금 프로덕션 코드 어디에서도 안 쓰인다.** `grep -rln ReplayRoller src/gptrpg/`가 `event_log/replay_roller.py` 자기 자신만 돌려준다. 즉 "재생"(TEST-04·`gptrpg replay`)은 지금 판정을 **다시 굴리지 않는다** — `CheckResolved.rolls`에 이미 기록된 숫자를 그대로 읽어 `fold()`로 상태만 다시 접는다. 이것이 TEST-04의 정확한 범위를 정한다: 세션1 895건을 다시 굴리는 것이 아니라, 그 895건을 **두 번 접어도(또는 두 개 코드 버전으로 접어도) 같은 `GameState`가 나오는지**를 확인하는 시험이다.

**다섯 번째 발견 — `.gptrpg/events.db`(895건)는 gitignore 대상이라 이 체크아웃에만 있다.** `.gitignore:16`이 `**/.gptrpg/*`를 무시한다. 기존 `tests/test_event_schema_migration.py`가 이미 `@pytest.mark.skipif(not path.is_file())` 패턴으로 이 문제를 우회하고 있다 — 즉 **CI에서는 이 시험이 항상 건너뛰어진다.** TEST-04가 진짜 "회귀 방지" 역할을 하려면(요구사항 출처가 "다음에는 CI가 잡는다"), 895건 중 대표적인 부분(또는 전체를 export한 JSON 사본)을 **저장소에 커밋된 픽스처**로 옮기는 것을 계획이 검토해야 한다 — 로컬 파일에만 의존하면 이 요구사항이 사실상 미검증 상태로 남는다. 또한 이 파일은 전부 `schema_version=2`이지 CONTEXT.md/과거 문서가 종종 말한 "판 5"가 아니다(`tests/test_event_schema_migration.py:5-9`가 이미 이 정정을 기록했다).

**여섯 번째 발견 — 파티 상태 노출(D-17/D-18)이 `TurnContext.character_state` 하나를 세 갈래가 공유하는 구조와 정면으로 충돌한다.** `build_classifier_prompt`(`prompt_assembly.py:367`)와 `build_situation_prompt`(509줄)가 **같은 함수** `_session_block_text(ctx)`를 불러 `ctx.character_state`를 렌더링한다. `build_narration_facts`(`turn/judgments.py:159`)도 `ctx.character_state`를 그대로 옮겨 `NarrationFacts.character_state`에 넣는다. D-17은 "분류기는 안 받는다"지만 지금 구조에서 `character_state`를 파티 전체로 넓히면 분류기도 자동으로 받게 된다 — 이 세 소비처의 분기가 이번 단계의 진짜 설계 지점이다(Pattern 5).

**Primary recommendation:** `GameState`(rules_core)는 캐릭터·자원 축의 **원값을 모른다** — 룰북/캐릭터 파이썬 상수는 웹 층에만 있다(`.importlinter` contract:2가 이 경계를 강제한다). 그러므로 `GameState`는 `declare_owners`/`occupied_by`와 같은 모양으로 **"축이 얼마나 바뀌었는가"의 순수 델타/연산 이력만** 담고, "시작값 + 폴딩된 변화 = 지금 값"을 합치는 순수 함수를 `rules_core`(예: `reducer.py` 옆) 하나 새로 두어 `routes_characters.py::get_character_sheet`가 그 함수를 호출하게 한다. 이 모양이 D-65("파이썬 상수는 시작 값이 되고 지금 값은 기록을 접어서 나온다")를 층 경계를 어기지 않고 satisfy하는 유일한 방법이다.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 능력치→보정치 변환("쓰임" 이름 + 선택적 구간표) | 룰북 콘텐츠(`rulebooks/*.py`) | 플랫폼 어휘(`rules_core.rulebook`이 "쓰임" enum과 검증 소유) | D-01 — 이름은 플랫폼, 어느 능력치·얼마로는 룰북(`rulebook.py` 도크스트링 관례 그대로) |
| 판정 계산에 보정치를 실어 넣는 조립 | API/Backend(`session_actor.actor._prepare_resolve_check`) | — | 신원·소유권 검증이 이미 이 함수 안에 있다 — 새 조립 로직도 여기가 자연스러운 위치 |
| 자원 변화량("축·동작·양") 계산 | `rules_core`(순수 함수, D14 경계 — AI가 못 건드림) | 룰북 데이터가 축·동작·양의 **내용**을 선언 | D-05/D-06 — 계산은 사람이 검산 가능한 순수 코드(D-04), 주사위는 `Roller`를 통해서만 |
| 지금 값 = 시작값 + 폴딩된 변화 | `rules_core`(신규 순수 함수) 결합, 시작값은 API/Backend(`characters_data.py`)에서 주입 | Database/Storage(`event_log`)가 원천 기록 | `GameState`는 rules_core에 있고 characters_data.py는 web 층 — 층 경계상 `GameState`가 시작값을 직접 알 수 없다 |
| 결과 카테고리 닫힌 목록(GM 대응 목록류) 선언·선택 | AI 에이전트 층이 선택(닫힌 목록에서), 룰북 데이터가 목록 내용을 선언 | `session_actor`가 확인 게이트(D-09/D-10)를 소유 | D-11 — AI는 고르고 서술만, 숫자가 실제로 변할 때만 사람 확인이 붙는다 |
| 소지품 대조(가지고 있는가) | API/Backend(`session_actor` 또는 새 검증 함수) | AI 에이전트가 후보 이름을 뽑음(closed menu = 캐릭터 현재 슬롯 값) | D-15 — "AI는 고르고, 판단은 코드가"라는 기존 D14/D16 경계와 같은 모양 |
| 파티 전원 상태 노출 | AI 에이전트 층(`turn.context`/`turn.judgments`/`agents.prompt_assembly`) | — | D-17/D-18 — 에이전트별로 받는 것이 코드에 명시(D-66/ARCH-06 연장) |
| 자원 변화 화면 표시 | Frontend(`StatusPane.tsx`) | API 응답 계약(`routes_characters.py`) | RULE-07/D-19 — 기존 여섯 형태 렌더 갈래가 이미 있다, 새 갈래가 아니라 변화 강조만 얹는다 |
| `EVENT_SCHEMA_VERSION` 7→8 + `reducer.py` 분기 | Database/Storage(`event_log/schema.py`) ↔ `rules_core`(`reducer.py`) | — | 08-CONTEXT.md D-06 규율 — 두 파일이 반드시 같은 커밋 |

## Standard Stack

이 단계는 새 외부 라이브러리를 설치하지 않는다 — 전부 기존 저장소 관례(순수 파이썬 `dataclasses`/`typing.Literal`, `.importlinter` 층 계약)로 구현 가능하다. 필요한 것은 **신규 내부 능력**(주사위식 파서, 델타 폴딩 결합 함수)이지 서드파티 패키지가 아니다.

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dataclasses`(표준 라이브러리) | `[VERIFIED: pyproject.toml — Python 3.13/3.14, tests/__pycache__ 파일명 cpython-314]` | 새 사건 페이로드·변화량 선언 값 객체 | `entities.py`·`rulebook.py`·`context.py` 전부 이미 이 패턴(`frozen=True`) |
| `typing.Literal` | 표준 라이브러리 | 「축·동작」의 동작 이름 판별 필드, `NoneKind`류 확장 | `ResourceAxisForm`(`entities.py:13`)이 이미 이 패턴 |
| `re`(표준 라이브러리) | 표준 라이브러리 | 주사위식(`"1d6"`, `"2d8+1"`) 파싱 — 무작위 자체는 `Roller`를 통해서만 | `agents/prompt_assembly.py`가 이미 `re`로 정규식 파싱을 함(`_FENCE_MARKER_PATTERN`) — 새 도구가 아니다 |

### Supporting

새로 도입할 서드파티 패키지가 없다. 주사위식 파서(`"1d8"`, `"2d6+1"`, `"-1d4"` 등)는 `dice`/`d20`류의 PyPI 패키지를 쓰지 않는다 — `rules_core`는 `.importlinter` contract:1(시간·무작위·파일·네트워크·비동기 금지)을 받는 층이고, 필요한 문법이 "NdM(+K)" 정도로 매우 좁아 외부 의존을 들이는 것이 오히려 이 저장소의 "필요한 만큼만 만든다" 관례와 어긋난다.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 자체 정규식 파서로 "NdM(+K)" 파싱 | `d20`/`dice`(PyPI) 같은 주사위식 라이브러리 | 문법이 더 풍부(재굴림·킵/드랍 등)해지지만, 이 저장소에서 실제로 필요한 문법은 좁고(D-06은 "주사위" 하나만 언급) `.importlinter`가 `rules_core`에 무작위·시간 관련 모듈을 통째로 금지하므로 외부 패키지의 랜덤 소비 부분을 `Roller` 뒤로 감추는 어댑터 작업이 필요해져 자체 파서보다 복잡도가 더 커진다 |
| `GameState`에 캐릭터 수치 원값을 직접 저장 | `GameState`가 시작값(파이썬 상수)까지 함께 들고 있게 만든다 | `.importlinter` contract:2 위반 — `rules_core`가 `web.characters_data`를 알아야 하는데 그 반대 방향 계층이다. `initial_state(session_id)` 시그니처도 캐릭터 인자를 받도록 바뀌어 기존 시험·CLI 호출부 전부가 깨진다 |

**Installation:** 없음 — 코드 신설.

## Package Legitimacy Audit

**해당 없음.** 이 단계는 외부 패키지를 설치하지 않는다. 새로 필요한 능력(주사위식 파서, 자원 델타 폴딩)은 전부 순수 파이썬 표준 라이브러리로 구현 가능하다는 것을 위 Standard Stack에서 확인했다 — Package Legitimacy Gate는 적용 대상이 없다.

## Architecture Patterns

### System Architecture Diagram

```
[플레이어 확인 클릭]
      │  ConfirmRequest(move, stat, declare_seq, character_id, ...) — target/modifiers 칸 D-02로 폐기
      ▼
web/routes_actions.py::confirm() ──신원 대조(TRUST-02, 기존)──┐
      │  character = get_character(body.character_id)          │ 기존 코드, 변경 없음
      ▼                                                          │
[신규] build_stat_modifier(character.stats, stat=body.stat,      │
        rulebook.stat_usage) → Modifier | target 값              │ D-01/D-02, RULE-02/03
      │
      ▼
ResolveCheck(move, stat=body.stat[신규 칸], modifiers, target, ...)
      ▼
session_actor/actor.py::_prepare_resolve_check
      │  resolve_2d6 / resolve_d100 (기존, 무변경) → CheckOutcome
      │  require_band(rulebook.grade_bands, outcome.grade) → GradeBand
      │    (counts_as_failure 기존 + [신규] costs 세 번째 칸, D-13/RULE-14)
      ▼
check_resolved 사건(기존, 무변경)
      │
      ▼
[신규] AI가 결과 목록(D-11, 룰북 선언)에서 항목 하나 선택 + 서술
      │  항목에 「축·동작·양」이 붙어 있음(D-05/D-07) — 목록 없으면 재량 판정(D-09)
      │  숫자가 실제로 안 변하는 항목도 목록에 있다(D-09)
      ▼
[숫자가 변하는가?] ──아니오──▶ 서술만, 새 사건 없음
      │ 예
      ▼
D-10: 그 캐릭터를 점유한 사람에게 확인 요청(기존 점유·신원 재사용)
      ▼
[신규 사건] resource_changed(character_id, changes=[(axis, op, amount, rolls?)], caused_by_seq=check_resolved.seq)
      │  EVENT_SCHEMA_VERSION 7→8, reducer.py 분기 반드시 같은 커밋(08-CONTEXT D-06 규율)
      ▼
rules_core/reducer.py::apply_event
      │  GameState에 캐릭터별 원시 변화 이력만 누적(원값은 모른다)
      ▼
[신규 순수 함수] resolve_character_stats(starting: Entity.stats, deltas) → tuple[StatEntry,...]
      │  QUAL-06: max 클램프가 여기서 일어난다
      ▼
web/routes_characters.py::get_character_sheet — 시작값(characters_data.py) + 폴딩 결과 결합
      ▼
frontend/StatusPane.tsx — 기존 여섯 형태 렌더 재사용 + 변화 강조(D-19, RULE-07)

[병렬 경로 — 파티 상태]
web/routes_actions.py::confirm() ── list_characters() 넷 전원의 Entity.stats + GameState 델타
      ▼
turn/context.py::build_turn_context — 신규 party_state 필드(D-17/D-18)
      ▼
agents/prompt_assembly.py — build_situation_prompt·build_gm_prompt만 party_state 렌더
                              build_classifier_prompt는 기존 character_state(행위자 1인)만 유지
```

### Recommended Project Structure

새 파일보다 기존 모듈 확장이 `.importlinter` contract:2와 맞는다.

```
src/gptrpg/
├── rules_core/
│   ├── entities.py        # (무변경 가능성 높음 — StatEntry 여덟 칸이 이미 여섯 형태를 담는다)
│   ├── reducer.py         # GameState에 델타 이력 표 신설 + resource_changed 분기 + resolve_character_stats() 신규
│   ├── rulebook.py        # ResourceAxisDecl에 stat_usage(D-01) 신설, GradeBand에 costs(D-13) 신설
│   ├── resolution.py      # (가능하면 무변경 — 등급 산출 로직은 안 건드림)
│   ├── dice.py            # Roller/PercentileRoller에 roll_die(sides) 신설(D-06)
│   └── resource_change.py # [신규 제안] 「축·동작·양」 값 객체 + 순수 적용 함수(주사위식 파싱 포함)
├── event_log/
│   ├── schema.py           # EVENT_SCHEMA_VERSION 8, ResourceChanged 사건 신설
│   └── replay_roller.py    # ReplayRoller/LiveRoller에 roll_die(sides) 신설(D-06)
├── rulebooks/
│   ├── dungeonworld_like.py  # stat_usage 선언 + 결과 목록(GM 대응류) 선언
│   ├── openquest.py           # stat_usage 선언 + 결과 목록 선언
│   └── cairn.py                # named_slots 소지품 대조용 선언, 결과 목록(있다면)
├── session_actor/
│   └── actor.py            # ResolveCheck.stat 신설, _prepare_resolve_check가 보정치 조립
├── turn/
│   └── context.py          # build_turn_context에 party_state 신설
├── agents/
│   ├── context.py          # TurnContext/NarrationFacts에 party_state 칸 추가 검토
│   └── prompt_assembly.py  # 파티 상태 포맷터 신설, 분류기용 기존 포맷터와 분리
├── web/
│   ├── routes_actions.py   # confirm()이 stat_modifier 조립 + 자원 변화 확인 게이트
│   └── routes_characters.py # get_character_sheet가 시작값+델타 결합 호출
tests/
└── fixtures/                # [신규 제안] TEST-04용 커밋된 session1 이벤트 사본
```

### Pattern 1: 능력치 → 보정치 — 「쓰임」 선언과 조립 지점

**What:** `ResolveCheck`가 `stat: str` 칸을 새로 받고, `_prepare_resolve_check`(또는 `confirm()` 라우트)가 확인된 캐릭터의 `StatEntry`에서 그 칸을 찾아, 룰북이 선언한 「쓰임」에 따라 `Modifier(FLAT, ...)`(2d6류) 또는 `target`/`skill` 값 자체(d100류)로 변환한다.

**When to use:** RULE-02/RULE-03/D-01/D-02 전체 — 모든 판정 확인 경로(웹·CLI).

**Example (권고 모양, 미검증 — `[ASSUMED]`):**
```python
# rules_core/rulebook.py에 추가할 형태 (권고)
StatUsage = Literal["add_flat_modifier", "used_as_target"]
"""쓰임 이름 — 플랫폼 어휘(D-01). 2d6류는 값이 판정 합계에 그대로 더해지고
(add_flat_modifier), d100류는 값 자체가 목표값이 된다(used_as_target)."""

@dataclass(frozen=True)
class ResourceAxisDecl:
    name: str
    form: ResourceAxisForm
    none_kind: NoneKind | None = None
    slot_count: int | None = None
    stat_usage: StatUsage | None = None          # 신규 — 판정에 쓰이는 축만 채운다
    value_to_modifier_bands: tuple[...] | None = None  # 신규 — 필요한 룰북만(D-01 "필요한 룰북만")
```

**근거(코드로 확인):**
- `session_actor/actor.py:102-122` — `ResolveCheck`에 현재 `stat` 칸이 없다.
- `web/routes_actions.py:504-514` — `confirm()`이 `ResolveCheck(move=..., modifiers=..., target=body.target, ...)`을 만들 때 `body.stat`(384줄에서 `ConfirmAction`에는 넘겼던 값)을 버린다.
- `web/routes_actions.py:445-447` — `character = get_character(body.character_id)`로 캐릭터를 이미 불러왔으나 442~514줄 어디서도 `character.stats`를 읽지 않는다.
- `web/api/client.ts:96-115`(프런트) — `confirmAction`이 `target`/`modifiers` 필드를 아예 안 보낸다 → OpenQuest 판정은 지금 서버 쪽 기본값 `DEFAULT_TARGET=10`(`grading.py:8`)으로 굴러간다는 뜻(실질적으로 깨져 있음).
- `rulebooks/openquest.py:74-86` — `difficulty_modifier()`가 "이름→숫자" 변환을 이미 룰북 쪽에 갖고 있다(D-02가 재사용해야 할 기존 패턴).

### Pattern 2: `EVENT_SCHEMA_VERSION` 7→8 체크리스트

**What:** 새 사건 종류(`ResourceChanged` 등)를 추가할 때 스키마 판을 올리는 것과 `reducer.py` 분기를 **반드시 같은 커밋**에 넣어야 한다는, 이 저장소가 이미 세 번 문서화한 규율(08-CONTEXT.md D-06)을 그대로 따른다.

**체크리스트(기존 사고 세 번의 패턴에서 추출, `reducer.py:244-283` 참조):**
1. `event_log/schema.py`에 새 pydantic 모델(`ResourceChanged(EventEnvelope)`) 추가, `EVENT_SCHEMA_VERSION`을 8로 올리고 도크스트링에 「판 7→8」 절 추가(기존 판 1~7 절의 서술 관례를 그대로 잇는다).
2. 같은 파일의 `GameEvent = Annotated[Union[..., ResourceChanged], Field(discriminator="event_type")]`에 새 클래스를 반드시 추가 — 빠뜨리면 `parse_event`가 그 사건을 아예 못 읽는다(다른 아홉 종류처럼).
3. `session_actor/actor.py`에 `_EVENT_CLASSES` 딕셔너리(253-264줄)와 새 `Command`(예: `RecordResourceChange`) + `_prepare_record_resource_change` 추가.
4. **`rules_core/reducer.py::apply_event`에 `resource_changed` 분기를 반드시 같은 커밋에 추가** — 빠뜨리면 이 종류가 하나라도 있는 세션이 폴링마다 `UnknownEventType`을 맞고 영구히 안 열린다(244-282줄의 세 주석이 이 정확한 사고를 세 번 기록해 뒀다: `scene_illustrated`, `character_occupied`, `safety_flagged`, `action_classified` 넷 다 이 패턴을 따른다).
5. 옛 기록(판 8 미만)에는 이 사건 종류가 아예 없으므로 하위 호환은 자동이다(`scene_illustrated` 도입 때와 같은 패턴 — "새 종류가 늘 뿐이라 옛 기록에는 그 종류가 없다").
6. `tests/test_event_schema_migration.py`에 판 8 스모크 시험 추가(기존 판 6 스모크와 같은 모양) — `.gptrpg/events.db`(판 2, 895건)와 `.gptrpg/uat9.db`(판 5, 221건) 둘 다 예외 없이 접히는지 확인.

**QUAL-01(사건 순서 어긋남 감지) — 근거:**
`event_log/store.py:100`의 `read_events`가 `"...ORDER BY seq"`로 항상 정렬해서 돌려준다 — `rules_core/reducer.py::apply_event`/`fold`는 이 정렬에 전적으로 기대고 있고 스스로는 순서를 검사하지 않는다(REQUIREMENTS.md 자신이 "지금은 저장소가 항상 정렬해서 넘겨주기 때문에 우연히 문제가 안 생긴다"고 정직하게 적어 뒀다). 권고 모양: `fold()`(reducer.py:286-294) 안에서 각 사건을 접기 전에 `payload["seq"] <= state.last_seq`(초기값 -1)면 새 예외 `OutOfOrderEvent(expected_min, got)`를 던진다 — `UnknownEventType`과 같은 모양(사건 종류·순번을 속성으로 노출, 조용히 넘어가지 않는다).

**QUAL-02(형식 표시 빠짐 vs 진짜 구버전) — 근거:**
`event_log/schema.py:104-109`의 `EventEnvelope.schema_version: int`는 **기본값 없는 필수 필드**다 — `pydantic`이 이미 "칸 자체가 아예 없는 레코드"를 `ValidationError`로 거부한다(조용히 통과 안 함). 반면 "칸은 있는데 값이 오래된 것"(예: `schema_version=2`)은 `reducer.py` 전체가 이미 쓰는 `if schema_version >= N` 분기 패턴(예: 144-159줄의 `action_declared`)으로 정상 처리된다. 즉 **두 상황은 이미 서로 다른 코드 경로로 갈라져 있다** — 남은 일은 "칸 자체가 없는" 경우의 pydantic `ValidationError`가 이 저장소 관례(사유·식별자를 속성으로 노출)를 안 따른다는 점뿐이다. 권고: `event_log/schema.py::parse_event`에서 `EVENT_ADAPTER.validate_json`을 `try/except ValidationError`로 감싸 프로젝트 예외(예: `CorruptEventRecord(reason, event_type_if_known)`)로 재던진다 — `SafetyFlagged`가 이미 지키는 "자유 문자열을 예외 메시지에 안 싣는다"(T-10-03) 관례를 함께 지킨다.

### Pattern 3: D-05 선언 형식 — 「축 · 동작 · 양」과 GameState 폴딩 모양

**What:** 결과 목록 항목(RULE-13/D-11)에 붙는 변화량 선언은 `(axis: str, operation: <플랫폼 동작 이름>, amount: int | str)` 세 칸 튜플의 목록이다. `axis`는 룰북 어휘(그 룰북이 이미 `ResourceAxisDecl.name`으로 선언한 이름), `operation`은 플랫폼 어휘, `amount`는 고정 정수 또는 주사위식 문자열(D-06).

**여섯 표현 형태별 "변화"의 뜻(우선순위 질문 5에 대한 답, 저장소에 실사용 예 없음 — `[ASSUMED]`, 시험 픽스처로만 검증 권고):**

| `form` | 무엇이 "변한다"는 뜻인가 | 권고 `operation` 값 | `amount`의 뜻 |
|--------|------------------------|---------------------|----------------|
| `numeric` | `current`가 오르내림(체력·기술값 등) | `"delta"` | 부호 있는 정수 또는 주사위식(`"-1d6"`) |
| `clock` | `current`(칸)가 나아감 | `"advance"` | 몇 칸 나아가는지(보통 고정 정수 1) |
| `named_slots` | 빈 슬롯을 채우거나 채운 슬롯을 비움 | `"fill"` / `"clear"` | 채울 값(문자열, `fill`일 때) 또는 인덱스/이름(`clear`일 때) |
| `tag_list` | 태그를 붙이거나 뗌 | `"add_tag"` / `"remove_tag"` | 태그 문자열 |
| `usage_die` | 주사위 등급이 한 단계 내려가거나 소진됨 | `"step_down"` / `"deplete"` | 없음(고정 감소 규칙) 또는 목표 면수 |
| `none` | 변할 수 없음(D-15 — 대조할 목록 자체가 없다) | — | 이 축은 결과 목록의 대상이 될 수 없다 — 룰북 등록 검증에서 걸러야 함 |

이 표는 **"동작 이름만 늘리면 나머지 원자 연산이 자란다"는 D-05/RULE-09의 근거를 형태별로 구체화한 것**이다 — 나중에 "상태를 붙인다"(`APPLY_CONDITION`, `docs/GPTRPG-M0-decisions.md:215`의 D7 예시)가 추가돼도 이 세 칸 모양(대상·동작·값)을 그대로 재사용할 수 있다.

**GameState 폴딩 모양(권고, 기존 표 관례를 따름):**

기존 `GameState`(`reducer.py:57-106`)의 확립된 패턴 — `declare_owners: dict[int, str]`, `occupied_by: dict[str, str]`, `confirmed_declares: dict[int, ConfirmedDeclareRecord]` — 은 전부 "사건을 접을 때 `dict(state.X)`로 복사 → 갱신 → `replace(state, X=new_dict)`"다. 자원 델타도 같은 모양을 따르는 것이 이 저장소 규율과 가장 잘 맞는다:

```python
# rules_core/reducer.py에 추가할 형태 (권고, [ASSUMED])
character_resource_ops: dict[tuple[str, str], tuple[ResourceOp, ...]] = field(default_factory=dict)
"""(character_id, axis_name) -> 그 축에 적용된 연산 이력(순서 보존, 튜플).
GameState는 시작값을 모른다(rules_core는 web.characters_data를 알 수 없다,
.importlinter contract:2) — "지금 값"은 이 이력을 시작값에 적용하는
별도의 순수 함수(resolve_character_stats)가 만든다."""
```

`resolve_character_stats(starting: tuple[StatEntry, ...], ops: Mapping[str, tuple[ResourceOp, ...]]) -> tuple[StatEntry, ...]`는 `rules_core` 안의 새 순수 함수(예: `reducer.py` 옆 또는 `resource_change.py`)로 두고, `routes_characters.py::get_character_sheet`가 `entity.stats`(시작값)와 `GameState.character_resource_ops.get(character_id, ...)`(폴딩된 이력)를 이 함수에 넘겨 "지금 값"을 만든다. **QUAL-06(최대치 클램프)은 이 함수 안에서 일어난다** — `numeric`/`clock` 형태에서 `current`가 `max`를 넘지 않도록 매 연산 적용 후 clamp한다(`entities.py:81-82`의 `InvalidStatEntry`가 이미 `max < 0`을 막지만 "런타임에 current가 max를 넘는 것"은 별개 방어가 필요하다 — 지금 `_validate_form_payload`는 그 방어를 안 한다, `entities.py:89-163` 확인).

**D-06 주사위 재사용 — 근거와 갭:**
`rules_core/dice.py::Roller`(6-16줄)에는 `roll_d6()`뿐이고, `PercentileRoller`(18-33줄)에는 `roll_tens()`/`roll_units()`뿐이다. **면수를 자유롭게 굴리는 메서드가 없다** — 던전월드·Cairn류 실제 피해 주사위(`1d6`, `1d8` 등)를 표현할 수단이 지금 저장소에 전혀 없다(`grep`으로 `rulebooks/*.py` 전체를 확인해도 damage-dice 선언이 0건). 권고: `Roller`/`PercentileRoller`에 `roll_die(self, sides: int) -> int` 하나를 추가(둘 다 확장이지 변경이 아니다 — `PercentileRoller` 신설 때 쓴 "기존 프로토콜은 한 글자도 안 고친다" 관례 재사용). `session_actor/live_roller.py::LiveRoller`에 `secrets.randbelow(sides) + 1` 한 줄 추가. `event_log/replay_roller.py::ReplayRoller`는 **이미 면수 무관한 평평한 반복자**이므로(`_next_roll()`, 54-59줄) `roll_die`도 `return self._next_roll()` 한 줄로 끝난다 — 구조 변경 없음.

**중요한 정정(우선순위 질문 6과 직결):** `ReplayRoller`는 지금 프로덕션 코드 어디에서도 안 쓰인다(`grep -rln ReplayRoller src/gptrpg/`가 자기 자신만 나온다) — 시험에서만 쓰인다. `gptrpg replay`/`rebuild_state`는 판정을 **다시 굴리지 않고** `CheckResolved.rolls`에 이미 기록된 숫자를 읽어 상태만 다시 접는다. 따라서 D-06의 "재생 시 같은 눈이 나오는 것을 replay_roller.py가 보장한다"는 문장은, 실제로는 **주사위를 실제로 다시 굴리는 것이 아니라 그 결과 숫자를 사건에 남기고 fold()가 그 숫자를 그대로 읽는다**는 뜻으로 해석해야 한다 — 새 `resource_changed` 사건에도 `CheckResolved.rolls`와 같은 모양으로 `rolls: list[int] | None`(주사위식이었을 때만)을 남기고, `amount`(실제로 적용된 최종 정수)를 별도로 남겨 폴딩은 `amount`만 읽으면 되게 하는 것을 권고한다(D-04 "검산 가능"과도 맞다 — 화면에 "1d6=4" 식으로 눈을 보여줄 수 있다).

### Pattern 4: `resolve_2d6`/`resolve_d100` 등급 산출 어긋남 — 고칠 것인가

**발견(코드로 확인):**
- `resolve_2d6`(`resolution.py:70`) → `grade_for_total(total, target)`(`grading.py:12-22`) — `WEAK_HIT_BAND=3`이 **모듈 상수로 하드코딩**되어 있고 등급 **이름**("strong_hit"/"weak_hit"/"miss")까지 함수가 직접 만든다. 룰북 선언(`rulebook.grade_bands`)을 인자로도 안 받는다.
- `resolve_d100`(`resolution_d100.py:72-151`) → `grade_for_margin(margin, is_doubles, bands)`(`rulebook.py:221-231`) — `bands`(=`rulebook.grade_bands`)를 인자로 받아 완전히 룰북 선언에서 등급을 정한다.
- 그러나 두 방식 모두 최종적으로 `SessionActor._prepare_resolve_check`(`actor.py:663-666`)의 `require_band(rulebook.grade_bands, outcome.grade)`를 거쳐 `counts_as_failure`(그리고 D-13이 더할 `costs`)를 **이름으로 재조회**한다.

**이것이 D-13에 미치는 영향:** D-13은 `GradeBand`에 세 번째 독립 칸(`costs: bool` 등)을 추가하는 것이다. `require_band`는 **이름만으로 밴드를 찾는 함수**(`rulebook.py:294-299`)이므로, `resolve_2d6`이 등급 경계를 하드코딩해서 계산하든 `resolve_d100`이 룰북 선언에서 계산하든 상관없이 **결과 이름이 룰북이 선언한 이름 목록 안에 있기만 하면** 새 `costs` 칸을 똑같이 읽어낼 수 있다. `dungeonworld_like.py:19-23`의 `DUNGEONWORLD_GRADE_BANDS`가 `grade_for_total`이 만드는 세 이름과 우연히 정확히 일치하기 때문에 지금 이 조회가 성립한다.

**정직한 결론:** D-13 구현은 이 어긋남을 고치지 않고도 안전하다 — `require_band`가 두 계산 경로의 차이를 이미 흡수하고 있다. 다만 **어긋남 자체는 남는다**: `resolve_2d6`을 쓰는 어떤 새 2d6 룰북이 `WEAK_HIT_BAND` 경계를 다르게 선언하고 싶어도(D-01 정신상 "룰북이 변환 규칙을 선언한다"), `grading.py`가 그 구간을 룰북에서 안 받으므로 반영할 방법이 없다. RULE-02~16 중 어느 것도 이 수정을 직접 요구하지 않고, ROADMAP 자체가 "이 단계가 가장 무겁다"고 경고했으므로 — **이번 단계 범위 밖으로 명시적으로 남기고, 계획 문서에 "알려진 제약"으로 기록하는 것을 권고한다.** 억지로 고치면 `grade_for_total`의 시그니처가 바뀌어 `resolution.py`를 쓰는 기존 시험 전부를 다시 열게 된다(로드맵이 피하려던 정확히 그 "같은 파일 두 번 열기").

### Pattern 5: 파티 상태 노출 — `TurnContext`/`NarrationFacts` 공유 지점 분기

**발견(코드로 확인):**
- `agents/context.py:63-79`의 `TurnContext.character_state: tuple[StatEntry, ...]`는 **행위자 한 명**의 상태값이다(단일 튜플, `Entity`가 아니다 — 이름도 없다).
- `prompt_assembly.py:324-374`의 `build_classifier_prompt`와 `prompt_assembly.py:465-516`의 `build_situation_prompt`가 **똑같이** `session = _session_block_text(ctx)`를 부른다(367줄·509줄) — `_session_block_text`(302-307줄)가 `_format_character_state(ctx.character_state)`를 렌더링한다.
- `turn/judgments.py:140-162`의 `build_narration_facts`가 `character_state=ctx.character_state`(159줄)를 그대로 옮겨 `NarrationFacts.character_state`에 넣는다 — `master_gm.narrate()`도 결국 같은 값을 받는다.

**문제:** D-17은 분류기(`action_classifier`)는 파티 상태를 받으면 **안 된다**고 정했다. 그런데 `ctx.character_state`는 분류기와 상황판단이 **같은 함수**(`_session_block_text`)로 렌더링되므로, 이 필드를 파티 전체로 그냥 넓히면 분류기도 자동으로 받게 된다. 반대로 D-01/D-03(어느 능력치로 판정할지 AI가 제안)을 위해 분류기는 **행위자 자신의** 스탯은 계속 봐야 한다(지금 이미 보고 있다) — "파티 전체를 안 받는다"이지 "자기 자신도 안 받는다"가 아니다.

**권고(설계 지점, `[ASSUMED]`):** `TurnContext.character_state`(행위자 1인)는 그대로 두고 — 분류기는 이 칸만 계속 쓴다 — **새 필드** `party_state: tuple[Entity, ...]`(선언 순서 그대로 넷)를 `TurnContext`에 추가한다. `build_classifier_prompt`는 이 새 필드를 렌더링하지 않는다(코드에 그냥 안 씀 — `EntityJudgeContext`/`ClockJudgeContext`가 이미 "타입에 없는 칸은 못 받는다"는 원칙을 세웠지만, `TurnContext`를 또 쪼개면 파급이 너무 커지므로 "코드가 명시적으로 안 읽는다"로 타협 — ARCH-06의 정신인 "에이전트별로 무엇을 받는지 코드에 명시"는 지켜지지만 타입 차원 강제는 아니다, 계획 단계에서 이 트레이드오프를 사람에게 확인받을 것을 권고). `build_situation_prompt`는 `_session_block_text` 대신 **새 포맷터**(`_session_block_text_with_party` 또는 유사)를 불러 `party_state`를 함께 렌더링한다. `build_narration_facts`도 `character_state=ctx.party_state`로 바뀌어야 하므로 `NarrationFacts.character_state`의 타입이 `tuple[Entity, ...]`로 넓어진다(master_gm은 이미 `_format_character_state`가 아니라 party 전용 포맷터를 새로 써야 함 — `_format_scene_entities`가 이미 `tuple[Entity, ...]`를 순회하는 비슷한 모양을 갖고 있다, `prompt_assembly.py:186-193`).

**참고 — `_format_character_state`(196-247줄) 자체는 그대로 재사용 가능.** 이미 여섯 형태 전부를 처리하는 완성된 렌더러다(11-07이 만듦) — party 렌더러는 이 함수를 캐릭터마다 한 번씩 불러 이름과 함께 이어 붙이면 된다(`_format_scene_entities`가 하는 것과 같은 모양).

### Pattern 6: 소지품 대조 — D-15/D-16

**발견:** 소지품을 세는 룰북은 지금 저장소에 Cairn(`named_slots`, 10칸) 하나뿐이다(`cairn.py:45`). AI가 "이 행동은 밧줄을 쓴다"까지 뽑고 실제로 있는지는 코드가 대조해야 한다(D-15). 그런데 아이템 이름은 **닫힌 목록으로 미리 정의된 것이 아니라 그 캐릭터의 `slot_values`에 실제로 적힌 자유 문자열**이다(`cairn.py:80-93`의 `"장검"`, `"랜턴"`, `"밧줄 15m"` 등) — 세션마다·캐릭터마다 다르다.

**권고 모양:** "닫힌 목록"은 미리 고정된 게 아니라 **그 순간 그 캐릭터의 `slot_values`(None 제외)를 매번 새로 만드는 목록**이다 — `action_classifier`가 룰북의 `moves` 고정 목록에서 고르는 것과 같은 패턴이지만, 목록의 출처가 룰북 선언이 아니라 **개체의 현재 상태**라는 점이 다르다. AI(분류기 또는 신규의 좁은 판단 하나)가 이 목록에서 문자열 하나(있으면) 또는 "해당 없음"을 고르면, 코드가 `stat.slot_values`에 그 정확한 문자열이 있는지 다시 한번 대조(이중 방어, `_prepare_confirm`의 소유권 이중 검사와 같은 신중함)한 뒤 판정을 이어간다 — 없으면 D-16이 아니라 D-09/D-16의 재량 판정 경로(소급 선언 여부는 룰북이 `flashback` 유사 축을 선언했는지에 달림)로 넘어간다.

**D-16(소급 선언):** 룰북이 "허용 + 비용 축"을 선언하고 "이번엔 얼마"만 AI가 제안 + 사람 확인 — 이것도 D-05의 「축·동작·양」 세 칸을 그대로 쓴다(축=룰북이 미리 선언, 동작·양=그 순간 정해짐). 새 형식이 필요 없다는 CONTEXT.md의 판단이 여기서 확인된다.

### Pattern 7: 결과 카테고리 닫힌 목록 — 던전월드 GM 대응 목록의 데이터 모양

**출처:** `.planning/research/RULEBOOK-SURVEY.md` §2-C·§3-C (이 저장소가 이미 수행한 서베이, `[CITED]`/`[확인됨]` 표시를 그대로 물려받는다). 던전월드/아포칼립스 월드의 GM 대응 목록은 실제로 8~10개 고정 카테고리(위협을 드러낸다/자원을 소모시킨다/불리한 위치로 몰아넣는다/피해를 입힌다/다가올 위협을 알린다/대가를 요구하되 이득을 준다/가진 것을 빼앗는다/세계의 특성을 이용한다/전선의 징조를 진행시킨다, `docs/GPTRPG-M0-decisions.md:412`)로 실재하는 표준 형태다.

**데이터 모양(권고, `[ASSUMED]` — 이번 단계는 목록 데이터를 실제로 채우는 것도 범위이지만 세 룰북 각각의 실제 항목 문구는 사람이 정할 재량 영역):**
```python
@dataclass(frozen=True)
class OutcomeCategory:
    """결과 목록(RULE-13/D-11)의 항목 하나 — "무슨 일이 일어나는 종류"까지만
    데이터다. "이 장면 이 순간의 구체적 문장"은 영원히 AI 재량이다
    (RULEBOOK-SURVEY.md §3-C, D-11이 이 경고를 그대로 인용)."""
    category_id: str          # 플랫폼이 부여하는 식별자 — 룰북 어휘 아님
    changes: tuple[ResourceChangeDecl, ...]  # D-05/D-07 — 이 항목에 붙는 자원 변화, 빈 튜플 정상(D-09)

@dataclass(frozen=True)
class OutcomeList:
    categories: tuple[OutcomeCategory, ...]  # 빈 튜플이 정상값(D-07 귀결 — 목록 없으면 재량 판정)
    max_picks: int = 1                        # D-12 — "하나 또는 여럿" 룰북 선언
```

**빈 목록이 정상값인 스펙트럼(우선순위 질문 7, `RULEBOOK-SURVEY.md`가 이미 정리):** 실제 출간작 중에도 "완전 GM 재량"(목록 자체가 없음, §2-C 항목 5)이 존재한다 — Cairn류가 이 끝에 해당할 가능성이 높다(SRD가 세이브 실패 시 결과를 절차로 안 정함). "닫힌 목록에서 고름"이 던전월드 GM 대응, "부분 성공 사다리"가 PbtA 7-9, "오라클/절차형"이 Ironsworn Pay the Price — 세 계열 다 실재하며 이 프로젝트가 담아야 할 스펙트럼의 서로 다른 점이다. **결론: `OutcomeList`가 없는(빈 튜플인) 룰북은 정상이고, D-07의 귀결대로 판정만으로는 숫자가 안 변하며 D-09/D-10의 재량 판정 경로로 넘어간다** — 이것이 RULE-13("목록이 없는 룰북은 전부 재량 판정으로 간다")과 정확히 일치한다.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| 임의 면수 주사위 굴림 | 새 무작위 소스(`random`/`secrets` 직접 호출을 `rules_core` 밖 아무 데나) | `Roller`/`PercentileRoller` 프로토콜에 `roll_die(sides)` 확장 + `LiveRoller`/`ReplayRoller` 구현 | `.importlinter` contract:1이 `rules_core`에서 무작위 모듈을 이미 차단한다 — 새 경로를 만들면 재생 일치(D-06)가 구조적으로 깨진다 |
| 능력치→보정치 변환 규칙 | 던전월드/OpenQuest 각각의 하드코딩된 if/elif | D-01의 "쓰임" 선언(`stat_usage`) + 필요한 룰북만 값→보정치 구간표 | D32/원칙3이 "룰북별 전용 어댑터"를 이미 폐기했다 — 플랫폼 코드에 룰북 변환식을 박으면 세 번째 룰북마다 코드를 또 고쳐야 한다 |
| 자원 변화 파이프라인(select category → apply → notify) | 매번 새 확인 화면 컴포넌트 | Phase 8의 점유·신원 검증(`read_identity`+`occupied_by`) 그대로 재사용, `ChatPane.tsx`의 기존 확인 UI 패턴(`proposal` 상태) 재사용 | D-10이 "새 권한 개념을 만들지 않는다"고 명시했다 |
| 소지품 대조("이 물건을 갖고 있나") | 아이템 이름 사전(플랫폼이 아는 아이템 목록) | 그 캐릭터의 `slot_values`(현재 상태)를 매번 닫힌 목록으로 다시 만든다 | `rules_core`가 룰북 어휘("체력"·아이템 이름)를 모른다는 경계(D32) — 아이템 사전을 만들면 그 경계가 깨진다 |
| 결과 카테고리 문구 | 카테고리별 하드코딩된 한국어 문장 여러 개 | 카테고리는 데이터(축·동작·양), 실제 문장은 AI 재량(D-11 — RULEBOOK-SURVEY.md가 명시적으로 이 경계를 못박음) | "무엇이 일어나는 종류"와 "이 장면의 구체적 문장"을 섞으면 목록을 늘릴수록 재량이 없어진다는 오해가 생긴다 |

**Key insight:** 이 단계의 위험은 "빠뜨리는 기능"이 아니라 "플랫폼 코드에 룰북 내용을 새어 넣는 것"이다 — 세 개의 층 규약(PROJECT.md)이 이미 세 번(D-01/D-05/D-32) 같은 실수를 경고했다. 새 코드를 짤 때마다 "이 이름이 던전월드/OpenQuest/Cairn 중 하나에만 있는 단어인가"를 자문하는 것이 가장 값싼 방어선이다.

## Common Pitfalls

### Pitfall 1: `EVENT_SCHEMA_VERSION`을 올리고 `reducer.py` 분기를 빠뜨림
**What goes wrong:** 새 사건 종류가 하나라도 기록된 세션이 폴링마다 `UnknownEventType`을 맞고 영구히 안 열린다.
**Why it happens:** 스키마 정의와 리듀서 분기가 서로 다른 파일(`event_log/schema.py` vs `rules_core/reducer.py`)에 있어 한쪽만 고치고 커밋하기 쉽다.
**How to avoid:** Pattern 2의 체크리스트를 계획의 단일 태스크 완료 조건으로 삼는다 — 두 파일 diff가 같은 커밋에 있는지 리뷰 체크리스트에 명시.
**Warning signs:** `reducer.py`에 `apply_event`의 `if/elif` 체인이 새 사건 이름을 언급하지 않는데 `schema.py`의 `GameEvent` Union에는 있다.

### Pitfall 2: `ResolveCheck.stat`을 더했지만 웹/CLI 중 한쪽만 고침
**What goes wrong:** 10-05가 세운 관례("웹과 CLI 두 호출부가 같은 자리·같은 조건으로 움직인다")를 어기면, 한쪽 경로는 능력치가 반영되고 다른 쪽은 그대로 깨진 채 남는다.
**Why it happens:** `web/routes_actions.py::confirm()`과 `cli/turn_flow.py`가 물리적으로 다른 파일이고, CLI는 `person_id=args.player, character_id=args.player`(임시 값)를 쓰는 등 애초에 신원 개념이 다르다.
**How to avoid:** D-02가 이미 "웹과 CLI 둘 다 같은 커밋에서 닫는다"를 못박았다 — 이 단계 계획도 `confirm()`과 `turn_flow.py`의 대응하는 구간을 같은 태스크에 넣는다.
**Warning signs:** `_parse_modifier`(두 파일에 각각 하나씩 존재, `routes_actions.py:132`·`turn_flow.py:53`)가 한쪽만 제거되고 다른 쪽에 남아 있음.

### Pitfall 3: `GameState`가 캐릭터 시작값을 직접 저장하려 함
**What goes wrong:** `.importlinter` contract:2 위반 — `rules_core`가 `web.characters_data`를 참조하게 되어 층 계약이 깨진다. `initial_state(session_id)`의 시그니처가 캐릭터 인자를 받도록 바뀌면 기존 CLI·시험 호출부가 전부 깨진다.
**Why it happens:** "지금 값을 어떻게 만드나"를 고민하다 보면 GameState 안에 전부 넣고 싶은 유혹이 생긴다.
**How to avoid:** Pattern 3의 권고대로 GameState는 델타/연산 이력만, 시작값 결합은 별도 순수 함수(호출부가 `Entity.stats`를 인자로 넘김)로 분리한다.
**Warning signs:** `reducer.py`가 `from gptrpg.web.characters_data import ...`를 시도하는 순간 `.importlinter` 검사가 실패한다(CI에 이미 이 검사가 있다면 즉시 드러남).

### Pitfall 4: 결과 목록 항목의 "구체적 문장"을 데이터로 착각
**What goes wrong:** 목록을 늘리면 언젠가 AI 재량이 완전히 없어질 거라 오해하고, 실제로는 불가능한 "완전 자동화"를 목표로 잡는다.
**Why it happens:** "카테고리를 데이터화한다"는 말이 "서술도 데이터화한다"로 슬쩍 넓어지기 쉽다.
**How to avoid:** `RULEBOOK-SURVEY.md`가 이미 명시적으로 경고한 문장("이 장면 이 순간에 구체적으로 어떤 문장인지는 영원히 재량이다")을 계획 문서에 그대로 인용해 둔다.
**Warning signs:** "자동화율 100%"류의 목표가 대화에 등장.

### Pitfall 5: TEST-04 회귀 픽스처가 gitignore된 로컬 파일에만 의존
**What goes wrong:** `.gptrpg/events.db`는 `.gitignore:16`(`**/.gptrpg/*`)에 걸려 커밋되지 않는다 — 다른 개발자 체크아웃이나 CI 환경에는 이 파일이 없다. 기존 `test_event_schema_migration.py`가 이미 `skipif(not path.is_file())` 패턴으로 이를 우회하고 있어, 이 시험들이 **로컬 개발 환경 밖에서는 항상 조용히 건너뛰어진다.**
**Why it happens:** 로컬에 이미 실제 데이터가 있으니 그것으로 시험을 짜는 것이 가장 쉬운 길이다.
**How to avoid:** 895건(또는 대표 부분집합)을 JSON/JSONL로 export해 `tests/fixtures/`에 커밋하고, `EventStore`에 그 데이터를 적재해 재생하는 시험을 만든다 — 로컬 DB 파일 스모크 시험(`skipif`)은 **추가로 유지**하되(사람이 로컬에서 실제 파일로도 재확인 가능), CI에서 실제로 도는 것은 커밋된 픽스처 기반 시험이어야 TEST-04("다음에는 CI가 잡는다"는 요구사항 출처)의 목적이 달성된다.
**Warning signs:** 계획에 `.gptrpg/events.db`를 직접 여는 새 시험만 있고 `tests/fixtures/` 아래 커밋된 사본이 없음.

### Pitfall 6: `resolve_2d6`/`grade_for_total`의 등급 산출 어긋남을 이번 단계에서 "김에 고치려" 함
**What goes wrong:** `grading.py`의 시그니처를 바꾸면 `resolution.py`를 쓰는 기존 시험(`test_resolution_edges.py` 등)이 대량으로 깨지고, 이미 16개 요구사항이 몰린 이 단계의 범위가 더 커진다.
**Why it happens:** CONTEXT.md가 이 어긋남을 명시적으로 지적해서 "지금 고쳐야 하나"는 자연스러운 반응이지만, Pattern 4에서 확인했듯 D-13은 이 어긋남과 무관하게 안전하게 구현된다.
**How to avoid:** 계획 문서에 "알려진 제약, 이번 범위 밖"으로 명시적으로 기록하고 넘어간다 — RULE-02~16 중 이 수정을 요구하는 항목이 없다는 것을 근거로 남긴다.
**Warning signs:** 계획에 `grading.py`나 `resolution.py`의 `resolve_2d6` 시그니처 변경이 들어 있는데 그 근거로 인용된 요구사항 ID가 없음.

## Code Examples

### 주사위식 파싱 + 적용 (권고 스케치, `[ASSUMED]` — 실제 문법·엣지케이스는 계획이 정할 것)

```python
# rules_core/dice.py 확장 (권고)
class Roller(Protocol):
    def roll_d6(self) -> int: ...
    def roll_die(self, sides: int) -> int: ...  # 신규 — 임의 면수

# rules_core/resource_change.py (신규 제안 모듈, rules_core 안이므로 무작위는 Roller 통해서만)
_DICE_EXPR = re.compile(r"^(?P<sign>[+-]?)(?P<count>\d+)d(?P<sides>\d+)(?P<flat>[+-]\d+)?$")

def roll_amount(roller: Roller, amount: int | str) -> tuple[int, tuple[int, ...]]:
    """고정 정수면 그대로, 주사위식이면 Roller로 굴려 (최종값, 굴린 눈)을 돌려준다.
    D-04(검산 가능)를 위해 눈을 항상 함께 돌려준다 — 고정값이면 빈 튜플."""
    if isinstance(amount, int):
        return amount, ()
    match = _DICE_EXPR.match(amount)
    if match is None:
        raise InvalidResourceChange(f"주사위식을 해석할 수 없다: {amount!r}")
    sign = -1 if match["sign"] == "-" else 1
    count, sides = int(match["count"]), int(match["sides"])
    flat = int(match["flat"]) if match["flat"] else 0
    rolls = tuple(roller.roll_die(sides) for _ in range(count))
    return sign * (sum(rolls) + flat), rolls
```

### `ReplayRoller`의 면수 무관 확장 (기존 코드 근거)

```python
# event_log/replay_roller.py:38-52 — 기존 코드 그대로. 새 메서드는 아래처럼
# _next_roll()을 그대로 재사용하면 된다(구조 변경 없음, 눈으로 확인).
def roll_die(self, sides: int) -> int:  # 신규, sides는 검증만(재생은 이미 굴려진 값을 그대로 재생)
    return self._next_roll()
```

## State of the Art

이 단계는 외부 라이브러리 생태계의 "최신 방식"이 적용되는 영역이 아니다 — 순수 내부 도메인 모델링(값 객체·순수 함수·이벤트 소싱형 폴딩)이라 State of the Art 표는 생략한다. 유일하게 참고할 만한 변화는 **저장소 자신의 관례가 Phase 마다 확립되어 온 방식**이다 — `GradeBand`(판별 필드 + 선택적 페이로드)가 그 예이며, 이 단계도 같은 패턴을 반복한다.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `GameState`에 `(character_id, axis_name) -> ResourceOp 이력` 형태의 델타 표를 두고, 시작값 결합은 별도 순수 함수로 분리한다 | Pattern 3 | 계획이 이 대신 GameState 안에 시작값을 넣으려 하면 `.importlinter` 위반으로 되돌아가야 한다 — 재작업 |
| A2 | 「축·동작·양」의 `operation` 값 목록(delta/advance/fill/clear/add_tag/remove_tag/step_down/deplete)이 여섯 형태를 정확히 덮는다 | Pattern 3 | 실제 룰북(특히 clock/usage_die)이 이 목록으로 표현 못 하는 변화 방식을 쓰면 이번 단계에서 목록을 다시 설계해야 한다 — 다만 저장소에 이 세 형태를 실사용하는 룰북이 아직 없어 검증 데이터가 없다 |
| A3 | `TurnContext`에 `party_state: tuple[Entity, ...]` 신규 필드를 추가하고, 분류기는 "코드가 명시적으로 안 읽는" 방식으로 배제한다(타입 차원 강제가 아님) | Pattern 5 | ARCH-06 정신("타입으로 막는다")을 엄격히 지키려면 `TurnContext`를 더 쪼개야 하고 파급이 커진다 — 계획 단계에서 사람 확인이 필요한 트레이드오프 |
| A4 | `resolve_2d6`/`grade_for_total` 어긋남은 이번 단계 범위 밖으로 남긴다 | Pattern 4/Pitfall 6 | 실제로는 D-13이 이 어긋남을 노출하는 새 시나리오(새 2d6 룰북이 다른 등급 이름을 쓰는 경우)를 만들면, 이 판단을 재검토해야 한다 — 다만 이번 단계에 그런 룰북 추가는 범위에 없다 |
| A5 | D-01의 "쓰임 이름"은 최소 `add_flat_modifier`/`used_as_target` 두 값이면 현재 세 룰북(던전월드류·OpenQuest·Cairn)을 전부 덮는다 | Pattern 1 | Cairn(`D20_ROLL_UNDER`)은 지금 `_RESOLVERS`에 계산기가 없어(11-04 Task 0, declare-only) 실제 판정을 시도하지 않는다 — Cairn의 "쓰임"이 이 두 값 중 어디에 해당하는지는 확인 안 됨. d20 롤언더는 통상 "능력치 자체가 목표값"(`used_as_target`)일 가능성이 높지만 확인은 못 했다 |
| A6 | 소지품 대조용 "닫힌 목록"은 룰북이 미리 선언한 고정 목록이 아니라 캐릭터의 현재 `slot_values`를 매번 새로 만든 목록이다 | Pattern 6 | 이 판단이 틀리면 D-15의 "AI가 뽑고 코드가 대조" 흐름 전체를 다시 설계해야 한다 — 다만 `slot_values`가 자유 텍스트인 이상 다른 설계가 성립하기 어렵다(RULE-16의 "밧줄"/"튼튼한 끈" 예시가 정확히 이 문제를 지적) |

**참고:** 이 표의 항목 대부분은 "새 코드의 권장 모양"이지 "코드에 이미 있는 사실"이 아니다 — 위 Summary/Pattern들의 사실 주장(파일:줄 인용이 붙은 것)은 이 로그에 없다. 계획·디스커스 단계에서 A1~A6을 사람에게 확인받는 것을 권고한다(특히 A3은 명시적으로 논의된 적이 없다).

## Open Questions

1. **D-01의 "쓰임 이름"이 정확히 몇 가지 값을 가져야 하는가.**
   - What we know: 지금 두 룰북(2d6→FLAT 더함, d100→target 자체)이 정확히 두 갈래다.
   - What's unclear: Cairn(d20 롤언더)이 세 번째 갈래가 필요한지, 아니면 `used_as_target`으로 충분한지 — `D20_ROLL_UNDER` 계산기 자체가 아직 없다(11-04가 `declare-only`로 미룸).
   - Recommendation: 이번 단계는 두 값으로 시작하고, Cairn 실제 판정 계산기(별도 마일스톤/후속 범위)가 들어올 때 필요하면 세 번째 값을 추가한다 — `StatUsage`가 `Literal`이라 확장은 저렴하다.

2. **파티 상태(D-17/D-18)를 `TurnContext`에 얹을지, 별도 타입으로 쪼갤지.**
   - What we know: 현재 `TurnContext.character_state`가 분류기·상황판단 둘에 공유되고 있어 그냥 넓히면 D-17을 어긴다(Pattern 5).
   - What's unclear: 이 저장소가 `EntityJudgeContext`/`ClockJudgeContext`로 이미 확립한 "타입으로 막는다" 원칙을 얼마나 엄격히 지켜야 하는지 — CONTEXT.md는 구체 모양을 사람이 안 정했다.
   - Recommendation: 계획 discuss 단계에서 "타입 분리(비용 큼, 원칙에 충실) vs 필드 추가+코드 규율(비용 작음, 원칙 완화)" 트레이드오프를 명시적으로 사람에게 물을 것.

3. **TEST-04 픽스처의 크기.**
   - What we know: 원본은 895건, gitignore 대상.
   - What's unclear: 전체 895건을 커밋할지(파일 크기 부담은 작을 것 — 이벤트 하나가 JSON 한 줄, 895줄은 수백 KB 이내로 추정되나 실측 안 함) 대표 부분집합만 export할지.
   - Recommendation: 계획 단계에서 `.gptrpg/events.db`의 실제 파일 크기를 `ls -la`로 확인한 뒤 결정 — 이 조사에서는 파일 크기를 재지 않았다.

## Environment Availability

이 단계는 순수 코드/데이터 변경이며 새 외부 도구·서비스·런타임 의존성이 없다 — 기존 Python 백엔드·SQLite·기존 AI 제공자 설정을 그대로 쓴다. 이 절은 생략한다(코드/설정만 바뀌는 단계).

## Validation Architecture

`workflow.nyquist_validation`이 `.planning/config.json`에 명시적으로 `false`가 아니므로(키 자체가 없음 — `[VERIFIED: .planning/config.json]`, 파일 내용은 `{"workflow": {"_auto_chain_active": false}}`뿐) 이 절을 포함한다.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest — 저장소 전체가 이미 사용(`tests/*.py`, `[VERIFIED: tests/ 디렉터리 60+개 test_*.py 파일 확인]`) |
| Config file | `pyproject.toml`(정확한 pytest 설정 절은 이번 조사에서 안 열었다 — 계획 단계에서 확인 권고) |
| Quick run command | `uv run pytest tests/test_reducer_*.py tests/test_entities.py tests/test_rulebook.py -q`(신규 코드에 가장 가까운 기존 시험군) |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RULE-02 | 능력치 높은 캐릭터가 유리한 판정 총합을 얻는다 | unit | `pytest tests/test_resolution_stat_modifier.py -x`(신규) | ❌ Wave 0 |
| RULE-04 | 자원 변화가 사건에 남고 재생 후 같은 상태 | unit+integration | `pytest tests/test_reducer_resource_change.py -x`(신규) | ❌ Wave 0 |
| RULE-13/RULE-14 | 결과 카테고리 선택 + 대가 축 독립 | unit | `pytest tests/test_rulebook.py -k grade_band_costs -x`(확장) | 부분(`test_rulebook.py` 존재, 새 케이스 필요) |
| QUAL-01 | 순서 어긋난 사건이 예외를 던진다 | unit | `pytest tests/test_reducer_*.py -k out_of_order -x`(신규 케이스) | ❌ Wave 0 |
| QUAL-06 | 최대치 클램프 | unit | `pytest tests/test_entities.py -k clamp -x`(신규 케이스) | 부분 |
| TEST-04 | 커밋된 session1 픽스처 재생 결정론 | regression | `pytest tests/test_event_schema_migration.py -k fixture -x`(신규, 커밋된 픽스처 사용) | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** 위 Quick run command
- **Per wave merge:** Full suite green before `/gsd-verify-work`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_resolution_stat_modifier.py` — RULE-02/RULE-03 커버(능력치→보정치 조립)
- [ ] `tests/test_reducer_resource_change.py` — RULE-04/RULE-05/QUAL-01/QUAL-06 커버
- [ ] `tests/fixtures/session1_events.jsonl`(또는 유사) — TEST-04가 CI에서 실제로 돌기 위한 커밋 픽스처(Pitfall 5)
- [ ] `tests/test_dice_amount.py` — D-06 주사위식 파싱·`roll_die` 확장 커버
- [ ] Framework install: 불필요(pytest 이미 설치됨)

## Security Domain

이 프로젝트는 `security_enforcement` 설정 키가 `.planning/config.json`에 없다(부재 = 활성). ASVS 관점 검토:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | 예(재확인) | 기존 서명 쿠키(`cookie_auth.py`) 재사용 — 이 단계가 새로 만들지 않는다 |
| V3 Session Management | 예(재확인) | Phase 8의 점유(`occupied_by`) 재사용 — D-10이 명시 |
| V4 Access Control | 예 | D-10 "그 캐릭터를 점유한 사람만 자원 변화를 확인할 수 있다" — `confirm`이 이미 `identity.character_id != body.character_id`를 맨 앞에서 막는 패턴(`routes_actions.py:423`)을 자원 변화 확인에도 같은 자리·같은 모양으로 적용 |
| V5 Input Validation | 예 — 이 단계의 핵심 | D-02가 닫는 자유 숫자 입력 통로(`ConfirmRequest.modifiers`/`target`)를 서버 계산으로 대체하는 것 자체가 V5 통제. 새로 여는 자유 문자열 입력(있다면, 예: 소급 선언 사유)은 기존 `MAX_ID_LEN`/`MAX_RAW_TEXT_LEN` 상한 패턴을 재사용해야 한다(QUAL-04 관례 연장) |
| V6 Cryptography | 아니오 | 이 단계는 암호화 관련 변경 없음 |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| 클라이언트가 임의 `target`/`modifiers`를 보내 판정 결과를 조작 | Tampering | D-02 — 서버가 `StatEntry`+룰북 선언에서만 보정치를 계산, 바깥 입력은 닫힌 이름 목록(예: 난이도 이름)만 |
| 남의 캐릭터의 자원 변화를 확인 | Tampering/Elevation of Privilege | D-10 — 점유·신원 검증 재사용(`confirm()`의 기존 423줄 검사와 같은 자리) |
| 재시도가 자원을 두 번 깎음 | Tampering(중복 적용) | Phase 8의 멱등성(`AlreadyConfirmed`/`AlreadyResolved`) 위에 자원 쓰기를 올린다 — 이 단계가 Phase 8에 의존하는 정확한 이유 |
| 사건 순서 조작으로 상태 재구성이 달라짐 | Tampering/Repudiation | QUAL-01 — `fold()`가 순서를 스스로 검증(Pattern 2) |
| 자유 문자열(소급 선언 사유 등)이 AI 프롬프트로 새어 들어가 인젝션 | Tampering | `fence_player_text`(SAFE-05, D-10, 10-04) 재사용 — 새 자유 텍스트 입력이 생기면 반드시 이 함수를 거치게 한다 |

## Sources

### Primary (HIGH confidence)

- 저장소 코드 직접 열람 — `src/gptrpg/rules_core/{entities,reducer,resolution,resolution_d100,rulebook,dice,grading}.py`, `src/gptrpg/event_log/{schema,store,replay_roller}.py`, `src/gptrpg/session_actor/{actor,live_roller,projection}.py`, `src/gptrpg/web/{routes_actions,routes_characters,characters_data}.py`, `src/gptrpg/rulebooks/{dungeonworld_like,openquest,cairn,moves}.py`, `src/gptrpg/turn/{context,judgments}.py`, `src/gptrpg/agents/{context,prompt_assembly}.py`, `frontend/src/{panes/StatusPane.tsx,panes/ChatPane.tsx,api/types.ts,api/client.ts,labels.ts}`, `.importlinter`, `.gitignore`, `tests/test_event_schema_migration.py`
- `.planning/phases/12-stats-resources-inventory/12-CONTEXT.md` — 잠금 결정 D-01~D-19, canonical_refs
- `.planning/PROJECT.md` — D-65/D-66/D-67, 세 개의 층 규약
- `docs/GPTRPG-M0-decisions.md` — D7(효과 DSL)·D14(주사위 순수 코드)·D16(재량 판정)·D32(적/NPC 숫자는 룰북 선언)

### Secondary (MEDIUM confidence)

- `.planning/research/RULEBOOK-SURVEY.md` §2-C·§3-C·§3-D — GM 대응 목록·부분 성공·변하는 자원 스펙트럼(이 문서 자신이 [확인됨]/[일반지식]으로 이미 신뢰도를 구분해 둠)
- `.planning/phases/11-rulebook-vocabulary/{11-CONTEXT.md,11-VERIFICATION.md}` — 여섯 표현 형태 실사용 현황(3/6)

### Tertiary (LOW confidence)

- 이 문서 자체가 제안하는 신규 코드 모양(GameState 델타 표, 「축·동작·양」 operation 목록, 주사위식 파서, `party_state` 필드) — 전부 `[ASSUMED]`, 저장소에 실사용 예가 없어 계획·디스커스 단계에서 사람 확인 권고(Assumptions Log 참조)

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — 새 외부 의존성이 없다는 것을 `.importlinter`·기존 코드 확인으로 검증
- Architecture (신규 설계 제안): MEDIUM — 저장소 관례에서 도출했으나 실코드 존재하지 않음, 우선순위 질문 1·3·5는 사람 확인 필요
- Pitfalls/기존 갭(D-01/D-02 실패 지점, ReplayRoller 미사용, gitignore 픽스처): HIGH — 전부 파일:줄 인용으로 확인

**Research date:** 2026-08-17
**Valid until:** 이 단계 실행 완료 시점까지(코드베이스 자체 조사이므로 코드가 바뀌면 재확인 필요 — 특히 Phase 11 산출물과 겹치는 `entities.py`/`rulebook.py`는 병렬 작업 시 재확인)

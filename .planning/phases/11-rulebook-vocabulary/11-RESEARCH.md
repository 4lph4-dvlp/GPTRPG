# Phase 11: 룰북 표현 어휘 확장 — 「안 쓴다」를 말할 수 있게 - Research

**Researched:** 2026-08-15
**Domain:** 룰북 선언 스키마 확장(자원 축 그릇) · 순수 파이썬 도메인 모델링 · 등록 시점 검증 알고리즘 · AI 에이전트 문맥 설계
**Confidence:** MEDIUM-HIGH — 코드 기반 발견(우선순위 2·3·4)은 HIGH, 세 번째 룰북 라이선스 조사(우선순위 1)는 실제로 공식 페이지를 직접 열람해 MEDIUM, 서드파티 서베이 요약(Ironsworn·Black Hack·Knave 라이선스)은 LOW로 별도 표시했다.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** 룰북이 자원 축 목록을 선언하고, 캐릭터·적·NPC는 그중 자기가 가진 축의 값만 갖는다. 「이 세계에 존재하는 축」과 「이 개체가 실제로 가진 축」이 갈라진다. `characters_data.py`의 네 캐릭터와 `openquest_creatures.py`·`dungeonworld_like.py`의 적 선언이 새 형식에 맞춰 다시 쓰인다. Reversibility: costly.
- **D-02:** 자원 축 목록을 통째로 빠뜨린 룰북은 등록할 때 거부한다. 「없다」고 말하려면 「없다」를 명시적으로 적어야 한다(`UnknownEventType`·`NoMatchingGradeBand`·`UnknownRulebook`과 같은 규율).
- **D-03:** `StatEntry`의 네 칸을 넓히는 것을 이 단계에서 명시적으로 재논의한다. D-20/D-65가 잠근 「네 칸」은 적·NPC 숫자를 담는 그릇 하나의 모양이었고, 이번 확장은 그 그릇을 모든 자원 축을 담는 그릇으로 넓히는 것이므로 적용 범위 재조정이지 원 결정 뒤집기가 아니다(D-64·D-65·D-66과 같은 패턴). `STAT_ENTRY_FIELD_NAMES` 고정 시험은 지우지 않고 새 칸 목록으로 **재고정**한다. Reversibility: one-way.
- **D-04:** 축 목록은 룰북당 하나이고, 어떤 개체가 어떤 축을 갖는지는 개체마다 다르다. 플레이어 캐릭터용·적용 두 벌로 선언하지 않는다.
- **D-05:** 「안 쓴다」는 두 갈래다 — 「규칙으로 안 센다」(서사에는 자유롭게 등장하되 시스템이 안 셈) / 「이 세계에 그 개념이 없다」(서사에서도 안 나옴). 자동화율 계산에서 `none`은 분모 제외, `discretionary`는 분모 포함·분자 항상 0.
- **D-06:** 룰북은 개념마다 반드시 「쓴다(형태)」/「규칙으로 안 센다」/「개념이 없다」 중 하나를 적는다. 빠뜨림이 구조적으로 불가능해진다.
- **D-07:** 룰북 선언 형식에 판 번호를 두지 않는다. 어휘가 늘어 기존 룰북에 빈칸이 생기면 그때 그 룰북 파일들을 고친다. 남이 쓴 룰북을 받기 시작할 때(M1 이후) 재검토.
- **D-08:** AI 진행자에게는 「없다」가 아니라 「어떻게 다루는가」를 알려준다 — 안 세는 룰북이면 「물건은 서사에 자유롭게 등장하되 숫자로 세지 않는다」, 개념이 없는 룰북이면 「이건 이 세계에 없다」. D-66의 에이전트별 상한 규율 안에서 자리를 잡아야 한다.
- **D-09:** 소지품을 안 세는 룰북에서 「없는 것을 쓴다」는 판단은 성립하지 않는다 — 그냥 서사로 흘러간다. Phase 12 성공 기준 5(소지품 재량 판정)는 세는 룰북에만 적용된다.
- **D-10:** 굴릴 필요가 없는 행동은 판정 없이 그냥 진행된다. 「굴리지 않는다」가 정식 경로다. Reversibility: costly — 분류기 반환 계약, 웹 `declare` 응답, 화면 세 갈래 확인, CLI 턴 흐름이 함께 바뀐다.
- **D-11:** 분류기는 셋 중 하나로 답한다 — ① 판정이 붙는다 ② 판정은 필요 없고 그냥 진행한다 ③ 무슨 말인지 모르겠다. **③만 지금처럼 「다시 쓰기」로 간다.** 목록 밖 이름 흡수(SAFE-07, 10-05)의 결과가 ②로 새면 안 된다 — 계약 위반은 ③ 쪽이다.
- **D-12:** 판정 트리거 목록이 비어 있는 경우도 두 갈래이고, 룰북이 고른다 — 「주사위를 안 굴리는 게임」과 「굴리긴 하는데 언제 굴릴지를 목록이 아니라 그 자리에서 정하는 게임」. 뒤쪽이면 AI가 제안하고 사람이 확인한다(재량 판정 경로).
- **D-13:** 표현 형태 여섯 가지를 전부 만든다 — 숫자+상한 / 세그먼트 원 / 이름 붙은 칸 / 태그 목록 / 자원 주사위 / 없음. **이번에 안 만든 형태는 룰북이 선언해도 등록에서 거부한다.**
- **D-14:** 세 번째 룰북을 데이터로 넣는다 — 스펙트럼의 반대쪽 끝에서. 저작권이 깨끗한 공개 자료(SRD)여야 한다. 자체 창작 미니 룰북은 D-18이 배제했다. 후보 없으면 그 사실을 그대로 보고하고 사람에게 되묻는다.
- **D-15:** 등록 검사(QUAL-03)가 잡는 것은 「가려짐」(앞 등급에 완전히 가려져 영영 안 나오는 등급)과 「구멍」(어떤 결과값에도 안 맞아 판정이 멈추는 구멍) 둘뿐이다. **단순 겹침은 정상으로 둔다.** ROADMAP 성공 기준 5의 「겹치거나」는 이 결정으로 「가려져 영영 도달 불가능하거나」로 읽는다.

### Claude's Discretion

- 자원 축이 하나도 없는 룰북에서 캐릭터 판에 무엇이 남는지, 사람이 빈 판을 고장으로 오해하지 않게 하는 방법
- 브람·나리 등 기존 캐릭터 수치를 새 형식으로 옮길 때의 값 처리 — 수치를 그대로 보존한다(D-49)
- 룰북 선언을 어떤 파일 모양으로 적을지, 검증기를 어디에 둘지
- 이 단계를 몇 개의 계획으로 쪼갤지 — 여섯 형태 + 세 번째 룰북 + 등록 검사라 얇게 나눌 것

### Deferred Ideas (OUT OF SCOPE)

- 룰북 선언 형식의 판 번호 — M1 이후 재검토
- 이름 붙은 칸·자원 주사위를 실제로 쓰는 네 번째 룰북 — 이후 마일스톤
- 소급 선언(플래시백) 비용 규칙 — Phase 12
- 결과 카테고리 닫힌 목록과 「성공했지만 대가가 있다」 두 축 — Phase 12(RULE-13)
- 자동화율 계측의 실제 계산 — 규칙만 정해졌고 계측 자체는 이 단계 밖
- 값 실제 변화 / `StatEntry` 쓰기 경로 — Phase 12
- 캐릭터 만들기 화면 — Phase 12.1
- 관계 장부·문맥 압축기 — Phase 14
- 프론트엔드 전면 재감사 — Phase 16
- 룰북 저작 도구·업로드 — M1 이후

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RULE-11 | 체력·소지품·스트레스·진행 원을 하나의 「이름 붙은 자원 축」 그릇으로 담는다 — 표현 형태 6종을 룰북이 고른다 | `## Architecture Patterns` Pattern 1(자원 축 컨테이너 모양) — 재고정할 `StatEntry`/`Rulebook` 필드 구조와 근거를 제시 |
| RULE-12 | 「이 개념을 안 쓴다」 선언이 가능하고, 선언하면 화면·판정 훅이 완전히 사라진다. 값 0 / 개념 없음 / 빠뜨림 / 의도적 선언이 구분된다 | Pattern 1 + `## Validation Architecture`(성공 기준 2·3의 기계적 검증 방법) |
| RULE-15 | 판정 트리거 목록이 비어 있는 것이 정상값 — 목록이 비면 재량 판정으로 떨어진다 | Pattern 2(분류기 3~4갈래 재설계)와 그 구조적 파급(narration facts 의존성) |
| QUAL-03 | 등급 구간이 가려지거나 구멍이 있으면 등록할 때 걸린다(단순 겹침은 정상) | Pattern 3(등록 시점 겹침/가려짐/구멍 검증 알고리즘) — 기존 두 룰북에 대해 직접 손으로 시뮬레이션해 통과함을 확인 |

</phase_requirements>

## Summary

이 단계는 「무엇을 담을 것인가」를 정하는 그릇 설계 단계이고, 실제 값 변화(Phase 12)는 손대지 않는다. 코드 조사 결과 네 가지 핵심 사실이 확인됐다.

첫째, 자원 축을 「룰북이 선언하고 개체가 하위 집합만 갖는다」는 구조(D-01/D-04)는 지금 코드에 **전혀 없다** — `Rulebook`(`src/gptrpg/rules_core/rulebook.py:34-42`)에는 판정 방식과 등급 밴드만 있고 자원 축 칸이 없다. 이 단계가 이 칸을 신설해야 하며, `GradeBand`가 이미 쓰고 있는 "플랫 데이터클래스 + 선택적 필드 + `__post_init__` 검증" 관례를 그대로 재사용하는 것이 이 저장소의 기존 관행과 가장 잘 맞는다.

둘째, `StatEntry.current: int`(`src/gptrpg/rules_core/entities.py:39-61`)는 숫자 하나만 담을 수 있어 6개 표현 형태 중 이름 붙은 칸·태그 목록·자원 주사위·없음(discretionary/absent 구분)을 표현하지 못한다. 조사는 `GradeBand`와 같은 "판별 필드 + 선택적 페이로드 필드" 단일 클래스 확장을 권고하며(순수 Union 타입보다 이 저장소 관례와의 정합성이 높다), `STAT_ENTRY_FIELD_NAMES` 고정 시험(`tests/test_entities.py:25`)을 8칸으로 재고정하는 구체 모양을 제시한다.

셋째, D-11의 3갈래 분류기는 코드 변화가 생각보다 크다 — 지금 `narrate()`로 가는 모든 경로는 `check_summary`가 실제 판정(`ResolveCheck`)에서 나온다는 전제 위에 있다(`web/routes_actions.py:611`, `cli/turn_flow.py:342`). 「판정 없이 그냥 진행」(D-10의 ②)은 판정 자체가 없으므로 이 전제가 깨진다 — 서술까지 가려면 `check_summary`/`NarrationFacts`의 원천을 다시 설계해야 한다. 이것이 CONTEXT.md가 D-10을 "costly"로 표시한 실제 근거다. 또한 CLI(`cli/turn_flow.py:284-289`)와 웹(`ChatPane.tsx:183`)이 지금 `tier=="none"`을 서로 다르게 처리한다는 사실도 이번에 확인했다 — CLI는 메시지 출력 후 조용히 턴을 끝내고(서사 없음), 웹은 「다시 쓰기」 버튼을 보여준다. 둘 다 "판정 없이 이야기가 이어지는" D-10의 ②를 구현하지 않는다는 점에서는 같다.

넷째, QUAL-03의 등록 시점 검증 알고리즘을 실제 `GradeBand` 표현(정수 margin의 닫힌 구간 + `requires_doubles` 불리언 차원)에 대해 손으로 설계하고 두 기존 룰북(dungeonworld_like·openquest) 양쪽에 대해 시뮬레이션했다 — **두 룰북 모두 통과한다**는 것을 이 문서가 직접 확인했다(아래 Pattern 3).

세 번째 룰북 후보는 **Cairn RPG SRD**(CC BY-SA 4.0, `https://cairnrpg.com/first-edition/cairn-srd/`)를 권고한다 — 이름 붙은 칸(10슬롯 인벤토리) **그리고** 판정 트리거 목록 부재(고정 무브 없이 세이브+GM 재량)를 **동시에** 실증하는 유일하게 확인된 후보다. 단, OpenQuest의 CC BY 4.0과 달리 **ShareAlike** 조항이 있다는 것을 명시적으로 짚었다.

**Primary recommendation:** `Rulebook`에 필수(기본값 없는) `resource_axes: tuple[ResourceAxisDecl, ...]` 필드를 신설해 D-02를 파이썬 생성자 수준에서 강제하고, `StatEntry`는 `GradeBand`와 같은 패턴으로 `form` 판별 필드 + 폼별 선택적 페이로드 필드로 확장하며, 분류기 3~4갈래 재설계는 `check_summary`/`NarrationFacts` 의존성 재설계를 반드시 동반한다는 것을 계획 단계가 못박아야 한다.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 자원 축 목록 선언(어떤 축이 존재하는가) | 룰북 콘텐츠(`gptrpg.rulebooks`) | 플랫폼 어휘(`rules_core.rulebook`이 형태 스키마 소유) | 이름은 룰북 것, 형태(6종 enum)는 플랫폼 것 — `rulebook.py` 도크스트링이 이미 이 경계를 명시 |
| 개체별 자원 축 현재값 | `rules_core`(`entities.py`) | 룰북 데이터(`rulebooks/*.py`, `web/characters_data.py`)가 값을 채움 | `Entity.stats`가 이미 이 층에 있다 — 확장이지 신규 층 아님 |
| 「안 쓴다」 선언에 따른 화면 요소 제거 | 프론트엔드(`StatusPane.tsx` 등) | API 응답 계약(`routes_characters.py`) — 화면이 형태를 몰라도 되도록 응답이 이미 걸러야 한다 | RULE-12 성공 기준 2("완전히 사라진다")는 서버가 안 보내는 것이지 화면이 숨기는 것이 아니어야 검증 가능하다(아래 Validation Architecture) |
| 판정 트리거 유무 판단 및 분류기 3갈래 출력 | AI 에이전트 층(`agents/action_classifier.py`) | 웹/CLI 호출부(`routes_actions.py`, `cli/turn_flow.py`) — 두 곳이 같은 계약을 소비해야 한다(10-05가 세운 관례) | 분류는 이미 이 층의 책임. 확장이지 이관 아님 |
| 「판정 없이 진행」 시 서술에 넘길 사실(check_summary 대체) | AI 에이전트 층(`turn/judgments.py`, `agents/context.py`) | — | `NarrationFacts.check_summary: str`가 이미 이 층에 있다 — 원천만 바뀐다 |
| 등급 밴드 가려짐/구멍 검증 | `rules_core`(순수 함수, `rulebook.py`와 같은 모듈이 적합) | 등록소(`rulebooks/__init__.py`)가 호출 지점 | `grade_for_margin`이 이미 `rules_core`에 있고 검증은 그 옆의 순수 함수로 자연스럽게 붙는다. `.importlinter` contract:1(시간·무작위·파일·네트워크 금지)을 지키는 순수 정수 구간 연산이라 이 층에 둘 수 있다 |
| AI 진행자에게 「어떻게 다루는가」 알리는 문장 | AI 에이전트 층(`agents/prompt_assembly.py`의 **영구 고정 블록**) | — | 이 문장은 룰북 단위로 고정이라 세션·턴마다 안 바뀐다 — 캐싱 순서 규약상 영구 고정 블록이 맞는 자리(아래 Pattern 4) |

## Standard Stack

이 단계는 새 외부 라이브러리를 설치하지 않는다 — 순수 파이썬 표준 라이브러리(`dataclasses`, `typing.Literal`)만으로 그릇을 구현한다. 기존 코드가 이미 이 조합(`GradeBand`, `StatEntry`, `TurnContext`)으로 같은 문제를 풀고 있으므로 새 도구를 들이는 것 자체가 이 저장소의 관례 위반이다.

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dataclasses`(표준 라이브러리) | Python 3.13/3.14 내장(`[VERIFIED: pyproject.toml, tests/__pycache__ 파일명 cpython-313/314]`) | 자원 축 선언·상태값의 불변 값 객체 | 저장소 전체가 이미 이 패턴(`frozen=True`)을 씀 — `entities.py`, `rulebook.py`, `context.py` 전부 |
| `typing.Literal` | 표준 라이브러리 | 6가지 표현 형태·`ProposalTier` 확장의 판별 필드 | `action_classifier.py:19`의 `ProposalTier = Literal[...]`가 이미 이 패턴을 씀 |

### Supporting

새로 도입할 서드파티 패키지가 없다. `functools.singledispatch`는 검토했으나(연구 우선순위가 명시적으로 요청) **권장하지 않는다** — 아래 Pattern 1의 근거 참조.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 판별 필드 하나짜리 플랫 데이터클래스(`GradeBand` 패턴) | `typing.Union`으로 6개 별도 프로즌 데이터클래스를 묶는 진짜 태그드 유니온 | 타입 안전성은 높아지지만 `StatEntryView`(pydantic, `routes_characters.py:57-63`)·`frontend/src/api/types.ts`의 `StatEntry` 인터페이스가 전부 "칸 이름이 한 글자도 다르지 않다"는 평평한 구조를 전제로 짜여 있다 — 판별 유니온으로 가면 이 계약을 깨고 pydantic Discriminated Union + TS 판별 유니온으로 양쪽을 다시 설계해야 한다. 저장소의 기존 확장 관례(`GradeBand`가 이미 같은 문제를 이 방식으로 풀었다)와도 어긋난다 |
| 판별 필드 + if/elif 분기(`StatRows`의 기존 `stat.max === null` 분기와 같은 모양) | `functools.singledispatch` | `singledispatch`는 **런타임 타입**으로 디스패치한다 — 판별 필드가 문자열인 단일 클래스 설계에서는 애초에 디스패치할 서로 다른 타입이 없으므로 적용 대상 자체가 안 맞는다. 태그드 유니온(위 대안)으로 가야 `singledispatch`가 의미 있어지는데, 그 대안 자체가 이 시점에는 배보다 배꼽이 크다 |

**Installation:** 없음 — 코드 신설.

## Package Legitimacy Audit

**해당 없음.** 이 단계는 외부 패키지를 설치하지 않는다(순수 파이썬 표준 라이브러리). 세 번째 룰북 데이터는 npm/PyPI/crates 같은 패키지 레지스트리에서 받아 오는 것이 아니라 SRD 공식 웹페이지의 수치·규칙을 사람이 손으로 옮겨 적는 것이다(기존 `openquest.py`/`openquest_creatures.py`와 같은 방식) — Package Legitimacy Gate는 적용 대상이 없다.

## Architecture Patterns

### System Architecture Diagram

```
룰북 파일(gptrpg.rulebooks/*.py)
  │  Rulebook(rulebook_id, resolution_method, grade_bands, resource_axes ←신설)
  │  MoveDecl 목록(비어 있어도 정상, RULE-15)
  ▼
등록소(rulebooks/__init__.py)
  │  D-02: resource_axes가 없으면 Rulebook() 생성 자체가 TypeError로 실패(선택 아님)
  │  D-15(QUAL-03, 신설): grade_bands의 가려짐·구멍을 여기서 검증 → 실패 시 등록 거부
  ▼
Entity/StatEntry(rules_core/entities.py) ── 개체별 「가진 축」만 담음(D-04)
  │
  ├─▶ routes_characters.py → StatEntryView(pydantic) → StatusPane.tsx
  │      RULE-12: none 형태 축은 여기서 걸러져 화면에 아예 안 실린다(화면이 숨기지 않는다)
  │
  ├─▶ prompt_assembly.py 영구 고정 블록 ── D-08: 「어떻게 다루는가」 문장이 룰북 단위로 캐시됨
  │
  └─▶ (판정 트리거 있는 축) moves.py MoveDecl.default_stat → action_classifier
         │
         ▼
      classify() ── D-11: ①check ②no_check(신설) ③unclear(기존 "none")
         │                                    │
         │              ②일 때 check_summary가 없다 ──▶ NarrationFacts 원천 재설계 필요(신설 경로)
         ▼
      routes_actions.py / cli/turn_flow.py(두 호출부, 반드시 같이 바뀐다)
```

### Recommended Project Structure

새 파일을 만들기보다 기존 모듈을 확장하는 편이 이 저장소의 층 계약(`.importlinter` contract:2)과 맞는다.

```
src/gptrpg/rules_core/
├── entities.py       # StatEntry 확장(6폼) — 재고정할 STAT_ENTRY_FIELD_NAMES가 여기 있다
├── rulebook.py        # ResourceAxisDecl 신설 + Rulebook.resource_axes 신설 + 가려짐/구멍 검증 함수 신설
src/gptrpg/rulebooks/
├── __init__.py         # 등록 시점 검증 호출 지점(D-02/D-15)
├── dungeonworld_like.py  # resource_axes 신설 선언 추가
├── openquest.py           # 〃
├── openquest_creatures.py # 〃 — 크리처 stats를 새 StatEntry 모양에 맞춰 다시 씀
├── cairn_like.py (신규, 이름은 계획 단계가 확정) # 세 번째 룰북 — named_slots + 빈 move 목록 실증
src/gptrpg/agents/
├── action_classifier.py  # ProposalTier 4값으로 확장, no_check 신호 파싱
├── prompt_assembly.py    # 영구 고정 블록에 「안 쓴다」 문장 추가(D-08)
├── context.py             # NarrationFacts.check_summary 원천 재설계에 필요한 칸/상한 검토
src/gptrpg/turn/
├── judgments.py           # build_narration_facts가 check 없는 경로도 받도록 확장
src/gptrpg/web/
├── routes_actions.py      # declare/confirm 두 경로 모두 D-11 4값 처리
├── routes_characters.py   # StatEntryView 확장(6폼 칸)
├── characters_data.py     # 브람·나리 등 4캐릭터 — 새 StatEntry 모양으로 재작성(D-49: 수치 보존)
src/gptrpg/cli/
├── turn_flow.py           # tier 4값 처리, CLI 쪽도 웹과 같은 의미로
frontend/src/
├── panes/StatusPane.tsx   # 6폼 렌더링(신규 3종: named_slots/tag_list/usage_die)
├── panes/ChatPane.tsx     # tier 4값 UI(신규: no_check → 즉시 진행 안내)
├── labels.ts              # 새 문구
├── api/types.ts           # StatEntry/tier 타입 확장
```

### Pattern 1: 자원 축 컨테이너 — `GradeBand` 관례를 그대로 재사용한다

**What:** `Rulebook`에 필수 필드 `resource_axes: tuple[ResourceAxisDecl, ...]`을 추가하고, `ResourceAxisDecl`은 `GradeBand`(`rulebook.py:19-31`)와 같은 모양 — `name`(룰북 어휘) + `form`(판별 필드, 플랫폼 어휘) + 폼별 선택적 필드.

**왜 이 모양인가 (근거):**

1. **D-02는 코드로 이미 공짜다.** `Rulebook`은 프로즌 데이터클래스다(`rulebook.py:34-42`, `[VERIFIED: src/gptrpg/rules_core/rulebook.py:34-42]` — 실제 코드: `@dataclass(frozen=True)\nclass Rulebook:\n    rulebook_id: str\n    display_name: str\n    resolution_method: str\n    grade_bands: tuple[GradeBand, ...]`). `resource_axes`에 **기본값을 주지 않고** 새 위치 인자로 추가하면, `DUNGEONWORLD_LIKE = Rulebook(...)`처럼 이 필드를 안 채운 모든 기존 호출이 파이썬 생성자 수준에서 `TypeError`로 즉시 실패한다. 「없다」를 말하려면 `resource_axes=()`를 명시적으로 타이핑해야만 한다 — D-02가 요구하는 "빠뜨림 구조적 불가능"이 등록 함수를 새로 짤 필요 없이 언어 자체의 강제로 달성된다.

2. **이름/형태 경계가 `GradeBand`와 정확히 같은 문제다.** `GradeBand.name`은 룰북이 짓는 이름(`"strong_hit"` 등), `margin_at_least`/`margin_at_most`/`requires_doubles`는 플랫폼이 아는 수치 구간 어휘다. 자원 축도 `name`(체력/스트레스 등 룰북 어휘)과 `form`(플랫폼이 아는 6종 enum)이 정확히 같은 이름/형태 분리를 요구한다 — 새 패턴을 발명하지 않고 검증된 기존 패턴을 확장하는 것이 이 저장소의 "판정 방식 이름은 플랫폼 능력의 이름이지 룰북 어휘가 아니다"(`rulebook.py:13` 도크스트링) 규율과 정확히 일치한다.

**StatEntry(개체별 현재값) 확장 — 추천 모양:**

```python
# rules_core/entities.py — 재고정 대상
StatEntryForm = Literal["numeric", "clock", "named_slots", "tag_list", "usage_die", "none"]

@dataclass(frozen=True)
class StatEntry:
    name: str
    form: StatEntryForm
    current: int | None = None
    """numeric의 현재값 / clock의 채워진 칸 수(ThreatClock.tsx의 `segment` prop과 그대로
    호환) / usage_die의 현재 주사위 면수(예: 8은 d8, 0은 소진)."""
    max: int | None = None
    """numeric의 상한 / clock의 전체 칸 수(ThreatClock.tsx의 `segmentCount`와 그대로 호환)."""
    depleted_effect_ref: str | None = None
    slot_values: tuple[str | None, ...] | None = None
    """named_slots 전용 — 고정 길이 튜플, 빈 칸은 None, 채워진 칸은 아이템 이름."""
    tags: tuple[str, ...] | None = None
    """tag_list 전용 — 지금 붙어 있는 태그들."""
    none_kind: Literal["discretionary", "absent"] | None = None
    """form == "none"일 때만 채운다 — D-05의 두 갈래(규칙으로 안 센다/개념이 없다)."""
```

`__post_init__`는 기존 검증(name 공백 금지, max 음수 금지, depleted_effect_ref 빈 문자열 금지)에 더해 **"현재 form에 맞는 필드만 채워져 있는가"**를 검사해야 한다 — 예: `form == "named_slots"`인데 `current is not None`이면 즉시 예외. 이 검증 자체가 새로운 값이 아니라 `InvalidStatEntry`(`entities.py:13-24`)가 이미 존재하는 예외 클래스를 확장하는 것이다.

**재고정할 상수:** `STAT_ENTRY_FIELD_NAMES = frozenset(f.name for f in fields(StatEntry))`(`entities.py:95`)는 지금 4개(`{"name","current","max","depleted_effect_ref"}`)에서 8개(`{"name","form","current","max","depleted_effect_ref","slot_values","tags","none_kind"}`)로 바뀐다. `tests/test_entities.py:25`의 `test_stat_entry_field_names_are_exactly_four`는 **삭제하지 않고** 새 8칸 집합을 단언하도록 재작성한다(D-03이 명시적으로 요구).

**세그먼트 원 재사용:** `ThreatClock.tsx`(`frontend/src/components/ThreatClock.tsx:12-17`)의 props는 `segment: number; segmentCount: number`뿐이다 — `[VERIFIED: frontend/src/components/ThreatClock.tsx:12-17]` 실제 코드: `interface ThreatClockProps {\n  segment: number;\n  segmentCount: number;\n  size?: number;\n  pulsing?: boolean;\n}`. 위 `StatEntry`의 `current`/`max`를 그대로 이 두 prop에 매핑할 수 있다 — 자원 축의 세그먼트 형태는 이 컴포넌트를 **그대로** 재사용 가능하다(CONTEXT.md의 예측이 코드로 확인됨).

**D-05/D-13 사이의 미해결 지점 (계획 단계가 잠가야 함):** D-13은 표현 형태를 "숫자+상한 / 세그먼트 원 / 이름 붙은 칸 / 태그 목록 / 자원 주사위 / **없음**" 6개로 나열해 "없음"을 하나의 값처럼 적었지만, D-05는 "안 쓴다"가 "규칙으로 안 센다"/"개념이 없다" **두 갈래**라고 명시한다. 위 설계는 `form="none"` 하나 아래 `none_kind`로 이 둘을 다시 가르는 절충안이다 — 이것이 D-13의 "여섯 형태"라는 숫자와 D-05의 "두 갈래"라는 요구를 동시에 만족하는 유일한 방법은 아니다(예: `form`을 아예 7값으로 늘려 `"none_discretionary"`/`"none_absent"`로 쪼갤 수도 있다). 이 문서는 **6폼 + 하위 판별자** 쪽을 권고하지만(D-13의 "여섯 가지" 문구를 문자 그대로 지킬 수 있어서), 계획 단계가 이 선택을 명시적으로 기록해야 한다.

**빠뜨림 vs 의도적 선언의 한계:** D-06은 "빠뜨림이 구조적으로 불가능해진다"고 하지만, 실제로 플랫폼이 강제할 수 있는 것은 "`resource_axes` **필드 자체**가 없으면 등록 실패"(D-02, 확인됨)까지다. "체력이라는 개념을 룰북이 깜빡 빠뜨렸는가, 원래 그 룰북에 체력이라는 개념이 없는가"는 플랫폼이 판단할 수 없다 — `rules_core`는 "체력"이라는 이름을 몰라야 한다(반편향 원칙, `rulebook.py:1-3` 도크스트링). 따라서 이 구분은 **플랫폼이 검증 가능한 것은 목록 자체의 존재뿐**이고, "각 개념을 다뤘는가"는 저작 규율(사람이 지키는 약속)이라는 것을 아래 `## Open Questions`에 명시했다.

### Pattern 2: 분류기 3~4갈래와 서술 경로 재설계

**What:** `ProposalTier`(`agents/action_classifier.py:19`)를 `"single" | "several" | "no_check" | "unclear"` 4값으로 넓히고, `classify()`가 모델 출력에서 "판정 불필요"를 명시적으로 구분해 반환한다.

**현재 계약 확인(`[VERIFIED: src/gptrpg/agents/action_classifier.py:19-21]`):**
```python
ProposalTier = Literal["single", "several", "none"]
```
`Proposal.tier`(`action_classifier.py:68-76`)는 `len(self.candidates)`만으로 계산된다 — `count == 0`이면 무조건 `"none"`. 지금 이 하나의 값이 ②(판정 불필요, 진행)와 ③(모르겠음, 다시 쓰기)을 **구분 없이** 담당하고 있다.

**분류기 프롬프트의 현재 지시문(`[VERIFIED: src/gptrpg/agents/prompt_assembly.py:214-223]`):** `"확실하면 무브 하나만, 애매하면 둘이나 셋을, 어느 것도 안 맞으면 하나도 내지 말 것"` — "안 맞음"과 "필요 없음"을 하나의 지시로 뭉쳐 두었다. D-11을 구현하려면 이 지시문 자체를 분리해야 한다(예: 실제 무브 목록에 없는 예약된 신호값을 추가해 "이 행동은 판정이 필요 없다"를 모델이 명시적으로 표시하게 하는 방법, 또는 응답을 배열에서 `{"disposition": "check"|"no_check"|"unclear", "candidates": [...]}` 객체로 바꾸는 방법 — 후자는 `_try_parse_json_array`(`json_parsing.py`, 배열 전제)의 파싱 계약을 깨므로 더 큰 변경이다).

**호출부 두 곳 실측(연구 우선순위가 명시적으로 요구):**

- `web/routes_actions.py`의 `declare()`는 `proposal.tier`를 그대로 `DeclareResponse.tier: str`에 담아 반환한다(`routes_actions.py:332-336`). 서술(`narrate`) 호출은 `declare()`가 아니라 **별도의 `confirm()`** 안에서 일어나고, `confirm()`은 `ConfirmRequest.move`/`.stat`을 **필수 필드**로 요구한다(`routes_actions.py:339-352`, `Field(min_length=1, ...)`). `check_summary`는 `confirm()` 안에서 `ResolveCheck` 제출 후 읽은 `check_event`로부터만 만들어진다(`routes_actions.py:495-496`, `[VERIFIED: src/gptrpg/web/routes_actions.py:495-496]`: `check_event = store.read_events(session_id, from_seq=resolve_seq)[0]\n    check_summary = f"{body.move} 판정 결과 {check_event.grade} (목표 {check_event.target})"`).
- `cli/turn_flow.py`의 `_turn_flow()`는 `tier == "none"`이면 `print("무브 없음 — 판정 없이 진행합니다. ...")`를 찍고 **`return 0`으로 함수를 끝낸다**(`turn_flow.py:284-289`, `[VERIFIED: src/gptrpg/cli/turn_flow.py:284-289]`) — `narrate()`를 호출하지 않는다. 즉 오늘의 CLI도 "판정 없이 진행" 문구를 화면에 찍을 뿐, 실제로 진행자가 서사를 이어가지는 않는다.

**결론(계획 단계가 반드시 알아야 함):** D-10/D-11이 요구하는 "판정 없이 진행자가 서술하고 이야기가 이어진다"는 것은 **CLI에도 웹에도 지금 존재하지 않는다.** ②(no_check) 갈래를 만들려면 `confirm()`의 move/stat 필수 요구와 `check_summary`가 `ResolveCheck`에서만 나온다는 전제를 함께 재설계해야 한다 — CONTEXT.md D-10이 "costly"로 표시한 이유가 이 조사로 구체화됐다. 계획은 최소한 다음 셋을 함께 다뤄야 한다: ① `NarrationFacts.check_summary`가 판정 없는 서사에서 무엇을 담을지(예: 선언 원문 요약) ② `confirm()`/CLI 흐름에서 판정을 건너뛰고 곧장 서술로 가는 경로의 진입점 ③ `ChatPane.tsx`(`183`행 근처)와 `labels.ts`(`100`행)가 새 tier에 어떤 화면을 보여줄지 — "다시 쓰기"는 오직 `"unclear"`에만 남는다(D-11 명시).

**SAFE-07 흡수 경로가 반드시 `"unclear"`로 가야 하는 근거(확인됨):** `classify()`의 `UnknownMove` 흡수 처리(`action_classifier.py:169-183`)는 지금 `Proposal(candidates=(), ai=result, unknown_move=exc.move_id)`를 반환한다 — `candidates=()`이므로 오늘의 `tier` 계산 규칙 그대로면 자동으로 `"none"`이 된다. 4값 확장 후에도 이 경로는 **`"unclear"`로만 매핑**되어야 한다(new "no_check" 신호와 절대 혼동되면 안 된다) — `_parse_candidates`가 `UnknownMove`를 던지는 시점(모델이 목록 밖 이름을 명시적으로 냄)과 "모델이 no_check 신호를 냄" 시점은 서로 다른 코드 경로이므로, 4값 확장을 반환 계약의 별도 필드가 아니라 `candidates`/`unknown_move`와 **같은 층**에서 조합해 파생하는 한 이 분리는 자연스럽게 유지된다.

### Pattern 3: 등급 밴드 「가려짐」·「구멍」 검증 — 알고리즘 설계 및 기존 두 룰북 검증

**밴드 표현의 실제 모양(`[VERIFIED: src/gptrpg/rules_core/rulebook.py:19-31]`):**
```python
@dataclass(frozen=True)
class GradeBand:
    name: str
    counts_as_failure: bool
    margin_at_least: int | None = None
    margin_at_most: int | None = None
    requires_doubles: bool | None = None
```
`grade_for_margin`(`rulebook.py:69-84`)의 실제 비교 로직: `margin < margin_at_least`면 건너뜀(즉 `margin_at_least`는 **포함** 하한), `margin > margin_at_most`면 건너뜀(즉 `margin_at_most`는 **포함** 상한), `None`은 그쪽 경계가 없음(비유계)을 뜻한다. `margin`은 정수(`int`)다. `requires_doubles`가 `None`이면 그 밴드는 `is_doubles` 값과 무관하게 매치된다.

**이것이 뜻하는 바:** 밴드 판정 공간은 사실 **2차원**이다 — 정수 `margin` 축(닫힌 구간, 양끝 비유계 가능) × `is_doubles` 불리언 축(밴드별로 `True`/`False`/무관 세 상태). D-15의 「가려짐」(먼저 온 밴드들에 완전히 덮여 영영 못 나오는 밴드)과 「구멍」(어떤 밴드도 안 맞는 `(margin, is_doubles)` 조합 — 런타임에서 `NoMatchingGradeBand`로 나타나는 바로 그 상황)은 이 2차원 공간에서 정의해야 정확하다. 단순히 `margin_at_least`/`margin_at_most`끼리 산술 비교만 하면 `requires_doubles`가 관여하는 밴드(현재는 OpenQuest의 `critical`/`fumble`)를 잘못 처리한다.

**권고 알고리즘 (스윕 방식, `rules_core`에 순수 함수로 둘 수 있다 — 시간·무작위·파일·네트워크 불사용):**

1. `is_doubles ∈ {True, False}` 두 "세계"로 나눠 각각 1차원 문제로 축소한다. 밴드는 `requires_doubles is None`이면 두 세계 모두에 참여하고, `True`/`False`면 해당 세계에만 참여한다.
2. 각 세계 안에서, 모든 밴드의 `margin_at_least`/`margin_at_most + 1`을 경계점으로 모아 유한 개의 원자 구간(cell)으로 정수선을 쪼갠다(`None`은 `-∞`/`+∞`로 취급).
3. 각 세계 × 각 원자 구간에 대해 **선언 순서대로** 첫 매치 밴드를 찾는다(= 오늘의 `grade_for_margin`과 동일한 규칙).
4. 어떤 밴드가 **어느 세계, 어느 구간에서도** 승자가 된 적이 없으면 → **가려짐(에러 ①)**.
5. 어떤 세계 × 구간에 **승자가 아예 없으면**(선언 순서와 무관하게, 그 구간을 커버하는 밴드가 하나도 없으면) → **구멍(에러 ②)** — 이 구간·세계에 해당하는 `(margin, is_doubles)`가 실제로 굴러오면 런타임에서 `NoMatchingGradeBand`가 터진다.

**두 기존 룰북에 대해 손으로 시뮬레이션해 통과를 확인함 (연구 우선순위가 명시적으로 요구한 검증):**

*던전월드류* (`[VERIFIED: src/gptrpg/rulebooks/dungeonworld_like.py:19-23]`, `requires_doubles` 전부 `None`이라 단일 세계로 축소됨):
```python
DUNGEONWORLD_GRADE_BANDS: tuple[GradeBand, ...] = (
    GradeBand(name="strong_hit", counts_as_failure=False, margin_at_least=0),
    GradeBand(name="weak_hit", counts_as_failure=False, margin_at_least=-WEAK_HIT_BAND),  # -3
    GradeBand(name="miss", counts_as_failure=True),
)
```
경계점 `{-3, 0}`으로 쪼갠 구간 `(-∞,-4] / [-3,-1] / [0,+∞)`에서 첫 매치: `miss`가 `(-∞,-4]`를 이김, `weak_hit`이 `[-3,-1]`을 이김(strong_hit은 `margin≥0` 조건에 안 걸림), `strong_hit`이 `[0,+∞)`를 이김. 세 밴드 모두 최소 한 구간을 이긴다 → 가려짐 없음. 세 구간이 정수선 전체를 덮는다 → 구멍 없음. **통과.**

*OpenQuest* (`[VERIFIED: src/gptrpg/rulebooks/openquest.py:15-20]`, `requires_doubles`가 `critical`/`fumble`에서 `True`):
```python
OPENQUEST_GRADE_BANDS: tuple[GradeBand, ...] = (
    GradeBand(name="critical", counts_as_failure=False, margin_at_least=0, requires_doubles=True),
    GradeBand(name="success", counts_as_failure=False, margin_at_least=0),
    GradeBand(name="fumble", counts_as_failure=True, margin_at_most=-1, requires_doubles=True),
    GradeBand(name="failure", counts_as_failure=True),
)
```
`is_doubles=True` 세계: `critical`이 `[0,+∞)`를 이김, `fumble`이 `(-∞,-1]`을 이김 — `success`/`failure`는 이 세계에서 안 이긴다(critical/fumble이 먼저 다 가져감). `is_doubles=False` 세계: `success`가 `[0,+∞)`를 이김(이 세계엔 critical이 없다), `failure`가 `(-∞,-1]`를 이김. 네 밴드 전부 **두 세계를 합쳐** 최소 한 구간씩 이긴다 → 가려짐 없음. 두 세계 각각 정수선 전체가 덮인다(항상 `failure`/`success`가 무제약 캐치올) → 구멍 없음. **통과.**

이로써 D-15가 명시한 "기존 두 룰북을 등록 거부하지 않는다"는 요구가 이 알고리즘으로 충족된다는 것을 사전에 확인했다.

**등록 지점:** `rulebooks/__init__.py`는 지금 `RULEBOOKS: dict[str, Rulebook]`을 모듈 임포트 시점에 정적으로 구성한다(`[VERIFIED: src/gptrpg/rulebooks/__init__.py:7-10]`) — "등록 함수"를 부르는 자리가 따로 없다. 계획 단계는 (a) 이 정적 딕셔너리 구성 직후 검증 루프를 돌려 위반 시 **임포트 시점에** 예외를 던지게 할지, (b) `register_rulebook()` 같은 명시적 함수로 바꿔 딕셔너리 리터럴을 대체할지 결정해야 한다 — 두 방법 다 QUAL-03("등록할 때 걸린다")을 만족하지만 파급 범위가 다르다(후자는 호출부를 새로 만들어야 한다).

### Pattern 4: AI 진행자에게 「어떻게 다루는가」 알리기 — 캐싱 규율 안에서

**부착 지점:** `build_gm_prompt`(`prompt_assembly.py:234-311`)와 `build_situation_prompt`(`prompt_assembly.py:314-357`)의 `permanent` 문자열 — `_format_moves(moves)`가 붙는 바로 그 위치(`build_classifier_prompt`의 경우 `prompt_assembly.py:222`, `f"무브 목록:\n{_format_moves(moves)}\n\n{NOT_AN_INSTRUCTION_LINE}"`)와 같은 층이다.

**왜 여기인가:** D-08의 문장("물건은 서사에 자유롭게 등장하되 숫자로 세지 않는다" 등)은 **룰북 단위**로 고정이다 — 세션이 바뀌거나 턴이 넘어가도 안 바뀐다. `prompt_assembly.py` 모듈 도크스트링(`1-14`행)이 명시하는 캐싱 순서 규약("영구 고정 → 세션 고정 → 턴마다 변함", 안 지키면 캐시가 매번 깨짐)에 따르면 이 문장은 **영구 고정 블록**(`_cached_block(permanent)`)에 들어가야 한다 — `_session_block_text`(장면 대상/캐릭터 상태, 장면이 바뀔 때만 갱신)에 넣으면 불필요하게 자주 무효화된다.

**상한 규율(D-66/ARCH-06):** `agents/context.py`는 이미 여러 상한 상수를 갖고 있다(`SITUATION_FACTS_LIMIT=5`, `CLOCK_JUDGE_RECENT_TURNS_LIMIT=4`, `NEW_ENTITY_LIMIT=3` 등, `[VERIFIED: src/gptrpg/agents/context.py:91-95,124-133,181-184]`). D-08의 문장 목록도 같은 규율을 따라야 한다 — 룰북의 `resource_axes` 중 `form=="none"`인 축 개수만큼 문장이 늘어나므로, 축 개수 자체에 상한이 있는지(D-01/D-04는 "상한 없음"이라고 명시하지 않았다) 계획 단계가 확인해야 한다. 문장이 룰북 단위로 고정이라 "매 턴 증가"하지는 않지만(D-66이 막으려는 것과는 다른 종류의 성장), 축 개수가 큰 룰북이 들어오면 영구 블록 자체가 커진다 — 렬록 초기 캐시 히트는 첫 턴에만 비용이고 이후는 캐시되므로 D-66의 "세션 길이에 비례해 늘지 않는다"는 목적은 유지되지만, 축 개수가 아주 많은 룰북에 대비한 상한을 둘지는 계획 단계의 판단 사항이다.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 자원 축의 판별 필드 + 선택적 페이로드 조합 검증 | 새 검증 프레임워크·pydantic 도입 | 기존 `InvalidStatEntry`/`InvalidEntity` 예외 패턴을 확장한 `__post_init__` | 저장소 전체가 `dataclass(frozen=True)` + 수제 `__post_init__` 검증으로 통일돼 있고, `rules_core`는 pydantic 같은 외부 의존을 지금 갖고 있지 않다(순수성 계약) |
| 등급 밴드 겹침 판정 알고리즘 | 범용 구간 트리(interval tree) 라이브러리 | Pattern 3의 손수 스윕(경계점 O(n) 정렬 + 원자 구간 순회) | 밴드 개수가 룰북 하나에 많아야 4~5개인 소규모 문제라 범용 자료구조 라이브러리를 들이는 비용이 이득보다 크다. `rules_core`가 외부 패키지를 못 쓴다는 제약(contract:1)과도 맞물린다 |
| 분류기의 "판정 불필요" 신호 파싱 | 새 LLM 출력 스키마 검증 라이브러리(예: instructor, guardrails) | 기존 `_try_parse_json_array`/`_parse_candidates` 계약을 확장 | 이 프로젝트는 이미 "닫힌 목록 JSON 배열 + 완화적 파싱(코드펜스·사고 블록 감쌈 허용)" 패턴을 5개 에이전트 전부에 통일해 쓰고 있다(`json_parsing.py` 공유 유틸) — 새 라이브러리를 들이면 이 통일성이 깨진다 |

**Key insight:** 이 단계에서 "직접 만들지 말아야 할 것"은 대부분 **외부 라이브러리가 아니라 이 저장소 안에 이미 있는 패턴**이다 — `GradeBand`, `InvalidStatEntry`, `_try_parse_json_array`가 전부 이번에 재사용할 정확한 선례를 이미 갖고 있다. 이 단계의 진짜 위험은 "새 것을 만드는 것"이 아니라 "기존 패턴과 다른 모양으로 새로 짜서 저장소 관례가 둘로 갈라지는 것"이다.

## Runtime State Inventory

> 이 단계는 리네임/리팩터 단계는 아니지만 `StatEntry` 스키마 확장이 **기존 프로덕션 데이터**(캐릭터 넷·크리처 둘)에 영향을 준다는 점에서 이 감사를 수행했다.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| 저장된 데이터 | **없음.** `StatEntry`/`Entity` 값은 SQLite 이벤트 로그(`.gptrpg/*.db`)에 직렬화되어 저장되지 않는다 — `routes_characters.py:148`의 `get_character()`가 매 요청마다 `characters_data.PLAYER_CHARACTERS`(파이썬 상수)를 직접 읽는다(`[VERIFIED: src/gptrpg/web/routes_characters.py:141-151]`). 사건 기록(`CheckResolved` 등)은 `move`/`grade`/`target`만 담고 `StatEntry` 자체를 담지 않는다 — 데이터 마이그레이션 대상이 없다 |
| 라이브 서비스 설정 | 없음 — `characters_data.py`/`openquest_creatures.py`/`dungeonworld_like.py`는 전부 git 추적 대상인 파이썬 소스 파일이다 |
| OS 등록 상태 | 없음 |
| 시크릿/환경변수 | 없음 — 자원 축 이름·형태는 코드 상수이지 시크릿이 아니다 |
| 빌드 산출물 | 없음 — 새 필드 추가는 재설치가 필요한 패키지 메타데이터를 바꾸지 않는다 |

**코드 편집만 필요한 것:** `characters_data.py`의 브람·나리·선·호두 네 `Entity` 리터럴, `openquest_creatures.py`의 고블린·스켈레톤 두 `Entity` 리터럴, `dungeonworld_like.py`의 `EXAMPLE_SINGLE_STAT_FOE` — 전부 새 `StatEntry(form=..., ...)` 시그니처로 **같은 커밋에서** 다시 써야 한다(안 그러면 `Entity.__post_init__`은 통과해도 8칸 재고정 시험이 즉시 깨진다). 브람·나리의 **수치 자체**는 D-49에 따라 보존한다 — `form="numeric"`으로 옮기고 `current`/`max` 값은 그대로 둔다.

## Common Pitfalls

### Pitfall 1: `StatEntry`를 넓히면서 필드를 "그냥 다 Optional로" 두고 형태별 정합성 검증을 빠뜨린다
**What goes wrong:** `form="numeric"`인데 `slot_values`가 채워져 있어도 아무 예외도 안 난다 — 화면 렌더링이 `form`을 무시하고 `slot_values is not None`으로 분기하면 룰북이 실수로 두 형태를 동시에 채운 데이터가 조용히 통과한다.
**Why it happens:** 기존 `StatEntry.__post_init__`(`entities.py:53-61`)는 "무엇이 채워져 있는가"만 보고 "지금 선언된 형태에 맞게 채워져 있는가"는 안 본다 — 4칸일 때는 이 구분이 필요 없었다(형태가 사실상 `max is None` 하나뿐이었다).
**How to avoid:** `form`별 "허용된 필드 집합"을 명시적 테이블로 두고 `__post_init__`에서 대조한다 — 그 테이블 자체가 `GradeBand`류 검증과 다른 새 패턴이 아니라 `InvalidStatEntry`의 확장이라는 것을 계획에 명시한다.
**Warning signs:** 코드 리뷰에서 "이 필드가 왜 두 form 모두에서 채워지죠?" 같은 질문이 나오면 이 함정에 걸린 것이다.

### Pitfall 2: 「완전히 사라진다」(성공 기준 2)를 프론트엔드가 조건부 렌더링으로 구현한다
**What goes wrong:** `StatusPane.tsx`가 `stat.form === "none"`이면 `null`을 반환하는 식으로 화면에서만 숨기면, 서버 응답(`CharacterSheetView`)에는 여전히 그 축의 존재가 실려 나간다 — 네트워크 탭에서 보이고, 성공 기준 2가 요구하는 "관련 화면 요소와 판정 훅이 완전히 사라진다"를 문자 그대로 어긴다(빈 인벤토리 패널을 회색으로 보여주는 것과 본질적으로 같은 실패 모양).
**Why it happens:** 프론트엔드가 서버 응답을 그대로 받아 조건부로 숨기는 것이 화면 코드만 건드리면 되는 가장 빠른 경로처럼 보인다.
**How to avoid:** `routes_characters.py`의 `CharacterSheetView` 조립 단계(또는 그 아래 `Entity.stats` 필터링 단계)에서 `form=="none"`인 축을 **응답 자체에서 제외**한다 — 화면은 "안 그린다"가 아니라 "받은 적이 없다"여야 한다. 아래 Validation Architecture의 테스트가 이 구분을 검증한다.
**Warning signs:** 프론트엔드 diff에만 `form === "none"` 분기가 생기고 백엔드 응답 스키마가 안 바뀌면 이 함정이다.

### Pitfall 3: D-11의 4갈래를 `Proposal.tier` 계산 로직만 바꿔서 끝냈다고 착각한다
**What goes wrong:** `tier` enum만 4값으로 넓히고 `web/routes_actions.py`의 `confirm()`이 여전히 `move`/`stat` 필수를 요구하면, "no_check" 갈래는 화면에 새 버튼만 생기고 실제로 누르면 400을 받는다.
**Why it happens:** `Proposal.tier`(`action_classifier.py:68-76`)는 계산된 읽기 전용 프로퍼티라 여기만 고치면 "다 됐다"는 착시가 생긴다 — 실제 파급은 `confirm()`의 요청 스키마와 `narrate()`가 받는 사실 원천까지 내려간다(위 Pattern 2).
**How to avoid:** 계획 문서에 "D-11 완료의 정의"를 `ProposalTier` 값 추가 + `ConfirmRequest`/`NarrationFacts` 재설계 + 웹/CLI 두 호출부 동시 반영 네 가지로 명시한다.
**Warning signs:** PLAN.md에 `action_classifier.py` 한 파일만 언급되어 있으면 이 함정이다.

### Pitfall 4: 등급 밴드 겹침 검사를 `margin_at_least`/`margin_at_most`만 보고 짠다
**What goes wrong:** `requires_doubles` 차원을 무시하면 OpenQuest처럼 두 밴드가 **같은 margin 구간, 다른 doubles 요구**로 공존하는 룰북에서 오탐(정상 밴드를 "가려짐"으로 잘못 판정)이 난다 — QUAL-03이 "기존 두 룰북을 등록 거부하지 않는다"(D-15)는 요구를 어기게 된다.
**Why it happens:** margin이 주인공처럼 보이고 `requires_doubles`는 부차적인 필드처럼 보인다.
**How to avoid:** Pattern 3의 2세계 분해를 그대로 구현하고, 반드시 OpenQuest 데이터로 회귀 테스트를 짠다(아래 Validation Architecture).
**Warning signs:** 검증 함수 시그니처가 `bands: tuple[GradeBand, ...]`만 받고 `requires_doubles`를 안 읽으면 이 함정이다.

## Code Examples

### 기존 패턴 — `GradeBand`(재사용할 판별 필드 + 선택적 페이로드 관례)
```python
# Source: src/gptrpg/rules_core/rulebook.py:19-31 (직접 읽음)
@dataclass(frozen=True)
class GradeBand:
    name: str
    counts_as_failure: bool
    margin_at_least: int | None = None
    margin_at_most: int | None = None
    requires_doubles: bool | None = None
```

### 기존 패턴 — 고정 필드 집합 시험(재고정 대상)
```python
# Source: src/gptrpg/rules_core/entities.py:93-96 (직접 읽음)
STAT_ENTRY_FIELD_NAMES = frozenset(f.name for f in fields(StatEntry))
ENTITY_FIELD_NAMES = frozenset(f.name for f in fields(Entity))
```

### 기존 패턴 — 세그먼트 원(재사용 가능한 프론트엔드 컴포넌트)
```tsx
// Source: frontend/src/components/ThreatClock.tsx:12-17 (직접 읽음)
interface ThreatClockProps {
  segment: number;
  segmentCount: number;
  size?: number;
  pulsing?: boolean;
}
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Ironsworn SRD의 상업적 이용 조건이 CC BY 4.0으로 별도 분리돼 있다는 서드파티 요약(WebSearch만, 공식 페이지 직접 열람 안 함) | Priority 1 후보 비교 | Ironsworn을 대안 후보로 검토할 경우, 실제로는 CC BY-NC-SA 4.0(비상업)만 적용되는 콘텐츠와 CC BY 4.0(상업) 콘텐츠가 챕터별로 섞여 있어 "SRD 페이지에 있다고 전부 CC BY"라고 오인하면 라이선스 위반 콘텐츠를 섞어 넣을 수 있다 — 채택 전 공식 라이선스 페이지(tomkinpress.com/pages/licensing) 직접 확인 필요 |
| A2 | Knave 2e·The Black Hack의 정확한 라이선스 조건(WebSearch 요약만, 공식 SRD 원문 직접 열람 안 함) | Priority 1 대안 후보 비교 | 이 문서는 Cairn을 주 후보로 권고하고 이 둘은 비교용으로만 언급했으므로 채택 시 재확인 필요 — 특히 Black Hack은 이름·로고가 오픈 콘텐츠에서 제외된다는 조건이 있어 표기 방식에 영향을 준다 |
| A3 | `GradeBand`/`StatEntry`의 검증 로직(Pattern 3)이 `rules_core`에 순수 함수로 둘 수 있다는 판단(문법상 가능함은 확인했으나, 계획 단계가 실제로 이 위치를 선택할지는 미확정) | Pattern 3, Architectural Responsibility Map | 계획이 다른 층(예: `rulebooks/__init__.py`)에 검증 로직을 두기로 하면 이 문서의 파일 배치 권고와 달라질 수 있음 — 이는 Claude's Discretion 항목("검증기를 어디에 둘지")이므로 이 문서는 강제하지 않는다 |

**참고:** Cairn RPG의 라이선스(CC-BY-SA 4.0)와 소지품/판정 메커니즘 요약은 공식 SRD 페이지(`https://cairnrpg.com/first-edition/cairn-srd/`)를 직접 열람해 확인했으므로 `[CITED]`로 표시했고 이 표에 넣지 않았다. `rules_core`/`agents`/`web`/`cli`/`frontend`의 모든 코드 인용은 이번 세션에서 해당 파일을 직접 읽고 확인한 `[VERIFIED]`다.

## Open Questions (RESOLVED)

아래 셋은 조사 단계가 열어 둔 질문이고, **셋 다 계획 단계에서 답이 났다.** 질문 원문은
무엇을 왜 물었는지가 남아야 하므로 지우지 않고 그대로 두고, 각 항목 끝에 **RESOLVED**
줄로 답과 그 답이 사는 자리(결정 번호 · 계획 · 작업)를 붙였다.

1. **D-05의 "두 갈래"와 D-13의 "여섯 형태" 사이의 정확한 관계**
   - What we know: D-13은 "없음"을 문자 그대로 하나의 형태처럼 나열했고, D-05는 "안 쓴다"가 반드시 두 갈래(규칙으로 안 센다/개념이 없다)로 갈린다고 명시한다.
   - What's unclear: "여섯 형태"라는 숫자를 문자 그대로 지킬지(`form="none"` + 하위 `none_kind` 판별자), 아니면 실질적으로 일곱 값(`numeric`/`clock`/`named_slots`/`tag_list`/`usage_die`/`none_discretionary`/`none_absent`)으로 갈지.
   - Recommendation: 이 문서는 6폼 + 하위 판별자를 권고했다(Pattern 1) — CONTEXT.md discuss-phase 단계에서 사장님께 이 절충이 D-13의 "여섯 가지"라는 숫자와 D-05의 "두 갈래" 요구를 둘 다 만족하는지 확인받는 것을 제안한다.
   - **RESOLVED — 6폼 + 하위 판별자로 확정** (`11-01-PLAN.md` § 「이 계획이 잠그는 설계 결정」
     결정 1, Task 1): 이 문서의 권고를 그대로 채택했다. `ResourceAxisForm`은 여섯 값
     (`numeric` / `clock` / `named_slots` / `tag_list` / `usage_die` / `none`)이고, D-05의
     두 갈래는 `form == "none"`일 때만 채우는 `none_kind`(`discretionary` = 규칙으로 안 셈 /
     `absent` = 개념 자체가 없음)로 가른다. D-13의 「여섯 가지」라는 숫자와 D-05의 「두 갈래」가
     동시에 성립하며, 두 갈래가 한 값으로 뭉개지지 않았다는 것은 11-01 Task 2의
     `test_discretionary_and_absent_are_different_none_kinds`가 시험으로 고정한다.

2. **D-06의 "빠뜨림 구조적 불가능"이 어디까지 플랫폼 강제인가**
   - What we know: `resource_axes` 필드 자체의 존재는 파이썬 생성자 수준에서 강제 가능하다(D-02, 확인됨). "체력·소지품·스트레스·진행 원 각각을 다뤘는가"는 반편향 원칙상 플랫폼이 이름을 몰라야 하므로 강제할 수 없다.
   - What's unclear: RULE-11의 "체력·소지품·스트레스·진행 원"이라는 네 가지 예시가 실제로는 이 프로젝트의 지금까지 룰북 두 개가 우연히 공유하는 개념일 뿐, 플랫폼이 알아야 하는 고정 목록이 아니라는 것이 계획 단계에 명확히 전달됐는가.
   - Recommendation: PLAN.md 작성 시 "네 개념 각각의 커버리지 검증"을 코드 검증 대상에서 명시적으로 제외하고, 대신 "룰북이 `resource_axes`에 최소 하나 이상 명시적으로 적었는가"(빈 튜플도 명시이므로 이 검사는 사실상 항상 통과) 정도로 검증 범위를 좁혀 서술한다.
   - **RESOLVED — 권고대로 강제 범위를 좁혔고, 계획에 명시적으로 전달됐다**
     (`11-01-PLAN.md` § 결정 2 · Task 1, 그리고 11-02의 등록 시점 검사): 플랫폼이 강제하는
     것은 **「룰북이 `resource_axes`라는 필드를 적었는가」까지**다 — D-02의 기본값 없는 필수
     인자라 빠뜨리면 생성자에서 `TypeError`로 즉시 죽는다. **「체력·소지품·스트레스·진행 원
     네 개념을 각각 다뤘는가」는 코드 검증 대상에서 명시적으로 제외했다.** RULE-11의 그 네
     이름은 지금 룰북 둘이 우연히 공유하는 개념일 뿐 플랫폼이 아는 고정 목록이 아니라는
     판단이 11-01의 `prohibitions`에 「`rules_core` 코드가 체력·소지품·스트레스·진행 원 같은
     룰북 어휘 이름을 상수나 조건문으로 알지 않는다」는 시험 가능한 금지로 못 박혀 있고,
     경계 문장 자체는 `ResourceAxisDecl` 도크스트링에 남는다. 등록 시점 검사(11-02)도 같은
     경계 안에서 D-15의 「가려짐·구멍」만 본다.

3. **판정 없이 진행하는 서술 경로(D-10의 ②)의 정확한 진입점**
   - What we know: `narrate()`로 가는 모든 기존 경로가 `ResolveCheck`에서 파생된 `check_summary`를 전제한다(Pattern 2에서 확인).
   - What's unclear: 판정 없는 서술이 `confirm()` 안에서 `move`/`stat`을 선택 필드로 만들어 우회하는 형태로 갈지, 아니면 `declare()`가 no_check일 때 곧바로 서술까지 마치는 새 응답 형태로 갈지 — 프론트엔드의 "확인 버튼 클릭" UX가 그대로 남는가도 여기 걸린다.
   - Recommendation: 이 결정은 RULE-15 자체보다 D-10/D-11의 실행 설계이므로, Phase 11 계획이 이 지점까지 완전히 구현할지(코드 변경 범위가 매우 크다) 아니면 "판정 트리거 목록이 비면 재량 판정으로 떨어진다"는 **선언 가능성**까지만 이 단계에서 만들고 실제 서술 파이프라인 재배선은 별도 후속 계획으로 쪼갤지, 계획 단계가 명시적으로 판단해야 한다. CONTEXT.md의 "이 단계를 몇 개의 계획으로 쪼갤지" discretion 항목이 정확히 이 결정을 가리킨다.
   - **RESOLVED — 「어디까지 만들 것인가」는 CONTEXT.md D-10이 이미 답했고, 진입점 형태는
     11-05/11-06이 답했다.** 이 항목이 계획 단계에 넘긴 갈림길 중 **앞쪽(선언 가능성까지만
     만들고 파이프라인 재배선은 후속으로 미룬다)은 실제로는 열려 있지 않았다** —
     CONTEXT.md D-10이 「굴릴 필요가 없는 행동은 판정 없이 그냥 진행된다」를 **정식 경로**로
     만들기로 이미 정했고, 그 Reversibility 항목(`costly`)이 함께 바뀌는 네 자리를 그대로
     열거해 두었다: **분류기 반환 계약 · 웹 `declare` 응답 · 화면 세 갈래 확인 · CLI 턴 흐름.**
     즉 재배선은 이 단계의 범위 안이다.
     **코드 변경 범위가 크다는 문제에 대한 답은 미루기가 아니라 얇게 쪼개기였다**
     (CONTEXT.md의 「이 단계를 몇 개의 계획으로 쪼갤지」 discretion을 이렇게 소진했다):
     분류기 반환 계약을 네 갈래로 여는 것은 **11-05**가, 그 ② 갈래를 실제 서사에 잇는
     재배선(웹 라우트 · CLI 같은 갈래 · 화면 세 갈래)은 **11-06**이 맡는다.
     진입점 형태의 미확정 부분도 결정됐다 — `confirm()`의 `move`/`stat` 제약을 풀어 우회하는
     형태는 **채택하지 않았고**(판정 경로에 빈 값이 새는 것을 막는다), 대신 **별도
     `POST /sessions/{sid}/proceed` 라우트**를 신설한다(`11-06-PLAN.md` Task 1). 프론트엔드의
     「확인 버튼 클릭」 UX는 남되 갈래가 갈린다 — `no_check`에는 후보 버튼도 「다시 쓰기」도
     없이 [이대로 진행] 버튼 하나만 뜬다(`11-06-PLAN.md` § 결정 2 · Task 2).

## Environment Availability

이 단계는 외부 도구·서비스·런타임 의존을 새로 추가하지 않는다(순수 파이썬 코드 확장 + 프론트엔드 TSX 확장 + 하나의 정적 데이터 파일). 기존 개발 환경(Python 3.13/3.14, `uv`, `pytest`)이 그대로 충분하다 — 이 섹션은 스킵한다.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest(`[VERIFIED: pyproject.toml:51-53]` — `[tool.pytest.ini_options]\ntestpaths = ["tests"]\nasyncio_mode = "auto"`) |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_entities.py tests/test_rulebook.py -q` (후자는 이번 단계가 신설) |
| Full suite command | `uv run pytest -q` |

프론트엔드 전용 자동 테스트 프레임워크는 이 저장소에 없다(`find frontend -iname "*.test.*"` 결과 0건 확인) — RULE-12 성공 기준 2("완전히 사라진다")의 화면 쪽 검증은 백엔드 응답 계약 테스트로 충분히 커버되도록 설계해야 한다(아래 REQ 매핑 참조). 프론트엔드 렌더링 자체의 자동 회귀는 이 단계 범위 밖이다(Phase 16이 프론트엔드 전면 감사를 맡는다).

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RULE-11 | 6가지 표현 형태 모두 `StatEntry`로 유효하게 구성된다(형태별 정합성 검증 포함) | unit | `uv run pytest tests/test_entities.py -k form -x` | ❌ Wave 0 — 새 테스트 함수 신설 |
| RULE-11 | `STAT_ENTRY_FIELD_NAMES`가 정확히 8칸으로 재고정된다 | unit | `uv run pytest tests/test_entities.py::test_stat_entry_field_names_are_exactly_eight -x` | ❌ Wave 0 — 기존 `test_stat_entry_field_names_are_exactly_four`(`tests/test_entities.py:25`) 재작성 |
| RULE-12 | `form=="none"`인 축이 `CharacterSheetView` 응답 자체에서 제외된다(화면이 아니라 서버 응답 레벨에서 사라짐을 단언) | integration | `uv run pytest tests/test_web_characters.py -k none_axis_excluded -x` | ❌ Wave 0 — 응답 JSON에 해당 축 이름이 **문자열로도 등장하지 않는지** 단언하는 새 테스트 |
| RULE-12 | 「값이 0」(`form="numeric", current=0`)과 「개념이 없음」(`form="none", none_kind="absent"`)이 서로 다른 `StatEntry`로 명확히 구성 가능하고 서로 바뀌지 않는다 | unit | `uv run pytest tests/test_entities.py -k zero_vs_absent -x` | ❌ Wave 0 |
| RULE-12 | 룰북이 `resource_axes`를 빠뜨리면(필드 자체를 안 씀) 등록/임포트가 실패한다 | unit | `uv run pytest tests/test_rulebook.py -k missing_resource_axes -x` | ❌ Wave 0 — `Rulebook(...)` 호출에서 `resource_axes` 인자를 뺀 경우 `TypeError`를 단언 |
| RULE-15 | 룰북의 `move_triggers`(또는 기존 `MoveDecl` 목록)가 빈 튜플이어도 룰북 등록·`get_moves()` 호출이 정상 동작한다(정상값 확인) | unit | `uv run pytest tests/test_rulebook.py -k empty_move_list_is_valid -x` | ❌ Wave 0 |
| RULE-15 | 4갈래 분류기 tier 값(`single`/`several`/`no_check`/`unclear`)이 후보 개수·no_check 신호·UnknownMove 흡수 세 입력 조합에서 올바르게 계산된다 | unit | `uv run pytest tests/test_action_classifier.py -k tier -x` | 부분 존재 — 기존 tier 테스트(`tests/test_action_classifier.py:64-88`)를 4값으로 확장 |
| QUAL-03 | 던전월드류·OpenQuest 기존 두 룰북이 새 등록 검증을 통과한다(회귀) | unit | `uv run pytest tests/test_rulebook.py -k existing_rulebooks_pass_validation -x` | ❌ Wave 0 — Pattern 3의 손 시뮬레이션을 코드 테스트로 고정 |
| QUAL-03 | 인위적으로 가려진 밴드(앞 밴드가 뒷 밴드를 완전히 덮음)를 등록하면 거부된다 | unit | `uv run pytest tests/test_rulebook.py -k shadowed_band_rejected -x` | ❌ Wave 0 |
| QUAL-03 | 인위적인 구멍(어떤 margin·doubles 조합도 못 잡는 밴드 집합)을 등록하면 거부된다 | unit | `uv run pytest tests/test_rulebook.py -k hole_rejected -x` | ❌ Wave 0 |
| QUAL-03 | 단순 겹침(선언 순서로 해소되는 정상 겹침)은 거부되지 않는다(D-15 해석 회귀) | unit | `uv run pytest tests/test_rulebook.py -k simple_overlap_is_legal -x` | ❌ Wave 0 |
| D-14 | 세 번째 룰북(Cairn류)이 플랫폼 코드 수정 없이 데이터만으로 등록되고, `move_triggers` 빈 목록 + `named_slots` 형태를 실제로 담는다 | integration | `uv run pytest tests/test_rulebook.py -k third_rulebook -x` | ❌ Wave 0 — HYP-03과 같은 성격의 검증(02-INTERFACE-CHANGES.md 선례) |

### Sampling Rate
- **Per task commit:** 위 표의 개별 `-k` 필터 명령(관련 테스트만 빠르게)
- **Per wave merge:** `uv run pytest -q`(전체 스위트)
- **Phase gate:** `uv run pytest -q` 초록 + `import-linter`(`.importlinter` 계약 1·2 위반 없음, `rules_core` 확장이 순수성을 유지하는지 확인) — `[VERIFIED: .importlinter:5-22]` 실제 계약: `forbidden_modules = time / random / os / socket / datetime / secrets / sqlite3 / asyncio / pathlib / urllib / http`

### Wave 0 Gaps
- [ ] `tests/test_rulebook.py` — 신설 필요. 지금 이 파일이 없다(`grade_for_margin`/`GradeBand` 테스트는 `tests/test_grading_d100.py`에 간접적으로만 있다 — 확인함, `grep -n "def test_" tests/test_grading_d100.py` 8개 함수 전부 d100 판정 경로를 통해서만 밴드를 시험한다). QUAL-03의 등록 시점 검증은 판정 경로와 독립적으로 시험해야 한다.
- [ ] `tests/test_entities.py`의 `test_stat_entry_field_names_are_exactly_four`(25행)와 `test_entity_field_names_are_exactly_four`(31행) — 재작성 대상(D-03 요구, 삭제 아님)
- [ ] `tests/test_action_classifier.py` — 4갈래 tier 확장 시험 추가(64~88행의 기존 5개 tier 테스트 옆에)
- [ ] `tests/test_web_characters.py`(존재 여부 미확인 — `characters_data.py` 도크스트링이 이 파일명을 인용하고 있으나 이번 세션에서 직접 읽지 않았다. 계획 단계가 실제 존재 여부와 현재 커버리지를 먼저 확인할 것)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 이 단계는 인증 경로를 건드리지 않는다 |
| V3 Session Management | no | 〃 |
| V4 Access Control | no | 〃 |
| V5 Input Validation | yes | 룰북 파일 자체는 지금 신뢰된 소스(git 추적 파이썬 코드, 사람이 리뷰)이지만, **등록 시점 검증(`InvalidStatEntry`/`InvalidEntity`/신규 밴드 검증 예외)이 이 계층의 실질적 V5 통제다** — "조용히 기본값으로 넘기지 않고 그 자리에서 예외로 멈춘다"는 이 저장소의 기존 규율(`UnknownEventType`·`NoMatchingGradeBand`·`UnknownRulebook`)을 그대로 확장한다 |
| V6 Cryptography | no | 관련 없음 |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 형태(form)와 페이로드 필드가 안 맞는 `StatEntry`가 조용히 통과해 화면·판정 로직이 `None` 필드를 역참조 | Tampering(데이터 무결성) | `__post_init__`에서 form별 필드 정합성을 즉시 검증하고 실패 시 예외(Pitfall 1 참조) — 신뢰 경계 자체가 "룰북 코드"이므로 외부 공격 표면은 아니지만, M1의 룰북 업로드가 이 경계를 신뢰 불가로 바꾼다는 것을 `resolution_d100.py:41`의 `MAX_BONUS_DICE_MAGNITUDE` 도크스트링이 이미 명시하고 있다 — 이 단계의 검증도 같은 미래를 전제로 짜야 한다 |
| 「안 쓴다」 선언이 서버 응답에서 안 걸러지고 클라이언트로 새어 나가 화면이 아니라 API 계약이 「완전히 사라짐」을 어김 | Information Disclosure | Pitfall 2 참조 — 서버 응답 조립 단계에서 필터링, 프론트엔드 조건부 렌더링에 의존하지 않는다 |
| 등급 밴드 구멍(hole)으로 인한 `NoMatchingGradeBand` 런타임 예외가 등록 시점이 아니라 실제 판정 중에 터져 진행 중이던 턴을 죽임 | Denial of Service(가용성) | Pattern 3의 등록 시점 사전 검증이 정확히 이 문제를 예방한다 — QUAL-03의 존재 이유 자체가 이 위협 패턴 |

## Sources

### Primary (HIGH confidence — 이번 세션에서 직접 읽은 이 저장소의 소스 코드)
- `src/gptrpg/rules_core/entities.py` — StatEntry/Entity 현재 모양, 고정 시험 상수
- `src/gptrpg/rules_core/rulebook.py` — GradeBand/Rulebook/grade_for_margin 전문
- `src/gptrpg/rules_core/resolution.py`, `resolution_d100.py` — 2d6/d100 두 판정 경로가 `grade_for_margin`을 실제로 어떻게(혹은 안) 쓰는지
- `src/gptrpg/agents/action_classifier.py` — ProposalTier/Proposal/classify() 전문
- `src/gptrpg/agents/prompt_assembly.py` — 6개 프롬프트 조립 함수 전문, 캐싱 순서 규약
- `src/gptrpg/agents/context.py` — TurnContext/NarrationFacts/각종 상한 상수
- `src/gptrpg/rulebooks/__init__.py`, `moves.py`, `dungeonworld_like.py`, `openquest.py`, `openquest_creatures.py`
- `src/gptrpg/web/routes_actions.py`, `routes_characters.py`, `characters_data.py`
- `src/gptrpg/cli/turn_flow.py`
- `src/gptrpg/turn/context.py`, `turn/judgments.py`
- `frontend/src/panes/StatusPane.tsx`, `panes/ChatPane.tsx`, `components/ThreatClock.tsx`, `labels.ts`, `api/types.ts`
- `.importlinter`, `pyproject.toml`
- `LICENSES.md` — OpenQuest 첨부 문구 선례
- `tests/test_entities.py`, `test_action_classifier.py`, `test_grading_d100.py` — 파일 목록·테스트 함수 이름으로 존재 여부·현재 커버리지 확인

### Secondary (MEDIUM confidence — 공식 페이지 직접 열람)
- Cairn RPG SRD — `https://cairnrpg.com/first-edition/cairn-srd/` (WebFetch로 직접 열람, 라이선스 문구·슬롯 인벤토리·세이브 기반 판정·자원 셋을 확인)

### Tertiary (LOW confidence — WebSearch 요약만, 원문 미열람. `## Assumptions Log` A1·A2 참조)
- Ironsworn SRD 라이선스(CC BY-NC-SA 4.0 비상업 / CC BY 4.0 상업 이원화) — `https://tomkinpress.com/pages/licensing`
- Knave 2e 서드파티 라이선스 존재 — 공식 페이지 미확인
- The Black Hack SRD OGL 조건, 이름/로고 제외 — `https://www.tenkarstavern.com/2016/05/the-black-hack-rpg-licensing-guidelines.html` 등

## Metadata

**Confidence breakdown:**
- 자원 축 컨테이너 설계(Pattern 1): HIGH — 기존 `GradeBand`/`StatEntry` 코드를 직접 읽고 확장한 것이라 근거가 코드 자체에 있다. 단, D-05/D-13 사이 형태 개수 절충은 계획 단계 확인이 필요한 권고다(MEDIUM)
- 분류기 4갈래·서술 경로(Pattern 2): HIGH — 두 호출부(`routes_actions.py`/`turn_flow.py`) 모두 직접 읽고 실제 코드 줄로 파급 범위를 확인했다
- 등급 밴드 검증 알고리즘(Pattern 3): HIGH — 두 기존 룰북에 대해 알고리즘을 손으로 시뮬레이션해 통과를 확인했다(연구 우선순위가 명시적으로 요구한 검증을 실제로 수행)
- 세 번째 룰북 후보(Priority 1): MEDIUM — Cairn 공식 SRD 페이지를 직접 열람해 확인, ShareAlike 조항까지 명시. 대안 후보(Ironsworn 등)는 LOW(원문 미열람)
- Validation Architecture: MEDIUM — 테스트 명령·파일 위치는 기존 관례에서 추론했으나 `tests/test_rulebook.py` 자체가 신설 파일이라 정확한 최종 배치는 계획 단계 판단

**Research date:** 2026-08-15
**Valid until:** 이 저장소의 코드 구조에 근거한 조사이므로, Phase 11 착수 전 코드가 추가로 바뀌지 않는 한 유효 — 세 번째 룰북의 라이선스 정보는 외부 웹 콘텐츠라 재확인 권장 기한 90일(SRD 페이지 자체가 자주 안 바뀌는 안정적 참조 문서라 표준 30일보다 길게 잡음)

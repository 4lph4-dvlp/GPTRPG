# Phase 2: 룰북 두 개를 같은 그릇에 - Research

**Researched:** 2026-08-01
**Domain:** d100 롤언더 판정 방식 구현 + 룰북-선언형 등급/수정치 스키마 + 적/NPC 공용 상태값 그릇 + CC 라이선스 콘텐츠 선정
**Confidence:** MEDIUM-HIGH (코드 통합 지점은 HIGH — 직접 읽은 소스에서 확인. 라이선스 후보 비교는 MEDIUM — 공식 사이트에서 확인했으나 2차 커뮤니티 요약을 함께 사용)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-18:** d100 콘텐츠는 **CC 라이선스가 있는 실제 룰북 자료를 찾아 쓴다.** 자체 창작 미니 룰북은 쓰지 않는다.
  - *이유:* 자체 창작은 검증 목적과 무관한 번역·정리 작업이 늘어난다. 실제 CC 라이선스 콘텐츠를 쓰면 라이선스 표기 관행(LAW-04)까지 자연스럽게 검증된다.
- **D-19:** 구체적인 CC 라이선스 후보 탐색은 이 리서치 단계(gsd-phase-researcher)의 몫이다. (본 문서가 그 답이다 — 아래 "d100 CC 라이선스 콘텐츠 후보" 절 참고)
- **D-20:** 적/NPC 상태값 하나의 모양은 **{이름, 현재값, 최대값(선택), 바닥날 때 효과 참조}**. `Modifier`(type/value/source)의 "값 + 출처/의미" 패턴을 재사용한다.
- **D-21:** 적/NPC 하나가 가질 수 있는 상태값 개수는 **제한 없음 — 목록(list)**.
- **D-22:** 성공 조건 5번(플랫폼 코드를 고쳤는지)은 **별도 문서** `02-INTERFACE-CHANGES.md`(가칭)로 남긴다. **고친 곳**과 **고치지 않고 데이터로 버틴 곳**을 둘 다 담되, 뒤쪽("고치고 싶었지만 참았다")이 더 중요하다.
- **D-23:** 크툴루 d100 푸시 롤(재굴림)은 **실제 동작까지 구현한다.** `reroll_2d6`과 같은 패턴 — 앞선 눈을 지우지 않고 이어 붙인다.
- **D-24:** 나머지 세 수정치 유형(숫자 가감·주사위 추가/제거·목표값 변경)도 **전부 실제 동작까지 만든다.** 자리만 열어두지 않는다. (숫자 가감은 Phase 1에 이미 있음 — 이 결정은 나머지 둘의 몫)

### Claude's Discretion

- CC 라이선스 d100 콘텐츠의 구체적 후보 — 본 문서가 결정한다 (D-19)
- `02-INTERFACE-CHANGES.md`의 정확한 파일명과 형식
- 등급 집합을 룰북이 선언하는 구체적 데이터 형식(이름 목록 vs 수치 구간을 어떻게 같은 필드에 담을지)
- 주사위 추가/제거(보너스 다이스) 수정치의 정확한 계산 규칙
- 목표값 변경 수정치가 `CheckOutcome.target`과 상호작용하는 방식

### Deferred Ideas (OUT OF SCOPE)

- 룰북 데이터의 필드 단위 상세 규격 · 효과 원자 연산의 최종 목록 (M1)
- d20 롤오버 등 세 번째 이후 판정 방식 (M1 이후)
- 룰북 파일 업로드 + 자동 구조화 (M1-04)
- 좌표계·전술 그리드·시야 계산 (M4)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RIG-08 | 판정 방식이 서로 다른 룰북 두 개(2d6 등급식 / d100 롤언더)와 그 룰북들의 적이 코드 수정 없이 데이터로만 들어간다 | "d100 CC 라이선스 콘텐츠 후보" 절이 실제 콘텐츠 소스를 확정하고, "Architecture Patterns"가 등급/수정치/적 상태값을 코드 무변경으로 표현하는 구체적 패턴을 제시한다 |
| HYP-03 | 룰북을 데이터로 표현할 수 있다 — 두 번째 룰북이 들어간다. 실패하면 유저 콘텐츠 마켓이 소멸한다 | "Integration Points" 절이 플랫폼 코드가 실제로 건드려야 하는 5개 지점(schema.py, resolution.py, reducer.py, actor.py, dice.py)을 정확한 파일·줄로 짚어, `02-INTERFACE-CHANGES.md`에 무엇을 "고친 곳"과 "참은 곳"으로 나눠 적을지 판단할 근거를 만든다 |

</phase_requirements>

## Summary

이 단계의 진짜 난제는 두 가지다. 첫째, D-18이 요구하는 "CC 라이선스가 있는 실제 d100 룰북"을 실제로 찾아 검증하는 것 — **OpenQuest System Resource Document**(CC BY 4.0, D101 Games/Newt Newport, 2021)를 1순위로 추천한다. 라이선스 문구가 명확하고, 판정 규칙(d100 roll-under, 4단계 등급, 퍼센트 가감식 난이도 수정치, 다중 상태값을 가진 크리처)이 전부 무료 SRD 페이지에 텍스트로 공개돼 있다. 둘째, 이 콘텐츠를 플랫폼 코드 위에 얹을 때 Phase 1이 남긴 다섯 개의 실제 접점(사건 스키마의 `Grade` 리터럴, `resolution.py`의 `_flat_total`, `reducer.py`의 `grade == "miss"` 하드코딩, `session_actor`의 `resolve_2d6` 고정 호출, `dice.py`의 `Roller` 프로토콜)을 정확히 찾아, 각각을 "확장"(새 코드 추가)으로 처리할지 "변경"(기존 코드 수정)으로 처리할지 미리 판단해 두는 것이다. 이 중 최소 하나(`event_log/schema.py`의 `Grade` 리터럴)는 명백히 손을 대야 한다 — CONTEXT.md도 이를 이미 예견했다. 그러나 이번 조사에서 새로 발견한 `reducer.py:66`의 `grade == "miss"` 문자열 비교는 CONTEXT.md에 언급되지 않은 **여섯 번째 지뢰**이며, d100 등급 이름이 "miss"가 아니면 실패 집계가 조용히 틀려질 수 있는 지점이다.

수정치 네 유형 중 숫자 가감(FLAT)과 목표값 변경은 OpenQuest의 실제 규칙(난이도 ±20%/±50%)으로 바로 검증 가능하다. 주사위 추가·제거(보너스 다이스)와 재굴림(푸시 롤)은 OpenQuest 자체에는 없는 메커닉이므로, 크툴루 계열 커뮤니티 문서에서 확인한 일반적인 d100 관행(보너스 다이스 = 십의 자리 주사위 추가 굴림 후 유리한 쪽 채택)을 플랫폼이 제공하는 **범용 수정치 유형**으로 구현하고, Phase 2가 직접 작성하는 소량의 예시 판정 데이터로 동작을 증명하는 것을 권장한다 — 이는 D-18("실제 자료를 찾아 쓴다")과 모순되지 않는다. D-18의 "콘텐츠"는 판정 종류·등급·적 스탯 같은 룰북 선언 내용을 가리키고, 수정치 유형 자체는 플랫폼이 제공하는 계산 능력이기 때문이다.

**Primary recommendation:** d100 콘텐츠 소스로 **OpenQuest SRD (CC BY 4.0)**를 채택하고, `Grade`를 `event_log/schema.py`·`rules_core/grading.py` 양쪽에서 고정 `Literal`이 아닌 문자열로 넓힌다. 보너스/페널티 다이스와 푸시 롤은 OpenQuest 콘텐츠에 없더라도 플랫폼 수정치 유형으로 구현하고 소규모 자체 작성 판정 예시로 검증한다. `reducer.py`의 `grade == "miss"` 하드코딩과 `session_actor`의 `resolve_2d6` 고정 호출은 이번 단계에서 반드시 재검토해야 할 항목으로 `02-INTERFACE-CHANGES.md`에 명시적으로 기록한다.

## Architectural Responsibility Map

> 이 프로젝트는 웹 다중 계층 앱이 아니라 Phase 1이 세운 3계층 순수 백엔드(`rules_core` / `event_log` / `session_actor`, CLI가 진입점)다. 아래 표는 이 프로젝트 고유의 계층 어휘로 작성했다.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| d100 판정 계산(굴림→등급) | `rules_core` (새 모듈, 예: `resolution_d100.py`) | — | 순수 함수, 시간·무작위·IO 금지 — `.importlinter` forbidden 계약이 강제 |
| 등급 집합 선언(이름 목록/수치 구간) | 룰북 데이터(신규 계층, 예: `gptrpg/rulebooks/`) | `rules_core`(그 선언을 소비하는 함수) | D32: "그릇은 플랫폼, 내용은 룰북" — 선언은 룰북, 계산 함수는 플랫폼 |
| 수정치 4유형 계산 | `rules_core` | 룰북 데이터(어떤 수정치를 어떤 판정에 붙일지) | 계산 로직은 플랫폼, "이 판정엔 이 수정치가 붙는다"는 룰북 |
| 판정 방식 선택(2d6 vs d100) | `session_actor` (`ResolveCheck` 처리부) | — | rules_core는 특정 룰북을 몰라야 하므로, "어떤 함수를 부를지" 배선은 한 계층 위(session_actor)의 책임 |
| 사건 기록 스키마의 `grade` 필드 타입 | `event_log` | — | 저장 계약이자 재생 계약 — 폭을 넓히면 `EVENT_SCHEMA_VERSION` 문제와 직결 |
| 적/NPC 상태값 그릇 | 신규 계층(세션 상태 또는 `session_actor`가 관리하는 엔티티 저장소) | `event_log`(상태 변경도 사건이어야 한다는 원칙, D-11) | D32: 그릇(식별자·표시 이름·상태값 묶음)은 플랫폼, 항목 뜻·바닥효과는 룰북 |
| 굴림 도구 확장(퍼센트 다이스) | `rules_core/dice.py` | — | 기존 `Roller` 프로토콜을 건드리지 않고 새 구조적 프로토콜을 나란히 추가 |
| "플랫폼 코드를 고쳤는지" 기록 | 신규 문서(`02-INTERFACE-CHANGES.md`) | — | D-22가 요구하는 사람이 읽는 단일 장소 |

## Standard Stack

### Core

이 단계는 **새 외부 라이브러리를 필요로 하지 않는다.** 순수 판정 로직·데이터 선언·문서 작성이 전부이고, Phase 1이 이미 확보한 스택으로 충분하다.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | ≥2.13.4 (이미 `pyproject.toml`에 고정, `[VERIFIED: pyproject.toml:11]`) | `event_log/schema.py`의 사건 검증 — `Grade` 폭 확장도 여기서 처리 | Phase 1이 이미 표준으로 채택, 새 판정 방식도 같은 검증 계층을 재사용해야 일관성이 깨지지 않는다 |
| hypothesis | ≥6.164.0 (`[VERIFIED: pyproject.toml:23]`) | d100 등급 경계·보너스 다이스 조합의 속성 기반 테스트 — `test_resolution_edges.py`가 이미 이 패턴을 증명 | Phase 1의 `test_edge_adjacency_*`가 같은 패턴을 재사용할 수 있음을 보여준다 |
| pytest / pytest-asyncio | ≥9.1.1 / ≥1.4.0 (`[VERIFIED: pyproject.toml:25-26]`) | 테스트 러너 | 이미 표준 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (없음) | — | — | 룰북 데이터는 Python dataclass/딕셔너리로 손으로 쓴다(REQUIREMENTS.md "룰북 저작 도구"는 Out of Scope) — JSON/YAML 파서 같은 새 의존성이 필요 없다 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python dataclass로 룰북 데이터 손으로 쓰기 | YAML/JSON 파일 + 파서 라이브러리 | 파일 업로드/파싱은 M1-04로 명시적으로 미뤄졌다(CONTEXT.md deferred). 지금 파서를 들이면 이 단계가 증명해야 할 것(코드 무변경)과 무관한 작업이 늘어난다 |
| 범용 규칙 엔진(예: 조건 DSL 라이브러리) 도입 | 자체 pure function 두 세트(`resolve_2d6`/`resolve_d100`) | 효과 원자 연산(D7)과 필드 단위 규격은 M1 몫 — 지금 범용 엔진을 만들면 과잉 추상화이고, Phase 1과 스타일도 어긋난다 |

**Installation:** 불필요 (신규 패키지 없음).

**Version verification:** 신규 패키지가 없으므로 생략. 기존 의존성 버전은 `pyproject.toml`을 직접 읽어 확인했다(위 표의 `[VERIFIED]` 태그).

## Package Legitimacy Audit

**이 단계는 새 외부 패키지를 설치하지 않는다.** 따라서 Package Legitimacy Gate 프로토콜(레지스트리 조회·`gsd-tools query package-legitimacy check`)은 적용 대상이 없다.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| *(해당 없음)* | — | — | — | — | — | N/A — 신규 패키지 없음 |

**Packages removed due to [SLOP] verdict:** 없음
**Packages flagged as suspicious [SUS]:** 없음

---

## d100 CC 라이선스 콘텐츠 후보 (D-19의 답)

### 후보 비교

| 후보 | 라이선스 | 등급 수 | 목표값 변경(난이도) | 보너스/페널티 다이스 | 푸시 롤 | 적 스탯 다중값 |
|---|---|---|---|---|---|---|
| **OpenQuest SRD (D101 Games)** | **CC BY 4.0** `[VERIFIED: openquestrpg.com/srd/licensing/]` | 4 (Critical/Success/Failure/Fumble, 이름 목록) `[CITED: openquestrpg.com/srd/skills/skill-rules/]` | 있음 — Easy +50%/Simple +20%/Normal +0%/Difficult −20%/Hard −50% `[CITED: openquestrpg.com/srd/skills/difficulty/]` | **없음** (조사 결과 확인 안 됨) | **없음** (조사 결과 확인 안 됨) | 있음 — Hit Points + Magic Points `[CITED: 검색 요약, openquestrpg.com/srd/creatures/creature-format/]` |
| Basic Roleplaying SRD (Chaosium) | **BRP Open Game License v1.0** — CC 아님, WotC OGL도 아닌 Chaosium 독자 라이선스. **"Pushing"(재굴림) 메커닉이 명시적으로 Prohibited Content(크툴루와 "substantially similar"하면 금지)로 지정됨** `[VERIFIED: chaosium.com/content/FreePDFs/BRP/BRP SRD - V1.0.pdf p.1-2, 직접 PDF 읽음]` | 5 (Critical/Special/Success/Fail/Fumble, 스킬값의 5%/20%/100%/파산 구간 기반 수치 구간) `[CITED: 검색 요약]` | 있음(추정, 조사에서 세부 미확인) | 조사에서 세부 미확인 | **금지 조항 있음** — 이 라이선스로는 못 씀 | 조사 안 함 |
| Open Cthulhu HPLed SRD (Cthulhu Reborn, 팬 편찬) | **OGL 1.0a** (Wizards 원 OGL) — CC 아님. Delta Green Agent's Handbook(16%)·Legend RPG(2%)·Eldritch Tales/Cthuloid Bestiary(6%) 텍스트를 짜깁기한 비공식 3차 편찬물 `[CITED: cthulhureborn.wordpress.com, mdhughes.tech]` | 5 — critical/extreme/hard/normal/failure (+ 폭 참패 별도 여부 조사에서 불확실) `[CITED: 검색 요약]` | 있음 | **있음** — 십의 자리 다이스 추가 후 유리/불리 쪽 채택 (표준 크툴루 관행) `[CITED: call-of-cthulhu-nachtstadt-berlin.fandom.com]` | **있음** — 크툴루 정체성 메커닉 원문 그대로 | 조사 안 함(가능성 높음, 미검증) |
| Delta Green Agent's Handbook | 공식 SRD 별도 미확인 — "Legend SRD 기반" 서술만 발견, Arc Dream이 독립 SRD로 공개했는지 불확실 | — | — | — | Delta Green이 크툴루 푸시 롤의 원류(원조 명칭: "Push a roll") | — |
| Renaissance Deluxe (Cakebread & Walton) | OGL — CC 아님, OpenQuest 기반 파생물 | — | — | — | — | — |

### 결론과 권장

**1순위 (Primary): OpenQuest System Resource Document.** D-18의 문구("CC 라이선스가 있는")를 글자 그대로 만족하는 유일한 후보다. 라이선스가 CC BY 4.0으로 명확하고, 필요한 첨부 문구까지 SRD 페이지에 이미 완성돼 있다(아래 인용). 4단계 등급(이름 목록), 목표값 변경형 난이도 수정치, 다중 상태값(HP+MP)을 가진 크리처까지 판정 인터페이스 검증에 필요한 만큼은 실제 콘텐츠로 커버된다.

> **필수 첨부 문구 (openquestrpg.com/srd/licensing/에서 그대로 인용):**
> "This work is based on the OpenQuest System Resource Document (found at https://openquestrpg.com/srd), a D101 Games product developed, authored by Newt Newport with Paul Mitchener. OpenQuest System Resource Document © 2021 by Newt Newport with Paul Mitchener is licensed under Attribution 4.0 International. To view a copy of this license, visit http://creativecommons.org/licenses/by/4.0/"

**빠진 것: 보너스/페널티 다이스와 푸시 롤.** OpenQuest는 이 두 메커닉이 조사 범위에서 확인되지 않았다(Legend/RuneQuest 계열은 애초에 이 메커닉이 없다 — 이건 크툴루 계열의 정체성이다, D27 발견 2). D-23·D-24는 "실제 동작"을 요구하지만 "OpenQuest 원문이 이 메커닉을 선언해야 한다"고 요구하지 않는다 — 두 메커닉은 **플랫폼이 제공하는 범용 수정치 계산 능력**으로 구현하고, Phase 2가 손으로 쓰는 소량의 판정 예시 데이터(스코프 펜스가 허용하는 "필드 단위 상세 규격 아닌 최소 예시")로 동작을 증명하는 것을 권장한다. 이 경우 계산 규칙 자체는 CC 콘텐츠가 아니라 널리 알려진 d100 장르 관행을 인용해야 하므로 `[CITED: call-of-cthulhu-nachtstadt-berlin.fandom.com/wiki/Bonus_Dice_and_Penalty_Dice]`로 태그한다 — OpenQuest 저작물이 아니다.

**대안 (Fallback), 조건부: Open Cthulhu HPLed SRD.** 두 메커닉(보너스/페널티 다이스, 푸시 롤)이 원문에 실제로 존재하고, 크툴루 장르 검증으로서 더 설득력 있다. 그러나 라이선스가 **CC가 아니라 OGL 1.0a**이고, 팬이 여러 출처(Delta Green·Legend·Eldritch Tales)를 짜깁기한 3차 편찬물이라 저작권 사슬이 OpenQuest보다 복잡하다. **D-18의 "CC 라이선스" 문구를 엄격히 지킨다면 이 후보는 탈락**이다. 이 판단(엄격한 CC 해석 vs "실질적으로 열려 있으면 OGL도 허용")은 플래너/디스커스 단계에서 사용자에게 재확인이 필요하다 — 아래 Assumptions Log·Open Questions 참고.

**탈락: Basic Roleplaying SRD (Chaosium).** 공식·저자 직속이라는 강점이 있었지만, **라이선스 원문 1(e)절이 "Pushing"(크툴루 유사 재굴림 메커닉)을 명시적으로 Prohibited Content로 지정**한다 — D-23이 요구하는 바로 그 기능을 이 라이선스 하에서 구현하면 라이선스 위반 소지가 생긴다. CC도 아니다. 이중으로 부적합.

## Architecture Patterns

### System Architecture Diagram

```
[ResolveCheck 명령] (session_actor)
        │
        ├─ command.rulebook_method 식별 ("2d6" | "d100" 등, 문자열 — 리터럴 아님)
        │
        ▼
   ┌─────────────────────────────────────┐
   │  session_actor._prepare_resolve_check │  ← 어떤 순수 함수를 부를지 "배선"만 담당
   └───────────────┬───────────────────────┘
                    │  분기
        ┌───────────┴────────────┐
        ▼                        ▼
  resolve_2d6(roller,       resolve_d100(roller,
   move, modifiers,          move, modifiers,
   target)                   skill, grade_bands)
  [rules_core, 기존]        [rules_core, 신규 — 2d6과 나란히 추가]
        │                        │
        └───────────┬────────────┘
                     ▼
            CheckOutcome
     {move, rolls, modifiers, target, grade: str}
       ← 두 판정 방식이 같은 모양을 돌려준다 (성공 조건 1)
                     │
                     ▼
        ModifierRecord 목록으로 변환 → CheckResolved 사건 생성
        {..., grade: str}  ← event_log/schema.py, Literal 폭 확장 필요
                     │
                     ▼
              EventStore.append (append-only)
                     │
                     ▼
        reducer.apply_event("check_resolved", payload)
     ⚠ grade == "miss" 하드코딩 지점 — 룰북마다 다른 "실패"
       등급 이름을 어떻게 셀지 재검토 필요 (아래 Pitfall 참고)
```

### Recommended Project Structure

```
src/gptrpg/
├── rules_core/
│   ├── dice.py            # 기존 Roller 프로토콜 유지 + 신규 PercentileRoller 프로토콜 추가(나란히, 수정 아님)
│   ├── grading.py          # Grade를 str로 넓힘. grade_for_total(2d6)은 그대로 유지
│   ├── grading_d100.py     # 신규 — d100 등급 계산(조건부 규칙: roll<=skill and 자릿수 일치 등)
│   ├── resolution.py        # 기존 resolve_2d6/reroll_2d6 유지, FLAT은 그대로
│   └── resolution_d100.py  # 신규 — resolve_d100/push_d100, 보너스/페널티 다이스·목표값 변경 처리
├── rulebooks/               # 신규 — 룰북이 선언하는 데이터(코드 아님, 상수/데이터클래스)
│   ├── dungeonworld_like.py # Phase 1이 암묵적으로 쓰던 2d6 등급 이름을 여기로 명시 이전(선택)
│   └── openquest.py         # OpenQuest 판정 종류·등급 4개·크리처 예시 2~3개(스코프 펜스 안에서 최소)
├── event_log/
│   └── schema.py            # Grade: Literal[...] → Grade: str (또는 조건부 확장 패턴, 아래 참고)
├── session_actor/
│   └── actor.py             # ResolveCheck에 판정 방식 식별 필드 추가, _prepare_resolve_check 분기
```

### Pattern 1: 등급을 "이름 목록"과 "수치 구간"을 모두 받는 하나의 필드로 표현하기

**What:** `Grade`를 고정 `Literal`에서 `str`로 넓힌다. 이름 목록형(2d6: "strong_hit"/"weak_hit"/"miss", OpenQuest: "critical"/"success"/"failure"/"fumble")과, 향후 다이스풀처럼 등급 자체가 수치인 경우("3 successes")를 문자열로 통일해서 담을 수 있다("3" 같은 문자열로 표현하거나, 별도 `grade_value: int | None` 필드를 미래에 추가). Phase 1의 `Modifier.type: str`이 이미 정확히 같은 패턴을 증명했다 — 새 유형을 코드 변경 없이 추가할 수 있는 자유도를 얻는 대가로, 오타를 정적 타입이 못 잡는다는 대가를 치른다(테스트로 보완).

**When to use:** `event_log/schema.py`의 `Grade` 리터럴, `rules_core/grading.py`의 `Grade` 별칭 양쪽.

**Example:**
```python
# rules_core/grading.py — 기존 (Literal 고정)
Grade = Literal["strong_hit", "weak_hit", "miss"]  # [VERIFIED: src/gptrpg/rules_core/grading.py:5]

# 권장 — 문자열로 넓히고, 2d6 쪽 세 이름은 "그 룰북이 실제로 쓰는 상수"로 격하
Grade = str
DUNGEONWORLD_STRONG_HIT = "strong_hit"
DUNGEONWORLD_WEAK_HIT = "weak_hit"
DUNGEONWORLD_MISS = "miss"
```

```python
# event_log/schema.py — 기존
Grade = Literal["strong_hit", "weak_hit", "miss"]  # [VERIFIED: src/gptrpg/event_log/schema.py:23]

class CheckResolved(EventEnvelope):
    ...
    grade: Grade  # [VERIFIED: src/gptrpg/event_log/schema.py:94]

# 권장
Grade = str  # 사건 스키마의 grade 필드가 어떤 룰북 등급 이름이든 받는다
```

**주의 — `EVENT_SCHEMA_VERSION` 판단이 필요하다.** `schema.py`의 docstring(`[VERIFIED: src/gptrpg/event_log/schema.py:6-10]`, D-12 규약)은 "사건 모양이 실제로 바뀌면 `EVENT_SCHEMA_VERSION`을 올리라"고 명시한다. `Literal`→`str`는 필드 이름·구조는 그대로지만 **검증 허용 범위**가 넓어진다. 이것이 "모양이 바뀐 것"인지는 플래너가 명시적으로 결정하고 `02-INTERFACE-CHANGES.md`에 이유를 적어야 한다 — 애매하게 넘기면 D-12 규약 위반 여지가 생긴다.

### Pattern 2: 수정치는 "언제 적용되는가"로 분류해야 한다 (계산 순서가 유형마다 다르다)

**What:** 2d6의 `_flat_total`(`[VERIFIED: src/gptrpg/rules_core/resolution.py:50-57]`)은 "굴림 후 합산"이라는 단일 패턴만 안다. 그러나 네 유형은 계산 파이프라인에서 **서로 다른 시점**에 적용된다:

| 유형 | 적용 시점 | d100에서 실제로 하는 일 |
|---|---|---|
| 숫자 가감(FLAT) | 굴림 **후**, 합계에 가산 | 2d6과 동일하게 재사용 가능 |
| 목표값 변경 | 굴림 **전**, 비교 기준값(target/skill)에 가산 — 굴림 결과 자체는 안 바뀜 | OpenQuest 난이도(+50%~-50%)가 정확히 이 패턴 |
| 주사위 추가·제거(보너스/페널티 다이스) | 굴림 **그 자체**를 바꾼다 — 몇 개를 굴려서 어느 쪽을 채택할지가 수정치의 효과 | Roller 호출 횟수 자체가 수정치에 의존 — `_flat_total` 패턴으로는 표현 불가능 |
| 재굴림(푸시) | 판정이 **끝난 후**, 새 판정을 이전 결과에 이어 붙인다 | `reroll_2d6`과 동일 패턴 재사용 |

**Why this matters:** `_flat_total`을 그대로 복사해서 "타입만 늘리면 되겠지"라고 접근하면 보너스 다이스와 목표값 변경을 못 만든다 — 이 둘은 "총합에 더할 숫자"가 아니라 "굴림 절차를 바꾸는 지시"이기 때문이다. `resolve_d100`은 반드시 **모디파이어 목록을 미리 훑어 굴림 전략(몇 개 굴릴지, 목표값을 얼마로 볼지)을 먼저 정한 다음** 굴리고, 그 다음에 FLAT 가산을 적용해야 한다.

**Example (권장 구조, 의사코드 — 검증되지 않은 설계 제안):**
```python
# rules_core/resolution_d100.py (신규 — 의사코드)
BONUS_DICE = "bonus_dice"      # value: 양수=보너스 개수, 음수=페널티 개수
TARGET_SHIFT = "target_shift"  # value: skill에 가산할 정수 (OpenQuest: +50/+20/-20/-50)
PUSH = "push"                  # 재굴림 마커 — push_d100이 별도로 처리, resolve_d100은 모름

def resolve_d100(roller, move, modifiers, skill):
    dice_delta = sum(m.value for m in modifiers if m.type == BONUS_DICE)
    target = skill + sum(m.value for m in modifiers if m.type == TARGET_SHIFT)
    target += sum(m.value for m in modifiers if m.type == "flat")  # 기존 FLAT 재사용
    extra = abs(dice_delta)
    tens_rolls = tuple(roller.roll_tens() for _ in range(1 + extra))
    units = roller.roll_units()
    chosen_tens = min(tens_rolls) if dice_delta > 0 else max(tens_rolls) if dice_delta < 0 else tens_rolls[0]
    roll = chosen_tens * 10 + units or 100
    grade = grade_for_d100(roll, target, tens=chosen_tens, units=units)
    return CheckOutcome(
        move=move, rolls=tens_rolls + (units,), modifiers=tuple(modifiers), total=roll, target=target, grade=grade,
    )
```

### Pattern 3: 등급 결정은 "숫자 구간"만이 아니라 "조건"일 수 있다

**What:** OpenQuest의 크리티컬/펌블은 단순 임계값 구간이 아니라 **두 자리 숫자가 같은지(더블)**라는 자릿수 패턴 조건이다(`[CITED: 검색 요약, openquestrpg.com/srd/skills/skill-rules/]` — "both dice show the same number"). 2d6의 `grade_for_total`은 스칼라 `total` 하나만 보고 등급을 정하지만, d100은 `roll`을 십의 자리/일의 자리로 분해해서 봐야 하는 경우가 있다. `CheckOutcome.rolls`가 이미 튜플이므로 분해된 자리값을 그대로 담을 수 있다 — **스키마 변경이 필요 없다.**

**When to use:** `grading_d100.py`의 등급 결정 함수를 설계할 때, "총합 하나"가 아니라 "굴림 원본(자릿수)"을 인자로 받도록 만든다.

**과잉 설계 경고:** D7(효과 DSL, 원자 연산 30~50개)과 "필드 단위 상세 규격"은 M1 범위다. Phase 2에서 등급 조건을 완전히 일반화된 "조건 표현 언어"로 만들 필요는 없다 — OpenQuest 하나, 2d6 하나, 각각의 등급 함수가 그 룰북에 맞는 조건을 직접 코드로 표현하면 충분하다. 플랫폼이 강제해야 하는 것은 오직 "`Grade`가 코드에 고정된 값 집합이 아니라는 것"이다.

### Pattern 4: 적/NPC 상태값 그릇 — D-20/D-21 그대로

**What:** D-20이 이미 모양을 확정했다: `{이름, 현재값, 최대값(선택), 바닥날 때 효과 참조}`, 목록(list)으로 무제한. `Modifier(type, value, source)`와 같은 "값 + 출처/의미" 패턴의 재사용이다(`[VERIFIED: src/gptrpg/rules_core/resolution.py:29-35]` — `Modifier` 정의 확인).

**Example (제안, 미검증 — Claude's Discretion 항목):**
```python
@dataclass(frozen=True)
class StatEntry:
    name: str                       # "Hit Points", "Sanity" 등 — 룰북이 뜻을 정한다
    current: int
    max: int | None = None
    depleted_effect_ref: str | None = None  # D7 효과 DSL의 실제 내용은 M1 — 지금은 참조 문자열만

@dataclass(frozen=True)
class Entity:
    entity_id: str      # 플랫폼이 정함
    display_name: str   # 플랫폼이 정함
    rulebook_id: str     # 플랫폼이 정함
    stats: tuple[StatEntry, ...]   # 무제한 목록 — D-21
```
OpenQuest 크리처(HP+MP 두 값)와 2d6 계열의 단일-HP 적이 같은 `Entity.stats` 튜플 길이만 다르게(1개 vs 2개) 넣을 수 있어야, D32의 검증 문구("특정 값이 바닥나면 무슨 일이 일어나는지는 룰북이 선언한다")를 코드로 직접 만족한다.

### Anti-Patterns to Avoid

- **`_flat_total`을 복사-붙여넣기해서 보너스 다이스를 "합산"으로 흉내내기:** 보너스 다이스는 총합에 더하는 숫자가 아니라 몇 개를 어떻게 굴리는지의 문제다(Pattern 2). 합산으로 흉내내면 "표현은 됐지만 실제 확률 분포가 틀린" 결과가 나와 D-24("전부 실제 동작까지 만든다")를 형식적으로만 만족하게 된다.
- **범용 룰 엔진/조건 DSL을 지금 설계하기:** D7·필드 단위 규격은 M1이다. Phase 2에서 필요한 건 "등급이 코드에 고정되지 않는다"는 증명이지, 완결된 룰 엔진이 아니다.
- **`reducer.py`의 `grade == "miss"` 패턴을 그대로 복사해 `grade == "failure"`(OpenQuest 이름) 하드코딩을 하나 더 추가하기:** 이러면 세 번째 룰북(M1의 d20)이 들어올 때 또 조건절이 늘어난다 — "룰북마다 실패 등급 이름이 다르다"는 문제 자체를 해결하지 못한다. 아래 Pitfall 1 참고.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| d100 확률 분포·주사위 통계 검증 | 손으로 짠 확률 계산 스크립트 | `hypothesis`의 property 기반 테스트(Phase 1이 `test_resolution_edges.py`에서 이미 증명한 패턴) | 경계값 220여 개를 손으로 나열하는 대신 불변식(예: "모든 total은 정확히 하나의 등급에 속한다")으로 표현하면 새 등급 규칙에도 그대로 재사용된다 |
| 룰북 등급·수정치 조건을 표현하는 범용 DSL | 자체 조건 파서/평가기 | 각 룰북 전용 순수 함수(`grade_for_total`, `grade_for_d100`) | D7 효과 DSL은 M1 몫. 지금 만들면 이 단계의 검증 목적(코드 무변경)과 무관한 설계 부채가 생긴다 |
| CC 라이선스 원문 파싱/자동 표기 생성기 | 라이선스 텍스트 자동 추출 도구 | 손으로 위 인용문을 그대로 복사해 `LICENSES.md`/README 같은 한 곳에 박아넣기 | LAW-04는 "문구와 게재 위치"를 법무가 정할 사안이라고 이미 명시했다 — 지금은 검증용으로 정확한 인용만 있으면 된다 |

**Key insight:** 이 도메인엔 가져다 쓸 "판정 방식 라이브러리"가 없다 — 그게 이 프로젝트가 검증하려는 것 자체다(룰북마다 판정 수학이 다르다는 것). 반대로, 룰북 **콘텐츠**(등급 이름, 크리처 스탯)는 절대 손으로 창작하지 않는다(D-18) — 이미 있는 CC 자료를 그대로 옮겨 쓴다.

## Common Pitfalls

### Pitfall 1: `reducer.py`의 `grade == "miss"` 하드코딩 — CONTEXT.md에 없는 새 발견

**What goes wrong:** `apply_event`가 `check_resolved` 사건을 접을 때 `miss_count=state.miss_count + (1 if grade == "miss" else 0)`으로 계산한다(`[VERIFIED: src/gptrpg/rules_core/reducer.py:66]`, 함께 `last_grade: Grade | None`도 `grading.py`의 `Grade`를 그대로 import한다 — `[VERIFIED: src/gptrpg/rules_core/reducer.py:11,28]`). OpenQuest 등급 이름은 "failure"/"fumble"이지 "miss"가 아니다. 이 상태로 d100 판정을 흘려보내면 **`miss_count`가 조용히 0으로 고정된다** — 예외도, 경고도 없다.

**Why it happens:** Phase 1은 2d6 하나만 있었으므로 "실패"를 "miss"라는 정확한 문자열로 판단해도 틀릴 일이 없었다. 이건 자연스러운 단일 룰북 시절의 지름길이었다.

**How to avoid:** `check_resolved` 페이로드나 룰북 선언에 "이 등급이 실패로 집계되는가"를 나타내는 명시적 신호가 있어야 한다. 가장 단순한 선택지: 룰북이 등급마다 `counts_as_failure: bool`을 선언하게 하고, 사건 페이로드에 이미 있는 `grade` 문자열이 아니라 그 신호를 reducer가 읽게 한다. 이 지점은 `tests/conftest.py`의 `fake_session_log` 픽스처(`failure_count=2` — `[VERIFIED: tests/conftest.py:205,234]`, `_make_fake_events`가 `grade="miss"`를 두 번 씀 — `[VERIFIED: tests/conftest.py:109,176]`)와 Phase 6/MEAS-03("실패는 많은데 시계가 안 돈다")이 직접 의존하는 계산이므로, Phase 2에서 고치지 않으면 Phase 4·6에서 조용히 잘못된 숫자가 쌓인다.

**Warning signs:** d100 판정 사건을 넣은 뒤 `replay`로 재구성한 상태의 `miss_count`가 실제 "실패" 판정 개수와 안 맞는다.

### Pitfall 2: `session_actor`가 `resolve_2d6`을 하드 배선하고 있다

**What goes wrong:** `_prepare_resolve_check`가 `resolve_2d6(self._roller, command.move, command.modifiers, command.target)`을 무조건 호출한다(`[VERIFIED: src/gptrpg/session_actor/actor.py:242]`). `ResolveCheck` 명령 자체에도 "어떤 판정 방식을 쓸지" 나타내는 필드가 없다(`[VERIFIED: src/gptrpg/session_actor/actor.py:55-61]` — `move`/`modifiers`/`target`/`caused_by_seq`뿐).

**Why it happens:** Phase 1은 판정 방식이 하나뿐이었으므로 분기가 필요 없었다.

**How to avoid:** `ResolveCheck`에 판정 방식 식별 필드(문자열 — 리터럴로 고정하면 D32 위반)를 추가하고, `_prepare_resolve_check`가 그 값으로 `resolve_2d6`/`resolve_d100` 중 부를 함수를 고른다. `session_actor`는 `rules_core`와 달리 `.importlinter` forbidden 계약 대상이 아니므로 이런 배선 책임을 가져도 계층 원칙을 어기지 않는다 — 다만 세 번째 판정 방식(M1의 d20)이 들어올 때 이 분기가 또 늘어난다는 한계는 정직하게 `02-INTERFACE-CHANGES.md`에 적어야 한다("참았다"가 아니라 "제한적으로 고쳤다"에 해당하는 사례).

**Warning signs:** d100 판정을 요청했는데 `resolve_2d6`이 실행돼 `TypeError`(인자 개수 불일치)나 엉뚱한 결과가 나온다.

### Pitfall 3: `dice.py`의 `Roller` 프로토콜이 d100에 그대로 안 맞는다

**What goes wrong:** 현재 `Roller` 프로토콜은 `roll_d6() -> int` 하나뿐이다(`[VERIFIED: src/gptrpg/rules_core/dice.py:6-15]`). d100은 최소 "1~100 하나" 또는 "십의 자리/일의 자리 따로"를 굴려야 하고, 보너스 다이스는 십의 자리를 여러 번 굴려야 한다 — 기존 프로토콜로는 표현이 안 된다.

**Why it happens:** Phase 1이 2d6 전용으로 최소하게 설계했다.

**How to avoid:** 기존 `Roller`를 **수정하지 않고**, 구조적 타이핑(PEP 544)의 장점을 살려 **새 프로토콜을 나란히 추가**한다(예: `PercentileRoller`에 `roll_tens() -> int`, `roll_units() -> int`). 실제 굴림 구현체(`LiveRoller` 등)가 두 프로토콜을 동시에 만족하도록 메서드를 추가하면 되고, 기존 2d6 경로는 전혀 안 건드린다. 이건 "확장이지 변경이 아니다"의 좋은 예시로 `02-INTERFACE-CHANGES.md`의 "참은 곳" 항목 후보다 — 다만 `LiveRoller`/`ReplayRoller` 구현체 자체에는 새 메서드를 "추가"해야 하므로 완전한 무변경은 아니다. 정직하게 "확장"으로 기록한다.

**Warning signs:** d100 판정 코드가 `AttributeError: 'LiveRoller' object has no attribute 'roll_tens'`를 던진다.

### Pitfall 4: `EVENT_SCHEMA_VERSION`을 올릴지 말지 애매하게 넘기기

**What goes wrong:** `Grade`를 `Literal`에서 `str`로 넓히는 것이 "사건 모양이 실제로 바뀐 것"인지 판단하지 않고 넘어가면, D-12 규약(`[VERIFIED: src/gptrpg/event_log/schema.py:6-10]`)이 정한 "재생 경로에 옛 판을 해석하는 통로를 추가하라"는 절차를 건너뛰게 된다.

**Why it happens:** 필드 이름과 JSON 구조 자체는 안 바뀌므로 "그냥 검증 완화"로 착각하기 쉽다.

**How to avoid:** 플래너가 이 질문에 명시적으로 답하고 `02-INTERFACE-CHANGES.md`에 이유를 남긴다. 실용적 절충안: 스키마 버전은 그대로 두되(과거 기록은 여전히 유효한 `Grade` 값만 담고 있으므로 하위 호환), **PR/커밋 메시지와 인터페이스 문서에 "검증 범위 확대"를 명시적으로 기록**하는 것으로 D-12의 정신(과거 기록이 여전히 해석 가능함을 보장)을 지킨다.

### Pitfall 5: OpenQuest SRD 본문과 그 외 저작물(메인 룰북)을 혼동하기

**What goes wrong:** OpenQuest 공식 안내(`[CITED: openquestrpg.com/about/]`)는 "SRD에 있는 텍스트만 쓸 수 있고, 메인 룰북(및 부록)의 나머지는 전부 저작권 콘텐츠라 못 쓴다"고 명시한다. 검색 결과 중 일부(예: 몬스터 전체 목록)는 SRD 페이지가 아니라 메인 룰북 내용을 인용한 3차 문서일 수 있다.

**How to avoid:** 실제 데이터를 작성할 때는 `openquestrpg.com/srd/` 경로 아래 페이지만 원본으로 삼는다. 위에서 인용한 크리처 스탯 구조(HP/MP)는 SRD의 `creature-format` 페이지에서 나온 것으로 확인됐다(`[CITED]`) — 실제 예시 크리처 1~2종을 뽑을 때도 반드시 `openquestrpg.com/srd/creatures/*` 페이지 원문을 직접 열어 옮겨야 한다(이번 조사는 검색 스니펫으로 구조만 확인했고, 개별 크리처 수치는 확인하지 않았다).

## Code Examples

### 2d6 재굴림 패턴 (그대로 재사용할 골격) — 이미 검증된 코드

```python
# Source: src/gptrpg/rules_core/resolution.py:80-98 [VERIFIED — 직접 읽음]
def reroll_2d6(roller: Roller, previous: CheckOutcome) -> CheckOutcome:
    """앞선 판정 결과에 재굴림을 이어 붙인다.

    앞선 눈을 지우지 않는다 — 굴림 도구를 두 번 더 불러 새 눈 두 개를 얻고,
    `rolls`는 앞선 눈 뒤에 새 눈을 이어 붙인 것으로 만든다. `total`과
    `grade`는 새로 굴린 두 눈만으로 다시 계산한다. `modifiers`와 `target`은
    앞선 판정의 것을 그대로 물려받는다.
    """
    new_rolls = (roller.roll_d6(), roller.roll_d6())
    total = sum(new_rolls) + _flat_total(previous.modifiers)
    grade = grade_for_total(total, previous.target)
    return CheckOutcome(
        move=previous.move,
        rolls=previous.rolls + new_rolls,
        modifiers=previous.modifiers,
        total=total,
        target=previous.target,
        grade=grade,
    )
```

D-23이 요구하는 `push_d100`은 이 함수의 "새 눈 두 개" 자리를 "새 백분위 굴림 하나(또는 십/일 자리 둘)"로 바꾸기만 하면 같은 구조를 그대로 물려받는다 — "앞선 눈을 지우지 않는다"는 핵심 불변식이 동일하게 성립해야 한다.

### 보너스/페널티 다이스의 일반적 d100 관행 (인용 — 특정 룰북 저작물 아님)

```
For each bonus die, you roll an additional "tens" percentage die and use the
"tens" die that yields the better (lower) result. A penalty die works exactly
the same way, but rather than keeping the better of the two "tens" values,
the player keeps the worse.
```
`[CITED: call-of-cthulhu-nachtstadt-berlin.fandom.com/wiki/Bonus_Dice_and_Penalty_Dice]` — 크툴루 계열 팬 위키의 관행 설명. 특정 룰북의 저작물이 아니라 장르 공통 규칙 서술이므로 CC 콘텐츠 인용 의무와는 무관하지만, 플랫폼 코드 주석에 "이 계산 규칙의 출처"로 남겨두는 것을 권장한다.

## State of the Art

이 도메인(TRPG 판정 엔진)은 "최신 트렌드"가 있는 영역이 아니라, 각 룰북이 수십 년간 고정해 온 계산 규칙을 정확히 재현하는 것이 전부다. "낡은 방식 vs 새 방식"이라는 축이 성립하지 않는다 — 생략.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | OpenQuest SRD가 보너스/페널티 다이스, 푸시 롤 메커닉을 원문에 포함하지 않는다는 판단은 검색 스니펫 기반이며 SRD 전체 목차를 페이지 단위로 완독하지 않았다 | "d100 CC 라이선스 콘텐츠 후보" | 실제로는 있는데 못 찾았다면, 두 메커닉을 "플랫폼 범용 기능 + 자체 예시 데이터"로 구현하기로 한 설계 결정이 불필요하게 보수적이었던 것 — 재작업 비용은 낮음(이미 CC 콘텐츠로 대체 가능하면 더 좋은 방향으로만 바뀜) |
| A2 | Open Cthulhu HPLed SRD의 정확한 등급 수(5개 vs 6개)와 원문에서의 정확한 push-roll 절차 서술은 공식 SRD PDF를 직접 읽지 않고 검색 요약으로만 확인했다 | "d100 CC 라이선스 콘텐츠 후보" 표 | Fallback 후보로만 제시했으므로, 실제 채택 시 반드시 PDF 원문(`i.4pcdn.org/tg/1575207690054.pdf` 등)을 직접 읽고 재검증해야 한다 |
| A3 | `EVENT_SCHEMA_VERSION`을 올려야 하는지에 대한 판단(Pitfall 4)은 D-12 규약 문구의 해석이며, 확정된 정책이 아니다 | Pattern 1, Pitfall 4 | 플래너가 실용적 절충안 대신 "버전을 올려야 한다"는 엄격한 해석을 택하면 재생 경로에 구버전 해석 로직을 추가하는 작업이 이 단계 범위에 새로 들어온다 |
| A4 | `ResolveCheck`에 판정 방식 식별 필드를 추가하고 `session_actor`가 문자열 분기하는 설계(Pitfall 2)는 이 조사의 제안이며 검증된 코드가 아니다 | Pattern 1 다이어그램, Pitfall 2 | 플래너가 다른 배선 방식(예: 룰북 레지스트리 객체를 세션 생성 시 주입)을 택할 수 있다 — 제안은 여러 방식 중 하나일 뿐 |
| A5 | 보너스/페널티 다이스 계산 규칙(십의 자리 다이스 추가, 유리한 쪽 채택)이 "장르 공통 관행이라 특정 룰북 저작물이 아니다"라는 판단은 법률 자문이 아니라 이 조사의 상식적 추론이다 | Code Examples, "Don't Hand-Roll" | LAW-04(CC-BY 고지 문구·게재 위치)가 법무 영역으로 명시돼 있으므로, 실제 게임 메커닉 서술의 저작권 경계는 법무 검토 없이 최종 확정하면 안 된다 |

## Open Questions

1. **D-18의 "CC 라이선스"를 얼마나 엄격하게 해석할 것인가?**
   - What we know: OpenQuest SRD는 순수 CC BY 4.0이라 논쟁의 여지가 없다. Open Cthulhu는 OGL 1.0a라 D-18 문구를 엄밀히 지키면 탈락이지만, 푸시 롤·보너스 다이스가 원문에 실제로 있어 D-23 검증 의미가 더 크다.
   - What's unclear: 사용자가 "CC 라이선스"를 "Creative Commons 라이선스"로 엄밀하게 의도했는지, 아니면 "누구나 자유롭게 쓸 수 있는 오픈 라이선스 일반"을 편하게 줄여 말한 것인지가 CONTEXT.md 원문만으로는 확정되지 않는다.
   - Recommendation: 1순위 OpenQuest로 진행하고, 계획 단계나 `/gsd-discuss-phase`에서 이 해석을 한 번 더 확인한다. OpenQuest만으로 성공 조건 1~5는 전부 만족 가능하므로(보너스 다이스·푸시 롤은 플랫폼 범용 기능으로 별도 처리), 이 질문이 이 단계를 막지는 않는다.

2. **`ResolveCheck`이 판정 방식을 어떻게 식별해야 하는가?**
   - What we know: 현재는 함수(`resolve_2d6`) 하나만 하드 배선돼 있다(Pitfall 2). 문자열 식별자를 명령에 추가하는 안을 제안했다.
   - What's unclear: 이 식별자가 "판정 방식"(2d6/d100)을 가리켜야 하는지, "룰북 ID"(OpenQuest/dungeonworld_like)를 가리켜야 하는지 — 같은 판정 방식을 여러 룰북이 공유할 수 있으므로 개념이 다르다.
   - Recommendation: 플래너가 두 개념을 분리해서 설계하도록 명시 — "판정 방식"은 `rules_core`가 어떤 순수 함수를 쓸지 결정하고, "룰북 ID"는 등급 이름·수정치 목록 등 선언 데이터를 어디서 가져올지 결정한다.

3. **OpenQuest SRD의 실제 몬스터 스탯 수치를 아직 직접 확인하지 않았다.**
   - What we know: 스탯 구조(HP+MP)는 확인했다.
   - What's unclear: 구체적인 크리처 1~2종의 정확한 수치·능력치는 이번 조사에서 원문을 열람하지 않았다.
   - Recommendation: 계획 단계에서 `openquestrpg.com/srd/creatures/*` 페이지를 직접 열어 실제 예시 1~2종을 확정한다(스코프 펜스가 요구하는 최소량).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | 전체 | ✓ | ≥3.11 (`[VERIFIED: pyproject.toml:9]`) | — |
| uv (패키지/실행 관리) | 테스트·린트 실행 | ✓ (Phase 1 `01-VERIFICATION.md`에서 `uv run pytest`/`uv run lint-imports`/`uv run ruff check .` 라이브 실행 확인 — `[VERIFIED: .planning/phases/01-rules-core-and-event-log/01-VERIFICATION.md]`) | — | — |
| pytest / hypothesis / import-linter / ruff | 테스트·경계 검사 | ✓ (Phase 1이 이미 106~142개 테스트로 사용 중) | `pyproject.toml` dev 그룹에 고정 | — |
| 인터넷 접근(SRD 원문 열람) | OpenQuest 실제 크리처 수치 확정 | 이번 조사 세션에서 가능함을 확인(WebFetch로 openquestrpg.com 열람 성공) | — | 오프라인 환경이면 SRD PDF를 미리 내려받아 두어야 함 |

**Missing dependencies with no fallback:** 없음.
**Missing dependencies with fallback:** 없음 — 이 단계는 신규 외부 의존성이 없다.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥9.1.1 + hypothesis ≥6.164.0 (`[VERIFIED: pyproject.toml]`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]` (`[VERIFIED: pyproject.toml:30-32]`) |
| Quick run command | `uv run pytest -q` |
| Full suite command | `uv run pytest && uv run lint-imports && uv run ruff check .` (Phase 1이 확립한 3종 게이트 — `[VERIFIED: 01-VERIFICATION.md]`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RIG-08a | d100 판정이 2d6과 같은 `CheckOutcome`/`CheckResolved` 모양으로 돈다 | unit | `uv run pytest tests/test_resolution_d100.py -x` | ❌ Wave 0 |
| RIG-08b | 등급 집합이 코드에 고정 안 됨 — d100 4등급이 `Literal` 없이 통과한다 | unit | `uv run pytest tests/test_grading_d100.py -x` | ❌ Wave 0 |
| RIG-08c | 수정치 4유형(FLAT/보너스다이스/목표값변경/푸시)이 전부 계산 결과에 반영된다 | unit + hypothesis | `uv run pytest tests/test_resolution_d100.py -k modifier -x` | ❌ Wave 0 |
| RIG-08d | OpenQuest 적(HP+MP)과 2d6 계열 적(HP 1개)이 같은 `Entity`/`StatEntry` 그릇에 들어간다 | unit | `uv run pytest tests/test_entities.py -x` | ❌ Wave 0 |
| HYP-03 | 두 번째 룰북을 넣으며 실제로 고친 곳/참은 곳이 `02-INTERFACE-CHANGES.md`에 기록된다 | manual-only (문서 검토) | — (사람이 문서를 읽고 판단) | ❌ Wave 0 — 문서 자체가 산출물 |
| (회귀) | 기존 2d6 판정·사건 재생·경계 계약이 전부 그대로 통과한다 | regression | `uv run pytest` (전체) | ✓ 이미 존재 (106+ 테스트) |

### Sampling Rate

- **Per task commit:** `uv run pytest -q` (해당 모듈만이라도)
- **Per wave merge:** `uv run pytest && uv run lint-imports && uv run ruff check .`
- **Phase gate:** 위 전체 명령이 초록이어야 `/gsd-verify-work` 진입

### Wave 0 Gaps

- [ ] `tests/test_resolution_d100.py` — RIG-08a·RIG-08c 커버
- [ ] `tests/test_grading_d100.py` — RIG-08b 커버, `hypothesis`로 등급 구간이 연속·배타적인지 증명(Phase 1의 `test_edge_adjacency_*` 패턴 재사용)
- [ ] `tests/test_entities.py` — RIG-08d 커버, D-20/D-21 `Entity`/`StatEntry` 신규 모듈
- [ ] `02-INTERFACE-CHANGES.md` — HYP-03의 산출물(테스트가 아니라 문서 자체가 검증 대상)
- [ ] Percentile roller 테스트용 스크립트 도구(`ScriptedRoller` 확장) — `tests/test_resolution_edges.py`가 이미 쓰는 인라인 구조적 타이핑 패턴을 d100용 tens/units 버전으로 재사용

## Security Domain

> `security_enforcement` 키가 `.planning/config.json`에 없음 — 기본값(활성)으로 처리.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 이 단계는 인증 표면을 추가하지 않는다(로컬 CLI/순수 함수) |
| V3 Session Management | no | 세션 액터 동시성 계약은 Phase 1이 이미 처리, 이번 단계는 건드리지 않는다 |
| V4 Access Control | no | 해당 없음 |
| V5 Input Validation | **yes** | 룰북 데이터(등급 집합, 수정치 목록, `StatEntry`)는 pydantic 모델 또는 이에 준하는 엄격한 dataclass 검증을 거쳐야 한다 — `event_log/schema.py`가 이미 쓰는 `extra="forbid", frozen=True` 패턴(`[VERIFIED: src/gptrpg/event_log/schema.py:42]`)을 새 모델에도 동일 적용 권장 |
| V6 Cryptography | no | 해당 없음 |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 잘못된/조작된 룰북 데이터가 판정 계산을 조용히 왜곡(예: 음수 HP 최대값, 존재하지 않는 등급 이름 참조) | Tampering | `UnsupportedModifier`가 이미 확립한 "모르면 예외로 실패"(silent skip 금지) 원칙을 새 검증 지점에도 동일하게 적용. `UnknownEventType`도 같은 철학(`[VERIFIED: src/gptrpg/rules_core/reducer.py:36-46]`) |
| `grade` 문자열 자유화로 인해 오타난 등급 이름이 조용히 통과 | Tampering / Repudiation | 룰북이 선언한 등급 집합과 실제 계산이 반환한 `grade` 값을 비교하는 방어적 검증(assert 또는 예외)을 `resolve_*` 함수 반환 직전에 추가 권장 |

## Sources

### Primary (HIGH confidence)
- `src/gptrpg/rules_core/resolution.py`, `grading.py`, `dice.py`, `reducer.py`, `event_log/schema.py`, `session_actor/actor.py`, `tests/conftest.py`, `pyproject.toml`, `.importlinter` — 전부 이번 세션에서 직접 `Read`로 읽고 정확한 줄 번호로 인용
- [OpenQuest SRD Licensing](https://openquestrpg.com/srd/licensing/) — CC BY 4.0 라이선스 원문·첨부 문구 확인 (WebFetch로 직접 열람)
- [BRP SRD V1.0 PDF](https://www.chaosium.com/content/FreePDFs/BRP/BRP%20SRD%20-%20V1.0.pdf) — 라이선스 조항(Prohibited Content로서의 "Pushing") 직접 PDF 페이지 열람으로 확인
- `.planning/phases/01-rules-core-and-event-log/01-VERIFICATION.md`, `01-04-SUMMARY.md` — Phase 1 산출물, 직접 읽음
- `docs/GPTRPG-M0-decisions.md` §D27, §D32 — 직접 읽음
- `docs/GPTRPG-design-plan.md` §4.1–4.9 — 직접 읽음

### Secondary (MEDIUM confidence)
- [OpenQuest Difficulty](https://openquestrpg.com/srd/skills/difficulty/), [OpenQuest Skill Rules](https://openquestrpg.com/srd/skills/skill-rules/) — WebFetch 요약(원문 열람이지만 AI 요약을 거침)
- WebSearch 결과 기반: OpenQuest 크리처 스탯 구조(HP+MP), Basic Roleplaying 등급 체계(5단계), Open Cthulhu HPLed SRD 라이선스(OGL 1.0a)·구성 출처 비율

### Tertiary (LOW confidence)
- Call of Cthulhu Nachtstadt Berlin 팬 위키(Fandom)의 보너스/페널티 다이스 서술 — 커뮤니티 2차 자료, 게임 메커닉 관행 확인용으로만 사용
- Open Cthulhu HPLed SRD의 정확한 등급 수·push roll 원문 절차 — 검색 요약만, PDF 원문 미열람(A2 참고)

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — 신규 의존성이 없고 기존 `pyproject.toml`을 직접 확인
- 코드 통합 지점(Architecture Patterns, Common Pitfalls): HIGH — 5개 지점 모두 실제 소스 파일을 직접 읽고 정확한 줄 번호로 인용
- CC 라이선스 후보 비교: MEDIUM — 1순위(OpenQuest)는 공식 페이지 직접 열람으로 HIGH급이나, fallback 후보(Open Cthulhu, BRP)는 검색 요약 의존 비중이 높음
- d100 등급/수정치 구체 설계(Pattern 2, 3): MEDIUM — 아키텍처 원리는 확실하나 구체 함수 시그니처는 이 조사의 제안(Assumptions Log A4 참고)이지 검증된 코드가 아님

**Research date:** 2026-08-01
**Valid until:** 2026-08-31 (OpenQuest SRD 콘텐츠·라이선스는 안정적이나, 실제 크리처 수치는 계획 단계에서 원문 재확인 필요 — Open Question 3)

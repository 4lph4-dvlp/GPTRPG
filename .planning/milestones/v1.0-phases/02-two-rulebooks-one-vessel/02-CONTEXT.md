# Phase 2: 룰북 두 개를 같은 그릇에 - Context

**Gathered:** 2026-08-01
**Status:** Ready for planning

<domain>
## Phase Boundary

판정 방식이 서로 다른 룰북 두 개(2d6 등급식 / d100 롤언더)와 그 룰북들의 적이, 플랫폼 코드를 고치지 않고 데이터로만 들어가는지를 검증한다. 여섯 가설 중 유일하게 플레이 없이 데이터 작성만으로 확인되는 가설(HYP-03)이 이 단계의 답이다.

**이 단계가 만드는 것:** d100 롤언더 판정 방식(순수 함수, Phase 1의 2d6과 같은 인터페이스) + 룰북이 자기 등급 집합을 선언하는 구조 + 수정치 네 유형(숫자 가감·주사위 추가/제거·목표값 변경·재굴림) 전부의 실제 동작 + 적/NPC 상태값을 담는 공용 그릇 + "플랫폼 코드를 고쳤는지" 기록 문서.

**이 단계가 만들지 않는 것:** 룰북 데이터의 필드 단위 상세 규격, 효과 원자 연산의 최종 목록, 세 번째 이후 판정 방식, 화면·서버, 룰북 파일 업로드/파싱 기능.

**이 단계의 유일한 숙제(로드맵 원문):** 두 번째 룰북을 넣으면서 플랫폼 코드를 고쳐야 했는지 아닌지가 명확히 기록되는 것.

</domain>

<decisions>
## Implementation Decisions

### d100 롤언더 검증용 룰북

- **D-18:** d100 콘텐츠는 **CC 라이선스가 있는 실제 룰북 자료를 찾아 쓴다.** 자체 창작 미니 룰북은 쓰지 않는다.
  - *이유:* 자체 창작은 검증 목적(판정 수학이 다른 두 룰북이 같은 그릇에 도는가)과 무관한 번역·정리 작업이 늘어난다. 실제 CC 라이선스 콘텐츠를 쓰면 라이선스 표기 관행(LAW-04)까지 자연스럽게 검증된다.

- **D-19:** 구체적인 CC 라이선스 후보(OpenQuest, Basic Roleplaying SRD 등) 탐색은 **이 논의 단계가 아니라 `/gsd-plan-phase 2`의 리서치 단계(gsd-phase-researcher)로 넘긴다.**
  - *이유:* 결정 포착(discuss)과 구현 조사(research)의 역할을 섞지 않는다. discuss는 "실제 자료를 찾아 쓴다"는 방향만 정하고, 후보 비교와 최종 선정은 조사 단계의 몫이다.

### 적/NPC 상태값의 최소 모양

- **D-20:** 적/NPC 상태값 하나의 모양은 **{이름, 현재값, 최대값(선택), 바닥날 때 효과 참조}** 로 둔다. Phase 1의 `Modifier`(type/value/source)와 같은 "값 + 출처/의미" 패턴을 재사용한다.
  - *이유:* D32 원문("특정 값이 바닥나면 무슨 일이 일어나는지는 룰북이 선언한다")을 코드 구조로 직접 만족시킨다. 효과 참조의 실제 연산 내용은 D7(효과 DSL)이고 M0 범위 밖이므로, 지금은 참조 자리만 연다.

- **D-21:** 적/NPC 하나가 가질 수 있는 상태값 개수는 **제한 없음 — 목록(list)으로 둔다.**
  - *이유:* 던전월드 계열 적(체력 하나)과 크툴루 계열 적(체력+San 등 여러 개)이 코드 수정 없이 같은 그릇에 들어가야 한다. 개수를 코드가 제한하면 D32의 "그릇은 플랫폼, 내용은 룰북"이 깨진다.

### "플랫폼 코드를 고쳤는지" 기록 방식

- **D-22:** 성공 조건 5번(플랫폼 코드를 고쳤는지 명확히 기록)은 **별도 문서로 남긴다.** SUMMARY.md들에 흩어 놓지 않는다.
  - *이유:* "명확히 기록된다"는 문구가 사람이 직접 읽고 판단할 수 있는 단일한 장소를 요구한다. git log를 훑어야 확인되는 것은 "추론"이지 "기록"이 아니다.
  - *산출물:* Phase 2 종료 시 `02-INTERFACE-CHANGES.md`(가칭, 계획 단계에서 최종 파일명 확정) 문서를 만든다. **고친 곳**(파일·이유)과 **고치지 않고 데이터로 버틴 곳**을 둘 다 담는다 — "고치고 싶었지만 참았다"가 추상화가 옳다는 가장 강력한 증거이므로 뒷쪽이 더 중요하다. 예: "수정치 유형을 rules_core에 박을까 고민했지만, 데이터의 type 칸으로 해결했다" 같은 사례가 여기에 쓰인다.

### 재굴림(푸시 롤)과 나머지 세 수정치 유형

- **D-23:** 크툴루 d100 푸시 롤(재굴림)은 **실제 동작까지 구현한다.** Phase 1의 `reroll_2d6`과 같은 패턴 — 앞선 눈을 지우지 않고 이어 붙인다.
  - *이유:* 성공 조건 3번은 "수정치 네 유형이 표현된다"이지 "동작한다"가 아니지만, Phase 1이 이미 2d6 쪽에서 재굴림을 실물로 증명한 패턴을 갖고 있어 새로 배우는 비용이 작다. 재굴림은 크툴루의 정체성이라 자리만 있고 안 도는 것은 검증으로서 약하다.

- **D-24:** 나머지 세 수정치 유형(숫자 가감·주사위 추가/제거·목표값 변경)도 **전부 실제 동작까지 만든다.** 자리만 열어두지 않는다.
  - *이유:* 네 유형 전부가 같은 감지(판정 요청 → 판정 결과)에서 돈다는 것이 "추상화가 옳다"는 가장 강력한 증거다. 숫자 가감(FLAT)은 Phase 1에 이미 있으므로 이 결정은 나머지 셋(주사위 추가/제거, 목표값 변경)을 실제 계산에 반영하는 작업이다.

### Claude's Discretion

계획·조사 단계에서 판단하되, 위 결정을 뒤집지 않는 선에서:

- CC 라이선스 d100 콘텐츠의 구체적 후보 — `/gsd-plan-phase 2`의 리서치 단계가 정한다 (D-19)
- `02-INTERFACE-CHANGES.md`의 정확한 파일명과 형식
- 등급 집합을 룰북이 선언하는 구체적 데이터 형식(이름 목록 vs 수치 구간을 어떻게 같은 필드에 담을지)
- 주사위 추가/제거(보너스 다이스) 수정치의 정확한 계산 규칙 — d100 방식에서 "추가 주사위 굴려 더 유리한 쪽 선택" 같은 세부
- 목표값 변경 수정치가 판정 결과 객체(`CheckOutcome`류)의 `target` 필드와 상호작용하는 방식

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 단일 권위 문서
- `docs/GPTRPG-M0-decisions.md` §D27 (룰북 파일 목차 + 판정 엔진 형태, 2개 방식 비교 검증 표) — 이 단계에 직접 걸리는 결정. 결과 등급을 코드에 고정하지 않는다는 발견 1, 수정치도 유형 목록이 필요하다는 발견 2, 두 방식이 같은 인터페이스에 들어간다는 발견 3
- `docs/GPTRPG-M0-decisions.md` §D32 (적과 NPC의 숫자는 룰북이 선언한다) — 플랫폼이 정하는 것(그릇)과 룰북 데이터가 선언하는 것(내용)의 표, 금지 사항("체력·피해·태그처럼 룰북 고유의 개념을 플랫폼 코드에 넣지 않는다")
- `.planning/intel/decisions.md` — D1~D33을 항목별로 정리한 것. 원문보다 읽기 쉽다

### 판정 인터페이스
- `docs/GPTRPG-design-plan.md` §4.3 (판정 방식 로드맵) — 2d6/d100/d20 등 6종 표, M0에 2개를 넣는 이유
- `docs/GPTRPG-design-plan.md` §4.4 (판정 인터페이스) — 판정 요청/판정 결과의 공통 형태, 결과 등급을 코드에 고정하지 않는 원칙, 수정치 유형 4가지 표
- `docs/GPTRPG-design-plan.md` §4.6 (자동화율) — 룰북별 예상 자동화율(던전월드 95%+, 크툴루 90%, D&D 5e 70~85%)

### 프로젝트 수준
- `.planning/PROJECT.md` — Constraints 절(아키텍처 불변 규칙 3개, LLM 경계), Key Decisions 표(특히 D5·D6·D7·D27·D32)
- `.planning/REQUIREMENTS.md` — RIG-08·HYP-03이 이 단계의 요구사항
- `.planning/ROADMAP.md` Phase 2 절 — 성공 조건 5개와 범위선("룰북 데이터의 필드 단위 상세 규격과 효과 원자 연산의 최종 목록은 M0이 아니다")

### Phase 1 산출물 (이 단계가 직접 확장하는 것)
- `.planning/phases/01-rules-core-and-event-log/01-04-SUMMARY.md` — 2d6 판정 완성 내역(FLAT 수정치, reroll_2d6 패턴, UnsupportedModifier)
- `.planning/phases/01-rules-core-and-event-log/01-06-SUMMARY.md` — 세션 액터·CLI 최종 형태
- `.planning/phases/01-rules-core-and-event-log/01-VERIFICATION.md` — Phase 1이 실제로 증명한 것(사건 기록에서 상태 재구성, AI 미개입 판정 경로 등)

### 읽으면 안 되는 것
- `docs/GPTRPG-design-plan-v1-archive.md` — **폐기된 v1 기획서.** 파일 안에 폐기 표기가 없어 열면 유효한 명세처럼 보인다

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/gptrpg/rules_core/dice.py` — `Roller` Protocol (구조적 타이핑, PEP 544). d100 굴림 도구도 이 프로토콜만 만족하면 재생 가능
- `src/gptrpg/rules_core/grading.py` — `Grade` 리터럴 + `grade_for_total` 패턴. d100의 최대 6개 등급은 이 함수 시그니처를 그대로 복제하되 등급 이름·경계는 다르게 가져간다
- `src/gptrpg/rules_core/resolution.py` — `Modifier`(type/value/source), `CheckOutcome`(rolls/modifiers/total/target/grade), `UnsupportedModifier` 예외, `resolve_2d6`/`reroll_2d6` 쌍. d100 쪽 판정 함수가 이 모양을 그대로 따라야 성공 조건 1번("같은 판정 요청·판정 결과 형태 위에서 돈다")이 성립한다
- `src/gptrpg/rules_core/reducer.py` — `apply_event`가 `UnknownEventType`으로 실패하는 패턴(조용한 무시 금지). 새 사건 종류나 필드가 필요해지면 같은 원칙 적용

### Established Patterns
- Phase 1이 세운 3계층 경계(`rules_core` / `event_log` / `session_actor`)와 `.importlinter` 자동 검사가 이 단계에도 그대로 적용된다. d100 관련 코드도 `rules_core` 폴더 안에서는 시각·무작위·파일·네트워크를 못 건드린다
- "값 + 출처" 패턴(`Modifier.type/value/source`)이 D-20의 적/NPC 상태값 모양의 직접 근거

### Integration Points
- `src/gptrpg/event_log/schema.py`의 `CheckResolved` 이벤트가 `grade: Grade`(현재 `Literal["strong_hit", "weak_hit", "miss"]`)를 고정 리터럴로 선언하고 있다 — d100의 최대 6개 등급을 넣으려면 이 필드 타입을 룰북이 선언하는 문자열로 넓혀야 할 가능성이 높다. **바로 이 지점이 성공 조건 5번(플랫폼 코드를 고쳤는지)의 첫 번째 실제 시험대**
- `src/gptrpg/rules_core/resolution.py`의 `Modifier.type`은 이미 문자열이라 새 유형(주사위 추가/제거·목표값 변경·재굴림)을 코드 변경 없이 추가할 수 있는 구조다 — 다만 `_flat_total`이 `FLAT` 하나만 처리하므로, 새 유형을 처리하는 함수/분기가 필요하다. 이 부분이 "고쳤나 안 고쳤나"의 두 번째 시험대

</code_context>

<specifics>
## Specific Ideas

**사용자가 처음에 세운 원칙(Phase 1에서 이어짐):** "웹이든 CLI든 모든 클라이언트에서 사용할 수 있는 코어를 만드는 게 중요하다." 이 단계에서는 "판정 방식이 다른 룰북 두 개가 코드 수정 없이 데이터로 들어가는가"로 구체화된다.

**"고치고 싶었지만 참았다"가 핵심 증거라는 관점** — 논의 중 사용자가 명시적으로 확인한 우선순위. `02-INTERFACE-CHANGES.md`는 실제로 고친 곳보다 "고치려다 데이터로 해결한 곳"을 더 무겁게 다뤄야 한다.

**네 수정치 유형 전부 실동작 원칙** — "자리만 있고 안 도는" 것은 검증으로서 약하다는 판단 아래, 표현(스키마)뿐 아니라 계산 로직까지 네 유형 모두 만든다.

</specifics>

<deferred>
## Deferred Ideas

- **룰북 데이터의 필드 단위 상세 규격 · 효과 원자 연산의 최종 목록** — ROADMAP.md가 M0 범위선 밖으로 명시. M1 착수 시
- **d20 롤오버 등 세 번째 이후 판정 방식** — Phase 2는 두 개만 검증한다. M1(d20)·M2(다이스풀·Year Zero)·M3(FATE)
- **룰북 파일 업로드 + 자동 구조화** — M1-04. Phase 2는 데이터를 손으로 쓴다
- **좌표계·전술 그리드·시야 계산** — D13⑥·D32 범위 밖. M4

### Reviewed Todos (not folded)

없음 — `todo.match-phase 2` 조회 결과 매칭되는 미해결 todo 없음.

</deferred>

---

*Phase: 2-룰북 두 개를 같은 그릇에*
*Context gathered: 2026-08-01*

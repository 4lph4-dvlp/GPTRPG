---
phase: 12-stats-resources-inventory
plan: 07
subsystem: ui
tags: [react, typescript, fastapi, resource-changes, verification-ui]

requires:
  - phase: 12-stats-resources-inventory
    provides: "12-01 — ResourceChanged 사건, GET 캐릭터 시트가 접은 지금 값을 돌려준다, ConfirmResponse 확장의 시작"
  - phase: 12-stats-resources-inventory
    provides: "12-06 — pick_outcome, pending_resource_changes/discretionary, POST confirm-resource-change 라우트(신원 대조·멱등)"
provides:
  - "frontend/src/components/CheckBreakdown.tsx — 눈·능력치 보정치·합계·목표값을 사람이 검산할 수 있게 보이는 컴포넌트(D-04)"
  - "frontend/src/components/ResourceChangeBadge.tsx + changeIntensity() — 여섯 표현 형태 전부에서 자원 변화를 보여주는 표시, 문턱 상수 없는 연속값 세기(RULE-07/D-19)"
  - "StatusPane이 폴링에 따라 다시 그려진다는 사실이 문서·동작 양쪽에 반영됨(RULE-06) — 시트가 사건으로 변한 뒤 새로고침 없이 새 값을 보인다"
  - "ChatPane의 자원 변화 확인 카드 — POST confirmResourceChange, busy 잠금으로 이중 클릭 방지, 변할 예정이 없으면 안 뜬다(D-09/D-10)"
  - "fix(12) 44ed73f — 캐릭터가 실제로 가진 축에만 자원 변화를 적용(character_axis_names/eligible_categories/require_axes_on_character), 제안·확인 두 시점 모두 대조"
  - "fix(ui) 1ad6dcd — 위협 시계 진행 문구가 trigger 값(advance/condition/exhausted)에 따라 갈린다, 더는 항상 실패로 표시하지 않는다"
affects: [13-regression-tests, 13.1-gm-leads-the-story]

actuals:
  tokens: 13800
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "changeIntensity(change, stat) -> number를 순수 함수로 뽑아 export — 형태별(상한 있는 숫자/상한 없는 숫자/슬롯/태그)로 계산 가능한 것만 쓰고, 등급 이름으로 가르는 분기나 백분율 문턱 상수를 코드에 두지 않는다. 시험이 단조성을 직접 단언해 RULE-07을 문턱 없이도 확인 가능하게 만든다"
    - "여섯 표현 형태 렌더 갈래(11-03)에 표시만 얹는다 — 새 갈래를 만들지 않는다. StatusPane.tsx의 stat.form 분기 개수는 이 계획 전후로 같다"
    - "확인 요청은 카테고리 식별자와 확인 여부만 보낸다 — 변화량 숫자는 애초에 요청 본문에 자리가 없다(서버가 룰북 선언에서 다시 굴린다, 12-06)"
    - "제안 시점과 확인 시점 양쪽에서 캐릭터가 실제로 가진 축만 대상으로 삼는다(44ed73f) — 룰북 선언 대조만으로는 부족하고, 개체 자신의 stats 튜플과도 맞춰야 한다"

key-files:
  created:
    - frontend/src/components/CheckBreakdown.tsx
    - frontend/src/components/ResourceChangeBadge.tsx
    - frontend/src/components/ResourceChangeBadge.test.ts
  modified:
    - frontend/src/api/types.ts
    - frontend/src/api/client.ts
    - frontend/src/labels.ts
    - frontend/src/panes/ChatPane.tsx
    - frontend/src/panes/StatusPane.tsx
    - frontend/src/panes/StoryPane.tsx
    - frontend/src/screens/SessionScreen.tsx
    - frontend/src/styles.css
    - src/gptrpg/web/routes_characters.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/rules_core/rulebook.py

key-decisions:
  - "changeIntensity는 형태마다 계산 가능한 신호만 쓴다 — 상한 있는 숫자·진행 칸은 변화량 대비 상한 비율, 상한 없는 숫자는 절대 크기를 완만하게 눌러 0~1, 슬롯·태그는 바뀐 개수/전체 칸 수. 반환 타입이 number 하나이고 이산 등급 문자열 분기가 없다"
  - "StatusPane 도크스트링의 '캐릭터 시트는 사건으로 변하지 않는 읽기 전용 자료라 한 번만 불러 둔다'는 거짓 전제를 제거 — 12-01 이후 시트는 시작값+접은 변화라 폴링마다 달라질 수 있다는 설명으로 교체. 매 폴링마다 무조건 다시 부르지 않고, 자원 변화 사건이 새로 들어왔거나 확인이 성공했을 때만 다시 부른다"
  - "44ed73f: 자원 변화 자격을 룰북 선언만으로 판단하지 않고 캐릭터 자신의 stats 튜플과도 대조한다 — 제안(outcome picker eligible_categories, discretionary axes 교집합)·제출(confirm-resource-change 400) 두 시점 모두. 카테고리는 통째로 걸러진다(부분 적용 없음) — 하나의 GM 응답이 절반만 적용되면 룰북이 선언한 적 없는 것이 된다"
  - "1ad6dcd: 시계 진행 문구를 trigger(advance/condition/exhausted) 세 갈래로 나눈다 — switch에 default 분기를 의도적으로 두지 않아, 네 번째 값이 생기면 조용히 폴백하지 않고 타입체크가 먼저 실패한다"

patterns-established:
  - "확인 카드 패턴(ChatPane의 기존 proposal 흐름)을 자원 변화 확인에 재사용 — busy 상태로 이중 클릭 방지, 서버 멱등(AlreadyChanged)과 화면 잠금 두 겹"
  - "순수 함수로 뽑은 세기 계산 함수에 단조성 시험(같은 축에서 변화량이 클수록 값이 작지 않다)을 붙이는 것으로, 문턱 상수를 코드에 안 두고도 '눈에 띄는가'를 회귀 방지 가능하게 만든다"

requirements-completed: [RULE-06, RULE-07]

coverage:
  - id: D1
    description: "판정이 끝나면 눈·능력치 보정치(출처 이름 포함)·합계·목표값이 화면에 보이고 사람이 그 산수를 검산할 수 있다 (D-04)"
    requirement: "RULE-02"
    verification:
      - kind: manual_procedural
        ref: "12-07-PLAN.md Task 3 확인 항목 1 — 사장님이 실제 판정으로 확인, PASS"
        status: pass
    human_judgment: true
    rationale: "화면에서 산수가 맞아떨어지는지는 사람 눈으로만 확인 가능 — 체크포인트에서 실제로 확인됨"
  - id: D2
    description: "캐릭터 시트가 지금 상태를 보여준다 — 자원이 변한 뒤 폴링으로 다시 그려지고, StatusPane 도크스트링의 거짓 전제가 제거됐다 (RULE-06)"
    requirement: "RULE-06"
    verification:
      - kind: unit
        ref: "uv run pytest tests/test_web_characters.py -q"
        status: pass
      - kind: manual_procedural
        ref: "12-07-PLAN.md Task 3 확인 항목 2 — 시트가 새로고침 없이 새 값으로 다시 그려짐, PASS"
        status: pass
    human_judgment: true
    rationale: "화면이 실제로 다시 그려지는지는 사람 눈으로 확인 — 체크포인트에서 PASS"
  - id: D3
    description: "자원이 변할 때마다 화면이 알린다(모든 변화가 보이고, 큰 것은 더 강하게 보인다). 여섯 표현 형태 전부에서 성립하고, 고정 문턱 상수를 코드에 두지 않는다 (RULE-07/D-19)"
    requirement: "RULE-07"
    verification:
      - kind: unit
        ref: "frontend/src/components/ResourceChangeBadge.test.ts — changeIntensity 단조성·범위(0~1)·반환타입 시험 4종(상한 있는 숫자/상한 없는 숫자/슬롯/태그)"
        status: pass
      - kind: manual_procedural
        ref: "12-07-PLAN.md Task 3 확인 항목 2 — 작게/크게 깎이는 결과를 각각 만들어 둘 다 알아챌 수 있는지, 큰 쪽이 더 강한지 확인, PASS(다만 아래 '알려진 갭' 참조)"
        status: pass
    human_judgment: true
    rationale: "'눈에 띄었는가'는 문턱 계산이 아니라 사람 판단 — 체크포인트에서 PASS로 확인됐으나, 변화가 보이는 것과 서사에 뜻이 연결되는 것은 별개 문제로 13.1에 남음(아래 알려진 갭)"
  - id: D4
    description: "변할 예정이 있을 때만 확인 카드가 뜨고, 그 캐릭터를 잡은 사람만 누를 수 있으며, 두 번 눌러도 한 번만 적용된다 (D-09/D-10)"
    requirement: "RULE-10"
    verification:
      - kind: unit
        ref: "uv run pytest tests/test_web_characters.py tests/test_web_actions.py -q"
        status: pass
      - kind: manual_procedural
        ref: "12-07-PLAN.md Task 3 확인 항목 3·4·5 — 확인 창 필요할 때만/남의 캐릭터 못 건드림/두 번 눌러도 한 번, 전부 PASS(브라우저 4개로 실측)"
        status: pass
    human_judgment: true
    rationale: "신원·중복 방지는 서버가 이미 시험으로 증명했지만, 화면 쪽 실제 상호작용(다른 브라우저·연타)은 사람이 실기로 확인"
  - id: D5
    description: "AI가 파티 네 명을 각각 다른 사람으로, 각자의 상태에 맞게 다룬다 — 세션1(2026-08-04)이 무너진 자리(D-18)"
    requirement: "RULE-08"
    verification:
      - kind: manual_procedural
        ref: "12-07-PLAN.md Task 3 확인 항목 6 — 파티 4명 실제 브라우저 4개로 자원 값을 다르게 만든 뒤 진행, 네 명을 뭉뚱그리지 않음 확인, PASS"
        status: pass
    human_judgment: true
    rationale: "AI 서술이 개별 인물을 구분하는지는 사람이 읽고 판단해야 한다 — 세션1 재현 시험이 이번에 처음으로 실물 4-브라우저 조건에서 PASS했다"

duration: ~2h (Task 1-2 실행 + 체크포인트 확인·발견된 결함 2건 수정 포함, 사람 확인 대기 시간 제외)
completed: 2026-08-18
status: complete
---

# Phase 12 Plan 7: 검산 표시 · 자원 변화 알림 · 확인 UI Summary

**능력치가 판정에 실제로 반영됐다는 것과 자원이 방금 변했다는 것을 사람이 화면에서 볼 수 있게 했다 — CheckBreakdown(D-04)과 ResourceChangeBadge(RULE-07/D-19)를 여섯 표현 형태 위에 얹고, 자원 변화 확인 카드(D-09/D-10)로 실제 적용을 사람 손에 남겼다.**

## Performance

- **Duration:** ~2시간(Task 1-2 실행 + 체크포인트 확인 중 발견된 결함 2건 수정 포함, 사람 확인 대기 시간 제외)
- **Tasks:** 3/3 (Task 3은 human-verify 체크포인트, 승인됨)
- **Files modified:** 11개(신규 3 + 기존 8) + 체크포인트에서 발견·수정한 결함 2건이 추가로 건드린 파일 7개

## Accomplishments

- **검산 표시(D-04)** — `CheckBreakdown` 컴포넌트가 눈·각 보정치의 값과 출처(능력치 이름은 `statLabel()`로 사람 말로 옮김)·합계·목표값을 한 블록으로 보인다. `ChatPane`이 `confirmAction` 응답 뒤 이것을 그린다. 판정이 없는 턴에는 안 뜬다.
- **자원 변화 표시(RULE-07/D-19)** — `ResourceChangeBadge` + 순수 함수 `changeIntensity(change, stat) -> number`(0~1 연속값, 문턱 상수 없음)가 11-03이 만든 여섯 표현 형태 갈래 각각에 표시만 얹는다. `StatusPane.tsx`의 `stat.form` 분기 개수는 이 계획 전후로 같다 — 새 렌더 갈래를 안 만들었다.
- **시트가 지금 상태를 보여준다(RULE-06)** — `StatusPane.tsx` 도크스트링의 「사건으로 변하지 않는 읽기 전용 자료라 한 번만 불러 둔다」는 거짓 전제를 제거했다. `SessionScreen.tsx`가 자원 변화 사건이 폴링에 새로 들어오거나 확인이 성공했을 때만 시트를 다시 부른다(매 폴링 무조건 재요청 아님). `routes_characters.py`의 `get_character_sheet` 도크스트링에도 "이제 이 응답은 접은 값이다"를 한 줄 더했다.
- **확인 카드(D-09/D-10)** — `confirmResourceChange(sessionId, characterId, causedBySeq, categoryIds, confirmed)`가 카테고리 식별자와 확인 여부만 보낸다(변화량 숫자는 요청 본문에 자리 자체가 없다). `ChatPane`의 기존 확인 카드 패턴을 재사용해 `busy` 상태로 이중 클릭을 막는다. `pending_resource_changes`가 비면 카드가 아예 안 뜬다(D-09). 403은 사람이 읽을 수 있는 문구로 옮긴다.
- **Task 3 체크포인트 — 사람이 눈으로 확인, 승인됨.** 4개의 실제 Chrome 프로필(4명의 플레이어)로 진행한 실측에서 여섯 항목 모두 PASS했다. 그중 가장 중요한 항목은 6번(AI가 파티 넷을 네 사람으로 본다, D-18) — 세션1(2026-08-04) 붕괴 지점이 실제 4-브라우저 조건에서 재현되지 않는다는 것을 처음으로 확인했다.

## Task Commits

1. **Task 1: 「주사위 7 + 힘 2 = 9, 목표 10」을 화면에 띄운다 (D-04)** — `5ebe3af` (feat)
2. **Task 2: 자원이 변할 때마다 알리고, 변할 예정이면 그 캐릭터를 잡은 사람에게 확인을 받는다 (RULE-06/RULE-07/D-19/D-10)** — `0307fcf` (feat)
3. **Task 3: 사람 눈으로만 확인되는 여섯 가지 확인 관문** — 승인(체크포인트, 코드 커밋 없음)

**체크포인트 확인 중 사장님이 발견하고, 오케스트레이터가 그 자리에서 수정한 결함 2건(이 계획의 Task 산출물이 아니라 확인 과정에서 나온 별도 수정):**

4. **fix(12): 캐릭터가 안 가진 축에 자원 변화가 적용되던 결함** — `44ed73f` (fix)
5. **fix(ui): 시계 진행 문구가 trigger와 무관하게 항상 실패로 표시되던 결함** — `1ad6dcd` (fix)

**Plan metadata:** (이 커밋 — docs)

## Files Created/Modified

- `frontend/src/components/CheckBreakdown.tsx` — (신설) 눈·보정치·합계·목표값 검산 표시
- `frontend/src/components/ResourceChangeBadge.tsx` — (신설) 자원 변화 표시, `changeIntensity()` export
- `frontend/src/components/ResourceChangeBadge.test.ts` — (신설) 단조성·범위·반환타입 시험 4종
- `frontend/src/api/types.ts` — `ModifierView`·`ResourceChangeView`·`PendingResourceChangeView`, `ConfirmResponse` 확장
- `frontend/src/api/client.ts` — `confirmResourceChange`
- `frontend/src/labels.ts` — 검산·변화 표시·확인 문구, 시계 진행 문구 3갈래
- `frontend/src/panes/ChatPane.tsx` — `CheckBreakdown` 배치, 자원 변화 확인 카드
- `frontend/src/panes/StatusPane.tsx` — 도크스트링 정정, 여섯 형태 갈래에 `ResourceChangeBadge` 배치
- `frontend/src/panes/StoryPane.tsx` — (fix 1ad6dcd) 시계 진행 문구를 `trigger`로 분기
- `frontend/src/screens/SessionScreen.tsx` — 시트 재요청 계기(자원 변화 사건 유입 / 확인 성공)
- `frontend/src/styles.css` — 검산·변화 표시 클래스(최소)
- `src/gptrpg/web/routes_characters.py` — 시트가 접은 값이라는 도크스트링 정정
- `src/gptrpg/web/routes_actions.py` — (fix 44ed73f) 제안·확인 시점 축 자격 대조
- `src/gptrpg/rules_core/rulebook.py` — (fix 44ed73f) `character_axis_names`/`eligible_categories`/`require_axes_on_character`

## Decisions Made

주요 설계 판단은 프런트매터 `key-decisions`에 있다. 요약:

- `changeIntensity`는 형태별로 계산 가능한 신호만 쓰고 등급 이름 분기·백분율 문턱 상수를 코드에 안 둔다 — 단조성 시험이 RULE-07을 문턱 없이도 회귀 방지 가능하게 만든다.
- `StatusPane` 도크스트링의 거짓 전제(읽기 전용, 한 번만 불러 둔다)를 제거하고, 필요할 때만 다시 부르는 것으로 불필요한 요청 증가를 피했다.
- 자원 변화 자격은 룰북 선언만이 아니라 캐릭터 자신의 stats 튜플과도 대조한다(44ed73f) — 카테고리는 통째로 걸러진다.
- 시계 진행 문구는 `trigger` 세 값으로 분기하고 `default` 분기를 의도적으로 안 둔다(1ad6dcd) — 조용한 폴백을 타입체크 실패로 바꾼다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - 버그, 체크포인트 확인 중 발견] 캐릭터가 안 가진 축에 자원 변화가 적용되어 사건까지 기록됐지만 조용히 버려짐**
- **Found during:** Task 3 체크포인트 확인 (사장님이 실제 4인 플레이 중 관찰 — 나리의 방어구 축이 없는데 방어구를 깎는 결과가 나옴)
- **Issue:** 결과 카테고리 자격 판단이 룰북의 닫힌 목록(`ordered_categories`)만 대조하고 캐릭터가 실제로 그 축을 가졌는지는 안 봤다. 사건은 기록되고 화면에는 「변했다」 표시까지 떴지만, `resolve_character_stats`가 그 캐릭터의 stats 튜플에 없는 축이라 조용히 op을 버렸다 — 기록은 남는데 실제로는 아무 일도 안 일어난 상태.
- **Fix:** `rules_core.rulebook`에 `character_axis_names`/`eligible_categories`/`require_axes_on_character`를 더해, 제안 시점(outcome picker가 보는 자격 있는 카테고리, discretionary 축 목록)과 제출 시점(`confirm-resource-change`의 400 거절) 양쪽에서 캐릭터 자신의 축과 대조한다. 카테고리는 통째로 걸러진다(부분 적용 없음).
- **Files modified:** `src/gptrpg/rules_core/rulebook.py`, `src/gptrpg/web/routes_actions.py`, `tests/test_rulebook.py`, `tests/test_web_actions.py`
- **Verification:** 회귀 시험 6건 추가, 전체 스위트 통과
- **Committed in:** `44ed73f` (fix) — **이 계획의 Task 산출물이 아니라 오케스트레이터가 체크포인트 확인 중 발견해 직접 수정**

**2. [Rule 1 - 버그, 체크포인트 확인 중 발견] 위협 시계 진행 문구가 `trigger` 값과 무관하게 항상 「판정 실패가 쌓여」로 표시됨**
- **Found during:** Task 3 체크포인트 확인 (사장님이 완전 성공 뒤 시계가 돈 것을 보고 "왜 실패라고 하는가" 질문)
- **Issue:** `ClockAdvanced` 사건은 이미 세 `trigger` 값(advance/condition/exhausted)을 갖고 있었고 프론트엔드 타입도 이미 선언돼 있었지만, `StoryPane.tsx`의 표시 문구가 그 값을 안 보고 항상 실패 문구 하나로 고정돼 있었다. `trigger="condition"`으로 (완전 성공을 포함한) 서사적 이유로 돈 시계에도 실패 문구가 나왔다 — 방금 성공한 사람에게 "실패해서"라고 말하는 거짓.
- **Fix:** `labels.ts`에 세 갈래 문구를 두고 `StoryPane.tsx`가 `trigger`로 분기한다. `switch`에 `default` 분기를 의도적으로 안 둬서, 네 번째 값이 생기면 타입체크가 먼저 실패하도록 만들었다(조용한 폴백 방지).
- **Files modified:** `frontend/src/labels.ts`, `frontend/src/panes/StoryPane.tsx`, `frontend/src/panes/StoryPane.test.ts`
- **Verification:** 회귀 시험 4건 추가, `npx tsc --noEmit`/`npm run build`/`npm run test` 통과
- **Committed in:** `1ad6dcd` (fix) — **이 계획의 Task 산출물이 아니라 오케스트레이터가 체크포인트 확인 중 발견해 직접 수정**

---

**Total deviations:** 2 auto-fixed (둘 다 Rule 1 — 체크포인트 확인 중 사람이 실제 4인 플레이로 발견한 버그)
**Impact on plan:** 둘 다 이 계획이 만든 표시 자체(검산·변화 알림)의 신뢰도를 지키는 데 필요했다 — 화면이 "변했다"고 보여주면서 실제로는 안 변했거나, "실패해서"라고 보여주면서 실제로는 성공했다면 이 계획의 목적(사람이 실제로 일어난 일을 화면에서 볼 수 있게 한다) 자체가 거짓이 된다. 스코프 확장이 아니라 이 계획이 세운 표시의 정확성을 지키는 수정이다.

## Issues Encountered

None beyond the two deviations above.

## Known Stubs / 알려진 갭 (13.1로 미룸, 차단 아님)

**3. 서사가 자원 변화를 모른다.** `NarrationFacts`(여덟 칸)에 고른 결과 카테고리를 담는 칸이 없고, 서사(`proceed()`)와 자원 확인(별도 요청 `POST confirm-resource-change`)이 구조적으로 만나지 않는다 — 서사를 쓰는 시점에는 아직 무엇이 깎일지 정해지지도 않았다(D-09). RULE-07은 문자 그대로("자원이 크게 깎이면 화면에서 바로 보인다")는 이번 계획으로 만족됐지만, 사장님 판단은 **"보이는데 뜻이 없으면 소용이 없다"** — 실측에서 방어구가 깎였는데 서사에 그 이유가 한 줄도 없었다. 이 결함은 Phase 13.1(진행자가 이야기를 이끈다)과 뿌리가 같아 따로 안 고치고 13.1에서 함께 본다. → `.planning/todos/pending/2026-08-18-narration-blind-to-resource-change.md`

**4. 시계가 「위협」 하나뿐이라 잘해도 나빠지는 쪽으로만 기록된다.** 완전 성공(`defy_danger` 등)이 위협 시계를 진행시켰다 — 「좋은 쪽 진행」을 담을 그릇이 플랫폼에 없다(설계 문서 자체가 「시계」를 "나쁜 일들의 목록"으로만 정의). 위 결함 2건 중 하나(1ad6dcd)는 화면이 그 사실을 실패로 잘못 말하던 것만 멈췄다 — 「좋은 진행」을 표현할 그릇을 만드는 것 자체는 13.1의 몫이다. → `.planning/todos/pending/2026-08-18-no-clock-for-good-progress.md`

이 두 갭 모두 이 계획의 `must_haves`/`success_criteria`에 적힌 문자 그대로의 기준은 충족한다 — 자원이 변하면 보이고(RULE-07), 시트는 지금 상태를 보여준다(RULE-06). 남은 것은 "보이는 것이 뜻과 이어지는가"라는 더 깊은 문제이고, 이는 명시적으로 13.1에 배정된 별개 요구사항이다.

## Threat Flags

새로 연 표면 없음 — 이 계획이 만든 것(`CheckBreakdown`·`ResourceChangeBadge`·확인 카드)은 전부 계획의 `<threat_model>`이 이미 등록한 항목(T-12-32~T-12-35)의 완화로 덮인다. 체크포인트 확인 중 수정한 `44ed73f`(축 자격 대조)는 T-12-32/T-12-35의 완화를 강화하는 방향이며 새 신뢰 경계를 안 연다. `1ad6dcd`는 순수 화면 표시 정정으로 신뢰 경계와 무관하다.

## User Setup Required

None - 외부 서비스 설정 불필요.

## Next Phase Readiness

- **RULE-06/RULE-07이 이 계획으로 완전히 닫힌다** — REQUIREMENTS.md 추적표에서 이 둘을 `requirements`로 갖는 다른 계획이 없음을 확인했다(`12-01-PLAN.md`만 RULE-06을 함께 적었으나 backend 절반만 담당, 실제 화면 재렌더 완성은 이 계획). 12-01-SUMMARY.md가 이전에 `requirements-completed: [... RULE-06 ...]`을 적었지만 REQUIREMENTS.md 추적표는 그때 체크되지 않은 채로 남아 있었다 — 이 계획이 실제로 화면 쪽 절반을 완성한 지금에야 체크한다.
- **Phase 12(stats-resources-inventory)가 7개 계획 전부 완료됐다** — 다음은 로드맵의 Phase 12.1(캐릭터 만들기)이다.
- **13.1(GM이 이야기를 이끈다)이 이어받을 것 둘:** 서사-자원 변화 연결 부재, 위협 시계 하나뿐인 설계 한계. 둘 다 위 "알려진 갭"에 todo 파일로 기록됨.
- **차단 아님:** 이 계획의 `must_haves`/`success_criteria`는 문자 그대로 전부 충족됐고 자동화 검증(pytest 1137건, tsc, build, vitest 14건)과 사람 확인 관문(6항목 PASS) 둘 다 통과했다.

---
*Phase: 12-stats-resources-inventory*
*Completed: 2026-08-18*

## Self-Check: PASSED

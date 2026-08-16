---
phase: 11-rulebook-vocabulary
verified: 2026-08-16T16:36:04Z
status: human_needed
score: 5/5 roadmap 성공 기준 verified (RULE-11은 부분 실증 — 아래 참고)
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "11-01-PLAN.md 181행에 남아 있는 미해소 탐침 항목(RULE-12) — 「값 0 / 개념 없음 / 규칙으로 안 셈 / 빠뜨림」 네 구분에 대해 자동 탐침이 스스로 분류하지 못한 경계 질문이 있는지 사람이 직접 훑어야 한다"
    expected: "핵심 구분(값 0 vs 개념 없음 vs 규칙으로 안 셈)은 11-01·11-03·11-07의 시험으로 이미 고정되어 있다는 것을 확인했으므로, 남은 질문은 「그 시험들이 놓친 경계가 더 있는가」뿐이다. 없다고 판단되면 그대로 종결, 있다고 판단되면 Phase 12 계획에 반영"
    why_human: "탐침 도구 자신이 이 요구사항에 대해 무슨 질문을 던져야 할지 스스로 정하지 못하고 「unclassified — review manually」로 남긴 항목이라 grep이나 시험 실행으로는 답이 안 나온다. 계획 문서가 명시적으로 「검증 단계에서 사람에게 그대로 올린다 — 자동 통과 처리하지 않는다」고 적어 뒀다"
  - test: "판정 없이 이야기가 이어지는 화면(D-10/D-11 경로)이 실제 배포 환경에서 켜지는지 확인 — 분류기 모델 설정이 이 화면의 실제 작동 여부를 좌우한다"
    expected: "작은 분류기 모델(예: 8B)에서는 「문을 연다」 같은 문장도 판정이 필요한 것으로 잘못 분류돼 이 화면이 실전에서 거의 안 켜졌다는 것이 11-06 사람 확인 관문에서 이미 측정됐고, 사장님이 큰 모델로 올리는 결정을 내렸다. 그 설정(`.gptrpg/agents.json`)은 git이 무시하는 로컬 파일이라 저장소에 남지 않는다 — 새로 이 저장소를 받는 사람/환경은 같은 설정을 다시 해야 이 기능이 실제로 작동한다"
    why_human: "코드는 옳고 자동 시험은 전부 가짜 모델을 쓰므로 이 문제를 절대 못 잡는다 — 실제 모델로 사람이 확인해야만 드러나는 종류의 문제다. 이번 검증은 이미 기록된 측정 결과(11-MODEL-FINDING.md)를 확인했을 뿐, 재측정하지 않았다"
gaps: []
deferred:
  - truth: "여섯 가지 표현 형태(숫자+상한 / 세그먼트 원 / 이름 붙은 칸 / 태그 목록 / 자원 주사위 / 없음) 전부가 실제로 저장소에 출하되는 룰북 데이터에서 쓰인다"
    addressed_in: "이후 마일스톤(11-CONTEXT.md가 명시적으로 「남는 형태의 실사용 검증은 이후 마일스톤」이라고 적어 뒀다)"
    evidence: "지금 실제로 쓰이는 것은 숫자+상한(모든 룰북) / 없음(던전월드류 소지품) / 이름 붙은 칸(Cairn 소지품) 셋뿐이다. 세그먼트 원 · 태그 목록 · 자원 주사위 세 형태는 선언·검증·화면 렌더 갈래가 전부 만들어져 있지만 그것을 실제로 쓰겠다고 선언한 룰북이 아직 하나도 없다. 이것은 이 단계가 스스로 정한 범위 결정이지 빠뜨린 것이 아니다"
  - truth: "코드 리뷰가 지적한 `_format_scene_entities`의 여섯 형태 미대응(CR-02) 수정"
    addressed_in: "사람 결정으로 보류 — `.planning/WINDOWS.md` 6번 항목, status: open"
    evidence: "지금은 장면에 등장하는 개체가 전부 숫자+상한 형태만 쓰고 있어 실제로 문제가 발생하지 않는다(코드로 확인). Cairn류 룰북의 개체가 장면에 등장하는 순간 진행자에게 가는 문장에 파이썬 None이 그대로 새어 들어갈 수 있는 잠재 결함이며, 고쳐야 할 곳까지 기록돼 있다"
---

# Phase 11: 룰북 표현 어휘 확장 검증 보고서

**단계 목표:** 체력·소지품·스트레스·진행 원을 하나의 「이름 붙은 자원 축」 그릇이 담고,
룰북이 「이 개념을 안 쓴다」를 명시적으로 선언할 수 있으며, 선언하면 관련 화면과 판정
훅이 완전히 사라진다.
**검증 시각:** 2026-08-16T16:36:04Z
**상태:** human_needed (자동으로 확인 가능한 부분은 전부 통과 — 사람이 두 가지를 마저 봐야 한다)
**재검증 여부:** 아니요 — 첫 검증

## 한눈에 보는 결론

이번 단계가 약속한 것 — "체력·소지품 같은 숫자를 담는 그릇 하나를 만들고, 룰북마다
"우리는 이걸 안 쓴다"를 선언할 수 있게 하고, 안 쓴다고 선언하면 화면과 판정에서
정말로 사라지게 만드는 것 — 은 코드에서 실제로 확인됩니다. 특히 아래 세 가지가 눈에
띕니다.

1. **플랫폼 코드가 룰북 이름을 모릅니다.** "체력"이나 "소지품" 같은 단어는 코드 어디에도
   상수나 조건문으로 박혀 있지 않고, 전부 룰북이 건네주는 문자열입니다. 세 번째 룰북
   (Cairn)을 추가했을 때 이 코드의 핵심 그릇(`entities.py`)이 **한 줄도 바뀌지 않았다**는
   것으로 이 원칙이 실제로 지켜졌음을 확인했습니다.
2. **"안 쓴다"가 진짜로 사라집니다.** 던전월드 계열 룰북이 실제로 "소지품은 규칙으로
   안 센다"를 선언했고, 그 캐릭터의 시트 응답 안에는 "소지품"이라는 글자 자체가 아예
   없다는 것이 자동 시험으로 고정돼 있습니다. 화면이 숨기는 게 아니라 서버가 처음부터
   안 보내는 방식이라, 나중에 다른 화면이 추가돼도 같은 실수가 반복될 수 없습니다.
3. **검증 중 실제 보안 문제 하나를 찾아 그 자리에서 고쳤습니다.** "판정 없이 이야기를
   이어가는" 새 기능에서, 다른 사람의 행동 선언을 가로채 판정 없이 서사를 받아낼 수
   있는 구멍이 있었습니다. 이번 검증 과정에서 실제 서버를 띄워 이 구멍을 재현했고,
   수정 후 다시 막혔는지 확인했습니다. 지금 코드에는 이 구멍을 막는 검사와, 그 검사가
   계속 지켜지는지 확인하는 자동 시험이 들어 있습니다.

다만 완전히 자동으로는 확인할 수 없는 두 가지가 남아 있어 **사람 확인이 필요한 상태**로
분류합니다. 자세한 내용은 "사람이 확인할 것" 항목을 봐 주세요. 둘 다 코드 결함이
아니라 확인 절차상 사람 눈이 필요한 항목입니다.

또한 "체력·소지품·스트레스·진행 원을 하나의 그릇으로 담는다"는 약속 자체는 이뤄졌지만,
그 그릇이 표현할 수 있는 여섯 가지 모양 중 아직 세 가지(세그먼트 원·태그 목록·자원
주사위)는 **실제로 그 모양을 쓰겠다고 선언한 룰북이 하나도 없습니다.** 그릇과 화면은
전부 준비돼 있지만 아직 아무도 안 써 봤다는 뜻입니다. 이건 이 단계가 처음부터
"이번에는 세 가지만 실제 룰북으로 실증하고 나머지는 다음에 채운다"고 계획 단계에서
스스로 정한 범위이지, 빠뜨린 것이 아닙니다 — 그래서 이 요구사항은 요구사항 목록에도
"진행 중"으로 정직하게 기록돼 있습니다.

## Goal Achievement

### Observable Truths (ROADMAP 성공 기준 5개 기준)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 체력·소지품·스트레스·진행 원이 하나의 그릇으로 표현되고, 표현 형태를 룰북이 고른다 | ✓ VERIFIED (그릇은 완성, 실사용은 3/6) | `src/gptrpg/rules_core/entities.py`의 `StatEntry`가 여섯 형태를 모두 지원하고 형태별 정합성 검증을 갖춤. 실제로 등록된 세 룰북에서 `numeric`(모든 룰북) / `none`(던전월드류 소지품) / `named_slots`(Cairn 소지품) 세 형태가 실사용 확인됨. `clock`/`tag_list`/`usage_die`는 선언·검증·화면 렌더 갈래(`StatusPane.tsx`)까지 다 있지만 실제로 그 형태를 쓰는 룰북이 없음(의도된 범위, 위 "결론" 참고) |
| 2 | 룰북이 「안 쓴다」를 선언할 수 있고, 선언하면 화면 요소와 판정 훅이 완전히 사라진다 | ✓ VERIFIED | `_visible_stats()`(routes_characters.py)가 `form="none"` 축을 시트 응답 조립 단계에서 제외 — 응답 JSON 문자열에 축 이름 자체가 없음. `test_none_axis_excluded_from_sheet_response`, `test_dungeonworld_discretionary_axis_is_absent_from_sheet_response` 실행 확인(통과). 던전월드류가 실제로 "소지품"을 `form="none", none_kind="discretionary"`로 선언(`dungeonworld_like.py:49`) |
| 3 | 「값 0」과 「개념 없음」이 구분되고, 「빠뜨려서 비어 있음」과 「의도적으로 없다고 선언함」도 구분된다 | ✓ VERIFIED | `StatEntry.form`에 기본값이 없어 형태를 안 적으면 생성 자체가 실패. `form="none"`은 `none_kind`(규칙으로 안 셈/이 세계에 없음) 필수. `Rulebook.resource_axes`도 기본값 없는 필수 필드라 "룰북이 자원 축을 아예 안 적음"은 파이썬 `TypeError`로 즉시 걸림 |
| 4 | 판정 트리거 목록이 비어 있는 것이 정상값이다 | ✓ VERIFIED | Cairn이 실제로 빈 트리거 목록(`check_trigger_mode="gm_discretion"`)으로 등록됨, `get_moves("cairn")`이 예외 없이 빈 값 반환. 분류기 결과가 4갈래(`single`/`several`/`no_check`/`unclear`)로 넓어져 "판정 필요 없음"과 "못 알아들음"이 분리됨. "판정 없이 이야기가 이어지는" 웹·CLI 경로(`POST /proceed`)가 실제로 구현되고 소유권·분류 결과 이중 검사까지 갖춤(아래 보안 항목 참고) |
| 5 | 등급 구간이 가려지거나 도달 불가능하면 등록할 때 걸린다(단순 겹침은 정상) | ✓ VERIFIED | `validate_grade_bands()`가 임포트 시점에 실행되고 가려짐(`ShadowedGradeBand`)·구멍(`UncoveredOutcomeGap`) 둘만 잡음. `tests/test_rulebook.py` 45개 시험 전부 통과(직접 실행 확인). 기존 두 룰북의 "일부러 겹치는" 등급 밴드가 여전히 등록을 통과함(회귀 없음) |

**점수:** 5/5 성공 기준 확인됨 (기준 1은 그릇 완성, 실사용 범위는 계획된 3/6)

### 사람이 확인할 것

자동으로는 답을 낼 수 없어 사람 눈이 필요합니다.

#### 1. 계획 문서에 남겨 둔 미해소 확인 항목

**확인할 것:** `11-01-PLAN.md` 181행에 "탐침이 못 본 다른 경계가 있는지는 사람이
봐야 안다"고 명시적으로 적어 둔 항목이 있습니다. "안 쓴다" 선언의 핵심 구분(값 0
/ 개념 없음 / 규칙으로 안 셈 / 빠뜨림)은 이미 자동 시험으로 고정돼 있지만, 자동
탐침 도구 자신이 이 요구사항에 대해 스스로 질문을 만들지 못하고 포기한 줄입니다.

**기대하는 결과:** 이 검증이 확인한 시험들(위 성공 기준 2·3 근거) 밖에 놓친 경계가
더 있는지 사람이 훑어보고, 없으면 그대로 종결, 있으면 다음 단계(Phase 12) 계획에
반영합니다.

**왜 사람이 봐야 하나:** 계획 문서가 "검증 단계에서 이 줄을 그대로 사람에게 올린다
— 자동 통과 처리하지 않는다"고 명시적으로 못박아 뒀습니다. 자동 검증이 임의로
"괜찮아 보인다"고 넘기면 안 되는 항목입니다.

#### 2. 「판정 없이 이야기가 이어지는」 기능이 실제로 켜지는지

**확인할 것:** 이 기능이 실제로 작동하려면 AI 판정관 모델을 어떤 것으로 쓰는지가
중요합니다. 작은 모델은 "문을 연다"처럼 판정이 필요 없는 문장도 판정이 필요한
것으로 잘못 읽어서, 이 기능이 실전에서 거의 안 켜지는 것으로 이미 확인됐습니다
(11-06 단계의 사람 확인 과정에서 실제 측정). 이 설정은 저장소에 저장되지 않는
개인 설정 파일에 들어 있어서, 새로 이 저장소를 내려받는 사람은 같은 설정을 직접
해 줘야 이 기능이 실제로 켜집니다.

**기대하는 결과:** 배포하거나 다른 사람에게 넘길 때 이 설정을 함께 안내하거나,
설정 자체를 저장소 안으로 옮기는 것을 검토합니다.

**왜 사람이 봐야 하나:** 코드 자체는 옳고, 이 저장소의 모든 자동 시험은 진짜
AI 모델 대신 가짜 응답을 쓰기 때문에 이런 종류의 문제(모델 크기에 따른 판단
품질 차이)를 절대 잡아내지 못합니다. 실제 모델로 직접 확인해야만 드러납니다.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/gptrpg/rules_core/entities.py` | 여덟 칸 `StatEntry`, 형태별 정합성 검증 | ✓ VERIFIED | 여섯 형태 각각 전용 필드 조합을 강제하는 `_validate_form_payload()` 확인. `STAT_ENTRY_FIELD_NAMES`/`ENTITY_FIELD_NAMES` 고정 상수 존재 |
| `src/gptrpg/rules_core/rulebook.py` | `ResourceAxisDecl`, `Rulebook.resource_axes`(필수), 등록 검증 | ✓ VERIFIED | `resource_axes: tuple[ResourceAxisDecl, ...]` 기본값 없음(생성자 필수), `validate_grade_bands`/`validate_entity_axes`/`validate_move_stats`/`validate_trigger_mode` 전부 존재 |
| `src/gptrpg/rulebooks/cairn.py` | 세 번째 룰북, 플랫폼 그릇 변경 없이 등록 | ✓ VERIFIED | `git show`로 11-04(Cairn) 커밋 6개 전부 확인 — `rules_core/entities.py`를 건드린 커밋이 하나도 없음. `named_slots`(10칸 소지품) 형태 실사용 |
| `src/gptrpg/web/routes_characters.py` | `_visible_stats()` — none 축 응답 제외 | ✓ VERIFIED | 코드·시험 둘 다 확인 |
| `frontend/src/panes/StatusPane.tsx` | 여섯 형태 렌더 갈래 | ✓ VERIFIED (경고 하나 있음) | 여섯 갈래 존재. 다만 여섯 번째(`none`) 자리의 "return null"이 정확히 `form==="none"`만 거르는 게 아니라 무조건 마지막 갈래라, 미래에 서버가 새 형태를 추가했는데 화면이 못 따라가면 그 축이 소리 없이 사라짐(코드 리뷰 WR-04, 경고 등급 — 지금 당장은 영향 없음) |
| `src/gptrpg/agents/prompt_assembly.py` | `_format_resource_treatment`, 여섯 형태 대응 `_format_character_state` | ✓ VERIFIED | 두 함수 모두 코드로 직접 확인. 다만 형제 함수 `_format_scene_entities`는 같은 대응을 못 받아 잠재 결함으로 남음(코드 리뷰 CR-02, 사람이 보류 결정 — 아래 "알려진 채로 남겨 둔 것" 참고) |
| `LICENSES.md` | Cairn CC BY-SA 4.0 항목 | ✓ VERIFIED | 항목 존재 확인 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `ResourceAxisDecl.form` | `StatEntry.form` | 같은 `ResourceAxisForm` 리터럴 공유 | ✓ WIRED | 두 곳 모두 `entities.py`의 같은 `Literal` 타입을 가져다 씀 |
| 룰북 선언(축 목록) | 등록 검증 | `rulebooks/__init__.py`의 임포트 시점 검증 루프 | ✓ WIRED | `validate_registered_rulebooks()`가 세 룰북 전부에 대해 실행되고, 던전월드류·OpenQuest·Cairn 모두 등록 통과 확인(45개 시험 실행) |
| `declare()`의 `tier=="no_check"` | `POST /proceed` 라우트 | `ChatPane`의 진행 버튼 | ✓ WIRED | 코드 확인 + `VerifyProceedEligibility`가 소유권·분류결과 이중 검사를 하는 것을 실제 시험 4개 실행으로 확인(통과) |
| 서버 응답 제외 로직 | 프론트엔드 렌더 갈래 | `form==="none"` 축이 프론트 조건문 없이 사라짐 | ✓ WIRED | `StatusPane.tsx`에 `form==="none"`을 걸러내는 조건문이 없음(서버가 이미 뺐으므로 그 갈래에 절대 안 옴) — 코드로 직접 확인 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| "다른 사람 행동에 무임승차해 판정 건너뛰기" 보안 수정이 실제로 막는지 | `uv run pytest tests/test_web_actions.py::test_proceed_on_another_characters_declare_returns_400_and_appends_nothing tests/test_web_actions.py::test_proceed_on_own_no_check_declare_still_returns_200 tests/test_session_actor.py::test_proceed_on_never_classified_declare_is_rejected_and_appends_nothing tests/test_session_actor.py::test_proceed_on_another_characters_declare_is_rejected_and_appends_nothing` | 4 passed | ✓ PASS |
| 「안 쓴다」 축이 시트 응답에서 진짜로 사라지는지 | `uv run pytest tests/test_web_characters.py -k none` | 2 passed | ✓ PASS |
| 등급 밴드 가려짐/구멍 검증 전체 | `uv run pytest tests/test_rulebook.py` | 45 passed | ✓ PASS |
| 전체 파이썬 시험(1회) | `uv run pytest -q` | 927 passed | ✓ PASS |
| 룰북 → 규칙 코어 방향 의존성 규율 | `uv run lint-imports` | 4 kept, 0 broken | ✓ PASS |
| 프론트엔드 단위 시험 | `npx vitest run` (frontend/) | 4 passed | ✓ PASS |
| 프론트엔드 타입 검사 | `npx tsc --noEmit` (frontend/) | 오류 없음 | ✓ PASS |
| 작업 트리 정합성 | `git status --short -- src/ frontend/ tests/` | 출력 없음(깨끗함) | ✓ PASS |

### Requirements Coverage

| Requirement | 원문(간단히) | 이 단계 계획 배정 | 상태 | 근거 |
|-------------|-------------|------------------|------|------|
| RULE-11 | 자원 축을 하나의 그릇으로 담고 표현 형태를 룰북이 고른다 | 11-01, 11-02, 11-03, 11-04 | 부분 완료 (그릇·검증·화면 완성, 실사용 3/6) | 위 성공 기준 1 근거 그대로. `REQUIREMENTS.md`도 "진행 중"으로 정직하게 기록돼 있고, 코드 확인 결과 그 기록이 사실과 맞음 |
| RULE-12 | 「안 쓴다」 선언과 완전한 화면·판정 제외 | 11-01, 11-02, 11-03, 11-07 | 완료 | 위 성공 기준 2 근거. 다만 미해소 확인 항목 하나가 사람 확인 대기 중(위 참고) |
| RULE-15 | 판정 트리거 목록 빈 값이 정상, 판정 없이 진행 가능 | 11-04, 11-05, 11-06 | 완료 | 위 성공 기준 4 근거. 보안 구멍을 검증 과정에서 찾아 즉시 수정 |
| QUAL-03 | 등급 구간 가려짐·구멍이 등록 시점에 걸림 | 11-02, 11-04 | 완료 | 위 성공 기준 5 근거 |

**요구사항 목록 대조:** `REQUIREMENTS.md`에서 Phase 11에 배정된 네 항목(RULE-11, RULE-12,
RULE-15, QUAL-03) 전부가 실제로 일곱 계획 중 하나 이상에 배정돼 있고, 빠뜨린 항목(고아
요구사항) 없음.

### Anti-Patterns Found

코드 리뷰(`11-REVIEW.md`)가 이미 표준 깊이로 훑어 심각 2건·경고 5건을 찾았습니다.
이번 검증에서 각각을 다시 확인한 결과는 다음과 같습니다.

| 항목 | 등급 | 상태 | 비고 |
|------|------|------|------|
| CR-01: `POST /proceed`가 소유권·분류결과 검사 없이 다른 사람 행동에 판정 없이 서사를 붙일 수 있었음 | 심각(원래) | **수정 확인됨** | `da0a758` 커밋으로 수정, 관련 시험 4개 실제 실행해 통과 확인. 지금 코드에는 이 구멍이 없음 |
| CR-02: `_format_scene_entities`가 여섯 형태 중 셋에서 `None`을 그대로 진행자 문맥에 흘릴 수 있음 | 심각 | **알려진 채로 보류(사람 결정)** | 지금 등록된 룰북 데이터로는 발동하지 않음(장면 등장 개체가 전부 숫자+상한 형태만 씀, 코드로 확인). `.planning/WINDOWS.md` 6번 항목에 공식 기록됨(open) |
| WR-01: `check_trigger_mode`/`none_kind`에 오타가 들어가도 등록 검증이 안 잡음 | 경고 | 미수정(경고 등급) | 다음에 이 필드를 다루는 계획에서 고려할 사항 |
| WR-02: `confirm()`/`proceed()`가 클라이언트가 보낸 룰북 ID를 캐릭터 실제 룰북과 대조 안 함 | 경고 | 미수정(경고 등급), 이 단계 이전부터 있던 문제이나 룰북이 셋으로 늘며 위험도 상승 | 다음 계획에서 고려할 사항 |
| WR-03: 플레이어 캐릭터의 축 정합성은 등록 시점이 아니라 시험으로만 지켜짐 | 경고 | 미수정(경고 등급) | 다음 계획에서 고려할 사항 |
| WR-04: 화면이 모르는 형태를 조용히 안 그림(위 StatusPane 항목과 동일) | 경고 | 미수정(경고 등급) | 위 참고 |
| WR-05: `depleted_effect_ref`가 안 맞는 형태에도 채워질 수 있음 | 경고 | 미수정(경고 등급), 현재 이 필드를 읽는 코드가 없어 실질 영향 없음 | M1 단계에서 이 필드를 실제로 읽기 시작할 때 함께 고칠 사항 |
| `COVERAGE.md`가 "새 npm 패키지를 설치하지 않는다"고 적었지만 11-06에서 프론트엔드 첫 단위 시험을 위해 `vitest`를 devDependency로 추가함 | 정보 | 문서와 실제가 어긋남(사소) | 시험 도구일 뿐 제품 코드에 영향 없음. 문서만 갱신하면 됨 |

디버트 마커(TBD/FIXME/XXX) 검사: 이 단계가 건드린 파일 전부에서 검색한 결과 없음.

### Gaps Summary

자동 검증이 실패로 판정할 만한 항목은 없습니다. 남은 것은 전부 (1) 이미 계획 문서가
"사람에게 올린다"고 명시한 확인 대기 항목, (2) 이 단계가 스스로 범위 밖으로 정한
항목(남는 세 형태의 실사용), (3) 코드 리뷰가 찾았지만 사람이 이미 "지금은 보류"로
결정한 항목(CR-02와 다섯 경고)입니다. 셋 다 phase 12 이전에 반드시 막아야 하는
차단 사유는 아니지만, 사람 확인 두 가지는 이번 검증에서 자동으로 종결할 수 없어
위에 그대로 올립니다.

---

_Verified: 2026-08-16T16:36:04Z_
_Verifier: Claude (gsd-verifier)_

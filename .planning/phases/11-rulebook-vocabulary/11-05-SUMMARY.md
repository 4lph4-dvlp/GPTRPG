---
phase: 11-rulebook-vocabulary
plan: 05
subsystem: ai
tags: [pydantic, fastapi, react, typescript, action-classifier, prompt-assembly]

# Dependency graph
requires:
  - phase: 11-01
    provides: "여섯 형태 어휘(ResourceAxisForm)와 여덟 칸 StatEntry 관례 — 이 계획이 직접 쓰지는 않지만 phase 11의 baseline이다. 이 계획의 실제 코드 의존은 Phase 3(action_classifier.classify()/Proposal)과 Phase 9-10(웹·CLI 두 호출부가 tier를 소비하는 구조)이다"
provides:
  - "ProposalTier 네 값(single/several/no_check/unclear) — NO_CHECK_SIGNAL 예약 키, Proposal.no_check 필드, Proposal.tier의 명시적 우선순위 계산(unknown_move > candidates > no_check > unclear)"
  - "분류기 지시문이 「안 맞음」과 「필요 없음」을 세 갈래로 명시 — NO_CHECK_SIGNAL을 지시문과 파서가 공유, 빈 무브 목록에서도 예외 없이 조립되고 「목록 없음」을 명시"
  - "웹(routes_actions.py)·CLI(turn_flow.py)·화면(ChatPane.tsx)·타입(types.ts) 네 곳이 같은 커밋에서 네 값 어휘로 이동 — CLI 안내 문구를 「진행합니다」(부정확)에서 「끝납니다」(정직)로 고침"
affects: [11-06, 11-04]

# Actuals (#2632)
actuals:
  tokens: 11575
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Proposal.tier의 계산 순서 자체가 우선순위 문서화 — ①계약위반 ②후보 ③신호 ④나머지, 각 줄에 왜 그 순서인지 주석을 단다(D-11)"
    - "순환 임포트 회피용 지역(함수 내부) 임포트 — action_classifier가 prompt_assembly.build_classifier_prompt를 모듈 최상단에서 쓰므로, 역방향 참조(NO_CHECK_SIGNAL)는 그 함수 몸통 안에서만 임포트한다"
    - "웹/CLI 두 호출부 동시 반영 관례(10-05가 세움)를 이 계획도 지킨다 — routes_actions.py와 turn_flow.py가 Task 3 한 커밋에 같이 들어간다"

key-files:
  created: []
  modified:
    - src/gptrpg/agents/action_classifier.py
    - src/gptrpg/agents/prompt_assembly.py
    - src/gptrpg/web/routes_actions.py
    - src/gptrpg/cli/turn_flow.py
    - frontend/src/api/types.ts
    - frontend/src/panes/ChatPane.tsx
    - tests/test_action_classifier.py
    - tests/test_cli.py
    - tests/test_web_actions.py
    - tests/test_agents_retry.py
    - tests/test_turn_tracer.py

key-decisions:
  - "Proposal.tier 우선순위: unknown_move 흡수가 항상 이긴다(①) → 후보가 있으면 후보 개수(②) → 후보 0개+no_check 신호(③) → 나머지 전부 unclear(④). no_check와 후보가 동시에 오면 후보가 이긴다는 것이 ②가 ③보다 먼저인 이유(RULE-15 adjacency)"
  - "prompt_assembly.build_classifier_prompt가 action_classifier.NO_CHECK_SIGNAL을 함수 몸통 안에서 지역 임포트한다 — action_classifier가 이미 모듈 최상단에서 build_classifier_prompt를 가져다 쓰므로, 모듈 최상단 역방향 임포트는 진짜 순환 임포트가 되어 ImportError가 난다(양방향으로 직접 확인함)"
  - "CLI 안내 문구를 「무브 없음 — 판정 없이 진행합니다」에서 「이번 턴은 판정 없이 여기서 끝납니다」로 고쳤다 — 옛 문구의 '진행합니다'가 서사가 이어진다는 오해를 만들었는데 실제로는 그냥 턴을 끝낼 뿐이었다. unclear/no_check 두 갈래 모두 이 계획 시점에서는 같은 보수적 화면(다시 쓰기)으로 간다는 것이 이 계획의 must_haves 백스톱 진술이고, 11-06이 no_check를 실제 서사 경로로 연다"
  - "RULE-15를 Complete로 표시하지 않았다 — 이 계획은 그릇(플랫폼 능력: 네 갈래 tier, no_check 신호, 빈 목록 프롬프트)만 만들었다. 실제 빈 트리거 목록을 선언한 룰북(Cairn)이 아직 없어 실증이 안 됐고(11-04 몫), no_check가 실제 서사 경로로 가는 것도 아직이다(11-06 몫). REQUIREMENTS.md를 In Progress로 유지하고 두 가지 남은 일을 명시했다"
  - "[deviation, Rule 1] tests/test_agents_retry.py와 tests/test_turn_tracer.py는 이 계획의 files_modified 목록에 없었지만, classify()를 직접 불러 proposal.tier == \"none\"을 단언하고 있어 Task 1의 개명만으로 즉시 깨졌다 — \"unclear\"로 고쳤다. CLI/웹 소비 코드(Task 3)와는 무관하게 Task 1 하나만으로 깨지는 실패였다"

patterns-established:
  - "지시문과 파서가 예약 신호 문자열을 상수 하나(NO_CHECK_SIGNAL)로 공유 — 지시문이 실수로 다른 문자열을 쓰는 사고를 코드로 막는다"

requirements-completed: []

coverage:
  - id: D1
    description: "분류기 결과가 네 갈래로 갈린다 — single(후보1)/several(후보2+)/no_check(판정 불필요 신호)/unclear(못 알아들음). ProposalTier 타입이 이 네 값만 허용한다"
    requirement: "RULE-15"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py::test_zero_candidates_yields_unclear_tier, ::test_one_candidate_yields_single_tier, ::test_two_candidates_yields_several_tier, ::test_no_check_signal_yields_no_check_tier"
        status: pass
      - kind: other
        ref: "python -c \"import typing; from gptrpg.agents.action_classifier import ProposalTier; print(sorted(typing.get_args(ProposalTier)))\" -> ['no_check', 'several', 'single', 'unclear']"
        status: pass
    human_judgment: false
  - id: D2
    description: "목록 밖 무브 이름을 흡수한 경우(unknown_move가 채워진 경우)의 tier는 반드시 unclear다 — no_check 신호가 같이 왔어도 마찬가지(계약 위반이 신호보다 우선)"
    requirement: "RULE-15"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py::test_classify_absorbs_unknown_move_into_unclear_tier_proposal, ::test_unknown_move_absorption_never_yields_no_check_tier"
        status: pass
    human_judgment: false
  - id: D3
    description: "제공자 호출이 두 번 다 실패한 경우의 tier도 unclear다 — no_check 기본값 False가 그대로 남아 응답 없음이 '판정 없이 진행해도 됨'으로 새지 않는다(T-11-17)"
    requirement: "RULE-15"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py::test_provider_failure_after_retry_yields_unclear_tier, ::test_provider_failure_yields_unclear_not_no_check"
        status: pass
    human_judgment: false
  - id: D4
    description: "모델이 no_check 신호와 후보를 동시에 낸 응답에서 tier는 후보 기반 값(single/several)으로 정해진다 — 후보가 신호를 이긴다(RULE-15 adjacency)"
    requirement: "RULE-15"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py::test_candidate_wins_when_no_check_signal_arrives_together"
        status: pass
    human_judgment: false
  - id: D5
    description: "판정 트리거 목록이 빈 룰북에서 분류기 프롬프트가 무브 목록 자리를 「목록 없음」으로 조립하고, 그 상태에서 classify()가 예외 없이 돈다"
    requirement: "RULE-15"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py::test_classifier_prompt_handles_empty_move_list, ::test_classifier_prompt_mentions_the_no_check_signal"
        status: pass
      - kind: other
        ref: "python -c \"from gptrpg.agents.prompt_assembly import _format_moves; print(repr(_format_moves(())))\" -> 빈 문자열 아님, '목록이 없다' 명시"
        status: pass
    human_judgment: false
  - id: D6
    description: "후보가 여럿일 때 화면과 CLI가 모델이 낸 순서를 그대로 유지하고 재정렬하지 않으며, 시스템 제안(suggestion)은 항상 첫 번째 후보다 — 이 계획이 새로 만든 동작이 아니라 기존 동작이 회귀하지 않았음을 확인"
    requirement: "RULE-15"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py::test_candidate_wins_when_no_check_signal_arrives_together (candidates[0]), ::test_markdown_code_fence_wrapped_json_array_still_parses, ::test_prose_before_and_after_json_array_still_parses"
        status: pass
    human_judgment: false
  - id: D7
    description: "웹과 CLI 두 호출부가 같은 커밋에서 같은 tier 어휘로 옮겨갔다 — 한쪽만 바뀐 상태로 이 계획이 끝나지 않았다(T-11-18)"
    requirement: "RULE-15"
    verification:
      - kind: other
        ref: "git show --stat 9e23c71 — src/gptrpg/web/routes_actions.py와 src/gptrpg/cli/turn_flow.py가 같은 커밋에 있음"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py::test_no_check_tier_ends_turn_without_indexerror"
        status: pass
    human_judgment: false
  - id: D8
    description: "이 계획 시점에서 no_check는 아직 「판정 없이 이야기가 이어지는」 화면으로 가지 않고 unclear와 같은 화면(다시 쓰기)으로 간다 — 오늘의 동작과 같은 보수적 상태이며, 11-06이 그 경로를 연다"
    requirement: "RULE-15"
    verification:
      - kind: other
        ref: "src/gptrpg/cli/turn_flow.py의 `if tier in (\"unclear\", \"no_check\")` 단일 분기, frontend/src/panes/ChatPane.tsx의 `proposal.tier === \"unclear\" || proposal.tier === \"no_check\"` 단일 분기"
        status: pass
    human_judgment: false

# Metrics
duration: ~20min
completed: 2026-08-16
status: complete
---

# Phase 11 Plan 05: 「굴릴 필요 없음」을 「못 알아들었음」에서 떼어낸다 Summary

**분류기 tier가 3값에서 4값(single/several/no_check/unclear)으로 넓어지고 NO_CHECK_SIGNAL 예약 신호가 지시문·파서·웹·CLI·화면 다섯 곳에서 일관되게 소비된다 — CLI 안내 문구도 "진행합니다"(부정확)에서 "끝납니다"(정직)로 함께 고쳤다**

## Performance

- **Duration:** ~20분
- **Completed:** 2026-08-16
- **Tasks:** 3 (전부 자동 실행, 체크포인트 없음)
- **Files modified:** 11개 (신규 파일 없음)

## Accomplishments

- `ProposalTier`가 `Literal["single", "several", "no_check", "unclear"]`로 넓어졌다 — 옛 `"none"`을 폐기가 아니라 **개명하며 뜻을 좁혔다**(D-11). `Proposal.tier`는 이제 명시적 4단계 우선순위로 계산된다: ① `unknown_move` 흡수(목록 밖 이름)는 무조건 `unclear` ② 후보가 있으면 개수로 `single`/`several`(신호와 동시에 와도 후보가 이긴다) ③ 후보 0개+`no_check` 신호면 `no_check` ④ 나머지 전부 `unclear`
- `NO_CHECK_SIGNAL = "no_check"` 상수와 `Proposal.no_check: bool = False` 필드가 신설됐다 — 모델이 JSON 배열 안에 `{"no_check": true}` 원소를 내면 그것을 신호로 읽는다. `_parse_candidates`가 `(candidates, no_check)` 짝을 돌려주도록 바뀌었고, "move 키 없는 원소는 건너뛴다"는 판정보다 신호 원소를 먼저 본다
- 분류기 지시문(`build_classifier_prompt`)이 "어느 것도 안 맞으면 하나도 내지 말 것" 한 문장을 세 갈래(①어울리는 무브 ②판정 불필요 신호 ③무슨 말인지 모르겠음)로 명시적으로 갈랐다. 신호 표기는 `action_classifier.NO_CHECK_SIGNAL`을 함수 내부에서 지역 임포트해 가져온다 — 지시문과 파서가 다른 문자열을 쓰는 사고를 코드로 막는다
- `_format_moves(())`(빈 무브 목록)가 빈 문자열 대신 "이 룰북에는 미리 정해 둔 판정 목록이 없다"는 명시적 문장을 낸다 — 「목록이 잘려서 안 왔나」로 읽히지 않는다(RULE-15 empty, D-12 `gm_discretion`)
- 웹(`routes_actions.py`)·CLI(`turn_flow.py`)·화면(`ChatPane.tsx`)·타입(`types.ts`) 네 곳이 **같은 커밋**(Task 3)에서 네 값 어휘로 옮겨갔다 — 이 저장소의 알려진 실패 모양(10-05가 세운 "웹/CLI 동시 반영" 관례)을 지켰다. CLI의 안내 문구가 "무브 없음 — 판정 없이 진행합니다"(부정확, 서사가 이어진다는 오해)에서 "이번 턴은 판정 없이 여기서 끝납니다"(정직)로 바뀌었다

## Task Commits

각 태스크를 개별 커밋했다:

1. **Task 1: 분류기 반환 계약을 네 갈래로 넓힌다** — `c5d4dcf` (feat)
2. **Task 2: 분류기 지시문에서 「안 맞음」과 「필요 없음」을 분리한다** — `94527ba` (feat)
3. **Task 3: 웹·CLI·화면 세 곳이 같은 커밋에서 새 tier 어휘로 옮겨 간다** — `9e23c71` (feat)

**Plan metadata:** 이 커밋(SUMMARY.md 등)

## Files Created/Modified

- `src/gptrpg/agents/action_classifier.py` - `ProposalTier` 4값, `NO_CHECK_SIGNAL` 상수, `Proposal.no_check` 필드, `Proposal.tier` 우선순위 재작성, `_parse_candidates`가 `(candidates, no_check)` 반환
- `src/gptrpg/agents/prompt_assembly.py` - `build_classifier_prompt`의 `permanent` 문자열을 3갈래로 재작성, `_format_moves(())` 빈 목록 명시 문구
- `src/gptrpg/web/routes_actions.py` - 도크스트링만 갱신(코드 변경 없음 — `proposal.tier`를 그대로 통과시키던 기존 동작이 새 4값에도 그대로 맞는다)
- `src/gptrpg/cli/turn_flow.py` - `if tier == "none"` → `if tier in ("unclear", "no_check")`, 안내 문구 정직하게 교체
- `frontend/src/api/types.ts` - `DeclareResponse.tier` 타입을 4값으로 확장
- `frontend/src/panes/ChatPane.tsx` - `proposal.tier === "none"` → `proposal.tier === "unclear" || proposal.tier === "no_check"`
- `tests/test_action_classifier.py` - 기존 tier 시험 전체를 `"none"`→`"unclear"`로 재고정, `no_check`/프롬프트 신규 시험 8건 추가
- `tests/test_cli.py` - tier 문자열 단언 갱신, `test_no_check_tier_ends_turn_without_indexerror` 신규
- `tests/test_web_actions.py` - tier 문자열 단언 갱신, `test_declare_no_check_signal_returns_tier_no_check` 신규
- `tests/test_agents_retry.py` - `proposal.tier == "none"` → `"unclear"`(계획 files_modified 목록 밖, Task 1 단독으로 깨진 시험)
- `tests/test_turn_tracer.py` - `proposal.tier == "none"` → `"unclear"`(동일 사유)

## Decisions Made

- **`Proposal.tier` 우선순위 ①계약위반 ②후보 ③신호 ④나머지** — 순서 자체가 문서이자 계약이다. 각 단계에 왜 그 순서인지 주석을 달아 향후 다섯 번째 갈래가 추가돼도 순서 규율이 깨지지 않게 했다.
- **순환 임포트 회피** — `action_classifier.py`가 모듈 최상단에서 `prompt_assembly.build_classifier_prompt`를 가져다 쓰므로, `prompt_assembly.py`가 `NO_CHECK_SIGNAL`을 되가져오는 것은 모듈 최상단에서 하면 진짜 순환 임포트가 된다(양방향 순서 둘 다 직접 실행해 확인). 함수 몸통 안에서의 지역 임포트로 해결했다 — 호출 시점에는 두 모듈 다 이미 완전히 로드돼 있다.
- **CLI 안내 문구를 정직하게 교체** — "판정 없이 진행합니다"는 서사가 이어진다는 오해를 만드는데 실제로는 그냥 턴을 끝낸다. "이번 턴은 판정 없이 여기서 끝납니다"로 바꿨다. 이 계획 시점에서는 `unclear`와 `no_check` 둘 다 같은 문구로 끝난다는 것이 must_haves의 명시적 백스톱 진술이다 — 11-06이 `no_check`를 실제 서사 경로로 연다.
- **RULE-15를 Complete로 표시하지 않았다** — 이 계획은 3개 계획(11-04/05/06)에 걸친 요구사항의 "그릇"(플랫폼 능력)만 만들었다. REQUIREMENTS.md를 `In Progress`로 유지하고 남은 두 가지(실제 빈 트리거 룰북 실증은 11-04, `no_check`의 실제 서사 경로는 11-06)를 명시했다. `requirements mark-complete`를 실행하지 않았다 — 11-03이 문서화한 "In Progress 상태 요구사항의 자동 전환 불가" 도구 한계와도 무관하게, 애초에 이 계획 하나로 완료 처리하면 안 되는 요구사항이었다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `tests/test_agents_retry.py`·`tests/test_turn_tracer.py`가 Task 1 단독으로 깨짐**
- **Found during:** Task 1 완료 후 전체 시험(`uv run pytest -q`) 실행 중
- **Issue:** 이 두 파일은 이 계획의 `files_modified` 목록에 없었지만, `classify()`를 직접 불러 `proposal.tier == "none"`을 단언하고 있었다 — `ProposalTier`의 `"none"`→`"unclear"` 개명만으로 즉시 실패했다(Task 3의 웹/CLI 소비 코드와는 무관, Task 1 하나만으로 발생하는 실패)
- **Fix:** 두 단언을 `"unclear"`로 고쳤다(그 외 로직·구조는 변경 없음)
- **Files modified:** `tests/test_agents_retry.py`, `tests/test_turn_tracer.py`
- **Verification:** `uv run pytest tests/test_agents_retry.py tests/test_turn_tracer.py -q` 통과
- **Committed in:** `c5d4dcf`(Task 1 커밋에 함께 포함)

---

**Total deviations:** 1 auto-fixed (bug)
**Impact on plan:** 계획서가 미처 못 짚은 두 시험 파일을 고쳤을 뿐, 새 기능이나 범위 확장은 없다.

## Issues Encountered

**계획 acceptance criteria의 문자열 스캔이 무관한 기존 값과 충돌.** Task 3의 acceptance criteria가 4개 파일에서 리터럴 `"none"` 문자열이 0개인지 파이썬 정규식으로 검사하는데, `frontend/src/api/types.ts`에는 이 계획과 완전히 무관한 `StatEntry.form`(`ResourceAxisForm`, RULE-11/12, 11-01·11-03이 만든 여섯 형태 어휘 중 하나)에도 `"none"`이라는 **다른 뜻의** 리터럴 값이 이미 있다. 이 값은 건드리지 않았다 — 삭제하면 RULE-12(「이 개념을 안 쓴다」 선언)가 깨진다. 내가 새로 쓴 문서 주석에서는 `"none"` 리터럴 인용을 전부 피해 스캔 결과를 4건에서 1건(그 기존 값 하나)으로 줄였다. 이 1건은 계획의 검사 스크립트가 "옛 tier 값이 남아 있다"고 오판할 수 있는 지점이지만, 실제로는 무관한 필드다.

## User Setup Required

None - 외부 서비스 설정 불필요.

## Next Phase Readiness

- 이 계획이 만든 것은 **플랫폼 능력**이다 — 네 갈래 tier와 `no_check` 신호 배관이 지시문부터 화면까지 관통했다. 실제 룰북 데이터나 실제 사용자 경험은 아직 다음 두 계획 몫이다.
- **11-04**가 세 번째 룰북(Cairn)을 투입하면서 실제로 빈 트리거 목록(`move_triggers=()`)을 선언해야 RULE-15의 "빈 목록이 정상값" 진술이 실제 데이터로 실증된다.
- **11-06**이 `no_check` tier를 실제로 "판정 없이 서사가 이어지는" 화면으로 열어야 한다 — 지금은 `unclear`와 완전히 같은 보수적 화면(다시 쓰기)이다. `frontend/src/labels.ts`에 `no_check` 전용 문구를 아직 추가하지 않은 것도 11-06 몫이다(계획이 명시적으로 이번 태스크 범위 밖으로 뒀다).
- 블로커 없음 — Phase 11의 다음 계획(11-04 또는 11-06, wave 순서에 따라)으로 바로 이어갈 수 있다.

## Self-Check: PASSED

- 파일 존재: `src/gptrpg/agents/action_classifier.py`, `src/gptrpg/agents/prompt_assembly.py`, `src/gptrpg/web/routes_actions.py`, `src/gptrpg/cli/turn_flow.py`, `frontend/src/api/types.ts`, `frontend/src/panes/ChatPane.tsx`, `tests/test_action_classifier.py`, `tests/test_cli.py`, `tests/test_web_actions.py`, `tests/test_agents_retry.py`, `tests/test_turn_tracer.py` 전부 확인됨
- 커밋 존재: `c5d4dcf`, `94527ba`, `9e23c71` 전부 `git log --oneline --all`에서 확인됨
- 마감 전 재검증: `uv run pytest -q` 879 passed, `uv run lint-imports` 4 kept/0 broken, `cd frontend && npx tsc --noEmit` 종료 코드 0

---
*Phase: 11-rulebook-vocabulary*
*Completed: 2026-08-16*

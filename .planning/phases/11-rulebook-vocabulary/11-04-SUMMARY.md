---
phase: 11-rulebook-vocabulary
plan: 04
subsystem: rules-core
tags: [rulebook-registration, cairn, licensing, trigger-mode, optional-field]

# Dependency graph
requires:
  - phase: 11-01
    provides: "ResourceAxisDecl/여덟 칸 StatEntry, 여섯 표현 형태 어휘(D-13)"
  - phase: 11-02
    provides: "validate_grade_bands/validate_entity_axes/validate_move_stats + validate_registered_rulebooks 등록 게이트"
provides:
  - "src/gptrpg/rulebooks/cairn.py — 세 번째 룰북(CC BY-SA 4.0), 플랫폼 그릇 변경 없이 등록"
  - "Rulebook.check_trigger_mode(declared_list/no_dice/gm_discretion) + validate_trigger_mode — 빈 트리거 목록의 두 갈래를 룰북이 명시적으로 선택(D-12)"
  - "D20_ROLL_UNDER 판정 방식 이름 상수 — 계산기는 아직 없고 CommandRejected로 눈에 보이게 멈춘다는 것이 회귀 시험으로 못박혀 있다(declare-only)"
  - "MoveDecl.default_stat: str | None — '그때그때 고른다'는 정상값(11-02 편차 해소)"
affects: [11-05, 11-06, 11-07, phase-12]

# Actuals (#2632)
actuals:
  tokens: 11221
  tasks: 3
  commits: 6

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "판별 필드 + 폼별 선택 페이로드 관례(GradeBand/ResourceAxisDecl)를 CheckTriggerMode에도 동일 적용 — 세 값짜리 리터럴 + move_count 대조 검증"
    - "필수 필드 추가 시 기존 테스트 전용 Rulebook(...) 호출부 전수 조사(grep) — Task 1이 등록된 두 룰북 말고도 test_session_actor.py/test_web_characters.py의 ad-hoc 호출부까지 놓치지 않고 갱신"

key-files:
  created:
    - src/gptrpg/rulebooks/cairn.py
  modified:
    - src/gptrpg/rules_core/rulebook.py
    - src/gptrpg/rulebooks/__init__.py
    - src/gptrpg/rulebooks/moves.py
    - src/gptrpg/rulebooks/dungeonworld_like.py
    - src/gptrpg/rulebooks/openquest.py
    - src/gptrpg/agents/prompt_assembly.py
    - LICENSES.md
    - tests/test_rulebook.py
    - tests/test_session_actor.py
    - tests/test_web_characters.py
    - tests/test_action_classifier.py

key-decisions:
  - "Task 0 체크포인트(declare-only, 사용자 승인): Cairn의 d20 계산기는 이번 단계에 안 만든다 — 선언·등록까지만 넣고, 계산기 부재는 CommandRejected('알 수 없는 판정 방식')로 눈에 보이게 멈춘다. D20_ROLL_UNDER 상수 도크스트링에 이 사실을 명시했다"
  - "접어넣은 todo(default_stat optional) 처리 순서를 계획서 지시대로 지켰다 — Cairn을 먼저 등록하고 벽에 부딪히는지 확인한 뒤(부딪히지 않음, Cairn은 애초에 무브 목록이 없어 이 필드 자체가 생기지 않는다) default_stat을 str | None로 넓혔다. 던전월드류 두 무브(defy_danger/aid_or_interfere)를 DEX/CHA 근사에서 원래 의도(None, '그때그때 고른다')로 되돌렸다"
  - "_GAPPED_RULEBOOK(test_session_actor.py)과 test_web_characters.py의 두 ad-hoc Rulebook(...) 호출부에 check_trigger_mode='no_dice'를 채웠다 — 계획서 <files> 목록에 test_web_characters.py는 없었지만 check_trigger_mode가 기본값 없는 필수 필드가 되면서 구조적으로 불가피했다(Rule 3)"

patterns-established:
  - "판정 방식 이름 상수(TWO_D6/D100_ROLL_UNDER/D20_ROLL_UNDER)에 '계산기가 아직 없으면 CommandRejected로 멈춘다'는 사실을 도크스트링에 명시하는 관례 — 이름만 있고 계산기 없는 상태를 조용한 구멍이 아니라 문서화된 설계로 남긴다"

requirements-completed: [RULE-15, RULE-11, QUAL-03]

coverage:
  - id: D1
    description: "Cairn(CC BY-SA 4.0)이 ResourceAxisDecl/StatEntry/GradeBand/Entity 그릇의 칸을 하나도 늘리지 않고 데이터 파일 하나로 등록된다(D-14) — git diff --stat src/gptrpg/rules_core/entities.py가 비어 있다"
    requirement: "RULE-11"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_third_rulebook_registers_without_platform_changes"
        status: pass
      - kind: other
        ref: "git diff --stat src/gptrpg/rules_core/entities.py (빈 출력 확인)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Cairn의 named_slots 형태(10칸 소지품)가 실제 데이터로 등록되고 예시 개체(CAIRN_EXAMPLE_ADVENTURER)가 등록 검증을 통과한다 — RULE-11의 여섯 형태 중 named_slots가 처음으로 실제 룰북 데이터로 실증됨(2/6, 남은 넷은 후속 계획 몫)"
    requirement: "RULE-11"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_cairn_inventory_axis_has_ten_named_slots"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_cairn_example_adventurer_matches_declared_axes"
        status: pass
    human_judgment: false
  - id: D3
    description: "Cairn의 판정 트리거 목록이 빈 튜플이고 get_moves('cairn')이 예외 없이 ()를 돌려준다 — 빈 목록이 정상값(RULE-15)이며 check_trigger_mode='gm_discretion'으로 그 이유를 룰북이 명시한다(D-12)"
    requirement: "RULE-15"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_cairn_move_list_is_empty_and_get_moves_returns_it"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_cairn_declares_gm_discretion_mode"
        status: pass
    human_judgment: false
  - id: D4
    description: "빈 판정 트리거 목록이 두 갈래(no_dice/gm_discretion)로 갈리고, 목록 길이와 check_trigger_mode가 어긋나면 InvalidTriggerMode로 등록이 거부된다(D-12) — Rulebook.check_trigger_mode가 resource_axes와 같은 이유로 기본값 없는 필수 필드"
    requirement: "RULE-15"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_declared_list_mode_requires_a_non_empty_move_list"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_empty_move_list_is_valid_with_gm_discretion_mode"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_empty_move_list_is_valid_with_no_dice_mode"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_non_empty_move_list_rejects_no_dice_mode"
        status: pass
      - kind: unit
        ref: "tests/test_rulebook.py#test_rulebook_without_check_trigger_mode_raises_type_error"
        status: pass
    human_judgment: false
  - id: D5
    description: "Cairn의 등급 밴드(통과/실패 둘뿐)가 11-02의 가려짐·구멍 검증을 통과하고, 기존 두 룰북도 계속 통과한다(QUAL-03 회귀)"
    requirement: "QUAL-03"
    verification:
      - kind: unit
        ref: "tests/test_rulebook.py#test_cairn_grade_bands_pass_validation"
        status: pass
      - kind: integration
        ref: "uv run pytest -q (895 passed)"
        status: pass
    human_judgment: false
  - id: D6
    description: "LICENSES.md에 Cairn CC BY-SA 4.0 항목이 OpenQuest(CC BY 4.0)와 같은 3단 구조로 추가되고, ShareAlike 조건이 다르다는 것이 글로 적혀 있다"
    verification:
      - kind: other
        ref: "grep -c 'CC BY-SA 4.0'/'ShareAlike'/'src/gptrpg/rulebooks/cairn.py'/'cairnrpg.com' LICENSES.md (전부 1건 이상)"
        status: pass
    human_judgment: false
  - id: D7
    description: "접어넣은 todo — MoveDecl.default_stat이 str | None으로 넓어지고, validate_move_stats가 None을 건너뛰며(구멍 검사는 유지), prompt_assembly가 None일 때 '상황에 맞게 고른다'로 렌더링하고, 던전월드류 두 무브가 원래 의도(None)로 되돌아간다"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py#test_format_moves_renders_none_default_stat_as_situational_choice"
        status: pass
      - kind: integration
        ref: "uv run pytest -q (895 passed, defy_danger/aid_or_interfere 관련 기존 시험 전부 그대로 통과 — moves[i].default_stat 동적 참조라 하드코딩 값 의존 없음)"
        status: pass
    human_judgment: false
  - id: D8
    description: "Cairn이 default_stat 벽('고정 능력치 요구')에 부딪히는지에 대한 정직한 실증 기록 — 부딪히지 않았다(Cairn은 무브 목록 자체가 없어 이 필드가 생기지 않음). 벽에 실제로 부딪힌 것은 여전히 던전월드류 두 무브뿐이라는 것을 SUMMARY 본문(아래 Deviations)에 근거와 함께 기록"
    verification: []
    human_judgment: true
    rationale: "이것은 '플랫폼 그릇을 안 고치고 데이터로 넣는다'는 이 계획의 전제에 대한 정직성 판단이다 — 자동 시험으로 참/거짓을 가릴 수 있는 항목이 아니라, 기록된 근거(Cairn의 MOVE_CATALOGS 항목이 빈 튜플이라는 사실)가 실제로 정직한 설명인지 사람이 확인해야 한다."
  - id: D9
    description: "declare-only 결정(Task 0)의 안전 근거인 '계산기가 없는 판정 방식으로 실제 판정을 시도하면 조용히 대체되지 않고 CommandRejected로 눈에 보이게 멈춘다'는 것이 회귀 시험으로 못박혀 있다 — 오케스트레이터 지적으로 발견된 간극(도크스트링은 시험이 있다고 주장했으나 실제로는 없었다) 해소"
    verification:
      - kind: unit
        ref: "tests/test_session_actor.py#test_rulebook_with_no_registered_resolver_is_rejected_not_silently_substituted"
        status: pass
      - kind: unit
        ref: "동일 시험이 CommandRejected 메시지에 D20_ROLL_UNDER 판정 방식 이름이 포함되는지, 그리고 거부 후 사건 기록에 아무것도 안 쌓이는지(_read_events == [])까지 확인"
        status: pass
    human_judgment: false

# Metrics
duration: ~50min (Task 0 체크포인트 대기 시간 제외)
completed: 2026-08-16
status: complete
---

# Phase 11 Plan 04: 세 번째 룰북(Cairn)을 데이터로, 빈 트리거 목록의 두 갈래를 룰북이 고르게 Summary

**Cairn(CC BY-SA 4.0)이 그릇 칸을 하나도 안 늘리고 등록됐고(D-14), 빈 판정 트리거 목록이 `no_dice`/`gm_discretion` 두 갈래로 갈려 룰북이 명시적으로 고른다(D-12) — 접어넣은 todo로 `MoveDecl.default_stat`도 옵셔널로 넓어져 던전월드 두 무브가 원래 의도로 돌아갔다**

## Performance

- **Duration:** ~50분 (Task 0 결정 관문 — `declare-only` 승인 — 대기 시간 제외)
- **Completed:** 2026-08-16
- **Tasks:** 3 (+ Task 0 결정 관문, 코드 변경 없음) + 접어넣은 todo 1건
- **Files modified:** 14개 (신규 파일 1개: `src/gptrpg/rulebooks/cairn.py`)

## Accomplishments

- **Task 0(체크포인트, 사용자 승인 `declare-only`):** Cairn의 d20 계산기는 이번 단계에 안 만든다. `D20_ROLL_UNDER` 이름만 신설했고, 실제로 굴리려 하면 `session_actor.actor.CommandRejected`("알 수 없는 판정 방식")로 눈에 보이게 멈춘다 — 조용한 구멍이 아니라 문서화된 설계다. **이 사실 자체가 회귀 시험(`test_rulebook_with_no_registered_resolver_is_rejected_not_silently_substituted`)으로 못박혀 있다** — 최초 제출 시 도크스트링만 이 사실을 주장하고 시험이 없었던 간극을 오케스트레이터가 지적해 이번 rework에서 추가했다(아래 Deviations 참조).
- **D-12(빈 트리거 목록의 두 갈래):** `CheckTriggerMode`(`declared_list`/`no_dice`/`gm_discretion`) 리터럴과 `Rulebook.check_trigger_mode` 필수 필드, `InvalidTriggerMode` 예외, `validate_trigger_mode(mode, move_count)`를 신설했다. `declared_list`인데 목록이 비었거나 `no_dice`/`gm_discretion`인데 목록이 차 있으면 등록이 거부된다. 던전월드류·OpenQuest는 `declared_list`.
- **Cairn 등록(D-14):** `src/gptrpg/rulebooks/cairn.py` 신설 — STR/DEX/WIL/Hit Protection(`numeric`) + Inventory(`named_slots`, `slot_count=10`), 통과/실패 두 `GradeBand`, `check_trigger_mode="gm_discretion"`(고정 무브 목록 없음), `CAIRN_EXAMPLE_ADVENTURER`(자체 작성 예시, SRD 유래 아님). `MOVE_CATALOGS["cairn"] = ()`로 `get_moves("cairn")`이 예외 없이 빈 튜플을 돌려준다. `git diff --stat src/gptrpg/rules_core/entities.py`가 비어 있다 — `ResourceAxisDecl`/`StatEntry`/`GradeBand`/`Entity` 어느 그릇도 칸이 안 늘었다.
- **LICENSES.md:** OpenQuest 절과 같은 3단 구조(담고 있는 파일/필수 첨부 문구/ShareAlike 주의)로 Cairn CC BY-SA 4.0 항목을 추가했다. ShareAlike 조건이 OpenQuest의 CC BY 4.0과 다르다는 것(파생물은 같은 라이선스로만 재배포 가능)을 명시했다.
- **접어넣은 todo(default_stat optional):** Cairn을 먼저 등록하고 벽에 부딪히는지 확인한 뒤(아래 Deviations 참조) `MoveDecl.default_stat: str | None`로 넓히고, `validate_move_stats`가 `None`을 검사에서 건너뛰게(구멍 검사는 유지) 하고, `prompt_assembly._format_moves`가 `None`일 때 "상황에 맞게 고른다"로 렌더링하게 했다. 던전월드류 `defy_danger`/`aid_or_interfere`의 `default_stat`을 `DEX`/`CHA` 근사에서 원래 의도(`None`)로 되돌렸다.

## Task Commits

각 태스크를 개별 커밋했다:

1. **Task 1: 판정 트리거 목록이 빈 경우의 두 갈래를 룰북이 고르게 한다 (D-12)** — `9e66374` (test)
2. **Task 2: Cairn 룰북을 데이터 파일 하나로 넣는다** — `f4a1fc2` (feat)
3. **Task 3: Cairn 라이선스 표기를 LICENSES.md에 추가한다** — `e1b1039` (docs)
4. **접어넣은 todo: default_stat 옵셔널화** — `7fd2f03` (fix)
5. **REQUIREMENTS.md 진행 노트 갱신** — `a7ff772` (docs)
6. **rework: declare-only 안전 근거 회귀 시험 신설** — `a738810` (test)

**Plan metadata:** 이 커밋 (SUMMARY.md 등)

## Files Created/Modified

- `src/gptrpg/rulebooks/cairn.py` (신규) - Cairn SRD 선언(CC BY-SA 4.0) — `CAIRN_ID`/`CAIRN_GRADE_BANDS`/`CAIRN_RESOURCE_AXES`/`CAIRN`/`CAIRN_EXAMPLE_ADVENTURER`
- `src/gptrpg/rules_core/rulebook.py` - `D20_ROLL_UNDER` 상수, `CheckTriggerMode` 리터럴, `Rulebook.check_trigger_mode` 필수 필드, `InvalidTriggerMode` 예외, `validate_trigger_mode()`, `validate_move_stats`가 `None`을 건너뛰도록 확장. `D20_ROLL_UNDER` 도크스트링이 이제 실제 회귀 시험 함수 이름을 가리킨다(rework)
- `src/gptrpg/rulebooks/__init__.py` - `RULEBOOKS`/`_REGISTERED_ENTITIES_FOR_AXIS_CHECK`에 Cairn 추가, `validate_registered_rulebooks()`에 네 번째 검사(`validate_trigger_mode`) 연결
- `src/gptrpg/rulebooks/moves.py` - `MOVE_CATALOGS["cairn"] = ()`, `MoveDecl.default_stat: str | None`, `defy_danger`/`aid_or_interfere`를 `None`으로 되돌림
- `src/gptrpg/rulebooks/dungeonworld_like.py` / `openquest.py` - `Rulebook(...)`에 `check_trigger_mode="declared_list"` 추가
- `src/gptrpg/agents/prompt_assembly.py` - `_format_moves`가 `default_stat is None`일 때 "상황에 맞게 고른다"로 렌더링
- `LICENSES.md` - `## Cairn (CC BY-SA 4.0)` 절 신설
- `tests/test_rulebook.py` - D-12(5건)·Cairn(7건) 시험 신설, 기존 ad-hoc `Rulebook(...)` 호출부에 `check_trigger_mode` 보강
- `tests/test_session_actor.py` - `_GAPPED_RULEBOOK`에 `check_trigger_mode="no_dice"` 추가. `_NO_RESOLVER_RULEBOOK`(시험 전용, `D20_ROLL_UNDER` 선언) + `test_rulebook_with_no_registered_resolver_is_rejected_not_silently_substituted` 신설(rework) — 계산기 없는 판정 방식이 `CommandRejected`로 거부되고 사건 기록에 아무것도 안 쌓이는 것을 확인
- `tests/test_web_characters.py` - ad-hoc `Rulebook(...)` 호출부 2곳에 `check_trigger_mode="no_dice"` 추가(계획 `<files>` 목록 밖, Rule 3)
- `tests/test_action_classifier.py` - `test_format_moves_renders_none_default_stat_as_situational_choice` 신설
- `.planning/todos/completed/2026-08-15-move-default-stat-optional.md` - `pending/`에서 이동, Resolved 절 추가
- `.planning/REQUIREMENTS.md` - RULE-11/RULE-15 진행 노트를 Cairn 실증 결과로 갱신(체크박스는 `[ ]` 유지 — 아직 완전히 안 끝남)

## Decisions Made

- **Task 0(D-03류 결정 관문, 사용자 승인 `declare-only`):** Cairn의 d20 계산기는 이번 단계에 안 만든다. 이유: 이 단계의 목적(그릇+선언이 플랫폼 코드를 안 고치고 등록되는가)이 계산기 없이도 전부 확인되고, Cairn은 애초에 고정 판정 목록이 없어 이번 단계 경로로는 주사위를 굴릴 자리까지 가지 않는다. 못 굴리는 상태는 `CommandRejected`로 눈에 보이게 거부되고 이미 시험(`test_rulebook_with_incomplete_grade_bands_is_rejected_not_a_raw_traceback`류 패턴)이 이 방어선을 지킨다.
- **`_GAPPED_RULEBOOK`/`test_web_characters.py`의 ad-hoc `Rulebook(...)` 호출부는 `check_trigger_mode="no_dice"`로 채웠다** — 이 픽스처들은 `MOVE_CATALOGS`에 항목이 없어(무브 목록 자체가 없음) `no_dice`가 뜻에 가장 가깝고, 어차피 `validate_registered_rulebooks()`를 지나가지 않는 런타임 전용 픽스처라 등록 검증에는 걸리지 않는다.
- **접어넣은 todo 처리 순서를 계획서 지시대로 지켰다:** 먼저 Cairn을 원래 계획대로 넣고, 그 다음 벽에 부딪히는지 확인했다(아래 Deviations 참조). 부딪히지 않았다는 것을 확인한 뒤에야 `default_stat`을 옵셔널로 바꿨다.

## Deviations from Plan

### 접어넣은 todo — Cairn 벽 실증 결과 (정직하게 기록)

**Cairn이 `default_stat` 벽에 부딪혔는가 — 아니다.** Cairn 자체는 SRD 원문에 고정 무브/행동
목록이 없다(`MOVE_CATALOGS["cairn"] = ()`, `check_trigger_mode="gm_discretion"`) — 그래서
Cairn에는 애초에 `MoveDecl.default_stat`이라는 필드 자리 자체가 하나도 생기지 않는다.
이 벽에 실제로 부딪힌 것은 여전히 던전월드류의 두 무브(`defy_danger`/`aid_or_interfere`)뿐이고,
이는 11-02에서 이미 발견된 편차였다.

**이 결과가 「플랫폼 그릇을 안 고치고 데이터로 넣는다」는 이 계획의 전제를 증명하는 것은
아니다** — Cairn의 설계(재량 판정 모드, 고정 목록 없음)가 이 특정 벽을 구조적으로 우회한
것이지, 플랫폼이 이 문제를 미리 해결해 둔 상태였던 것은 아니다. 던전월드류 두 무브의
부채는 Cairn을 넣는 것과 무관하게 그대로 남아 있었고, 이번 todo가 그 부채를 별도로 갚았다.
`default_stat`을 옵셔널로 바꾼 것은 Cairn 검증에서 나온 필수 요구가 아니라, 11-02가 이미
발견해 둔 편차(원문의 "어느 능력치든 가능하다"를 DEX/CHA 근사로 좁힌 것)를 해소한 것이다.

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `check_trigger_mode`를 필수 필드로 만들면서 계획 `<files>` 목록 밖의 `test_web_characters.py` 두 호출부가 깨졌다**
- **Found during:** Task 1 이후 `uv run pytest -q` 전체 실행
- **Issue:** `test_none_axis_excluded_from_sheet_response`/`test_rulebook_with_zero_axes_returns_empty_stats`가 각자 만드는 ad-hoc `Rulebook(...)`에 `check_trigger_mode`가 없어 `TypeError`로 실패했다. Task 1의 `<files>` 목록에는 `tests/test_web_characters.py`가 없었지만, 필수 필드 추가는 이 파일의 기존 호출부에도 구조적으로 영향을 미쳤다.
- **Fix:** 두 호출부에 `check_trigger_mode="no_dice"` 추가(두 픽스처 모두 무브 목록이 없다).
- **Files modified:** `tests/test_web_characters.py`
- **Verification:** `uv run pytest -q` 894 passed (당시)
- **Committed in:** `f4a1fc2` (Task 2 커밋에 포함 — Cairn 등록 검증 실행 중 발견됨)

---

**2. [Rework - Orchestrator rejected first submission] `D20_ROLL_UNDER` 도크스트링이 존재하지 않는 시험을 있다고 주장했다**
- **Found during:** 마감 보고 후 오케스트레이터 검증(`grep -rn "D20_ROLL_UNDER" tests/` → 0건)
- **Issue:** `D20_ROLL_UNDER` 상수 도크스트링이 "이 상태는 `tests/test_session_actor.py`의 회귀 시험으로 고정되어 있다"고 적었지만, 실제로는 그런 시험이 없었다 — `declare-only` 결정이 안전하다는 근거의 전부(계산기 없는 판정 방식이 조용히 대체되지 않고 눈에 보이게 거부된다)가 검증되지 않은 채로 마감 보고됐다. 도크스트링의 거짓 주장은 시험이 없는 것보다 나쁘다 — 나중에 읽는 사람이 커버리지가 있다고 믿게 만든다.
- **Fix:** `tests/test_session_actor.py`에 `_NO_RESOLVER_RULEBOOK`(시험 전용, `D20_ROLL_UNDER` 선언)과 `test_rulebook_with_no_registered_resolver_is_rejected_not_silently_substituted`를 신설 — 이 파일의 기존 `_GAPPED_RULEBOOK`/`test_rulebook_with_incomplete_grade_bands_is_rejected_not_a_raw_traceback` 관례를 그대로 따랐다. `CommandRejected`가 나고 메시지에 `D20_ROLL_UNDER` 판정 방식 이름이 담기며, 사건 기록에 아무것도 안 쌓인다는 것(`_read_events == []`)까지 확인한다. `D20_ROLL_UNDER` 도크스트링을 실제 시험 함수 이름을 가리키도록 갱신해 이제 검증 가능한 주장이 됐다.
- **Files modified:** `tests/test_session_actor.py`, `src/gptrpg/rules_core/rulebook.py`
- **Verification:** `uv run pytest -q` 896 passed, `uv run lint-imports` 4 kept/0 broken
- **Committed in:** `a738810`
- **하지 않은 것:** `D20_ROLL_UNDER` 계산기 구현(오케스트레이터가 명시적으로 금지), 도크스트링 약화로 주장을 낮추는 방식(조건은 시험을 만드는 것이었다)

---

**Total deviations:** 1 auto-fixed (Rule 3 - Blocking) + 1 folded-todo 실증 기록(위 참조) + 1 rework(도크스트링-시험 간극 해소)
**Impact on plan:** 계획서 자신의 `<verify>`(`uv run pytest -q` 전체 초록)가 요구하는 최소 조건을 충족하기 위해 구조적으로 불가피했다. 범위 이탈이 아니다.

## Issues Encountered

None — 세 태스크와 접어넣은 todo 모두 계획서/todo 파일의 지시를 그대로 따라 실행했고, 위 두 건(auto-fix 1건 + rework 1건) 외에 추가 버그는 없었다. rework는 오케스트레이터의 정당한 지적이었다 — 첫 제출 시 도크스트링이 검증되지 않은 커버리지 주장을 담고 있었다.

## User Setup Required

None - 외부 서비스 설정 불필요.

## Verification Results

- `uv run pytest -q` — **896 passed**, 2 warnings(기존 `starlette`/`google-genai` 사용 경고, 이 계획과 무관)
- `uv run pytest tests/test_session_actor.py -q -k no_registered_resolver` — **1 passed** (declare-only 안전 근거 회귀 시험)
- `uv run lint-imports` — **Contracts: 4 kept, 0 broken**, 종료 코드 0
- `git diff --stat src/gptrpg/rules_core/entities.py` — **빈 출력** (그릇 칸이 하나도 안 늘었다)
- `python -c "from gptrpg.rulebooks import RULEBOOKS; print(sorted(RULEBOOKS))"` → `['cairn', 'dungeonworld_like', 'openquest']`
- `python -c "from gptrpg.rulebooks.moves import get_moves; print(get_moves('cairn'))"` → `()`
- `python -c "from gptrpg.rulebooks.cairn import CAIRN; print([(a.name, a.form, a.slot_count) for a in CAIRN.resource_axes if a.form=='named_slots'])"` → `[('Inventory', 'named_slots', 10)]`

## Next Phase Readiness

- **RULE-11**: `[ ]` In Progress로 유지 — Cairn이 `named_slots`(2/6)를 실제 데이터로 실증했다. `clock`/`tag_list`/`usage_die`/`none` 네 형태는 여전히 실제 등록된 룰북 데이터가 없다(화면 렌더 갈래만 존재).
- **RULE-15**: `[ ]` In Progress로 유지 — Cairn이 빈 트리거 목록 경로를 실제 데이터로 실증했다. `no_check`가 실제로 "판정 없이 서사가 이어지는" 화면으로 가는 것은 여전히 11-06 몫이다.
- **QUAL-03**: 이미 11-02에서 Complete — 이번 계획은 Cairn으로 회귀 확인만 추가했다(체크박스 변경 없음).
- 다음 계획(11-05는 이미 완료됨 — STATE.md 기준 다음은 11-06)이 착수 전에 알아야 할 것: `MoveDecl.default_stat`이 이제 `None`일 수 있으므로, 이 필드를 다루는 새 코드는 `None` 갈래를 명시적으로 처리해야 한다(`prompt_assembly.py`가 이미 그 예시를 남겼다).
- **declare-only의 안전 근거가 이제 코드로 못박혀 있다** — Cairn류(계산기 없는 판정 방식)로 실제 판정을 시도하면 `CommandRejected`로 거부되고 사건 기록에 아무것도 안 남는다는 것이 회귀 시험으로 고정됐다. 후속 계획이 실제 d20 계산기를 붙일 때 이 시험이 자연스럽게 "이제 거부가 아니라 실제 판정이 일어나야 한다"는 신호로 실패하며 알려준다.
- 블로커 없음.

## Self-Check: PASSED

- 파일 존재: `src/gptrpg/rulebooks/cairn.py`, `src/gptrpg/rules_core/rulebook.py`, `src/gptrpg/rulebooks/__init__.py`, `src/gptrpg/rulebooks/moves.py`, `LICENSES.md`, `tests/test_rulebook.py`, `tests/test_session_actor.py`, `.planning/todos/completed/2026-08-15-move-default-stat-optional.md` 전부 확인됨
- 커밋 존재: `9e66374`, `f4a1fc2`, `e1b1039`, `7fd2f03`, `a7ff772`, `a738810` 전부 `git log --oneline --all`에서 확인됨
- rework 시험 재확인: `uv run pytest tests/test_session_actor.py -q -k no_registered_resolver` → 1 passed

---
*Phase: 11-rulebook-vocabulary*
*Completed: 2026-08-16*

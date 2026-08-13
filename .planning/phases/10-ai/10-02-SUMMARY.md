---
phase: 10-ai
plan: 02
subsystem: ai-safety
tags: [prompt-injection, narration-guard, regex, unicode-normalization, streaming]

requires:
  - phase: 10-ai
    provides: "10-01이 만든 narration_guard.py leaf 모듈(GuardVerdict/inspect_sentence/strip_think_blocks)과 master_gm.narrate()의 1문장 지연 버퍼 + NarrationChunk 반환 타입 — 10-02가 이 뼈대의 원문 겹침·캐릭터 이탈 갈래를 채운다"
provides:
  - "normalize_for_overlap() — NFC → Cf 제거 → casefold → P*/S*/공백 제거 4단계 정규화(agents/narration_guard.py)"
  - "find_source_overlap() — 12코드포인트 문턱, 문장 경계를 넘나드는 슬라이딩 윈도 대조(agents/narration_guard.py)"
  - "CHARACTER_BREAK_PATTERNS — 자기지칭/3인칭 메타분석/시스템 화제삼기 5개 정규식, 절대 blocked로 승격 안 됨(agents/narration_guard.py)"
  - "narrate()가 build_gm_prompt의 영구 고정 블록(system[0])만 원문 겹침 대조 소스로 배선 — 세션 고정 블록은 의도적으로 제외(agents/master_gm.py)"
affects: [10-03, 10-04, 10-05]

actuals:
  tokens: 10025
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "슬라이딩 윈도 부분열 대조 — 정규화된 (문장+다음문장) 결합 문자열 위에서 시작 위치를 문장 내부로 제한한 12자 창을 밀며 소스와 대조, 적중하면 오른쪽으로 늘려 실제 최대 겹침 길이를 구한다"
    - "정규식 목록 순회 + '전부 flagged' 회귀 그물 — PROVIDER_FACTORIES 순회 관례(tests/test_providers.py)와 같은 모양으로, 패턴이 늘어도 D-03 규율(캐릭터 이탈은 절대 차단 안 됨)이 자동으로 지켜지는지 확인"

key-files:
  created: []
  modified:
    - src/gptrpg/agents/narration_guard.py
    - src/gptrpg/agents/master_gm.py
    - tests/test_narration_guard.py

key-decisions:
  - "대조 소스는 build_gm_prompt의 영구 고정 블록 하나뿐이다 — RESEARCH.md 가정 A1(영구+세션 둘 다)을 계획이 좁혔다. 세션 고정 블록(_narration_session_block_text)은 장면 대상·캐릭터 상태라는 정당한 이야기 맥락이라 대조 소스에 넣으면 정상 서사가 걸린다(오탐 폭증)"
  - "문턱은 정규화 후 12 코드포인트, 정규화는 NFC→Cf 제거→casefold→공백·구두점(P*)·기호(S*) 제거 — 계획이 확정한 값(10-02-PLAN.md 설계 판단 2·3)"
  - "캐릭터 이탈 정규식은 넓게 잡되 절대 blocked로 승격하지 않는다(D-03) — 자기 지칭 계열은 대명사와 AI 명사가 근접해 함께 있을 때만 잡아 '저는 촌장입니다' 같은 정상 대사와 갈랐다"

requirements-completed: [SAFE-02]

coverage:
  - id: D1
    description: "진행자 지시문 원문과 정확히 12자 이상 겹치는 문장이 화면에 닿기 전에 걸린다(경계값 포함, 11자는 안 걸림)"
    requirement: "SAFE-02"
    verification:
      - kind: unit
        ref: "tests/test_narration_guard.py#test_find_source_overlap_exactly_twelve_chars_is_blocked"
        status: pass
      - kind: unit
        ref: "tests/test_narration_guard.py#test_find_source_overlap_eleven_chars_is_clean"
        status: pass
      - kind: unit
        ref: "tests/test_narration_guard.py#test_inspect_sentence_blocks_verbatim_instruction_overlap"
        status: pass
    human_judgment: false
  - id: D2
    description: "빈 문장·공백뿐 문장·정규화 후 12자 미만인 문장은 소스에 통째로 들어 있어도 항상 clean이다"
    requirement: "SAFE-02"
    verification:
      - kind: unit
        ref: "tests/test_narration_guard.py#test_find_source_overlap_empty_sentence_is_always_clean"
        status: pass
      - kind: unit
        ref: "tests/test_narration_guard.py#test_find_source_overlap_short_sentence_never_blocks_even_if_verbatim_in_source"
        status: pass
    human_judgment: false
  - id: D3
    description: "문장 경계에 걸쳐 이어지는 겹침(앞 문장 끝 몇 자 + 다음 문장 앞 몇 자)도 잡힌다"
    requirement: "SAFE-02"
    verification:
      - kind: unit
        ref: "tests/test_narration_guard.py#test_find_source_overlap_across_sentence_boundary_is_blocked"
        status: pass
    human_judgment: false
  - id: D4
    description: "캐릭터 이탈로 보이는 문장(자기지칭/3인칭 메타분석/시스템 화제)은 감지되지만 절대 blocked로 승격하지 않고 통과·기록만 한다"
    requirement: "SAFE-02"
    verification:
      - kind: unit
        ref: "tests/test_narration_guard.py#test_character_break_never_produces_blocked_for_any_pattern"
        status: pass
      - kind: unit
        ref: "tests/test_narration_guard.py#test_character_break_self_reference_as_ai_korean_is_flagged_not_blocked"
        status: pass
      - kind: unit
        ref: "tests/test_narration_guard.py#test_character_break_third_person_meta_analysis_english_is_flagged"
        status: pass
    human_judgment: false
  - id: D5
    description: "이야기 속 인물이 '저는…'으로 말을 시작하는 정상 대사는 flagged가 아니다(오탐 방지)"
    requirement: "SAFE-02"
    verification:
      - kind: unit
        ref: "tests/test_narration_guard.py#test_character_break_in_story_dialogue_starting_with_i_am_is_not_flagged"
        status: pass
    human_judgment: false
  - id: D6
    description: "narrate()가 실제 영구 고정 블록을 대조 소스로 배선하고, 장면 대상·캐릭터 상태를 언급하는 정상 서사는 안 걸린다"
    requirement: "SAFE-02"
    verification:
      - kind: integration
        ref: "tests/test_narration_guard.py#test_narrate_does_not_block_narration_mentioning_scene_entity_and_character_state"
        status: pass
    human_judgment: false
  - id: D7
    description: "narrate()를 통해 영구 고정 블록 구절을 그대로 옮긴 서사가 blocked로 걸리고, NarrationChunk가 reason=source_overlap과 matched_len>0을 싣고 나온다"
    requirement: "SAFE-02"
    verification:
      - kind: integration
        ref: "tests/test_narration_guard.py#test_narrate_blocks_narration_that_quotes_permanent_block_verbatim"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-08-14
status: complete
---

# Phase 10 Plan 2: 원문 겹침 대조와 캐릭터 이탈 감지 Summary

**결정론적 원문 겹침 대조(NFC 정규화 → 12코드포인트 슬라이딩 윈도)로 진행자 지시문 유출을 자동 차단하고, 5개 정규식으로 캐릭터 이탈 말투를 감지해 절대 차단하지 않고 통과·기록만 하도록 `narration_guard.py`와 `master_gm.narrate()`를 확장했다.**

## Performance

- **Duration:** ~20분
- **Completed:** 2026-08-14
- **Tasks:** 3/3
- **Files modified:** 3 (`agents/narration_guard.py`, `agents/master_gm.py`, `tests/test_narration_guard.py` — 신규 파일)

## Accomplishments

- `MIN_OVERLAP_CHARS = 12` · `normalize_for_overlap()` · `find_source_overlap()`을 `narration_guard.py`에 신설 — NFC 정규화 → 유니코드 Cf(폭 없는 문자) 제거 → casefold → 공백·구두점(P*)·기호(S*) 제거 순서로 정규화하고, 문장+다음문장 결합 문자열 위에서 시작 위치가 검사 대상 문장 안에 있는 12자 창을 밀어 소스와 대조한다. 적중한 창은 오른쪽으로 늘려 실제 최대 겹침 길이를 구한다.
- `inspect_sentence()`의 원문 겹침 갈래를 채움 — 생각 블록(차단) → 원문 겹침(차단) → 캐릭터 이탈(기록만) → clean 순서. 겹침 적중 시 `reason="source_overlap"`, `matched_len`에 실제 겹친 길이.
- `CHARACTER_BREAK_PATTERNS`(정규식 5개)를 신설 — 자기 지칭(한/영), 3인칭 메타 분석(한/영), 시스템 프롬프트·지시문 화제 삼기. 각 정규식 옆에 세션1 감사 또는 03-04 라이브 검증 관찰 근거를 주석으로 남김. 자기 지칭 계열은 대명사와 AI 명사가 근접할 때만 잡아 "저는 촌장입니다" 같은 정상 대사와 구분.
- `inspect_sentence()`의 캐릭터 이탈 갈래를 채움 — 걸리면 `disposition="flagged"`, `text`는 원문 그대로, **절대 `blocked`를 돌려주지 않는다**(D-03).
- `master_gm.narrate()`가 `build_gm_prompt`의 `system[0]["text"]`(영구 고정 블록)만 원문 겹침 대조 소스로 배선 — 새로 조립하지 않고 이미 만들어진 값을 그대로 쓴다. 세션 고정 블록(`system[1]`, 장면 대상·캐릭터 상태)은 대조 소스에서 의도적으로 제외했고, 그 이유를 `narrate()` 도크스트링에 한 문단으로 남김.
- `tests/test_narration_guard.py` 신설(30개 시험) — 정규화 네 단계, 겹침 문턱(11/12자 경계값), 문장 경계를 넘나드는 겹침, 캐릭터 이탈 패턴 전수 순회(절대 blocked 안 나옴 회귀 그물), `narrate()`를 실제로 관통하는 통합 시험(장면 대상/캐릭터 상태 언급은 clean, 영구 블록 구절 그대로 옮긴 서사는 blocked) 전부 실제 `build_gm_prompt` 호출로 소스를 얻는다(하드코딩 없음).

## Task Commits

1. **Task 1: 원문 겹침 대조 — 정규화와 문턱 (SAFE-02, D-02②)** - `7dc3aa2` (feat)
2. **Task 2: 캐릭터 이탈 신호 — 통과시키되 기록만 (D-02③/D-03)** - `33dbfa8` (feat)
3. **Task 3: 대조 소스를 narrate()에 배선하고 오탐 경계를 못박는다 (SAFE-02)** - `ea41a69` (feat)

**Plan metadata:** (이 커밋 — STATE.md/ROADMAP.md/REQUIREMENTS.md 갱신과 함께)

## Files Created/Modified

- `src/gptrpg/agents/narration_guard.py` - `MIN_OVERLAP_CHARS`/`normalize_for_overlap`/`find_source_overlap`/`CHARACTER_BREAK_PATTERNS` 신설, `inspect_sentence`의 두 갈래(원문 겹침·캐릭터 이탈) 채움
- `src/gptrpg/agents/master_gm.py` - `_judge_sentence`/`narrate()`가 영구 고정 블록을 `source_texts`로 배선, 도크스트링에 세션 블록 제외 근거 추가
- `tests/test_narration_guard.py` - 신설. 정규화·문턱·경계값·캐릭터 이탈 전수 순회·`narrate()` 통합 시험 30개

## Decisions Made

- **대조 소스 = 영구 고정 블록 하나뿐(계획이 확정, RESEARCH.md A1 좁힘).** 위 "key-decisions" 참조 — 세션 고정 블록을 넣으면 정상 서사(장면 대상·캐릭터 상태 언급)가 오탐으로 걸린다는 것을 Task 3의 통합 시험으로 실제 확인했다.
- **문턱 12자·정규화 4단계는 계획이 이미 확정한 값을 그대로 구현.** 재논의하지 않았다(10-02-PLAN.md 설계 판단 2·3).
- **캐릭터 이탈 정규식은 넓게 잡되 자기 지칭 계열만 AI 명사 근접 조건을 걸었다.** "플레이어/사용자 + 메타분석" 계열과 "시스템 프롬프트/지시문" 계열은 이야기 어휘에 자연스럽게 등장할 확률이 낮아 근접 조건 없이도 오탐 위험이 낮다고 판단.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 한국어 3인칭 메타 분석 정규식이 실제 활용형을 못 잡음**
- **Found during:** Task 2, `test_character_break_never_produces_blocked_for_any_pattern` 첫 실행
- **Issue:** 계획 문구 그대로 `(하려는|하려고 한다|...)` 형태로 구현하면 "열려는 것 같다"처럼 "하다"가 아닌 다른 동사 어간에 "-려는"이 붙는 활용형을 놓친다.
- **Fix:** "하려는" 대신 "려는"(어간 공통 어미)으로 패턴을 넓혀 임의 동사 활용형을 포괄하도록 수정.
- **Files modified:** `src/gptrpg/agents/narration_guard.py`
- **Verification:** `test_character_break_never_produces_blocked_for_any_pattern` 통과, 나머지 캐릭터 이탈 시험 전부 통과.
- **Committed in:** `33dbfa8` (Task 2 커밋)

**2. [Rule 1 - Bug] Task 3 통합 시험에서 leaked_phrase 앵커 선택이 문장 경계 오탐을 유발**
- **Found during:** Task 3, `test_narrate_blocks_narration_that_quotes_permanent_block_verbatim` 첫 실행
- **Issue:** 처음 고른 앵커 구절("이미 정해진 값을 그대로 반영해서 서술만")이 영구 블록 안에서 "…않는[다] — 이미 정해진…" 바로 뒤에 위치해, 앞 문장이 흔한 한국어 종결 "다"로 끝나기만 하면(대부분의 정상 서사가 그렇다) 문장 경계 겹침 검사가 우연히 걸렸다 — Task 1이 설계한 대로 정확히 동작한 것이지만, "정상 서사는 안 걸린다"를 보여야 할 시험의 앞 문장까지 걸려 시험 의도가 흐려졌다.
- **Fix:** 소스 안에서 "다"가 아닌 문자(을) 뒤에 오는 다른 구절("네 문장 안에 스스로 지어내지")로 앵커를 교체 — 문장 경계 오탐 위험 없이 앵커 단독으로도 12자 문턱을 정확히 채운다.
- **Files modified:** `tests/test_narration_guard.py`
- **Verification:** `test_narrate_blocks_narration_that_quotes_permanent_block_verbatim` 통과, `chunks[0]`(정상 서사)과 `chunks[2]`가 모두 clean임을 확인.
- **Committed in:** `ea41a69` (Task 3 커밋)

---

**Total deviations:** 2 auto-fixed (둘 다 Rule 1 — 시험 스스로가 드러낸 버그/시험 설계 결함을 즉시 고침)
**Impact on plan:** 계획의 설계 의도(문턱 12자, 정규화 4단계, 세션 블록 제외, 캐릭터 이탈 record-only)를 하나도 뒤집지 않았다. 스코프 확장 없음.

## Known Stubs

없음 — 이 계획의 산출물(원문 겹침·캐릭터 이탈 검사)은 전부 실제 동작으로 배선됐고, 목표 달성을 막는 스텁이 없다. (재생성 시도 D-06/D-07은 여전히 10-03의 몫이며, 10-01이 남긴 `NOTICE_GAVE_UP` 미소비 스텁도 그대로 10-03이 이어받는다 — 이 계획이 새로 만든 스텁은 없다.)

## Issues Encountered

없음 — 위 "Deviations from Plan"이 실제로 부딪힌 문제와 해결을 전부 담는다.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **10-04(fence_player_text, SAFE-05)가 바로 이어붙일 수 있다** — `narration_guard.py`는 여전히 leaf 모듈(`json_parsing`만 import)이고, `CHARACTER_BREAK_PATTERNS`가 확립한 "정규식 목록 + 전수 순회 회귀 그물" 패턴을 재사용할 수 있다.
- **10-03(재생성 시도, D-06/D-07)이 `avoid_text` 매개변수를 추가할 자리(`narrate()`)가 이번 계획으로 안 건드려졌다** — Task 3은 `source_texts` 배선만 추가했고 재시도 루프(`for _attempt in range(MAX_ATTEMPTS)`)와 재생성 로직은 손대지 않았다.
- 정직하게 남는 한계(계획이 명시): ① 이 대조는 지시문을 **그대로** 옮긴 유출만 잡는다 — 뜻만 옮긴 유출은 못 잡는다. ② 시나리오 원문은 애초에 서술 프롬프트에 안 들어가므로(Phase 9) 이 대조 소스에 없다 — "시나리오 정보" 부분은 Phase 9의 타입 차원 차단이 담당한다. 이 둘을 "막았다"고 보고하지 않는다.
- 블로커 없음. `uv run pytest`(671건) · `uv run lint-imports`(4계약 유지) · `uv run ruff check src` 전부 초록불.

---
*Phase: 10-ai*
*Completed: 2026-08-14*

## Self-Check: PASSED

- FOUND: `src/gptrpg/agents/narration_guard.py`
- FOUND: `src/gptrpg/agents/master_gm.py`
- FOUND: `tests/test_narration_guard.py`
- FOUND commit: `7dc3aa2` (Task 1)
- FOUND commit: `33dbfa8` (Task 2)
- FOUND commit: `ea41a69` (Task 3)

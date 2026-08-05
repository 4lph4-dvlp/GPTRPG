---
phase: 03-ai
plan: 04
subsystem: ai
tags: [confirm-ux, tiered-confidence, progress-indicator, streaming, prompt-assembly, robustness]

# Dependency graph
requires:
  - phase: 03-ai
    plan: "03-02"
    provides: "다섯 제공자 어댑터, 역할별 제공자·모델 선택 영속화 — 이 계획의 turn_flow가 role별 provider를 해석해 쓴다"
  - phase: 03-ai
    plan: "03-03"
    provides: "call_with_one_retry(D-27/D-28), classify()/narrate()의 실패-시-빈-후보/스트리밍 재시도 규칙, chunk_sentences() 경계 보장 — 이 계획이 그 위에 세 갈래 UX와 진행 표시를 얹는다"
provides:
  - "action_classifier.Proposal.tier (읽기 전용 property, single/several/none) + MAX_CANDIDATES=3 — 후보 개수에서만 화면 강도를 뽑는다, 신뢰도 숫자 칸 없음"
  - "src/gptrpg/cli/turn_flow.py — 03-01이 cli/main.py에 직접 짜 둔 턴 흐름을 옮겨 세 갈래 확인 화면 + with_progress_dots(D-26) + 판정-우선-서사 순서로 넓힌 모듈"
  - "action_classifier의 실제 모델(추론형 포함) 응답에 대한 강건한 JSON 파싱 — <think> 블록·마크다운 코드펜스·설명 문장에 둘러싸인 배열도 뽑아낸다"
  - "invoke.call_with_one_retry의 실패 시 stderr 진단 — '무브 없음'과 '제공자 호출 실패'를 운영자가 구분할 유일한 창구"
  - "master_gm.narrate()의 스트림 정지 워치독(_drain_with_stall_timeout, STREAM_STALL_TIMEOUT_S=90.0) — 멈춘 스트림이 터미널을 무한정 붙잡지 않는다"
  - "turn_flow._build_turn_context의 화자 표시('플레이어: '/'진행자: ') + build_gm_prompt의 '분석하지 말고 서사만 써라' 지시문 — 모델이 대화록을 메타 분석 과제로 오인하지 않는다"
affects: ["04 (동기 멀티플레이 화면이 이 CLI 확인 흐름을 웹으로 옮긴다)", "05 (실험 참가자가 이 세 갈래 화면·진행 표시로 직접 플레이한다)", "06 (HYP-04 채점이 system_suggestion/move 분리, MEAS-02가 caused_by_seq 인과 사슬에 의존)"]

# Actuals (#2632)
actuals:
  tokens: 21070
  tasks: 3
  commits: 5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "화면 강도는 후보 개수에서만 계산하는 읽기 전용 property(Proposal.tier) — 별도 저장 칸을 만들지 않는다"
    - "with_progress_dots(fn, threshold_s, tick_s) — 데몬 스레드 하나가 출력만 맡고 fn()은 호출 스레드에서 그대로 블로킹한다, 외부 라이브러리 없음"
    - "_drain_with_stall_timeout(source, stall_timeout_s) — 배경 데몬 스레드 + 큐로 블로킹 I/O를 감싸, 강제로 끊을 수는 없어도 호출한 쪽은 더 기다리지 않고 돌아간다(with_progress_dots와 같은 스레드 격리 원칙)"
    - "제공자 호출이 성공했지만 형식이 깨진 응답은 원문 그대로 먼저 파싱을 시도하고(회귀 없음), 실패해야만 <think>/코드펜스 벗기기 대체 경로로 넘어간다"
    - "재시도까지 실패한 호출의 진단 정보(마지막 예외 문자열)는 사건 기록에는 안 남기고 stderr로만 노출한다 — D-30의 최소 봉투 규격을 건드리지 않는다"

key-files:
  created:
    - src/gptrpg/cli/turn_flow.py
    - tests/test_action_classifier.py
  modified:
    - src/gptrpg/agents/action_classifier.py
    - src/gptrpg/agents/invoke.py
    - src/gptrpg/agents/master_gm.py
    - src/gptrpg/agents/prompt_assembly.py
    - src/gptrpg/cli/main.py
    - tests/test_agents_retry.py
    - tests/test_cli.py
    - tests/test_master_gm.py
    - tests/test_session_actor.py
    - tests/test_turn_tracer.py

key-decisions:
  - "Proposal.tier는 후보 개수 하나에서만 계산하는 읽기 전용 property — MAX_CANDIDATES=3으로 모델이 넷 이상 돌려줘도 화면은 항상 최대 셋(several)"
  - "cli/main.py의 턴 흐름을 cli/turn_flow.py로 옮기되 _build_turn_context는 main.py에서 재노출(one-way import)해 tests/test_turn_tracer.py의 기존 import를 한 글자도 안 고쳤다"
  - "진행 표시는 두 자리(분류기 호출 대기, 서사 첫 조각 대기)에만 건다 — 서사 두 번째 조각부터는 걸지 않는다(원래 설계 그대로, 이번 라이브 검증에서 문제가 안 됨)"
  - "[deviation] action_classifier의 max_tokens를 4096으로 올렸다가(추측성 수정) 라이브 검증에서 근거가 없다고 판명되어 1024로 되돌렸다 — 두 번째로 다시 추측하는 대신 마지막으로 검증된 값으로 복귀"
  - "[deviation] call_with_one_retry가 실패 사유를 stderr에 찍는다 — D-29/D-30이 정한 플레이어 화면의 무구분은 그대로 두고, 운영자만 구분할 수 있는 별도 창구를 열었다(사건 기록에는 안 들어간다)"
  - "[deviation] recent_turns 각 줄에 '플레이어: '/'진행자: ' 화자 표시를 붙이고 build_gm_prompt에 '분석하지 말고 서사만 써라' 지시문을 추가 — 라이브에서 모델이 대화록을 메타 분석 과제로 오인한 실제 사례를 고쳤다"
  - "[deviation] narrate()에 STREAM_STALL_TIMEOUT_S=90.0 스톨 워치독 추가 — GM_TIMEOUT_S(D-33)는 건드리지 않는다(D-33이 '완결까지는 목표 없음'이라고 명시한 응답 속도 목표이지, 안전판이 아니다). 이 값은 별도의, 순수 안전용 Claude's Discretion 값"

patterns-established:
  - "제공자 호출의 진단 문자열(last_error_text)은 사건 기록 스키마를 늘리지 않고 stderr 부수효과로만 노출한다 — D-30의 최소 봉투 규격을 지키면서도 운영 가능성을 확보하는 방법"
  - "블로킹 I/O를 감쌀 때는 배경 데몬 스레드 + 큐로 '기다리는 쪽'만 시간제한을 걸고, 블로킹 그 자체를 강제로 끊으려 하지 않는다(파이썬이 못 하는 일이므로) — with_progress_dots와 _drain_with_stall_timeout이 같은 원칙을 공유"

requirements-completed: [RIG-01, MEAS-02, MEAS-04]

coverage:
  - id: D1
    description: "화면 강도가 후보 개수(0/1/2~3/4+)에서만 계산되고, Proposal에 신뢰도 숫자 칸이 없다"
    requirement: RIG-01
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py#test_zero_candidates_yields_none_tier, test_one_candidate_yields_single_tier, test_two_candidates_yields_several_tier, test_three_candidates_yields_several_tier, test_four_candidates_are_truncated_to_three_and_yield_several_tier, test_proposal_field_names_have_no_confidence_slot"
        status: pass
    human_judgment: false
  - id: D2
    description: "single 갈래는 한 줄 제안 + [Enter=확인/n=아니오], 번호 목록이 안 뜬다 (D-34)"
    requirement: RIG-01
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_turn_single_candidate_shows_one_line_no_numbered_list"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 라이브 검증(f2 세션) — '문을 부수고 들어간다' 턴에서 defy_danger 한 줄 제안 확인"
        status: pass
    human_judgment: false
  - id: D3
    description: "several 갈래는 번호 목록(최대 3개)에서 숫자로 고르고, 2번 고른 경우 ConfirmAction.move가 system_suggestion.move와 다르게 남는다 (D-35, HYP-04)"
    requirement: RIG-01
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_turn_several_candidates_shows_numbered_list_and_second_pick_diverges_from_suggestion, test_turn_several_candidates_reprompts_on_out_of_range_and_non_digit_input"
        status: pass
      - kind: integration
        ref: "tests/test_session_actor.py#test_ai_turn_preserves_raw_text_verbatim_and_diverges_pick_from_system_suggestion"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 라이브 검증(f2 세션) — '말로 설득해보다가...' 턴에서 parley/hack_and_slash 번호 목록이 뜨고 2번을 골랐다"
        status: pass
    human_judgment: false
  - id: D4
    description: "none 갈래는 되돌리기 화면 없이 '판정 없이 진행합니다'를 찍고 끝난다 — ConfirmAction을 제출하지 않는다 (D-29, D-36)"
    requirement: RIG-01
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_turn_no_candidates_proceeds_without_check_and_records_no_confirm_event"
        status: pass
      - kind: integration
        ref: "tests/test_session_actor.py#test_ai_turn_no_move_turn_has_declaration_but_no_confirmation_event"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 라이브 검증(f2 세션) — 두 턴 모두 '무브 없음 — 판정 없이 진행합니다'로 정상 낙하"
        status: pass
    human_judgment: false
  - id: D5
    description: "5초(진행 표시 기준)를 넘기면 점이 하나 이상 찍히고, 그 전에 응답이 오면 점이 하나도 안 찍힌다 (D-26)"
    requirement: MEAS-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_turn_shows_progress_dots_when_classifier_response_exceeds_threshold, test_turn_no_progress_dots_when_response_is_immediate"
        status: pass
    human_judgment: true
    rationale: "실제 5초 초과는 실제 모델 응답 지연에 의존하는 터미널 렌더링 효과라 자동 시험이 아니라 사람 눈으로만 최종 확인된다 — 이번 계획 자체가 plan.must_haves에서 이 항목을 backstop으로 못박았다. f2 라이브 세션에서는 응답이 빨라 점이 안 찍혔다(정상 — 4턴 모두 5초 미만)."
  - id: D6
    description: "판정 결과 줄이 서사 첫 조각보다 항상 먼저 화면·기록에 나간다 (MEAS-02 성공조건 3) — 지연과 무관하게 흐름 구조로 보장"
    requirement: MEAS-02
    verification:
      - kind: unit
        ref: "tests/test_turn_tracer.py#test_turn_runs_full_loop_and_records_events_in_causal_order"
        status: pass
      - kind: integration
        ref: "tests/test_session_actor.py#test_ai_turn_preserves_raw_text_verbatim_and_diverges_pick_from_system_suggestion"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 라이브 검증(f2 세션) — 두 확인된 턴 모두 판정 결과(예: strong_hit)가 서사보다 먼저 출력됨"
        status: pass
    human_judgment: false
  - id: D7
    description: "ActionDeclared.raw_text가 손질 없이 그대로 남고, several 갈래에서 system_suggestion과 move가 서로 다른 칸에 남는다 (MEAS-04)"
    requirement: MEAS-04
    verification:
      - kind: integration
        ref: "tests/test_session_actor.py#test_ai_turn_preserves_raw_text_verbatim_and_diverges_pick_from_system_suggestion"
        status: pass
    human_judgment: false
  - id: D8
    description: "「무브 없음」 턴의 기록에 선언 사건은 있고 확인 사건은 없다 (MEAS-04, HYP-04 세 번째 칸)"
    requirement: MEAS-04
    verification:
      - kind: integration
        ref: "tests/test_session_actor.py#test_ai_turn_no_move_turn_has_declaration_but_no_confirmation_event"
        status: pass
    human_judgment: false
  - id: D9
    description: "[deviation 수정] 추론형 모델(예: NIM Nemotron)이 <think> 블록·코드펜스·설명 문장으로 감싼 JSON 응답도 후보로 정확히 파싱된다 — 원문 그대로 파싱이 실패해야만 대체 경로를 탄다"
    verification:
      - kind: unit
        ref: "tests/test_action_classifier.py#test_think_block_wrapped_json_array_still_parses, test_markdown_code_fence_wrapped_json_array_still_parses, test_prose_before_and_after_json_array_still_parses, test_unknown_move_inside_think_block_wrapped_response_still_raises, test_completely_unparseable_response_yields_none_tier_not_a_crash, test_non_list_json_response_yields_none_tier_not_a_crash"
        status: pass
    human_judgment: true
    rationale: "f2 라이브 재검증에서 D-35 번호 목록이 정상 작동했지만, 실제 모델 원문이 처음부터 순수 JSON이었는지(빠른 경로) 대체 파싱 경로가 실제로 발동했는지는 구분되지 않는다 — WINDOWS.md id 5로 unrun-verify 기록"
  - id: D10
    description: "[deviation 수정] 제공자 호출이 두 번 다 실패하면(예: 타임아웃) 플레이어 화면은 '무브 없음'과 똑같이 보이지만, stderr에는 실제 예외 문자열이 남아 운영자가 구분할 수 있다"
    verification:
      - kind: unit
        ref: "tests/test_agents_retry.py#test_both_attempts_failing_prints_last_error_text_to_stderr, test_successful_call_prints_nothing_to_stderr"
      - kind: integration
        ref: "tests/test_cli.py#test_turn_provider_call_failure_looks_like_no_move_but_leaves_a_stderr_trail"
      - kind: manual_procedural
        ref: "Task 3 재검증 Run 1(자물쇠 턴) — 실제 stderr에 '경고: 제공자 호출이 2번 모두 실패했다 — Request timed out.' 출력됨을 사용자가 직접 확인, WINDOWS.md id 3(unrun-verify) 해소"
        status: pass
    human_judgment: false
  - id: D11
    description: "[deviation 수정] recent_turns에 화자 표시('플레이어: '/'진행자: ')가 붙어, 서사가 대화록을 메타 분석하지 않고 이야기를 이어 쓴다"
    verification:
      - kind: unit
        ref: "tests/test_turn_tracer.py#test_second_turn_prompt_labels_prior_turn_with_speaker_prefixes, test_turn_context_recent_turns_is_capped_at_ten"
        status: pass
      - kind: manual_procedural
        ref: "Task 3 재검증(f2 세션) — parley/hack_and_slash 번호 목록 갈래(원래 메타 분석이 나왔던 바로 그 갈래)에서 서사가 한국어 인물 시점 산문으로 정상 출력됨을 사용자가 확인"
        status: pass
    human_judgment: false
  - id: D12
    description: "[deviation 수정] 스트림이 실제로 멈춰도(예: 응답 끊김) narrate()가 STREAM_STALL_TIMEOUT_S 안에 실패로 낙하해, 터미널이 무한정 멈추지 않는다"
    verification:
      - kind: unit
        ref: "tests/test_master_gm.py#test_drain_with_stall_timeout_raises_after_no_item_for_the_deadline, test_narrate_gives_up_and_marks_failure_when_stream_never_produces_anything, test_narrate_keeps_already_emitted_sentence_when_stream_stalls_mid_way"
        status: pass
    human_judgment: true
    rationale: "f2 재검증 배치의 4턴 모두 정상 완주해 워치독이 실제로 발동하는 상황이 재현되지 않았다 — 합성 이중체로만 검증됨. WINDOWS.md id 4로 unrun-verify 기록"

# Metrics
duration: ~3h (Task 1·2 구현 + Task 3 라이브 검증 3왕복 + 그 사이 발견된 실제 버그 4건 수정)
completed: 2026-08-02
status: complete
---

# Phase 3 Plan 4: 확신도 세 갈래 확인 화면 + 진행 표시 + 판정 우선 순서 Summary

**후보 개수(0/1/2~3/4+)에서만 화면 강도를 뽑는 `Proposal.tier`와 세 갈래 CLI 확인 화면(한 줄 확인/번호 목록/판정 없이 진행)을 완성하고, 5초 진행 표시와 판정 결과 우선 순서를 흐름 구조로 못박았다. 라이브 검증 중 실제 발견된 버그 4건(추론형 모델의 JSON 파싱 실패, 제공자 실패의 무진단, 대화록 메타 분석 오작동, 스트림 무한 정지)을 모두 그 자리에서 고쳐 재검증까지 마쳤다.**

## Performance

- **Duration:** ~3시간 (Task 1·2 구현 40분 + Task 3 라이브 검증 3왕복 및 그 사이 실제 버그 4건 진단·수정·재검증)
- **Completed:** 2026-08-02
- **Tasks:** 3/3 (auto → auto → checkpoint:human-verify, 승인됨)
- **Files modified:** 12 (2 new, 10 modified)

## Accomplishments

- `Proposal.tier`(읽기 전용 property) + `MAX_CANDIDATES=3` — 후보 개수 하나에서만 화면 강도(single/several/none)를 계산한다. `Proposal`/`MoveCandidate`에 신뢰도 숫자 칸이 없다는 것을 필드 이름 집합 단언으로 못박았다(D-16/D-37)
- `build_classifier_prompt`의 지시문에 "확실하면 무브 하나만, 애매하면 둘이나 셋을, 어느 것도 안 맞으면 하나도 내지 말 것"을 영구 고정 조각 안에 추가
- `src/gptrpg/cli/turn_flow.py` 신설 — 03-01이 `cli/main.py`에 직접 짜 둔 턴 흐름을 옮겨 세 갈래 확인 화면(D-34/D-35/D-36), `with_progress_dots`(D-26, 스레드 하나로 화면만 담당·외부 라이브러리 없음), 판정 결과를 서사보다 항상 먼저 내보내는 흐름 구조(MEAS-02)로 넓혔다. `cli/main.py`는 인자 파싱과 저장소·세션 준비만 하도록 얇아졌다
- `turn` 서브커맨드에 `--progress-after`/`--progress-tick` 추가(기본 5.0/1.0)
- **라이브 검증 중 발견해 고친 실제 버그 4건** (아래 Deviations 참조): 추론형 모델의 JSON 응답 파싱 강건화, 제공자 호출 실패의 stderr 진단 노출, `recent_turns` 화자 표시로 서사 메타 분석 오작동 수정, 스트림 정지 워치독 신설
- Task 3(NIM `nvidia/nemotron-3-ultra-550b-a55b`로 라이브 검증) — 세 차례 재검증 끝에 승인. 세 갈래 확인 화면 전부, 판정-우선 순서, 신뢰도 숫자 미노출, 무브없음 낙하가 실제 모델 응답으로 확인됨

## Task Commits

Each task was committed atomically, plus deviation fix commits found during Task 3's live verification:

1. **Task 1: 화면 강도를 후보 개수에서 뽑는다** - `733ac8f` (feat)
2. **Task 2: 세 갈래 확인 화면 + 진행 표시 + 판정 결과 먼저** - `f3dc4ad` (feat)
3. **[deviation] 추론형 모델의 JSON 파싱 강건화** - `b425a18` (fix)
4. **[deviation] max_tokens 추측 되돌리기 + stderr 진단 추가** - `89eb0a7` (fix)
5. **[deviation] recent_turns 화자 표시 + 스트림 정지 워치독** - `f510d43` (fix)
6. **Task 3: 라이브 검증** — checkpoint, no commit (세 번 왕복 끝에 사용자 승인, f2 세션)

**Plan metadata:** (다음 커밋에서 이 SUMMARY.md·STATE.md·ROADMAP.md·REQUIREMENTS.md를 묶음)

## Files Created/Modified

- `src/gptrpg/cli/turn_flow.py` - 세 갈래 확인 화면 + `with_progress_dots` + 턴 흐름 본체 (신설)
- `tests/test_action_classifier.py` - tier 계산 10개 + 강건 파싱 7개 시험 (신설)
- `src/gptrpg/agents/action_classifier.py` - `ProposalTier`/`Proposal.tier`/`MAX_CANDIDATES`, `_try_parse_json_array` 강건 파싱
- `src/gptrpg/agents/invoke.py` - 실패 시 stderr 진단 줄
- `src/gptrpg/agents/master_gm.py` - `_drain_with_stall_timeout`/`STREAM_STALL_TIMEOUT_S`
- `src/gptrpg/agents/prompt_assembly.py` - 분류기 후보 개수 지시문, 진행자 프롬프트의 "분석 말고 서사만" 지시문
- `src/gptrpg/cli/main.py` - 턴 흐름을 `turn_flow`에 위임하도록 얇아짐, `_build_turn_context` 재노출
- `tests/test_agents_retry.py`, `tests/test_cli.py`, `tests/test_master_gm.py`, `tests/test_session_actor.py`, `tests/test_turn_tracer.py` - 시험 함수 확장

## Decisions Made

- `Proposal.tier`는 후보 개수 하나에서만 계산하는 읽기 전용 property — 별도 저장 칸 없음
- `cli/main.py`의 턴 흐름을 `turn_flow.py`로 옮기되 `_build_turn_context`는 단방향 재노출로 기존 시험 호환 유지
- 진행 표시는 분류기 호출 대기·서사 첫 조각 대기 두 자리에만 건다
- (deviation) `max_tokens` 추측성 인상(1024→4096)을 근거 없음이 라이브로 드러나 되돌림
- (deviation) 제공자 호출 실패 진단을 stderr로만 노출 — 사건 기록 스키마(D-30)는 그대로
- (deviation) `recent_turns`에 화자 표시 + 진행자 프롬프트에 "분석 말고 서사만" 지시문 추가
- (deviation) `narrate()`에 90초 스트림 정지 워치독 추가 — D-33의 `GM_TIMEOUT_S`와는 별개(D-33은 "완결까지는 목표 없음"이라 안전판이 아니다)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 추론형 모델의 JSON 응답이 파싱되지 않아 "무브 없음"으로 조용히 오인됨**
- **Found during:** Task 3 라이브 검증(1차) — D-35 번호 목록을 노리고 설계한 애매한 문장이 매번 "무브 없음"으로 떨어짐
- **Issue:** `_parse_candidates`가 원문 그대로 `json.loads` 한 번만 시도했다. 실제 모델(특히 NIM Nemotron 계열 추론형 모델)은 `<think>` 추론 블록·마크다운 코드펜스·설명 문장을 JSON 앞뒤에 덧붙이는데, 이 경우 파싱이 예외 없이 빈 후보로 떨어져 "모델이 못 골랐다"와 "모델 출력을 못 읽었다"가 구분 없이 뒤섞였다
- **Fix:** `_try_parse_json_array`가 원문을 먼저 시도(회귀 없음)하고, 실패하면 `<think>` 블록·코드펜스를 벗기고 첫 `[`~마지막 `]`를 다시 시도하는 대체 경로를 추가. 비-리스트/비-딕셔너리 원소는 죽지 않고 건너뛴다
- **Files modified:** `src/gptrpg/agents/action_classifier.py`, `tests/test_action_classifier.py`
- **Verification:** 7개 신규 시험(think 블록/코드펜스/설명문 감싼 JSON, 감싼 응답 안의 UnknownMove, 완전히 못 읽는 응답, 비-리스트 JSON) 전부 통과
- **Committed in:** `b425a18`

**2. [Rule 1 - Bug, 되돌림] 검증 안 된 max_tokens 인상**
- **Found during:** 위 1번 수정 시도 중, `max_tokens=1024`가 추론 과정에 다 쓰이고 잘릴 수 있다는 가설로 4096으로 인상
- **Issue:** Task 3 재검증(2차)에서 정확히 두 개의 서로 다른 문장(그중 하나는 discern_realities+pick_lock_or_trap을 명시적으로 겨냥한 문장)이 전부 "무브 없음"으로 떨어졌고, `replay` 토큰 합계가 AI 호출 2회 추가에도 전혀 안 늘어 제공자 호출 자체가 두 번 다 실패(`ok=False`, 토큰 0)한 것으로 확인됨 — max_tokens 인상은 근거가 없었고 오히려 문제를 키웠을 가능성이 있다
- **Fix:** `max_tokens`를 1024로 되돌림. 대신 `call_with_one_retry`가 실패 사유를 stderr에 찍도록 해 다음 라이브 실행에서 실제 원인이 보이게 함
- **Files modified:** `src/gptrpg/agents/action_classifier.py`, `src/gptrpg/agents/invoke.py`, `tests/test_action_classifier.py`, `tests/test_agents_retry.py`, `tests/test_cli.py`
- **Verification:** stderr 진단 시험 2개(성공 시 무출력/실패 시 예외 문자열 출력) + CLI 종단 재현 시험 1개(항상 실패하는 이중체로 `gptrpg turn`을 실제로 돌려 토큰 0/AI 호출 기록 확인). 실제 Task 3 재검증(3차) Run 1에서 stderr에 `Request timed out.`이 실제로 찍혀 확인됨(WINDOWS.md id 3 해소)
- **Committed in:** `89eb0a7`

**3. [Rule 1 - Bug] 진행자 서사가 대화록을 메타 분석하는 오작동**
- **Found during:** Task 3 재검증(2차) — D-35 번호 목록이 처음 정상 작동한 턴에서, 서사 대신 "The user is describing a situation... The user seems to be trying multiple actions: 1. ..."라는 3인칭 메타 분석과 이전 실패 턴의 원문 되풀이가 출력됨
- **Issue:** `_build_turn_context`가 `action_declared`/`narration_appended` 원문을 화자 구분 없이 한 줄씩 그대로 이어 붙였다 — 모델이 화자 표시 없는 문장 뭉치를 "다음 서사를 이어 써라"가 아니라 "이 입력 뭉치를 분석하라"는 별개 과제로 오인했다
- **Fix:** 각 줄에 `"플레이어: "`/`"진행자: "` 화자 표시를 붙이고, `build_gm_prompt`의 영구 고정 지시문에 "최근 대화·판정 결과는 분석·요약·되풀이 대상이 아니라 이어 쓸 맥락"이라는 문장과 "3인칭으로 사용자를 지칭하지 않는다"를 추가
- **Files modified:** `src/gptrpg/cli/turn_flow.py`, `src/gptrpg/agents/prompt_assembly.py`, `tests/test_turn_tracer.py`
- **Verification:** 두 번째 턴의 실제 렌더링된 프롬프트를 `FakeProvider.calls`로 캡처해 화자 표시가 실려 있는지 확인하는 종단 시험 추가. 기존 `test_turn_context_recent_turns_is_capped_at_ten`의 단언을 새 형식에 맞게 갱신. Task 3 재검증(3차)에서 바로 그 갈래(parley/hack_and_slash 번호 목록)로 다시 재현해 정상적인 한국어 서사가 나옴을 확인
- **Committed in:** `f510d43`

**4. [Rule 2 - Missing Critical] 스트림이 멈추면 터미널이 무한정 붙잡힘**
- **Found during:** Task 3 재검증(2차) — 서사가 문장 중간에서 끊긴 뒤 사용자의 터미널이 ~22분 동안 반응 없이 멈춤("난 아무것도 하지 않았어")
- **Issue:** `GM_TIMEOUT_S=15.0`을 제공자 SDK의 `timeout_s`로 넘겼지만, 이 값은 스트림의 최초 응답까지만 재는 것으로 보이고 스트림 전체 소요 시간을 재지 않았다 — 스트림이 실제로 멈춰도 `narrate()`의 소비 루프가 예외 없이 무한정 블로킹할 수 있었다(안전판 없음)
- **Fix:** `_drain_with_stall_timeout`(배경 데몬 스레드 + 큐, `with_progress_dots`와 같은 스레드 격리 원칙) 신설 — `provider.stream()`의 원문 조각을 감싸, `STREAM_STALL_TIMEOUT_S`(90초, 안전용 Claude's Discretion 값) 동안 새 조각이 없으면 `TimeoutError`를 던진다. `narrate()`의 기존 예외 처리 절이 이를 다른 실패와 똑같이 처리한다(이미 나간 조각은 보존, 새 분기 코드 없음)
- **Files modified:** `src/gptrpg/agents/master_gm.py`, `tests/test_master_gm.py`
- **Verification:** `_drain_with_stall_timeout` 단위 시험 2개(정상 통과/스톨 시 예외) + `narrate()` 통합 시험 2개(스트림이 아예 시작 안 함/한 문장 낸 뒤 멈춤 — 둘 다 짧은 `stall_timeout_s`로 1초 미만에 끝남). Task 3 재검증(3차) 4턴 모두 정상 완주해 워치독이 실제로 발동하는 상황은 재현 못 함(WINDOWS.md id 4로 unrun-verify 기록)
- **Committed in:** `f510d43`

---

**Total deviations:** 4 auto-fixed (3 Rule 1 - Bug, 1 Rule 2 - Missing Critical; 그중 하나는 이전 자체 수정의 되돌림)
**Impact on plan:** 전부 Task 3의 라이브 검증 없이는 발견되지 않았을 실제 결함이다. 자동 시험만으로는 실제 모델의 응답 형태(추론 흔적, 스트림 정지)를 재현할 수 없어 계획 자체가 Task 3를 backstop(사람 눈 최종 확인)으로 못박은 이유가 그대로 증명됐다. 범위 확장 없음 — 전부 이 계획이 원래 약속한 "세 갈래가 실제로 작동한다"는 목표를 달성하기 위한 필수 수정이었다.

## Issues Encountered

Task 3가 세 번의 왕복을 거쳤다 — 자동 시험은 처음부터 끝까지 전부 통과했지만, 실제 모델(NIM `nvidia/nemotron-3-ultra-550b-a55b`)의 실제 응답 형태는 각 라운드마다 새로운 실패 모드를 드러냈다. 이는 문제가 아니라 계획이 Task 3를 backstop으로 설계한 정확한 이유였다 — 가짜 제공자로는 재현할 수 없는 실제 모델의 습성(추론 블록, 스트림 정지, 대화록 오독)이 세 라운드 각각에서 드러났고, 그때마다 그 자리에서 고쳐 자동 시험으로 못박은 뒤 재검증했다.

## User Setup Required

None beyond 03-02가 이미 요구한 것 — 사용자는 이미 `NVIDIA_API_KEY`를 갖고 있었고 `gptrpg agents select`로 두 역할 모두 `nvidia/nemotron-3-ultra-550b-a55b`를 골라 f1/f2 세션으로 Task 3를 완주했다.

## Next Phase Readiness

- Phase 3(AI 진행자 한 턴)의 마지막 계획이 끝났다 — 자유 문장 분류, 세 갈래 확인 화면, 5초 진행 표시, 판정 결과 우선 순서, 문장 단위 서사, 그리고 그 모든 것이 정답 데이터로 기록에 남는 전체 루프가 실제 모델로 검증됐다
- `.planning/WINDOWS.md`: 이 계획이 id 1(D-26/D-33 UX 임계값 미구현)과 id 3(실제 제공자 타임아웃 예외 형 미검증)을 해소(fixed)했다. id 2(OpenRouter 귀속 헤더, OPENROUTER_API_KEY 없어 여전히 미검증)는 그대로 열려 있다. 이 계획이 새로 연 id 4(스트림 정지 워치독이 실제로 발동하는 상황 미재현)·id 5(추론형 모델의 `<think>`/코드펜스 대체 파싱 경로가 실제로 탄 사례 미확인)는 open으로 남는다 — 둘 다 향후 실제 지연·응답 형태가 재현되면 자연스럽게 검증될 항목이지 블로커는 아니다
- Phase 3 성공조건 다섯 줄(자유 문장 분류 → 세 갈래 확인 → 판정 → 문장 단위 서사 → 정답 데이터 기록) 전부가 03-01~03-04 네 계획에 걸쳐 실제 모델로 완주 확인됨
- No blockers for phase-level verification/closeout.

---
*Phase: 03-ai*
*Completed: 2026-08-02*

## Self-Check: PASSED

All 12 files claimed as created/modified exist on disk; all 5 task/deviation commit hashes (`733ac8f`, `f3dc4ad`, `b425a18`, `89eb0a7`, `f510d43`) verified present in `git log --oneline --all`. `.planning/WINDOWS.md` updated: id 1 and id 3 marked fixed (resolved by this plan), ids 4 and 5 newly recorded as open (unrun-verify — stall watchdog and reasoning-model parsing fallback not exercised live in the final re-verification batch), id 2 (OpenRouter attribution headers) remains open unchanged.

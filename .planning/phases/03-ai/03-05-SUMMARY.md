---
phase: 03-ai
plan: 05
subsystem: ai
tags: [openrouter, httpx, unicode-encoding, provider-adapters, regression-test]

# Dependency graph
requires:
  - phase: 03-ai (plan 02)
    provides: PROVIDER_FACTORIES 다섯 자리 등록소, OpenAIProvider 위임 구조
provides:
  - "ASCII 전용 OpenRouter 귀속 헤더 — 모델 목록·분류·서사 세 호출 경로 모두 복구"
  - "다섯 어댑터 전부를 그물로 덮는 헤더 ASCII 인코딩 가능성 회귀 시험"
  - "실제 키로 재확인된 OpenRouter 모델 목록 조회 성공 (UAT 1번 재실행)"
affects: [03-ai (남은 gap G-03-3), Phase 6 (원가 실측이 OpenRouter를 저가 대안으로 쓸 가능성)]

actuals:
  tokens: 1400
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns:
    - "귀속/식별 헤더는 항상 ASCII 문자열로 고정하고, 사람이 읽을 현지어 이름이 필요하면 헤더가 아니라 화면 출력에 둔다"
    - "SDK 클라이언트 생성자를 가짜로 바꿔치기하는 시험 이중체는 httpx 인코딩 단계를 재현하지 못한다 — 인코딩 가능성 자체를 단언하려면 `.encode(\"ascii\")`를 시험 코드에서 직접 호출해야 한다"

key-files:
  created: []
  modified:
    - src/gptrpg/agents/providers/openrouter_provider.py
    - tests/test_providers.py
    - .planning/phases/03-ai/03-UAT.md

key-decisions:
  - "X-Title 값을 RFC 8187 percent-encoding이 아니라 순수 ASCII 문자열로 교체 — X-Title은 확장 필드 문법을 해석하지 않는 평범한 자유 문자열 헤더라 percent-encoding하면 OpenRouter 대시보드에 깨진 문자열이 그대로 찍힌다"
  - "귀속 헤더 자체는 지우지 않는다 — '붙일지'가 아니라 '어떤 바이트로 붙일지'만 고친다(조사 단계 미해결 질문에 대한 기존 방어적 선택 유지)"

patterns-established:
  - "다섯 어댑터를 PROVIDER_FACTORIES로 순회하며 `getattr(client, \"default_headers\", None)`이 있을 때만 단언하는 시험 패턴 — 여섯 번째 어댑터가 헤더를 붙이면 자동으로 이 그물에 걸린다"

requirements-completed: [RIG-01, RIG-03]

coverage:
  - id: D1
    description: "OpenRouter _ATTRIBUTION_HEADERS의 X-Title 값을 ASCII 문자열로 교체 — 모델 목록·분류·서사 호출이 UnicodeEncodeError 없이 나간다"
    requirement: RIG-01
    verification:
      - kind: unit
        ref: "tests/test_providers.py#test_openrouter_attribution_header_constant_is_ascii"
        status: pass
      - kind: unit
        ref: "tests/test_providers.py#test_openrouter_delegate_client_headers_are_ascii"
        status: pass
    human_judgment: false
  - id: D2
    description: "다섯 어댑터 전부를 덮는 헤더 ASCII 인코딩 가능성 회귀 시험 — 여섯 번째 어댑터가 같은 실수를 하면 자동으로 잡힌다"
    requirement: RIG-03
    verification:
      - kind: unit
        ref: "tests/test_providers.py#test_all_five_adapters_header_dicts_are_ascii_when_present"
        status: pass
    human_judgment: false
  - id: D3
    description: "실제 OPENROUTER_API_KEY로 agents select를 돌리면 모델 목록이 오류 없이 화면에 뜬다 (UAT 1번 시험 재실행, G-03-1 실증)"
    verification:
      - kind: manual_procedural
        ref: "uv run gptrpg agents select --role action_classifier --config /tmp/openrouter-check.json (사람이 실제 키로 실행, 2026-08-02)"
        status: pass
    human_judgment: true
    rationale: "합성 이중체는 httpx의 실제 인코딩·네트워크 단계를 타지 않아 이 결과를 증명하지 못한다 — 실제 키로 사람이 화면에 뜬 모델 목록을 확인해야만 gap이 닫힌다"

duration: ~15min
completed: 2026-08-02
status: complete
---

# Phase 03 Plan 05: OpenRouter 귀속 헤더 ASCII 수정 Summary

**OpenRouter 어댑터의 `X-Title` 귀속 헤더를 한글에서 ASCII 문자열로 교체해 다섯 제공자 중 하나가 통째로 죽어 있던 것(UnicodeEncodeError)을 고치고, 다섯 어댑터 전부를 덮는 헤더 인코딩 가능성 회귀 시험을 추가한 뒤 실제 키로 재확인.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-08-02T13:20:00Z (approx.)
- **Completed:** 2026-08-02T13:36:07Z
- **Tasks:** 2 (1 auto/tdd + 1 checkpoint:human-verify)
- **Files modified:** 3 (openrouter_provider.py, test_providers.py, 03-UAT.md)

## Accomplishments

- `_ATTRIBUTION_HEADERS["X-Title"]`을 `"GPTRPG M0 실험 도구"`(한글, 비-ASCII)에서 `"GPTRPG M0 Experiment Tool"`(ASCII)로 교체 — `HTTP-Referer`는 이미 ASCII라 손대지 않음
- `_ATTRIBUTION_HEADERS` 바로 아래와 모듈 도크스트링 양쪽에 "왜 ASCII여야 하는지"와 이번 실측 사고 기록을 남겨, 다음에 이 파일을 읽는 사람이 "시험이 통과하니 헤더는 안전하다"고 오해하지 않게 함
- 헤더 ASCII 인코딩 가능성을 검증하는 시험 3개 추가 + 기존 `test_openrouter_sends_attribution_headers`를 값 비어있음 검사까지 확장(4번째 behavior) — 상수 자체, 실제로 클라이언트에 넘겨진 헤더, 다섯 어댑터 전체를 각각 다른 각도에서 그물질
- 실제 `OPENROUTER_API_KEY`로 `agents select --role action_classifier`를 돌려 `openrouter` 제공자 선택 시 모델 목록이 오류 없이 뜨는 것을 사람이 확인(UAT 1번 시험 재실행) — `nvidia/nemotron-nano-9b-v2:free` 선택, `/tmp/openrouter-check.json`에 키 노출 없이 저장 확인
- `03-UAT.md`의 G-03-1 gap을 `resolved`로 마감 (resolved_by: 03-05-PLAN.md, resolved_at: 2026-08-02)

## Task Commits

Each task was committed atomically:

1. **Task 1: 귀속 헤더를 ASCII로 바꾸고, 헤더 인코딩 가능성 자체를 시험으로 못 박는다** - `a427381` (fix)
2. **Task 2: 실제 OpenRouter 키로 모델 목록이 돌아오는지 사람이 확인한다 (UAT 1번 재실행)** - 체크포인트, 코드 변경 없음(검증 전용) — 사람이 직접 실제 키로 실행해 확인. 승인: "approved"

**Plan metadata:** (이 커밋 — SUMMARY/STATE/ROADMAP/REQUIREMENTS/03-UAT 반영)

## Files Created/Modified

- `src/gptrpg/agents/providers/openrouter_provider.py` - `_ATTRIBUTION_HEADERS`의 `X-Title` 값을 ASCII로 교체, "왜 ASCII인가"·실측 사고 기록 도크스트링 추가
- `tests/test_providers.py` - 헤더 ASCII 인코딩 가능성 시험 3개 추가 + 기존 귀속 헤더 시험을 값 비어있음 검사까지 확장
- `.planning/phases/03-ai/03-UAT.md` - G-03-1 gap 상태를 `resolved`로 갱신 (resolved_by/resolved_at 추가)

## Decisions Made

- **RFC 8187 percent-encoding이 아니라 순수 ASCII 문자열을 선택.** `X-Title`은 `Content-Disposition`의 `filename*`처럼 확장 필드 문법을 서버가 되돌려 해석하는 자리가 아니라, OpenRouter가 대시보드·앱 순위에 그대로 찍는 평범한 자유 문자열 헤더다. percent-encoding하면 요청은 통과하지만 사람이 볼 화면에 `%EC%8B%A4...` 같은 깨진 문자열이 남는다 — 사람이 읽을 이름 자리에 깨진 문자열을 두느니 ASCII 영문 이름으로 바꾸는 쪽이 맞다(계획의 `<gap_coverage>`에 근거 명시됨).
- **헤더를 지우지 않는다.** 귀속 헤더를 항상 붙이는 것은 OpenRouter 문서가 "권장"만 하고 필수 여부를 조사 단계에서 확인 못 했던 것에 대한 기존의 의도된 방어적 선택이다(파일 도크스트링). 이번 gap은 "붙일지 말지"가 아니라 "어떤 바이트로 붙일지"의 문제이므로 그 결정을 뒤집지 않았다.
- **ASCII 검사에 `str.isascii()`가 아니라 `.encode("ascii")`를 사용.** 실패 시 어느 위치의 어떤 글자가 문제인지 예외 메시지에 그대로 나와, UAT에 보고된 실제 오류 문장(`'ascii' codec can't encode characters in position 10-11`)과 같은 모양으로 읽힌다.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. (Task 2의 사람 확인은 사용자가 이미 보유한 `OPENROUTER_API_KEY`로 직접 수행함, 새 설정 없음.)

## RESEARCH.md / Open Question 실증 결과

- **RESEARCH.md 가정 A4(OpenRouter 모델 목록이 실제로 돌아온다)가 참으로 확인됐다** — 헤더를 ASCII로 고친 뒤 실제 키로 `agents select`를 돌리자 모델 목록이 정상적으로 조회됐다(선택: `nvidia/nemotron-nano-9b-v2:free`).
- **Open Question 1(귀속 헤더가 모델 목록 조회에 필수인가)는 이번 실행으로도 여전히 미해결이다** — 헤더를 붙인 채로 성공했다는 것만 확인했을 뿐, 헤더를 뺐을 때도 성공하는지는 시험하지 않았다(계획 범위 밖). 기존의 방어적 선택(항상 붙인다)은 유지된다.

## Next Phase Readiness

- G-03-1이 닫혔다 — OpenRouter 다섯 어댑터 중 하나가 되살아났고, 회귀 시험이 다섯 어댑터 전부를 계속 덮는다.
- `03-UAT.md`에는 아직 열려 있는 G-03-3(narrate() 스트림 실패 시 raw traceback으로 죽는 문제, `turn_flow.py`)이 남아 있다 — 이 계획의 범위 밖이며 별도 gap-closure 계획이 필요하다.
- Anthropic/OpenAI/Gemini 세 제공자는 이번 단계 전체에서 실제 네트워크로 아직 검증되지 않은 채로 남아 있다(사용자가 해당 API 키를 보유하지 않음, 03-UAT.md 테스트 2 skipped) — 다섯 중 NIM·OpenRouter 둘만 실증됨.

---
*Phase: 03-ai*
*Completed: 2026-08-02*

## Self-Check: PASSED
- FOUND: .planning/phases/03-ai/03-05-SUMMARY.md
- FOUND: a427381 (fix(03-05): make OpenRouter attribution headers ASCII-safe)

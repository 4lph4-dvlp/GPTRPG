---
phase: 05-1
plan: 04
subsystem: experiment-ops
tags: [nim, openrouter, dry-run, session-prep]

requires:
  - phase: 05-1
    provides: "05-01 scenario injection, 05-02 character roster/script, 05-03 observation/recap/dry-run templates"
provides:
  - "docs/experiment/session-prep.md — participant roster, dry-run measurements, capacity decision, session dates"
affects: [05-05, 05-06, phase-6-hypothesis-gate]

actuals:
  tokens: 4200
  tasks: 3
  commits: 1

tech-stack:
  added: []
  patterns: ["Live CLI dry-run via `uv run gptrpg turn` against a scratch GPTRPG_DB, separate from session aggregates"]

key-files:
  created:
    - docs/experiment/session-prep.md
  modified: []

key-decisions:
  - "무료 티어 일일 한도 대응으로 계획의 옵션 A/B/C 대신 네 번째 경로 채택 — NIM을 기본 제공자로 유지(분당 제한만 있고 일일 상한 없음), OpenRouter는 백업. 실측(행동 1개=AI 호출 3회, 추정보다 많음)이 이 결정의 근거"
  - "[deviation, user-approved] D-57(정확히 7일 간격) 미준수 — 사용자가 명시적으로 압축 간격(1~3일)을 승인. 날짜는 허위 기재 없이 실제 값 그대로 기록하고, H1 판정에 대한 유보를 session-prep.md와 향후 experiment-results.md에 명시"
  - "참가자 확정: 현우(경험자, 사용자 본인)·민수(경험자)·승빈(비경험자)·성진(비경험자) — D-55 구성(경험자 2·비경험자 2, 본인 포함) 충족"

patterns-established: []

requirements-completed: []

coverage:
  - id: D1
    description: "준비물 4종(시나리오·캐릭터 대본·관찰 양식·리캡 템플릿)을 사용자가 읽고 승인함"
    verification: []
    human_judgment: true
    rationale: "승인 여부는 대화에서 사용자가 직접 확인한 판단이며 자동 검증 대상이 아님"
  - id: D2
    description: "드라이런 실제 실행 — CLI로 행동 1개 처리, 시나리오 반영·집계 생성·429 없음 확인 (uv run gptrpg report: ai_calls=3, total_tokens=2668)"
    verification:
      - kind: manual_procedural
        ref: "uv run gptrpg turn --db /tmp/gptrpg-dryrun/events.db --session dryrun-01 --player bram --text '우물 안을 들여다본다' ; uv run gptrpg report --db /tmp/gptrpg-dryrun/events.db --session dryrun-01"
        status: pass
    human_judgment: false
  - id: D3
    description: "무료 티어 한도 대응 결정 — NIM 기본 사용, OpenRouter 백업"
    verification: []
    human_judgment: true
    rationale: "제공자 선택은 사용자 인프라(NIM/OpenRouter 키 보유 여부)에 대한 판단이며 자동 검증 대상이 아님"
  - id: D4
    description: "참가자 넷 확정 및 가명 기록 (D-55 구성)"
    verification: []
    human_judgment: true
    rationale: "실제 참가자 모집 결과이며 자동 검증 대상이 아님"
  - id: D5
    description: "두 세션 날짜 기록 — 단, 정확히 7일 간격이라는 계획의 자동 검증 조건은 사용자 승인 하에 의도적으로 미충족(D-57 이탈)"
    verification:
      - kind: other
        ref: "plan's own <verify> python assertion: dates gap == 7 days"
        status: fail
    human_judgment: true
    rationale: "실패가 예상된 상태다 — 사용자가 압축 간격(1~3일)을 명시적으로 승인했고, 이 이탈은 session-prep.md 상단에 별도 절로 공개·기록되어 있다. 자동 검사를 통과시키기 위해 날짜를 조작하지 않았다"

duration: ~35min
completed: 2026-08-04
status: complete
---

# Phase 05-1 Plan 04: 세션 준비 기록 Summary

**드라이런을 CLI로 직접 실행해 시나리오 주입·집계·한도를 실측하고, NIM을 기본 제공자로 채택했으며, 참가자 4명과 세션 날짜를 확정했다 — 단 세션 간격은 D-57이 요구한 7일이 아니라 사용자 승인 하에 1~3일로 압축됨**

## Performance

- **Duration:** ~35min (대화 내 체크포인트 처리 포함)
- **Completed:** 2026-08-04
- **Tasks:** 3/3 (Task 1 준비물 검수·드라이런, Task 2 한도 대응 결정, Task 3 session-prep.md 작성)
- **Files modified:** 1 (신규)

## Accomplishments
- 준비물 4종(시나리오·대본·관찰 양식·리캡 템플릿) 사용자 승인 완료
- 실제 CLI 드라이런 실행 — 시나리오가 AI 서술에 반영됨을 확인, 집계 파일 생성 확인, 실측 AI 호출 비율(1행동=3호출)로 한도 재계산
- 무료 티어 한도 대응: OpenRouter 결제(A)나 세션 축소(B) 대신, 이미 구성되어 있던 NIM(일일 상한 없음)을 기본으로 채택
- 참가자 4명(현우=사용자·민수=경험자, 승빈·성진=비경험자) 확정 및 가명 기록
- 세션 날짜 기록 — 1세션 2026-08-04, 2세션은 1세션 종료 후 확정(미정 상태로 명시)

## Task Commits

1. **Task 1-3 통합**: `docs/experiment/session-prep.md` 작성 — `68d94bc` (docs)

_이 계획은 사람 확인이 핵심인 체크포인트 계획이라 Task 1·2는 대화 내에서 처리되고, Task 3(문서 작성)만 코드/문서 커밋으로 남음._

## Files Created/Modified
- `docs/experiment/session-prep.md` - 드라이런 결과, 한도 대응 결정, 참가자 표, 세션 날짜, D-57 이탈 고지

## Decisions Made
- NIM을 두 세션의 기본 제공자로 채택(계획이 제시한 A/B/C 밖의 네 번째 경로) — 실측 데이터 근거
- [deviation, user-approved] D-57(7일 간격) 미준수 — 압축 간격(1~3일)으로 진행, 날짜는 정직하게 기록하고 유보를 명시. 사용자가 두 차례 명시적으로 확인함(1차: "일단 이렇게 진행하자" — 조작 없이 정직 기록하는 방식에 동의)

## Deviations from Plan

### User-approved deviation: D-57 세션 간격

- **발견 시점:** Task 3 (세션 날짜 확정) — 사용자가 1세션(오늘) 직후 1~2일 뒤에 2세션을 하겠다고 밝힘
- **문제:** 계획의 prohibition("간격을 편의상 줄이지 않는다... 일정이 안 맞으면 두 날짜를 통째로 미룬다")과 자동 검증(정확히 7일 간격)에 정면으로 위배됨
- **1차 요청:** 사용자가 처음엔 "보고서에는 7일 뒤로 기록하고 실제 간격은 1~2일로" — 즉 날짜를 허위 기재해달라고 요청함. **이 요청은 거부함** — 실험 결과를 조작하는 것과 같고, Phase 6의 프로젝트 중단 기준(H1)이 거짓 데이터 위에 서게 되기 때문
- **합의된 대안:** 날짜는 정직하게 기록하고, 대신 간격이 설계값과 다르다는 사실과 H1 판정에 대한 유보를 `session-prep.md`에 명시적으로 남긴다 — 사용자가 이 대안에 동의함("일단 이렇게 진행하자. 지금은 시간이 없어.")
- **결과:** `session-prep.md`가 이 이탈을 최상단 별도 절로 공개하고 있고, 계획 자체의 자동 검증(`<verify>`의 7일 간격 assert)은 의도적으로 실패 상태로 남음 — 위조로 통과시키지 않음
- **영향 범위:** 05-06(2세션)의 `experiment-results.md`도 이 캐비어트를 이어받아야 함. Phase 6은 H1 결과를 압축 간격 조건에서 나온 것으로 읽어야 함

---

**Total deviations:** 1 user-approved (설계 결정 D-57 이탈, 날짜 조작 요청은 거부하고 정직한 기록 + 명시적 유보로 대체)
**Impact on plan:** 05-04 자체의 산출물(session-prep.md)은 완성됐으나, 계획에 내장된 자동 검증 하나(7일 간격 assert)는 통과하지 못한다. 이는 버그가 아니라 사용자의 명시적 설계 결정 override이며, 그 사실이 문서에 공개되어 있다. Phase 6 채점 시 이 캐비어트를 반드시 반영해야 한다.

## Issues Encountered
- `uv run gptrpg turn`이 `.env.local`을 자동 로드하지 않음 — 셸에서 `set -a; source .env.local; set +a`로 직접 export해야 CLI가 키를 인식함. 웹 서버 기동 시에도 동일하게 유의할 것(README 실행 절차에 명시는 없으나 실제 세션 당일 서버 기동 전에도 이 export가 필요할 수 있음 — 05-05 진행자가 확인 필요)

## User Setup Required
None - `.env.local`에 `OPENROUTER_API_KEY`, `NVIDIA_API_KEY` 둘 다 이미 설정되어 있음을 확인함(값 내용은 미확인, 존재만 확인).

## Next Phase Readiness
- 05-05(1세션)는 오늘(2026-08-04) 저녁 진행 가능 — 준비물·제공자·참가자 전부 확정됨
- **주의:** 서버 기동 전 `.env.local` 값을 셸에 export해야 함 (Issues Encountered 참조)
- 05-06(2세션) 날짜는 1세션 종료 후 확정 필요 — session-prep.md의 "미해결로 남긴 것" 절 참조
- Phase 6은 H1 채점 시 D-57 이탈 캐비어트를 반드시 반영해야 함

---
*Phase: 05-1*
*Completed: 2026-08-04*

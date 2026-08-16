---
status: complete
phase: 11-rulebook-vocabulary
source: [11-VERIFICATION.md]
started: 2026-08-17
updated: 2026-08-17
---

## Current Test

[testing complete]

## Tests

### 1. 「값이 0 / 개념 없음 / 규칙으로 안 셈 / 빠뜨림」 네 구분에 빠진 경계가 있는지 사람이 훑는다

expected: 네 구분은 이미 시험으로 고정되어 있다. 남은 질문은 「그 시험들이 놓친 경계가 더 있는가」 하나뿐이다.
result: pass
reported: "없다"

사장님이 직접 훑고 추가로 구분할 상황이 없다고 판단했다. 계획서 181행이 요구한 「자동 통과 처리하지 않고 사람에게 올린다」가 충족됐다.

### 2. 새 환경에서 「판정 없이 이야기가 이어지는」 기능이 실제로 켜지는지

expected: 모델 설정(`.gptrpg/agents.json`)이 git 무시 파일이라 새 환경에서 기본값으로 돌아가 기능이 조용히 안 켜진다. 자동 시험은 가짜 제공자를 쓰므로 이 상태를 절대 못 잡는다.
result: pass
reported: "예시 파일을 저장소에 넣고, 켜질 때 경고하며, 문서에도 적는다"
severity: major
resolved_by: "G-11-2 갭 해소 (커밋 02a47e5 / 397ef27 / a54eada) — 아래 Gap Resolutions 참조"

사장님이 지정한 세 가지를 그대로 실행해 닫았다. 오케스트레이터가 직접 확인한 것:
예시 파일 2개가 `git ls-files`에 실제로 잡히고, 사장님 실제 설정(`.gptrpg/agents.json`)·
API 키(`.env.local`)·사건 DB·쿠키 비밀은 여전히 무시되며, 작은 모델로 CLI를 돌리면
경고 두 줄이 뜨고 종료 코드 0으로 **막지 않고** 진행되고, 권장값으로 돌리면 경고가 없다.

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-11-2
  truth: "새 환경에서 저장소를 받은 사람이 모델 설정을 몰라 기능이 조용히 안 켜지는 일이 없다"
  status: resolved
  resolved_by: "02a47e5 (기동 경고) / 397ef27 (예시 파일) / a54eada (README)"
  resolved_at: 2026-08-17
  reason: "User reported: 예시 파일을 저장소에 넣고, 켜질 때 경고하며, 문서에도 적는다"
  severity: major
  test: 2
  root_cause: |
    `.gptrpg/agents.json`이 `.gitignore` 대상이라 저장소에 남지 않는다. 이 파일의 모델
    선택이 두 기능의 실제 작동 여부를 좌우한다는 것이 이번 단계에서 실측됐다:
    - 분류기가 작으면(8B) 「굴릴 필요 없음」이 실전에서 거의 안 켜진다 (11-MODEL-FINDING.md)
    - 서사 모델이 작으면(120b) 한국어 서사의 40%에 외국어가 섞인다 (11-NARRATION-LANGUAGE-FINDING.md)
    자동 시험은 전부 가짜 제공자를 쓰므로 이 저하를 원리적으로 못 잡는다 — 코드는 초록인데
    제품은 망가진 상태가 조용히 성립한다.
  artifacts:
    - path: ".gptrpg/agents.json"
      issue: "git 무시 파일이라 저장소에 안 남고, 새 환경에서 기본값으로 돌아간다"
    - path: "README.md"
      issue: "모델 설정이 기능 작동 조건이라는 사실이 적혀 있지 않다"
    - path: "src/gptrpg/agents/providers/__init__.py"
      issue: "권장값보다 작은 모델을 골라도 아무 신호가 없다"
  missing:
    - "저장소에 커밋되는 예시 설정 파일 (새 환경에서 복사만 하면 되도록)"
    - "서버/CLI 기동 시 권장값보다 작은 모델이면 눈에 보이는 경고"
    - "README에 「이 설정을 해야 두 기능이 실제로 켜진다」는 안내와 근거 문서 링크"
  debug_session: ""

## Deferred Follow-Ups

(없음)

## Gap Resolutions

### G-11-2 (2026-08-17)

사장님이 직접 지정한 세 가지를 각각 커밋으로 닫았다.

| missing 항목 | 커밋 | 내용 |
|---|---|---|
| 저장소에 커밋되는 예시 설정 파일 | `397ef27` | `.gitignore`를 `.gptrpg/`(디렉터리 전체 무시)에서 `**/.gptrpg/*` + `!**/.gptrpg/agents.example.json`/`.md`(두 예시 파일만 예외)로 좁혔다. `.gptrpg/agents.example.json`(사장님이 확정한 두 값)과 `agents.example.md`("왜 이 값인가" — JSON은 주석을 못 담아 옆 파일로 뺐다)를 커밋했다. `.gptrpg/agents.json`(실제 설정)·`.env.local`은 손대지 않았다 — `git diff --stat`으로 무변경 확인. |
| 서버/CLI 기동 시 경고 | `02a47e5` | `src/gptrpg/agents/model_recommendations.py` 신설 — 실측으로 미달이 확인된 정확한 두 모델(`action_classifier`=`meta/llama-3.1-8b-instruct`, `master_gm`=`nvidia/nemotron-3-super-120b-a12b`)과 정확히 같을 때만 경고한다(추측 경고 없음, no_unverified_claims). 웹은 `create_app()`의 `lifespan` 기동 시점, CLI는 `agents set`/`agents show`/`turn` 세 자리에서 부른다. 막지 않는다(경고 뒤에도 그대로 진행) — `rules_core`는 이 모듈을 import하지 않는다(계층 규율 유지, `lint-imports` 확인됨). |
| README 안내 + 근거 문서 링크 | `a54eada` | "실험 당일 실행 절차" 2번 항목을 갱신 — 기존에 실측으로 결함이 확인된 `meta/llama-3.1-8b-instruct`를 권장값으로 잘못 적어 두고 있던 것을 고치고, `cp .gptrpg/agents.example.json .gptrpg/agents.json` 절차와 `11-MODEL-FINDING.md`/`11-NARRATION-LANGUAGE-FINDING.md` 링크를 추가했다. |

**검증(전부 초록):**
- `uv run pytest -q` — 944 passed (기존 927 + 신규 17, 감소 없음)
- `uv run lint-imports` — 4 kept, 0 broken
- `cd frontend && npx tsc --noEmit` — 오류 없음
- `cd frontend && npx vitest run` — 4 passed

**경고 실동 확인(사장님 실제 설정 파일은 건드리지 않고, 스크래치 디렉터리의 임시 설정 파일로 확인):**
- CLI: `uv run gptrpg agents show --config <임시경로>/agents.json`(값이 `meta/llama-3.1-8b-instruct`/`nvidia/nemotron-3-super-120b-a12b`인 파일) → stderr에 두 줄 경고 출력, 종료 코드 0(안 막힘) 직접 확인.
- 웹: `create_app(agent_config_path=<임시경로>/agents.json, ...)`을 `TestClient` 컨텍스트로 열어(=lifespan 기동) 같은 두 경고가 stderr에 뜨고 `SERVER BOOTED OK`가 그대로 찍히는 것을 직접 확인.
- 확인 뒤 임시 디렉터리만 지웠다 — `.gptrpg/agents.json`(사장님 실제 설정)·`.env.local`은 세션 내내 열람도 하지 않았다.
- 같은 시나리오는 자동 시험으로도 고정했다(`tests/test_model_recommendations.py`, `tests/test_web_startup_model_warning.py`, `tests/test_agent_config.py`의 `test_agents_set_with_known_undersized_model_warns_on_stderr_but_still_saves` 등, `tests/test_cli.py`의 `test_turn_with_known_undersized_model_warns_but_still_completes`).

**범위:** CR-02·WR-01~WR-05는 이번 작업 대상이 아니다(건드리지 않음). 새 의존성 없음.

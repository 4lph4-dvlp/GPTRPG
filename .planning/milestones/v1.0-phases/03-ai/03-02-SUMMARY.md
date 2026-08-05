---
phase: 03-ai
plan: 02
subsystem: ai
tags: [openai, nim, openrouter, gemini, provider-abstraction, cli, persistence, prompt-caching]

# Dependency graph
requires:
  - phase: 03-ai
    plan: "03-01"
    provides: "gptrpg.agents 패키지 골격, Provider 프로토콜, AnthropicProvider·NimProvider(최소 범위) 두 어댑터, PROVIDER_ENV_VARS(다섯 개 선언), PROVIDER_FACTORIES(둘만 등록), gptrpg turn CLI 트레이서"
provides:
  - "OpenAIProvider — NIM·OpenRouter가 base_url 스왑으로 위임해 쓰는 공통 구현체"
  - "NimProvider 재작성(위임 방식), OpenRouterProvider, GeminiProvider — PROVIDER_FACTORIES 다섯 자리 완성"
  - "agents/config.py — AgentChoice/save_config/load_config/resolve_provider, ConfigNotFound/InvalidAgentConfig"
  - "gptrpg agents select/show CLI 하위 명령 — D-31 두 단계 선택 화면, D-32 역할별 독립, D-33 영속화"
  - "turn 하위 명령의 --provider/--model 선택 사항화 — 역할별 독립 제공자 해석"
affects: ["03-03 (타임아웃·재시도가 이 계획의 provider.complete/stream 호출을 감싼다)", "03-04 (신뢰도 UI가 이 계획의 classify() 호출 결과를 소비한다)", "06 (원가 계산이 다섯 제공자 중 실제로 골라 쓴 것의 AiInvoked 필드에 의존)"]

# Actuals (#2632)
actuals:
  tokens: 40624
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: ["google-genai>=2.16.0"]
  patterns:
    - "OpenAIProvider가 base_url·default_headers를 선택 인자로 받는 위임 대상 — NimProvider/OpenRouterProvider는 이 클래스를 감싸기만 하고 openai SDK를 직접 import하지 않는다"
    - "역할별 독립 제공자 해석 — turn CLI가 action_classifier/master_gm 각각에 대해 별도로 get_provider()를 부른다(공유 인스턴스를 강제하지 않는다)"
    - "저장 파일은 {provider, model} 두 칸만 — 키는 매 실행마다 os.environ에서 다시 읽는다, 조용한 대체 없이 즉시 예외"

key-files:
  created:
    - src/gptrpg/agents/providers/openai_provider.py
    - src/gptrpg/agents/providers/openrouter_provider.py
    - src/gptrpg/agents/providers/gemini_provider.py
    - src/gptrpg/agents/config.py
    - tests/test_providers.py
    - tests/test_agent_config.py
  modified:
    - src/gptrpg/agents/providers/nim_provider.py
    - src/gptrpg/agents/providers/__init__.py
    - src/gptrpg/agents/providers/base.py
    - src/gptrpg/cli/main.py
    - pyproject.toml
    - uv.lock
    - .gitignore

key-decisions:
  - "NimProvider를 03-01의 '독립 복제' 구현에서 03-02 원래 설계인 'OpenAIProvider 위임'으로 재작성 — Task 1을 시작하기 전 03-01-SUMMARY.md의 핸드오프 노트와 03-02-PLAN.md 본문을 대조해 의도적으로 재조정(reconciliation)했다. 행동은 03-01이 NIM으로 라이브 검증한 것과 동일 — 이번 재작성은 중복 제거일 뿐 동작 변경이 아니다"
  - "google.genai의 정확한 서명(Client.models.list/generate_content/generate_content_stream, GenerateContentConfig.system_instruction/max_output_tokens)을 구현 전에 실제로 help()·model_fields로 확인 — RESEARCH.md가 이 SDK를 MEDIUM confidence(WebSearch cross-check만, 세션 내 실행 미확인)로 표시했기 때문"
  - "OpenRouter 귀속 헤더(HTTP-Referer/X-Title)를 방어적으로 항상 붙임 — RESEARCH.md Open Question 1(모델 목록 조회에 필수인지 불명)이 이 계획의 실행 시점에도 완전히 풀리지 않아, '넣어서 손해 볼 것 없다'는 조사 단계의 권고를 그대로 따름"
  - "turn CLI의 --provider/--model은 '둘 다 주어지면 두 역할 모두에 적용'(빠른 수동 시험 겸 기존 트레이서 시험과의 하위 호환)으로 유지하고, 둘 다 없을 때만 role별 load_config 해석으로 분기 — 기존 03-01 트레이서 시험 6개를 한 글자도 고치지 않고 그대로 통과시켰다"
  - "PROVIDER_NOT_IMPLEMENTED 예외 갈래는 지금은 자연 발생하지 않지만(다섯 자리 전부 등록) 코드에서 지우지 않고 주석으로 이유를 남김 — 여섯 번째 제공자를 2단계로 배포할 때를 위해"

patterns-established:
  - "제공자 어댑터가 다른 어댑터를 감싸는 위임 계층(OpenAIProvider -> Nim/OpenRouter) — SDK import 지점을 하나로 계속 줄인다"
  - "CLI가 역할별로 독립된 provider 인스턴스를 만드는 것이 기본값이고, 단일 인스턴스 공유는 명시적 override(둘 다 지정)일 때만 발생한다"

requirements-completed: [RIG-01, RIG-03]

coverage:
  - id: D1
    description: "다섯 제공자(Anthropic·OpenAI·Gemini·Nvidia NIM·OpenRouter)가 전부 같은 Provider 프로토콜을 구현한다 — isinstance(adapter, Provider)가 참이다"
    requirement: RIG-01
    verification:
      - kind: unit
        ref: "tests/test_providers.py#test_all_five_adapters_satisfy_provider_protocol"
        status: pass
    human_judgment: false
  - id: D2
    description: "PROVIDER_FACTORIES의 열쇠 집합이 PROVIDER_ENV_VARS의 열쇠 집합과 정확히 같다(다섯 개)"
    verification:
      - kind: unit
        ref: "tests/test_providers.py#test_provider_factories_and_env_vars_have_identical_key_sets"
        status: pass
    human_judgment: false
  - id: D3
    description: "등록되지 않은 이름/키 없음/미구현 세 갈래가 각각 UnknownProvider/MissingApiKey/ProviderNotImplemented로 조용한 대체 없이 실패하고, 키 값이 예외 메시지에 없다"
    verification:
      - kind: unit
        ref: "tests/test_providers.py#test_get_provider_raises_unknown_provider_for_unregistered_name, test_get_provider_raises_missing_api_key_when_env_var_absent, test_missing_api_key_message_never_contains_key_value, test_get_provider_raises_provider_not_implemented_when_factory_missing"
        status: pass
    human_judgment: false
  - id: D4
    description: "NimProvider와 OpenRouterProvider는 서로 다른 기본 주소로 만들어진다"
    verification:
      - kind: unit
        ref: "tests/test_providers.py#test_nim_and_openrouter_have_different_base_urls"
        status: pass
    human_judgment: false
  - id: D5
    description: "save_config -> load_config 왕복에서 두 역할의 제공자·모델이 그대로 돌아오고, 저장 파일 원문에 환경 변수 값이 없다"
    requirement: RIG-01
    verification:
      - kind: unit
        ref: "tests/test_agent_config.py#test_save_then_load_round_trips_both_roles, test_saved_file_never_contains_env_var_values"
        status: pass
    human_judgment: false
  - id: D6
    description: "저장 파일이 없으면 ConfigNotFound, 저장된 제공자의 키가 없으면 MissingApiKey — 둘 다 조용히 다른 값으로 대체하지 않는다"
    verification:
      - kind: unit
        ref: "tests/test_agent_config.py#test_load_config_raises_config_not_found_when_file_missing, test_resolve_provider_raises_missing_api_key_when_env_unset"
        status: pass
    human_judgment: false
  - id: D7
    description: "두 역할에 서로 다른 제공자·모델을 저장했다가 읽으면 서로 다른 값이 그대로 나온다(D-32) — 코드 경로가 역할별로 독립적으로 동작한다"
    verification:
      - kind: unit
        ref: "tests/test_agent_config.py#test_two_roles_can_hold_different_provider_and_model, test_agents_select_lets_each_role_pick_independently"
      - kind: manual_procedural
        ref: "Task 3 라이브 실행, 2026-08-02 — 화면이 두 역할에 대해 각각 한 번씩(총 두 번) 떴음을 사용자가 직접 확인. 다만 사용자 환경에 NIM 키 하나만 있어 두 번 모두 같은 값을 선택 — 코드 경로의 독립성은 자동 시험(위 unit 항목, 서로 다른 스텁 제공자로 검증)이 대신 증명한다"
        status: pass
    human_judgment: true
    rationale: "라이브 실행에서는 두 역할이 실제로 다른 값을 갖는 것까지는 보이지 않았다(제공자가 하나뿐이라 사용자가 같은 모델을 두 번 선택) — 사람이 이 격차를 명시적으로 인지한 채 승인했다(체크포인트 대화 참조). 자동 시험은 서로 다른 스텁 제공자로 이 요구사항을 완전히 증명한다"
  - id: D8
    description: "gptrpg agents show는 저장된 두 역할의 제공자·모델을 각각 한 줄로 출력하고, 그 출력에 키 값이 없다"
    verification:
      - kind: unit
        ref: "tests/test_agent_config.py#test_agents_show_prints_both_roles_without_key_values"
      - kind: manual_procedural
        ref: "Task 3 라이브 실행 — cat /tmp/agents.json으로 API 키 문자열이 한 글자도 없음을 사용자가 직접 확인"
        status: pass
    human_judgment: false
  - id: D9
    description: "turn --provider/--model 없이 실행하면 다시 묻지 않고 저장된 선택으로 바로 돈다(D-33)"
    requirement: RIG-01
    verification:
      - kind: manual_procedural
        ref: "Task 3 라이브 실행 — uv run gptrpg turn ... --config /tmp/agents.json (제공자/모델 인자 없이) 이 분류->확인->판정->문장 단위 서사까지 즉시 완주함을 사용자가 확인"
        status: pass
    human_judgment: false
  - id: D10
    description: "실제 NIM 키로 모델 목록 조회와 complete/stream 호출이 실제로 응답을 돌려준다(RESEARCH.md 가정 A3 확인)"
    verification:
      - kind: manual_procedural
        ref: "Task 3 라이브 실행, 2026-08-02 — nim 제공자로 102개 모델 실시간 조회, turn 실행에서 분류(complete)·서사(stream) 둘 다 실제 응답 수신·스트리밍 확인됨"
        status: pass
    human_judgment: false
  - id: D11
    description: "OpenRouter 귀속 헤더가 실제로 붙어 나간다(가정 A4는 OpenRouter 키가 없어 라이브로는 미확인 — 방어적 헤더 부착 자체만 자동 시험으로 증명)"
    verification:
      - kind: unit
        ref: "tests/test_providers.py#test_openrouter_sends_attribution_headers"
        status: pass
    human_judgment: true
    rationale: "사용자에게 OPENROUTER_API_KEY가 없어 Task 3에서 실제 네트워크로 확인하지 못했다 — RESEARCH.md Open Question 1(가정 A4)은 여전히 미해결로 남는다. WINDOWS.md에 기록"

# Metrics
duration: ~50min (Task 1·2 구현 + 체크포인트 대화 왕복 1회)
completed: 2026-08-02
status: complete
---

# Phase 3 Plan 2: 다섯 제공자 + 역할별 선택 영속화 Summary

**OpenAI·NIM·OpenRouter·Gemini 네 어댑터로 Provider 프로토콜 구현을 다섯으로 채우고, `gptrpg agents select/show`로 역할별 제공자·모델을 실시간 조회해 고르고 저장하는 흐름을 완성했다. NIM 실제 키로 모델 102개 실시간 조회와 전체 턴 실행을 사람이 직접 확인.**

## Performance

- **Duration:** ~50분 (Task 1·2 구현 + Task 3 체크포인트 대화 1왕복, 재검증 없이 1차 승인)
- **Completed:** 2026-08-02
- **Tasks:** 3/3 (auto → auto → checkpoint:human-verify)
- **Files modified:** 13 (6 new, 7 modified)

## Accomplishments

- `OpenAIProvider` 신설 — `base_url`/`default_headers` 선택 인자를 받는 위임 대상. NIM·OpenRouter가 이 클래스 하나만 감싸 쓴다(별도 SDK 설치 없음)
- `NimProvider`를 03-01의 임시 복제 구현에서 이 계획의 원래 설계(위임)로 재작성 — 03-01-SUMMARY.md의 핸드오프 노트를 따라 의도적으로 재조정(reconciliation), 동작은 그대로(03-01이 NIM으로 이미 라이브 검증)
- `OpenRouterProvider` 신설 — 귀속 헤더(`HTTP-Referer`/`X-Title`) 방어적 부착(RESEARCH.md 미해결 Open Question 1 대응)
- `GeminiProvider` 신설 — `google.genai` 실제 서명을 구현 전에 `help()`로 확인 후 작성(RESEARCH.md가 MEDIUM confidence로 표시한 항목)
- `PROVIDER_FACTORIES` 다섯 자리 완성 — `PROVIDER_ENV_VARS`와 열쇠 집합 정확히 일치
- `agents/config.py` 신설 — `AgentChoice`/`save_config`/`load_config`/`resolve_provider`, `ConfigNotFound`/`InvalidAgentConfig` 둘 다 조용한 대체 없이 즉시 실패
- `gptrpg agents select` — D-31 두 단계 화면(제공자 선택 → 그 자리에서 실시간 모델 목록 조회 → 모델 선택), `--role` 없으면 두 역할을 각각 독립적으로 돈다(D-32)
- `gptrpg agents show` — 저장된 두 역할을 키 값 없이 출력
- `turn`의 `--provider`/`--model`을 선택 사항으로 전환, 역할별 독립 제공자 해석 추가 — 기존 트레이서 시험 6개 무수정 통과
- Task 3(라이브 검증)을 NIM 실제 키로 완주 — 모델 102개 실시간 조회, 전체 턴(분류→확인→판정→스트리밍 서사) 즉시 재프롬프트 없이 완주, 저장 파일에 키 문자열 없음을 사람이 직접 확인

## Task Commits

Each task was committed atomically:

1. **Task 1: 제공자 어댑터 네 개를 더해 프로토콜 구현을 다섯으로 채운다** - `f0bd3dc` (feat)
2. **Task 2: 역할별 제공자·모델 선택과 그 선택의 영속화** - `a5c0163` (feat)
3. **Task 3: 진짜 키로 살아 있는 모델 목록을 사람이 직접 확인한다** — checkpoint, no commit (NIM 실제 키로 사람이 직접 승인)

**Plan metadata:** (다음 커밋에서 이 SUMMARY.md·STATE.md·ROADMAP.md·REQUIREMENTS.md를 묶음)

## Files Created/Modified

- `src/gptrpg/agents/providers/openai_provider.py` - `OpenAIProvider`(위임 대상)
- `src/gptrpg/agents/providers/nim_provider.py` - `NimProvider`(위임 방식으로 재작성)
- `src/gptrpg/agents/providers/openrouter_provider.py` - `OpenRouterProvider`(귀속 헤더)
- `src/gptrpg/agents/providers/gemini_provider.py` - `GeminiProvider`(google-genai)
- `src/gptrpg/agents/providers/__init__.py` - `PROVIDER_FACTORIES` 다섯 자리 완성
- `src/gptrpg/agents/providers/base.py` - `Provider`에 `@runtime_checkable`
- `src/gptrpg/agents/config.py` - `AgentChoice`/`save_config`/`load_config`/`resolve_provider`
- `src/gptrpg/cli/main.py` - `agents select`/`agents show`, `turn`의 역할별 독립 해석
- `pyproject.toml`/`uv.lock` - `google-genai` 의존성
- `.gitignore` - `.gptrpg/` 추가
- `tests/test_providers.py` - 어댑터 등록·프로토콜 시험 14개
- `tests/test_agent_config.py` - 영속화·CLI 시험 12개

## Decisions Made

- `NimProvider`를 위임 방식으로 재작성(03-01의 복제 구현 대신) — 이유는 위 `key-decisions` 참조
- `google.genai` 서명을 구현 전에 실제로 확인 후 작성
- OpenRouter 귀속 헤더 방어적 부착
- `turn`의 `--provider`/`--model`은 "둘 다 있으면 양쪽 역할에 적용, 둘 다 없으면 역할별 저장값" 규칙으로 하위 호환 유지

## Deviations from Plan

### Auto-fixed Issues

None beyond the pre-planned reconciliation documented below — no bugs found requiring Rule 1/2/3 fixes during this plan's execution.

### Reconciliation (per prior plan's explicit handoff note, not a Rule 1-3 auto-fix)

**1. NimProvider 재작성 — 복제 구현에서 위임 구조로**
- **Trigger:** 03-01-SUMMARY.md가 명시적으로 남긴 핸드오프 노트: "03-02는 이 파일을 새로 만들지 말고 이어받아 검증·확장해야 한다"
- **Found during:** Task 1 착수 전 필수 읽기(03-01-SUMMARY.md, 03-02-PLAN.md 대조)
- **Issue:** 03-01이 앞당겨 만든 `NimProvider`는 `OpenAIProvider`가 아직 없었으므로 OpenAI chat-completions 호출 로직을 파일 안에 직접 복제했다. 이 계획의 원래 설계(PLAN.md Task 1 action)는 "OpenAIProvider를 기본 주소만 바꿔 만들어 위임한다"였다
- **Fix:** `OpenAIProvider`를 새로 만든 뒤 `NimProvider`를 위임 구조로 재작성 — 복제된 로직 삭제, `self._delegate = OpenAIProvider(api_key, base_url=NIM_BASE_URL)` 패턴으로 전환
- **Files modified:** `src/gptrpg/agents/providers/nim_provider.py`
- **Verification:** 기존 자동 시험(`tests/test_turn_tracer.py`, NIM 관련 로직을 직접 시험하진 않지만 `Provider` 프로토콜 계약을 통해 간접 검증)과 이 계획의 새 `tests/test_providers.py`가 전부 통과. 03-01이 이미 라이브로 검증한 것과 같은 엔드포인트·호출 모양이므로 동작 변경 없음
- **Committed in:** `f0bd3dc`

**Impact on plan:** No scope creep — this was explicit prior-plan guidance, applied exactly as instructed. Behavior parity with 03-01's live-verified NIM path was preserved; only the internal structure changed (duplication → delegation).

## Issues Encountered

None. Checkpoint (Task 3) required one round-trip conversation to close a coverage gap: the live run happened to pick the same model for both roles (user has only one provider key), so D-32's "two roles hold *different* values" wasn't visually demonstrated end-to-end. This was flagged to the user during the checkpoint; they reviewed the tradeoff (automated tests already prove per-role independence with two distinct stub providers) and approved without a re-run. See coverage entry D7's `rationale` and D11 for the two items this leaves flagged.

## User Setup Required

**External services require manual configuration.**
- This plan's `user_setup` lists all five provider env vars. The user has `NVIDIA_API_KEY` set (used for Task 3's live verification) but not `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`GEMINI_API_KEY`/`OPENROUTER_API_KEY`. Task 3 was completed successfully against NIM alone; OpenRouter's attribution-header behavior (RESEARCH.md Assumption A4) and OpenAI/Gemini's live model-list/call paths remain unverified against real traffic — flagged below and in WINDOWS.md.

## Next Phase Readiness

- All five `Provider` adapters are registered and satisfy the protocol; `agents select`/`agents show`/`turn`'s per-role resolution are stable building blocks for 03-03 (timeout/retry wrapping `provider.complete`/`stream`) and 03-04 (confidence-tiered confirm UX consuming `classify()`'s `Proposal`).
- **Not yet built, by design (03-03/03-04's explicit scope, unchanged from 03-01's readiness note):** D-26 (5s dot-progress), D-27/D-28/D-29 (timeout+retry+no-move fallback), D-34/D-35/D-36 (three-tier confirm UX).
- **Left unverified against real network traffic (flagged, not blocking):** OpenAI's and Gemini's `list_models()`/`complete()`/`stream()` paths, and OpenRouter's attribution-header requirement (RESEARCH.md Assumption A4) — the user's environment only has an NVIDIA_API_KEY, so only NIM was live-verified in this plan's Task 3. Recorded in `.planning/WINDOWS.md` as an open item for whenever a second provider key becomes available.
- No blockers for continuing phase 3's remaining plans.

---
*Phase: 03-ai*
*Completed: 2026-08-02*

## Self-Check: PASSED

All 14 files claimed as created/modified exist on disk; both task commit hashes (`f0bd3dc`, `a5c0163`) verified present in `git log --oneline --all`. `.planning/WINDOWS.md` ledger entry recorded (id 2, `unrun-verify`, open) for the OpenRouter attribution-header assumption (A4) left unconfirmed against real network traffic.

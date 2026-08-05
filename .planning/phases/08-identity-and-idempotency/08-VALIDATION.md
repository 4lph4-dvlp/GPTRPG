---
phase: 8
slug: identity-and-idempotency
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-06
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded by `/gsd-plan-phase 8` from `08-RESEARCH.md` § Validation Architecture.
> Task-level rows are filled by `/gsd-validate-phase` once PLAN.md task IDs exist.
>
> **이 단계의 특성:** 요구사항 10개 전부 코드로 자동 검증 가능하다(운영 활동이 섞인 Phase 5와
> 다르다). 단, `.gptrpg/events.db`의 세션1 실사건 895건을 판 5 리듀서로 읽는 스모크 확인은
> 일반 유닛 테스트와 별도로 phase gate에서 챙겨야 한다(RESEARCH.md Pitfall 2).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest `>=9.1.1` + pytest-asyncio `>=1.4.0` (기존 dev dependency) [VERIFIED: pyproject.toml:46-49] |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (기존, 줄 51-53) — `testpaths=["tests"]`, `asyncio_mode="auto"` |
| **Quick run command** | `uv run pytest tests/test_session_actor.py tests/test_web_actions.py tests/test_web_characters.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | RESEARCH.md에 실측치 없음 — 계획 단계에서 `time uv run pytest -q`로 베이스라인을 재측정 권고 |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/test_session_actor.py tests/test_web_actions.py tests/test_web_characters.py -q`
- **After every plan wave:** `uv run pytest -q` (전체 스위트 green 유지)
- **Before `/gsd-verify-work`:** 전체 스위트 green + `.gptrpg/events.db` 복제본을 판 5 리듀서로 읽었을 때 예외 없음 스모크 확인(Pitfall 2)
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

Task IDs are assigned during planning; this table is seeded at the requirement level and
re-keyed to `08-{plan}-{task}` by `/gsd-validate-phase`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | TRUST-01 | Spoofing / Info. Disclosure | 서명 없이 조작한 쿠키가 검증에서 거부된다; `hmac.compare_digest` 타이밍 안전 비교 | unit(web) | `pytest tests/test_web_characters.py -k signed_cookie -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | TBD | TRUST-02 | Spoofing | 요청 body의 character_id ≠ 쿠키의 character_id면 declare/confirm이 라우트 계층에서 거부된다 | unit(web) | `pytest tests/test_web_actions.py -k identity_mismatch -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | TBD | TRUST-03 | Spoofing / Elevation of Privilege | 라우트를 우회해 직접 `actor.submit`해도 액터 계층에서 소유권 불일치가 거부된다(서버 재시작 후에도) | unit(actor) | `pytest tests/test_session_actor.py -k owner_mismatch -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | TBD | TRUST-04 | Repudiation | `CheckResolved`에 person_id·character_id가 필수 칸으로 남아 사건 사슬을 안 거슬러도 "누구의 판정인가"를 안다 | unit(schema) | `pytest tests/test_session_actor.py -k check_resolved_has_actor -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | TBD | TRUST-05 | Tampering (게임 상태 무결성) | 같은 declare_seq를 두 번 확인해도 판정 사건이 하나만 남는다(주사위 재굴림 없음) | unit(actor) | `pytest tests/test_session_actor.py -k idempotent_confirm -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | TBD | TRUST-06 | — (신뢰성, STRIDE 대상 아님) | 서사 생성만 실패하면 응답에 이미 나온 판정 결과가 그대로 남고, 재시도는 판정을 재사용한다 | integration(web) | `pytest tests/test_web_actions.py -k narration_retry_reuses_roll -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | TBD | QUAL-04 | Input Validation | `SelectCharacterRequest.character_id` 길이 초과 요청이 422로 거부된다(`MAX_ID_LEN` 재사용) | unit(web) | `pytest tests/test_web_characters.py -k max_length -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | TBD | QUAL-05 | Information Disclosure | 신원/점유 예외 문구에 쿠키 값·비밀 열쇠·서명이 포함되지 않는다 | unit(web) | `pytest tests/test_web_characters.py -k no_secret_leak -x` | ❌ Wave 0 | ⬜ pending |
| TBD | TBD | TBD | TEST-01 | — (회귀 방지) | 실제 캐릭터 여러 명(가짜 "p1" 아님)으로 도는 통합 테스트가 있고, 각자의 발화에 각자의 이름이 붙는다 | integration | `pytest tests/test_web_actions.py -k multi_character_names -x` | ❌ Wave 0(픽스처 자체가 이번 단계 산출물) | ⬜ pending |
| TBD | TBD | TBD | TEST-02 | Tampering / Repudiation (동시 요청) | 겹치는 확인 요청·겹치는 점유 요청이 결정적으로(non-flaky) 재현된다(actor-level `asyncio.gather` + HTTP-level `httpx.AsyncClient`) | integration(actor+http) | `pytest tests/test_session_actor.py tests/test_web_characters.py -k concurrent -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**이 단계의 숨은 위험은 침입이 아니라 "재시작 후 조용한 무력화"다.** RESEARCH.md Pitfall 1 —
`ActionDeclared`/`ActionConfirmed`가 지금 `character_id`를 담지 않아, 이 칸을 스키마에 추가하지
않으면 TRUST-03 검증이 서버 재시작 직후부터 근거를 잃는다(과잉 거부 또는 검증 무력화 중 하나로
나타남). 두 번째 위험은 Pitfall 2 — 판 5 리듀서가 판 2~4의 실제 세션1 기록(895건)을 읽을 때
`character_id` 없는 옛 사건을 만나 예외를 던지면 안 된다.

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — 다중 캐릭터 픽스처(TEST-01), 서명된 쿠키를 발급하는 테스트 헬퍼
- [ ] `tests/test_web_characters.py` — 서명 쿠키·점유 충돌·길이 상한·비밀 미노출 테스트 신설
- [ ] `tests/test_web_actions.py` — 신원 대조·서사 실패 후 판정 재사용·다중 캐릭터 이름 통합 테스트 신설
- [ ] `tests/test_session_actor.py` — 소유권/멱등성/점유 명령 단위 테스트 + `asyncio.gather` 동시성 테스트 신설
- Framework install: 불필요(기존 pytest/pytest-asyncio/httpx로 충분) [VERIFIED: RESEARCH.md § Environment Availability]

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification (RESEARCH.md § Phase Requirements → Test Map covers all 10 REQ-IDs with automated commands).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

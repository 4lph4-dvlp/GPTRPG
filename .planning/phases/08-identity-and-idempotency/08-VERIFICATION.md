---
phase: 08-identity-and-idempotency
verified: 2026-08-06T00:00:00Z
status: passed
score: 30/30 must-haves verified (30 plan-level truths across 4 plans) + 5/5 roadmap success criteria
behavior_unverified: 0
overrides_applied: 0
---

# Phase 8: 신원 검증과 멱등성 Verification Report

**Phase Goal:** 누가 어떤 캐릭터로 무엇을 선언·확인했는지 서버가 위조 불가능하게 확인하고, 같은 선언에 대한 재시도가 두 번 처리되지 않는다
**Verified:** 2026-08-06
**Status:** passed
**Re-verification:** No — initial verification

## Method

This is not a SUMMARY-trust review. I read all four PLAN.md files' `must_haves` frontmatter (truths/artifacts/key_links/prohibitions), read the actual source (`cookie_auth.py`, `routes_characters.py`, `routes_actions.py`, `session_actor/actor.py`, `rules_core/reducer.py`, `event_log/schema.py`) line-by-line against those claims, and **executed the code myself**: full test suite, targeted `-k` selections for every named gate (`identity_tracer`, `occupy`, `occupancy`, `idempotent_confirm`, `narration_retry_reuses_roll`, `concurrent` ×3 consecutive runs, `multi_character_names`, `max_length`, `no_secret_leak`), `lint-imports`, `ruff check`, the real `.gptrpg/events.db` (895-record, schema-2) replay smoke test, and `cd frontend && npm run build`. All passed live in this session — not merely cited from SUMMARY.md.

## Goal Achievement — Roadmap Success Criteria

| # | Success Criterion | Status | Evidence |
|---|---|---|---|
| 1 | 다른 사람의 character_id로 행동을 선언/확인하면 서버가 거부한다 — 라우트 계층과 SessionActor 양쪽 대조 | ✓ VERIFIED | `routes_actions.py:191-193,332-334` — `read_identity()` cross-check at top of `declare()`/`confirm()`, 403, no event. `actor.py:457-475` — `_prepare_confirm` independently checks `declare_owners[caused_by_seq]` against `command.character_id`. Live-ran `test_identity_tracer.py::test_actor_level_ownership_check_rejects_bypassing_route` and `..._survives_actor_restart` (bypasses route, calls `actor.submit` directly, then rebuilds via a fresh `SessionRegistry`) — both pass. |
| 2 | 판정 기록에 「누구의 판정인가」가 필수 항목으로 남는다 (사건 사슬을 안 거슬러도 앎) | ✓ VERIFIED | `schema.py:124-145` — `CheckResolved.person_id`/`character_id`, enforced by `@model_validator(mode="after")` when `schema_version >= 5`. Fields sit directly on the event, no traversal needed. `test_check_resolved_records_person_id_and_character_id` passes. |
| 3 | 확인 재시도가 주사위를 다시 굴리지 않고, 서사만 실패하면 기존 판정 결과가 그대로 응답에 돌아온다 — 굴림 실패와 서사 실패가 구분됨 | ✓ VERIFIED | `actor.py:457-499` `AlreadyConfirmed` short-circuit (no new `action_confirmed` event on same move/stat) + `actor.py:541-556` `AlreadyResolved` second-tier guard (closes a TOCTOU the route-level cache-reuse alone left open — discovered and fixed mid-plan, confirmed present in code). `routes_actions.py` `ConfirmResponse.narration_failed` returns 200 + cached `rolls`/`grade`/`target` on narration failure; roll-submission failure still returns an error status with no `rolls`. Live-ran `test_narration_retry_reuses_roll_and_only_narration_appended_grows` and `test_check_submission_failure_returns_error_status_with_no_rolls` — pass. No `status_code=502` remains in `routes_actions.py` (confirmed via grep). |
| 4 | 실제 캐릭터 여러 명(가짜 상수 아님)으로 도는 테스트와 겹치는 요청을 재현하는 테스트가 있어 CI가 재발을 잡는다 | ✓ VERIFIED | `"p1"` count is 0 in `tests/conftest.py`, `tests/test_web_actions.py`, `tests/test_session_actor.py` (the three files the plan scoped as identity-meaningful — confirmed by grep). Live-ran `test_multi_character_names_two_characters_get_distinct_labels`/`_four_characters_all_appear` (asserts **distinct** name labels, not merely "a name exists"). Live-ran `-k concurrent` (8 tests) three consecutive times, all pass every time, covering both actor-layer (`asyncio.gather`) and HTTP-layer (`httpx.AsyncClient`+`ASGITransport`) races for occupancy and confirm. |
| 5 | API 요청 입력 길이 상한이 빠짐없이 걸리고, 예외 메시지가 자격 증명을 실어 나르지 않는다 | ✓ VERIFIED | `routes_actions.py` `ConfirmRequest.target` (`ge=MIN_TARGET, le=MAX_TARGET`), `rulebook_id` (`max_length=MAX_ID_LEN` on both `DeclareRequest`/`ConfirmRequest`), `modifiers` (list `max_length=MAX_MODIFIERS_COUNT` + item `max_length=MAX_MODIFIER_LEN`); `routes_characters.py` `SelectCharacterRequest.character_id` (`max_length=MAX_ID_LEN`). Live-ran `-k max_length` (5 tests) and `-k no_secret_leak` (2 tests) — pass. |

**Score:** 5/5 roadmap success criteria verified by direct code inspection + live test execution (not SUMMARY citation).

## Plan-Level Must-Haves (frontmatter truths, all 4 plans)

| Plan | Truths | Verified | Notes |
|---|---|---|---|
| 08-01 (identity tracer) | 8 (incl. 1 backstop) | 8/8 | Backstop (895-record replay) live-ran: `test_real_events_db_replay_smoke_test_folds_without_exception` passes against the actual `.gptrpg/events.db` on disk (360KB, present). |
| 08-02 (occupancy) | 7 (incl. 1 backstop) | 7/7 | Backstop (bypass-route `actor.submit(OccupyCharacter(...))`) confirmed by reading `test_session_actor.py`'s `occupy` group, which submits directly to the actor. |
| 08-03 (idempotency) | 9 (incl. 1 backstop) | 9/9 | Backstop confirmed via `test_concurrent_confirm_same_move_exactly_one_action_confirmed_event`, which bypasses the route and calls `actor.submit(ConfirmAction(...))` twice directly. |
| 08-04 (fixtures/caps) | 6 (incl. 1 backstop) | 6/6 | See **Finding F-1** below — one *task-level acceptance criterion* (not a frontmatter truth) does not hold as literally written, though the frontmatter truth itself is satisfied. |

**Total: 30/30 must-have truths verified.**

### Key Links (spot-checked against source, not SUMMARY)

| From | To | Verified |
|---|---|---|
| `cookie_auth.sign_cookie` → `select_character`'s `Set-Cookie` → `routes_actions.declare/confirm`'s `read_identity` → `cookie_auth.verify_cookie` | Single verification chain | ✓ — confirmed in `routes_actions.py:191,332` (`read_identity` import used at both call sites) and `cookie_auth.py:106-127` (`read_identity` docstring explicitly names both callers) |
| `routes_actions` `character_id` → `DeclareAction.character_id` → `ActionDeclared.character_id` → `reducer.declare_owners[seq]` → `_prepare_confirm` ownership check | Survives restart | ✓ — confirmed in `reducer.py:131-144` (only writes when payload has the field, "모른다" not guessed) and `actor.py:473-475` |
| `EVENT_SCHEMA_VERSION = 5` ↔ `reducer.apply_event`'s 판 5 branch | Same commit | ✓ — both present; `character_occupied` branch exists in `reducer.py:243-245`; grep count 2 (declaration + apply-branch use) |
| `select_character` → `actor.submit(OccupyCharacter(...))` → `_prepare_occupy` → `character_occupied` event → `reducer.occupied_by` → next `_prepare_occupy` | Self-reinforcing loop, survives restart | ✓ — confirmed in `routes_characters.py:190-203` and `actor.py:501-539` |
| `action_confirmed.caused_by_seq` → `GameState.confirmed_declares` → `_prepare_confirm` idempotent short-circuit → route's `AlreadyConfirmed` handling → cached `check_resolved` reuse | Retry doesn't re-roll | ✓ — confirmed in `reducer.py:154-171`, `actor.py:482-486`, `routes_actions.py:371-383` |
| `check_resolved.caused_by_seq` (=confirm_seq) → `confirm_to_declare` → that declare's `resolve_seq` | Retry knows which roll to reuse | ✓ — confirmed in `reducer.py:181-198` |
| `ConfirmResponse.narration_failed` (server) ↔ `frontend/src/api/types.ts` ↔ `ChatPane.resolve()` branch | Contract doesn't silently drift | ✓ — `types.ts` has the field, `ChatPane.tsx` reads it and routes through the existing `onTurnFailed`/`setStatus` path; `npm run build` passes (live-ran, exit 0) |

### Prohibitions (spot-checked)

All prohibitions across the four plans were checked against source and hold: no fallback to unsigned-cookie trust on verification failure (`cookie_auth.verify_cookie` returns `None`, never partial-trust); no route-only check without an actor-layer counterpart (confirmed for identity, occupancy, and both idempotency tiers — `AlreadyConfirmed` *and* `AlreadyResolved`); no owner-guessing for pre-판5 records (`reducer.py:131-139` only assigns when the field exists in the payload); no release/unoccupy path anywhere in `session_actor/` or `rules_core/` (grep confirms no delete/pop site); no `browser_id`/holder identity leaked into rejection text (confirmed by reading `_prepare_occupy`'s messages and by live-running the `no_secret_leak` tests); no idempotency key introduced beyond `declare_seq`/`caused_by_seq` (confirmed — no new request-id field anywhere in the diff).

## Live Test Execution (run in this session, not cited from SUMMARY)

| Check | Command | Result |
|---|---|---|
| Full suite | `uv run pytest -q` | **534 passed** |
| lint-imports | `uv run lint-imports` | 4/4 contracts kept |
| ruff | `uv run ruff check src/gptrpg` | All checks passed |
| Identity tracer + legacy replay | `pytest tests/test_identity_tracer.py tests/test_event_log.py -k "restart or check_resolved or real_events_db or legacy"` | 20 passed |
| Concurrent (×3 consecutive) | `pytest -k concurrent -q` ×3 | 8 passed, 8 passed, 8 passed — no flake |
| Multi-character name attribution | `pytest tests/test_web_actions.py -k multi_character_names` | 2 passed |
| Secret hygiene | `pytest -k no_secret_leak` | 2 passed |
| Input caps | `pytest -k max_length` | 5 passed |
| Schema version | `python -c "assert EVENT_SCHEMA_VERSION == 5"` | exit 0 |
| Frontend build | `cd frontend && npm run build` | exit 0 |
| `.gptrpg/events.db` present, unmodified by test run | `ls -la` before/after | 360448 bytes, real file on disk, replay test passes against it |

## Requirements Coverage

All 10 phase-owned requirement IDs (TRUST-01…06, QUAL-04, QUAL-05, TEST-01, TEST-02) are declared across the four plans' frontmatter, cross-referenced against `.planning/REQUIREMENTS.md`, and marked `[x]` there with `Phase 8 | Complete`. No orphaned requirements — the union of the four plans' `requirements:` fields exactly matches the phase's requirement set with no gaps and no extras.

| Requirement | Plan(s) | REQUIREMENTS.md | Evidence |
|---|---|---|---|
| TRUST-01 | 08-01, 08-02 | [x] Complete | Signed cookie + occupancy both close this |
| TRUST-02 | 08-01 | [x] Complete | route-layer 403 on mismatch |
| TRUST-03 | 08-01 | [x] Complete | actor-layer ownership check, restart-survives |
| TRUST-04 | 08-01 | [x] Complete | `CheckResolved.person_id`/`character_id` required |
| TRUST-05 | 08-03 | [x] Complete | `AlreadyConfirmed` short-circuit |
| TRUST-06 | 08-03 | [x] Complete | `narration_failed`, roll-vs-narration distinction |
| QUAL-04 | 08-01, 08-04 | [x] Complete | input caps swept, closed 4 gaps |
| QUAL-05 | 08-01, 08-04 | [x] Complete | no-secret-leak gates, both files |
| TEST-01 | 08-04 | [x] Complete | real-character fixtures, distinct-label test |
| TEST-02 | 08-02, 08-03, 08-04 | [x] Complete | concurrent tests at both layers |

## Findings (non-blocking — weighed against goal achievement, not deferred to review severity labels alone)

### F-1 (new finding, not in 08-REVIEW.md): 08-04's Task 1 acceptance criterion "`grep -rn '\"p1\"' tests/ | wc -l` < 44" does not literally hold

I measured this myself: the baseline before Phase 8 (commit `973d415~1`) was exactly 44 occurrences of `"p1"` across `tests/`. After all four plans, the count is **46**, not below 44 — the opposite of what the acceptance criterion demanded. Root cause: 08-01's Task 2 made `ResolveCheck.person_id`/`character_id` unconditionally required at the actor layer, which forced every direct `ResolveCheck`/`CheckResolved` construction site across the suite (including non-identity-meaningful files like `test_measurement.py`, `test_report.py`, `test_tracer_d100.py`, `test_imagery.py`, `test_session_actor_auto_advance.py`, `test_prompt_assembly_scenario.py`, `test_turn_flow_failure.py`, `test_web_events.py`) to supply a value, and the executor filled `person_id="p1"` as a stand-in (matching the existing `player_id="p1"` convention already present in those unrelated files) — adding 19 new occurrences while only 17 were removed from the three identity-meaningful files.

**Does this affect the phase goal?** No. The plan's own scope decision ("바꿨을 때 시험의 뜻이 달라지면 신원이고, 안 달라지면 토큰이다") explicitly excludes non-identity-meaningful files from the TEST-01 replacement scope, and by that stated criterion the newly-added `"p1"` fills in unrelated files are legitimate opaque tokens, not identity. The frontmatter `must_have` truth ("신원이 뜻을 갖는 시험이... bram/nari/seon/hodu로 돈다") is satisfied — confirmed 0 occurrences in the three scoped files. But 08-04-SUMMARY.md's claim "Deviations from Plan: None - plan executed exactly as written" is **not accurate** for this specific, mechanically-checkable Task 1 acceptance criterion — it would have failed if run. This is a SUMMARY-accuracy gap I'm flagging directly (per this agent's adversarial mandate), not a phase-goal gap.

### F-2 (from 08-REVIEW.md WR-01, my own judgment applied): `my_character()` re-implements `read_identity()` instead of calling it

Confirmed by reading `routes_characters.py:228-245` — the function does its own inline `verify_cookie`/session-id/character-id parse instead of calling `cookie_auth.read_identity()`, directly contradicting `read_identity()`'s own docstring claim ("이 함수가 이 프로젝트의 유일한 신원 검증 경로다... `my_character`와 `declare`/`confirm`이 전부 이 함수를 거친다"). **My judgment:** this is a real contradiction between a docstring's stated invariant and the actual code, and a genuine duplication-maintenance risk, but `my_character()` is a read-only status endpoint that never writes an event or grants access to anything — it is not in the enforcement path for any of the five roadmap success criteria (all five are about `declare`/`confirm`/`select-character`, all of which do route through `read_identity()`, confirmed by import + call-site inspection). Today's divergence (missing `browser_id` type-check, extra `get_character` check) is not exploitable — both `my_character()`'s and `read_identity()`'s checks are strictly *more* restrictive than "any signed cookie for this session," not less. Non-blocking.

### F-3 (from 08-REVIEW.md WR-02, my own judgment applied): confirm-idempotency short-circuit can report `confirmed: false` while the event log holds an accepted+resolved check

Confirmed by reading `actor.py:482-486` (dedup keys only on move/stat, not `player_confirmed`) and `routes_actions.py:395-400` (`if not body.confirmed: return ConfirmResponse(confirmed=False, ...)` fires unconditionally, even when `prior_confirm` came from a true `AlreadyConfirmed` reuse). Reachable in a genuine two-tab-same-cookie race (tab A accepts, stale tab B's reject click lands after). **My judgment:** the persisted event log stays correct in all cases (this is a response-shaping bug, not a data-integrity bug), and none of 08-03's must-have truths or prohibitions literally cover this specific accept-then-stale-reject scenario — the phase's TRUST-05 truth ("판정 사건은 하나만 남는다") holds regardless. It does not violate roadmap SC #3 as worded (that SC is specifically about the narration-failure-retry scenario, which is correctly handled and tested). This is a real edge-case correctness gap worth fixing but it does not block phase-goal achievement. Recommend tracking via 08-REVIEW.md's existing fix suggestion in a follow-up task.

### F-4/F-5 (from 08-REVIEW.md WR-03/WR-04, info only)

WR-03 (frontend reject-path error-swallow) and WR-04 (unguarded second `actor.submit` in `declare()`) are both real but (a) pre-existing/explicitly-scoped-out by 08-03's own plan text ("catch 블록은 그대로 둔다"), and (b) outside the five roadmap success criteria's literal scope (WR-04 concerns `action_classifier` `RecordAiCall` bookkeeping robustness, not identity/idempotency). Non-blocking, tracked in 08-REVIEW.md.

## Anti-Pattern Scan

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any of the ten phase-touched production files (`schema.py`, `reducer.py`, `cookie_auth.py`, `app.py`, `routes_characters.py`, `routes_actions.py`, `actor.py`, `types.ts`, `ChatPane.tsx`, `labels.ts`) — checked directly via grep, not cited.

## Human Verification Required

None. All five roadmap success criteria are backend-observable behaviors with deterministic automated coverage that I executed myself in this session (not SUMMARY citations). The one frontend-adjacent item (narration-failure display routing through `ChatPane`'s existing failure path) is verified by a passing TypeScript build plus code inspection showing the value is actually read and branched on — no subjective/visual judgment is required to confirm wiring, and Phase 16 (FE-03) is explicitly where copy/layout polish is scoped.

## Gaps Summary

No gaps block phase-goal achievement. Four non-blocking findings are recorded above (F-1 through F-5) — one newly discovered by this verification (F-1, a SUMMARY-accuracy issue on a task-level acceptance criterion, not a phase-goal gap), and three carried forward from 08-REVIEW.md with my own judgment applied against the phase's actual must-haves and roadmap success criteria (all judged non-blocking, consistent with the review's own severity classification). Recommend a small follow-up task (not required before proceeding) to: (1) make `my_character()` call `read_identity()` per its own docstring's claim, (2) have `_prepare_confirm`/the route branch on `prior_confirm is not None` before consulting `body.confirmed` so the response always reports the actually-recorded outcome.

---

_Verified: 2026-08-06_
_Verifier: Claude (gsd-verifier)_

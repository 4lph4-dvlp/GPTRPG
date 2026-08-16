---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: 돌아가는 프로토타입
current_phase: 11
current_phase_name: rulebook-vocabulary
status: executing
stopped_at: Completed 11-04-PLAN.md
last_updated: "2026-08-16T11:30:35.026Z"
last_activity: 2026-08-15
last_activity_desc: Phase 11 execution started
progress:
  total_phases: 11
  completed_phases: 3
  total_plans: 22
  completed_plans: 20
  percent: 27
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-05)

**Core value:** 이야기가 어떻게 끝나는지 보고 싶어서 일주일 뒤에 다시 접속한다
**Current focus:** Phase 11 — rulebook-vocabulary

> ⚠️ **킬 크리테리아 실험은 보류다 (D-62).** 세션1(2026-08-04)이 답한 것은 「재미있나」가 아니라 「도구가 망가져서 잴 수가 없다」였다. EXP·HYP를 로드맵에서 내리고 코어 완성에 집중한다. 자동 계측은 코드에 그대로 남아 관찰값으로 쌓인다. 근거는 `docs/session1-code-review.md`.

## Current Position

Phase: 11 (rulebook-vocabulary) — EXECUTING
Plan: 6 of 7
Status: Ready to execute
Last activity: 2026-08-15 — Phase 11 execution started

> 라우팅 정정: `phase.complete`가 12.1을 다음으로 골랐으나 12.1은 ROADMAP상 **Phase 11·12에 의존**한다
> (「담을 그릇 — 자원 축 표현」·「StatEntry 쓰기 경로」). 11·12는 아직 단계 디렉터리가 없어
> 도구가 건너뛴 것이므로 로드맵 순서대로 11을 다음으로 되돌렸다.

Progress: [█████████░] 91%

## Performance Metrics

**Velocity:**

- Total plans completed: 33 (M0 누적)
- Average duration: -
- Total execution time: 0.0 hours (v1.1 기준 — 아직 실행 없음)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 (M0) | 6 | - | - |
| 02 (M0) | 4 | - | - |
| 03 (M0) | 6 | - | - |
| 04 (M0) | 6 | - | - |
| 05 (M0) | 4/6, 보류 | - | - |
| 08 | 4 | - | - |
| 10 | 7 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P02 | 55min | 2 tasks | 14 files |
| Phase 01 P03 | 25min | 2 tasks | 4 files |
| Phase 01 P04 | 16min | 2 tasks | 4 files |
| Phase 01 P05 | 20min | 2 tasks | 2 files |
| Phase 01 P06 | 65min | 3 tasks | 6 files |
| Phase 02 P01 | 40min | 3 tasks | 19 files |
| Phase 02 P02 | 45min | 3 tasks | 5 files |
| Phase 02 P03 | 25min | 2 tasks | 5 files |
| Phase 02 P04 | 10min | 3 tasks | 3 files |
| Phase 03 P01 | 95min | 3 tasks | 17 files |
| Phase 03 P02 | 50min | 3 tasks | 13 files |
| Phase 03 P03 | 25min | 3 tasks | 5 files |
| Phase 03 P04 | ~180min | 3 tasks | 12 files |
| Phase 03 P05 | 15min | 2 tasks | 3 files |
| Phase 03 P06 | 45min | 3 tasks | 13 files |
| Phase 08 P01 | unspecified | 4 tasks | 20 files |
| Phase 08 P02 | unspecified | 3 tasks | 5 files |
| Phase 08 P03 | 20min | 4 tasks | 8 files |
| Phase 08 P04 | 13min | 3 tasks | 5 files |
| Phase 09 P01 | ~3h (2 sessions, interrupted+resumed) | 3 tasks | 19 files |
| Phase 09 P02 | ~45min | 3 tasks | 19 files |
| Phase 09 P03 | ~12min | 3 tasks | 20 files |
| Phase 09 P04 | ~15min | 2 tasks | 5 files |
| Phase 10 P01 | 40min | 2 tasks | 16 files |
| Phase 10 P02 | ~20min | 3 tasks | 3 files |
| Phase 10-ai P05 | ~35min | 3 tasks | 10 files |
| Phase 10 P03 | ~50min | 2 tasks | 7 files |
| Phase 10-ai P04 | ~40min | 3 tasks | 6 files |
| Phase 10-ai P06 | ~25min | 2 tasks | 6 files |
| Phase 10 P07 | ~20min | 3 tasks | 7 files |
| Phase 11 P01 | ~45min | 2 tasks | 15 files |
| Phase 11 P02 | ~35min | 3 tasks | 5 files |
| Phase 11 P03 | ~25min (Task1-2) + checkpoint overnight wait | 3 tasks | 5 files |
| Phase 11 P05 | ~20min | 3 tasks | 11 files |
| Phase 11 P04 | ~50min | 3 tasks | 14 files |

## Accumulated Context

### Decisions

전체 결정 목록은 PROJECT.md의 Key Decisions 표에 있다. D1~D33은 전부 잠금이며 권위는 `docs/GPTRPG-M0-decisions.md` 한 곳이다.

지금 작업에 직접 걸리는 것:

- 사건을 순서대로 기록하는 구조가 **M0의 유일한 되돌릴 수 없는 결정**이다. 제자리 수정 방식으로 먼저 짜면 되돌릴 수 없다
- 주사위와 판정에 AI가 끼어드는 지점을 만들지 않는다. AI는 닫힌 목록에서 고르는 일과 서술만
- 프롬프트 조립 순서를 안정성 순서로 짜는 것은 최적화가 아니라 설계 제약이다 (캐싱 유무가 원가를 3.7배 가른다)
- M0은 최상급 모델 고정 — 재는 것은 원가가 아니라 품질 상한선이다
- 실행 환경 = Python 백엔드 + TypeScript 프런트엔드. **원본 문서가 아니라 이번 정리에서 새로 고른 결정이다**
- [ROADMAP] 2026-08-05: v1.1 로드맵 확정 — Phase 번호는 6에서 끊기지 않고 7부터 이어진다.
  RULE-01(D-20 재논의)·MEM-01(D-31 재논의)을 Phase 7 하나로 묶어 가장 먼저 배치(코드 없음).
  TRUST 6건 + 멱등성 + 테스트 픽스처 앞단(TEST-01·02)을 Phase 8로 묶어 신원·재시도 문제를
  한 번에 닫는다. RULE-02~08(읽기+쓰기)을 Phase 10 하나로 묶어 C4(능력치 미반영/자원 불변)를
  한 단계에서 닫는다 — 능력치 읽기는 D-20 없이도 시작 가능하지만 같은 파일을 반복해서 열게
  되므로 자원 쓰기와 합쳤다. QUAL 8건은 전부 가장 관련 있는 코드 경로에 흩어 배정했다(단독
  phase를 만들지 않음). TEST는 앞단(01·02, Phase 8)·중간(03, Phase 9 / 04, Phase 10)·
  최종(05, Phase 13) 3곳에 분산 — 픽스처 재작성이 근사-선행이라 앞으로 당기고, 4탭 통합
  테스트는 모든 새 경로가 갖춰진 뒤에만 의미가 있어 맨 뒤에 뒀다. 48개 요구사항 전부 정확히
  하나의 phase에 매핑, 중복·누락 없음(REQUIREMENTS.md Traceability 참조)

- [Phase ?]: 01-02: caused_by_seq(nullable) 필드를 사건 봉투와 events 표에 추가한다 (option-a) — Phase 6의 두 응답 속도 계산이 이 필드에 의존한다
- [Phase ?]: 01-03: 사건 종류를 6종으로 확정(action_declared/action_confirmed/check_resolved/narration_appended/clock_advanced/ai_invoked) — GameEvent가 실제 discriminated union이 됨. apply_event가 모르는 event_type에 UnknownEventType을 던지도록 강화(조용한 무시 방지)
- [Phase ?]: 01-04: 2d6 판정 완성 — flat 수정치 합산(비-FLAT 은 UnsupportedModifier), reroll_2d6 은 앞선 눈을 지우지 않고 이어 붙여 새 두 눈으로만 재계산 (D-16/D-17 구조화)
- [Phase ?]: 01-04: Task 2 엣지 테스트 9개(경계·인접·빈입력·순서·정수성) 첫 실행에 전부 통과 — Task 1이 올바름이 확인되어 판정 코드 고침 없음
- [Phase ?]: 01-04: 정수성 성질 기반 테스트는 type(total) is int 와 total == 눈 합 + 수정치 합 을 정확히 단언 — 부동소수/반올림 경로 자체 부재를 증명
- [Phase ?]: caused_by_seq (01-02 option-a) already existed; all six D-11 numbers producible without a schema change
- [Phase ?]: 01-06 Task 1: SessionActor widened to six commands (DeclareAction/ConfirmAction/ResolveCheck/AppendNarration/AdvanceClock/RecordAiCall) with a shared validate->rules-core->next_seq->append pipeline — validation fully precedes seq acquisition so a rejected command consumes no seq and appends nothing. SessionRegistry.get_or_create(session_id) guarantees one live actor per session id (D-09① first layer). SequenceConflict is forwarded to the caller via a per-command asyncio.Future, never caught-and-discarded.
- [Phase ?]: 01-06 Task 2: CLI submit gained six subcommands (declare/confirm/roll/narrate/clock/ai) sharing --db/--session; submit prints the recorded event's seq (feeds the next command's --caused-by by hand). replay prints ten Korean-labeled GameState fields with no wall-clock/duration values (byte-identical across repeat runs, verified manually). CommandRejected/SequenceConflict become one-line stderr messages with a non-zero exit, never a raw traceback. Deviation (Rule 1): updated tests/test_tracer.py's four argv lists and two label assertions to match the finalized `roll` subcommand and renamed labels ("판정 횟수"->"판정 수", "마지막 등급"->"마지막 판정 등급") — this was the pre-01-06 `--command roll` interface this task's own action text explicitly replaces.
- [Phase ?]: 01-06 Task 3 checkpoint resolved: human approved replay output after clarifying that '틱(tick)' is deliberately not a platform-wide primitive name — it stays expressed as this ruleset's own '위협 시계' vocabulary, so a future rulebook without that clock shape isn't forced into a vocabulary it doesn't have.
- [Phase ?]: 02-01 Task 1 체크포인트(option-a): EVENT_SCHEMA_VERSION 1->2, CheckResolved.counts_as_failure 필수 필드, 리듀서에 판 1 해석 경로 신설 — 이미 쓰인 판 1 기록은 손대지 않는다(D-12)
- [Phase ?]: 02-01: Grade를 event_log/schema.py·rules_core/grading.py 양쪽에서 str로 넓힘(promote) — 던전월드 세 이름은 rulebooks/dungeonworld_like.py의 룰북 내용으로 격하, OpenQuest SRD(CC BY 4.0) 등급 4종이 rulebooks/openquest.py에만 존재
- [Phase ?]: 02-01: 실패 집계(failure_count)가 등급 이름 비교가 아니라 룰북 선언 신호(counts_as_failure)로 계산되도록 reducer.py 재작성 — grading.py의 grade_for_total 자체는 이번 단계에서 고치지 않고 남김(참은 곳, 02-04 인터페이스 변경 문서에서 재확인 필요)
- [Phase ?]: 02-02 고친 곳: resolve_d100 계산 순서를 세 시점(굴리기 전/굴림 자체/굴린 뒤)으로 재구성, T-02-06 대응으로 MAX_BONUS_DICE_MAGNITUDE=20 상한 추가(Rule 2). 참은 곳: Modifier dataclass와 GradeBand/grade_for_margin을 한 글자도 안 고쳤다 — 새 수정치 유형·수치 구간형 등급 선언 모두 기존 자료구조로 표현된다
- [Phase ?]: 02-02: push_d100이 reroll_2d6과 같은 불변식(앞선 눈 보존, 새 눈만으로 재채점)을 물려받음. PushNotPermitted가 룰북 미허가 재굴림을 막음. NUMERIC_BAND_RULEBOOK_BANDS는 tests/test_grading_d100.py 안에서만 선언(세 번째 룰북은 M1로 유지)
- [Phase ?]: 02-03: Entity/StatEntry frozen dataclass 4칸 확정(D-20/D-21), stats 개수 상한 없음. OpenQuest 고블린/스켈레톤 SRD 수치 그대로, EXAMPLE_SINGLE_STAT_FOE는 자체작성 라벨. 참은 것: hp 전용 필드, stats 개수 상한, max 필수화, depleted_effect_ref 자동추론 — 전부 02-04 인터페이스 변경 문서용 증거로 SUMMARY에 기록
- [Phase ?]: 02-04: CLI --rulebook flag added (default DUNGEONWORLD_LIKE_ID imported, not re-typed); _parse_modifier zero-diff proven by roundtrip test. 02-INTERFACE-CHANGES.md written and human-approved: 10 files changed (only _RESOLVERS dispatch table recurs per future rulebook), 7 items resisted-as-data (weighted heavier per D-22), EVENT_SCHEMA_VERSION 1->2 explicit judgment, 4 limitations disclosed. HYP-03 confirmed by human verdict — Phase 2 complete.
- [Phase ?]: 03-01: agents/envelope.py AgentResult는 plain dataclass(pydantic 아님) — 기록에 직접 안 들어가는 메모리 임시 그릇(D-30)
- [Phase ?]: 03-01: gptrpg.agents는 session_actor/event_log를 전혀 import하지 않는다 — CLI가 반환값을 명령으로 조립하는 것이 유일한 경로. .importlinter 계약 3이 코드로 강제(ROADMAP 성공조건 4)
- [Phase ?]: 03-01 [deviation, user-approved]: NimProvider를 03-02에서 03-01로 앞당김 — 사용자에게 ANTHROPIC_API_KEY 없고 NVIDIA_API_KEY만 있어 Task 3을 NIM(meta/llama-3.1-70b-instruct)으로 검증. openai SDK를 base_url 스왑(https://integrate.api.nvidia.com/v1)으로 재사용. 03-02는 이 파일을 새로 만들지 말고 이어받아 검증/확장할 것
- [Phase ?]: 03-01: MEAS-02는 latency_ms/토큰 실측 기록만 이번 계획이 만든다 — D-26 5초 진행표시·D-33 15초 판정우선 UX 임계값은 03-02/03-03 몫, WINDOWS.md에 open 항목으로 기록됨
- [Phase ?]: 03-02: NimProvider를 03-01의 복제 구현에서 위임 구조(OpenAIProvider 감싸기)로 재작성 — 03-01 핸드오프 노트대로 재조정, 동작 변경 없음
- [Phase ?]: 03-02: PROVIDER_FACTORIES 다섯 자리 완성(openai/nim/openrouter/gemini/anthropic) — turn CLI가 역할별로 독립된 provider 인스턴스를 해석(D-32), agents select/show로 D-31/D-33 영속화 완성
- [Phase ?]: 03-03: call_with_one_retry(fn, *, timeout_s) -> tuple[AgentResult, str|None] — 전역 상태 없이 마지막 실패 사유를 선택적 반환 경로로 전달. action_classifier.classify()는 재시도까지 실패해도 예외 없이 candidates=()로 떨어져 기존 '무브 없음' 경로를 재사용(D-29); UnknownMove는 재시도 층 밖에서 즉시 던져져 재시도 대상이 아니다
- [Phase ?]: 03-03: master_gm.narrate()는 스트리밍 전용 재시도 규칙(첫 조각 전 실패는 재시도, 조각이 나간 뒤엔 즉시 종료)을 갖고, provider._last_result를 직접 갈아 끼워 실패를 반영한다 — 다섯 어댑터가 공유하는 내부 관례에 기댄 범위 안 해법(새 프로토콜 메서드 추가는 계획 범위 밖)
- [Phase ?]: 03-03: chunk_sentences()는 여덟 경계 상황을 실행해 이미 정확함을 확인했고 로직을 고치지 않았다 — 도크스트링만 여덟 보장을 명시하도록 확장
- [Phase ?]: 03-04: Proposal.tier(읽기 전용 property, 후보 개수 0/1/2-3/4+ -> none/single/several)만으로 화면 강도를 정한다 — 신뢰도 숫자 칸 자체가 없다(D-16/D-37). MAX_CANDIDATES=3으로 모델이 넷 이상 돌려줘도 화면은 항상 최대 셋
- [Phase ?]: 03-04: cli/main.py의 턴 흐름을 cli/turn_flow.py로 옮겨 세 갈래 확인 화면(D-34/D-35/D-36) + with_progress_dots(D-26, 스레드 하나로 화면만 담당) + 판정 결과가 서사보다 항상 먼저 나가는 흐름 구조(MEAS-02)를 완성. main.py는 인자 파싱·저장소 준비만 하도록 얇아짐
- [Phase ?]: 03-04 [deviation, Task 3 라이브 검증 3왕복에서 발견·수정]: (1) 추론형 모델(NIM Nemotron)의 <think>/코드펜스로 감싼 JSON 응답이 파싱 안 되던 문제를 강건 파서로 수정 (2) max_tokens 4096 추측성 인상을 근거 없음이 드러나 1024로 되돌리고 대신 call_with_one_retry 실패 시 stderr 진단 추가 (3) recent_turns에 화자 표시('플레이어:'/'진행자:')를 붙이고 진행자 프롬프트에 '분석 말고 서사만' 지시문을 추가해 모델이 대화록을 메타 분석하던 오작동 수정 (4) narrate()에 90초 스트림 정지 워치독(_drain_with_stall_timeout) 추가 — 실제 ~22분 터미널 행 재현됨
- [Phase ?]: 03-05: OpenRouter X-Title 헤더를 percent-encoding 대신 ASCII 문자열로 교체 — X-Title은 RFC 8187 확장 필드 문법을 해석하지 않는 평범한 자유 문자열 헤더라 percent-encoding하면 사람이 볼 화면에 깨진 문자열이 남는다
- [Phase ?]: 03-05: 다섯 어댑터를 PROVIDER_FACTORIES로 순회하며 헤더 ASCII 인코딩 가능성을 그물질하는 회귀 시험 패턴 확립 — 여섯 번째 어댑터가 같은 실수를 하면 자동으로 잡힌다
- [Phase ?]: 03-06: Provider 프로토콜에 note_result() 메서드 추가 — 위임 어댑터(nim/openrouter)에서 사적 속성 직접 대입으로 실패 껍데기가 사라지던 것을 고침(03-03이 범위 밖으로 미룬 판단을 실측 근거로 뒤집음, G-03-3 실제 크래시 원인)
- [Phase ?]: 03-06: turn_flow._turn_flow()의 서사 구간을 Exception 포착으로 감싸고 last_result() 무조건 호출을 합성 실패 껍데기 도우미로 교체 — RecordAiCall은 성공/실패 모두 제출(MEAS-02 실패 턴 보존), _cmd_turn의 예외 허용 목록은 넓히지 않음
- [Phase ?]: 08-01 Task 1 checkpoint(approved-scope) 기록: 판 5는 ActionDeclared/ActionConfirmed.character_id(선택)·CheckResolved.person_id/character_id(schema_version>=5 필수)·CharacterOccupied 신설 넷을 한 커밋에 묶는다 — TRUST-03이 서버 재시작을 넘어 성립하는 유일한 범위
- [Phase ?]: 08-01: CookieIdentity/read_identity를 routes_characters.py가 아니라 cookie_auth.py에 둠 — 계획 원문대로 하면 routes_characters<->routes_actions 순환 import가 생겨서 자리를 옮겨 해소함
- [Phase ?]: 08-01: ResolveCheck.person_id/character_id를 액터에서 무조건 필수로 만들면서, 브라우저 쿠키 개념이 없는 CLI(cli/main.py submit roll, cli/turn_flow.py turn)에는 고정 자리표시자('cli' 또는 args.player 재사용)를 채워 기존 CLI 동작을 그대로 보존함
- [Phase ?]: 08-02: OccupyCharacter/_prepare_occupy — D-14 old/new session split lives in exactly one place (last_seq>=0 AND empty occupied_by => reject); AlreadyOccupied(CommandRejected) makes self-reselect a success path with no duplicate event
- [Phase ?]: 08-02: select_character submits OccupyCharacter before signing the cookie (mirrors declare()'s submit-before-proceed order); declare/confirm's own D-14 exposure left untouched since 08-01 already closed it via cookie-required checks
- [Phase ?]: 08-02: two-browser HTTP tests against routes that call actor.submit(...) must open each TestClient in its own sequential (non-nested) with-block — nesting reuses a live portal's event loop for the SessionActor's asyncio.Queue from a second, different-loop portal and deadlocks (same class of bug 08-01 already documented)
- [Phase ?]: 08-03: GameState.confirmed_declares/confirm_to_declare fold from action_confirmed/check_resolved events; SessionActor.AlreadyConfirmed short-circuits same-move re-confirm (no new event), different move/stat gets CommandRejected (D-10)
- [Phase ?]: 08-03: confirm route catches AlreadyConfirmed before CommandRejected and reuses prior.resolve_seq when present; narration-only failure is now 200 + narration_failed=true with rolls/grade/target intact instead of discarding the roll via 502 (TRUST-06, D-08)
- [Phase ?]: 08-03 [deviation, Rule 1 bug found in Task 4]: route-level resolve-reuse decision left a TOCTOU window under concurrent confirms (reproduced: two distinct resolve_seq from one confirm). Fixed with actor-level AlreadyResolved(CommandRejected) in _prepare_resolve_check, mirroring the AlreadyConfirmed two-tier defense pattern one step further (D-11)
- [Phase ?]: 08-04: fake_session_log/test_web_actions.py player_id defaults changed p1/p2 -> bram/nari to match production's player_id===character_id convention (D-42) — this is what makes context.py's speaker-label lookup (keyed by event.player_id) attach each character's own display name
- [Phase ?]: 08-04: ConfirmRequest.target bounded ge=-200/le=200 (covers d100 skill 0-100 + OpenQuest difficulty shifts, and 2d6's low-teens targets); new MAX_MODIFIERS_COUNT=20/MAX_MODIFIER_LEN=128 constants cap ConfirmRequest.modifiers list length + item length; DeclareRequest/ConfirmRequest.rulebook_id reuse existing MAX_ID_LEN
- [Phase ?]: 09-01: DP-01/DP-02/DP-03/DP-04 확정대로 구현 — clock_judge 관문/깊은 판단 분리, 배경 자동 반영(확인 화면 없음), AGENT_ROLES 다섯 역할 + ROLE_FALLBACKS, 새 사건 종류·스키마 판 올림 없음(ClockAdvanced(trigger="condition") 재사용)
- [Phase ?]: 09-01 Task 3: D-05/ARCH-05 조용한 실패 계약을 판단 함수·웹 라우트·CLI 세 층 모두에서 시험으로 고정 — 소스 변경 없이 19개 새 단언 전부 통과
- [Phase ?]: 09-02: DP-05/DP-06/DP-07 확정대로 구현 — 서술 system에서 시나리오 원문 완전 제거(NarrationFacts에 clock_state 칸 없음), narrate()는 facts 하나만 받음, situation_judge/clock_judge 병렬 판단을 turn/judgments.gather_turn_judgments 한 자리로 통합
- [Phase ?]: 09-03: DP-08/DP-09 확정대로 구현 — scene_entity_judge가 turn/judgments.gather_turn_judgments의 세 번째 코루틴으로 들어감(각자 독립 호출, 관계 결과는 서술용 사실로만 쓰고 사건·Entity 목록에 안 씀). ARCH-04는 tests/test_parallel_judgment.py의 ast 기반 구문 검사로, ARCH-06은 tests/test_agent_context_caps.py의 세션-길이-무관 증명으로 회귀 방지 그물에 못박음. ARCH-04/05/06 셋 다 REQUIREMENTS.md에서 [x]로 완료
- [Phase ?]: 09-04: D-68 확정 기록 — CLOCK-01 최소판(위협 시계 조건 검사)은 Phase 9에 남고, 관계 기록(MEM-02)·문맥 압축(MEM-03)은 최소판까지 포함해 전부 Phase 14로 되돌림. ROADMAP Phase 15 Depends-on/성공조건 1을 그 전제로 갱신, Phase 14 절은 무변경. docs/PIPELINE.md·README.md를 실제 다섯 역할 구조와 재동기화
- [Phase ?]: 09-04 Task 2 체크포인트: 사람이 6개 확인 항목 중 0/1/4①만 통과 확인하고 2(사건 기록 역할별 분해 — replay 도구 한계로 미확인)·3(시계 폭주 5턴 검사 — 미실행)·4②③(브라우저 지시문 유출·시계 표시 — 미확인)·5(D-05 실사용 복원력 — 미실행)는 남겨둔 채 '미확인 항목은 남겨두고 넘어가자'는 명시적 판단으로 통과 처리. 항목 3·5는 향후 UAT 후속 작업으로 남김(단계 완료를 막지 않음)
- [Phase ?]: 10-01 Task 1 checkpoint(option-a): safety_flagged 사건 하나로 서사 검사(source=narration)와 분류기 계약 위반(source=classifier) 기록을 함께 담는다
- [Phase ?]: 10-01: EVENT_SCHEMA_VERSION 5->6, SafetyFlagged 사건 신설. rules_core/reducer.py 분기와 같은 커밋(08-CONTEXT.md D-06). .gptrpg/uat9.db 판 5 실기록은 세션 넷(221건), events.db는 전부 판 2(895건) — CONTEXT/RESEARCH/VALIDATION의 '판 5' 서술 정정
- [Phase ?]: 10-01: master_gm.narrate()가 NarrationChunk를 내는 1문장 지연 버퍼를 갖는다. 스톨·실패 도중에도 이미 도착한 보류 문장은 판정·방출한 뒤 예외를 다시 던져(안쪽 except), 바깥 재시도 판단(스톨 절대 재시도 금지 등)과 03-04의 '이미 나간 조각 보존' 보장을 둘 다 지킨다
- [Phase ?]: 10-02: 원문 겹침 대조 소스는 build_gm_prompt의 영구 고정 블록 하나뿐 — 세션 고정 블록(장면 대상·캐릭터 상태)은 정당한 이야기 맥락이라 대조 소스에서 뺐다(RESEARCH.md A1 좁힘)
- [Phase ?]: 10-02: 캐릭터 이탈 정규식(CHARACTER_BREAK_PATTERNS)은 D-03에 따라 절대 blocked로 승격하지 않는다 — flagged로 통과시키고 기록만 남긴다
- [Phase ?]: 10-05: classify()가 UnknownMove를 call_with_one_retry 밖 함수 경계에서 흡수해 tier=="none" Proposal(unknown_move 칸)로 돌려준다 — _parse_candidates는 여전히 예외를 던진다(SAFE-07/D-12)
- [Phase ?]: 10-05: 웹 declare()·명령줄 turn_flow가 RecordAiCall 제출과 같은 자리·조건으로 RecordSafetyFlag(source="classifier", reason="unknown_move")를 제출한다 — 두 경로가 구조적으로 갈라질 수 없다
- [Phase ?]: 10-05: QUAL-08 남은 대상(추론 노출 형태의 어댑터별 차이)을 test_providers.py에 회귀 시험으로 고정 — anthropic/openai는 구조적 배제, nim/openrouter는 openai에 위임, gemini는 정규식 의존(구조적으로 못박을 수 없다는 한계를 도크스트링에 명시)
- [Phase ?]: 10-03: 재생성은 기존 MAX_ATTEMPTS 재시도 루프 완전히 밖의 독립된 단발 호출이다(내부 재시도 없음, system 재사용) — 한 턴 제공자 스트림 호출 상한 3회(정상 최대 2 + 재생성 1)로 고정, RESEARCH.md Pitfall 2(03-04 22분 먹통 사고) 재발 방지
- [Phase ?]: 10-03: 재생성 자신의 차단 안내(NOTICE_FILTERED)는 화면에 안 내고 D-08의 NOTICE_GAVE_UP 하나로 합친다 — safety_flagged 사건이 정확히 두 건(첫 차단+최종 차단)으로 유지되며, web/routes_actions.py·cli/turn_flow.py는 무변경으로 기존 narration_failed 경로를 그대로 재사용한다
- [Phase ?]: 10-04: fence_player_text()가 turn/context.py의 action_declared 자리 한 곳에서 최근 대화 재주입분까지 감싸 D-10을 지킨다 — 표식은 정규화 후 12자 이상으로 잡아 10-02의 원문 겹침 문턱과 맞물린다
- [Phase ?]: 10-04 Task 3 실측(사람 판정): direct_command/role_swap 2회씩은 분류기 흡수(10-05)로 진행자에 도달 못 함, in_story_hiding/delimiter_escape 각 1회 도달 — 역할 파괴 0건이나 둘 다 제재 없이 통과. 울타리 자체의 실측 근거는 이 2건뿐
- [Phase ?]: 10-04: 진행자에게 도달한 입력이 제재 없이 서사로 무마되는 문제를 새 요구사항으로 승격 — .planning/todos/pending/2026-08-14-game-breaking-input-sanction.md
- [Phase ?]: 10-04 실측 중 발견(범위 밖): nvidia/nemotron-3-ultra-550b-a55b가 받침 복잡한 한글 음절을 못 뱉어 U+FFFD로 저장됨 — master_gm을 nemotron-3-super-120b-a12b로 교체(.gptrpg/ 로컬 설정, git 미추적). U+FFFD 감지는 10-06 담당
- [Phase ?]: 10-06: 깨진 글자(U+FFFD)는 flagged이지 blocked가 아니다 — inspect_sentence 4번째 갈래, EVENT_SCHEMA_VERSION 6 유지(reason은 쓰기 검증에서만 쓰이고 reducer가 안 봄), 옛 실기록 1116건 예외 없이 접힘 확인
- [Phase ?]: 10-07: WR-02 subject_len 재정의(matched_len 비절단), WR-03 SafetyFlagged source×reason 스키마+액터 이중 model_validator, WR-01 MAX_REGENERATIONS 제거·3회 호출 상한을 실제 호출-횟수 시험이 보증
- [Phase ?]: 11-01 Task 0(D-03, widen-now): StatEntry를 네 칸에서 여덟 칸으로 넓힌다 — D-20/D-65를 뒤집는 게 아니라 그 그릇이 담는 범위를 자원 축 전체로 다시 그리는 것(D-64/D-65/D-66과 같은 패턴)
- [Phase ?]: 11-01: numeric 형태 하나가 룰북 선언(Rulebook.resource_axes) → Entity → GET 시트 응답 → StatusPane 화면까지 관통 — 나머지 다섯 형태는 11-03이 데이터·화면을 붙인다
- [Phase ?]: 11-01 [deviation, Rule 3+Rule 2]: Task 1의 <verify>가 요구했으나 <files> 목록엔 없던 test_entities.py/test_web_characters.py를 Task1에서 앞당겨 고침(고정 시험 8칸 재고정 포함); must_haves.truths가 요구한 ResourceAxisDecl/Rulebook 경계 시험을 위해 계획서에 없던 tests/test_rulebook.py를 신설(12건) — 둘 다 사용자/오케스트레이터 사전 승인
- [Phase ?]: 11-02: validate_grade_bands()가 is_doubles 두 세계 x 원자 구간 스윕으로 가려짐/구멍을 등록 시점에 잡는다(QUAL-03/D-15) - grade_for_margin과 _band_matches 헬퍼를 공유해 두 판정 규칙이 구조적으로 갈라질 수 없다. 단순 겹침(DW strong_hit/weak_hit, OQ critical/success)은 정상 통과 회귀 확인
- [Phase ?]: 11-02: validate_entity_axes/validate_move_stats + validate_registered_rulebooks가 rulebooks 패키지 임포트 시점에 개체 축/무브 축 정합성까지 함께 검사(D-01/T-11-07). _GAPPED_RULEBOOK류 런타임 RULEBOOKS 패치 시험은 이 게이트를 안 지나가 별개 방어선으로 유효
- [Phase ?]: 11-02 [deviation, Rule 3, 사람 확인 필요]: validate_move_stats를 실제 등록에 연결하자 OpenQuest 무브 열 개의 default_stat(기술 이름)이 애초에 축으로 선언돼 있지 않았고(이미 있던 이름 그대로 축 10개 추가로 해소), 던전월드류 defy_danger/aid_or_interfere의 default_stat='상황에 맞는 능력치'(원문상 의도적 서술)가 DEX/CHA 근사치로 교체됨 - 게임 메커니즘은 안 바뀌지만(ConfirmRequest.stat이 확인 시점에 자유 선택) 룰북 설계 뉘앙스를 좁힌 판단이라 사람 확인 필요
- [Phase ?]: 11-03: _visible_stats()가 form=="none" 축을 시트 응답 조립 단계에서 제외 — 룰북 축 선언과 개체 StatEntry.form 두 신호를 독립적으로 확인, 등록 검증 전제에 안 기댐
- [Phase ?]: 11-03: StatusPane이 여섯 형태(numeric/clock/named_slots/tag_list/usage_die/none) 전부에 명시적 렌더 갈래를 갖춤 — clock은 ThreatClock 재사용, none은 서버가 이미 제외해 도달 불가
- [Phase ?]: 11-03 [deviation]: 체크포인트 확인 시 실제 룰북 데이터가 numeric만 선언해 나머지 다섯 형태를 볼 화면이 없어, 저장소를 안 건드리고 서버 메모리에만 데모 캐릭터 둘을 얹어 확인 후 폐기함
- [Phase ?]: 11-05: ProposalTier 4값(single/several/no_check/unclear) + NO_CHECK_SIGNAL 신호, Proposal.tier 우선순위(unknown_move>후보>신호>나머지)를 코드로 못박음(D-11)
- [Phase ?]: 11-05: 분류기 지시문이 '안 맞음'과 '필요 없음'을 3갈래로 분리, 빈 무브 목록도 예외 없이 조립(RULE-15 empty)
- [Phase ?]: 11-05: 웹/CLI/화면/타입 네 곳이 같은 커밋(9e23c71)에서 4값 어휘로 이동 — CLI 안내 문구를 '진행합니다'(부정확)에서 '끝납니다'(정직)로 교체
- [Phase ?]: 11-05: RULE-15는 Complete로 표시하지 않음 — 이 계획은 그릇(플랫폼 능력)만 만들었고 실증(11-04)과 no_check 실제 서사 경로(11-06)가 남음
- [Phase ?]: 11-04 Task 0(declare-only, 승인): Cairn d20 계산기는 이번 단계에 안 만든다 — 선언·등록까지만, CommandRejected로 눈에 보이게 멈춘다
- [Phase ?]: 11-04: Cairn(CC BY-SA 4.0)을 플랫폼 그릇 변경 없이 세 번째 룰북으로 등록(D-14) — named_slots(10칸 소지품) 형태를 실제 데이터로 첫 실증
- [Phase ?]: 11-04: check_trigger_mode(declared_list/no_dice/gm_discretion) 신설(D-12) — 빈 판정 트리거 목록의 두 갈래를 룰북이 명시적으로 선택하게 강제
- [Phase ?]: 11-04 [접어넣은 todo]: Cairn은 default_stat 벽에 부딪히지 않음(무브 목록 자체가 없음) — 그래도 MoveDecl.default_stat을 str | None으로 넓혀 던전월드 defy_danger/aid_or_interfere를 원래 의도(None)로 되돌림, 11-02 편차 해소

### Pending Todos

없음.

### Blockers/Concerns

**[v1.1이 풀어야 하는 것] 세션1(2026-08-04)에서 드러난 코어 결함.**
전수 감사는 `docs/session1-code-review.md`. 심각도 순으로 C1~C4 · H1~H2 · M1~M8 · L1~L10.
로드맵은 이 전부를 Phase 7~13에 매핑했다(REQUIREMENTS.md Traceability 참조).

세 가지가 실전에서 동시에 터졌다 — ① 네 명의 행동이 AI 컨텍스트에서 한 사람으로 뭉뚱그려짐
(라벨은 고쳤으나 **신원 검증 부재라는 근본 구조는 그대로**, Phase 8이 닫는다) ② 참가자 한
문장에 AI가 캐릭터 이탈(탈옥, Phase 9가 닫는다) ③ 진행자 지시문 전체가 서사로 유출(Phase 9).
여기에 재검증에서 C4가 새로 발견됐다 — **능력치가 판정 계산에 전혀 안 들어가고, 캐릭터
상태가 플레이로 절대 안 바뀐다(Phase 10이 닫는다).**

**[다음 행동] Phase 7(D-20/D-31 재논의)이 v1.1의 진입점이다.** 코드보다 결정이 먼저다.
잠금 결정을 코드가 조용히 우회하지 않는다는 것이 이 프로젝트의 규약이다.

**[보류 — 폐기 아님] 킬 크리테리아 실험 (D-62).** EXP-01~04 · HYP-01~06.
D-59·D-60·D-61은 그 실험의 채점 규칙을 좁힌 결정이라 실험과 함께 보류 상태로 들어간다.
v1.1이 완료되면 조건을 갖춘 재실험을 새로 설계할지 결정한다.

**[문서 정리 — 여전히 미해결] 3건.** 상세는 `.planning/INGEST-CONFLICTS.md`.

1. **원가 수치의 계산 전제가 결정과 어긋난다.** 원가 문서는 「최근 대화 20턴」으로 1인 1시간당 $0.30을 뽑았는데 확정 규칙은 「초기값 10턴」이다. → 실험 보류로 실측 시점이 미뤄졌다. 계측 코드는 살아 있으므로 프로토타입을 돌릴 때마다 쌓인다. **Phase 11(문맥 압축기)이 구현되면 「압축 없는 상태의 값」이라는 유보는 해소된다**
2. **v1에만 있고 유지·폐기 진술이 없는 구현 약속 2건.** ① 에이전트 응답 껍데기 + 가벼운/중간 모델 타임아웃·재시도 ② 연결 유지 신호 주기와 스트리밍 중 재연결 이어붙이기
3. **폐기된 v1 기획서에 폐기 표기가 없다.** 파일명 말고 단서가 없어서 그 파일만 연 사람은 폐기된 설계를 유효한 명세로 읽는다

**[v1.1로 당긴 M1 항목 — D-63, 로드맵에 반영 완료]** M1-09(시계 진행 규칙 ②③ + 진행자
수동 경로, Phase 12) · M1-12(`context_summarizer`, Phase 11) · M1-13(관계 장부 주입,
Phase 11). **M1에 남는 것:** M1-01~08 · M1-10(폴링 읽기 비용) · M1-11(D-11의 3주 재개
검증) · M1-14(동적 파티).

- [해소됨 2026-08-12 — Phase 9 열린 UAT 4항목 전부 확인] 09-04 Task 2 체크포인트에서 미확인으로 남겼던 항목을 후속 UAT 패스에서 전부 돌렸다(`09-UAT.md`, 4/4 PASS). ① 시계 폭주 검사(T-09-20): 완결 5턴 뒤 시계 **2/4** — 마지막 칸에 닿지 않았다. 진행 두 번 다 `trigger="condition"`(Phase 9 배경 경로)이고 사건으로 기록됐다. ② D-05 실사용 복원력: clock_judge를 존재하지 않는 모델로 바꾸고 브라우저에서 한 턴 완주 — 서사까지 정상, 실패는 서버 표준오류에만(`404 page not found`), 화면·콘솔 유출 0건. ③ 역할별 `ai_invoked`: situation_judge·scene_entity_judge·clock_judge가 같은 `caused_by_seq` 아래 각각 한 번씩(정적 병렬 gather 증거). ④ 브라우저 육안: 시나리오 원문 특징 문구 6개 전부 미출현, 지시문·사고블록 흔적 0건, 시계 표시 정상

- [Phase 9 UAT에서 새로 관찰된 것 3건 — `09-UAT.md` Gaps 참조] ① 분류기가 닫힌 목록 밖 무브(`'track'`)를 내면 그 턴이 안내 없이 죽는다(exit 1, 방어 자체는 정상) — **Phase 10 논의에 올릴 것**. ② 실패한 제공자 호출도 `ai_invoked`로 기록되고 토큰이 0이라 정상 응답과 구분되지 않는다 — **Phase 14 성공 조건 5가 가리키는 바로 그 상황이고, 이제 실물 증거가 있다**. ③ 제공자 시간초과가 실제로 났는데도 턴이 완주했다 — 성공 조건 4의 실사용 증거

- [`gptrpg replay`의 한계] replay 출력에는 「AI 호출 수」 합계만 있고 역할별 내역이 없다 — UAT 항목 ③은 사건 기록의 `ai_invoked.agent_role`을 직접 읽어 확인했다. replay에 역할별 집계 한 줄을 붙이면 이 확인이 명령 하나로 끝난다(후속 제안, 미착수)

### Roadmap Evolution

- Phase 12.1 inserted after Phase 12: 캐릭터 만들기 — 7가지 동작과 애착 장치 (D22). Phase 8 논의 중 사용자가 지적해 발견: D22가 잠긴 결정인데도 v1.1·M1~M4 어디에도 배정된 적이 없었음. CHAR-01~05 요구사항 신설, REQUIREMENTS.md 69→74건 (URGENT)

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| 실험 운영 | EXP-01~04 — 참가자 4명 · 1주 간격 2세션 · 관찰 | 보류 (D-62) | 2026-08-05 |
| 가설 판정 | HYP-01~06 — 재미·봐주기·룰북·자유텍스트·원가·비경험자 | 보류 (D-62) | 2026-08-05 |
| 계측 | MEAS-05 — 손으로 쓴 리캡으로 이어하기 | 보류 (실험에 종속) | 2026-08-05 |

## Session Continuity

Last session: 2026-08-16T11:30:34.988Z
Stopped at: Completed 11-04-PLAN.md
Traceability 갱신 완료
Resume file: None

**다음 행동:** Phase 10(AI 출력 검증과 탈옥 방어) **논의 완료** — `10-CONTEXT.md`에 결정
13개가 잠겼다. 다음은 `/gsd-plan-phase 10`(조사 → 계획).

**계획 단계가 반드시 알아야 할 것 셋:**

1. **판을 5 → 6으로 올린다**(D-04, 안내를 사건 기록에 남기기 위해). `reducer.py` 분기를
   **같은 커밋에** 내야 한다 — 이 프로젝트에서 이미 한 번 사고가 난 자리다(08-CONTEXT.md D-06)

2. **「한 문장씩 늦추기」가 구조를 정한다**(D-01). 서사가 지금은 문장이 완성되는 즉시
   기록·표시되는데, 그 사이에 한 칸을 끼운다. `master_gm.narrate()`의 재시도 규칙 세 갈래
   (특히 스톨은 절대 재시도 안 함)를 깨면 안 된다

3. **SAFE-07이 신설됐다** — 분류기가 목록 밖 이름을 내면 「무브 없음」과 같은 경로로 보낸다
   (D-12). 2026-08-12 Phase 9 UAT에서 발견

Phase 9는 검증까지 완전히 닫혔다 — 09-04까지 4개 계획 종료, ARCH-02~06 다섯 다 완료, 열린
UAT 4항목도 2026-08-12에 전부 PASS(증거는 `.gptrpg/uat9.db`의 `pacing5`·`uatweb` 세션).
이전 마일스톤의 단계 산출물은 `.planning/milestones/v1.0-phases/`에 보관되어 있다.

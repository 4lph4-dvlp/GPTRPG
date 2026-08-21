---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: 돌아가는 프로토타입
current_phase: 12.3
current_phase_name: 캐릭터 만들기 화면 (INSERTED)
status: executing
stopped_at: Completed 12.3-06-PLAN.md (backstop 진실 사람 확인 대기 중, CHAR-06 여전히 미체크)
last_updated: "2026-08-21T10:06:48.826Z"
last_activity: 2026-08-21
last_activity_desc: Phase 12.3 execution started
state_head: 91fc1a9037b22f5ddfa07650671b9ed5744c723f
progress:
  total_phases: 14
  completed_phases: 6
  total_plans: 45
  completed_plans: 44
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-05)

**Core value:** 이야기가 어떻게 끝나는지 보고 싶어서 일주일 뒤에 다시 접속한다
**Current focus:** Phase 12.3 — 캐릭터 만들기 화면 (INSERTED)

> ⚠️ **킬 크리테리아 실험은 보류다 (D-62).** 세션1(2026-08-04)이 답한 것은 「재미있나」가 아니라 「도구가 망가져서 잴 수가 없다」였다. EXP·HYP를 로드맵에서 내리고 코어 완성에 집중한다. 자동 계측은 코드에 그대로 남아 관찰값으로 쌓인다. 근거는 `docs/session1-code-review.md`.

## Current Position

Phase: 12.3 (캐릭터 만들기 화면 (INSERTED)) — EXECUTING
Plan: 2 of 7
Status: Ready to execute
"자랄 수 있는 모양" 나머지 원자 연산을 더해야 그 요구사항이 완전히 닫힌다 — 지금 체크하지 않는다)
Last activity: 2026-08-21 — Phase 12.3 execution started

> 라우팅 정정(2026-08-17 갱신): `phase.complete`가 Phase 11 마감 후에도 12.1을 다음으로 골랐다.
> 그러나 ROADMAP 순서는 **11 → 12 → 12.1**이고, 12.1 자신이 `Depends on`에 **Phase 12
> (「StatEntry 쓰기 경로」)**를 적고 있다. 도구가 12를 건너뛰는 이유는 `.planning/phases/`에
> `12-` 디렉터리가 없고 `12.1-character-creation`만 있어서다(문자열 정렬 문제). 로드맵 순서대로
> **Phase 12**를 다음으로 되돌렸다 — 12를 건너뛰고 12.1을 하면 의존성이 깨진다.

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 56 (M0 누적)
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
| 11 | 7 | - | - |
| 12 | 7 | - | - |
| 12.1 | 6 | - | - |
| 12.2 | 3 | - | - |

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
| Phase 11 P06 | ~3시간20분(사람 확인 대기 포함) | 3 tasks | 15 files |
| Phase 11 P07 | ~90min | 3 tasks | 15 files |
| Phase 12 P01 | ~2h30m (체크포인트 승인 대기 제외) | 3 tasks | 21 files |
| Phase 12 P02 | ~20min | 3 tasks | 10 files |
| Phase 12 P03 | ~1h | 2 tasks | 6 files |
| Phase 12 P05 | ~35min | 3 tasks | 20 files |
| Phase 12 P04 | ~40min | 3 tasks | 9 files |
| Phase 12 P06 | ~4h | 3 tasks | 18 files |
| Phase 12 P07 | ~2h | 3 tasks | 18 files |
| Phase 12.1 P01 | not tracked (checkpoint-resumed session) | 3 tasks | 11 files |
| Phase 12.1 P02 | not tracked precisely (single continuous session) | 3 tasks | 13 files |
| Phase 12.1 P03 | ~1h | 2 tasks | 6 files |
| Phase 12.1-character-creation P04 | not tracked precisely (single continuous session) | 3 tasks | 8 files |
| Phase 12.1 P05 | 약 2시간 | 3 tasks | 22 files |
| Phase 12.1 P06 | ~5h (사람 확인 대기 포함) | 2 tasks | 5 files |
| Phase 12.2 P01 | not tracked (checkpoint-resumed) | 3 tasks | 24 files |
| Phase 12.2 P02 | not tracked precisely | 3 tasks | 10 files |
| Phase 12.2 P03 | ~4h | 3 tasks | 8 files |
| Phase 12.3 P01 | 78min | 3 tasks | 19 files |
| Phase 12.3 P02 | 24min | 3 tasks | 6 files |
| Phase 12.3 P03 | 45min | 3 tasks | 9 files |
| Phase 12.3 P04 | 40min | 3 tasks | 9 files |
| Phase 12.3 P05 | 55min | 4 tasks | 11 files |
| Phase 12.3 P06 | 체크포인트 재개 - 미측정 | 4 tasks | 9 files |

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
- [Phase ?]: 11-06: proceed()의 caused_by_seq를 declare_seq로 고정(확인·판정 사건이 없는 경로), check_summary 자리에 NO_CHECK_SUMMARY 고정 문장(SAFE-03 울타리 우회 방지), no_check 화면에 다시 쓰기 버튼 없음(D-10 결정 2)
- [Phase ?]: 11-06 [Task 3 관문에서 발견, Rule 2]: groupTurns.isConfirmedTurn을 isVisibleTurn으로 확장(확인 또는 서사 있음) — proceed 턴이 이야기 화면에 안 보이던 결함 수정. 이 저장소 최초 프론트엔드 단위 시험(vitest) 도입
- [Phase ?]: 11-07: 던전월드류가 「소지품」을 form="none"/none_kind="discretionary"로 실제 선언 — RULE-12를 시험 픽스처가 아니라 저장소 데이터로 실증(D-67)
- [Phase ?]: 11-07: _format_resource_treatment()가 discretionary/absent 두 갈래를 서로 다른 처리 지침 문장으로 세 프롬프트 조립 함수의 영구 고정 블록에 싣는다(D-08) — RESOURCE_TREATMENT_LINES_LIMIT=8, 초과 시 ContextCapExceeded
- [Phase ?]: 11-07: resource_axes 매개변수를 기본값 ()로 넓혀 classify/judge_situation/narrate/gather_turn_judgments에 추가 — 이 저장소 전역의 기존 프롬프트 조립 호출부·시험이 대부분 무변경으로 남고, 웹·CLI 실제 호출부 10곳만 rulebook.resource_axes를 명시적으로 넘긴다
- [Phase ?]: 11-07: _format_character_state가 stat.form 여섯 값 명시적 분기로 재작성됨 — form=="none"은 건너뛴다(T-11-25). _format_scene_entities는 같은 버그를 잠재적으로 갖고 있으나 이 계획 범위 밖, WINDOWS.md에 todo로 기록
- [Phase ?]: 11-06 rework 2(코드 리뷰 후 차단 결함, T-11-29): POST /proceed가 라우트 계층 신원 대조만 하고 선언 소유권·분류 결과(tier)를 서버 자체 검증 없이 클라이언트 말을 믿어, 판정이 필요한 행동을 선언한 뒤 판정을 통째로 건너뛸 수 있었다. ActionClassified 사건(판 7)+SessionActor.VerifyProceedEligibility(declare_owners+declare_no_check 이중 검사)로 막았다. 옛/미분류 기록은 declare_owners의 '모르면 통과'와 반대로 '모르면 거부'한다 — 통과시키면 이 구멍이 다시 열린다
- [Phase 12]: 12-01 Task 1 체크포인트(option-a, 사용자 승인): 자원 변화 선언은 「축 · 동작 · 양」 세 칸으로 확정 — 룰북 데이터·사건 기록·재생 코드 세 곳에 동시에 박힌다. 두 칸(축·양)으로 좁히는 대안은 로드맵 성공 기준 8("자랄 수 있는 모양")을 못 채워 기각
- [Phase 12]: 12-01: StatUsage(add_to_dice_total/use_as_target)를 rulebook.py에 능력치 쓰임 선언으로 세우고, build_stat_check_input이 캐릭터 StatEntry.current를 룰북 이름 모른 채 Modifier/target으로 조립(D-01). 던전월드류 여섯 능력치가 add_to_dice_total, OpenQuest 능력치 일곱이 use_as_target(계획 원문에 없던 추가 — 아래 참조)
- [Phase 12]: 12-01: resource_change.py 신설 — 「축 · 동작 · 양」(ResourceChangeDecl/ResourceOp), 이번 계획은 delta 동작 하나뿐이고 12-02가 나머지 일곱을 같은 형식 위에 붙인다(RULE-09 — 요구사항은 12-02까지 완결돼야 완전히 닫힌다, REQUIREMENTS.md 체크 안 함)
- [Phase 12]: 12-01: EVENT_SCHEMA_VERSION 7→8, ResourceChanged 사건 + reducer.py의 character_resource_ops/resource_change_by_cause를 같은 커밋에(08-CONTEXT.md D-06 네 번째 실증). GET 캐릭터 시트가 시작값이 아니라 사건을 접은 지금 값을 돌려준다(RULE-06)
- [Phase 12]: 12-01: ConfirmRequest에서 target/modifiers 제거하고 difficulty 하나로 대체(D-02), 웹·CLI 같은 커밋. 난이도는 룰북이 선언한 닫힌 이름 목록(require_difficulty)에서만 찾고, 없는 이름은 사건을 남기기 전에 거절(웹은 ConfirmAction 제출 이전에 미리 검증해 "요청 전후 사건 개수 동일" 보장)
- [Phase 12]: 12-01 [deviation, Rule 4 — 계획 자기모순 해소, 승인 불필요 조건에 해당]: 계획 원문은 ResolveCheck.stat 빈 문자열을 person_id/character_id처럼 거부하라고 적었으나, Task 2 자신의 <verify>가 요구하는 test_session_actor.py가 stat 없이 ResolveCheck를 부르는 기존 호출을 여러 건 갖고 있어 문자 그대로 하면 그 파일이 깨진다. 빈 stat은 "건너뛴다"로 구현(opt-in) — 웹 confirm()은 ConfirmRequest.stat이 이미 필수라 실질적으로 항상 채워진 값을 넘긴다
- [Phase 12]: 12-01 [deviation, Rule 2 — 계획 자신의 acceptance criteria 재현 불가 문제 해소]: OpenQuest 능력치 일곱 축에 stat_usage="use_as_target" 추가(계획 원문 액션에 없음) — ConfirmRequest.stat이 여전히 필수이고 웹 캐릭터 로스터가 던전월드류뿐이라, 이것 없이는 "OpenQuest + difficulty=hard → 200"이라는 Task 3 acceptance criteria를 HTTP로 재현할 방법이 없었다. 실제 OpenQuest 플레이어 캐릭터·진짜 기술값 판정은 다음 마일스톤 몫으로 파일에 명시
- [Phase 12]: 12-01 알려진 갭(차단 아님): ResourceChangeRecord.before/after와 ConfirmResponse.total이 항상 None — 각각 액터의 캐릭터 시작값 접근 경로(층 계약 재검토 필요)와 CheckResolved의 total 필드(스키마 변경 필요)가 없어서다. WINDOWS.md 자동 기록은 시도했으나 이 세션에서 gsd-tools 쿼리 계층이 응답 없이 조용히 실패(타임아웃/무출력) — SUMMARY.md의 "Known Stubs" 절이 1차 기록이다
- [Phase ?]: [Phase 12] 12-02: ResourceChangeDecl.amount의 str 거절(12-01)을 _DICE_EXPR 형식 검사로 좁혔다 — 유효한 주사위식(NdM+flat)은 통과, 그 밖은 여전히 InvalidResourceChange
- [Phase ?]: [Phase 12] 12-02: ResourceOp.amount를 int에서 int | str로 넓혔다 — named_slots(fill/clear)·tag_list(add_tag/remove_tag)가 문자열 페이로드를 실어야 해서. _require_int_amount/_require_str_amount로 형변환 없이 검증
- [Phase ?]: [Phase 12] 12-02: clock의 최대치 자르기는 위아래 둘 다(0과 max) — numeric은 위쪽만(0 아래는 룰북 몫, D-08). clock은 max가 항상 필수라는 StatEntry 규약을 그대로 이용
- [Phase ?]: [Phase 12] 12-02: OutOfOrderEvent 검사를 fold() 한 자리에만 뒀다 — apply_event는 건드리지 않음(두 자리에 검사를 두면 서로 다른 규칙으로 갈릴 수 있다는 _band_matches 관례)
- [Phase ?]: [Phase 12] 12-02: CorruptEventRecord는 정확히 세 사유(칸 없음/정수 아님/알 수 없는 종류)만 잡는다 — 그 밖의 pydantic 검증 실패는 원래 ValidationError를 그대로 다시 던진다(QUAL-02 edge probe 경계를 안 넘음)
- [Phase ?]: [Phase 12] 12-03: 튜플 키(character_id, axis) -> 문자열 키 변환 규칙을 '::'로 이어붙이는 것으로 확정, 스크립트와 시험 파일 양쪽에 같은 규칙을 문서화(import 대신 재작성 — 계획이 허용한 대안). 기대 상태 비교 시 actual을 json 라운드트립으로 정규화해야 int/str 딕셔너리 키 불일치로 인한 거짓 회귀를 피한다
- [Phase ?]: [Phase 12] 12-03: session1 실기록 895건(판 2)을 tests/fixtures/에 커밋해 TEST-04 회귀 시험이 CI에서 항상 돈다 — 기존 skipif 로컬 스모크 여섯은 무변경으로 남김. scripts/export_session_fixture.py가 재생성 절차를 스크립트로 남김
- [Phase ?]: [Phase 12] 12-05: TurnContext.character_state -> party_state(tuple[Entity,...])/actor_character_id 두 칸으로 재구성(promote) — 행위자 한 명 상태는 actor_stats(ctx)가 매번 파티에서 뽑는 파생값, 나란히 저장 안 함(어긋난 단수 표현이 살아남는 세션1 사고 재발 방지)
- [Phase ?]: [Phase 12] 12-05: build_classifier_prompt/build_situation_prompt가 공유하던 _session_block_text를 갈랐다 — 분류기는 actor_stats(ctx) 한 명만, 상황판단/서술은 _format_party_state로 파티 전원(D-17). _format_character_state 본문은 무변경, 11-07 렌더러 재사용
- [Phase ?]: [Phase 12] 12-05: web declare()/confirm()/proceed() 세 호출부 전부 party_state=_current_party_state(store,session_id)+actor_character_id=identity.character_id로 전환(declare()는 계획 원문 acceptance criteria의 grep 카운트 2와 어긋나지만 기존 통과 시험 test_prompt_carries_the_acting_character_real_stat_names 보존을 위해 포함, Rule 1) — CLI 세 호출부는 무변경(기본값이 예시 개체 파티)
- [Phase ?]: [Phase 12] 12-04: GradeBand에 succeeded/costs 두 칸을 counts_as_failure 옆에 필수로 더했다(D-13/D-14, RULE-14) — 세 칸 다 서로 독립이고, succeeded=True이면서 counts_as_failure=True인 조합도 등록을 거부하지 않는다. 사건(CheckResolved)에는 안 싣는다 — session_actor/web이 이미 rulebook_id로 require_band를 통해 직접 읽을 수 있다
- [Phase ?]: [Phase 12] 12-04: OutcomeCategory/OutcomeList/RetroDeclarationDecl 신설(RULE-13/D-16) — validate_outcome_list를 rulebooks/__init__.py의 등록 시점 자동 검증에 배선하지 않고(파일 목록 밖), 세 룰북 전부에 대한 명시적 시험으로만 확인했다. 12-06이 실제 목록 사용 경로를 만들 때 자동 배선을 고려할 것
- [Phase ?]: [Phase 12] 12-04 [deviation, Rule 3]: dungeonworld_like.py에서 DUNGEONWORLD_MISS_HP_COST를 outcome_list 항목으로 흡수하며 제거하자 web/routes_actions.py(파일 목록 밖)의 import가 깨져, require_outcome_category 조회로 교체했다 — 값(체력/delta/-6)은 무변경
- [Phase ?]: 12-06 Task1: pick_outcome의 두 조기 반환(빈 목록·costs=False)은 함수 안 순수 판단 — gather_turn_judgments 자신은 조건 분기 없이 언제나 넷을 부른다(ARCH-04 유지)
- [Phase ?]: 12-06 Task1: UnknownOutcomeCategoryFromAI는 pick_outcome 밖으로 그대로 던져지고 confirm()/proceed()의 기존 D-05 광범위 except가 흡수 — 새 방어를 안 만듦
- [Phase ?]: 12-06 Task2: confirm()이 판정 직후 자원 변화를 곧바로 적용하던 것을 대체 — pending_resource_changes만 응답에 싣고, 실제 적용은 새 POST confirm-resource-change가 사람 확인 뒤에 한다(D-09)
- [Phase ?]: 12-06 Task2: RULE-10 재량 판정의 실제 AI 제안 생성은 파일 범위 밖(Task1의 0회 호출 계약과 충돌) — 서버는 자격 있는 축 이름만 알리고 축·동작·양 제안은 요청 쪽이 만들어 보내면 validate_outcome_list로 재검사(알려진 갭으로 문서화)
- [Phase ?]: 12-06 Task3: 소지품 판단은 새 AI 역할 없이 action_classifier.Proposal.item_use로 기존 분류기 응답에 얹음 — named_slots 축 없는 룰북은 이 판단 자체가 프롬프트에 안 실림(D-09 적용 범위)
- [Phase ?]: 12-06 Task3: declare()의 item_use 이중 대조 실패 시 held를 not_held로 낮춘다(안전한 실패 방향) — 소급 선언 축·동작은 룰북이 잠그고 양만 confirm-resource-change의 retro_declaration_amount로 확인 관문을 지남(D-16)
- [Phase ?]: 12-07: CheckBreakdown(D-04)·ResourceChangeBadge+changeIntensity(RULE-07/D-19)로 검산·자원 변화가 화면에 보이게 함. StatusPane 도크스트링의 '읽기 전용, 한 번만 불러 둔다' 거짓 전제를 제거하고 폴링 재요청 계기를 만들어 RULE-06을 닫음(12-01의 backend 절반에 이어 화면 절반 완성)
- [Phase ?]: 12-07 체크포인트 확인(4인 실제 브라우저): 여섯 항목 전부 PASS, 특히 D-18(AI가 네 명을 한 사람으로 뭉뚱그림, 세션1 붕괴 지점)이 재현 안 됨을 처음 실측 확인. 확인 중 발견된 결함 2건(캐릭터 미보유 축에 자원 변화 적용 44ed73f, 시계 진행 문구가 trigger 무관하게 항상 실패로 표시 1ad6dcd)을 그 자리에서 수정
- [Phase ?]: 12-07: 서사가 자원 변화를 모르는 문제(NarrationFacts에 결과 카테고리 칸 없음)와 위협 시계 하나뿐이라 잘해도 나빠지는 쪽으로만 기록되는 문제, 둘 다 Phase 13.1(GM이 이야기를 이끈다)로 미룸 — RULE-06/RULE-07 문자 그대로의 기준은 충족했으나 '보이는데 뜻이 없으면 소용없다'는 더 깊은 문제로 별개 요구사항
- [Phase ?]: [Phase 12.1] 12.1-01 Task 1 체크포인트(option-a, 사용자 승인): 사건 판 8->9를 한 번에 올리고 캐릭터 만들기 다섯 사건(끼어들기 포함)을 같은 커밋에 연다 — 명단 잠금에 푸는 사건을 만들지 않는다(D-08)
- [Phase ?]: [Phase 12.1] 12.1-01: _prepare_occupy의 옛 세션 판별에 created_characters 조건을 더했다 — 판 9부터 만들기 사건은 있는데 점유가 없는 것이 정상 새 세션일 수 있다(CHAR-05 자동 점유)
- [Phase ?]: [Phase 12.1] 12.1-01: PartySizeFixed.rulebook_min/max는 Rulebook.party_size_range가 아직 없어 1/None 자리표시자다 — 12.1-02가 실제 룰북 범위로 교체해야 한다
- [Phase ?]: [Phase 12.1] 12.1-01: CHAR-01/04/05는 이 계획이 시작만 열었을 뿐(각각 12.1-02·03·05·04가 마저 닫아야 완결) REQUIREMENTS.md 체크는 그대로 Pending 두었다 — 여러 계획에 걸친 요구사항 조기 완료 표시를 피한다
- [Phase ?]: [Phase 12.1] 12.1-02 Task 순서 충돌 해소: Task 2의 party_size_range None-검사를 계획대로 넣으면 Task 3까지 미채워진 OpenQuest/Cairn 때문에 등록 시점 필수 검사(계획 액션 ⑤)를 넣을 수 없다 — 등록 시점 필수 검사를 Task 3으로 미루고 던전월드류에만 최종값(3~5)을 Task 2에서 앞당겨 채워 기존 FixPartySize(count=1) 호출들을 count=3으로 옮겼다
- [Phase ?]: [Phase 12.1] 12.1-02: PARTY_MEMBER_LIMIT 검사는 session_actor가 agents를 import할 수 없다는 층 규약(.importlinter contract:2) 때문에 액터가 아니라 web/routes_creation.py에 둔다 — 계획의 <behavior>와 <action> 절이 서로 다른 자리를 가리키던 자기모순을 아키텍처 규약 우선으로 해소
- [Phase ?]: [Phase 12.1] 12.1-02: build_creation_stats는 max/depleted_effect_ref를 채우지 않는다 — ResourceAxisDecl에 그 두 칸을 선언할 자리가 아직 없어 축 이름으로 추측하면 축 이름 문자열을 코드가 해석하지 않는다는 규약을 어기게 된다. 알려진 한계로 문서화(기존 _prepare_create_character 손 조립과 동일 동작)
- [Phase ?]: [Phase 12.1] 12.1-02: PLAN.md frontmatter가 requirements:[CHAR-01, CHAR-04]로 적었지만 REQUIREMENTS.md의 CHAR-04 원문(characters_data.py 대체까지 요구)은 이 계획이 안 건드린 characters_data.py 교체(12.1-05 몫, D-12)를 포함한다 — CHAR-01만 Complete로 남기고 CHAR-04는 되돌려 Pending 유지(여러 계획에 걸친 요구사항 조기 완료 표시 함정 회피, 12.1-01-SUMMARY.md가 이미 경고)
- [Phase ?]: [Phase 12.1] 12.1-03 Task 1 체크포인트 자동 승인: D-03(GM 진행 대화, 상태 기계는 코드가 돈다)을 재확정 — 12.1-CONTEXT.md와 12.1-01의 동일 체크포인트에서 이미 승인된 결정의 재확인이라 auto 모드에서 자동 선택(option-a)
- [Phase ?]: [Phase 12.1] 12.1-03: 아직 안 끝난 사람 후보 목록은 GameState.creation_step_values 키(character_id)에서 계산한다 — 아직 항목을 하나도 제출하지 않은 참가자는 플랫폼이 식별할 방법이 없어 이 목록에 못 들어간다(방을 여는 사람이 정한 인원수와 실제 참가자 식별자는 다른 정보)
- [Phase ?]: [Phase 12.1] 12.1-03: 제공자 설정 해석 실패(ConfigNotFound 등)는 503, GM 호출·계약 위반(CreationGmContractViolation)은 200 폴백 — 두 실패 층을 declare()/confirm()과 같은 구분으로 갈랐다
- [Phase ?]: [Phase 12.1] 12.1-03: CHAR-03을 REQUIREMENTS.md에서 Complete로 찍지 않았다 — 원문이 요구하는 'GM 정리로 자동 생성'은 12.1-04(정리·동의 관문) 몫이라 계획 자신의 알려진 한계 절이 이미 명시했다. CHAR-01은 12.1-02에서 이미 Complete
- [Phase ?]: wrap-up의 '전원 완성' 판정 기준을 party_size_fixed(룰북 권장 인원)가 아니라 _unfinished_candidates(시작한 사람 전원이 끝났는가)로 잡았다 — D-08의 '명단과 출석은 다르다'를 그대로 코드에 반영, 룰북 권장 3~5명 방이어도 실제 참가자 둘이면 정리·동의로 진행된다
- [Phase ?]: RecordConsent/ReopenCreationStep은 사건이 아니라 액터 메모리 상태다(D-10 결정) — 이 저장소에서 사건이 아닌 유일한 만들기 상태. LockPartyRoster를 직접 불러도 완성된 전원의 동의 집계가 없으면 거절된다
- [Phase ?]: 12.1-05: characters_data.py 삭제, GameState.created_characters를 캐릭터의 유일한 출처로 통일 — CHAR-02/CHAR-04 닫음
- [Phase ?]: 12.1-05: 계획 조사가 놓친 routes_actions.py 네 호출부(declare/confirm/confirm_resource_change/proceed)를 _created_character() 공용 헬퍼로 통일
- [Phase ?]: 12.1-05: 시험이 앱 sqlite 연결을 재사용하지 않도록 app.state.db_path 추가 — 스레드 종속 연결 재사용 버그 예방
- [Phase ?]: 12.1-06: 접힌 할 일 세 선택지 중 2번(변경하기 숨김)만 채택 — 1번(점유 놓기)은 D-08과 어긋나 기각, 3번(카드 비활성 표시)은 Phase 16 몫으로 이관
- [Phase ?]: 12.1-06: 쿠키 분실 한계 문구를 사람 확인 피드백으로 구체화 — '표시를 지우면'을 '인터넷 사용 기록을 지울 때'로 교체(f16de59)
- [Phase ?]: 12.1-06 사람 확인 중 발견(범위 밖): Phase 12.1 전체가 서버 라우트만 완성하고 프런트엔드 화면이 없다 — Phase 12.3(캐릭터 만들기 화면)이 로드맵에 신설됨(f6109be)
- [Phase ?]: 12.2-01 Task 1 체크포인트(option-a, 사용자 승인): 판 9→10을 한 번에 올려 total·rulebook_id 두 칸을 같은 판에 넣는다(D-01/D-02/D-03)
- [Phase ?]: 12.2-01: 계산 줄은 PollResponse의 병렬 목록(check_calculations)으로 싣는다 — groupTurns.ts는 안 고친다
- [Phase ?]: 12.2-01: 계산 조각의 역할 이름은 자유 문자열(promote, Grade = str 전례) — 닫힌 목록을 만들지 않는다(D-10)
- [Phase ?]: 12.2-01 [deviation, Rule 3]: 판 올리기로 깨진 기존 CheckResolved() 생성부 6개 파일(conftest.py 등)에 total/rulebook_id 추가
- [Phase ?]: 12.2-02: buildCheckSummary 매개변수를 CheckFacts(Pick<rolls|modifiers|target|grade>)로 좁혀 ConfirmResponse·CheckResolvedEvent 양쪽이 새 타입 변환 없이 같은 함수를 공유하게 함
- [Phase ?]: 12.2-02: DiceModal 괄호 표시를 summary.rows flatMap으로 교체 — 다시 굴림(D-12) 줄 나눔이 실제로 연결되면 이 자리를 재검토(알려진 한계)
- [Phase ?]: 12.2-03: 채택 판정은 값이 아니라 자리(순서)로 정한다 — 동값 두 개일 때 값 비교로 채택을 고르면 채택 조각이 둘 이상 될 수 있어 항상 앞 자리를 채택으로 본다
- [Phase ?]: 12.2-03 [deviation, D-15 관문에서 발견, 계획 밖]: 액션 라우트가 rulebook_id를 요청 기본값(DUNGEONWORLD_LIKE_ID)에서 가져오던 사전 존재 결함을 character.rulebook_id 읽기로 교체(6e7c2e5) — OpenQuest 캐릭터가 던전월드류 무브를 받아 판정이 400으로 끊기던 문제, D-15 확인을 완전히 막고 있었다
- [Phase ?]: 12.2-03 [deviation, D-15 관문에서 발견, 일부만 계획 안]: 주사위 모양이 값이 아니라 서버 role(die/tens/units)을 따르도록 고침(0a0c9fe, D-13 갭) — 모달 자동 닫힘 제거·죽은 턴 스피너 수정은 계획 밖. 확인 버튼 pointer-events 복구(5c28766)도 계획 밖
- [Phase 12.3]: Task 0 사람 결정: GM의 말을 CreationGmSpoke 하나(one-event)로 묶는다 — kind 리터럴로 네 갈래 구분, dedupe_key 하나로 D-12 중복 방지를 전부 덮는다
- [Phase 12.3]: Command 클래스는 RecordGmSpoke로 짓는다 — 계획 문서의 CreationGmSpoke 문구는 schema.py Event 클래스와 이름이 겹쳐 파이썬에서 재사용할 수 없다(FixPartySize/PartySizeFixed 규약을 따름)
- [Phase 12.3]: CharacterSelect 화면을 지운다(D-10) — 만들기 완성이 자동 점유까지 끝내므로 쿠키 없는 브라우저가 명단 잠금 뒤 고를 목록이 애초에 없다
- [Phase 12.3]: GM의 지목·되묻기·정리를 announce와 같은 사건화 모양으로 통일하고, 만들기 진행 상태 계산을 web/creation_state.py 한 자리로 모아 routes_creation.py·routes_events.py가 공유한다 — 판단이 두 곳에 생기면 언젠가 어긋난다는 Phase 12.2 규율을 그대로 따랐다(D-04)
- [Phase 12.3]: 동의/재오픈을 액터 메모리에서 creation_consent_recorded 사건으로 옮기고, 방장(ClaimCreationHost)을 신설해 인원 확정 권한을 사건 기록 위에 세웠다(12.3-03)
- [Phase 12.3]: 방장 재실 표는 사건이 아니라 프로세스 메모리로 뒀다 — 판단은 서버 한 자리에만 있되 그 재료까지 전부 사건일 필요는 없다는 재량 판단(12.3-03 Task 2)
- [Phase 12.3]: 만들기 대화판이 단일 활성 항목(activeRow) 모델을 쓴다 — 다음 미완료 필수 항목이나 고치기로 연 항목 하나에만 조작 UI를 그린다 — 12.1 D-03의 자기소개처럼을 마법사가 아니면서도 한 번에 하나씩 답하는 대화 리듬으로 해석했다
- [Phase 12.3]: DiceModal이 판정과 만들기 굴림 두 자리에서 재사용된다 — roll 프롭을 유니온으로 넓히고 눈 개수·타이밍·착지값 코드는 한 줄도 안 바꿨다 — 같은 굴림은 같게 보여야 한다(D-07) — 새 연출을 만들지 않는다
- [Phase 12.3]: 12.3-05: 인원 확정/동의 두 관문을 순수 게이트 함수(partySizeGate/consentGate)+렌더 스위치로 배선, CreationScreen이 onEntered로 App의 Gate를 세션으로 바꾼다
- [Phase 12.3]: 12.3-05: CHAR-06을 REQUIREMENTS.md/ROADMAP.md에 만들었지만 사람 확인(Task 4, 14개 항목) 전이라 체크하지 않는다 — requirements.ready-ids는 1/1이지만 그것은 계획 완료이지 사람 확인이 아니다
- [Phase 12.3]: 12.3-06 Task 0(사장님 결정): 첫 지목 교착 gap 해소 — 재실 신호(POST /creation/host)에 character_id를 얹는 갈래 ①을 선택. add-alongside로 present_candidates를 명단 잠금 판단에는 안 흘려보낸다 — 갈래 ②는 후보가 항상 한 명이라 GM이 고를 게 없어져 D-06 취지를 흐리고, 갈래 ③(참가 사건화)은 사건 기록을 되돌릴 수 없게 바꿔야 해서 기각

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
- Phase 13.1 inserted after Phase 13: GM이 이야기를 이끈다 — 2026-08-17 플레이테스트에서 발견한 빈칸: 진행자가 반응만 하고 이야기를 밀지 않는다 (URGENT)
- Phase 12.2 inserted after Phase 12: 판정 합계를 서버가 보낸다 — 2026-08-18 코드 리뷰 CR-02: 화면이 눈을 더해 d100에서 틀린 검산을 보여준다 (URGENT)

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| 실험 운영 | EXP-01~04 — 참가자 4명 · 1주 간격 2세션 · 관찰 | 보류 (D-62) | 2026-08-05 |
| 가설 판정 | HYP-01~06 — 재미·봐주기·룰북·자유텍스트·원가·비경험자 | 보류 (D-62) | 2026-08-05 |
| 계측 | MEAS-05 — 손으로 쓴 리캡으로 이어하기 | 보류 (실험에 종속) | 2026-08-05 |

## Session Continuity

Last session: 2026-08-21T10:06:48.519Z
Stopped at: Completed 12.3-06-PLAN.md (backstop 진실 사람 확인 대기 중, CHAR-06 여전히 미체크)
이어받아 Task 2·Task 3 커밋까지 완료
Resume file: None

**다음 행동:** `/gsd-execute-phase 12`로 12-02 실행(주사위 양·나머지 여섯 자원 형태 —
`resource_change.py`의 `ResourceOperation` Literal을 12-01이 `"delta"` 하나로 열어 뒀고
`apply_resource_op`이 `form != "numeric"`을 이미 명시적으로 거절해 다음 계획이 채울 자리를
코드로 표시해 둔다).

**계획 단계가 반드시 알아야 할 것 셋:**

1. **RULE-09는 아직 REQUIREMENTS.md에서 체크하지 않았다** — 12-01이 「축 · 동작 · 양」 형식과
   `delta` 동작 하나를 세웠지만, 그 형식이 실제로 "자란다"는 것은 12-02가 나머지 동작을
   붙여야 증명된다. 12-02 완료 시 RULE-09를 닫을 것

2. **`ResourceChangeRecord.before`/`.after`가 항상 `None`이다** — `session_actor`가 캐릭터
   시작값(`web.characters_data`)에 접근할 수 없어서다(층 계약). 12-07(화면)이 이 칸을
   실제로 그리게 되면 그 전에 반드시 채워야 한다

3. **`ConfirmResponse.total`도 항상 `None`이다** — `CheckResolved`가 `total`을 저장하지
   않는다. 채우려면 `event_log/schema.py` 스키마 변경(판 올리기)이 필요하다

Phase 9는 검증까지 완전히 닫혔다 — 09-04까지 4개 계획 종료, ARCH-02~06 다섯 다 완료, 열린
UAT 4항목도 2026-08-12에 전부 PASS(증거는 `.gptrpg/uat9.db`의 `pacing5`·`uatweb` 세션).
이전 마일스톤의 단계 산출물은 `.planning/milestones/v1.0-phases/`에 보관되어 있다.

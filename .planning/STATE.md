---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: 돌아가는 프로토타입
status: planning
last_updated: "2026-08-05T08:10:00.000Z"
last_activity: 2026-08-05
progress:
  total_phases: 10
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-05)

**Core value:** 이야기가 어떻게 끝나는지 보고 싶어서 일주일 뒤에 다시 접속한다
**Current focus:** v1.1 돌아가는 프로토타입 — Phase 7(거버넌스) 완료, Phase 8 착수 대기

> ⚠️ **킬 크리테리아 실험은 보류다 (D-62).** 세션1(2026-08-04)이 답한 것은 「재미있나」가 아니라 「도구가 망가져서 잴 수가 없다」였다. EXP·HYP를 로드맵에서 내리고 코어 완성에 집중한다. 자동 계측은 코드에 그대로 남아 관찰값으로 쌓인다. 근거는 `docs/session1-code-review.md`.

## Current Position

Phase: 8 of 16 (신원 검증과 멱등성) — 번호는 이전 마일스톤(Phase 1~6)에서 이어짐
Plan: 미작성
Status: Ready to plan — Phase 7(거버넌스 재논의) 완료, `/gsd-plan-phase 8` 대기
Last activity: 2026-08-06 — Phase 7 완료(D-64·D-65·D-66). 실전 관찰 4항목을 출간 룰북/시나리오 조사 후 D-67로 추가 — Phase 9·11·13 신설, 로드맵 7단계 → 10단계, 요구사항 50 → 69

Progress: [█░░░░░░░░░] 1/10 단계 (v1.1 기준)

## Performance Metrics

**Velocity:**

- Total plans completed: 22 (M0 누적)
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

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| 실험 운영 | EXP-01~04 — 참가자 4명 · 1주 간격 2세션 · 관찰 | 보류 (D-62) | 2026-08-05 |
| 가설 판정 | HYP-01~06 — 재미·봐주기·룰북·자유텍스트·원가·비경험자 | 보류 (D-62) | 2026-08-05 |
| 계측 | MEAS-05 — 손으로 쓴 리캡으로 이어하기 | 보류 (실험에 종속) | 2026-08-05 |

## Session Continuity

Last session: 2026-08-05
Stopped at: v1.1 ROADMAP.md 작성 완료 — Phase 7~13, 요구사항 48/48 매핑, REQUIREMENTS.md
Traceability 갱신 완료
Resume file: —

**다음 행동:** Phase 7(거버넌스 재논의 — D-20 · D-31) 착수. 코드 계획이 아니라 사용자와의
직접 논의로 시작하는 편이 맞을 수 있다 — `/gsd-plan-phase 7` 실행 전에 D-20/D-31 재논의
결과를 먼저 정하고 PROJECT.md에 기록한다. 이전 마일스톤의 단계 산출물은
`.planning/milestones/v1.0-phases/`에 보관되어 있다.

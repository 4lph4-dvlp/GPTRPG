# 파이프라인 — 코드가 실제로 도는 경로

> 작성: 2026-08-04. **이 문서는 결정의 출처가 아니다** — 권위는 `docs/GPTRPG-M0-decisions.md`다.
> 이 문서는 지금 저장소에 있는 코드가 실제로 무엇을 어떤 순서로 하는지만 적는다.
> 설계 의도와 코드가 어긋나는 지점은 §9에 따로 모았다.

---

## 1. 층 구조 — 화살표는 import 방향

`.importlinter` contract:2가 코드로 강제한다. 위에서 아래로만 볼 수 있다.

```
  gptrpg.cli          |   gptrpg.web            ← 서로를 import 못 한다 (co-equal)
        └──────┬──────────────┘
               ▼
          gptrpg.turn          ← cli·web 양쪽이 공유하는 TurnContext 조립 자리
               ▼
          gptrpg.agents        ← event_log·session_actor·sqlite3 import 금지 (contract:3)
               ▼
       gptrpg.session_actor    ← 세션당 유일한 쓰기 주체 + 집계 저장
               ▼
          gptrpg.rulebooks     ← 룰북·시나리오 "데이터" 선언 전용
               ▼
  gptrpg.rules_core  |  gptrpg.event_log
   (시각·무작위·파일·네트워크·asyncio import 금지, contract:1)
```

핵심 성질 두 개가 이 그림에서 바로 나온다.

- **AI는 판정에 닿을 수 없다.** `agents`는 `session_actor`를 import할 수 없으므로 사건을 쓸 수단이 없다. AI 출력이 게임 상태로 바뀌는 유일한 통로는 `cli`/`web`이 반환값을 읽어 `Command`로 조립하는 것뿐이다.
- **규칙 계산은 시간을 모른다.** `rules_core`가 `time`/`random`/`datetime`을 import하지 못하므로 판정 코드에 타이머·접속 상태가 들어갈 자리 자체가 없다.

---

## 2. 파이프라인 A — 브라우저에서 한 턴 (쓰기 경로)

행동 하나가 **HTTP 요청 두 번**으로 끝난다. 사람의 확인 클릭이 그 둘을 가른다.

### A-1. 선언 `POST /api/sessions/{id}/actions/declare`

`frontend/src/panes/ChatPane.tsx` (`submit`) → `web/routes_actions.py:121`

```
① validate_session_id          app.py:39      [A-Za-z0-9_-]{1,64} 아니면 400
② DeclareAction 제출  ─────────────────────────▶ seq N : action_declared
      actor.submit()           actor.py:204                (raw_text 원문 그대로, MEAS-04)
③ get_character()              characters_data.py:173      없으면 400 (선언은 이미 남음)
④ build_turn_context()         turn/context.py:29
      ├─ rebuild_state()       projection.py:7   ← 사건 전체를 처음부터 접는다
      ├─ read_events() 전체 읽기 → 선언·서사 텍스트만 뽑아 마지막 10개
      ├─ THREAT_CAST 전체       threat_clocks.py:89   (D-48, 국면 필터 없음)
      └─ character.stats
⑤ load_config()                agents/config.py:67   .gptrpg/agents.json 없으면 503
⑥ classify()  ── asyncio.to_thread ──▶            [AI 호출 #1]
      action_classifier.py:139       5초 타임아웃 · 재시도 1회 (invoke.py:49)
      └─ 실패해도 예외 없음 → candidates=() (D-29)
⑦ RecordAiCall 제출 ───────────────────────────▶ seq N+1 : ai_invoked
                                                  (caused_by_seq = N)
⑧ 응답 {declare_seq: N, tier, candidates[0..3]}
```

- **AI 호출만 작업 스레드로 나간다.** `EventStore`의 sqlite3 연결은 만든 스레드에 묶여 있어(`check_same_thread`) 액터·저장소 접근은 예외 없이 이벤트 루프에 남는다. 이걸 어기면 `ProgrammingError`.
- `tier`는 후보 **개수**만으로 정해진다 — 0개 `none` / 1개 `single` / 2~3개 `several`. 신뢰도 숫자를 담는 칸이 아예 없다(D-16 임계값 폐기).

### A-2. 확인 `POST /api/sessions/{id}/actions/confirm`

`frontend/src/panes/ChatPane.tsx` (`resolve`) → `web/routes_actions.py:227`

```
① 요청 형식 검증을 사건 기록보다 먼저 전부 끝낸다 (수정치 구문·캐릭터·룰북)
      → 실패하면 400, 사건은 하나도 안 남는다 (짝 잃은 "확인됨" 방지, RIG-06)
② ConfirmAction 제출 ──────────────────────────▶ seq M : action_confirmed
                                                  (caused_by_seq = declare_seq)
      · confirmed=false면 여기서 끝. "확인 사건은 있고 판정 사건은 없다" = 거부 기록
③ ResolveCheck 제출 ───────────────────────────▶ seq M+1 : check_resolved
      actor.py:346                                (caused_by_seq = M)
      ├─ get_rulebook(rulebook_id)
      ├─ _RESOLVERS[rulebook.resolution_method]   two_d6 | d100_roll_under
      ├─ resolve_2d6(roller, ...)   rules_core — 순수 함수, 눈이 사건에 그대로 남는다
      └─ require_band(...).counts_as_failure ← 실패 여부는 룰북 선언이 정한다
   ┌─ _maybe_auto_advance()  actor.py:251
   │    fails_since_clock >= 3 이면 **큐를 안 거치고** _process를 직접 재귀 호출
   └────────────────────────────────────────────▶ seq M+2 : clock_advanced
                                                  (trigger="fail_counter", RIG-04)
④ check_summary 조립 ← 방금 쓴 사건을 다시 읽어서 만든다 (store.read_events)
⑤ build_turn_context() 재호출  ← 시계·최근 대화가 ③에서 바뀌었으므로 다시 접는다
⑥ narrate()  ── asyncio.to_thread(next, ...) ──▶  [AI 호출 #2]
      master_gm.py:103   15초 타임아웃 + 90초 스트림 정지 워치독(:34)
      └─ chunk_sentences(:75) 가 .!? 경계로 문장 하나씩 흘려보낸다
           문장이 나오는 족족 ──────────────────▶ seq ... : narration_appended
                                                  (caused_by_seq = M+1, chunk_index 0,1,2…)
⑦ RecordAiCall 제출 (성공·실패 무조건) ─────────▶ seq ... : ai_invoked
                                                  (caused_by_seq = M)
⑧ 실패였으면 502 + 고정 문구. 성공이면 판정 결과 + 조각 수
```

**이 순서가 조건 분기가 아니라 코드 순서로 고정된 것이 요점이다.** ③이 ⑥보다 위에 있으므로 지연이 1초든 15초를 넘기든 판정 사건이 서사 사건보다 앞선 순번을 갖는 것이 뒤집힐 수 없다(D-33 / MEAS-02).

### A-3. 액터 안에서 명령 하나가 처리되는 네 단계

`session_actor/actor.py:231`

```
_prepare(command)   ① 값 검증  ② 필요하면 rules_core 호출(판정 명령만)
        │                └ 실패 → CommandRejected. 순번도 안 쓰고 기록도 안 남는다
        ▼
next_seq()          ③ 순번 획득            store.py:52   MAX(seq)+1
        ▼
append(event)       ④ INSERT (트랜잭션)     store.py:62   PK 충돌 → SequenceConflict
        ▼
apply_event()          액터 자기 인식 갱신   reducer.py:73
        ▼
_maybe_auto_advance()  시계 자동 진행 (재귀 최대 한 겹)
        ▼
_write_report_snapshot()  .gptrpg/reports/{id}.json 덮어쓰기 (실패해도 경고 한 줄)
```

`①·② → ③` 순서가 "거부된 명령은 순번을 소모하지 않는다"를 만든다. 액터는 `asyncio.Queue` 하나 + 소비자 태스크 하나이므로 **세션당 쓰기 주체가 하나**다(D-09①). 두 번째 겹은 `(session_id, seq)` PK로 프로세스 경계를 넘어서도 유효하다.

---

## 3. 파이프라인 B — 폴링 (읽기 경로)

`frontend/src/session/usePolling.ts` ↔ `web/routes_events.py:60`

```
브라우저 4개, 각자 1.5초마다 (POLL_INTERVAL_MS=1500, D-38)
    GET /api/sessions/{id}/events?from_seq=lastSeq+1
        │
        ├─ store.read_events(from_seq)   ← 새 사건 목록 (경계 포함)
        └─ rebuild_state(store, id)      ← **매 요청마다 사건 전체를 다시 접는다**
                                            상태 숫자를 만드는 곳은 이 함수 하나뿐
        ▼
    { events: [...], state: {12칸 + clock_segment_count + auto_advance_threshold} }
        ▼
    groupTurns()   session/groupTurns.ts
        caused_by_seq 사슬을 거슬러 사건을 「턴」 단위로 묶는다
        ├─ action_declared     → 턴의 뿌리. 우측 채팅 한 줄
        ├─ action_confirmed    → 턴 머리말(무브·능력치) + 채팅 꼬리표
        ├─ check_resolved      → 턴 카드의 판정 줄 + 주사위 모달 한 번
        ├─ narration_appended  → 그 턴 카드 안에만 쌓인다 (다른 턴과 안 섞인다)
        ├─ clock_advanced      → 그 턴 카드 아래 배너 + 좌측 시계 눈금 강조
        └─ ai_invoked          → 안 그린다
        ▼
    lastSeq = state.last_seq
```

- 처리기는 `async def`이고 내부에 `await`가 하나도 없다 → 이벤트 루프 기준 원자적. `read_events`와 `rebuild_state` 사이에 다른 사건이 끼어들 수 없다.
- 브라우저는 마지막 순번을 저장하지 않는다. 새로고침·재접속은 언제나 `from_seq=0`부터 전체 역사를 다시 받아 다시 그린다(D-41).
- 7회 연속 실패(≈10.5초)에 끊김 배너를 띄우고, 폴링은 계속 재시도한다(D-40).
- 모든 텍스트는 JSX 자식으로만 들어간다 — `dangerouslySetInnerHTML`은 저장소 어디에도 없다. AI 서사와 플레이어 원문이 스크립트 문맥에 닿는 지점이라 HTML 문자열 대입 경로를 만들지 않는다(T-04-01).

---

## 4. 파이프라인 C — 캐릭터 (읽기 전용)

`web/routes_characters.py`

```
GET  /characters                → 입장 화면 목록 (선언 순서 그대로)
POST /select-character          → gptrpg_character 쿠키 (서명 없음, httponly, 14일)
GET  /my-character              → 쿠키 파싱. 옛 형식·다른 세션·모르는 id는 전부 selected:false
GET  /characters/{character_id} → 시트. **이 주소에 GET 처리기 하나만 등록되어 있다**
                                   → PUT/PATCH/DELETE는 FastAPI가 405로 거절 (RIG-05가
                                     "쓰기 경로가 없다"를 시험으로 증명 가능한 사실이 된다)
```

신뢰 모델은 「같은 방 네 명이 링크 하나를 나눠 가진 것」이다(D-42). 쿠키로 할 수 있는 최악의 일은 남의 읽기 전용 시트를 보는 것. **M0 실험 한정 판단이며 M1 계정 체계로 그대로 가져가면 안 된다** — 그 판단은 `routes_characters.py` 모듈 도크스트링에 이미 적혀 있다.

---

## 5. 파이프라인 D — 프롬프트 조립 (원가를 3.7배 가르는 순서)

`agents/prompt_assembly.py:105` / `:130`

```
system[0]  영구 고정   룰북 이름 + 무브 10개 목록 + 역할 지시문        + cache_control
system[1]  세션 고정   장면 캐스트 4명 · 캐릭터 상태값 · 위협 시계     + cache_control
                       (이름·정체·원하는 것·지나온 칸·다음 칸,
                        파국은 시계를 다 지났을 때만)
messages   턴마다     "최근 대화 10턴" + 이번 문장 또는 판정 요약
```

규율은 두 줄이다. **① 시각·플레이어 표시 이름·세션 식별자처럼 호출마다 달라지는 값을 `system`에 한 글자도 넣지 않는다.** ② 관측 지표(`clock_advances` / `fails_since_clock`)를 `ClockState`에 애초에 담지 않는다 — AI가 "봐주기를 재는 지표"를 보면 그 지표를 만족시키는 쪽으로 서술을 바꿔 계측 자체가 무의미해진다.

`TurnContext`는 칸이 정확히 넷이고(`agents/context.py:51`), `recent_turns`가 10개를 넘으면 조용히 자르지 않고 `TooMuchContext`를 던진다. AI가 저장소 전체를 훑는 경로는 구조적으로 없다(D-31).

---

## 6. 파이프라인 E — 집계 (MEAS)

```
GameState  ─────── build_report(state) ───────▶ 상태에서 오는 칸들 ──▶ .gptrpg/reports/{id}.json
사건 목록  ─ (선택) build_report(…, events=) ─▶ latency + friction + episodes

호출자 둘 — 넘기는 것이 다르다:
  · SessionActor._process 가 사건 하나 쓸 때마다 자동 (D-44)
        events 를 **안 넘긴다** → latency/friction/episodes 는 null
        (사건마다 전체를 다시 읽으면 비용이 세션 길이의 제곱이 된다)
  · uv run gptrpg report --db … --session …   (조회용)
        events 를 넘긴다 → 세 칸이 채워지고 파일에 덮어써진다
```

**그래서 세션이 끝나면 `gptrpg report`를 반드시 한 번 쳐야 한다** — 자동 저장본만으로는 응답 속도·마찰·시계 칸별 누적이 남지 않는다. `null`은 「계산하지 않았다」는 뜻이며 「0이었다」와 다르다.

`episodes`는 시계가 한 칸 돌 때마다의 **누적 스냅샷**이다. 세션 합계만으로는 「무료로 주는 1~2칸이 얼마짜리인가」(D20·D21의 상품 단위, D-61이 실험 목표로 잡은 범위)를 갈라낼 수 없어서 생긴 칸이다 — 세션이 3칸까지 갔으면 합계에 무료 구간 밖의 몫이 섞인다. 숫자를 여기서 새로 세지 않는다: 리듀서에 사건을 하나씩 먹여 가며 `clock_advanced`에서 그때의 `GameState`를 찍는다(누적 규칙의 출처가 리듀서 하나뿐이라는 성질을 깨지 않는다).

`build_report`는 **어떤 걸러내기도 하지 않는다.** 실패한 턴, 오류가 난 AI 호출, 서사가 끝까지 안 나온 턴이 전부 그대로 세어진다 — 그래서 03-06이 실패한 서사에도 `RecordAiCall`을 반드시 제출하게 만들었다.

`failure_count`(절대 초기화 안 됨, MEAS-03의 분자)와 `fails_since_clock`(시계가 돌 때마다 0, 화면 표시용)을 분리해 두는 것이 「실패는 많은데 시계가 안 돈다」를 사후에 관측 가능하게 만드는 장치다.

### 가설 → 계측 필드 대응

| 가설 | 필요한 숫자 | 지금 어디서 나오나 |
|---|---|---|
| H1 재미 | 2세션 참석·완주 | **손으로** (`session-N-log.md`). 실질 표본 3명 — 채점 규칙 §1~§2 |
| H2 봐주기 | 실패 수 ÷ 시계 진행 수 | `failure_to_clock_ratio` (자동). **다만 항상 3.0에 고정되어 정보량이 0이다** — 판정은 관찰 기록으로 (§9-10, 채점 규칙 §3) |
| H3 룰북 데이터화 | 고친 곳/참은 곳 | `02-INTERFACE-CHANGES.md` (Phase 2에서 판정 완료) |
| H4 자유 텍스트 마찰 | 엔터 한 번 / 클릭 한 번 / 직접 찾아야 함 3분류 | `report`의 `friction` (자동, 원자료). 문턱 판정은 사람이 라벨을 다시 붙인 뒤 (채점 규칙 §4) |
| H5 원가 | 입력·출력·캐시 토큰 × 단가 | `report`의 `prompt_tokens` / `completion_tokens` / `cached_prompt_tokens` (자동). 계산식·기준 단가는 채점 규칙 §5 |
| — 무료 체험 획득 원가 | 시계 1~2칸의 토큰·시간 | `report`의 `episodes` (자동) — D-61이 실험 목표를 그 상품 단위로 잡아 실측이 된다. 멈춤 판정에는 쓰지 않는다 |
| H6 비경험자 진입 | 캐릭터 완성 여부·애착 답변 | **손으로** (`character-creation-script.md`) |
| — 응답 속도 (MEAS-02) | 두 지점의 지연 | `report`의 `latency` (자동) — 분류기 호출과 「확인→서사 첫 글자」를 따로 |

**채점 규칙은 실험 전에 고정되어 있다** — `docs/experiment/hypothesis-scoring-rules.md`. 자동 집계된 숫자를 최종 판정으로 쓰지 않는다는 것, 문턱·표본·기준 단가를 사후에 조정하지 않는다는 것이 그 문서의 실질이다.

---

## 7. 파이프라인 F — 명령줄 경로

브라우저 없이도 같은 사건 기록에 붙는다. 웹과 **완전히 같은 액터·저장소·규칙 코어**를 쓴다.

```
gptrpg turn      한 턴 전체 (분류 → 세 갈래 확인 → 판정 → 서사)   cli/turn_flow.py:172
gptrpg submit    사건 하나 직접 (declare/confirm/roll/narrate/clock/ai)
gptrpg replay    사건 기록에서 상태 재구성 후 10칸 출력 (벽시계 값 없음 = 반복 실행에 바이트 동일)
gptrpg report    집계 조회 + JSON 저장 (여기서만 latency/friction 이 계산된다)
gptrpg agents    set  — 제공자·모델을 대화 없이 그대로 적는다 (실행 절차서용)
                 select — 살아 있는 모델 목록을 받아 번호로 고른다 (대화형 + 네트워크)
                 show — 지금 저장된 두 역할을 찍는다
```

`agents set`과 `select`가 갈라져 있는 이유는 **런북에 적을 수 있어야** 하기 때문이다 — `select`는 대화형이고 모델 목록 조회 왕복을 하므로 "이렇게 치면 이 상태가 된다"를 절차서에 쓸 수 없다. 둘 다 완성되지 않은 설정 파일을 `load_partial_config`로 읽는다(엄격한 `load_config`로 읽으면 역할 하나만 저장된 파일에서 예외가 나고, 그것을 빈 사전으로 받으면 방금 저장한 다른 역할이 지워진다).

`submit clock`이 **D-21의 나머지 두 진행 규칙(조건·AI 선택)에 닿는 유일한 경로**다 — 웹 화면에는 시계를 손으로 돌리는 버튼이 없다(§9-10).

---

## 8. 이 파이프라인이 보장하는 것 — 그리고 무엇이 그걸 강제하나

| 보장 | 강제 지점 |
|---|---|
| 상태는 사건 기록에서만 나온다 | `rebuild_state` → `fold` 하나뿐. 중간 저장 없음(D-08). 액터도 생성 시 같은 함수로 자기 인식을 복원한다 |
| 같은 굴림을 재생하면 같은 결과 | 굴린 눈 원본이 `check_resolved.rolls`에 남고, `replay_roller`가 그걸 그대로 되먹인다 |
| AI가 수치를 못 바꾼다 | `.importlinter` contract:3 + 모델 출력은 무브 **이름 문자열**로만 해석 (`_parse_candidates`) |
| 룰북에 없는 무브가 기록에 안 남는다 | `UnknownMove`를 조용히 통과시키지 않는다. 재시도 층 **밖에서** 대조한다 |
| 거부된 명령이 반쪽 상태를 안 남긴다 | `_prepare`(검증) → `next_seq`(순번) 순서 |
| 확인 없이 주사위가 안 굴러간다 | `tier=="none"`에서는 확인 버튼을 만들지 않는다. 판정은 `confirm` 처리기에만 있다 |
| 실패한 턴이 집계에서 안 빠진다 | `RecordAiCall`을 성공·실패 무조건 제출 + `build_report`에 필터 없음 |
| 이미 쓴 기록을 안 고친다 | `EVENT_SCHEMA_VERSION` 3 + 리듀서에 옛 판 해석 경로 두 개 — 판 1의 `counts_as_failure` 부재(`_legacy_v1_counts_as_failure`)와 판 1·2의 `cached_prompt_tokens` 부재(기본값 0). 판 3의 새 칸을 **필수로 만들지 않은** 이유가 이것이다: 필수면 옛 기록이 아예 파싱되지 않아 Phase 6이 두 세션 기록을 함께 읽을 수 없다 |
| 원가를 계산할 수 있다 | 입력·출력·캐시 토큰이 사건에 **따로** 남는다. 합계 하나로 세면 단가가 4~5배 다른 두 값에 단가 하나를 곱하는 계산이 되어 H5 판정 자체가 불가능해진다 |

---

## 9. 파이프라인과 설계 의도가 어긋나던 지점 — 무엇이 고쳐졌고 무엇이 남았나

여기부터는 "코드가 이렇게 돈다"가 아니라 "그래서 이게 문제다"다. 근거는 전부 위 절의 코드 경로다.
2026-08-04에 11건을 적었고, 2026-08-05에 그중 8건을 고쳤다. **고친 항목도 지우지 않는다** —
무엇이 왜 문제였는지가 다음에 같은 실수를 막는 유일한 기록이다.

### 9-A. 고쳐진 것 (8건)

1. ~~**`.gptrpg/agents.json`이 저장소에 없다.**~~ **[고침]** 설정 파일은 여전히 저장소에 안 들어가지만(`.gitignore`의 `.gptrpg/`), 이제 그 상태를 벗어나는 절차가 재현 가능하다 — `gptrpg agents set --role … --provider … --model …`이 대화·네트워크 없이 값을 적고, README A절 2번이 그 두 줄을 그대로 담고 있다. 예전에는 `agents select`(대화형 + 모델 목록 조회 왕복)뿐이라 절차서에 적을 수 없었고, README는 "이미 설정되어 있다. 확인만"이라고 **사실이 아닌 것**을 적고 있었다. 이 작업 중에 관련 버그도 하나 잡았다: `set`을 두 번 쳐서 두 역할을 채우면 두 번째가 첫 번째를 지웠다(`load_config`가 역할 하나만 있는 파일에 예외를 던지고, 호출부가 그것을 빈 사전으로 받았다) — `load_partial_config`가 「고치기 위해 읽는 경로」를 분리해 해결했고, `agents select --role`에 있던 같은 함정도 함께 고쳤다.

2. ~~**원가(H5)를 집계 파일로 계산할 수 없다.**~~ **[고침]** `GameState`·`AiInvoked`·집계가 이제 입력·출력을 끝까지 나눠 센다(`prompt_tokens` / `completion_tokens`). `total_tokens`는 두 값의 파생값으로 남겨 기존 화면 호출부를 깨뜨리지 않았다. `gptrpg report`가 두 값을 따로 찍는다.

3. ~~**캐싱 설계 제약이 실제로 쓰는 제공자에서 무력하다.**~~ **[절반 고침 — 계측은 되고 전달은 여전히 안 된다]** `cache_control`이 OpenAI 호환 표면에서 버려지는 것은 그대로다(그쪽에 대응 API가 없다). 대신 **캐시 적중을 실측할 수 있게 했다** — `cached_prompt_tokens`가 사건 스키마(판 2→3)·리듀서·집계에 생기고, 제공자 다섯이 각자의 자리에서 그 값을 꺼낸다(OpenAI 계열 `prompt_tokens_details.cached_tokens` / Anthropic `cache_read_input_tokens` / Gemini `cached_content_token_count`). Anthropic은 `input_tokens`에 캐시 몫을 포함하지 않아 `prompt_tokens`를 따로 합산한다 — 그러지 않으면 캐싱이 걸린 호출의 원가가 실제보다 싸게 계산된다. **0은 「적중 없음」과 「미보고」를 구분하지 않으므로 그때의 원가는 상한선으로 읽어야 한다** — 그 규칙은 `hypothesis-scoring-rules.md` §5에 있다.

4. ~~**스트림 정지 시 배경 스레드가 샌다.**~~ **[완화]** 누수 자체는 없앨 수 없다(파이썬에 블로킹 읽기를 강제로 끊을 수단이 없다). 없앤 것은 **겹치는 것**이다 — `StreamStalled` 전용 예외가 생겨 스톨은 재시도하지 않는다. 예전에는 스톨이 「첫 조각 전 실패」로 묶여 재시도돼서 턴 하나가 막힌 스레드를 **둘** 남기고 사람을 180초 기다리게 했다. 그리고 누수가 일어나면 `_LEAKED_PUMP_THREADS`를 올리고 표준오류에 한 줄 찍는다 — 서버를 몇 시간 띄우는 실험에서 "다시 띄울까"를 판단할 근거가 그 줄이다.

5. ~~**시계에 상한이 없어 화면에 `5/4`가 뜰 수 있다.**~~ **[고침]** `_maybe_auto_advance`가 마지막 칸에 도달하면 더 돌리지 않는다. D-47의 뒷문장("파국 이후에도 즉흥으로 계속 진행하지 않는다")을 코드로 지킨 것이며, 실패는 계속 세어지므로(`failure_count`는 초기화되지 않는다) MEAS-03의 분자를 잃지 않는다. 화면 쪽도 `StoryPane`이 `Math.min(segment_index, segmentCount)`으로 한 번 더 막는다 — 상한이 생기기 전에 기록된 세션이 있어도 `5/4`가 안 뜬다.

6. ~~**H4·MEAS-02를 세는 코드가 없다.**~~ **[고침]** `gptrpg report`가 둘 다 낸다. **마찰 3분류**는 선언·확인 짝을 맞춰 `accepted_as_is`(엔터 한 번) / `picked_other`(클릭 한 번) / `no_candidate`(직접 찾아야 함)로 세고 HYP-04의 두 문턱에 대응하는 비율까지 찍는다. **응답 속도**는 두 지점을 따로 낸다 — 분류기 `latency_ms`(D-33의 0.5초 지점)와, `caused_by_seq` 사슬(확인→판정→서사)을 거슬러 두 기록 시각을 뺀 **확인→서사 첫 글자**(2초 지점). 뒤엣것은 어느 사건 칸에도 없던 값이다: `master_gm`의 `latency_ms`는 서사 **전체** 시간이라 D-33이 목표를 둔 「첫 글자」와 다르다. 평균이 아니라 중앙값 + 최대값을 쓰고, D-33의 두 문턱(5초·15초) 초과 횟수를 함께 센다.

7. ~~**동시 확인이 두 서사를 문장 단위로 뒤섞는다.**~~ **[화면 쪽에서 해소]** 사건 기록 쪽은 지금도 그대로다 — 두 `narrate` 스트림이 각자 `AppendNarration`을 제출하고 액터가 도착 순서대로 쌓는다. 화면이 `session/groupTurns.ts`에서 `caused_by_seq` 사슬을 거슬러 턴 단위로 묶으므로 두 이야기가 각자의 카드에 쌓인다. 서버에서 세션당 서사를 직렬화하는 선택지는 쓰지 않았다(D-10의 「락 없음」과 어긋난다).

8. ~~**드라이런의 호출 수 계산이 코드와 안 맞는다.**~~ **[고침]** `session-prep.md`에 「정정」 절을 넣었다. 완주한 행동당 AI 호출은 정확히 2회이고 세션 하나는 약 60~80회다(적혀 있던 120회가 아니다). 한도 결정은 안 바뀌지만(NIM에 일일 상한이 없다) 같은 숫자가 H5 원가 환산의 입력값이라 1.5배 과대 추정을 만들고 있었다.

### 9-B. 남은 것 (3건)

9. **읽기 비용이 사건 수에 선형으로 는다 — 절반만 줄였다.** 요청 하나가 사건 전체를 **두 번** 읽던 것을 한 번으로 줄였다(`rebuild_state_from_events`가 이미 읽은 목록을 접는다 — 폴링 처리기와 `build_turn_context` 양쪽. 행동 하나당 전체 읽기가 4회에서 2회로). 그러나 **매 요청이 전체를 읽는다는 구조 자체는 그대로다** — 상태는 언제나 처음부터 접어 만들어야 하기 때문이다(D-08, 중간 저장 없음). 스냅샷이나 증분 폴링은 M1의 첫 숙제다. `_write_report_snapshot`도 사건마다 JSON 파일을 통째로 다시 쓴다(그쪽은 상태 한 칸만 보므로 O(1)이다).

10. **D-21의 세 진행 규칙 중 하나만 있다 — 그래서 H2를 비율로 판정할 수 없다.** `_maybe_auto_advance`가 `fail_counter`만 만들고, `condition`/`ai_choice`는 CLI `submit clock`으로만 닿는다. 서버가 떠 있는 중에 CLI가 같은 세션에 쓰면 두 번째 쓰기 프로세스가 되어 `next_seq` 경합이 나고(PK 제약이 잡아 주지만 CLI가 실패한다), 즉 **세션 중에 시계를 손으로 돌리는 안전한 경로가 없다.** 더 중요한 결과는 계측 쪽이다 — 실패 3회마다 정확히 한 칸이 도므로 `failure_to_clock_ratio`가 **항상 3.0에 고정되어 정보량이 0**이다. ②③ 구현은 M1로 넘기고, 그때까지 H2를 어떻게 판정하는지는 `hypothesis-scoring-rules.md` §3이 정한다.

11. **실험 설계 자체의 유보 3건.** D-57 이탈(7일 → 1~3일), D-58(무료 모델로 D18의 "품질 상한선" 취지 미충족), 그리고 오너가 참가자 겸 관찰자라 **H1의 실질 표본이 3명**이라는 것(D-55·D-56의 귀결이며 어느 문서에도 적혀 있지 않던 사실). 셋 다 코드 문제가 아니라 **판정을 제약하는 조건**이다. 이 셋이 H1의 킬 판정을 불가능하게 만든다는 판단과 그 대응은 `hypothesis-scoring-rules.md` §1~§2에 있다.

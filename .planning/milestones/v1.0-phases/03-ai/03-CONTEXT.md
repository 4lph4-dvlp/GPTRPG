# Phase 3: AI 진행자 한 턴 - Context

**Gathered:** 2026-08-02
**Status:** Ready for planning

<domain>
## Phase Boundary

플레이어가 자유 문장을 치면 분류 → 확인 → 주사위 → 서사까지 한 턴이 끊기지 않고 끝까지 도는 것을 만든다. 여섯 가설 중 RIG-01·RIG-03·MEAS-02·MEAS-04가 이 단계의 요구사항이다.

**이 단계가 만드는 것:** action_classifier(경량 에이전트, 자유 텍스트 → 무브+능력치 분류) + master_gm(최상급 에이전트, GM 대응 선택 + 서사 생성) 두 에이전트의 실제 호출 코드 + 제공자 추상화 계층(D19) + 재량 판정 계층의 혼합형 확인 흐름(D16) + 이 모두를 사람이 직접 확인할 CLI 인터페이스 확장.

**이 단계가 만들지 않는 것:** 실제 웹 화면(배치·컴포넌트·반응형 — M0 범위 밖), 여러 명이 같은 화면을 보는 동기화(RIG-07, Phase 4), onboarding_agent·context_summarizer(Phase 5 이후 영역), 룰북 파일 업로드/파싱, 위협 시계 실패 카운터 화면(RIG-04, Phase 4).

**이 단계의 유일한 숙제(로드맵 원문):** 프롬프트 조립 순서를 안정성 순서(영구 고정 → 세션 고정 → 턴마다 변함)로 짜는 것 — 캐싱 유무가 원가를 3.7배 가른다. 그리고 v1에만 있고 유지·폐기 진술이 없던 "에이전트 응답 껍데기 + 경량/중형 모델 타임아웃·재시도"를 최소한만 정하는 것(이번 논의로 해소).

</domain>

<decisions>
## Implementation Decisions

### 화면 형태 — 이번 단계에서 무엇으로 확인하나

- **D-25:** 이번 단계에서 "한 턴이 끝까지 도는지" 사람이 직접 확인하는 인터페이스는 **CLI 확장**이다. Phase 1·2가 만든 명령줄 도구(declare/confirm/roll/narrate/clock/ai 서브커맨드)를 그대로 확장한다. 실제 웹 화면은 만들지 않는다.
  - *이유:* Phase 4(RIG-07, 링크 하나로 여러 명)에서 처음으로 실제 웹 화면이 필요해진다. 지금은 AI 턴 루프 자체가 도는지가 검증 대상이고, CLI가 최소 비용으로 그것을 증명한다. ROADMAP의 "화면은 만들지만 설계는 하지 않는다"는 문구를 CLI 확장으로 충족한다 — 배치·컴포넌트를 고민할 필요가 없는 화면이 곧 CLI다.

- **D-26:** 응답이 5초를 넘으면 CLI에서 **점 세기(dots)**로 진행 표시를 한다.
  - *이유:* 별도 라이브러리 없이 터미널 출력만으로 구현되고, 성공 조건 3번(응답이 늦어도 게임이 멈추지 않는다)을 사람 눈으로 확인할 수 있는 최소 신호다.

### 에이전트 응답 껍데기 + 경량/중형 모델 타임아웃·재시도 — 최소 규칙

> v1에만 있고 유지·폐기 진술이 없던 항목(`.planning/INGEST-CONFLICTS.md` WARNING 2번째 항목, `STATE.md` Blockers #2). 이번 논의로 M0 실험 도구용 최소 규칙만 정하고, 제품 규격은 M1 착수 시 정한다.

- **D-27:** action_classifier(경량 모델) 타임아웃은 **5초**. master_gm(최상급 모델)은 D33이 이미 15초로 확정했으므로 건드리지 않는다.
  - *이유:* 문장 입력 → 행동 확인 표시 목표가 0.5초(D33)이므로 그보다 훨씬 짧은 값도 고려됐으나, 실험 도구 단계에서는 여유를 조금 더 주는 쪽을 택했다.

- **D-28:** 타임아웃이나 모델 오류로 실패하면 **한 번 재시도 후 실패 처리**한다. v1의 지수 백오프 최대 2회, `MODEL_ERROR`/`VALIDATION_FAILED` 오류 종류별 구분은 이번 단계에 넣지 않는다.
  - *이유:* 실험 도구에 과한 정교함이다. 재시도 1회로도 일시적 오류는 대부분 걸러진다.

- **D-29:** action_classifier가 재시도까지 실패하면 **자동으로 "판정 없이 진행"으로 떨어진다** — 재량 판정 계층의 "무브 없음" 경로(§4.7)를 그대로 재사용한다.
  - *이유:* 플레이어는 잠시 멈춤을 느끼지만 게임 자체는 멈추지 않는다. 새 분기 코드 없이 이미 검증 대상인 기존 경로를 재사용한다.

- **D-30:** 에이전트 응답 껍데기(AgentResult류)의 최소 규격은 **성공/실패 + 값 + 걸린 시간·토큰 수**다. v1의 `error_code`·`fallback_suggestion` 등 나머지 칸은 이번 단계에서 만들지 않는다.
  - *이유:* `AiInvoked` 사건(D-14)이 이미 `agent_role`/`model`/`provider`/`prompt_tokens`/`completion_tokens`/`latency_ms`를 기록하도록 스키마가 잡혀 있다. 응답 껍데기는 그 값들을 호출 직후 담는 임시 그릇이면 충분하다. `error_code`의 `LOW_CONFIDENCE`는 D16이 신뢰도 임계값을 폐기하면서 이미 근거를 잃었다.

### 모델·제공자 선택

- **D-31:** **5개 주요 제공자(Anthropic Claude, Nvidia NIM, OpenRouter, Google Gemini, OpenAI)의 API 키를 환경 변수로 선택적으로 입력받는다.** 프로그램 시작 시 존재하는 API 키를 기반으로 사용 가능한 제공자를 감지해 고를 수 있게 하고, 제공자를 고르면 그 제공자가 제공하는 모델의 **실시간 목록을 조회해 그중에서 고르게 한다.**
  - *이유:* 사용자가 직접 확인한 요구사항. D19("에이전트별 모델 분리 + 제공자 추상화 계층을 M0에 넣는다")를 다섯 제공자·실시간 모델 목록까지 구체화한 것이다.

- **D-32:** 이 선택 화면은 **action_classifier(경량)와 master_gm(최상급)에 각각 따로 적용**한다 — 같은 제공자를 고르더라도 모델은 다를 수 있다.
  - *이유:* D19의 "에이전트별 모델 분리" 원문과 정확히 일치한다. 하나로 묶으면 "경량 모델은 원가 절감용"이라는 원래 취지(§3.5, 원가 비중 action_classifier 5% vs master_gm 95%)가 흐려진다.

- **D-33:** 제공자·모델 선택은 **한 번 고르면 파일로 저장**하고, 이후 실행에서는 다시 묻지 않는다.
  - *이유:* 실험 참가자 4명이 매번 선택 화면을 마주치면 실험 자체가 방해된다(EXP-02, 우리는 관찰만 한다). 선택은 진행자(운영자) 몫이지 플레이어 몫이 아니다.

### 재량 판정 확인 화면의 표현

> §4.7의 신뢰도별 UI 강도 표(높음=엔터 한 번, 낮음=후보 2~3개, 무브없음=판정 없이 진행+되돌리기)를 D-25에서 정한 CLI 인터페이스로 구체화한다.

- **D-34:** 신뢰도가 높을 때(무브가 하나로 선명할 때) CLI는 **한 줄 제안 + `[Enter=확인 / n=아니오]`**를 보여준다.
  - *이유:* 설계 문서의 "이건 「위험을 무릅쓰다」 판정이 필요해 보입니다 [민첩으로 굴리기] [아니오, 그냥 하는 겁니다]" 문구를 CLI 텍스트로 그대로 옮긴다. "엔터 한 번" 원칙이 유지된다.

- **D-35:** 신뢰도가 낮아 후보가 2~3개 나란히 될 때, 플레이어는 **번호 목록에서 숫자를 입력**해 고른다.
  - *이유:* CLI에서 가장 단순하고 오타 여지가 적은 선택 방식.

- **D-36:** 시스템이 "판정 없이 진행"으로 떨어졌는데 사실 판정이 필요했다면, **되돌리기 전용 화면을 만들지 않는다** — 플레이어가 다음 턴에 직접 판정 명령(`roll` 서브커맨드, Phase 1·2가 이미 만듦)을 치면 된다.
  - *이유:* 새 되돌리기 경로를 만들지 않고 이미 검증된 기존 명령을 재사용한다. 실험 도구 단계에 맞는 최소 구현.

- **D-37:** 신뢰도 숫자 자체(예: 0.82)는 플레이어에게 **노출하지 않는다** — UI 강도(프롬프트 모양)만 바뀐다.
  - *이유:* §4.7 원문 "신뢰도는 UI 강도로만 쓴다"를 그대로 따른다. 숫자를 보여주면 D16이 폐기한 임계값 개념이 플레이어 경험으로 되살아난다.

### Claude's Discretion

계획·조사 단계에서 판단하되, 위 결정을 뒤집지 않는 선에서:

- 다섯 제공자 각각의 실시간 모델 목록 조회 API 형태 — 제공자별로 방식이 다를 수 있으므로 `/gsd-plan-phase 3`의 리서치 단계가 조사한다
- 프롬프트 조립 순서(영구 고정 → 세션 고정 → 턴마다 변함)의 구체적 구현 — 어느 필드가 어느 층에 속하는지 세부 배치
- action_classifier의 신뢰도 판정 기준(무엇을 "높음"으로 볼지)의 구체적 임계값이나 계산 방식
- 재시도 사이 대기 시간(즉시 재시도 vs 짧은 지연)
- CLI 서브커맨드 이름과 정확한 인자 형태(예: `confirm` 확장 방식)
- 제공자·모델 선택 결과를 저장할 파일 형식과 위치

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 단일 권위 문서
- `docs/GPTRPG-M0-decisions.md` §D5 (판정 코드/룰북 데이터), §D14 (주사위 순수 코드), §D16 (재량 판정 신뢰도 임계값 폐기), §D17 (에이전트 4개), §D18 (M0 최상급 모델 고정), §D19 (에이전트별 모델 분리 + 제공자 추상화 계층), §D31 (매 턴 주입 4가지 고정), §D33 (응답 속도 두 지점 + 15초 초과 시 판정 결과 먼저) — 이 단계에 직접 걸리는 결정
- `.planning/intel/decisions.md` — 위 항목들을 항목별로 정리한 것

### 에이전트·응답 흐름
- `docs/GPTRPG-design-plan.md` §3.4 (에이전트 4개 표 — action_classifier/master_gm 역할, 삭제·강등된 6개 항목, 턴당 평균 1.5회 LLM 호출)
- `docs/GPTRPG-design-plan.md` §3.5 (모델 전략 — action_classifier 원가 비중 5%/검증 가능 vs master_gm 95%/주관적, 프로바이더 추상화 계층 M0 필수)
- `docs/GPTRPG-design-plan.md` §3.6 (응답 속도 목표 두 지점 + 초과 시 화면 동작 — 5초 진행 표시, 15초 판정 결과 먼저)
- `docs/GPTRPG-design-plan.md` §3.8 (기억 주입 규칙 — 매 턴 넣는 것 네 가지 고정, 프롬프트 캐싱을 위한 조립 순서)
- `docs/GPTRPG-design-plan.md` §4.7 (재량 판정 계층 — 5단계 파이프라인, 신뢰도별 UI 강도 표, "판정 없이 진행" 되돌리기)

### 프로젝트 수준
- `.planning/PROJECT.md` — Constraints 절(LLM 경계, 프롬프트 캐싱, 기억 주입, 응답 속도, 모델·모델 교체 가능성), Key Decisions 표(특히 D5·D14·D16·D17·D18·D19·D31·D33)
- `.planning/REQUIREMENTS.md` — RIG-01·RIG-03·MEAS-02·MEAS-04가 이 단계의 요구사항
- `.planning/ROADMAP.md` Phase 3 절 — 성공 조건 5개, "여기서 최소한만 정할 것"(에이전트 응답 껍데기+타임아웃·재시도), "화면은 만들지만 설계는 하지 않는다"
- `.planning/STATE.md` Blockers/Concerns #2 — 이번 논의로 최소 규칙을 정해 해소한 항목
- `.planning/INGEST-CONFLICTS.md` WARNING 2번째 항목 — 에이전트 응답 껍데기+타임아웃·재시도가 유지·폐기 진술 없이 남아 있던 근거(v1 §2.6.3)

### Phase 1·2 산출물 (이 단계가 직접 확장하는 것)
- `src/gptrpg/event_log/schema.py` — `AiInvoked`(agent_role/model/provider/prompt_tokens/completion_tokens/latency_ms), `ActionConfirmed`(system_suggestion/player_confirmed) 이벤트가 이미 이 단계가 채워야 할 자리를 정의해 둠
- `src/gptrpg/session_actor/actor.py` — `RecordAiCall`/`ConfirmAction` 명령과 검증→규칙코어 호출→기록 파이프라인
- `.planning/phases/01-rules-core-and-event-log/01-06-SUMMARY.md` — CLI 서브커맨드(declare/confirm/roll/narrate/clock/ai) 최종 형태
- `.planning/phases/02-two-rulebooks-one-vessel/02-04-SUMMARY.md` — CLI `--rulebook` 플래그, 고친 곳/참은 곳 기록 관례

### 읽으면 안 되는 것
- `docs/GPTRPG-design-plan-v1-archive.md` §2.6.3 — 폐기된 v1의 `AgentResult<T>` 껍데기 원안(2초/5초/15초 타임아웃, MODEL_ERROR/VALIDATION_FAILED 재시도 구분). 이번 논의로 M0용 최소 규칙(D-27~30)이 새로 정해졌으므로 v1 원안을 그대로 구현하지 않는다 — 파일 자체에 폐기 표기가 없어 열면 유효한 명세처럼 보이니 주의

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/gptrpg/event_log/schema.py`의 `AiInvoked` — `agent_role`/`model`/`provider`/`prompt_tokens`/`completion_tokens`/`latency_ms` 필드가 이미 응답 껍데기 최소 규격(D-30)과 정확히 겹친다. 새 스키마를 만들 필요가 없다
- `src/gptrpg/event_log/schema.py`의 `ActionConfirmed` — `system_suggestion: dict[str, str]`, `player_confirmed: bool` 필드가 이미 있어 action_classifier의 제안+확인 흐름(D-34, D-35)을 그대로 기록할 수 있다
- `src/gptrpg/session_actor/actor.py`의 `RecordAiCall`/`ConfirmAction` 커맨드 — 검증 → 규칙 코어 호출 → 기록 파이프라인이 이미 있어 실제 AI 호출 결과를 채워 넣기만 하면 된다
- `src/gptrpg/cli/main.py` — Phase 1·2가 만든 서브커맨드 패턴(declare/confirm/roll/narrate/clock/ai)을 그대로 확장한다(D-25)

### Established Patterns
- Phase 1이 세운 3계층 경계(`rules_core`/`event_log`/`session_actor`)와 `.importlinter` 자동 검사가 이 단계에도 적용된다. AI 호출 코드는 이 세 폴더 중 어디에도 속하지 않는 바깥 층이어야 한다 — `rules_core`는 여전히 AI를 몰라야 한다(성공 조건 2번, D14)
- "값 + 출처" 패턴(`Modifier.type/value/source`, Phase 2의 D-20)이 제공자·모델 설정 파일의 모양에도 참고가 될 수 있다

### Integration Points
- `src/gptrpg/session_actor/actor.py`의 `RecordAiCall`이 실제 AI 호출 결과를 받는 자리다 — 지금까지는 CLI가 수동으로 값을 채워 넣었는데(Phase 1·2 SUMMARY 참고), Phase 3는 이 자리를 실제 AI 호출 코드로 채운다
- `src/gptrpg/cli/main.py`의 서브커맨드 확장 지점 — 제공자·모델 선택 화면(D-31~D-33)이 시작 시 프롬프트 또는 별도 서브커맨드로 붙는다

</code_context>

<specifics>
## Specific Ideas

**사용자가 직접 명시한 제공자 목록과 선택 방식:** "Claude, Nvidia NIM, Openrouter, Gemini, OpenAI 5개의 주요 제공자의 API 키를 선택적으로 환경 변수로 입력 받고, 프로그램이 시작될 때 존재하는 API 키를 기반으로 프로바이더를 그 중 선택할 수 있고, 프로바이더 선택 후 모델 선택 화면에서 해당 프로바이더가 제공하는 모델들 실시간 리스트를 나열해서 선택할 수 있게 하자." (D-31)

이 다섯 제공자는 로드맵이나 잠금 결정 어디에도 이름으로 나오지 않는다 — 이번 논의에서 사용자가 처음으로 구체화한 것이다.

</specifics>

<deferred>
## Deferred Ideas

- **실제 웹 멀티플레이어 화면**(링크 하나로 여러 명이 같은 화면을 봄, RIG-07) — Phase 4
- **서사의 실시간 웹 스트리밍 전송**(문장 청크를 브라우저로 보내기) — Phase 4. 이번 단계는 CLI 출력으로 "문장 단위로 흘러나온다"를 증명하는 것으로 충분
- **v1의 전체 `AgentResult<T>` 껍데기**(`error_code`, `fallback_suggestion` 등) — 필요해지면 M1 착수 시 재검토
- **하트비트 주기·스트리밍 중 재연결 시 이어붙이기**(연결 유지 신호) — Phase 4(RIG-07)와 함께 다룬다. `.planning/INGEST-CONFLICTS.md` WARNING 2번째 항목의 나머지 절반
- **자동화율이 플레이하면서 올라가는 홈브루 승격 기능**(§4.7 "재사용") — M1 이후, 룰북 저작 도구와 함께

### Reviewed Todos (not folded)

없음 — `todo.match-phase 3` 조회 결과 매칭되는 미해결 todo 없음.

</deferred>

---

*Phase: 3-AI 진행자 한 턴*
*Context gathered: 2026-08-02*

---
status: complete
phase: 09-agent-architecture
source: [09-VERIFICATION.md]
started: 2026-08-09T13:33:13Z
updated: 2026-08-12T11:35:00Z
---

## Current Test

number: —
name: —
awaiting: none — 네 항목 전부 확인됨

## Tests

### 1. 연속 다섯 턴을 더 돌려 위협 시계가 4/4(마지막 칸)에 닿는지 확인 (T-09-20 페이싱 안전그물)
expected: 다섯 턴 안에 시계가 마지막 칸에 닿지 않는다 — 닿으면 clock_judge 조건 판단 프롬프트가 너무 헐겁다는 신호
result: PASS — 판정이 완결된 다섯 턴을 돌린 뒤 시계는 **2/4**에서 멈췄다. 마지막 칸에 닿지 않았다.

- 실행: `gptrpg turn` × 6회, DB `.gptrpg/uat9.db`, 세션 `pacing5`, 룰북 던전월드 계열
- 진행 내역: 턴1 → 0/4, 턴2 → 1/4, 턴3 → (판정 중단, 아래 관찰 참조), 턴4 → 2/4, 턴5 → 2/4, 턴6 → 2/4
- 진행 두 번 모두 `clock_advanced`의 `trigger="condition"`이었다 — 실패 누적이 아니라 Phase 9가 새로 만든 배경 조건 검사 경로다. 두 사건 모두 `caused_by_seq`가 그 턴의 `check_resolved`를 가리키고 `segment_index`가 1 → 2로 올랐다 (성공 조건 2: 배경 산출물이 사건으로 기록된다)
- 관측된 진행률: 완결 5턴에 2회. 문턱(5턴 내 4/4)은 넘지 않았지만 여유가 크지는 않다 — 같은 비율이 이어지면 8턴 근처에서 마지막 칸이다. **다음 실세션에서 다시 관찰할 값으로 남긴다**

### 2. clock_judge 역할을 존재하지 않는 모델로 바꾼 뒤 실제 살아있는 앱에서 한 턴을 돌려 D-05가 실전에서도 조용히 지켜지는지 확인
expected: 턴이 정상적으로 끝나고 서사가 그대로 나오며, 실패 문구는 표준오류에만 뜬다
result: PASS

- 설정: `gptrpg agents set --role clock_judge --provider nim --model does-not-exist-9999` (확인 후 원래 설정으로 복원 완료)
- 실행: uvicorn 웹 서버 + 브라우저(headless Chromium)로 세션 `uatweb`에 「선」으로 입장해 한 턴 완주 — 선언 → 무브 확인 → 판정(7 vs 목표 10, 대가 있는 성공) → 서사 11조각까지 끊김 없이 나왔다
- 실패 문구는 서버 표준오류에만: `경고: 제공자 호출이 2번 모두 실패했다 — 404 page not found` (2회 재시도 후 포기)
- 브라우저에는 아무것도 안 샜다 — 화면 글자에 `404`·`경고`·`does-not-exist`·`clock_judge` 없음, 콘솔 오류 0건, 4xx/5xx 네트워크 응답 0건
- 시계 표시는 0/4에서 움직이지 않았다 (판단이 아예 못 돌았으니 정상)

### 3. `gptrpg replay`로 한 턴의 ai_invoked 사건을 역할별로 확인 (situation_judge/scene_entity_judge/clock_judge 세 역할 모두 나타나는지)
expected: 세 역할이 각각 정확히 한 번씩 기록으로 보인다
result: PASS — 단, `gptrpg replay`가 아니라 사건 기록을 직접 읽어 확인했다

- **`gptrpg replay`의 출력에는 역할별 내역이 없다.** 「AI 호출 수: N」 합계 한 줄뿐이라 이 항목을 replay만으로는 확인할 수 없다. 사건 기록의 `ai_invoked` payload(`agent_role`)를 직접 읽어 대조했다
- 세션 `uatweb` 턴2 (정상 설정): `caused_by_seq=27` 하나에 `situation_judge`(seq 29) · `scene_entity_judge`(seq 30) · `clock_judge`(seq 31)가 각각 정확히 한 번씩 — 같은 원인 사건을 가리키는 것이 정적 병렬 gather의 증거다 (성공 조건 3)
- 세션 `1`(2026-08-09 기록)에서도 동일: seq 5·6·7이 전부 `caused_by_seq=3`
- 후속 제안: replay에 역할별 집계 한 줄을 붙이면 이 확인이 명령 하나로 끝난다 — 이번 범위 밖

### 4. 브라우저 경로에서 서사에 지시문 유출이 없는지, 시계 머리띠 표시가 튀지 않는지 육안 확인
expected: 서사에 진행자 지시문·시나리오 원문이 안 보이고, 시계 표시가 정상 범위에서만 움직인다
result: PASS

- 정상 설정으로 서버를 다시 띄우고 세션 `uatweb`에서 두 턴을 돌려 화면을 캡처해 확인
- 시나리오 원문 대조 — `threat_clocks.py`의 `identity`·`wants`·`segment_descriptions`·`catastrophe`에서 뽑은 특징 문구 6개(「수백 년간 잠들어」·「땅의 균형을 지키는 수호자」·「자신의 일부로 삼는 것뿐」·「합창이 된다」·「염소 두」·「회관 문이 저절로」)가 화면에 **하나도 안 나온다**
- 지시문·사고블록 흔적(`system`/`assistant`/`prompt`/`<think>`/`You are`/「당신은 진행자」/「규칙:」) **0건**
- 서사는 전부 극중 문장이다 — 인물 대사와 묘사뿐, 진행자 말투나 규칙 설명이 섞이지 않았다
- 시계 표시는 두 턴 내내 0/4 고정, 실패 카운터도 정상 범위. 튀는 값 없음
- 콘솔 오류 0건

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

확인 중에 관찰된 것들 — 이번 단계의 성공 조건을 깨지는 않지만 기록해 둔다.

1. **분류기가 닫힌 목록 밖 무브를 내면 그 턴이 그대로 죽는다.** `pacing5` 턴3에서
   `action_classifier`(llama-3.1-8b)가 `'track'`을 골라 `오류: 닫힌 목록에 없는 무브: 'track'`으로
   끝났다(exit 1). 예외 없이 깔끔하게 멈추고 자격 증명도 안 새므로 **방어는 제대로 돈다** —
   다만 플레이어 입장에서는 친 문장이 아무 결과 없이 사라진다. 재시도나 안내 경로가 없다.
   Phase 10(AI 출력 검증) 논의에 올릴 것.

2. **실패한 제공자 호출도 `ai_invoked`로 기록되고, 토큰이 0이라 정상 응답과 구분되지 않는다.**
   존재하지 않는 모델 호출이 `prompt_tokens=0, completion_tokens=0, latency_ms=175`로 남았다.
   집계에서는 「AI를 한 번 불렀다」로 세어지고 토큰만 0이다. **이것은 Phase 14 성공 조건 5
   (「토큰 집계가 조용히 0으로 떨어지면 그것이 정상 응답과 구분된다」)가 가리키는 바로 그
   상황이다** — 이번에 실물 증거가 생겼으니 Phase 14에서 이 사례를 회귀 기준으로 쓸 수 있다.

3. **제공자 시간초과가 실제로 났고, 턴은 살아남았다.** `pacing5` 마지막 턴에서
   `경고: 제공자 호출이 2번 모두 실패했다 — Request timed out.`이 떴는데 턴은 exit 0으로
   끝나고 판정 등급(strong_hit)까지 나왔다. 성공 조건 4(「병렬 참조 수집 중 하나가 늦어도
   턴이 멈추지 않는다」)의 실사용 증거로 함께 남긴다.

## Evidence

- 사건 기록: `.gptrpg/uat9.db` — 세션 `pacing5`(항목 1) · `uatweb`(항목 2·3·4)
- 확인 일자: 2026-08-12
- 제공자: NIM (`action_classifier`/`scene_entity_judge`/`clock_judge` = meta/llama-3.1-8b-instruct,
  `master_gm`/`situation_judge` = nvidia/nemotron-3-ultra-550b-a55b)
- `.gptrpg/agents.json`은 확인 전 상태로 복원 완료 (`action_classifier`·`master_gm` 두 항목만 명시,
  나머지 셋은 D-05 물려받기)

# 제약 (Constraints)

**출처 문서 2건 (SPEC 분류) — 둘은 같은 계열의 v2와 v1이다**

| 문서 | 상태 |
|---|---|
| `docs/GPTRPG-design-plan.md` (기획 명세서 v2) | **유효** |
| `docs/GPTRPG-design-plan-v1-archive.md` (코어 엔진 기획 명세서) | **폐기 — v2로 대체됨** |

두 문서는 같은 SPEC 등급이므로 **기본 우선순위로는 서로를 이길 수 없다.** 둘을 가르는 것은 우선순위가 아니라 **대체(supersession)**이며, 근거는 문서 자체에 있다 — v2 헤더가 v1-archive를 `이전 버전`으로 지목하고(`docs/GPTRPG-design-plan.md:4`), v2 부록 A가 v1에서 뒤집힌 항목 18건을 열거한다(`docs/GPTRPG-design-plan.md:1034-1057`). 더 중요하게, 뒤집힌 항목 하나하나를 **잠금된 ADR**(`docs/GPTRPG-M0-decisions.md`)이 독립적으로 재확인하므로, v1의 폐기 항목들은 `ADR > SPEC` 규칙으로도 동일하게 해소된다.

> ⚠️ **v1-archive 문서 본문에는 superseded/status 표기가 없다.** 대체 사실은 전적으로 외부(후속 문서)의 진술에 의존한다. `INGEST-CONFLICTS.md`의 WARNING 참조.

아래에서 v1 유래 항목은 제목에 `[폐기]` 또는 `[미결]`을 붙이고 `content` 첫 줄에 처리 근거를 남겼다. **`[폐기]` 표시 항목을 살아 있는 제약으로 읽으면 안 된다.**

---

# A. 유효한 제약 — 기획 명세서 v2

## 4계층 아키텍처와 불변 규칙 3개

- source: docs/GPTRPG-design-plan.md §3.1
- type: protocol
- content: 전송 어댑터(게임 로직 0줄, 교체 가능) → 세션 액터(세션당 1개, 유일한 직렬화 지점, 명령 수신 → 검증 → 이벤트 발행, 진행 정책 주입) → 규칙 코어(순수 함수, I/O 없음, 시간 개념 없음 — 판정 방식·효과 표현·주사위 엔진) → 이벤트 로그(append-only) + 파생 상태 스냅샷. 불변 규칙 — ① 규칙 코어는 시간을 모른다(타이머·접속 상태 개념 금지) ② 세션 액터가 유일한 쓰기 주체다 ③ 모드는 코드 경로가 아니라 진행 정책 설정값이다(새 모드 추가 = 표에 열 하나 추가, `if` 분기 추가가 아니다).

## 이벤트 소싱 — 되돌릴 수 없는 결정

- source: docs/GPTRPG-design-plan.md §3.2
- type: protocol
- content: 모든 사건을 순서대로 기록하고 현재 상태는 그 기록을 훑어서 만든다. CRUD 제자리 변경으로 먼저 짜면 재접속 동기화·리플레이·비동기 참여·관전자 합류·다시보기가 전부 나중에 불가능해진다. 부수 효과로 계측이 공짜다 — 모든 판정·시계 진행·GM 대응 선택이 로그에 남는다. M0에서 할 일은 **이벤트 스키마에 필드를 빠뜨리지 않는 것**뿐이다.

## 진행 정책 (PacingPolicy) 프리셋 표

- source: docs/GPTRPG-design-plan.md §3.3
- type: schema
- content: 열 = 스트리머 / 일반 파티 / 솔로 / 비동기. 턴 타이머 45~60초 / 180초 / 없음 / 없음. 순서 강제 ON / ON / 해당없음 / OFF. 리액션 윈도우 5초 / 15초 / 인라인 / 알림·무기한. 접속 전제 전원 / 전원 / 1인 / 없음. (ADR 원본 `docs/GPTRPG-M0-decisions.md` §2 D3에는 「미접속자」 행이 추가로 있다 — 자동 스킵 / 자동 스킵 / 없음 / 대기.)

## 에이전트 4개 구성

- source: docs/GPTRPG-design-plan.md §3.4
- type: schema
- content: `action_classifier`(경량) 자유 텍스트 → 무브 + 능력치 분류 + 신뢰도 / `master_gm`(M0은 최상급) GM 대응 선택 + 서사 생성 / `onboarding_agent`(중형) 캐릭터 만들기 안내 / `context_summarizer`(경량) 배경 압축 + 리캡 생성. 메시지 버스는 인프로세스 함수 호출로 충분하다(세션 액터가 유일한 직렬화 지점). 턴당 LLM 호출 평균 1.5회.

## 통신 — 문장 청크 전송과 재접속 동기화

- source: docs/GPTRPG-design-plan.md §3.6
- type: protocol
- content: 문장 청크 전송(토큰 단위 스트리밍 폐기, v1 판단 유지). 각 패킷에 순번 부여, 재접속 시 누락분 델타 재전송.

## 응답 속도 목표와 초과 시 행동

- source: docs/GPTRPG-design-plan.md §3.6 (권위: docs/GPTRPG-M0-decisions.md §2 D33)
- type: nfr
- content: 문장 입력 → 행동 확인 표시 0.5초 / 확인 → GM 서사 첫 글자 2초 / 완결까지 목표 없음. 첫 글자 5초 초과 시 진행 표시. 15초 타임아웃 시 판정 결과(주사위·성공/실패·시계 변화)를 먼저 내보내고 서사를 뒤이어 붙인다. 주사위와 판정은 순수 코드라 서사보다 먼저 끝나 있다.

## 개인 정보 분리 — 가시성 필드

- source: docs/GPTRPG-design-plan.md §3.7
- type: schema
- content: `master_gm` 출력에 가시성 필드를 둔다 — `{ "visibility": "public" }` / `{ "visibility": "private", "to": ["player_3"] }`. 이벤트 소싱과 궁합이 좋으며 M4에서 시야 계산이 들어와도 같은 메커니즘을 재사용한다.

## 기억 주입 규칙 — 매 턴 네 가지

- source: docs/GPTRPG-design-plan.md §3.8 (권위: docs/GPTRPG-M0-decisions.md §2 D31)
- type: protocol
- content: 매 턴 넣는 것 = 현재 장면에 등장한 대상 / 내 캐릭터 상태 / 위협 시계 상태 / 최근 대화 몇 턴(초기값 10턴, 실측으로 조정). 나머지 저장소는 이름 + 한 줄 색인만. AI가 저장소 전체를 훑는 경로는 만들지 않는다. 턴당 토큰 예산 상한을 안전장치로 두되 저장소 색인·위협 시계 상태·관계 장부는 접지 않는다. 룰북과 캐릭터 시트는 프롬프트 앞쪽에 고정해 캐시가 붙고 장면 정보만 뒤쪽에서 바뀐다.

## 룰북 3부 구조

- source: docs/GPTRPG-design-plan.md §4.1
- type: schema
- content: ① 원문(자연어, 사람이 쓰고 읽는 것, 게임 중에도 살아 있음 — 재량 판정이 읽는다) ② 구조화 데이터(판정 방식 / 만들기 단계 / 라이프사이클 유형 / 효과) ③ 연결(①의 어느 문단이 ②의 어느 항목인가 → 판정 근거 표시에 사용). 원문을 버리지 않는다.

## 룰북 파일 목차

- source: docs/GPTRPG-design-plan.md §4.2 (권위: docs/GPTRPG-M0-decisions.md §2 D27)
- type: schema
- content: 룰북 = 메타(이름·설명·버전·저작자·라이선스 / 판정 방식 지정 / 자동화율) · 원문(자연어 그대로, 절 단위) · 캐릭터 정의(능력치 목록 / 파생값 계산식 / 캐릭터 종류 / 만들기 단계) · 판정 정의(판정 종류 목록 / 결과 등급 집합 / 수정치 규칙) · 효과 목록(주문·특성·아이템) · 라이프사이클(성장 / 회복 / 장비 / 죽음 / 화폐 유형) · 적·위협 정의 · 원문↔구조 연결표. **M0에서 확정하는 것은 목차까지이며 필드 단위 상세 규격은 M1이다.**

## 판정 인터페이스 계약

- source: docs/GPTRPG-design-plan.md §4.4
- type: api-contract
- content: 판정 요청 `{ 판정 종류 / 기준값 / 난이도(선택) / 수정치 목록(유형별) }` → 판정 방식 코드(순수 함수, 룰북 데이터를 읽어 계산) → 판정 결과 `{ 굴림 원본 / 최종값 / 등급 / 그 등급의 효과 }`. **결과 등급을 코드에 고정하지 않는다** — 2d6식은 3개, d100식은 최대 6개이며 룰북이 자기 등급 집합을 선언한다. 다이스풀 방식은 등급이 수치(성공 개수)이므로 목록과 수치 구간을 모두 받아야 한다. 수정치 유형 목록 = 숫자 가감 / 주사위 추가·제거 / 목표값 변경 / 재굴림(푸시 롤 — 숫자 수정치만 지원하면 표현 불가).

## 효과 표현 — 원자 연산

- source: docs/GPTRPG-design-plan.md §4.5
- type: schema
- content: 주문·특성·아이템의 효과를 조합 가능한 원자 연산으로 표현한다. 30~50개 규모 목표 — 피해를 준다 / 상태를 부여한다 / 저항 판정을 요구한다 / 판정을 수정한다 / 이동시킨다 / 자원을 쓴다·회복한다 / 발동 조건을 심는다 / 선택을 요구한다 / 집중을 요구한다. **원자 연산 최종 목록 확정은 M1이다.**

## 적과 NPC의 상태값 그릇

- source: docs/GPTRPG-design-plan.md §4.9 (권위: docs/GPTRPG-M0-decisions.md §2 D32)
- type: schema
- content: 플랫폼이 정하는 것 = 식별자 / 표시 이름 / 상태값 묶음(키-값 그릇) / 소속 룰북 / 가시성. 룰북 데이터가 선언하는 것 = 상태값 묶음의 항목 / 각 값의 뜻 / 특정 값이 바닥나면 무슨 일이 일어나는지. 상태 변경은 효과 표현을 통해서만. 저장은 캐릭터와 같은 그릇을 재사용하고 유형으로만 구분한다. **플랫폼 코드에 체력·피해·태그처럼 룰북 고유의 개념을 넣지 않는다.** 상태값 묶음의 구체 형태는 M1 미결.

## 위협 시계 데이터 구조

- source: docs/GPTRPG-design-plan.md §5.1 (권위: docs/GPTRPG-M0-decisions.md §2 D21)
- type: schema
- content: 위협 시계 = 이름/한 줄 요약 · 분량(칸 수) · 톤 태그(진지/코믹/호러) · 위협의 정체 · 그것이 원하는 것(한 문장) · 등장인물[](엔티티 장부와 연결) · 시계 칸[순서 있음]{순번 / 무슨 일이 일어나나(한 문장) / 상태: 대기|진행됨|무효화됨 / 진행 조건 / 진행 후 세상에 남는 흔적} · 파국 · 시작 칸. 규격 = 시계 하나 4~6칸 / 8~15시간, 무료 제공 1~2칸.

## 위협 시계 진행 규칙

- source: docs/GPTRPG-design-plan.md §5.2
- type: protocol
- content: 세 가지를 함께 쓴다 — ① 실패 누적 카운터(판정 실패 시 +1, 기본 3회 도달 시 강제 1칸 진행 후 초기화) ② 조건 트리거(시간 경과·장소·선행 칸 진행 여부) ③ AI 선택(GM 대응 목록에서 "시계 진행"). ③만 있으면 봐주기가 생기고 ①만 있으면 기계적이 된다. ①이 관측 지표를 공짜로 만든다.

## 캐릭터 만들기 7가지 동작

- source: docs/GPTRPG-design-plan.md §6.1
- type: schema
- content: ① 목록에서 하나 고르기 ② 목록에서 여러 개 고르기 ③ 숫자를 나눠 담기 ④ 정해진 숫자를 자리에 배치 ⑤ 주사위 굴려 채우기 ⑥ 자유롭게 쓰기 ⑦ 자동 계산. 룰북 데이터가 "만들기 단계 목록"을 갖고 시스템이 순서대로 실행한다. 화면 부품도 7개면 모든 룰북에 재사용된다.

## 캐릭터 라이프사이클 유형 목록

- source: docs/GPTRPG-design-plan.md §6.3
- type: schema
- content: 성장 = 경험치 누적(획득 조건은 룰북이 별도 정의) / 사용 기반 개선 / 점수 지급 / 성장 없음. 회복 = 휴식 기반 / 시간 경과 기반 / 치료 판정 기반 / 안전지대 기반 / 거의 회복 안 됨. 장비 = 개별 품목 + 무게·슬롯 제한(1순위 구현) / 추상 회분 / 하중 등급만 / 관리 없음. 죽음 = 즉사 / 빈사→안정화 판정 / 협상 / 부상 누적 / 캐릭터 교체 전제. 화폐도 동일 패턴. 각 영역의 유형은 코드로 구현하고 어느 유형인지는 룰북이 선언한다.

## 안전 장치 4개 층

- source: docs/GPTRPG-design-plan.md §7.6 (권위: docs/GPTRPG-M0-decisions.md §2 D23)
- type: protocol
- content: 1층 방 생성 시 톤·선·장막 설정(선 = 아예 안 나옴 / 장막 = 나오지만 묘사 안 함). 2층 정지 카드 — 익명·설명 요구 없음·즉시 작동의 세 원칙이 절대적이며 강도 2단계(`[이 장면을 돌려주세요]` / `[이 주제를 빼주세요]`). 3층 AI가 넘지 않게 하는 3겹 — 방의 선·장막 목록을 GM 프롬프트에 상시 포함 / GM 출력을 내보내기 전 검사 / 장막은 삭제하지 않고 전환. 4층(M2) 신고·방장 강퇴·차단. **안전 장치 작동 사실을 언급하지 말 것을 AI에 명시 지시한다.** 1~3층은 M1, 4층은 M2.

## 저작 흐름과 안전한 기본값

- source: docs/GPTRPG-design-plan.md §8.1 · §8.3
- type: protocol
- content: 유저가 룰북을 쓴다(또는 파일 업로드) → AI가 구조화 초안 생성 → 유저 확인(성패가 갈리는 지점) → 확인된 부분만 자동 처리, 나머지는 원문 + 재량 판정. **확인할 때 구조화 데이터를 보여주지 않고 시험 판정 결과를 보여준다.** 안전한 기본값 = 확실한 것만 구조화하고 애매한 것은 원문 + 재량 판정으로 남긴다 — 자동화율이 낮게 시작하는 것이 잘못 구조화하는 것보다 안전하다.

## 유저 업로드 공개 범위 3단

- source: docs/GPTRPG-design-plan.md §10.3 (권위: docs/GPTRPG-M0-decisions.md §2 D29)
- type: protocol
- content: 비공개(본인만) 관대 / 초대한 친구만 관대·기록 보존 / 공개 마켓 엄격 — 라이선스 선언 + SRD 원문 유사도 검사 + 등록 검수 + 신고·삭제 절차. 배포와 사적 이용은 법적 취급이 다르며 이 선을 시스템으로 그으면 리스크가 세 번째 칸에 모인다.

## M0 최소 도구 범위

- source: docs/GPTRPG-design-plan.md §12.3 (권위: docs/GPTRPG-M0-decisions.md §2 D30)
- type: nfr
- content: 필요 = 텍스트 입력창 / 행동 분류 + 확인(최소 형태) / 주사위(코드) / GM 서사 생성 / 위협 시계 상태 + 실패 카운터 / 캐릭터 시트(읽기만) / 이벤트 기록 저장 / 여러 명이 같은 세션을 보는 것. 안 필요 = 캐릭터 만들기 화면(손으로 준비) / 매칭·로비(링크 하나) / 코스메틱 / 룰북 저작 도구(데이터를 손으로) / 리캡 자동 생성(손으로 써서 보여줘도 검증됨) / 안전 장치 UI(실험에서는 구두 대체) / 결제·계정. **제품이 아니라 실험 도구다.**

---

# B. 폐기된 제약 — v1 아카이브

> 아래 항목은 **살아 있는 제약이 아니다.** 각 항목의 `content` 첫 줄에 무엇이 대체했는지 적었다.

## [폐기] RulebookAdapter 인터페이스 (룰북별 전용 어댑터)

- source: docs/GPTRPG-design-plan-v1-archive.md §2.1
- type: api-contract
- content: **[폐기 — D5 / v2 §2.3으로 대체]** 원문: 각 룰북이 `system_id`, `action_type_enum`, `build_parser_prompt`, `validate_action`, `resolve_check`, `execute_combat_action`, `get_available_reactions`, `calculate_dc`를 구현한 전용 어댑터를 제공하고 백엔드는 이 인터페이스를 통해서만 룰북 로직과 통신한다. **폐기 사유:** UGC 룰북 공유가 제품에 포함되므로 유저가 룰북을 올릴 때마다 코드를 짤 수 없다. 대체안 = 판정 방식은 코드, 룰북은 데이터. 특히 `calculate_dc()`는 지적 C1(하드코딩 불가)의 대상이었고 D4의 PbtA 전환으로 DC 개념 자체가 사라졌다.

## [폐기] SceneContext / ParsedAction 계약

- source: docs/GPTRPG-design-plan-v1-archive.md §2.1
- type: api-contract
- content: **[폐기 — D5·D16으로 대체]** 원문: `SceneContext`가 entities(ac/hp_current/distance_feet 등), actor(action_used·bonus_action_used·reaction_used·movement_used_feet·spell_slots·ability_scores·proficiency_bonus·equipped_weapon), lighting, terrain_difficulty, combat_state, initiative_order를 주입하고 파서가 `ParsedAction`(action_type, confidence, target, requested_skill, spell_id, advantage_sources, ambiguities, fallback_action)을 반환한다. **폐기 사유:** 5e 고유 개념(액션 이코노미·주문 슬롯·AC·사거리)을 계약에 박은 형태이며 지적 C2의 대상. D32가 금지하는 "플랫폼 코드에 룰북 고유 개념을 넣는" 실수의 원형이다.

## [폐기] 신뢰도 0.9 임계값 기반 폴백

- source: docs/GPTRPG-design-plan-v1-archive.md §1 원칙 6 · §2.3 · §2.6.5
- type: protocol
- content: **[폐기 — D16으로 대체]** 원문: 파싱 신뢰도가 임계값(기본 0.9) 미만이면 구조화 액션 선택 UI로 강제 전환하고, `combat_parser` confidence < 0.7이면 오케스트레이터가 구조화 UI를 강제 오픈한다. **폐기 사유:** 모든 분류가 어차피 플레이어 확인을 거치므로 임계값과 폴백 UI가 불필요해진다. 신뢰도는 UI 강도로만 쓴다. 지적 W9(LLM self-confidence 과신 편향) 해소.

## [폐기] 하이브리드 전투 엔진 — 15×15 그리드·A*·Fog of War

- source: docs/GPTRPG-design-plan-v1-archive.md §2.3 · 핸드오프 §3.1~3.2
- type: protocol
- content: **[M4로 연기 — 폐기가 아니라 이동. D13⑥ · D17 · D32]** 원문: 전투 진입 시 최대 15×15 전술 그리드를 팝업하고 탐험 모드의 논리 좌표계를 그대로 계승하며, 이동 반경(A*)·사거리·AoE·엄폐물·시야(Bresenham 레이캐스팅)를 100% 백엔드가 연산하고 시야 밖 엔티티는 클라이언트에 로드조차 하지 않는다(Server-Authoritative Fog of War). **처리:** 첫 타깃이 던전월드(좌표계 없음)로 바뀌었으므로 M0~M3에는 보드가 없다. 좌표계·전술 그리드·시야 계산은 M4(D&D 5e 어댑터)로 유지된다. v2 부록 A는 "서버 권위 시야 계산(M4에서 활용)"을 v1의 유지된 좋은 판단으로 분류한다.

## [폐기] 스포트라이트 토큰 · 리액션 큐 · 우선순위 정렬

- source: docs/GPTRPG-design-plan-v1-archive.md §2.5 · 핸드오프 §5.1
- type: protocol
- content: **[폐기 — D10으로 대체]** 원문: 비전투 상황에서 첫 입력자가 스포트라이트 토큰을 획득해 타 유저 입력창이 락되고, 대기자는 리액션 예약 버튼으로 비동기 큐에 적재하며 백엔드가 하드코딩된 우선순위 테이블(INTERRUPT_DEFENSIVE > REACTION > FREE_ACTION > ACTION > BONUS_ACTION)로 결정론적 정렬한다. 동시 상반 선언 시 이니셔티브 순서로 선후를 강제한다. **폐기 사유:** 조율은 외부 메신저에서 끝나며(D10), 선착순 락은 말 많은 사람이 독식한다(W4). 비전투에는 이니셔티브가 존재하지도 않는다(W3). 던전월드에는 이니셔티브가 없다(D4).

## [폐기] 3초 리액션 팝업 (타임아웃 인터셉트)

- source: docs/GPTRPG-design-plan-v1-archive.md §2.3 · 핸드오프 §3.3
- type: protocol
- content: **[완화 — D10으로 대체]** 원문: 기회 공격 조건 발생 시 백엔드가 패킷 송신을 일시 정지하고 해당 유저에게 3초 타이머 선택 UI를 띄운다. **처리 사유:** 지적 W2(UX 재앙). 타이머 없는 리액션 대기로 완화하고 짧은 타이머는 스트리머 프리셋에만 남긴다.

## [폐기] AFK 타임아웃 인젝터 데몬 (이원화)

- source: docs/GPTRPG-design-plan-v1-archive.md §2.5 · 핸드오프 §5.2
- type: protocol
- content: **[대폭 축소 — D10·D24로 대체]** 원문: `combat_state`에 따라 이원화하여 전투 모드 90초(숙련)/180초(초보), 만료 시 `idle_timeout` 패킷 인젝션 → 무반응 처리 → 다음 턴 강제 진행. 탐험 모드는 기본 무제한(소프트 5분), 5분 경과 시 스포트라이트 자동 반납. **처리 사유:** "자리 비움" 표시 + 수동 넘기기로 축소. D24가 세 경우(잠깐 자리 비움 / 오늘 중도 이탈 / 영구 이탈)를 다르게 처리하도록 분해했고, 시스템이 자동 축출하지 않고 방장이 판단한다.

## [폐기] 서브에이전트 레지스트리 10개

- source: docs/GPTRPG-design-plan-v1-archive.md §2.6.1
- type: schema
- content: **[폐기 — D17로 대체(10개 → 4개)]** 원문: `master_gm`, `combat_parser`, `exploration_parser`, `onboarding_agent`, `rules_interpreter`, `context_summarizer`, `entity_ledger_keeper`, `reaction_classifier`, `dice_narrator`, `initiative_resolver`. **폐기 사유:** 지적 W11(과잉) — `initiative_resolver`·`reaction_classifier`는 에이전트가 아니라 함수이며, 3개는 병합·강등된다. 남는 4개는 `constraints.md` A절 「에이전트 4개 구성」 참조.

## [폐기] 에이전트 간 통신 — gRPC + Redis Streams

- source: docs/GPTRPG-design-plan-v1-archive.md §2.6.3
- type: protocol
- content: **[폐기 — D17로 대체]** 원문: 메시지 버스는 내부 gRPC 스트리밍(동기) + Redis Streams(비동기/백그라운드) 이중 구성. **폐기 사유:** M0에 과하다. Session Actor 하나가 유일한 직렬화 지점이므로 인프로세스 함수 호출로 충분하며, 분산이 필요해지면 Actor를 프로세스 밖으로 빼면 되고 구조는 바뀌지 않는다.

## [폐기] 상태 관리 및 격리 계층 표

- source: docs/GPTRPG-design-plan-v1-archive.md §2.6.4
- type: schema
- content: **[폐기 — D3(이벤트 소싱)으로 대체]** 원문: 세션 레벨은 PostgreSQL + JSONB(캠페인 영구), 씬 레벨은 Redis(TTL 24h — 전투 그리드·엔티티 위치·이니셔티브), 턴 레벨은 In-Memory, 온보딩 레벨은 Redis(TTL 1h), 엔티티 장부는 PostgreSQL 별도 테이블(영구). **폐기 사유:** 가변 상태를 제자리에서 관리하는 모델이다. D3은 append-only 이벤트 로그를 진실의 원천으로 두고 상태를 파생 스냅샷으로 만들며, "CRUD 제자리 변경으로 먼저 짜면 안 된다"를 M0의 되돌릴 수 없는 결정으로 못박았다. 다만 하위 항목 중 **자주 조회되는 필드의 컬럼 분리**는 v2 부록 A가 유지된 좋은 판단으로 분류한다.

## [폐기] 토큰 예산 관리 — 세션당 128k, Master GM 40k

- source: docs/GPTRPG-design-plan-v1-archive.md §2.6.6
- type: nfr
- content: **[폐기 — D31 / 원가 문서 §1로 대체]** 원문: 세션당 총 예산 128k 토큰, Master GM 프롬프트 40k(시스템 프롬프트 + 룰북 요약 + 엔티티 장부 + 최근 20턴), 사용률 80% 초과 시 압축 트리거, 95% 초과 시 비상 압축(최신 20턴만 보존). **폐기 사유:** D2가 "세션당 토큰 예산" 서술 자체를 재작성 대상으로 지목했고, D31이 주입 규칙을 장면 단위로 바꿔 주입량이 세션 길이와 거의 무관해졌다. 원가 문서는 턴당 프롬프트를 약 14,500으로 재산정한다("원 기획안의 Master GM 40k보다 훨씬 작다").

## [폐기] 엔티티 장부 상시 주입

- source: docs/GPTRPG-design-plan-v1-archive.md 핸드오프 §4.1
- type: protocol
- content: **[폐기 — D31로 대체]** 원문: 이벤트가 압축되더라도 파생된 고유 NPC(이름·외모 특징·호감도), 핵심 단서, 획득 고유 아이템의 상태 값은 영구 보존 풀에 격리 저장되어 **LLM 프롬프트에 상시 주입**되도록 설계한다. **폐기 사유:** 지적 W6(장부 무한 성장 + 상시 주입 모순). 세션 길이에 비례해 주입량이 늘어나는 구조는 원가와 캐싱을 동시에 깨뜨린다. 대체안 = 장면 단위 주입 + 이름·한 줄 색인 + 요청 기반 조회.

## [폐기] 인터랙티브 온보딩 — 아키타입 → 13클래스 드롭다운

- source: docs/GPTRPG-design-plan-v1-archive.md §2.4 · 핸드오프 §5.3
- type: protocol
- content: **[폐기 — D22로 대체]** 원문: 백스토리 자유 입력 → 키워드 추출 → 추천 초안 → 아키타입 선택(전사형/마법형/기술형/치유형) → 세부 직업 드롭다운(D&D 5e 13개 클래스) → 능력치 생성 방식 선택(4d6k3 6회 롤링 / 27포인트 슬라이더 / 고정 배열 [15,14,13,12,10,8] 드래그) → 종족·배경·특성 드롭다운 → 최종 검토 → 확정 버튼. **폐기 사유:** 지적 W1 — 온보딩이 진입장벽을 오히려 올렸다("예쁜 캐릭터 시트 마법사"). 개수가 아니라 이해할 수 없는 선택이 문제였다. 대체안 = 7가지 동작 + 이야기 질문으로 감싸기 + 숫자를 서술로 번역. **단, 「추천만 하고 자동 확정 금지」와 「전 단계 되돌리기 상시 제공」은 v2 부록 A가 유지된 좋은 판단으로 분류한다.**

## [폐기] 스타터 룰북 3종 라인업 (크로니클 d20 메인)

- source: docs/GPTRPG-design-plan-v1-archive.md §3.1
- type: schema
- content: **[폐기 — D4·D6으로 대체]** 원문: ① 크로니클 d20(D&D 5e SRD 5.1 기반) = 오픈 베타 메인 타이틀, 선정 이유는 "가장 복잡한 5e를 첫 프로토타입 타겟으로 삼아 하이브리드 엔진의 완결성을 검증" ② 월드 앤 어드벤처(던전월드 CC BY 3.0) ③ 미지의 그림자(자체 d100). **폐기 사유:** D4가 "가장 복잡한 것으로 엔진 완결성 검증" 논리를 폐기하고 첫 타깃을 던전월드 계열로 바꿨으며 D&D 5e를 M4로 이동시켰다. M0 판정 방식은 2d6 등급식 + d100 롤언더 2종이다.

## [폐기] 프로토타입 검증 기준 13케이스

- source: docs/GPTRPG-design-plan-v1-archive.md §6
- type: nfr
- content: **[폐기 — D30 / v2 §12로 대체]** 원문: D&D 5e SRD 단독 프로토타입에서 13개 E2E 케이스(근접 공격+이동, 보너스 액션, 주문 업캐스트, 리액션 기회 공격, 어드밴티지/디스어드밴티지, 스킬 체크, 동시 상반 행동, AFK 타임아웃, 스포트라이트, 캐릭터 생성 플로우, 파서 정확도 벤치마크 500샘플 confidence ≥ 0.9 비율 ≥ 95%·오분류 ≤ 1%, 오케스트레이션 지연 탐험 E2E ≤ 2초·전투 ≤ 3초, 에이전트 장애 격리)가 수동 개입 없이 자동 통과해야 한다. **폐기 사유:** 지적 V1 — 13개 케이스가 전부 "파서가 맞게 파싱했나"이고 "3시간 하면 재미있나"를 재는 지표가 0개였다. 지적 V2 — 가설을 죽일 조건이 없었다. 대체안 = 가설 6개 + 킬 크리테리아(`requirements.md`). 파서 목표도 정확도에서 마찰로 교체되었다(D28).

## [폐기] E2E 3초 / 오케스트레이션 지연 목표

- source: docs/GPTRPG-design-plan-v1-archive.md §6
- type: nfr
- content: **[폐기 — D33으로 대체]** 원문: 탐험 턴 E2E ≤ 2초, 전투 턴 E2E ≤ 3초(P99, 네트워크 제외). **폐기 사유:** 지적 W8(레이턴시 목표 자기모순 — E2E 3초 vs Heavy 타임아웃 15초). 완결 기준이었고 달성 불가능하다(무거운 모델 첫 토큰 1~2초, 완결 5~10초). 대체안 = 두 구간 목표(0.5초 / 2초) + 초과 시 행동.

## [미결] 에이전트 응답 래퍼 · 타임아웃 · 재시도 정책

- source: docs/GPTRPG-design-plan-v1-archive.md §2.6.3
- type: api-contract
- content: **[대체·폐기 진술 없음 — 사용자 판단 필요. `INGEST-CONFLICTS.md` WARNING 참조]** 원문: 모든 에이전트 응답은 `AgentResult<T>` 래퍼(success, data, error_code ∈ {LOW_CONFIDENCE, VALIDATION_FAILED, TIMEOUT, MODEL_ERROR}, error_message, latency_ms, token_usage, fallback_suggestion)로 통일한다. 타임아웃 정책 = 동기 호출 2초(Light) / 5초(Medium) / 15초(Heavy), 초과 시 폴백 동작 트리거. 재시도 정책 = `MODEL_ERROR` 시 지수 백오프 최대 2회, `VALIDATION_FAILED`는 재시도 안 함. **상태:** D33이 15초 타임아웃과 그때의 화면 동작을 확정했으므로 Heavy 값은 정합하나, `AgentResult` 래퍼와 Light/Medium 타임아웃·재시도 정책은 어느 후속 문서도 유지·폐기를 진술하지 않았다. `error_code`의 `LOW_CONFIDENCE`는 D16의 임계값 폐기로 근거를 잃었다.

## [미결] WebSocket 하트비트 및 재연결 세부

- source: docs/GPTRPG-design-plan-v1-archive.md 핸드오프 §2.1
- type: protocol
- content: **[상위 원칙만 승계, 세부는 진술 없음 — 사용자 판단 필요]** 원문: 각 패킷에 시퀀스 번호(`seq`) 부여, 클라이언트는 `last_acked_seq` 유지, 재연결 시 누락 패킷 델타 재전송, 하트비트 5초 간격 + 3회 실패 시 재연결, GM 스트리밍 중 재연결 시 마지막 완료 청크부터 재생성(멱등성 보장). **상태:** v2 §3.6이 "각 패킷에 순번 부여, 재접속 시 누락분 델타 재전송"으로 원칙은 승계했으나 하트비트 주기·실패 횟수·멱등성 재생성 규칙은 v2에 없다. 폐기 진술도 없다.

## [유지] v1에서 그대로 살아남은 판단

- source: docs/GPTRPG-design-plan.md 부록 A (v1 원문: docs/GPTRPG-design-plan-v1-archive.md §2.2 · 핸드오프 §2.1~2.2 · §4.1~4.2)
- type: protocol
- content: **[유지 — v2 부록 A가 명시적으로 "v1에서 그대로 유지된 좋은 판단"으로 열거]** LLM은 파서일 뿐 저지가 아니다(원칙 1) / 상태 트랜잭션 Pending & Commit 분리 / 주사위 결과 확정 후 서사 생성(사전 분기 스케치 폐기) / 문장 청크 전송(토큰 단위 스트리밍 폐기) / 서버 권위 시야 계산(M4에서 활용) / 이벤트 기반 압축 트리거(턴 카운트 폐기) / 엔티티 장부 분리 / 캐릭터 만들기의 명시적 확정 + 되돌리기 / AI 추천, 자동 확정 금지 / 자주 조회되는 필드를 별도 컬럼으로 분리 / 전체 원본 로그 보존 + 캠페인 기념품 컴파일.

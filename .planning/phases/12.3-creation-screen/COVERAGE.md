# Phase 12.3 — Coverage Declarations

**Written:** 2026-08-20 (planning)
**Phase:** 12.3-creation-screen

이 문서는 자동 탐지기가 「신호 없음」을 돌려준 항목들을 **사람이 읽어 판단한 결과**로 대체해 적는다.
탐지기의 `detected: false`는 「없다」가 아니라 「영어 방아쇠 어휘를 못 찾았다」다 — 이 저장소의
로드맵·논의 문서가 전부 한국어라 그 값은 아무것도 증명하지 않는다.

## API coverage

No external API integration: 이 단계는 이 저장소가 이미 가진 자체 HTTP 경로와 화면을 잇는다 (외부 API 연동 없음).

**근거 (읽고 확인한 것):**
- 이 단계가 부르는 HTTP 경로는 전부 `src/gptrpg/web/routes_creation.py`·`routes_events.py`가 이
  저장소 안에서 정의한 것이다. 새로 붙는 것은 `GET /creation/steps`(12.3-02)와
  `POST /creation/host`(12.3-03) 둘이고 둘 다 같은 FastAPI 앱 안에 산다.
- LLM 제공자 호출(`creation_gm` 역할)은 **이미 통합된 경로**다 — Phase 9가 세운 에이전트 구조와
  `_resolve_creation_gm_provider`를 그대로 쓰고, 이 단계는 새 제공자·새 모델·새 호출 규약을
  하나도 도입하지 않는다. 오히려 중복 호출을 **줄인다**(D-12).
- 새 npm/pip/cargo 패키지가 없다. 따라서 `## Package Legitimacy Audit`가 필요한 설치 작업도 없다.

## Schema push detection

**해당 없음.** 탐지기가 덮는 것은 Payload·Prisma·Drizzle·Supabase·TypeORM이다.
`package.json`과 `pyproject.toml`을 직접 확인했고 다섯 중 어느 것도 없다. 이 프로젝트는
Python + React이고 저장 계층이 **덧붙이기만 하는 사건 기록(sqlite3 + 직접 작성한 `EventStore`)**
이라 마이그레이션 명령을 미는 ORM 자체가 없다. 대신 이 저장소가 쓰는 것은 `EVENT_SCHEMA_VERSION`
올림 규약이고, 이 단계는 그것을 10에서 11로 올린다 — 그 위험은 `[BLOCKING]` 푸시 작업이 아니라
12.3-01 Task 0의 `checkpoint:decision`과 Task 1의 「다섯 자리를 한 커밋에」 승인 기준으로 막는다.

## Spec-less probe fallback — 이번 실행의 명시적 건너뜀

**탐침에서 나온 술어가 이번 실행에는 없다.** 이유 둘:
- 이 단계에는 아직 요구사항 번호가 없었다(`ROADMAP.md`의 `**Requirements**: TBD`). 탐침이
  물어볼 대상이 존재하지 않았다. 이 계획 묶음이 `CHAR-06`을 **만든다**(12.3-05 Task 3).
- `SPEC.md`가 없어서 `## Edge Coverage`·`## Prohibitions`에서 들어 올릴 절도 없었다.
  `UI-SPEC.md`도 없다 — UI 안전 관문은 이 단계에서 **의도적으로 건너뛴 것**이고
  (배치·색·간격은 Phase 16), 그것을 보상하려고 시각 설계 계약을 대신 쓰지 않았다.

따라서 `must_haves`는 `12.3-CONTEXT.md`의 잠긴 결정 D-01~D-15와 ROADMAP의 단계 목표에서
직접 도출했다.

## Assumption delta — 「방장(host)」

D-11이 이 저장소에 없던 개념을 하나 만든다. 이것이 단수→복수 신원 전환인지 판단한 결과를 적는다.

<assumption_delta_decision>
**판정: add-alongside (기존 신원 축은 그대로 두고 새 축을 나란히 더한다).**

근거: 지금 이 저장소의 신원은 두 축이다 — `browser_id`(어느 브라우저인가, Phase 8 서명 쿠키)와
`character_id`(어느 캐릭터인가). 「방장」은 그 둘을 대체하지 않고, **세션 하나에 대해 브라우저
하나를 가리키는 역할(role)** 을 하나 더 얹는다. 기존 코드에서 「사용자 하나」를 전제하던 자리가
「여럿」으로 바뀌는 종류의 전환이 아니다 — 이 제품은 처음부터 한 세션에 네 브라우저를 전제했고
(D-38 폴링, `PARTY_MEMBER_LIMIT`), 바뀌는 것은 「그 넷 중 하나가 인원을 정한다」는 새 규칙뿐이다.

그래서 `browser_id`를 「방장 여부를 담는 값」으로 승격(promote)하지 않는다. 대신 `GameState`에
`creation_host_browser_id` 칸을 따로 두고, 그 값의 공개 범위를 좁힌다(부른 사람에게 `you_are_host`
불리언만 답한다 — T-12.3-05).

**이 정의가 임시라는 것을 함께 적는다:** 「방을 만든 사람이 방장」이 사장님의 뜻이고, 방을 만드는
화면이 생기면(다음 마일스톤) D-11의 정의를 「링크를 만든 사람」으로 바꾼다. 지금의 「가장 먼저
들어온 사람」은 그 화면이 없어서 쓰는 대체안이고 사장님이 합의한 것이다.
</assumption_delta_decision>

## CLI 대응 — 명시적 예외

이 저장소에는 「웹과 CLI를 같은 커밋에서 닫는다」는 관례가 있고, 이 단계는 그 관례의 **명시적
예외**다. 조용히 한쪽만 고치는 것이 이 저장소의 알려진 실패 모양이므로 이유를 남긴다.

- 명령줄에는 **캐릭터 선택·신원 개념이 아예 없다** — `src/gptrpg/cli/turn_flow.py:257-258`이
  `person_id=args.player`·`character_id=args.player`를 전제하고 그 사실을 주석으로 적어 두었다.
- 이 단계가 더하는 것 셋(동의·방장·GM 지목)이 **전부 그 두 개념 위에 선다.**
- Phase 12.1이 이미 같은 예외 판단을 했고, 그 판단과 근거(신원 개념을 먼저 만들어야 하며 그것은
  계정이 생기는 다음 마일스톤 범위)가 같은 파일의 같은 자리에 이미 적혀 있다.
- **따라서 이 단계는 그 주석을 갱신하기만 한다**(12.3-05 Task 3) — 12.3이 무엇을 더했고 왜
  여전히 명령줄에 없는지를 한 문단 덧붙인다. 새 CLI 하위명령을 만들지 않는다.

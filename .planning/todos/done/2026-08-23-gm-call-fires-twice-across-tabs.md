---
created: 2026-08-23
title: 겹친 요청이 AI를 두 번 부른다 — 사전 검사를 큐 안으로 옮긴다
area: web/routes_creation, session_actor/actor
severity: major
files:
  - src/gptrpg/web/routes_creation.py:787 (announce)
  - src/gptrpg/web/routes_creation.py:860 (nominate)
  - src/gptrpg/web/routes_creation.py:993 (follow_up)
  - src/gptrpg/web/routes_creation.py:1129 (wrap_up)
  - src/gptrpg/session_actor/actor.py:_prepare_gm_spoke
---

## Problem

**어디서 나왔나:** 2026-08-22 Phase 12.3 코드 리뷰 WR-02
(`.planning/phases/12.3-creation-screen/12.3-REVIEW.md`). 사장님이
2026-08-23에 (a)안 — "지금은 두고 근본 수정을 별도로 뺀다" — 를 골랐다.

만들기 화면의 GM 호출 네 곳(안내·지목·되묻기·정리)은 AI를 부르기 **전에**
"이미 같은 말을 했는가"를 먼저 본다. 그런데 그 조회는 액터 큐 **밖**의
평범한 속성 읽기라, 두 요청이 겹치면 둘 다 그 조회를 통과해 둘 다 AI를
부른다. 큐 **안**의 재검사(`AlreadyGmSpoken`)가 두 번째를 잡아 주므로
**게임 사건은 하나만 남는다** — 새는 것은 AI 제공자 호출 비용과 지연뿐이다.

이건 원래부터 있던 한계고, `_prepare_gm_spoke`의 도크스트링이 스스로
그렇게 적어 두고 있었다. 새로 문제가 된 이유는 Phase 12.3-14가 첫 안내를
**자동 발동**으로 바꿨기 때문이다 — 전에는 누군가 단추를 눌러야 했으니
겹침이 드물었는데, 이제 **열려 있는 모든 탭이 인원 확정 직후 동시에**
같은 호출을 낸다. 참가자 넷이면 네 번이 기본값이 된다.

## Solution

**큐 밖 사전 검사를 큐 안 검사로 대체하거나, 세션당 뮤텍스로 좁힌다.**
네 경로가 전부 같은 모양이라 한 자리를 고치면 넷 다 닫힌다 — 개별 라우트에
가드를 하나씩 다는 방식은 쓰지 않는다.

**하지 않기로 한 것 (사장님 결정, 2026-08-23):**
프런트엔드 완화책 — `shouldAnnounce`에 "방장 탭만 부른다"를 더하는 것 —
은 채택하지 않는다. 「여러 탭이 부른다」를 「방장이 탭을 닫으면 아무도
안 부른다」로 바꾸는 거래이고, 방장이 나갔을 때 서버가 대신 진행할 방법이
아직 없다.

**설계 잠금과의 관계:** D-12(AI는 같은 자리에서 한 번만 불린다)가 이
요구의 근거다. 지금 코드는 D-12의 **결과**(사건 하나)는 지키지만 **문언**
(호출 한 번)은 못 지키고 있다.

## Evidence

- `.planning/phases/12.3-creation-screen/12.3-REVIEW.md` WR-02
- `.planning/phases/12.3-creation-screen/12.3-REVIEW-FIX.md` — WR-02를 왜
  자동 수정하지 않고 남겼는지, 두 선택지의 대가가 각각 무엇인지
- `src/gptrpg/session_actor/actor.py:_prepare_gm_spoke` 도크스트링 —
  이 한계를 코드가 스스로 문서화해 둔 자리
- 자동 발동으로 바꾼 계획: `.planning/phases/12.3-creation-screen/12.3-14-PLAN.md`

## Closed by

**13-02-PLAN.md Task 1 (2026-08-26).** 13-01이 오프닝 라우트를 위해 세운
큐 안 `ClaimGmSlot`/`ReleaseGmSlot` 슬롯 메커니즘을 이 문서가 지목한
네 자리(announce/nominate/follow_up/wrap_up) 전부로 넓혔다 — 라우트마다
가드를 따로 다는 대신 같은 자리(`web/routes_creation.py`)를 네 번 반복해
같은 모양으로 고쳤다(요구사항이 명시한 "한 자리를 고치면 넷 다 닫힌다"의
실제 실행 단위).

큐 **밖** 사전 검사(`_gm_dedupe_key` 조회)는 지우지 않고 그대로 남겼다 —
그것이 「이미 말했으면 제공자 설정 없이도 지난 말을 본다」는 별개의 캐시
성질을 지키는 자리였기 때문이다. `ClaimGmSlot`은 그 캐시 조회 **뒤**,
제공자 해석·AI 호출 **앞**에 들어가 겹친 요청 중 하나만 AI를 부르게
막는다 — 슬롯을 못 딴 쪽은 409를 받고 AI를 아예 안 부른다. 큐 안
`AlreadyGmSpoken`(「이미 끝남」 방어선)은 그대로 남아 슬롯이 풀린 뒤 늦게
도착한 요청을 잡는다 — 두 방어선이 서로 다른 갈래(「동시」 대 「이미
끝남」)를 막으므로 둘 다 필요했다.

`tests/test_gm_slot.py`가 **AI 제공자 호출 횟수**를 세는 회귀 시험으로
고정했다(사건 개수가 아니다 — 이 결함은 정확히 「사건은 하나인데 호출은
둘」이었으므로 사건 개수만 세는 시험은 이 결함을 못 잡는다). 슬롯을
넣기 전 코드로 네 갈래(안내·지목·되묻기·정리) 모두가 「제공자 호출
2회」로 실패하는 것을 먼저 확인했고, 슬롯을 넣은 뒤 전부 「1회」로
바뀌었다. 프런트엔드 쪽 "겹친 탭에 409가 오류로 안 보이게" 처리는
13-02 Task 2 몫이다.

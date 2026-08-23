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

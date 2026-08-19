---
created: 2026-08-16
title: 「캐릭터 변경하기」가 막다른 길이고, 실패 문구가 엉뚱한 것을 가리킨다
area: web/routes_characters, frontend/screens/CharacterSelect
severity: major
resolves_in: 12.1-06
files:
  - frontend/src/screens/CharacterSelect.tsx:88-97
  - frontend/src/labels.ts:105
  - src/gptrpg/web/routes_characters.py:209 (select_character)
---

## Problem

**어디서 나왔나:** 2026-08-16, 계획 11-03 체크포인트에서 사장님이 화면을 직접 확인하다
발견. Phase 11이 만든 것이 아니다 — `CharacterSelect.tsx`는 저장소 초기 커밋(`7821dc0`)
이후 한 번도 수정되지 않았다. **원래 있던 결함이다.**

### 결함 A — 화면이 서버가 못 들어주는 동작을 권한다

서버는 한 브라우저가 캐릭터를 하나만 점유하도록 의도적으로 설계돼 있고(D-05), **점유를
놓는 경로가 없다.** 그런데 화면에는 「캐릭터 변경하기」가 있어서 선택 화면으로 데려간다.
거기서 다른 캐릭터를 고르면 서버가 거절한다.

재현 (확인 완료):
```
POST /api/sessions/{sid}/select-character {"character_id":"bram"}          → 200
POST /api/sessions/{sid}/select-character {"character_id":"demo-showcase"} → 409
   {"detail":"이 브라우저는 이미 다른 캐릭터를 점유하고 있다"}
GET  /api/sessions/{sid}/characters                                        → 200 (목록은 멀쩡)
```

### 결함 B — 오류 문구가 거짓말을 한다

`CharacterSelect.tsx:88-97`:
```ts
async function choose(characterId: string): Promise<void> {
  setPending(characterId);
  try {
    await selectCharacter(sessionId, characterId);
    onSelected(characterId);
  } catch {
    setPending(null);
    setFailed(true);        // ← 목록 실패 플래그
  }
}
```
`failed`는 `characterListError`("캐릭터 목록을 불러오지 못했어요. 새로고침해 주세요")를
띄운다. **선택이 실패했는데 목록이 실패했다고 말한다.** 목록 fetch는 성공했고 새로고침해도
같은 일이 반복된다 — 사장님이 실제로 이 안내를 따르고도 원인을 짐작할 수 없었다.

**Why:** 사람이 화면만 보고 무슨 일이 일어났는지 알 수 없으면, 그건 안내가 아니라 방해다.
게다가 시키는 대로(새로고침) 해도 안 풀린다.

## Fix

두 결함은 독립적이므로 따로 고칠 수 있다.

**B (작음, 먼저):** `choose()`의 실패를 목록 실패와 분리한다. 별도 상태(`selectError`)와
문구를 두고, 409의 `detail`을 그대로 보여준다 — 서버가 이미 사람이 읽을 한국어로 이유를
말하고 있다("이미 다른 분이 고른 캐릭터예요" / "이 브라우저는 이미 다른 캐릭터를
점유하고 있다"). 이 둘은 사람이 취할 행동이 서로 다르므로 구분해서 보여야 한다.

**A (설계 판단 필요):** 셋 중 하나다.
1. 점유를 놓는 경로를 만든다 (`release-character`) — 「변경하기」가 실제로 동작하게 된다
2. 이미 점유 중이면 「변경하기」 버튼을 숨기거나 비활성화한다 — 못 하는 일을 권하지 않는다
3. 선택 화면에서 이미 점유된 카드를 비활성 상태로 그린다 — 누르기 전에 알 수 있다

2와 3은 화면만 고치면 되고, 1은 D-05 점유 규칙의 의도를 다시 봐야 한다(재접속한 본인은
통과시키는 규칙과 「놓기」가 어떻게 어울리는지).

## Workaround (지금 당장)

세션 id를 새로 만들면 점유가 비어 있으므로 원하는 캐릭터를 바로 고를 수 있다:
`?session=<새이름>`. 브라우저 쿠키도 세션별이라 신원이 새로 발급된다.

## Resolved (2026-08-19, 계획 12.1-06)

**결함 A는 2번 선택지로 닫았다.** 이미 점유 중인 사람에게는 「캐릭터 변경하기」 버튼을
아예 렌더하지 않는다(`StatusPane.tsx`). 버튼이 사라진 자리에는 `characterIdentityLimit`
문구를 넣어 「왜 없어졌는지」가 같이 보이게 했다 — 그냥 없어지면 「고장났다」로 읽히기
때문이다.

**1번 선택지(점유를 놓는 경로를 만든다)는 채택하지 않았다.** D-08이 「중간에 캐릭터를
바꿀 수 없다」를 명시적으로 확정했고, `release-character` 같은 경로를 만드는 것은 그
결정과 정면으로 어긋난다. 이번 계획은 그런 경로를 프런트·백 어디에도 추가하지 않았다
(회귀 시험이 `release-character`/`releaseCharacter`/`unoccupy` 문자열 0줄을 확인한다).

**3번 선택지(선택 화면에서 이미 점유된 카드를 비활성으로 그린다)는 일부러 하지 않았다.**
2번이 이미 「누를 수 없는 동작을 권하지 않는다」는 목표를 채우고, 카드 상태를 다르게
그리는 것은 화면 생김새(배치·색·컴포넌트 구조) 영역이라 Phase 16(FE-*)의 몫과 겹친다.
이번 계획은 화면 생김새를 바꾸지 않기로 스스로 범위를 그었다(계획 원문의 명시적 금지
사항).

**결함 B(선택 실패인데 「목록을 불러오지 못했어요」라고 말한다)도 같이 닫았다.**
`CharacterSelect.tsx`의 실패 상태를 목록 조회 실패(`failed`)와 선택 실패
(`selectError`)로 나누고, 서버가 409로 이미 사람이 읽을 한국어로 준 이유(「이미 다른
분이 고른 캐릭터예요」 등)를 그대로 보여준다. 「새로고침해 주세요」는 선택 실패 문구에서
뺐다 — 새로고침해도 안 풀리는 상태에서 그 안내를 하는 것이 결함 B의 해악이었다.

**부수적으로 D-08의 알려진 한계(쿠키를 잃거나 다른 기기로 오면 캐릭터로 못 돌아온다)를
사람이 읽을 자리에 적었다** — 감추지 말라는 D-08의 명시적 지시. 사람 확인 중 문구가
추상적이었던 곳(무엇을 하면 마커가 사라지는지)을 구체적으로 고쳤다(커밋 `f16de59`).

전체 verification 완료: `.planning/phases/12.1-character-creation/12.1-06-SUMMARY.md`.

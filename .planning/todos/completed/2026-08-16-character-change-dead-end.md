---
created: 2026-08-16
title: 「캐릭터 변경하기」가 막다른 길이고, 실패 문구가 엉뚱한 것을 가리킨다
area: web/routes_characters, frontend/screens/CharacterSelect
severity: major
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

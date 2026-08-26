/** 화면 동작을 가르는 값 몇 개 — 코드 여기저기서 찾지 않게 한 자리에 모은다. */

/**
 * 그림이 **없는** 턴 카드에 빈 이미지 자리를 보여줄지.
 *
 * 실제 그림은 이제 연결되어 있다 — `scene_illustrated` 사건이
 * `groupTurns`에서 `turn.illustration`이 되고 `StoryPane`이 그것을
 * `TurnCard`의 `imageUrl`로 넘긴다. 이 값은 그 그림이 **없을 때**의 처리만
 * 가른다.
 *
 * 기본값이 `false`인 이유: 그림 기능은 기본적으로 꺼져 있고
 * (`GPTRPG_IMAGERY`), 꺼진 채로 빈 상자를 매 카드마다 띄우면 화면이
 * 미완성으로 보인다. 켜고 돌리는 동안에도 삽화는 서사보다 2~4초 늦게
 * 도착하므로, `true`로 두면 그 사이 빈 상자가 잠깐 보이고 그림으로 채워진다 —
 * 그림이 오고 있다는 신호가 필요하면 켠다.
 */
export const SHOW_IMAGE_PLACEHOLDER = false;

/** 서버 `MAX_RAW_TEXT_LEN`(routes_actions.py)과 같은 값. */
export const MAX_RAW_TEXT_LEN = 2000;

/** 서버 `MAX_ID_LEN`(routes_actions.py)과 같은 값 — `browserIdentity.ts`가
 * 만드는 `browser_id`/`character_id`가 이 길이를 넘지 않는다. */
export const MAX_ID_LEN = 64;

/** 방장 재실 신호 주기(Phase 12.3-05, D-11). 서버 `HOST_IDLE_S`
 * (`web/creation_state.py`, 2026-08-26 verify-13-06 결함3 재현 뒤
 * 240초로 올랐다 — 배경 탭 스로틀링만으로도 이 신호가 몇 분씩 늦게
 * 도착할 수 있다는 실측 때문이다)보다 훨씬 짧게 유지한다. 신호 주기
 * 자체을 함께 올리지 않는 이유: 자주 보내는 것 자체는 비용이 낮고,
 * 문턱(HOST_IDLE_S)만 넉넉하면 신호가 몇 번 늦게 도착해도(스로틀링)
 * 유휴로 오판되지 않는다 — 두 값을 같은 비율로 묶어 둘 필요가 없다. */
export const HOST_BEACON_MS = 15000;

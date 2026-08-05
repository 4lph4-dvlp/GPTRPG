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

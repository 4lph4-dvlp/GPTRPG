/**
 * 세션 화면이 쓰는 오프닝 자동 발동 판단(SCENE-01, D-01/D-02) — 화면
 * 판단을 여기 모은다(`creationView.ts`의 `shouldAnnounce`와 같은
 * 자리·같은 모양).
 *
 * 이 저장소는 RTL을 안 쓰고 순수 함수만 시험하므로, 이 부트스트랩 판단을
 * 컴포넌트 안에 두면 시험이 그 조건을 볼 수 없다(`shouldAnnounce`의
 * docstring이 이미 세운 규율) — 조건이 틀려도(한 번도 안 불리거나·명단
 * 잠금 전에도 불리거나·실패 뒤 무한히 불려도) 화면 구조 검사는 전부
 * 통과한다. 12.3에서 여섯 라운드를 살아남은 결함이 정확히 그 모양이었다.
 */

import type { GameStateView } from "../api/types.ts";

/**
 * 지금 오프닝을 부를 때인가(SCENE-01, D-01/D-02) — 네 갈래:
 *
 * - 폴링 상태가 아직 `null`이면 → 거짓. `null`을 「부를 때다」로 바꿔
 *   읽지 않는다(`isMyTurn`이 세운 같은 규율).
 * - 명단이 아직 안 잠겼으면(`party_roster === null`) → 거짓(D-01) —
 *   「첫 사람이 완성한 순간」이 아니다.
 * - 오프닝이 이미 있으면(`scene_opened_seq !== null`) → 거짓 — 서버가
 *   막긴 하지만(D-02/D-03) 화면이 매 폴링마다 헛요청을 내지 않는다.
 * - 직전 시도가 실패했으면 → 거짓. 자동 재시도 고리를 만들지 않는다 —
 *   실패는 사람에게 말하고 멈춘다(재시도 단추가 유일한 복구 경로다).
 *
 * 넷을 전부 통과하면 참이다.
 */
export function shouldOpenScene(
  state: GameStateView | null,
  lastAttemptFailed: boolean,
): boolean {
  if (state === null) {
    return false;
  }
  if (state.party_roster === null) {
    return false;
  }
  if (state.scene_opened_seq !== null) {
    return false;
  }
  if (lastAttemptFailed) {
    return false;
  }
  return true;
}

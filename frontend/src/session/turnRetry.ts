/**
 * 서사 실패한 턴의 재시도 요청을 조립한다(verify-13-06 결함1).
 *
 * **문제였던 것:** 서사만 실패한 턴(`narration_failed`)에서 사람이
 * 「다시 시도해 주세요」를 보고 입력칸에 같은 문장을 다시 쳐 보내면,
 * 그것은 재시도가 아니라 **새 선언**(`declareAction`)이었다 — 새
 * `declare_seq`로 분류·확인·판정이 처음부터 다시 돌아 주사위를 다시
 * 굴렸다. 실패한 첫 판정의 실패 카운터는 그대로 남은 채, 재시도로
 * 다른 등급이 나오는 두 번째 판정이 하나 더 쌓였다 — 한 선언에 판정이
 * 둘 남는 결함.
 *
 * **서버는 이미 이 문제를 풀어 뒀다(D-09).** `POST .../actions/confirm`은
 * 같은 `declare_seq`로 같은 move/stat을 다시 보내면 `AlreadyConfirmed`로
 * 캐시된 확인·판정을 재사용하고 서사만 다시 쓴다
 * (`tests/test_web_actions.py::test_narration_retry_reuses_roll_and_only_narration_appended_grows`
 * 가 이미 이 경로를 고정한다). **화면이 이 경로를 부를 방법이 없었을
 * 뿐이다** — 실패 뒤 `proposal`(후보 목록)을 지워 버려서, 사람이
 * 남긴 재시도 수단은 "새로 쓰기"뿐이었다.
 *
 * 이 함수는 실패한 `Turn`(서버가 사건 기록에서 다시 접은 그대로 —
 * 브라우저 로컬 상태가 아니다) 하나에서 confirm()/proceed() 재호출에
 * 필요한 값을 그대로 뽑아낸다. `turn.confirmed`가 있으면(판정 경로)
 * 그 사건에 이미 적힌 move/stat/system_suggestion/player_confirmed를
 * 그대로 되돌려 보낸다 — **서버가 다시 굴리지 않고 재사용할 수 있는
 * 유일한 조건이 "완전히 같은 move/stat"이므로**, 이 함수가 조립하는
 * 값은 절대 새로 고르지 않는다. `turn.confirmed`가 없으면(D-10 ②갈래,
 * `proceed()` 경로 — 애초에 판정이 없다) `declareSeq`만으로 충분하다.
 */

import type { ActionConfirmedEvent, MoveCandidate } from "../api/types.ts";
import type { Turn } from "./groupTurns.ts";

export type RetryRequest =
  | {
      kind: "confirm";
      declareSeq: number;
      chosen: MoveCandidate;
      suggestion: MoveCandidate;
      confirmed: boolean;
    }
  | { kind: "proceed"; declareSeq: number };

function suggestionFrom(confirmed: ActionConfirmedEvent): MoveCandidate {
  // system_suggestion은 서버가 `{"move": ..., "stat": ...}` 두 칸으로만
  // 채운다(`routes_actions.py`의 `ConfirmAction` 조립 자리) — 그 두 값이
  // 없으면 확인 자체가 성립하지 않았을 것이므로, 없을 때는 실제 확정값
  // (move/stat)으로 대신한다(안전한 대체값이지 정상 경로가 아니다).
  return {
    move: confirmed.system_suggestion["move"] ?? confirmed.move,
    stat: confirmed.system_suggestion["stat"] ?? confirmed.stat,
  };
}

/** 실패한 턴 하나에서 재시도 요청을 조립한다 — 새 값을 하나도 안
 * 고른다, 사건에 이미 적힌 값만 그대로 되돌린다. */
export function buildRetryRequest(turn: Turn): RetryRequest {
  if (turn.confirmed !== null) {
    return {
      kind: "confirm",
      declareSeq: turn.declareSeq,
      chosen: { move: turn.confirmed.move, stat: turn.confirmed.stat },
      suggestion: suggestionFrom(turn.confirmed),
      confirmed: turn.confirmed.player_confirmed,
    };
  }
  return { kind: "proceed", declareSeq: turn.declareSeq };
}

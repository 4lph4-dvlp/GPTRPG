/**
 * 캐릭터 만들기 화면이 쓰는 순수 함수 둘 — 화면 판단을 전부 여기 모은다
 * (RTL이 없는 이 저장소의 시험 방식, `groupTurns.ts`와 같은 자리).
 *
 * 진행 상태(지금 몇 단계인가·누가 아직 안 끝났는가)를 계산하는 코드는
 * 여기 두지 않는다(D-04) — 그 판단은 서버가 폴링 응답에 실어 내린다.
 * 이 파일은 「사건에서 GM의 말을 뽑는다」와 「오류를 문구로 바꾼다」
 * 딱 둘만 한다.
 */

import { ApiError } from "../api/client.ts";
import { COPY } from "../labels.ts";
import type { GameEvent } from "../api/types.ts";

/** `creation_gm_spoke` 사건 하나를 화면이 그리기 좋은 모양으로 옮긴 것. */
export interface CreationGmLine {
  seq: number;
  kind: string;
  say: string;
  targetCharacterId: string | null;
}

/**
 * `creation_gm_spoke` 사건만 골라 `seq` 오름차순으로 편다. 다른 종류
 * 사건은 무시하고, 같은 `seq`가 두 번 오면(겹쳐 도착한 폴링 응답)
 * 하나만 남긴다.
 */
export function gmLinesFrom(events: GameEvent[]): CreationGmLine[] {
  const bySeq = new Map<number, CreationGmLine>();
  for (const event of events) {
    if (event.event_type !== "creation_gm_spoke") {
      continue;
    }
    bySeq.set(event.seq, {
      seq: event.seq,
      kind: event.kind,
      say: event.say,
      targetCharacterId: event.target_character_id,
    });
  }
  return [...bySeq.values()].sort((a, b) => a.seq - b.seq);
}

/**
 * 만들기 조작 실패를 사람이 읽을 문구 하나로 바꾼다(D-13 ②/D-15).
 *
 * - 503(운영자 설정 문제)이면 고정 문구 `COPY.creationGmUnavailable` —
 *   기다려도 안 되는 상황이다.
 * - 그 밖의 `ApiError`에 서버가 이유(`detail`)를 실어 보냈으면 그
 *   문장을 **그대로** 보여준다 — 화면이 따로 옮겨 적지 않는다(D-15).
 * - 이유가 없거나 `ApiError`가 아니면 `COPY.creationFailed`로 떨어진다.
 */
export function creationErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 503) {
      return COPY.creationGmUnavailable;
    }
    if (error.detail !== undefined) {
      return error.detail;
    }
  }
  return COPY.creationFailed;
}

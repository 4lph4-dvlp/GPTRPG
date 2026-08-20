/**
 * 캐릭터 만들기 화면이 쓰는 순수 함수 모음 — 화면 판단을 전부 여기 모은다
 * (RTL이 없는 이 저장소의 시험 방식, `groupTurns.ts`와 같은 자리).
 *
 * **진행 상태(지금 몇 단계인가 · 누가 아직 안 끝났는가 · 지금 누구
 * 차례인가)를 계산하는 코드는 여기 두지 않는다(D-04).** 그 판단은 전부
 * 서버가 폴링 응답(`GameStateView`)에 실어 내린 값을 그대로 읽고 고르는
 * 것으로 끝난다 — Phase 12.2가 「화면이 스스로 검산해 서버와 다른 값을
 * 보여준」 사고를 고친 뒤로, 이 규율은 협상하지 않는다. 12.3-04(Task 1)가
 * 더한 다섯 함수(`isMyTurn`·`myStepValues`·`stepRows`·`canEdit`·
 * `nextUnfilledStep`)도 전부 이 규율 안에서 산다 — 서버가 내려준 값을
 * 읽고 고르기만 한다.
 */

import { ApiError } from "../api/client.ts";
import { COPY } from "../labels.ts";
import type {
  CreationStepValueView,
  CreationStepView,
  GameEvent,
  GameStateView,
} from "../api/types.ts";

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

/**
 * 「지금 이 캐릭터의 차례인가」 — 서버가 내려준 `creation_current_speaker_id`와
 * 비교하는 것 딱 하나다(D-04). `null`이면 「아직 지목이 없다」다 — 이
 * 함수가 그것을 「내 차례다」로 바꿔 읽지 않는다.
 */
export function isMyTurn(state: GameStateView, myCharacterId: string): boolean {
  return state.creation_current_speaker_id === myCharacterId;
}

/**
 * `state.creation_step_values`에서 이 캐릭터의 것만 골라 `step_id`로
 * 찾을 수 있는 지도로 만든다. **접기를 다시 하지 않는다** — 서버가 이미
 * 최신 값 하나만 내려주므로, 같은 `step_id`가 두 번 오는 것은 서버 버그다.
 */
export function myStepValues(
  state: GameStateView,
  myCharacterId: string,
): Map<string, CreationStepValueView> {
  const values = new Map<string, CreationStepValueView>();
  for (const value of state.creation_step_values) {
    if (value.character_id === myCharacterId) {
      values.set(value.step_id, value);
    }
  }
  return values;
}

/** `stepRows`가 만드는 줄 하나 — 룰북 선언 하나에 이 캐릭터의 진행 상태를
 * 붙인 것. `value`가 `null`이면 아직 안 채워진 것이다. */
export interface CreationStepRow {
  step: CreationStepView;
  filled: boolean;
  reopened: boolean;
  value: CreationStepValueView | null;
}

/**
 * `CreationStepView` 선언 순서를 그대로 유지하고 각 줄에 채워짐(`filled`) ·
 * 다시 열림(`reopened`) · 값(`value`)을 붙인다. **선언에 없는 값이
 * 상태에 있어도 줄을 만들지 않는다** — 룰북 선언이 순서의 유일한
 * 출처다(D-05).
 */
export function stepRows(
  steps: CreationStepView[],
  state: GameStateView,
  myCharacterId: string,
): CreationStepRow[] {
  const values = myStepValues(state, myCharacterId);
  const reopenedStepIds = new Set(
    state.creation_reopened_step_ids
      .filter((row) => row.character_id === myCharacterId)
      .map((row) => row.step_id),
  );
  return steps.map((step) => {
    const value = values.get(step.step_id) ?? null;
    return {
      step,
      filled: value !== null,
      reopened: reopenedStepIds.has(step.step_id),
      value,
    };
  });
}

/**
 * 내 차례일 때 **아무 줄이나** 고칠 수 있다 — 「마지막 것만 한 칸 뒤로」가
 * 아니다(D-09). `row` 자체는 가리지 않는다: 채워졌는지와 무관하게 내
 * 차례이기만 하면 참이다 — 어떤 줄에 실제로 「고치기」 버튼을 보여줄지는
 * 호출부(이미 채워진 줄만 고칠 대상이 된다)가 고른다.
 */
export function canEdit(_row: CreationStepRow, myTurn: boolean): boolean {
  return myTurn;
}

/** `required`이면서 아직 안 채워진 첫 줄 — 전부 채워졌으면 `null`이다. */
export function nextUnfilledStep(rows: CreationStepRow[]): CreationStepRow | null {
  return rows.find((row) => row.step.required && !row.filled) ?? null;
}

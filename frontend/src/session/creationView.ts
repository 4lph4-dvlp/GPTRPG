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
  CreationStepCompletedEvent,
  CreationStepValueView,
  CreationStepView,
  GameEvent,
  GameStateView,
  PartySizeRangeView,
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

/** `partySizeGate`가 돌려주는 네 갈래(D-11, 12.3-05 Task 1) — 「fix」는
 * 내가 방장이라 인원을 정하는 조작을 보일 차례, 「waiting_for_host」는
 * 방장이 이미 있고 내가 아닐 때, 「waiting_for_claim」은 아직 아무도 방장을
 * 안 잡았을 때, 「done」은 인원이 이미 확정돼 이 관문 자체가 더는 볼 일이
 * 없을 때다. */
export type PartySizeGate = "fix" | "waiting_for_host" | "waiting_for_claim" | "done";

/**
 * 인원 확정 관문의 네 갈래를 고른다(D-11) — `state.party_size_fixed`와
 * `state.creation_host_claimed`, 그리고 이 호출이 부른 사람의
 * `you_are_host`(폴링이 아니라 `POST /creation/host` 응답에서만 나온다,
 * 이 함수가 그 값을 스스로 추측하지 않는다)만 읽고 고른다.
 */
export function partySizeGate(state: GameStateView, youAreHost: boolean): PartySizeGate {
  if (state.party_size_fixed !== null) {
    return "done";
  }
  if (youAreHost) {
    return "fix";
  }
  return state.creation_host_claimed ? "waiting_for_host" : "waiting_for_claim";
}

/**
 * 「인원 `count`가 서버가 내려준 범위 밖인가」(G-12.3-2) — `validate_party_size`
 * (`rules_core/rulebook.py`)와 **정확히 같은 규칙**의 거울이다: 최소
 * 미만이면 참, 상한이 있는데 그보다 크면 참, 경계는 양쪽 포함.
 *
 * (가) 이 함수는 **서버 판정의 거울이지 대체물이 아니다** — 마지막 말은
 * 언제나 서버가 하고(D-15), 이 함수는 사람이 범위 밖 값을 애초에 못
 * 고르게 돕는 것뿐이다. (나) 그래서 룰북 숫자를 **하나도 안 갖는다** —
 * 범위를 인자로 받는다. 특정 룰북에 편향된 값이 이 파일에 들어오면
 * 안 된다. (다) 진행 상태를 계산하지 않는다(D-04 경계) — 서버가 내려준
 * 범위와 사람이 지금 고른 숫자만 본다.
 */
export function partySizeOutOfRange(count: number, range: PartySizeRangeView): boolean {
  if (count < range.min_player_characters) {
    return true;
  }
  if (range.max_player_characters !== null && count > range.max_player_characters) {
    return true;
  }
  return false;
}

/** `consentGate`가 돌려주는 네 갈래(D-03/D-11, 12.3-05 Task 2). 「not_ready」는
 * 아직 만드는 사람이 있거나 완성된 캐릭터가 하나도 없을 때, 「needs_wrap_up」은
 * 전원 완성됐지만 GM의 정리(`kind: "wrap_up"`)가 아직 기록에 없을 때,
 * 「open」은 정리가 끝나 동의 관문이 열렸을 때, 「locked」는 명단이 이미
 * 잠겼을 때다. */
export type ConsentGate = "not_ready" | "needs_wrap_up" | "open" | "locked";

/**
 * 동의 관문의 네 갈래를 고른다. `wrappedUp`은 「`kind: "wrap_up"`인
 * `creation_gm_spoke` 사건이 기록에 있는가」하나뿐이다(`gmLinesFrom(events)`
 * 에서 존재 여부만 확인한 값을 호출부가 넘긴다) — 진행 상태를 다시
 * 계산하지 않는다(D-04). 나머지 판단은 전부 `state`가 이미 갖고 있는
 * 값(누가 아직 안 끝났나·완성된 캐릭터가 있나·명단이 잠겼나)을 읽는
 * 것으로 끝난다.
 */
export function consentGate(state: GameStateView, wrappedUp: boolean): ConsentGate {
  if (state.party_roster !== null) {
    return "locked";
  }
  // G-12.3-22 — 누군가 「고칠 게 있어요」로 항목을 다시 열어 놓고 아직
  // 안 채웠으면 시작할 수 없다. 예전에는 이 값을 아무도 안 봐서
  // 「이대로 시작」이 그대로 눌렸고, 고치는 중이던 값 대신 **옛 값으로**
  // 판이 시작됐다.
  if (state.creation_reopened_step_ids.length > 0) {
    return "not_ready";
  }
  if (state.creation_characters.length === 0 || state.creation_unfinished_character_ids.length > 0) {
    return "not_ready";
  }
  // G-12.3-11 — `creation_unfinished_character_ids`는 **항목을 하나라도 낸
  // 사람**만 담는다(서버 `creation_state.unfinished_candidates`의 doc).
  // 들어와서 아직 아무것도 안 누른 참가자는 그 목록에 원리적으로 못
  // 들어가므로, 먼저 끝낸 한 사람에게 「이대로 시작」이 떠서 나머지가
  // 영구히 배제됐다(D-08은 잠금을 되돌리는 사건을 두지 않는다).
  // 방장이 정한 인원이 이 세션이 몇 명짜리인지 아는 유일한 닫힌 숫자다.
  // 서버도 같은 검사를 한다(`actor._party_size_shortfall`) — 여기서는
  // 「서버가 거절할 단추를 애초에 안 그린다」를 맡는다(D-15).
  if (
    state.party_size_fixed !== null &&
    state.creation_characters.length < state.party_size_fixed
  ) {
    return "not_ready";
  }
  return wrappedUp ? "open" : "needs_wrap_up";
}

/**
 * GM의 정리가 **지금 값 기준**인가(G-12.3-23).
 *
 * `wrap_up`은 캐릭터를 다시 만들어(`CreateCharacter` 재제출) 표시 이름과
 * 능력치를 그 시점의 항목 값으로 다시 조립한다. 그래서 누가 항목을
 * 고친 뒤에는 **정리를 다시 받아야** 고친 값이 캐릭터에 반영된다.
 *
 * 예전에는 화면이 「wrap_up 사건이 하나라도 있나」만 봤다. 고치기 전에
 * 받은 정리가 그대로 「정리됨」으로 세어져, 고친 뒤에도 동의 관문이
 * 곧바로 열리고 **옛 이름 그대로 판이 시작됐다** — 실제 시험에서
 * 곽철용을 김철용으로 고쳤는데 게임에는 곽철용으로 들어갔다.
 *
 * 서버는 이미 같은 규율을 갖고 있다: `wrap_up`의 중복방지 키가 항목
 * 값의 최대 순번을 담으므로, 값이 바뀌면 새 키가 되어 AI를 다시 부르고
 * 캐릭터를 다시 만든다. 화면이 그 사실을 안 보고 있었을 뿐이다.
 */
export function wrapUpIsCurrent(state: GameStateView, events: GameEvent[]): boolean {
  const latestWrapUpSeq = gmLinesFrom(events)
    .filter((line) => line.kind === "wrap_up")
    .reduce((newest, line) => Math.max(newest, line.seq), -1);
  if (latestWrapUpSeq < 0) {
    return false;
  }
  const latestStepSeq = state.creation_step_values.reduce(
    (newest, value) => Math.max(newest, value.seq),
    -1,
  );
  return latestWrapUpSeq > latestStepSeq;
}

/**
 * GM에게 다음 차례를 지목해 달라고 부를 때인가(12.3-06, D-06) — 이
 * 저장소는 RTL을 안 쓰고 순수 함수만 시험하므로(CR-01이 이번 결함으로
 * 확인시켜 준 것) 이 부트스트랩 판단을 컴포넌트 안에 두면 시험이 그
 * 조건을 볼 수 없다. **`creation_unfinished_character_ids`(이미 항목을
 * 낸 사람만 담는 목록)를 조건으로도 의존성으로도 쓰지 않는다** — 그게
 * 이전 결함의 정체였다: 아무도 아직 항목을 안 낸 부트스트랩 세션에서는
 * 그 목록이 영원히 비어 지목이 한 번도 안 불렸다. 이 함수는 대신
 * `creation_characters.length`(완성된 사람 수)와 `party_size_fixed`만
 * 비교한다 — 완성 안 된 사람이 남아 있다는 사실은 「후보가 이미 있다」가
 * 아니라 「아직 끝나지 않았다」로 충분하다.
 */
export function shouldNominateNext(state: GameStateView, announced: boolean): boolean {
  if (!announced) {
    return false;
  }
  if (state.party_roster !== null) {
    return false;
  }
  if (state.party_size_fixed === null) {
    return false;
  }
  if (state.creation_current_speaker_id !== null) {
    return false;
  }
  if (state.creation_characters.length >= state.party_size_fixed) {
    return false;
  }
  return true;
}

/**
 * 지금 첫 안내를 부를 때인가(G-12.3-5, D-06) — `shouldNominateNext`와
 * **같은 종류의 부트스트랩 판정**이고, 그 함수의 docstring이 이미 적은
 * 이유(이 저장소는 RTL을 안 쓰고 순수 함수만 시험하므로 이 부트스트랩
 * 판단을 컴포넌트 안에 두면 시험이 그 조건을 볼 수 없다) 때문에 여기
 * 있다 — 안내만 그 규율에서 빠져 있었다.
 *
 * 실패 뒤에는 거짓인 이유: 자동 재시도 고리를 만들지 않는다(D-13 ②) —
 * 503(운영자 설정 문제)은 기다려도 안 되는 상황이라, 자동 재시도는 원인을
 * 감추고 AI 호출만 폭주시킨다. 실패는 사람에게 말하고 멈춘다.
 *
 * 진행 상태를 다시 계산하지 않는다(D-04) — 서버가 내려준 값(`party_size_
 * fixed`·`party_roster`)을 읽고 고르기만 하고, `announced`·
 * `lastAttemptFailed`도 호출부가 이미 계산한 값을 그대로 받는다.
 */
export function shouldAnnounce(
  state: GameStateView,
  announced: boolean,
  lastAttemptFailed: boolean,
): boolean {
  if (state.party_size_fixed === null) {
    return false;
  }
  if (announced) {
    return false;
  }
  if (lastAttemptFailed) {
    return false;
  }
  if (state.party_roster !== null) {
    return false;
  }
  return true;
}

/**
 * `creationTurn`이 돌려주는 세 갈래(G-12.3-7) — 「아무 차례도 아님」·
 * 「내 차례」·「남의 차례(이름 또는 이름 없음)」.
 */
export type CreationTurn =
  | { kind: "none" }
  | { kind: "me" }
  | { kind: "other"; name: string | null };

/**
 * 지금 누구 차례인지(G-12.3-7) — 판단은 전부 서버가 내려준 값을 읽는
 * 것으로 끝난다(D-04). 다음이 누구일지 화면이 계산하지 않는다.
 *
 * 순서는 **정해진 규칙이 아니라 GM의 선택**이고(D-06, `nominate_speaker`),
 * 그 사실이 화면에 드러나야 사람이 「규칙이 있는데 내가 못 읽는 것인가」로
 * 헤매지 않는다 — `labels.ts::creationTurnLabel`이 「순서는 진행자가
 * 정해요」를 문구에 넣는 이유다.
 *
 * **이름이 없을 수 있는 것이 정상이다** — 서버가 이름을 주는 것은 완성된
 * 캐릭터뿐이고(`state.creation_characters`), 이름 항목이 마지막인
 * 룰북에서는 지목받은 사람의 이름이 대개 아직 없다. **없는 이름을
 * 지어내지 않는다** — 식별자(`pc-xxxxxxxx`)를 대신 보이지 않는다. 그
 * 사람이 이미 항목을 채웠으면(`provides_display_name` 항목의
 * `creation_step_values`) 완성 전이라도 그 이름을 쓴다.
 *
 * 「아무 차례도 아님」과 「남의 차례」를 가르는 것이 이번 gap의 절반이다
 * — 오늘은 지목 전에도 「다른 사람의 차례예요」가 떴다.
 */
export function creationTurn(
  state: GameStateView,
  myCharacterId: string,
  steps: CreationStepView[],
): CreationTurn {
  const speakerId = state.creation_current_speaker_id;
  if (speakerId === null) {
    return { kind: "none" };
  }
  if (speakerId === myCharacterId) {
    return { kind: "me" };
  }
  const finished = state.creation_characters.find((character) => character.character_id === speakerId);
  if (finished !== undefined) {
    return { kind: "other", name: finished.display_name };
  }
  const nameStepId = steps.find((step) => step.provides_display_name)?.step_id;
  const nameValue =
    nameStepId !== undefined
      ? state.creation_step_values.find(
          (value) => value.character_id === speakerId && value.step_id === nameStepId,
        )
      : undefined;
  return { kind: "other", name: nameValue?.text_value ?? null };
}

/** 아직 동의를 안 누른 캐릭터의 `display_name` 목록이다(D-03) —
 * `character_id`가 아니라 사람이 알아볼 이름을 돌려준다. 순서는
 * `state.creation_characters` 순서를 그대로 따른다. */
export function pendingConsenters(state: GameStateView): string[] {
  return state.creation_characters
    .filter((character) => !character.consented)
    .map((character) => character.display_name);
}

/** `creationRollsFrom`이 만드는 큐 항목 하나 — 주사위로 채운 만들기
 * 항목 하나와 그 항목의 표시 라벨. */
export interface CreationRollQueueItem {
  creationStep: CreationStepCompletedEvent;
  label: string;
}

/**
 * `creation_step_completed` 사건 중 **눈이 실제로 있는 것만** 골라 큐
 * 항목으로 편다(D-07) — 자유 서술·선택처럼 굴림이 없는 항목은 큐에
 * 넣지 않는다. `label`은 `stepsById`(`GET /creation/steps`로 받아 둔
 * 선언)에서 `step_id`로 찾고, 못 찾으면 `step_id`를 그대로 쓴다. 같은
 * `seq`가 두 번 와도(겹쳐 도착한 폴링 응답) 하나만 남는다 —
 * `gmLinesFrom`과 같은 규칙이다.
 */
/**
 * 「값 V를 지금 한 칸 더 쓸 수 있는가」의 순수 산수(G-12.3-6) — 선언된 값 목록과
 * 지금 배정 상태에서 값별 남은 개수를 낸다.
 *
 * (가) 근거는 **개수**이지 존재 여부가 아니다 — 값의 집합으로 다루면 같은 값이
 * 둘 이상인 풀을 표현할 수 없다(`PlaceFixedValuesControl`이 실제로 겪은 결함의
 * 정확한 모양). (나) 서로 다른 값의 중복 배정 방지는 사라지지 않는다 — **개수가
 * 1인 경우**로 여기에 포함된다. (다) 이것은 **진행 상태 계산이 아니다**(D-04
 * 경계) — 서버가 내려준 룰북 선언과 이 브라우저의 지금 배정만 보는 순수 산수이고,
 * 서버의 어떤 판단도 다시 계산하지 않는다. (라) **마지막 말은 여전히 서버가
 * 한다** — 배치 묶음이 룰북 선언과 다중집합으로 같은지는 `actor.py`가 검사한다
 * (T-12.1-04). 이 함수는 사람이 불가능한 배치를 고르지 못하게 돕는 것이고,
 * 규칙을 화면으로 옮기는 것이 아니다.
 */
export function remainingFixedValues(
  fixedValues: number[],
  assignment: Record<string, number | null>,
): Map<number, number> {
  const remaining = new Map<number, number>();
  for (const value of fixedValues) {
    remaining.set(value, (remaining.get(value) ?? 0) + 1);
  }
  for (const value of Object.values(assignment)) {
    if (value === null) {
      continue;
    }
    const count = remaining.get(value) ?? 0;
    if (count > 0) {
      remaining.set(value, count - 1);
    }
  }
  return remaining;
}

export function creationRollsFrom(
  events: GameEvent[],
  stepsById: Map<string, CreationStepView>,
): CreationRollQueueItem[] {
  const bySeq = new Map<number, CreationRollQueueItem>();
  for (const event of events) {
    if (event.event_type !== "creation_step_completed") {
      continue;
    }
    if (event.rolls === null || event.rolls.length === 0) {
      continue;
    }
    bySeq.set(event.seq, {
      creationStep: event,
      label: stepsById.get(event.step_id)?.label ?? event.step_id,
    });
  }
  return [...bySeq.values()].sort((a, b) => a.creationStep.seq - b.creationStep.seq);
}

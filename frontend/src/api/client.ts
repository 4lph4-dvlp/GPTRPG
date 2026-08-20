/**
 * HTTP 호출은 전부 여기를 지난다 — 경로 문자열이 화면 코드에 흩어지지 않게
 * 한 자리에 모은다.
 *
 * 상태 코드를 삼키지 않는다. 이전 화면은 `!response.ok`면 조용히 돌아가서,
 * 서버 설정이 없어 503이 뜨는 동안 「보내기를 눌러도 아무 일도 안 일어나는」
 * 상태가 됐다. `ApiError`가 코드를 들고 올라가고 화면이 그 코드에 맞는 문구를
 * 고른다.
 */

import type {
  AnnounceCreationResponse,
  CharacterSheet,
  CharacterSummary,
  ConfirmResourceChangeResponse,
  ConfirmResponse,
  CreationAxisValueRecord,
  CreationCompleteResponse,
  CreationFollowUpResponse,
  CreationStepView,
  DeclareResponse,
  MoveCandidate,
  MyCharacterResponse,
  NominateSpeakerResponse,
  PollResponse,
  ProceedResponse,
  SeqResponse,
  WrapUpCreationResponse,
} from "./types.ts";

export class ApiError extends Error {
  readonly status: number;
  /** 서버가 응답 본문에 담아 보낸 사람이 읽을 이유(`detail`) — 있을 때만
   * 채워진다. `announceCreation`의 409가 이 칸을 쓴다(D-15). */
  readonly detail: string | undefined;

  constructor(status: number, message: string, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function sessionBase(sessionId: string): string {
  return `/api/sessions/${encodeURIComponent(sessionId)}`;
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new ApiError(response.status, `GET ${url} → ${response.status}`);
  }
  return (await response.json()) as T;
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new ApiError(response.status, `POST ${url} → ${response.status}`);
  }
  return (await response.json()) as T;
}

/**
 * `postJson`과 달리 실패 응답 본문의 `detail`을 읽어 `ApiError.detail`에
 * 그대로 담는다(D-15) — 사람이 직접 눌러 400/403/409를 받을 수 있는 만들기
 * 경로 전부가 이 함수를 쓴다. 서버가 이미 사람이 읽을 한국어로 거절 사유를
 * 말하는데(`routes_creation.py`의 `detail`) 공용 `postJson`은 그 사유를
 * 버리고 `POST url → status` 같은 기술 문자열만 남긴다 — 그러면 사람 눈에는
 * 「보내기를 눌러도 아무 일도 안 일어나는」 상태로 보인다. 캐릭터 고르기
 * 화면(Phase 12.3 D-10으로 삭제)의 `selectCharacter`가 쓰던 것과 같은
 * 방식이고, `announceCreation`(12.3-01)도 이 함수로 옮겨 온다.
 */
async function postJsonWithDetail<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let detail: string | undefined;
    try {
      const errorBody = (await response.json()) as { detail?: unknown };
      detail =
        typeof errorBody.detail === "string" && errorBody.detail.length > 0
          ? errorBody.detail
          : undefined;
    } catch {
      detail = undefined;
    }
    throw new ApiError(response.status, `POST ${url} → ${response.status}`, detail);
  }
  return (await response.json()) as T;
}

export function fetchEvents(sessionId: string, fromSeq: number): Promise<PollResponse> {
  return getJson<PollResponse>(`${sessionBase(sessionId)}/events?from_seq=${fromSeq}`);
}

export function fetchCharacters(sessionId: string): Promise<CharacterSummary[]> {
  return getJson<CharacterSummary[]>(`${sessionBase(sessionId)}/characters`);
}

export function fetchCharacterSheet(
  sessionId: string,
  characterId: string,
): Promise<CharacterSheet> {
  return getJson<CharacterSheet>(
    `${sessionBase(sessionId)}/characters/${encodeURIComponent(characterId)}`,
  );
}

export function fetchMyCharacter(sessionId: string): Promise<MyCharacterResponse> {
  return getJson<MyCharacterResponse>(`${sessionBase(sessionId)}/my-character`);
}

/**
 * GM에게 만들기 안내를 부탁한다(D-02/D-12). 사람이 직접 눌러 409(명단이
 * 이미 잠겼다)를 받을 수 있는 경로이므로 `postJsonWithDetail`을 쓴다(D-15).
 */
export function announceCreation(
  sessionId: string,
  rulebookId: string,
): Promise<AnnounceCreationResponse> {
  return postJsonWithDetail<AnnounceCreationResponse>(
    `${sessionBase(sessionId)}/creation/announce`,
    { rulebook_id: rulebookId },
  );
}

/**
 * 룰북이 선언한 만들기 항목 목록을 가져온다(D-05) — 세션 중에 안 바뀌므로
 * 폴링에 싣지 않는다(D-04 경계). 사람이 직접 트리거하는 경로가 아니라
 * 화면이 시작할 때 한 번 부르는 순수 조회이므로 공용 `getJson`으로
 * 충분하다.
 */
export function fetchCreationSteps(
  sessionId: string,
  rulebookId: string,
): Promise<CreationStepView[]> {
  return getJson<CreationStepView[]>(
    `${sessionBase(sessionId)}/creation/steps?rulebook_id=${encodeURIComponent(rulebookId)}`,
  );
}

/** 방장이 이 세션의 인원을 확정한다(D-01). 재확정이 없으므로 사람이 직접
 * 눌러 409를 받을 수 있다(D-15) — `postJsonWithDetail`을 쓴다. */
export function fixPartySize(
  sessionId: string,
  playerCharacterCount: number,
  rulebookId: string,
): Promise<SeqResponse> {
  return postJsonWithDetail<SeqResponse>(`${sessionBase(sessionId)}/creation/party-size`, {
    player_character_count: playerCharacterCount,
    rulebook_id: rulebookId,
  });
}

export interface CompleteCreationStepBody {
  character_id: string;
  browser_id: string;
  step_id: string;
  rulebook_id: string;
  text_value?: string;
  picked?: string[];
  axis_values?: CreationAxisValueRecord[];
}

/** 만들기 항목 하나의 값을 확정한다(D-03/D-07) — 같은 항목을 다시 내면
 * 그것이 곧 고치기다(D-09). 사람이 직접 눌러 400/403/409를 받을 수 있다
 * (D-15) — `postJsonWithDetail`을 쓴다. */
export function completeCreationStep(
  sessionId: string,
  body: CompleteCreationStepBody,
): Promise<SeqResponse> {
  return postJsonWithDetail<SeqResponse>(`${sessionBase(sessionId)}/creation/step`, body);
}

export interface CompleteCreationBody {
  character_id: string;
  browser_id: string;
  rulebook_id: string;
  one_line_intro: string;
}

/** 확정된 항목 값으로 캐릭터를 완성하고 자동으로 점유한다(CHAR-05). 사람이
 * 직접 눌러 400/403/409를 받을 수 있다(D-15) — `postJsonWithDetail`을
 * 쓴다. */
export function completeCreation(
  sessionId: string,
  body: CompleteCreationBody,
): Promise<CreationCompleteResponse> {
  return postJsonWithDetail<CreationCompleteResponse>(
    `${sessionBase(sessionId)}/creation/complete`,
    body,
  );
}

export interface RecordInterjectionBody {
  speaker_character_id: string;
  browser_id: string;
  during_character_id: string;
  mentioned_character_ids: string[];
  text: string;
}

/** 남의 차례에 자유롭게 끼어드는 말을 사건으로 남긴다(D-09) — 어느
 * 캐릭터의 데이터도 바꾸지 않는다. 사람이 직접 눌러 403/409를 받을 수
 * 있다(D-15) — `postJsonWithDetail`을 쓴다. */
export function recordInterjection(
  sessionId: string,
  body: RecordInterjectionBody,
): Promise<SeqResponse> {
  return postJsonWithDetail<SeqResponse>(`${sessionBase(sessionId)}/creation/interject`, body);
}

/** GM이 아직 자기소개를 안 끝낸 사람 중 다음 차례를 지목한다(D-06,
 * D-02/D-12). 사람이 직접 눌러 409를 받을 수 있다(D-15) —
 * `postJsonWithDetail`을 쓴다. */
export function nominateCreationSpeaker(
  sessionId: string,
  rulebookId: string,
): Promise<NominateSpeakerResponse> {
  return postJsonWithDetail<NominateSpeakerResponse>(
    `${sessionBase(sessionId)}/creation/nominate`,
    { rulebook_id: rulebookId },
  );
}

/** GM이 방금 나온 이야기에 더 물을 것이 있는지 판단한다(D-05 위층,
 * D-02 ④). 사람이 직접 눌러 403/409를 받을 수 있다(D-15) —
 * `postJsonWithDetail`을 쓴다. */
export function creationFollowUp(
  sessionId: string,
  characterId: string,
  rulebookId: string,
): Promise<CreationFollowUpResponse> {
  return postJsonWithDetail<CreationFollowUpResponse>(
    `${sessionBase(sessionId)}/creation/follow-up`,
    { character_id: characterId, rulebook_id: rulebookId },
  );
}

/** 전원 완성 뒤 GM이 정리하고 캐릭터마다 한 줄 소개를 낸다(CHAR-03/D-10,
 * D-02/D-12). 사람이 직접 눌러 409를 받을 수 있다(D-15) —
 * `postJsonWithDetail`을 쓴다. */
export function wrapUpCreation(
  sessionId: string,
  rulebookId: string,
): Promise<WrapUpCreationResponse> {
  return postJsonWithDetail<WrapUpCreationResponse>(`${sessionBase(sessionId)}/creation/wrap-up`, {
    rulebook_id: rulebookId,
  });
}

export function declareAction(
  sessionId: string,
  playerId: string,
  characterId: string,
  rawText: string,
): Promise<DeclareResponse> {
  return postJson<DeclareResponse>(`${sessionBase(sessionId)}/actions/declare`, {
    player_id: playerId,
    character_id: characterId,
    raw_text: rawText,
  });
}

export function confirmAction(
  sessionId: string,
  playerId: string,
  characterId: string,
  declareSeq: number,
  chosen: MoveCandidate,
  suggestion: MoveCandidate,
  confirmed: boolean,
): Promise<ConfirmResponse> {
  return postJson<ConfirmResponse>(`${sessionBase(sessionId)}/actions/confirm`, {
    player_id: playerId,
    character_id: characterId,
    move: chosen.move,
    stat: chosen.stat,
    suggestion_move: suggestion.move,
    suggestion_stat: suggestion.stat,
    confirmed,
    declare_seq: declareSeq,
  });
}

/**
 * 숫자가 실제로 변할 때만 뜨는 확인 관문(12-06, D-09/D-10). `confirmAction`과
 * 같은 오류 처리·같은 쿠키 취급을 따른다 — `fetch`가 쿠키를 자동으로 실어
 * 보내므로 서버가 이 요청도 「그 캐릭터를 잡은 사람인가」로 대조한다(남의
 * 캐릭터면 403).
 *
 * **변화량 숫자를 보내지 않는다** — 서버가 `categoryIds`로 룰북 결과 목록을
 * 다시 대조해 실제 양을 만든다(D-02와 같은 근거, T-12-26). `causedBySeq`는
 * 그 자원 변화를 일으킨 원인 사건 순번(보통 그 판정의 `resolve_seq`)이고,
 * Phase 8 멱등성 창이 이 값으로 재시도를 단락시킨다 — 같은 값으로 두 번
 * 보내도 서버는 처음 기록한 사건을 그대로 되읽어 돌려준다(두 번 안 깎인다).
 */
export function confirmResourceChange(
  sessionId: string,
  characterId: string,
  causedBySeq: number,
  categoryIds: string[],
  confirmed: boolean,
): Promise<ConfirmResourceChangeResponse> {
  return postJson<ConfirmResourceChangeResponse>(
    `${sessionBase(sessionId)}/actions/confirm-resource-change`,
    {
      character_id: characterId,
      caused_by_seq: causedBySeq,
      category_ids: categoryIds,
      confirmed,
    },
  );
}

/**
 * 굴릴 필요가 없는 행동(`tier === "no_check"`)을 판정 없이 서술로 잇는다
 * (D-10 ②갈래, 11-06). `confirmAction`과 같은 오류 처리·같은 쿠키 취급을
 * 따른다 — `fetch`가 쿠키를 자동으로 실어 보내므로 이 함수도 다르지 않다.
 * 서버 경로는 `confirmAction`과 달리 `/actions/` 아래가 아니다
 * (`src/gptrpg/web/routes_actions.py`의 `proceed()`가 그렇게 등록한다).
 */
export function proceed(
  sessionId: string,
  playerId: string,
  characterId: string,
  declareSeq: number,
): Promise<ProceedResponse> {
  return postJson<ProceedResponse>(`${sessionBase(sessionId)}/proceed`, {
    player_id: playerId,
    character_id: characterId,
    declare_seq: declareSeq,
  });
}

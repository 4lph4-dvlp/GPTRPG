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
  CharacterSheet,
  CharacterSummary,
  ConfirmResourceChangeResponse,
  ConfirmResponse,
  DeclareResponse,
  MoveCandidate,
  MyCharacterResponse,
  PollResponse,
  ProceedResponse,
} from "./types.ts";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
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

export function selectCharacter(sessionId: string, characterId: string): Promise<unknown> {
  return postJson(`${sessionBase(sessionId)}/select-character`, {
    character_id: characterId,
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

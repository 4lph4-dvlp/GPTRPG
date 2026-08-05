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
  ConfirmResponse,
  DeclareResponse,
  MoveCandidate,
  MyCharacterResponse,
  PollResponse,
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

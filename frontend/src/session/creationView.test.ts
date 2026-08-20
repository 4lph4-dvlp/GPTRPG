/**
 * `gmLinesFrom`/`creationErrorMessage` 순수 함수 시험(12.3-01 Task 3) —
 * `groupTurns.test.ts`와 같은 모양(vitest, RTL 없음, 순수 함수만).
 */

import { describe, expect, it } from "vitest";
import { ApiError } from "../api/client.ts";
import { COPY } from "../labels.ts";
import type { GameEvent } from "../api/types.ts";
import { creationErrorMessage, gmLinesFrom } from "./creationView.ts";

function envelope(seq: number) {
  return {
    session_id: "s1",
    seq,
    schema_version: 11,
    visibility: "public",
    caused_by_seq: null,
    recorded_at: "2026-01-01T00:00:00.000Z",
  };
}

function gmSpoke(
  seq: number,
  overrides: Partial<{
    kind: "announce" | "nominate" | "follow_up" | "wrap_up";
    say: string;
    target_character_id: string | null;
  }> = {},
): GameEvent {
  return {
    ...envelope(seq),
    event_type: "creation_gm_spoke",
    kind: overrides.kind ?? "announce",
    say: overrides.say ?? "안내합니다.",
    target_character_id: overrides.target_character_id ?? null,
    dedupe_key: "announce",
  };
}

function otherEvent(seq: number): GameEvent {
  return {
    ...envelope(seq),
    event_type: "party_size_fixed",
    player_character_count: 3,
    rulebook_id: "dungeonworld_like",
    rulebook_min: 3,
    rulebook_max: 5,
  };
}

describe("gmLinesFrom", () => {
  it("creation_gm_spoke 사건만 골라 seq 오름차순으로 편다 — 다른 종류는 무시한다", () => {
    const events: GameEvent[] = [
      otherEvent(0),
      gmSpoke(2, { say: "두 번째" }),
      gmSpoke(1, { say: "첫 번째" }),
    ];
    const lines = gmLinesFrom(events);
    expect(lines).toEqual([
      { seq: 1, kind: "announce", say: "첫 번째", targetCharacterId: null },
      { seq: 2, kind: "announce", say: "두 번째", targetCharacterId: null },
    ]);
  });

  it("빈 배열이면 빈 배열이다 — 「아직 아무 말도 없다」와 「불러오기 실패」를 섞지 않는다", () => {
    expect(gmLinesFrom([])).toEqual([]);
  });

  it("같은 seq가 두 번 오면 하나만 남는다 — 겹쳐 도착한 폴링 응답", () => {
    const events: GameEvent[] = [
      gmSpoke(5, { say: "먼저 온 사본" }),
      gmSpoke(5, { say: "나중에 온 사본" }),
    ];
    const lines = gmLinesFrom(events);
    expect(lines).toHaveLength(1);
    expect(lines[0].seq).toBe(5);
  });

  it("target_character_id가 있으면(지목) targetCharacterId로 그대로 옮긴다", () => {
    const lines = gmLinesFrom([gmSpoke(0, { kind: "nominate", target_character_id: "hero-1" })]);
    expect(lines[0].targetCharacterId).toBe("hero-1");
  });
});

describe("creationErrorMessage", () => {
  it("503이면 COPY.creationGmUnavailable을 돌려준다 — 기다려도 안 되는 상황(D-13 ②)", () => {
    const error = new ApiError(503, "POST .../announce → 503");
    expect(creationErrorMessage(error)).toBe(COPY.creationGmUnavailable);
  });

  it("503이 아닌 ApiError에 detail이 있으면 그 문장을 그대로 돌려준다(D-15)", () => {
    const error = new ApiError(409, "POST .../announce → 409", "파티 명단이 이미 잠겼다");
    expect(creationErrorMessage(error)).toBe("파티 명단이 이미 잠겼다");
  });

  it("detail이 없는 ApiError면 COPY.creationFailed로 떨어진다", () => {
    const error = new ApiError(500, "POST .../announce → 500");
    expect(creationErrorMessage(error)).toBe(COPY.creationFailed);
  });

  it("ApiError가 아니면 COPY.creationFailed로 떨어진다", () => {
    expect(creationErrorMessage(new Error("network down"))).toBe(COPY.creationFailed);
  });
});

/**
 * `groupTurns`/`isVisibleTurn` 회귀 시험 — 11-06 사람 확인 관문에서 실제로
 * 발견된 결함(「이대로 진행」한 턴이 이야기 화면에 아예 안 보임)의 재발
 * 방지가 목적이다.
 *
 * 이 저장소에 프론트엔드 단위 시험 틀이 이 계획 전까지 없었다(11-03
 * SUMMARY.md 참조) — 이 파일이 `vitest`를 처음 들여온다.
 */

import { describe, expect, it } from "vitest";
import type { GameEvent } from "../api/types.ts";
import { groupTurns, isVisibleTurn } from "./groupTurns.ts";

function envelope(seq: number, causedBy: number | null) {
  return {
    session_id: "s1",
    seq,
    schema_version: 6,
    visibility: "player",
    caused_by_seq: causedBy,
    recorded_at: "2026-01-01T00:00:00.000Z",
  };
}

describe("isVisibleTurn", () => {
  it("판정 없이 진행한 턴(선언 + 서사, 확인 없음)이 보인다 — D-10 ②갈래, 11-06 proceed()", () => {
    const events: GameEvent[] = [
      {
        ...envelope(0, null),
        event_type: "action_declared",
        player_id: "bram",
        raw_text: "문을 연다",
        character_id: "bram",
      },
      {
        ...envelope(1, 0),
        event_type: "narration_appended",
        text: "문이 삐걱 열린다.",
        chunk_index: 0,
      },
      {
        ...envelope(2, 0),
        event_type: "narration_appended",
        text: "안이 어둡다.",
        chunk_index: 1,
      },
    ];

    const turns = groupTurns(events);
    expect(turns).toHaveLength(1);
    const [turn] = turns;
    expect(turn.confirmed).toBeNull();
    expect(turn.check).toBeNull();
    expect(turn.narration).toHaveLength(2);
    expect(isVisibleTurn(turn)).toBe(true);
  });

  it("서사가 통째로 실패한 확인 턴도 계속 보인다 — 회귀 방지(TRUST-06/D-08)", () => {
    const events: GameEvent[] = [
      {
        ...envelope(10, null),
        event_type: "action_declared",
        player_id: "bram",
        raw_text: "문을 부순다",
        character_id: "bram",
      },
      {
        ...envelope(11, 10),
        event_type: "action_confirmed",
        player_id: "bram",
        move: "hack_and_slash",
        stat: "STR",
        system_suggestion: { move: "hack_and_slash", stat: "STR" },
        player_confirmed: true,
        character_id: "bram",
      },
      {
        ...envelope(12, 11),
        event_type: "check_resolved",
        move: "hack_and_slash",
        rolls: [4, 5],
        modifiers: [],
        target: 10,
        grade: "miss",
        counts_as_failure: true,
        person_id: "bram",
        character_id: "bram",
        total: 9,
        rulebook_id: "dungeonworld_like",
      },
    ];

    const turns = groupTurns(events);
    expect(turns).toHaveLength(1);
    const [turn] = turns;
    expect(turn.confirmed).not.toBeNull();
    expect(turn.check).not.toBeNull();
    expect(turn.narration).toHaveLength(0);
    expect(isVisibleTurn(turn)).toBe(true);
  });

  it("선언만 하고 확인도 진행도 안 한 턴은 계속 안 보인다 — 회귀 방지", () => {
    const events: GameEvent[] = [
      {
        ...envelope(20, null),
        event_type: "action_declared",
        player_id: "bram",
        raw_text: "음... 잠깐만 생각 좀 할게",
        character_id: "bram",
      },
    ];

    const turns = groupTurns(events);
    expect(turns).toHaveLength(1);
    const [turn] = turns;
    expect(turn.confirmed).toBeNull();
    expect(turn.narration).toHaveLength(0);
    expect(isVisibleTurn(turn)).toBe(false);
  });

  it("세 모양이 섞인 사건 목록에서 보이는 턴만 정확히 걸러진다(end-to-end)", () => {
    const events: GameEvent[] = [
      {
        ...envelope(0, null),
        event_type: "action_declared",
        player_id: "bram",
        raw_text: "문을 연다",
        character_id: "bram",
      },
      {
        ...envelope(1, 0),
        event_type: "narration_appended",
        text: "문이 삐걱 열린다.",
        chunk_index: 0,
      },
      {
        ...envelope(10, null),
        event_type: "action_declared",
        player_id: "bram",
        raw_text: "문을 부순다",
        character_id: "bram",
      },
      {
        ...envelope(11, 10),
        event_type: "action_confirmed",
        player_id: "bram",
        move: "hack_and_slash",
        stat: "STR",
        system_suggestion: { move: "hack_and_slash", stat: "STR" },
        player_confirmed: true,
        character_id: "bram",
      },
      {
        ...envelope(12, 11),
        event_type: "check_resolved",
        move: "hack_and_slash",
        rolls: [4, 5],
        modifiers: [],
        target: 10,
        grade: "miss",
        counts_as_failure: true,
        person_id: "bram",
        character_id: "bram",
        total: 9,
        rulebook_id: "dungeonworld_like",
      },
      {
        ...envelope(20, null),
        event_type: "action_declared",
        player_id: "nari",
        raw_text: "음... 잠깐만 생각 좀 할게",
        character_id: "nari",
      },
    ];

    const visible = groupTurns(events).filter(isVisibleTurn);
    expect(visible.map((turn) => turn.declareSeq)).toEqual([0, 10]);
  });
});

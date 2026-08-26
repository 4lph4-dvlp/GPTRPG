/**
 * `buildRetryRequest` 회귀 시험(verify-13-06 결함1) — 재시도 요청이
 * 사건에 이미 적힌 값만 그대로 되돌리는지, 특히 **판정 경로에서 declare_seq/
 * move/stat이 원래 확인과 완전히 같은지**를 고정한다. 서버(`confirm()`의
 * `AlreadyConfirmed` 재사용 경로)가 판정을 재사용하는 유일한 조건이 바로
 * 그 값들의 완전한 일치이므로, 이 시험이 깨지면 재시도가 다시 새 판정을
 * 만들어 낸다.
 */

import { describe, expect, it } from "vitest";
import type { ActionConfirmedEvent } from "../api/types.ts";
import type { Turn } from "./groupTurns.ts";
import { buildRetryRequest } from "./turnRetry.ts";

function confirmedEvent(overrides: Partial<ActionConfirmedEvent> = {}): ActionConfirmedEvent {
  return {
    session_id: "s1",
    seq: 64,
    schema_version: 14,
    visibility: "player",
    caused_by_seq: 61,
    recorded_at: "2026-08-26T14:14:03.178Z",
    event_type: "action_confirmed",
    player_id: "pc-1",
    move: "discern_realities",
    stat: "WIS",
    system_suggestion: { move: "discern_realities", stat: "WIS" },
    player_confirmed: true,
    character_id: "pc-1",
    ...overrides,
  };
}

function turnWith(overrides: Partial<Turn> = {}): Turn {
  return {
    declareSeq: 61,
    playerId: "pc-1",
    rawText: "철용은 일단 무기를 든 서리를 경계하며 묻는다.",
    declaredAt: "2026-08-26T14:11:52.058Z",
    confirmed: null,
    check: null,
    clock: null,
    narration: [],
    illustration: null,
    ...overrides,
  };
}

describe("buildRetryRequest", () => {
  it("판정 경로 — 확인 사건의 move/stat/system_suggestion/player_confirmed를 그대로 되돌린다", () => {
    const turn = turnWith({ confirmed: confirmedEvent() });

    const request = buildRetryRequest(turn);

    expect(request).toEqual({
      kind: "confirm",
      declareSeq: 61,
      chosen: { move: "discern_realities", stat: "WIS" },
      suggestion: { move: "discern_realities", stat: "WIS" },
      confirmed: true,
    });
  });

  it("판정 경로 — 시스템 제안과 실제 확정이 다른 경우 둘을 섞지 않는다", () => {
    const turn = turnWith({
      confirmed: confirmedEvent({
        move: "hack_and_slash",
        stat: "STR",
        system_suggestion: { move: "parley", stat: "CHA" },
      }),
    });

    const request = buildRetryRequest(turn);

    expect(request).toEqual({
      kind: "confirm",
      declareSeq: 61,
      chosen: { move: "hack_and_slash", stat: "STR" },
      suggestion: { move: "parley", stat: "CHA" },
      confirmed: true,
    });
  });

  it("판정 경로 — 거부된 확인(player_confirmed=false)도 그 값 그대로 되돌린다", () => {
    const turn = turnWith({
      confirmed: confirmedEvent({ player_confirmed: false }),
    });

    const request = buildRetryRequest(turn);

    expect(request.kind).toBe("confirm");
    expect(request).toMatchObject({ confirmed: false });
  });

  it("판정 없는 경로(D-10 ②갈래) — confirmed가 없으면 declareSeq만으로 proceed 재시도를 요청한다", () => {
    const turn = turnWith({ declareSeq: 41, confirmed: null });

    const request = buildRetryRequest(turn);

    expect(request).toEqual({ kind: "proceed", declareSeq: 41 });
  });

  it("재시도 요청이 매번 같은 declareSeq를 쓴다 — 새 선언을 만들지 않는다(회귀의 핵심)", () => {
    const turn = turnWith({ declareSeq: 61, confirmed: confirmedEvent({ caused_by_seq: 61 }) });

    const first = buildRetryRequest(turn);
    const second = buildRetryRequest(turn);

    expect(first).toEqual(second);
    expect(first.declareSeq).toBe(61);
  });
});

/**
 * `buildCheckSummary`/`indexCalculations` 시험 (Phase 12.2, D-05/D-09/D-10).
 *
 * 네 갈래를 덮는다: 계산 줄 있음 · 없음(D-05) · 처음 보는 역할 이름(D-10
 * 동반 불변식) · `segmentRoleLabel` 되돌림. `groupTurns.test.ts`와 같은
 * 자리·같은 관례.
 */

import { describe, expect, it } from "vitest";
import type { CheckCalculationView, CheckResolvedEvent } from "../api/types.ts";
import { segmentRoleLabel } from "../labels.ts";
import {
  buildCheckSummary,
  buildCheckSummaryFromConfirmResponse,
  indexCalculations,
} from "./checkSummary.ts";

function envelope(seq: number) {
  return {
    session_id: "s1",
    seq,
    schema_version: 10,
    visibility: "player" as const,
    caused_by_seq: null,
    recorded_at: "2026-01-01T00:00:00.000Z",
  };
}

function checkEvent(overrides: Partial<CheckResolvedEvent> = {}): CheckResolvedEvent {
  return {
    ...envelope(3),
    event_type: "check_resolved",
    move: "hack_and_slash",
    rolls: [4, 3],
    modifiers: [],
    target: 10,
    grade: "weak_hit",
    counts_as_failure: false,
    person_id: "p1",
    character_id: "bram",
    total: 9,
    rulebook_id: "dungeonworld_like",
    ...overrides,
  };
}

describe("buildCheckSummary", () => {
  it("계산 줄이 있으면 totalMissing이 거짓이고 서버가 준 조각 순서를 그대로 갖는다", () => {
    const calculation: CheckCalculationView = {
      seq: 3,
      rows: [
        {
          segments: [
            { role: "die", value: 4, source: null, discarded: false },
            { role: "die", value: 3, source: null, discarded: false },
          ],
          total: 9,
        },
      ],
      total: 9,
      target: 10,
      direction: "roll_over",
    };
    const summary = buildCheckSummary(checkEvent(), calculation);

    expect(summary.totalMissing).toBe(false);
    expect(summary.total).toBe(9);
    expect(summary.direction).toBe("roll_over");
    expect(summary.rows).toHaveLength(1);
    expect(summary.rows[0].segments.map((segment) => segment.role)).toEqual(["die", "die"]);
  });

  it("계산 줄이 null이면 totalMissing이 참이고 원시 값은 그대로 실린다(D-05)", () => {
    const summary = buildCheckSummary(checkEvent({ total: null, rulebook_id: null }), null);

    expect(summary.totalMissing).toBe(true);
    expect(summary.total).toBeNull();
    expect(summary.rows).toEqual([]);
    expect(summary.direction).toBeNull();
    expect(summary.rolls).toEqual([4, 3]);
    expect(summary.target).toBe(10);
    expect(summary.grade).toBe("weak_hit");
  });

  it("처음 보는 역할 이름이 있어도 순서가 유지되고 항목이 사라지지 않는다(D-10 동반 불변식)", () => {
    const calculation: CheckCalculationView = {
      seq: 3,
      rows: [
        {
          segments: [
            { role: "explosion", value: 12, source: null, discarded: false },
            { role: "die", value: 4, source: null, discarded: false },
          ],
          total: 16,
        },
      ],
      total: 16,
      target: 10,
      direction: "roll_over",
    };
    const summary = buildCheckSummary(checkEvent(), calculation);

    expect(summary.rows[0].segments.map((segment) => segment.role)).toEqual([
      "explosion",
      "die",
    ]);
  });
});

describe("buildCheckSummaryFromConfirmResponse", () => {
  it("응답 출처와 폴링 사건 출처가 같은 입력값에서 같은 결과를 낸다(D-14, 12.2-02)", () => {
    const calculation: CheckCalculationView = {
      seq: 3,
      rows: [
        {
          segments: [
            { role: "die", value: 4, source: null, discarded: false },
            { role: "die", value: 3, source: null, discarded: false },
          ],
          total: 9,
        },
      ],
      total: 9,
      target: 10,
      direction: "roll_over",
    };
    const fromEvent = buildCheckSummary(checkEvent(), calculation);
    const fromResponse = buildCheckSummaryFromConfirmResponse({
      rolls: [4, 3],
      modifiers: [],
      target: 10,
      grade: "weak_hit",
      calculation,
    });

    expect(fromResponse).toEqual(fromEvent);
  });

  it("계산 줄이 null이면 totalMissing이 참이고 원시 눈·보정치·목표값이 그대로 실린다(D-05)", () => {
    const summary = buildCheckSummaryFromConfirmResponse({
      rolls: [3, 7],
      modifiers: [{ type: "flat", value: 2, source: "stat:CHA" }],
      target: 55,
      grade: "success",
      calculation: null,
    });

    expect(summary.totalMissing).toBe(true);
    expect(summary.total).toBeNull();
    expect(summary.rows).toEqual([]);
    expect(summary.rolls).toEqual([3, 7]);
    expect(summary.modifiers).toEqual([{ type: "flat", value: 2, source: "stat:CHA" }]);
    expect(summary.target).toBe(55);
  });
});

describe("세 화면 자리가 같은 입력에서 같은 요약을 낸다(D-14, 12.2-02 Task 3)", () => {
  it("이야기 화면·검산 창·주사위 연출이 부르는 자리(순수 함수 수준)가 같은 결과를 낸다", () => {
    const calculation: CheckCalculationView = {
      seq: 3,
      rows: [
        {
          segments: [
            { role: "tens", value: 3, source: null, discarded: false },
            { role: "units", value: 7, source: null, discarded: false },
            { role: "percentile", value: 37, source: null, discarded: false },
          ],
          total: 39,
        },
      ],
      total: 39,
      target: 55,
      direction: "roll_under",
    };
    const check = checkEvent({ rolls: [3, 7], target: 55, total: 39, rulebook_id: "openquest" });

    // TurnCard.tsx·DiceModal.tsx는 이 자리(사건 + 계산 줄)를 그대로 부른다.
    const fromEventSource = buildCheckSummary(check, calculation);
    // ChatPane.tsx(CheckBreakdown 배선)는 이 얇은 진입점을 부른다.
    const fromResponseSource = buildCheckSummaryFromConfirmResponse({
      rolls: check.rolls,
      modifiers: check.modifiers,
      target: check.target,
      grade: check.grade,
      calculation,
    });

    expect(fromEventSource).toEqual(fromResponseSource);
    expect(fromEventSource.total).toBe(39);
    expect(fromEventSource.rows[0].segments.map((segment) => segment.value)).toEqual([3, 7, 37]);
  });
});

describe("indexCalculations", () => {
  it("계산 줄 목록을 seq로 색인한다", () => {
    const list: CheckCalculationView[] = [
      { seq: 1, rows: [], total: 5, target: 10, direction: "roll_over" },
      { seq: 3, rows: [], total: 9, target: 10, direction: "roll_over" },
    ];
    const bySeq = indexCalculations(list);

    expect(bySeq.get(1)?.total).toBe(5);
    expect(bySeq.get(3)?.total).toBe(9);
    expect(bySeq.get(2)).toBeUndefined();
  });
});

describe("segmentRoleLabel", () => {
  it("아는 역할 이름은 한국어 꼬리표로 옮긴다", () => {
    expect(segmentRoleLabel("tens")).toBe("십의 자리");
  });

  it("모르는 역할 이름은 원문 그대로 돌려준다(닫힌 목록이 없다, D-10)", () => {
    expect(segmentRoleLabel("전혀_모르는_역할")).toBe("전혀_모르는_역할");
  });
});

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
import { buildCheckSummary, indexCalculations } from "./checkSummary.ts";

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

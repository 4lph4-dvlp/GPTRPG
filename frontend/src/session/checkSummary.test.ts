/**
 * `buildCheckSummary`/`indexCalculations` 시험 (Phase 12.2, D-05/D-09/D-10).
 *
 * 네 갈래를 덮는다: 계산 줄 있음 · 없음(D-05) · 처음 보는 역할 이름(D-10
 * 동반 불변식) · `segmentRoleLabel` 되돌림. `groupTurns.test.ts`와 같은
 * 자리·같은 관례.
 *
 * **다시 굴림 줄 나눔(D-12)·버려진 눈 흐림(D-13)은 지금 브라우저에서
 * 도달할 수 없다** — `reroll_2d6`/`push_d100`은 시험에서만 불리고,
 * `BONUS_DICE`를 만드는 제품 코드가 없다(12.2-03-PLAN.md). `rowLabelFor`·
 * `rollDiscarded` 관련 시험이 두 표시의 유일한 검증 수단이다.
 */

import { describe, expect, it } from "vitest";
import type { CheckCalculationView, CheckResolvedEvent } from "../api/types.ts";
import { segmentRoleLabel } from "../labels.ts";
import {
  buildCheckSummary,
  buildCheckSummaryFromConfirmResponse,
  indexCalculations,
  rowLabelFor,
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

describe("rowLabelFor", () => {
  it("줄이 하나뿐이면 꼬리표가 없다", () => {
    expect(rowLabelFor(0, 1)).toBeNull();
  });

  it("줄이 둘이면 첫 줄이 「처음 굴림」·둘째 줄이 「다시 굴림」이다(D-12)", () => {
    expect(rowLabelFor(0, 2)).toBe("처음 굴림");
    expect(rowLabelFor(1, 2)).toBe("다시 굴림");
  });
});

describe("buildCheckSummary — 다시 굴림 줄 나눔과 버려진 눈(D-11/D-12/D-13)", () => {
  it("줄이 둘이면 각 row가 rowLabel을 갖고, 첫 줄은 total이 null이다", () => {
    const calculation: CheckCalculationView = {
      seq: 3,
      rows: [
        { segments: [{ role: "die", value: 4, source: null, discarded: false }], total: null },
        {
          segments: [
            { role: "die", value: 6, source: null, discarded: false },
            { role: "flat", value: 2, source: "stat:STR", discarded: false },
          ],
          total: 8,
        },
      ],
      total: 8,
      target: 10,
      direction: "roll_over",
    };
    const summary = buildCheckSummary(checkEvent({ rolls: [4, 3, 6, 5] }), calculation);

    expect(summary.rows[0].rowLabel).toBe("처음 굴림");
    expect(summary.rows[0].total).toBeNull();
    expect(summary.rows[1].rowLabel).toBe("다시 굴림");
    expect(summary.rows[1].total).toBe(8);
  });

  it("줄이 하나면 rowLabel이 null이다(회귀 없음)", () => {
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

    expect(summary.rows[0].rowLabel).toBeNull();
  });

  it("버려진 십의 자리가 rollDiscarded에서 같은 자리에 참으로 뜬다(D-13) — 백분위는 안 낀다", () => {
    const calculation: CheckCalculationView = {
      seq: 3,
      rows: [
        {
          segments: [
            { role: "tens", value: 3, source: null, discarded: false },
            { role: "tens", value: 8, source: null, discarded: true },
            { role: "units", value: 7, source: null, discarded: false },
            { role: "percentile", value: 37, source: null, discarded: false },
          ],
          total: 37,
        },
      ],
      total: 37,
      target: 60,
      direction: "roll_under",
    };
    const summary = buildCheckSummary(
      checkEvent({ rolls: [3, 8, 7], target: 60, rulebook_id: "openquest" }),
      calculation,
    );

    // rolls = [3, 8, 7] -> [채택 3, 버려짐 8, 일의 자리 7]
    expect(summary.rollDiscarded).toEqual([false, true, false]);
  });

  it("계산 줄이 없으면 rollDiscarded가 빈 배열이다(D-05)", () => {
    const summary = buildCheckSummary(checkEvent({ total: null, rulebook_id: null }), null);

    expect(summary.rollDiscarded).toEqual([]);
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

describe("rollRoles — 굴림 연출이 눈을 어떤 모양으로 그릴지의 근거", () => {
  it("d100의 두 자릿수는 값과 무관하게 'tens'/'units'로 나온다", () => {
    // 브라우저에서 실제로 나온 판정: 눈 8과 6. 값으로 모양을 고르면 8은
    // 숫자·6은 6면체 그림이 되어 한 판정 안에서 두 가지 그림이 섞였다.
    // 6이 나왔다고 6면체인 것이 아니다 — 역할이 그것을 말해 준다.
    const calculation: CheckCalculationView = {
      seq: 3,
      rows: [
        {
          segments: [
            { role: "tens", value: 8, source: null, discarded: false },
            { role: "units", value: 6, source: null, discarded: false },
            { role: "percentile", value: 86, source: null, discarded: false },
          ],
          total: 86,
        },
      ],
      total: 86,
      target: 55,
      direction: "roll_under",
    };
    const summary = buildCheckSummary(
      checkEvent({ rolls: [8, 6], total: 86, target: 55, rulebook_id: "openquest" }),
      calculation,
    );

    // 눈 하나에 대응하는 역할만 나란히 실린다 — 백분위는 파생값이라 빠진다.
    expect(summary.rollRoles).toEqual(["tens", "units"]);
    expect(summary.rollRoles.length).toBe(summary.rolls.length);
  });

  it("룰북이 선언한 주사위는 'die'로 나온다", () => {
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

    expect(summary.rollRoles).toEqual(["die", "die"]);
  });

  it("계산 줄이 없는 옛 기록은 빈 배열이다 — 부르는 쪽이 옛 규칙으로 떨어진다", () => {
    const summary = buildCheckSummary(checkEvent(), null);

    expect(summary.rollRoles).toEqual([]);
  });
});

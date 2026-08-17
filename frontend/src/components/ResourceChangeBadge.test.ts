/**
 * `changeIntensity` 회귀 시험 — RULE-07/D-19가 요구하는 것은 "몇 % 이상이면
 * 크다"는 이산 문턱이 아니라 "변화량이 클수록 표시가 더 강하다"는 연속
 * 성질이다. 등급 이름으로 가르는 분기를 안 만들었다는 것을, 반환값이
 * 0~1 사이 연속값이고 단조 비감소라는 성질로 직접 확인한다.
 *
 * 형태별로 계산 가능한 것만 쓴다는 것(플랜 액션②)을 네 경우 각각으로
 * 확인한다 — 상한이 있는 숫자 축·상한이 없는 숫자 축·slots·tags.
 */

import { describe, expect, it } from "vitest";
import type { StatEntry } from "../api/types.ts";
import { changeIntensity } from "./ResourceChangeBadge.tsx";

function stat(overrides: Partial<StatEntry>): StatEntry {
  return {
    name: "체력",
    form: "numeric",
    current: 5,
    max: null,
    depleted_effect_ref: null,
    slot_values: null,
    tags: null,
    none_kind: null,
    ...overrides,
  };
}

describe("changeIntensity", () => {
  it("항상 0 이상 1 이하다", () => {
    const capped = stat({ form: "numeric", max: 10 });
    const uncapped = stat({ form: "numeric", max: null });
    const slots = stat({ form: "named_slots", slot_values: [null, null, "rope"] });
    const tags = stat({ form: "tag_list", tags: ["dazed"] });

    for (const amount of [0, 1, 3, 10, 1000]) {
      expect(changeIntensity({ amount }, capped)).toBeGreaterThanOrEqual(0);
      expect(changeIntensity({ amount }, capped)).toBeLessThanOrEqual(1);
      expect(changeIntensity({ amount }, uncapped)).toBeGreaterThanOrEqual(0);
      expect(changeIntensity({ amount }, uncapped)).toBeLessThanOrEqual(1);
      expect(changeIntensity({ amount }, slots)).toBeGreaterThanOrEqual(0);
      expect(changeIntensity({ amount }, slots)).toBeLessThanOrEqual(1);
      expect(changeIntensity({ amount }, tags)).toBeGreaterThanOrEqual(0);
      expect(changeIntensity({ amount }, tags)).toBeLessThanOrEqual(1);
    }
  });

  it("상한이 있는 숫자 축 — 변화량이 클수록 세기가 작지 않다(단조 비감소)", () => {
    const gauge = stat({ form: "numeric", max: 20 });
    const small = changeIntensity({ amount: 2 }, gauge);
    const large = changeIntensity({ amount: 10 }, gauge);
    expect(large).toBeGreaterThan(small);
    expect(changeIntensity({ amount: 20 }, gauge)).toBeCloseTo(1);
    expect(changeIntensity({ amount: 0 }, gauge)).toBe(0);
  });

  it("상한이 없는 숫자 축 — 변화량이 클수록 세기가 작지 않다(단조 비감소, 절대 1을 안 넘는다)", () => {
    const unbounded = stat({ form: "numeric", max: null });
    const values = [0, 1, 2, 5, 10, 50, 500];
    let previous = -1;
    for (const amount of values) {
      const value = changeIntensity({ amount }, unbounded);
      expect(value).toBeGreaterThanOrEqual(previous);
      expect(value).toBeLessThan(1);
      previous = value;
    }
  });

  it("named_slots — 바뀐 칸 수 대비 전체 칸 수, 단조 비감소", () => {
    const slots = stat({ form: "named_slots", slot_values: [null, "rope", "torch", null] });
    const one = changeIntensity({ amount: 1 }, slots);
    const two = changeIntensity({ amount: 2 }, slots);
    expect(two).toBeGreaterThan(one);
    expect(changeIntensity({ amount: 4 }, slots)).toBeCloseTo(1);
  });

  it("tag_list — 바뀐 태그 수 대비 지금 태그 목록 길이, 단조 비감소", () => {
    const tags = stat({ form: "tag_list", tags: ["dazed", "prone"] });
    const one = changeIntensity({ amount: 1 }, tags);
    const two = changeIntensity({ amount: 2 }, tags);
    expect(two).toBeGreaterThan(one);
    expect(changeIntensity({ amount: 2 }, tags)).toBeCloseTo(1);
  });

  it("이산 등급 문자열을 돌려주지 않는다 — 반환 타입이 항상 number", () => {
    const gauge = stat({ form: "numeric", max: 10 });
    expect(typeof changeIntensity({ amount: 1 }, gauge)).toBe("number");
    expect(typeof changeIntensity({ amount: 9 }, gauge)).toBe("number");
  });
});

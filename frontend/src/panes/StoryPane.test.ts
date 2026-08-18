/**
 * `clockAdvanceReason` 회귀 시험 — 2026-08-18 플레이테스트.
 *
 * 관측된 결함: 완전 성공(`strong_hit`, 누적 실패 0) 직후 위협 시계가 돌면서
 * 화면에 「판정 실패가 쌓여 시스템이 진행시켰어요」가 떴다. 실제 사건은
 * `trigger="condition"`(AI가 이야기 조건 충족을 판단)이었고 시계는 제대로
 * 돈 것이었다 — 화면 문구가 실패 문구 하나로 박혀 있어서 **성공한
 * 플레이어에게 실패했다고 말한 것**이 결함이었다.
 *
 * 이유를 안 보여주는 것보다 틀린 이유를 보여주는 것이 나쁘다. 그래서 세
 * 갈래가 서로 다른 문장을 돌려주는지, 그리고 실패 문구가 실패일 때만
 * 나오는지를 직접 고정한다.
 */

import { describe, expect, it } from "vitest";
import { COPY } from "../labels.ts";
import { clockAdvanceReason } from "./StoryPane.tsx";

describe("clockAdvanceReason", () => {
  it("실패 누적으로 돌았을 때만 실패 문구를 쓴다", () => {
    expect(clockAdvanceReason("fail_counter")).toBe(COPY.clockAdvancedByFailCounter);
    expect(clockAdvanceReason("condition")).not.toBe(COPY.clockAdvancedByFailCounter);
    expect(clockAdvanceReason("ai_choice")).not.toBe(COPY.clockAdvancedByFailCounter);
  });

  it("이야기 조건으로 돌았을 때 조건 문구를 쓴다 (관측된 결함 그 자체)", () => {
    expect(clockAdvanceReason("condition")).toBe(COPY.clockAdvancedByCondition);
  });

  it("진행자 판단으로 돌았을 때 그 문구를 쓴다", () => {
    expect(clockAdvanceReason("ai_choice")).toBe(COPY.clockAdvancedByAiChoice);
  });

  it("세 갈래가 서로 다른 문장이다 — 갈래를 나눈 것이 표시로 이어진다", () => {
    const reasons = (["fail_counter", "condition", "ai_choice"] as const).map(clockAdvanceReason);
    expect(new Set(reasons).size).toBe(reasons.length);
    for (const reason of reasons) {
      expect(reason.trim()).not.toBe("");
    }
  });
});

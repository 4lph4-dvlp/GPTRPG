/**
 * `shouldOpenScene` 순수 함수 시험(Phase 13, SCENE-01) —
 * `creationView.test.ts`의 `shouldAnnounce` 시험과 같은 모양(vitest, RTL
 * 없음, 순수 함수만). 이 시험이 없으면 effect의 발동 조건이 틀려도
 * 아무것도 안 걸린다 — 12.3이 같은 종류의 부트스트랩 판단에서 여섯
 * 라운드를 살아남은 결함과 같은 모양이다.
 */

import { describe, expect, it } from "vitest";
import type { GameStateView } from "../api/types.ts";
import { shouldOpenScene } from "./openingView.ts";

function baseState(overrides: Partial<GameStateView> = {}): GameStateView {
  return {
    session_id: "s1",
    last_seq: 0,
    turn_count: 0,
    check_count: 0,
    failure_count: 0,
    fails_since_clock: 0,
    clock_segment: 0,
    clock_advances: 0,
    narration_count: 0,
    ai_calls: 0,
    total_tokens: 0,
    last_grade: null,
    clock_segment_count: 4,
    auto_advance_threshold: 3,
    party_size_fixed: 4,
    creation_rulebook_id: "dungeonworld_like",
    party_roster: null,
    creation_unfinished_character_ids: [],
    creation_current_speaker_id: null,
    creation_characters: [],
    creation_reopened_step_ids: [],
    creation_step_values: [],
    creation_host_claimed: false,
    scene_opened_seq: null,
    ...overrides,
  };
}

describe("지금 오프닝을 부를 때인지 판정한다 (SCENE-01, D-01/D-02)", () => {
  it("폴링 상태가 아직 null이면 거짓이다 — null을 '부를 때다'로 바꿔 읽지 않는다", () => {
    expect(shouldOpenScene(null, false)).toBe(false);
  });

  it("명단이 아직 안 잠겼으면(party_roster === null) 거짓이다(D-01)", () => {
    const state = baseState({ party_roster: null });
    expect(shouldOpenScene(state, false)).toBe(false);
  });

  it("오프닝이 이미 있으면(scene_opened_seq !== null) 거짓이다", () => {
    const state = baseState({
      party_roster: ["hero-1", "hero-2"],
      scene_opened_seq: 12,
    });
    expect(shouldOpenScene(state, false)).toBe(false);
  });

  it("직전 시도가 실패했으면 거짓이다 — 자동 재시도 고리를 만들지 않는다", () => {
    const state = baseState({
      party_roster: ["hero-1", "hero-2"],
      scene_opened_seq: null,
    });
    expect(shouldOpenScene(state, true)).toBe(false);
  });

  it("명단이 잠겼고 오프닝이 없고 직전 시도가 실패하지 않았으면 참이다", () => {
    const state = baseState({
      party_roster: ["hero-1", "hero-2"],
      scene_opened_seq: null,
    });
    expect(shouldOpenScene(state, false)).toBe(true);
  });
});

/**
 * `shouldOpenScene` 순수 함수 시험(Phase 13, SCENE-01) —
 * `creationView.test.ts`의 `shouldAnnounce` 시험과 같은 모양(vitest, RTL
 * 없음, 순수 함수만). 이 시험이 없으면 effect의 발동 조건이 틀려도
 * 아무것도 안 걸린다 — 12.3이 같은 종류의 부트스트랩 판단에서 여섯
 * 라운드를 살아남은 결함과 같은 모양이다.
 */

import { describe, expect, it } from "vitest";
import type { GameStateView } from "../api/types.ts";
import { hasLockedRoster, shouldOpenScene } from "./openingView.ts";

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

/**
 * `hasLockedRoster` 배선 회귀 시험 — Task 3 사람 확인이 잡은 실제 결함.
 *
 * `shouldOpenScene`의 갈래는 전부 옳았다(위 다섯 시험이 그대로 통과했다).
 * 결함은 `SessionScreen`의 effect **의존성 배열**에 있었다 — 순수 판정
 * 함수를 시험해도 「그 판정이 실제로 다시 도는가」는 안 잡힌다는 것이
 * 이 파일의 도크스트링이 이미 경고한 바로 그 모양이다. RTL 없이 이
 * 저장소에서 닿을 수 있는 가장 가까운 시험 자리는 effect가 의존성으로
 * 쓰는 신호 자체를 순수 함수로 빼서 그 신호가 실제 상태 전이에서
 * 바뀌는지를 확인하는 것이다.
 */
describe("hasLockedRoster — SessionScreen effect 의존성 배선 결함 회귀 시험", () => {
  it("결함 재현: 이전 식(`feed.state?.party_roster !== null`)은 「마운트 직후 아직 상태 없음」과 「이미 잠긴 채로 첫 폴링 도착」을 똑같이 true로 접는다 — 그래서 React가 변화를 못 보고 effect가 다시 안 돈다", () => {
    const beforeFirstPoll = (null as GameStateView | null)?.party_roster !== null;
    const afterFirstPollAlreadyLocked =
      baseState({ party_roster: ["hero-1"] }).party_roster !== null;
    expect(beforeFirstPoll).toBe(true);
    expect(afterFirstPollAlreadyLocked).toBe(true);
    expect(beforeFirstPoll).toBe(afterFirstPollAlreadyLocked); // 결함: 값이 안 바뀐다
  });

  it("hasLockedRoster는 같은 전이에서 false → true로 실제로 바뀐다 — React가 변화를 보고 effect를 다시 돌린다", () => {
    expect(hasLockedRoster(null)).toBe(false);
    expect(hasLockedRoster(baseState({ party_roster: ["hero-1"] }))).toBe(true);
  });

  it("명단이 마운트 이후에 잠기는 정상 경로도 여전히 false → true다(기존 전이가 안 깨졌다)", () => {
    expect(hasLockedRoster(baseState({ party_roster: null }))).toBe(false);
    expect(hasLockedRoster(baseState({ party_roster: ["hero-1"] }))).toBe(true);
  });
});

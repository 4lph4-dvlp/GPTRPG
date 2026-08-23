/**
 * `gmLinesFrom`/`creationErrorMessage` 순수 함수 시험(12.3-01 Task 3) —
 * `groupTurns.test.ts`와 같은 모양(vitest, RTL 없음, 순수 함수만).
 */

import { describe, expect, it } from "vitest";
import { ApiError } from "../api/client.ts";
import { COPY } from "../labels.ts";
import type {
  CreationStepCompletedEvent,
  CreationStepValueView,
  CreationStepView,
  GameEvent,
  GameStateView,
  PartySizeRangeView,
} from "../api/types.ts";
import {
  canEdit,
  consentGate,
  type CreationStepRow,
  creationErrorMessage,
  creationRollsFrom,
  creationTurn,
  gmLinesFrom,
  isMyTurn,
  myStepValues,
  nextUnfilledStep,
  partySizeGate,
  partySizeOutOfRange,
  pendingConsenters,
  remainingFixedValues,
  shouldAnnounce,
  shouldNominateNext,
  stepRows,
} from "./creationView.ts";

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
    ...overrides,
  };
}

function stepDecl(overrides: Partial<CreationStepView> = {}): CreationStepView {
  return {
    step_id: "name",
    kind: "free_text",
    label: "이름·모습",
    required: true,
    provides_display_name: true,
    axis_names: [],
    options: null,
    pick_count: null,
    fixed_values: null,
    point_budget: null,
    per_target_max: null,
    dice_expr: null,
    derive_base_axis: null,
    derive_multiplier: null,
    derive_offset: null,
    depends_on: [],
    default_from: null,
    ...overrides,
  };
}

function stepValue(overrides: Partial<CreationStepValueView> = {}): CreationStepValueView {
  return {
    character_id: "hero-1",
    step_id: "name",
    kind: "free_text",
    text_value: "브람, 마른 체구의 전직 용병",
    picked: null,
    axis_values: null,
    rolls: null,
    seq: 1,
    ...overrides,
  };
}

describe("isMyTurn", () => {
  it("creation_current_speaker_id가 내 캐릭터와 같을 때만 참이다", () => {
    const state = baseState({ creation_current_speaker_id: "hero-1" });
    expect(isMyTurn(state, "hero-1")).toBe(true);
    expect(isMyTurn(state, "hero-2")).toBe(false);
  });

  it("creation_current_speaker_id가 null이면 거짓이다 — 「아직 지목이 없다」를 「내 차례다」로 바꿔 읽지 않는다", () => {
    const state = baseState({ creation_current_speaker_id: null });
    expect(isMyTurn(state, "hero-1")).toBe(false);
  });
});

describe("myStepValues", () => {
  it("state.creation_step_values에서 내 것만 골라 step_id로 찾을 수 있는 지도를 만든다", () => {
    const state = baseState({
      creation_step_values: [
        stepValue({ character_id: "hero-1", step_id: "name" }),
        stepValue({ character_id: "hero-2", step_id: "name" }),
        stepValue({ character_id: "hero-1", step_id: "look", text_value: "가벼운 방어구" }),
      ],
    });
    const values = myStepValues(state, "hero-1");
    expect([...values.keys()].sort()).toEqual(["look", "name"]);
    expect(values.get("name")?.character_id).toBe("hero-1");
    expect(values.has("look")).toBe(true);
  });
});

describe("stepRows", () => {
  it("CreationStepView 선언 순서를 그대로 유지하고 filled/reopened/value를 붙인다", () => {
    const steps = [
      stepDecl({ step_id: "armor", kind: "pick_one", required: false, provides_display_name: false }),
      stepDecl({ step_id: "name" }),
    ];
    const state = baseState({
      creation_step_values: [stepValue({ character_id: "hero-1", step_id: "name" })],
      creation_reopened_step_ids: [{ character_id: "hero-1", step_id: "armor" }],
    });
    const rows = stepRows(steps, state, "hero-1");
    expect(rows.map((row) => row.step.step_id)).toEqual(["armor", "name"]);
    expect(rows[0]).toMatchObject({ filled: false, reopened: true, value: null });
    expect(rows[1].filled).toBe(true);
    expect(rows[1].reopened).toBe(false);
    expect(rows[1].value?.step_id).toBe("name");
  });

  it("선언에 없는 값이 상태에 있어도 줄을 만들지 않는다 — 룰북 선언이 순서의 유일한 출처다", () => {
    const steps = [stepDecl({ step_id: "name" })];
    const state = baseState({
      creation_step_values: [stepValue({ character_id: "hero-1", step_id: "unknown-step" })],
    });
    const rows = stepRows(steps, state, "hero-1");
    expect(rows).toHaveLength(1);
    expect(rows[0].step.step_id).toBe("name");
  });
});

describe("canEdit", () => {
  it("내 차례일 때 아무 줄이나 참이다 — 「마지막 것만 한 칸 뒤로」가 아니다(D-09)", () => {
    const filledRow: CreationStepRow = {
      step: stepDecl(),
      filled: true,
      reopened: false,
      value: stepValue(),
    };
    const unfilledRow: CreationStepRow = {
      step: stepDecl({ step_id: "armor", required: false, provides_display_name: false }),
      filled: false,
      reopened: false,
      value: null,
    };
    expect(canEdit(filledRow, true)).toBe(true);
    expect(canEdit(unfilledRow, true)).toBe(true);
  });

  it("내 차례가 아니면 거짓이다", () => {
    const row: CreationStepRow = { step: stepDecl(), filled: true, reopened: false, value: stepValue() };
    expect(canEdit(row, false)).toBe(false);
  });
});

describe("nextUnfilledStep", () => {
  it("required이면서 안 채워진 첫 줄을 돌려준다", () => {
    const rows: CreationStepRow[] = [
      {
        step: stepDecl({ step_id: "armor", required: false, provides_display_name: false }),
        filled: false,
        reopened: false,
        value: null,
      },
      { step: stepDecl({ step_id: "name" }), filled: false, reopened: false, value: null },
    ];
    expect(nextUnfilledStep(rows)?.step.step_id).toBe("name");
  });

  it("전부 채워졌으면 null이다", () => {
    const rows: CreationStepRow[] = [
      { step: stepDecl({ step_id: "name" }), filled: true, reopened: false, value: stepValue() },
    ];
    expect(nextUnfilledStep(rows)).toBeNull();
  });
});

function creationStepCompleted(
  seq: number,
  overrides: Partial<CreationStepCompletedEvent> = {},
): CreationStepCompletedEvent {
  return {
    ...envelope(seq),
    event_type: "creation_step_completed",
    character_id: "hero-1",
    browser_id: "browser-1",
    step_id: "stats",
    kind: "roll_to_fill",
    text_value: null,
    picked: null,
    axis_values: [{ axis_name: "STR", value: 12 }],
    rolls: [4, 5, 3],
    superseded_seq: null,
    ...overrides,
  };
}

describe("creationRollsFrom", () => {
  it("rolls가 null이거나 빈 creation_step_completed는 큐에 안 들어간다 — 자유 서술·선택은 굴림이 아니다", () => {
    const events: GameEvent[] = [
      creationStepCompleted(0, { rolls: null }),
      creationStepCompleted(1, { rolls: [] }),
    ];
    expect(creationRollsFrom(events, new Map())).toEqual([]);
  });

  it("rolls가 있는 사건은 label과 함께 나온다 — step_id로 stepsById에서 찾는다", () => {
    const stepsById = new Map([
      ["stats", stepDecl({ step_id: "stats", kind: "roll_to_fill", label: "능력치 굴리기" })],
    ]);
    const items = creationRollsFrom([creationStepCompleted(2)], stepsById);
    expect(items).toHaveLength(1);
    expect(items[0].label).toBe("능력치 굴리기");
    expect(items[0].creationStep.rolls).toEqual([4, 5, 3]);
  });

  it("stepsById에 없으면 step_id를 그대로 쓴다", () => {
    const items = creationRollsFrom([creationStepCompleted(3, { step_id: "unknown" })], new Map());
    expect(items[0].label).toBe("unknown");
  });

  it("다른 종류 사건이 섞여도 무시한다", () => {
    const events: GameEvent[] = [
      creationStepCompleted(4),
      { ...envelope(5), event_type: "creation_interjection", speaker_character_id: "hero-2", browser_id: "b2", during_character_id: "hero-1", mentioned_character_ids: [], text: "끼어드는 말" },
    ];
    expect(creationRollsFrom(events, new Map())).toHaveLength(1);
  });

  it("같은 seq가 두 번 와도 하나만 나온다", () => {
    const events: GameEvent[] = [creationStepCompleted(6), creationStepCompleted(6)];
    expect(creationRollsFrom(events, new Map())).toHaveLength(1);
  });
});

describe("partySizeGate", () => {
  it("party_size_fixed가 있으면 done이다 — 방장 여부와 무관하다", () => {
    const state = baseState({ party_size_fixed: 4 });
    expect(partySizeGate(state, true)).toBe("done");
    expect(partySizeGate(state, false)).toBe("done");
  });

  it("아직 인원이 없고 내가 방장이면 fix다", () => {
    const state = baseState({ party_size_fixed: null, creation_host_claimed: true });
    expect(partySizeGate(state, true)).toBe("fix");
  });

  it("아직 인원이 없고 방장이 이미 있는데 내가 아니면 waiting_for_host다", () => {
    const state = baseState({ party_size_fixed: null, creation_host_claimed: true });
    expect(partySizeGate(state, false)).toBe("waiting_for_host");
  });

  it("아직 인원도 방장도 없으면 waiting_for_claim이다", () => {
    const state = baseState({ party_size_fixed: null, creation_host_claimed: false });
    expect(partySizeGate(state, false)).toBe("waiting_for_claim");
  });
});

describe("partySizeOutOfRange (G-12.3-2)", () => {
  // 이 숫자들은 순수한 시험 입력이다 — 어떤 룰북의 실제 범위라고 적지
  // 않는다(그렇게 적는 순간 화면 시험이 특정 룰북 지식을 갖게 된다).
  const RANGE: PartySizeRangeView = { min_player_characters: 3, max_player_characters: 5 };
  const UNBOUNDED_RANGE: PartySizeRangeView = { min_player_characters: 1, max_player_characters: null };

  it("범위 안이면 거짓이다", () => {
    expect(partySizeOutOfRange(3, RANGE)).toBe(false);
    expect(partySizeOutOfRange(4, RANGE)).toBe(false);
    expect(partySizeOutOfRange(5, RANGE)).toBe(false);
  });

  it("최소 미만이면 참이다", () => {
    expect(partySizeOutOfRange(2, RANGE)).toBe(true);
  });

  it("상한 초과면 참이다", () => {
    expect(partySizeOutOfRange(6, RANGE)).toBe(true);
  });

  it("상한이 없는 범위(null)에서는 아무리 커도 거짓이다", () => {
    expect(partySizeOutOfRange(1, UNBOUNDED_RANGE)).toBe(false);
    expect(partySizeOutOfRange(1_000_000, UNBOUNDED_RANGE)).toBe(false);
  });
});

describe("consentGate", () => {
  it("party_roster가 있으면 locked다 — wrappedUp과 무관하다", () => {
    const state = baseState({ party_roster: ["hero-1"] });
    expect(consentGate(state, true)).toBe("locked");
    expect(consentGate(state, false)).toBe("locked");
  });

  it("완성된 캐릭터가 없으면 not_ready다", () => {
    const state = baseState({ party_roster: null, creation_characters: [], creation_unfinished_character_ids: [] });
    expect(consentGate(state, true)).toBe("not_ready");
  });

  it("아직 안 끝난 사람이 있으면 not_ready다", () => {
    const state = baseState({
      party_roster: null,
      creation_characters: [{ character_id: "hero-1", display_name: "브람", consented: false, required_steps_filled: true }],
      creation_unfinished_character_ids: ["hero-2"],
    });
    expect(consentGate(state, true)).toBe("not_ready");
  });

  it("정한 인원만큼 완성됐지만 GM 정리가 아직 없으면 needs_wrap_up이다", () => {
    const state = baseState({
      party_roster: null,
      party_size_fixed: 1,
      creation_characters: [{ character_id: "hero-1", display_name: "브람", consented: false, required_steps_filled: true }],
      creation_unfinished_character_ids: [],
    });
    expect(consentGate(state, false)).toBe("needs_wrap_up");
  });

  it("정한 인원만큼 완성되고 GM 정리도 있으면 open이다", () => {
    const state = baseState({
      party_roster: null,
      party_size_fixed: 1,
      creation_characters: [{ character_id: "hero-1", display_name: "브람", consented: false, required_steps_filled: true }],
      creation_unfinished_character_ids: [],
    });
    expect(consentGate(state, true)).toBe("open");
  });

  // G-12.3-11 — 아직 아무것도 안 누른 참가자는
  // `creation_unfinished_character_ids`에 원리적으로 못 들어간다. 그래서
  // 먼저 끝낸 한 사람에게 「이대로 시작」이 떠서 나머지가 영구히
  // 배제됐다. 방장이 정한 인원이 유일하게 그것을 아는 숫자다.
  it("정한 인원보다 적게 완성됐으면 not_ready다 — 아직 아무것도 안 누른 사람이 남아 있다", () => {
    const state = baseState({
      party_roster: null,
      party_size_fixed: 3,
      creation_characters: [{ character_id: "hero-1", display_name: "브람", consented: false, required_steps_filled: true }],
      creation_unfinished_character_ids: [],
    });
    expect(consentGate(state, true)).toBe("not_ready");
  });

  it("인원이 아직 안 정해졌으면 이 검사는 아무 말도 안 한다", () => {
    const state = baseState({
      party_roster: null,
      party_size_fixed: null,
      creation_characters: [{ character_id: "hero-1", display_name: "브람", consented: false, required_steps_filled: true }],
      creation_unfinished_character_ids: [],
    });
    expect(consentGate(state, true)).toBe("open");
  });
});

describe("pendingConsenters", () => {
  it("consented가 거짓인 캐릭터의 display_name만 돌려준다 — character_id가 아니다", () => {
    const state = baseState({
      creation_characters: [
        { character_id: "hero-1", display_name: "브람", consented: false, required_steps_filled: true },
        { character_id: "hero-2", display_name: "나리", consented: true, required_steps_filled: true },
      ],
    });
    expect(pendingConsenters(state)).toEqual(["브람"]);
  });

  it("전원 동의했으면 빈 배열이다", () => {
    const state = baseState({
      creation_characters: [
        { character_id: "hero-1", display_name: "브람", consented: true, required_steps_filled: true },
      ],
    });
    expect(pendingConsenters(state)).toEqual([]);
  });
});

describe("shouldNominateNext", () => {
  it("부트스트랩(인원 확정·안내됨·완성 0·미완성 빈 목록·지목 없음)이면 참이다 — 오늘 화면의 조건(unfinished.length>0)으로는 거짓이다(12.3-06 gap)", () => {
    const state = baseState({
      party_size_fixed: 3,
      party_roster: null,
      creation_current_speaker_id: null,
      creation_characters: [],
      creation_unfinished_character_ids: [],
    });
    expect(shouldNominateNext(state, true)).toBe(true);
  });

  it("첫 사람이 완성되고 나머지는 아직 아무 항목도 안 낸 상태여도 참이다 — 두 번째 교착을 막는다", () => {
    const state = baseState({
      party_size_fixed: 3,
      party_roster: null,
      creation_current_speaker_id: null,
      creation_characters: [
        { character_id: "hero-1", display_name: "브람", consented: false, required_steps_filled: true },
      ],
      creation_unfinished_character_ids: [],
    });
    expect(shouldNominateNext(state, true)).toBe(true);
  });

  it("이미 지목된 사람이 있으면 거짓이다", () => {
    const state = baseState({
      party_size_fixed: 3,
      creation_current_speaker_id: "hero-1",
    });
    expect(shouldNominateNext(state, true)).toBe(false);
  });

  it("안내가 아직 없으면 거짓이다", () => {
    const state = baseState({ party_size_fixed: 3, creation_current_speaker_id: null });
    expect(shouldNominateNext(state, false)).toBe(false);
  });

  it("명단이 잠겼으면 거짓이다", () => {
    const state = baseState({
      party_size_fixed: 3,
      party_roster: ["hero-1", "hero-2", "hero-3"],
      creation_current_speaker_id: null,
    });
    expect(shouldNominateNext(state, true)).toBe(false);
  });

  it("완성 수가 확정 인원과 정확히 같으면 거짓이다(경계값) — 다음은 지목이 아니라 정리·동의다", () => {
    const state = baseState({
      party_size_fixed: 1,
      party_roster: null,
      creation_current_speaker_id: null,
      creation_characters: [
        { character_id: "hero-1", display_name: "브람", consented: false, required_steps_filled: true },
      ],
      creation_unfinished_character_ids: [],
    });
    expect(shouldNominateNext(state, true)).toBe(false);
  });

  it("인원이 아직 확정 안 됐으면 거짓이다", () => {
    const state = baseState({ party_size_fixed: null, creation_current_speaker_id: null });
    expect(shouldNominateNext(state, true)).toBe(false);
  });
});

describe("첫 안내를 부를 때인지 판정한다 (G-12.3-5)", () => {
  // 이 시험이 없으면 effect의 발동 조건이 틀려도 아무것도 안 걸린다 —
  // 의존성 배열이 잘못돼 한 번도 안 불리거나, 인원 확정 전에도 불리거나,
  // 실패 뒤 무한히 다시 불려도 화면 구조 검사(ref 존재·줄 순서·문구
  // 개수)는 전부 통과한다. 이번 라운드가 닫는 결함(G-12.3-6)이 여섯
  // 라운드를 살아남은 모양이 정확히 그것이었다 — 발동 조건은 반드시
  // 시험이 직접 실행하는 순수 함수 하나에 있어야 한다.

  it("인원이 확정됐고 안내가 없고 직전 시도가 실패하지 않았으면 참이다", () => {
    const state = baseState({ party_size_fixed: 3, party_roster: null });
    expect(shouldAnnounce(state, false, false)).toBe(true);
  });

  it("인원 확정 전(party_size_fixed === null)이면 거짓이다", () => {
    const state = baseState({ party_size_fixed: null, party_roster: null });
    expect(shouldAnnounce(state, false, false)).toBe(false);
  });

  it("이미 안내가 있으면(announced === true) 거짓이다", () => {
    const state = baseState({ party_size_fixed: 3, party_roster: null });
    expect(shouldAnnounce(state, true, false)).toBe(false);
  });

  it("직전 시도가 실패했으면 거짓이다 — 자동 재시도 고리를 만들지 않는다(D-13 ②)", () => {
    const state = baseState({ party_size_fixed: 3, party_roster: null });
    expect(shouldAnnounce(state, false, true)).toBe(false);
  });

  it("명단이 이미 잠겼으면(party_roster !== null) 거짓이다 — 만들기가 끝난 세션이다", () => {
    const state = baseState({ party_size_fixed: 3, party_roster: ["hero-1", "hero-2", "hero-3"] });
    expect(shouldAnnounce(state, false, false)).toBe(false);
  });
});

describe("지금 누구 차례인지 판정한다 (G-12.3-7)", () => {
  const NAME_STEP = stepDecl({ step_id: "name", provides_display_name: true });
  const LOOK_STEP = stepDecl({ step_id: "look", provides_display_name: false });
  const STEPS = [NAME_STEP, LOOK_STEP];

  it("아직 아무도 지목되지 않았으면 아무 차례도 아니다", () => {
    const state = baseState({ creation_current_speaker_id: null });
    expect(creationTurn(state, "hero-1", STEPS)).toEqual({ kind: "none" });
  });

  it("내가 지목됐으면 내 차례다", () => {
    const state = baseState({ creation_current_speaker_id: "hero-1" });
    expect(creationTurn(state, "hero-1", STEPS)).toEqual({ kind: "me" });
  });

  it("남이 지목됐고 그 사람이 이미 완성됐으면 그 이름을 낸다", () => {
    const state = baseState({
      creation_current_speaker_id: "hero-2",
      creation_characters: [
        { character_id: "hero-2", display_name: "나리", consented: false, required_steps_filled: true },
      ],
    });
    expect(creationTurn(state, "hero-1", STEPS)).toEqual({ kind: "other", name: "나리" });
  });

  it("남이 지목됐고 이름 항목을 아직 안 채웠으면 이름이 없다고 답한다 — 없는 이름을 지어내지 않는다", () => {
    const state = baseState({
      creation_current_speaker_id: "hero-2",
      creation_characters: [],
      creation_step_values: [],
    });
    expect(creationTurn(state, "hero-1", STEPS)).toEqual({ kind: "other", name: null });
  });

  it("남이 지목됐고 이름 항목을 이미 채웠으면 완성 전이라도 그 이름을 낸다", () => {
    const state = baseState({
      creation_current_speaker_id: "hero-2",
      creation_characters: [],
      creation_step_values: [
        stepValue({ character_id: "hero-2", step_id: "name", text_value: "가온" }),
      ],
    });
    expect(creationTurn(state, "hero-1", STEPS)).toEqual({ kind: "other", name: "가온" });
  });
});

describe("남은 개수로 배정 가능한 값을 고른다 (G-12.3-6)", () => {
  // 이 숫자 여섯(2, 1, 1, 0, 0, -1)은 **시험 재료**다 — 던전월드류가 실제로
  // 내려주는 값이지만 제품 코드의 상수가 아니다(실제로는 GET /creation/steps의
  // fixed_values로 온다). 지금까지 이 모양(같은 값이 둘 이상인 풀)을 쓰는 시험이
  // 하나도 없어서, 이 결함이 여섯 라운드의 코드 검증과 81건의 화면 시험을 살아남았다
  // — 서로 다른 값만 쓰는 풀에서는 「집합」과 「개수」가 정확히 같은 답을 낸다.
  const POOL = [2, 1, 1, 0, 0, -1];
  const AXIS_NAMES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];

  it("같은 값이 둘 있는 풀에서 하나를 쓰면 나머지 하나가 남는다", () => {
    const assignment: Record<string, number | null> = {
      STR: 1,
      DEX: null,
      CON: null,
      INT: null,
      WIS: null,
      CHA: null,
    };
    const remaining = remainingFixedValues(POOL, assignment);
    expect(remaining.get(1)).toBe(1);
  });

  it("값 여섯 개를 여섯 칸에 전부 배정하고 확정까지 간다", () => {
    const assignment: Record<string, number | null> = Object.fromEntries(
      AXIS_NAMES.map((name) => [name, null]),
    );
    for (let i = 0; i < AXIS_NAMES.length; i++) {
      const axisName = AXIS_NAMES[i];
      const valueToAssign = POOL[i];
      const remaining = remainingFixedValues(POOL, assignment);
      expect(remaining.get(valueToAssign)).toBeGreaterThan(0);
      assignment[axisName] = valueToAssign;
    }
    expect(Object.values(assignment).every((value) => value !== null)).toBe(true);
    const finalRemaining = remainingFixedValues(POOL, assignment);
    for (const value of POOL) {
      expect(finalRemaining.get(value)).toBe(0);
    }
  });

  it("풀에 하나뿐인 값은 여전히 한 칸에만 쓸 수 있다", () => {
    const assignment: Record<string, number | null> = {
      STR: 2,
      DEX: null,
      CON: null,
      INT: null,
      WIS: null,
      CHA: null,
    };
    const remaining = remainingFixedValues(POOL, assignment);
    expect(remaining.get(2)).toBe(0);
  });
});

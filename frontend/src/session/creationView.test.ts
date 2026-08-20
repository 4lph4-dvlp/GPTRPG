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
} from "../api/types.ts";
import {
  canEdit,
  type CreationStepRow,
  creationErrorMessage,
  creationRollsFrom,
  gmLinesFrom,
  isMyTurn,
  myStepValues,
  nextUnfilledStep,
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

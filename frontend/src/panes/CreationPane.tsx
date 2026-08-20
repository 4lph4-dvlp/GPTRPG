/**
 * 만들기 대화판 — 대화 줄기 하나 안에서 자기소개가 일어난다(D-06).
 *
 * `ChatPane.tsx`의 상태 관리 패턴(`busy`/`status`/오류 문구 고르기)을
 * 복제하되 **`ChatPane.tsx` 자체는 고치지 않는다** — 그 파일은 판정 턴을
 * 묶는 로직(`groupTurns.ts`)에 붙어 있어서 만들기 대화를 억지로 끼우면 두
 * 흐름이 서로를 망가뜨린다. 두 판의 생김새를 합칠지는 Phase 16이 정한다.
 *
 * 판이 그리는 것(위에서 아래로 하나의 줄기):
 *  · **대화 줄기** — GM의 말(`creation_gm_spoke`)과 끼어든 말
 *    (`creation_interjection`)을 `seq` 순서로 섞어 그린다.
 *  · **끼어들기 입력** — 남의 차례에도 항상 열려 있다(D-08). 항목을
 *    확정하는 조작만 자기 차례에 뜬다.
 *  · **항목 목록 + 「고치기」** — 확정한 항목이 목록으로 보이고, 내 차례인
 *    동안에는 아무 항목이나 다시 열 수 있다(D-09). 「고치기」는 새 경로가
 *    아니다 — 같은 `step_id`로 `completeCreationStep`을 다시 내는 것이
 *    곧 되돌리기다(서버가 나중 값으로 덮는다).
 *  · **항목 조작** — 지금 채워야 할 항목(다음 미완료 필수 항목, 또는
 *    「고치기」로 다시 연 항목) 하나의 입력이 대화 줄기 바로 아래 뜬다.
 *  · **되묻기 관문(D-14)** — 필수 항목이 전부 채워지면 「진행자에게
 *    물어보기」가 뜬다. GM이 되묻기를 포기해도(`needs_more: false`) 사람이
 *    「더 말하기 / 이걸로 끝」을 고른다 — 이 선택은 **말할 기회**를 여는
 *    것이지 값을 정하는 일이 아니다.
 *
 * **판단은 서버 한 자리에만(D-04).** 이 파일은 `stepRows`/`isMyTurn`/
 * `canEdit`/`nextUnfilledStep`(`session/creationView.ts`)이 이미 고른
 * 값을 그리기만 한다 — 「누가 아직 안 끝났나」・「최소선이 채워졌나」를
 * 다시 계산하지 않는다. 화면의 비활성화(배분 합계·다중집합 검사 등)는
 * **헛걸음 줄이기**일 뿐이고, 판정의 권위는 항상 서버다(T-12.3-17) —
 * 서버가 같은 규칙을 다시 본다.
 */

import { useEffect, useRef, useState } from "react";
import {
  completeCreation,
  completeCreationStep,
  creationFollowUp,
  recordInterjection,
} from "../api/client.ts";
import type { CompleteCreationStepBody } from "../api/client.ts";
import type {
  CreationCharacterView,
  CreationStepValueView,
  CreationStepView,
  GameEvent,
  GameStateView,
} from "../api/types.ts";
import { COPY, statLabel } from "../labels.ts";
import { MAX_RAW_TEXT_LEN } from "../config.ts";
import {
  canEdit,
  type CreationStepRow,
  creationErrorMessage,
  gmLinesFrom,
  isMyTurn,
  nextUnfilledStep,
  stepRows,
} from "../session/creationView.ts";

interface CreationPaneProps {
  sessionId: string;
  browserId: string;
  myCharacterId: string;
  rulebookId: string;
  state: GameStateView;
  events: GameEvent[];
  steps: CreationStepView[];
  pollNow: () => void;
}

interface ConversationLine {
  seq: number;
  speaker: string;
  text: string;
}

/** GM의 말 + 끼어든 말을 seq 순서로 섞어 하나의 줄기로 편다. 누가
 * 말했는지: GM은 「진행자」로, 사람은 `creation_characters`의
 * `display_name`으로, 아직 완성 전이라 이름이 없으면 그 사람의
 * `character_id`로 붙인다. */
function conversationLines(
  events: GameEvent[],
  characters: CreationCharacterView[],
): ConversationLine[] {
  const nameById = new Map(characters.map((character) => [character.character_id, character.display_name]));
  const lines: ConversationLine[] = [];
  for (const line of gmLinesFrom(events)) {
    lines.push({ seq: line.seq, speaker: "진행자", text: line.say });
  }
  for (const event of events) {
    if (event.event_type !== "creation_interjection") {
      continue;
    }
    lines.push({
      seq: event.seq,
      speaker: nameById.get(event.speaker_character_id) ?? event.speaker_character_id,
      text: event.text,
    });
  }
  return lines.sort((a, b) => a.seq - b.seq);
}

/** 확정된 항목 값을 목록 줄 하나에 보여줄 요약 문자열로 바꾼다. */
function stepValueSummary(value: CreationStepValueView): string {
  if (value.text_value !== null) {
    return value.text_value;
  }
  if (value.picked !== null) {
    return value.picked.join(", ");
  }
  if (value.axis_values !== null) {
    return value.axis_values.map(([axisName, amount]) => `${statLabel(axisName)} ${amount}`).join(" · ");
  }
  return "";
}

/**
 * 「이걸로 끝」을 누른 시점에 서버가 요구하는 `one_line_intro` 자리표시자다
 * — 실제로 화면에 남는 값이 아니다. 전원 완성 뒤 `wrap_up_creation`이
 * GM의 AI 정리로 이 값을 덮어쓴다(`routes_creation.py::wrap_up_creation`).
 * 여기서 새 AI 호출을 만들지 않는다 — `provides_display_name` 항목의
 * 값을 그대로 쓴다(서버 `_fallback_intro_for`가 첫 문장을 못 찾았을 때
 * 쓰는 것과 같은 최소값).
 */
function fallbackIntro(rows: CreationStepRow[], myCharacterId: string): string {
  const nameRow = rows.find((row) => row.step.provides_display_name);
  const name = nameRow?.value?.text_value;
  return name !== null && name !== undefined && name.length > 0 ? name : myCharacterId;
}

type StepSubmitPayload = Pick<CompleteCreationStepBody, "text_value" | "picked" | "axis_values">;

interface ControlProps {
  row: CreationStepRow;
  busy: boolean;
  onSubmit: (payload: StepSubmitPayload) => void;
}

function FreeTextControl({ row, busy, onSubmit }: ControlProps) {
  const [value, setValue] = useState(row.value?.text_value ?? "");
  return (
    <div className="composer__row">
      <textarea
        className="composer__input"
        value={value}
        maxLength={MAX_RAW_TEXT_LEN}
        disabled={busy}
        placeholder={row.step.label}
        aria-label={row.step.label}
        onChange={(event) => setValue(event.target.value)}
      />
      <button
        type="button"
        className="btn btn--primary"
        disabled={busy || value.trim().length === 0}
        onClick={() => onSubmit({ text_value: value.trim() })}
      >
        확정
      </button>
    </div>
  );
}

function PickOneControl({ row, busy, onSubmit }: ControlProps) {
  return (
    <div className="proposal">
      <p className="t-caps">{row.step.label}</p>
      {(row.step.options ?? []).map((option) => (
        <button
          type="button"
          className="candidate"
          key={option}
          disabled={busy}
          onClick={() => onSubmit({ picked: [option] })}
        >
          <span className="candidate__move">{option}</span>
        </button>
      ))}
    </div>
  );
}

function PlaceFixedValuesControl({ row, busy, onSubmit }: ControlProps) {
  const axisNames = row.step.axis_names;
  const fixedValues = row.step.fixed_values ?? [];
  const [assignment, setAssignment] = useState<Record<string, number | null>>(() => {
    const initial: Record<string, number | null> = Object.fromEntries(
      axisNames.map((name) => [name, null]),
    );
    for (const [axisName, value] of row.value?.axis_values ?? []) {
      if (axisName in initial) {
        initial[axisName] = value;
      }
    }
    return initial;
  });
  const usedValues = new Set(
    Object.values(assignment).filter((value): value is number => value !== null),
  );
  const complete = axisNames.every((name) => assignment[name] !== null);
  return (
    <div className="proposal">
      <p className="t-caps">{row.step.label}</p>
      {axisNames.map((axisName) => (
        <label className="composer__row" key={axisName}>
          <span className="t-label">{statLabel(axisName)}</span>
          <select
            value={assignment[axisName] ?? ""}
            disabled={busy}
            onChange={(event) => {
              const next = event.target.value === "" ? null : Number(event.target.value);
              setAssignment((previous) => ({ ...previous, [axisName]: next }));
            }}
          >
            <option value="">—</option>
            {fixedValues.map((value) => (
              <option key={value} value={value} disabled={usedValues.has(value) && assignment[axisName] !== value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      ))}
      <button
        type="button"
        className="btn btn--primary btn--wide"
        disabled={busy || !complete}
        onClick={() =>
          onSubmit({
            axis_values: axisNames.map((name) => ({ axis_name: name, value: assignment[name] as number })),
          })
        }
      >
        확정
      </button>
    </div>
  );
}

function AllocatePointsControl({ row, busy, onSubmit }: ControlProps) {
  const axisNames = row.step.axis_names;
  const budget = row.step.point_budget ?? 0;
  const perTargetMax = row.step.per_target_max;
  const [amounts, setAmounts] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = Object.fromEntries(axisNames.map((name) => [name, 0]));
    for (const [axisName, value] of row.value?.axis_values ?? []) {
      if (axisName in initial) {
        initial[axisName] = value;
      }
    }
    return initial;
  });
  const total = Object.values(amounts).reduce((sum, value) => sum + value, 0);
  const remaining = budget - total;
  // 화면의 비활성화는 헛걸음을 줄일 뿐이다 — 서버가 같은 규칙(합계 ==
  // 예산, 항목별 상한)을 다시 본다(T-12.3-17).
  const overCap = perTargetMax !== null && axisNames.some((name) => amounts[name] > perTargetMax);
  return (
    <div className="proposal">
      <p className="t-caps">{row.step.label}</p>
      <p className="t-label">
        {COPY.creationBudgetLeft} {remaining}
        {perTargetMax !== null ? ` · 항목당 최대 ${perTargetMax}` : ""}
      </p>
      {axisNames.map((axisName) => (
        <label className="composer__row" key={axisName}>
          <span className="t-label">{statLabel(axisName)}</span>
          <input
            type="number"
            min={0}
            max={perTargetMax ?? undefined}
            value={amounts[axisName]}
            disabled={busy}
            onChange={(event) => {
              const next = Number(event.target.value);
              setAmounts((previous) => ({ ...previous, [axisName]: Number.isNaN(next) ? 0 : next }));
            }}
          />
        </label>
      ))}
      <button
        type="button"
        className="btn btn--primary btn--wide"
        disabled={busy || remaining !== 0 || overCap}
        onClick={() =>
          onSubmit({ axis_values: axisNames.map((name) => ({ axis_name: name, value: amounts[name] })) })
        }
      >
        확정
      </button>
    </div>
  );
}

function RollToFillControl({ row, busy, onSubmit }: ControlProps) {
  return (
    <div className="proposal">
      <p className="t-caps">{row.step.label}</p>
      {/* 브라우저가 눈을 만들어 보내지 않는다 — 서버가 주입된 Roller로
          직접 굴린다(D-07, 12.1 D-04). axis_values를 여기 싣지 않는다. */}
      <button type="button" className="btn btn--primary btn--wide" disabled={busy} onClick={() => onSubmit({})}>
        {COPY.creationRoll}
      </button>
    </div>
  );
}

function StepControl({ row, busy, onSubmit }: ControlProps) {
  switch (row.step.kind) {
    case "free_text":
      return <FreeTextControl row={row} busy={busy} onSubmit={onSubmit} />;
    case "pick_one":
      return <PickOneControl row={row} busy={busy} onSubmit={onSubmit} />;
    case "place_fixed_values":
      return <PlaceFixedValuesControl row={row} busy={busy} onSubmit={onSubmit} />;
    case "allocate_points":
      return <AllocatePointsControl row={row} busy={busy} onSubmit={onSubmit} />;
    case "roll_to_fill":
      return <RollToFillControl row={row} busy={busy} onSubmit={onSubmit} />;
    case "derive":
      // 조작이 없다 — 부모의 자동 확정 effect가 depends_on 충족 시
      // completeCreationStep을 스스로 부른다. 부모가 kind==="derive"인
      // activeRow에는 이 컴포넌트를 아예 그리지 않으므로 여기 닿지 않는다.
      return null;
    case "pick_many":
      // 세 룰북 중 아무도 안 쓴다(12.3-CONTEXT §Claude's Discretion) —
      // 입력칸을 만들지 않는다. 조용히 빈 칸을 보이지 않고 문구로 알린다.
      return <p className="t-label">{COPY.creationStepKindUnsupported}</p>;
    default: {
      // 여기 도달하면 CreationStepKind에 새 kind가 추가됐는데 이 switch가
      // 못 따라간 것이다 — tsc가 컴파일 시점에 잡는다(never 대입).
      const exhaustiveCheck: never = row.step.kind;
      return exhaustiveCheck;
    }
  }
}

function InterjectBox({
  sessionId,
  browserId,
  myCharacterId,
  duringCharacterId,
  pollNow,
  onError,
}: {
  sessionId: string;
  browserId: string;
  myCharacterId: string;
  duringCharacterId: string;
  pollNow: () => void;
  onError: (message: string) => void;
}) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);

  async function send(): Promise<void> {
    const trimmed = text.trim();
    if (trimmed.length === 0 || sending) {
      return;
    }
    setSending(true);
    try {
      await recordInterjection(sessionId, {
        speaker_character_id: myCharacterId,
        browser_id: browserId,
        during_character_id: duringCharacterId,
        mentioned_character_ids: [],
        text: trimmed,
      });
      setText("");
      pollNow();
    } catch (error) {
      onError(creationErrorMessage(error));
    } finally {
      setSending(false);
    }
  }

  return (
    <form
      className="composer__row"
      onSubmit={(event) => {
        event.preventDefault();
        void send();
      }}
    >
      <input
        className="composer__input"
        type="text"
        value={text}
        maxLength={MAX_RAW_TEXT_LEN}
        disabled={sending}
        placeholder={COPY.creationInterjectPlaceholder}
        aria-label={COPY.creationInterjectPlaceholder}
        onChange={(event) => setText(event.target.value)}
      />
      <button type="submit" className="btn btn--ghost" disabled={sending || text.trim().length === 0}>
        보내기
      </button>
    </form>
  );
}

type FollowUpPhase =
  | { kind: "idle" }
  | { kind: "asked_more" }
  | { kind: "ready_to_finish"; requiredStepsFilled: boolean };

export function CreationPane({
  sessionId,
  browserId,
  myCharacterId,
  rulebookId,
  state,
  events,
  steps,
  pollNow,
}: CreationPaneProps) {
  const myTurn = isMyTurn(state, myCharacterId);
  const rows = stepRows(steps, state, myCharacterId);
  const [editingStepId, setEditingStepId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [followUp, setFollowUp] = useState<FollowUpPhase>({ kind: "idle" });
  const submittedDeriveRef = useRef<Set<string>>(new Set());

  const conversation = conversationLines(events, state.creation_characters);

  async function submitStep(stepId: string, payload: StepSubmitPayload): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      await completeCreationStep(sessionId, {
        character_id: myCharacterId,
        browser_id: browserId,
        step_id: stepId,
        rulebook_id: rulebookId,
        ...payload,
      });
      setEditingStepId(null);
      pollNow();
    } catch (submitError) {
      setError(creationErrorMessage(submitError));
    } finally {
      setBusy(false);
    }
  }

  // derive 항목은 조작이 없다 — depends_on이 전부 채워지면 자동으로 한
  // 번 확정한다(계획 Task 2 ②). submittedDeriveRef는 폴링이 아직 새 값을
  // 반영하기 전에 같은 항목을 두 번 자동 제출하지 않게 막는다.
  useEffect(() => {
    if (!myTurn) {
      return;
    }
    for (const row of rows) {
      if (row.step.kind !== "derive" || row.filled) {
        continue;
      }
      if (submittedDeriveRef.current.has(row.step.step_id)) {
        continue;
      }
      const dependsFilled = row.step.depends_on.every(
        (depId) => rows.find((candidate) => candidate.step.step_id === depId)?.filled === true,
      );
      if (dependsFilled) {
        submittedDeriveRef.current.add(row.step.step_id);
        void submitStep(row.step.step_id, {});
      }
    }
  }, [rows, myTurn]);

  async function askGm(): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      const response = await creationFollowUp(sessionId, myCharacterId, rulebookId);
      setFollowUp(
        response.needs_more
          ? { kind: "asked_more" }
          : { kind: "ready_to_finish", requiredStepsFilled: response.required_steps_filled },
      );
      pollNow();
    } catch (askError) {
      setError(creationErrorMessage(askError));
    } finally {
      setBusy(false);
    }
  }

  async function finishCreation(): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      await completeCreation(sessionId, {
        character_id: myCharacterId,
        browser_id: browserId,
        rulebook_id: rulebookId,
        one_line_intro: fallbackIntro(rows, myCharacterId),
      });
      pollNow();
    } catch (finishError) {
      setError(creationErrorMessage(finishError));
    } finally {
      setBusy(false);
    }
  }

  function sayMore(): void {
    setFollowUp({ kind: "idle" });
    setEditingStepId(null);
  }

  const activeRow =
    editingStepId !== null
      ? (rows.find((row) => row.step.step_id === editingStepId) ?? null)
      : nextUnfilledStep(rows);

  const followUpGateVisible = myTurn && editingStepId === null && nextUnfilledStep(rows) === null;

  return (
    <section className="pane pane--chat">
      <p className="t-label">{myTurn ? COPY.creationMyTurn : COPY.creationOthersTurn}</p>

      <div className="chat">
        {conversation.length === 0 ? (
          <p className="t-label">{COPY.loading}</p>
        ) : (
          conversation.map((line) => (
            <div className="chat-line" key={line.seq}>
              <div className="chat-line__who">{line.speaker}</div>
              <div className="chat-line__text">{line.text}</div>
            </div>
          ))
        )}
      </div>

      {myTurn ? (
        <div>
          {rows.map((row) => (
            <div className="chat-line" key={row.step.step_id}>
              <div className="chat-line__who">{row.step.label}</div>
              <div className="chat-line__text t-label">
                {row.filled && row.value !== null
                  ? stepValueSummary(row.value)
                  : row.step.kind === "derive"
                    ? COPY.creationDerivedAuto
                    : ""}
              </div>
              {/* derive 항목은 조작이 없다 — 「고치기」를 눌러도 다시 낼 값을
                  입력할 방법이 없으므로 편집 버튼 자체를 그리지 않는다.
                  canEdit(row, myTurn)이 참이라는 사실 자체는 안 바뀐다 — D-09가
                  「아무 줄이나」를 요구하는 것이지, 편집 UI가 없는 kind까지
                  버튼을 강제하는 것은 아니다. */}
              {row.filled && row.step.kind !== "derive" && canEdit(row, myTurn) && editingStepId !== row.step.step_id ? (
                <button
                  type="button"
                  className="btn btn--ghost"
                  disabled={busy}
                  onClick={() => {
                    setEditingStepId(row.step.step_id);
                    setFollowUp({ kind: "idle" });
                  }}
                >
                  {COPY.creationEdit}
                </button>
              ) : null}
            </div>
          ))}

          {activeRow !== null && activeRow.step.kind !== "derive" ? (
            <div className="composer">
              <StepControl
                key={activeRow.step.step_id}
                row={activeRow}
                busy={busy}
                onSubmit={(payload) => void submitStep(activeRow.step.step_id, payload)}
              />
            </div>
          ) : null}

          {followUpGateVisible ? (
            <div className="proposal">
              {followUp.kind === "idle" ? (
                <button type="button" className="btn btn--primary btn--wide" disabled={busy} onClick={() => void askGm()}>
                  {COPY.creationAskGm}
                </button>
              ) : null}
              {followUp.kind === "asked_more" ? <p className="t-label">{COPY.creationGmSilent}</p> : null}
              {followUp.kind === "ready_to_finish" ? (
                <>
                  <p className="t-label">{COPY.creationGmSilent}</p>
                  <button type="button" className="btn btn--ghost btn--wide" disabled={busy} onClick={sayMore}>
                    {COPY.creationSayMore}
                  </button>
                  <button
                    type="button"
                    className="btn btn--primary btn--wide"
                    disabled={busy || !followUp.requiredStepsFilled}
                    onClick={() => void finishCreation()}
                  >
                    {COPY.creationDoneTalking}
                  </button>
                </>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      {error !== null ? <p className="t-label">{error}</p> : null}

      <InterjectBox
        sessionId={sessionId}
        browserId={browserId}
        myCharacterId={myCharacterId}
        duringCharacterId={state.creation_current_speaker_id ?? myCharacterId}
        pollNow={pollNow}
        onError={setError}
      />
    </section>
  );
}

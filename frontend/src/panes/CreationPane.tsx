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
 *  · **정리 요청 · 동의 관문(12.3-05 Task 2, D-03/D-11)** — 전원이
 *    완성되면(`creation_unfinished_character_ids`가 비었고
 *    `creation_characters`가 비어 있지 않으면) 「진행자에게 정리를
 *    부탁하기」가 뜬다. GM의 정리(`kind: "wrap_up"`)가 기록에 나타나면
 *    동의 관문으로 넘어간다 — `state.creation_characters`를 전부 줄로
 *    그리고 **이름**과 동의 여부를 보인다(D-03, 숫자만 보이지 않는다).
 *    「고칠 게 있어요」는 `recordCreationConsent(agree: false)`로 항목
 *    하나를 다시 열고, 그 순간부터는 `isMyTurn`이 아니어도(차례 지목은
 *    안 바뀐다) 그 항목만 다시 채울 수 있다.
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
  nominateCreationSpeaker,
  recordCreationConsent,
  recordInterjection,
  wrapUpCreation,
} from "../api/client.ts";
import type { CompleteCreationStepBody } from "../api/client.ts";
import type {
  CreationCharacterView,
  CreationStepValueView,
  CreationStepView,
  GameEvent,
  GameStateView,
} from "../api/types.ts";
import { COPY, creationTurnLabel, statLabel } from "../labels.ts";
import { MAX_RAW_TEXT_LEN } from "../config.ts";
import {
  canEdit,
  consentGate,
  type CreationStepRow,
  creationErrorMessage,
  creationTurn,
  gmLinesFrom,
  isMyTurn,
  nextUnfilledStep,
  pendingConsenters,
  remainingFixedValues,
  shouldNominateNext,
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
  /** 이 브라우저가 방을 연 사람인가(D-11) — 「진행자에게 정리를
   * 부탁하기」를 누가 보는지 정한다(G-12.3-16). */
  youAreHost: boolean;
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
  /** 쓰다 만 글을 판이 대신 들고 있는다(G-12.3-18).
   *
   * 자유 서술 입력칸은 `activeRow`가 사라지면 통째로 언마운트된다 —
   * 회복 시간(D-13)이 돌아 차례가 넘어가면 그 순간 일어난다. 지역
   * `useState`에 있던 글은 그때 사라지고, 차례가 돌아와도 빈 칸으로
   * 다시 뜬다. 실제 시험에서 마지막 참가자가 서사를 쓰는 도중 이걸
   * 당했다. 판이 항목별로 들고 있으면 언마운트를 넘긴다. */
  draft: string;
  onDraftChange: (text: string) => void;
}

function FreeTextControl({ row, busy, onSubmit, draft, onDraftChange }: ControlProps) {
  const value = draft;
  const setValue = onDraftChange;
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
  // 지웠던 것: 이미 쓴 값을 값의 **집합**으로 모으던 지역 변수(`usedValues`).
  // 같은 값이 둘 이상인 풀(예: 던전월드류 2, 1, 1, 0, 0, -1)에서는 집합이
  // 「그 값이 몇 개 남았는가」를 아예 세지 않아 하나를 쓰면 나머지도 함께
  // 잠기고, 서로 다른 값이 넷뿐이라 여섯 칸을 못 채워 「확정」이 영원히 안
  // 켜졌다(G-12.3-6). `remainingFixedValues`(시험된 순수 함수, session/
  // creationView.ts)가 개수 기반으로 다시 판정한다 — 서로 다른 값의 중복
  // 배정 방지는 사라지지 않고 **개수가 1인 경우**로 그대로 남는다. 마지막
  // 말은 여전히 서버다: 배치 묶음이 룰북 선언과 다중집합으로 같은지는
  // `actor.py::_prepare_complete_creation_step`이 검사한다(T-12.1-04) — 이
  // 판정은 사람이 불가능한 배치를 고르지 못하게 돕는 것일 뿐이다.
  const remaining = remainingFixedValues(fixedValues, assignment);
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
            {fixedValues.map((value, index) => (
              <option
                key={`${index}:${value}`}
                value={value}
                disabled={(remaining.get(value) ?? 0) <= 0 && assignment[axisName] !== value}
              >
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

function StepControl({ row, busy, onSubmit, draft, onDraftChange }: ControlProps) {
  switch (row.step.kind) {
    case "free_text":
      return (
        <FreeTextControl
          row={row}
          busy={busy}
          onSubmit={onSubmit}
          draft={draft}
          onDraftChange={onDraftChange}
        />
      );
    case "pick_one":
      return (
        <PickOneControl
          row={row}
          busy={busy}
          onSubmit={onSubmit}
          draft={draft}
          onDraftChange={onDraftChange}
        />
      );
    case "place_fixed_values":
      return (
        <PlaceFixedValuesControl
          row={row}
          busy={busy}
          onSubmit={onSubmit}
          draft={draft}
          onDraftChange={onDraftChange}
        />
      );
    case "allocate_points":
      return (
        <AllocatePointsControl
          row={row}
          busy={busy}
          onSubmit={onSubmit}
          draft={draft}
          onDraftChange={onDraftChange}
        />
      );
    case "roll_to_fill":
      return (
        <RollToFillControl
          row={row}
          busy={busy}
          onSubmit={onSubmit}
          draft={draft}
          onDraftChange={onDraftChange}
        />
      );
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
  myTurn,
  pollNow,
  onSent,
  onError,
}: {
  sessionId: string;
  browserId: string;
  myCharacterId: string;
  duringCharacterId: string;
  myTurn: boolean;
  pollNow: () => void;
  onSent: () => void;
  onError: (message: string) => void;
}) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  // 같은 입력칸이지만 자기 차례에는 「끼어들기」가 아니다(G-12.3-13).
  const placeholder = myTurn ? COPY.creationSpeakPlaceholder : COPY.creationInterjectPlaceholder;

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
      onSent();
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
        placeholder={placeholder}
        aria-label={placeholder}
        onChange={(event) => setText(event.target.value)}
      />
      <button type="submit" className="btn btn--ghost" disabled={sending || text.trim().length === 0}>
        보내기
      </button>
    </form>
  );
}

/** ChatPane/StoryPane과 같은 값 — 바닥에서 이만큼 안이면 「따라가는 중」으로 본다. */
const NEAR_BOTTOM_PX = 48;

type FollowUpPhase =
  | { kind: "idle" }
  /** 되물음을 한 번 받은 뒤. `question`은 GM이 실제로 물은 문장이고,
   * `null`이면 GM이 물러난 것(`needs_more: false`)이다 — 두 경우에 서로
   * 다른 문구를 쓴다. 어느 쪽이든 「더 말하기」와 「이걸로 끝」이 함께
   * 남는다: 갈래마다 길이 갈리면 한쪽이 막다른 골목이 된다(G-12.3-8). */
  | {
      kind: "asked";
      question: string | null;
      requiredStepsFilled: boolean;
      /** GM이 실제로 판단했는가 — 거짓이면 AI가 물러난 것이다. */
      gmAnswered: boolean;
    };

export function CreationPane({
  sessionId,
  browserId,
  myCharacterId,
  rulebookId,
  state,
  events,
  steps,
  youAreHost,
  pollNow,
}: CreationPaneProps) {
  const myTurn = isMyTurn(state, myCharacterId);
  const rows = stepRows(steps, state, myCharacterId);
  // 내 항목 중 지금 다시 열려 있는 것(D-11) — 동의 관문에서 「고칠 게
  // 있어요」로 연 것이다. isMyTurn과 무관하다: 동의 관문에 들어선 시점엔
  // 이미 아무도 「차례」가 아니다(creation_current_speaker_id는 지목이
  // 끝나면 null로 남는다) — 그래도 이 항목 하나는 다시 채울 수 있어야
  // D-11이 성립한다.
  const myReopenedRow = rows.find((row) => row.reopened) ?? null;
  const stepEditingEnabled = myTurn || myReopenedRow !== null;
  const [editingStepId, setEditingStepId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [followUp, setFollowUp] = useState<FollowUpPhase>({ kind: "idle" });

  // 대화판이 새 줄로 자동으로 내려간다 — `ChatPane.tsx`/`StoryPane.tsx`가
  // 이미 쓰는 것과 같은 배선이다. 여기 없어서 **자기 차례인 사람만** GM의
  // 되물음을 못 보는 결함이 났다(G-12.3-8): 자기 차례면 대화판 아래에
  // 항목 줄·입력칸·되물음 관문이 함께 그려져 `.chat`(flex:1)이 눌리고,
  // 가장 새 줄이 접힌 자리로 밀린다. 남의 차례인 사람은 그 블록이 없어
  // 같은 줄이 그대로 보였다.
  const chatRef = useRef<HTMLDivElement>(null);
  const pinnedRef = useRef(true);
  // 항목별로 쓰다 만 글(G-12.3-18). 확정하면 그 항목 것만 지운다.
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [reopenPickerOpen, setReopenPickerOpen] = useState(false);
  const [consentMessage, setConsentMessage] = useState<string | null>(null);
  const submittedDeriveRef = useRef<Set<string>>(new Set());

  const conversation = conversationLines(events, state.creation_characters);
  // gmLinesFrom(events)는 여기 한 번만 불러 wrappedUp/announced 둘 다
  // 이 결과에서 계산한다(12.3-06 Task 2 ③) — 같은 배열을 두 번 안 훑는다.
  const gmLines = gmLinesFrom(events);
  // 「kind: "wrap_up"」인 GM 말이 기록에 있는가 — 존재 여부만 본다(진행
  // 상태를 다시 계산하지 않는다, D-04). consentGate가 이 값과 state를
  // 조합해 네 갈래를 고른다.
  const wrappedUp = gmLines.some((line) => line.kind === "wrap_up");
  // 「kind: "announce"」인 GM 말이 기록에 있는가 — shouldNominateNext가
  // 요구하는 값이다(CHAR-06의 흐름이 안내부터 시작한다).
  const announced = gmLines.some((line) => line.kind === "announce");
  const consentPhase = consentGate(state, wrappedUp);

  async function submitStep(stepId: string, payload: StepSubmitPayload): Promise<void> {
    setBusy(true);
    setError(null);
    setConsentMessage(null);
    try {
      await completeCreationStep(sessionId, {
        character_id: myCharacterId,
        browser_id: browserId,
        step_id: stepId,
        rulebook_id: rulebookId,
        ...payload,
      });
      setEditingStepId(null);
      // 확정된 항목의 초안은 지운다 — 안 지우면 「고치기」로 다시 열
      // 때 서버에 확정된 값이 아니라 옛 초안이 뜬다(G-12.3-18).
      setDrafts((previous) => {
        const { [stepId]: _submitted, ...rest } = previous;
        return rest;
      });
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

  // CR-01(12.3-REVIEW.md) + 12.3-06(D-06 첫 지목 교착 gap) — GM이 아직
  // 아무도 지목하지 않았으면 자동으로 다음 차례를 지목해 달라고 부른다.
  // **`creation_unfinished_character_ids`(이미 항목을 낸 사람만 담는
  // 목록)를 조건으로도 의존성으로도 쓰지 않는다** — 그 목록만 보면
  // 완전히 새 세션에서는 아무도 항목을 낸 적이 없어 이 effect가 영원히
  // 안 돈다(12.3-VERIFICATION.md 2차가 실제로 재현한 결함). 대신
  // `shouldNominateNext`(순수 함수, 시험됨)가 「완성 인원이 확정 인원
  // 미만이고 안내됐고 지목 없음」만 보고 판단한다. 여러 탭이 동시에 이
  // effect를 타도 서버의 `_gm_dedupe_key`(그 호출이 실제로 쓴 후보
  // 목록에서 나온 키)가 중복 지목을 막으므로(D-12/T-12.3-20) 안전하다 —
  // derive 자동 제출과 같은 자리, `nominatingRef`는 응답이 오기 전 같은
  // 요청을 두 번 겹쳐 보내지 않게만 막는다.
  const nominatingRef = useRef(false);
  useEffect(() => {
    if (!shouldNominateNext(state, announced) || nominatingRef.current) {
      return;
    }
    nominatingRef.current = true;
    void nominateCreationSpeaker(sessionId, rulebookId)
      .then(() => pollNow())
      .catch(() => undefined)
      .finally(() => {
        nominatingRef.current = false;
      });
    // party_roster 배열 자체는 의존성에 안 넣는다(폴링마다 새 참조라
    // effect가 매번 다시 돈다) — 재실 신호 effect(CreationScreen.tsx)의
    // 같은 규율을 그대로 따른다. null 여부만 shouldNominateNext 안에서 본다.
  }, [
    sessionId,
    rulebookId,
    announced,
    state.creation_current_speaker_id,
    state.party_size_fixed,
    state.party_roster !== null,
    state.creation_characters.length,
  ]);

  async function askGm(): Promise<void> {
    setBusy(true);
    setError(null);
    setConsentMessage(null);
    try {
      const response = await creationFollowUp(sessionId, myCharacterId, rulebookId);
      setFollowUp({
        kind: "asked",
        question: response.needs_more ? response.question : null,
        requiredStepsFilled: response.required_steps_filled,
        gmAnswered: response.gm_answered,
      });
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

  /** 「진행자에게 정리를 부탁하기」(Task 2 ①) — 넷이 동시에 눌러도
   * `wrap_up`의 `_gm_dedupe_key`가 AI를 한 번만 부른다(D-12). 화면이
   * 따로 잠그지 않는다. */
  async function askWrapUp(): Promise<void> {
    setBusy(true);
    setError(null);
    setConsentMessage(null);
    try {
      await wrapUpCreation(sessionId, rulebookId);
      pollNow();
    } catch (wrapUpError) {
      setError(creationErrorMessage(wrapUpError));
    } finally {
      setBusy(false);
    }
  }

  /** 동의 관문의 두 버튼이 부르는 자리(Task 2 ②) — `agree=false`면
   * `stepId`가 항상 함께 실린다(서버가 그것 없이는 400으로 거절한다).
   * 성공하면 서버가 보낸 `message`를 그대로 담아 둔다(D-15) — 화면이
   * 같은 뜻의 문장을 새로 짓지 않는다. */
  async function sendConsent(agree: boolean, stepId?: string): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      const response = await recordCreationConsent(sessionId, {
        character_id: myCharacterId,
        browser_id: browserId,
        agree,
        step_id: stepId,
      });
      setConsentMessage(response.message);
      setReopenPickerOpen(false);
      pollNow();
    } catch (consentError) {
      setError(creationErrorMessage(consentError));
    } finally {
      setBusy(false);
    }
  }

  const activeRow =
    editingStepId !== null
      ? (rows.find((row) => row.step.step_id === editingStepId) ?? null)
      : (myReopenedRow ?? (myTurn ? nextUnfilledStep(rows) : null));

  // 사람이 위로 올려 읽는 중이면 끌어내리지 않는다(near-bottom 가드) —
  // ChatPane과 같은 규율.
  useEffect(() => {
    const node = chatRef.current;
    if (node !== null && pinnedRef.current) {
      node.scrollTop = node.scrollHeight;
    }
  }, [conversation.length]);

  const followUpGateVisible = myTurn && editingStepId === null && nextUnfilledStep(rows) === null;

  // 대화판 첫 줄의 차례 문구(G-12.3-7) — 오늘은 아무도 지목되지 않은
  // 동안에도 「다른 사람의 차례예요」가 떠서 사람을 기다리게 만들었다.
  // 이제 판정이 `creationView.ts`의 시험된 순수 함수(`creationTurn`)에서
  // 오고, 「아무 차례도 아님」이면 이 줄 자체를 안 그린다.
  const turnLabel = creationTurnLabel(creationTurn(state, myCharacterId, steps));

  return (
    <section className="pane pane--chat">
      {turnLabel !== null ? <p className="t-label">{turnLabel}</p> : null}

      <div
        className="chat"
        ref={chatRef}
        onScroll={() => {
          const node = chatRef.current;
          if (node !== null) {
            pinnedRef.current =
              node.scrollHeight - node.scrollTop - node.clientHeight <= NEAR_BOTTOM_PX;
          }
        }}
      >
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

      {stepEditingEnabled ? (
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
                draft={
                  drafts[activeRow.step.step_id] ?? activeRow.value?.text_value ?? ""
                }
                onDraftChange={(text) =>
                  setDrafts((previous) => ({ ...previous, [activeRow.step.step_id]: text }))
                }
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
              {followUp.kind === "asked" ? (
                <>
                  {followUp.question !== null ? (
                    <>
                      <p className="t-body">{followUp.question}</p>
                      <p className="t-label">{COPY.creationAnswerBelow}</p>
                    </>
                  ) : (
                    <p className="t-label">
                      {followUp.gmAnswered ? COPY.creationGmNothingMore : COPY.creationGmSilent}
                    </p>
                  )}
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

      {consentPhase === "needs_wrap_up" ? (
        <div className="proposal">
          {/* 방을 연 사람에게만 단추를 준다(G-12.3-16). 서버는 누가 불러도
              받고 D-12가 AI를 한 번으로 접지만, 모두에게 같은 단추가 뜨면
              「전원이 눌러야 하나」로 읽힌다 — 한 사람의 일이라는 것이
              화면에 드러나야 한다. */}
          {youAreHost ? (
            <button
              type="button"
              className="btn btn--primary btn--wide"
              disabled={busy}
              onClick={() => void askWrapUp()}
            >
              {COPY.creationAskWrapUp}
            </button>
          ) : (
            <p className="t-label">{COPY.creationWrapUpWaiting}</p>
          )}
        </div>
      ) : null}

      {consentPhase === "open" ? (
        <div className="proposal">
          <p className="t-caps">{COPY.creationConsentTitle}</p>
          {pendingConsenters(state).length > 0 ? (
            <p className="t-label">
              {COPY.creationConsentPending}: {pendingConsenters(state).join(", ")}
            </p>
          ) : null}
          {state.creation_characters.map((character) => (
            <div className="chat-line" key={character.character_id}>
              <div className="chat-line__who">{character.display_name}</div>
              <div className="chat-line__text t-label">
                {character.consented ? COPY.creationConsentDone : COPY.creationConsentPending}
              </div>
              {character.character_id === myCharacterId ? (
                reopenPickerOpen ? (
                  <div>
                    <p className="t-label">{COPY.creationPickStepToReopen}</p>
                    {rows.map((row) => (
                      <button
                        type="button"
                        className="btn btn--ghost"
                        key={row.step.step_id}
                        disabled={busy}
                        onClick={() => void sendConsent(false, row.step.step_id)}
                      >
                        {row.step.label}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="composer__row">
                    {/* 이미 동의했으면 다시 눌리지 않는다(G-12.3-17) —
                        예전에는 눌러도 같은 모양이라 「계속 눌러야 하나」로
                        헷갈렸다. 「아니요」는 살려 둔다: 마음이 바뀌면
                        항목을 다시 열 수 있어야 한다(D-11). */}
                    <button
                      type="button"
                      className="btn btn--primary"
                      disabled={busy || character.consented}
                      onClick={() => void sendConsent(true)}
                    >
                      {character.consented ? COPY.creationConsentDone : COPY.creationConsentYes}
                    </button>
                    <button
                      type="button"
                      className="btn btn--ghost"
                      disabled={busy}
                      onClick={() => setReopenPickerOpen(true)}
                    >
                      {COPY.creationConsentNo}
                    </button>
                  </div>
                )
              ) : null}
            </div>
          ))}
          {consentMessage !== null ? <p className="t-label">{consentMessage}</p> : null}
        </div>
      ) : null}

      {error !== null ? <p className="t-label">{error}</p> : null}

      <InterjectBox
        sessionId={sessionId}
        browserId={browserId}
        myCharacterId={myCharacterId}
        duringCharacterId={state.creation_current_speaker_id ?? myCharacterId}
        myTurn={myTurn}
        pollNow={pollNow}
        onSent={() => {
          // 되물음을 받은 상태에서 말을 하나 했으면 그 답을 GM에게
          // 전한다(G-12.3-13) — 서버의 중복방지 키가 이 말로 이미
          // 바뀌었으므로 같은 질문이 아니라 새 판단이 온다.
          if (myTurn && followUp.kind === "asked") {
            void askGm();
          }
        }}
        onError={setError}
      />
    </section>
  );
}

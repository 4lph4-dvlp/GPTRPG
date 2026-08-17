/**
 * 우측 — 플레이어 발화와 입력.
 *
 * 행동을 낸 사람도 다른 세 명과 똑같이 폴링으로 결과를 본다 — 이 파일은 확인
 * 응답을 받아도 이야기를 직접 그리지 않는다. 렌더 경로가 둘이 되면 행동한
 * 사람과 구경한 사람이 서로 다른 화면을 보게 된다.
 *
 * **확인 버튼을 누르는 것만이 판정으로 가는 유일한 통로다** — `tier === "unclear"`
 * 에서는 확인 버튼을 아예 만들지 않는다(T-04-25). `tier === "no_check"`는
 * 판정으로 가는 통로가 아니라 **판정 없이 이야기가 이어지는 통로**다(D-10
 * ②갈래, 11-06) — 여기도 사람이 버튼 하나를 눌러야 넘어간다는 점은 같지만
 * (D-10 결정 2, AI 호출 비용 통제 + "사람이 누른 것만 서사로 간다"는 이
 * 파일의 기존 규율), 그 버튼은 `proceed()`를 부르지 `confirmAction`을
 * 부르지 않는다. `unclear`/`no_check`는 D-11(11-05)이 옛 tier 값 하나를
 * 갈라서 만들었다(`api/types.ts`의 `DeclareResponse.tier` 주석 참조).
 *
 * 꼬리표는 **사건이 있을 때만** 붙인다. 남이 선언만 하고 아직 확인하지 않은
 * 줄에 "판정 대기" 같은 말을 지어내지 않는다 — 그건 내 브라우저가 알 수 없는
 * 사실이고, 화면이 모르는 것을 아는 척하면 안 된다.
 */

import { useEffect, useRef, useState } from "react";
import { ApiError, confirmAction, declareAction, proceed } from "../api/client.ts";
import type { DeclareResponse, ModifierView, MoveCandidate } from "../api/types.ts";
import { CheckBreakdown } from "../components/CheckBreakdown.tsx";
import { MAX_RAW_TEXT_LEN } from "../config.ts";
import { COPY, moveLabel, statLabel } from "../labels.ts";
import type { Turn } from "../session/groupTurns.ts";

/** `resolve()`가 만든 방금 판정의 검산 재료(D-04) — `CheckBreakdown`에
 * 그대로 넘긴다. `ConfirmResponse.rolls`가 `null`이 아닐 때만(=판정이 실제로
 * 있었을 때만) 만들어진다. */
interface CheckBreakdownData {
  rolls: number[];
  modifiers: ModifierView[];
  target: number | null;
}

const NEAR_BOTTOM_PX = 48;

interface ChatPaneProps {
  turns: Turn[];
  nameOf: (playerId: string) => string;
  sessionId: string;
  characterId: string;
  onTurnFailed: (declareSeq: number) => void;
  pollNow: () => void;
}

function tagFor(turn: Turn): { text: string; rejected: boolean } | null {
  if (turn.confirmed === null) {
    return null;
  }
  if (!turn.confirmed.player_confirmed) {
    return { text: COPY.reject, rejected: true };
  }
  return { text: moveLabel(turn.confirmed.move), rejected: false };
}

export function ChatPane({
  turns,
  nameOf,
  sessionId,
  characterId,
  onTurnFailed,
  pollNow,
}: ChatPaneProps) {
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<{ text: string; error: boolean } | null>(null);
  const [proposal, setProposal] = useState<DeclareResponse | null>(null);
  // D-04 — 방금 판정의 검산 표시. 판정이 없는 턴(no_check/unclear)에는 안 켠다.
  const [breakdown, setBreakdown] = useState<CheckBreakdownData | null>(null);

  const listRef = useRef<HTMLDivElement>(null);
  const pinnedRef = useRef(true);

  useEffect(() => {
    const node = listRef.current;
    if (node !== null && pinnedRef.current) {
      node.scrollTop = node.scrollHeight;
    }
  }, [turns.length]);

  function onListScroll() {
    const node = listRef.current;
    if (node !== null) {
      pinnedRef.current =
        node.scrollHeight - node.scrollTop - node.clientHeight <= NEAR_BOTTOM_PX;
    }
  }

  function messageFor(error: unknown): string {
    // 응답 본문을 그대로 화면에 쏟지 않는다 — 상태 코드별로 미리 정해진 문구만.
    return error instanceof ApiError && error.status === 503
      ? COPY.serverConfigFailed
      : COPY.turnFailed;
  }

  async function submit(): Promise<void> {
    const rawText = draft.trim();
    if (rawText.length === 0 || busy) {
      return;
    }
    setBusy(true);
    setProposal(null);
    setBreakdown(null);
    setStatus({ text: COPY.classifying, error: false });
    try {
      const response = await declareAction(sessionId, characterId, characterId, rawText);
      setDraft("");
      setProposal(response);
      setStatus(null);
      pollNow();
    } catch (error) {
      // 입력 칸 값을 지우지 않는다 — 사람이 다시 칠 필요가 없어야 한다.
      setStatus({ text: messageFor(error), error: true });
    } finally {
      setBusy(false);
    }
  }

  async function resolve(chosen: MoveCandidate, confirmed: boolean): Promise<void> {
    const pending = proposal;
    const suggestion = pending?.candidates[0];
    if (pending === null || suggestion === undefined) {
      return;
    }
    setProposal(null);
    setBusy(true);
    setStatus(confirmed ? { text: COPY.narrating, error: false } : null);
    try {
      const response = await confirmAction(
        sessionId,
        characterId,
        characterId,
        pending.declare_seq,
        chosen,
        suggestion,
        confirmed,
      );
      // 서사만 실패하면 응답은 200이지만 `narration_failed`가 참이다(TRUST-06,
      // D-08) — 판정 값은 이미 화면에 붙었으니(폴링) 이 실패는 조용히
      // 사라지면 안 된다. 이미 있는 실패 표시 경로를 그대로 탄다.
      if (response.narration_failed) {
        onTurnFailed(pending.declare_seq);
        setStatus({ text: COPY.narrationFailed, error: true });
      } else {
        setStatus(null);
      }
      // D-04 — 판정이 실제로 있었을 때만(굴릴 필요 없는 행동에는 rolls가
      // 없다) 검산 표시를 켠다. `total`은 서버 값을 안 쓴다(항상 null,
      // `ConfirmResponse.total` 참조) — `CheckBreakdown`이 rolls/modifiers로
      // 직접 다시 더한다.
      if (response.rolls !== null) {
        setBreakdown({
          rolls: response.rolls,
          modifiers: response.modifiers ?? [],
          target: response.target,
        });
      }
    } catch (error) {
      // 서사 실패는 이제 200이지만, 다른 실패(403·409·503 등)는 여전히
      // 예외로 온다 — 이 경로는 그대로 둔다.
      if (confirmed) {
        onTurnFailed(pending.declare_seq);
        setStatus({ text: messageFor(error), error: true });
      }
    } finally {
      setBusy(false);
      pollNow();
    }
  }

  async function proceedWithoutCheck(): Promise<void> {
    const pending = proposal;
    if (pending === null) {
      return;
    }
    setProposal(null);
    setBusy(true);
    setStatus({ text: COPY.narrating, error: false });
    try {
      const response = await proceed(sessionId, characterId, characterId, pending.declare_seq);
      // `confirmAction`의 `narration_failed` 처리와 같은 규칙(TRUST-06,
      // D-08) — 판정이 없는 경로에도 서사 실패는 조용히 사라지면 안 된다.
      if (response.narration_failed) {
        onTurnFailed(pending.declare_seq);
        setStatus({ text: COPY.narrationFailed, error: true });
      } else {
        setStatus(null);
      }
    } catch (error) {
      onTurnFailed(pending.declare_seq);
      setStatus({ text: messageFor(error), error: true });
    } finally {
      setBusy(false);
      pollNow();
    }
  }

  return (
    <section className="pane pane--chat">
      <div className="chat__head">
        <p className="t-caps">모두의 행동</p>
      </div>

      <div className="chat" ref={listRef} onScroll={onListScroll}>
        {turns.length === 0 ? (
          <p className="t-label">아직 아무도 행동하지 않았어요</p>
        ) : (
          turns.map((turn) => {
            const tag = tagFor(turn);
            const mine = turn.playerId === characterId;
            return (
              <div
                className={mine ? "chat-line chat-line--mine" : "chat-line"}
                key={turn.declareSeq}
              >
                <div className="chat-line__who">{nameOf(turn.playerId)}</div>
                <div className="chat-line__text">{turn.rawText}</div>
                {tag !== null ? (
                  <span
                    className={
                      tag.rejected ? "chat-line__tag chat-line__tag--rejected" : "chat-line__tag"
                    }
                  >
                    {tag.rejected ? "다시 씀" : `→ ${tag.text}`}
                  </span>
                ) : null}
              </div>
            );
          })
        )}
      </div>

      <div className="composer">
        {proposal !== null ? (
          <div className="proposal">
            {/* 세 갈래 — unclear(못 알아들었음, 다시 쓰기)와 no_check(굴릴
                필요 없음, 이대로 진행)는 11-06부터 서로 다른 화면이다
                (D-11, D-10). single/several만 후보 버튼을 그린다. */}
            {proposal.tier === "unclear" ? (
              <>
                <p className="t-label">{COPY.noActionRecognized}</p>
                <button
                  type="button"
                  className="btn btn--ghost btn--wide"
                  onClick={() => setProposal(null)}
                >
                  {COPY.reject}
                </button>
              </>
            ) : proposal.tier === "no_check" ? (
              <>
                <p className="t-label">{COPY.noCheckNeeded}</p>
                {/* 후보 버튼은 하나도 그리지 않는다 — no_check는 애초에
                    candidates가 빈 목록이다. 「다시 쓰기」도 함께 두지
                    않는다 — 정식 경로를 예외처럼 보이게 만들지 않기
                    위해서다(D-10 결정 2). */}
                <button
                  type="button"
                  className="btn btn--primary btn--wide"
                  disabled={busy}
                  onClick={() => void proceedWithoutCheck()}
                >
                  {COPY.proceedWithoutCheck}
                </button>
              </>
            ) : (
              <>
                <p className="t-caps">
                  {proposal.tier === "single" ? "이 판정으로 진행할까요" : "어느 쪽인가요"}
                </p>
                {proposal.candidates.slice(0, 3).map((candidate) => (
                  <button
                    type="button"
                    className="candidate"
                    key={`${candidate.move}-${candidate.stat}`}
                    disabled={busy}
                    onClick={() => void resolve(candidate, true)}
                  >
                    <span className="candidate__move">{moveLabel(candidate.move)}</span>
                    <span className="candidate__stat">{statLabel(candidate.stat)}</span>
                  </button>
                ))}
                <button
                  type="button"
                  className="btn btn--ghost btn--wide"
                  disabled={busy}
                  onClick={() => {
                    const suggestion = proposal.candidates[0];
                    if (suggestion !== undefined) {
                      // 거부도 확인 경로를 부른다 — 거부 기록이 "직접 찾아야 함"
                      // 사례의 근거가 된다.
                      void resolve(suggestion, false);
                    }
                  }}
                >
                  {COPY.reject}
                </button>
              </>
            )}
          </div>
        ) : null}

        {breakdown !== null ? (
          <CheckBreakdown
            rolls={breakdown.rolls}
            modifiers={breakdown.modifiers}
            target={breakdown.target}
          />
        ) : null}

        <form
          className="composer__row"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <input
            className="composer__input"
            type="text"
            value={draft}
            maxLength={MAX_RAW_TEXT_LEN}
            disabled={busy}
            placeholder="무엇을 하나요?"
            aria-label="행동을 문장으로 입력하세요"
            onChange={(event) => setDraft(event.target.value)}
          />
          <button
            type="submit"
            className="btn btn--primary"
            disabled={busy || draft.trim().length === 0}
          >
            보내기
          </button>
        </form>

        <div
          className={status?.error === true ? "composer__status composer__status--error" : "composer__status"}
          role="status"
          aria-live="polite"
        >
          {status !== null ? (
            <>
              {!status.error ? (
                <span className="dots">
                  <span />
                  <span />
                  <span />
                </span>
              ) : null}
              {status.text}
            </>
          ) : null}
        </div>
      </div>
    </section>
  );
}

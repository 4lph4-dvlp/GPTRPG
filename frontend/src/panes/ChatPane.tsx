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
import {
  ApiError,
  confirmAction,
  confirmResourceChange,
  declareAction,
  proceed,
} from "../api/client.ts";
import type { DeclareResponse, MoveCandidate, PendingResourceChangeView } from "../api/types.ts";
import { CheckBreakdown } from "../components/CheckBreakdown.tsx";
import { MAX_RAW_TEXT_LEN } from "../config.ts";
import { COPY, moveLabel, resourceOperationLabel, statLabel } from "../labels.ts";
import type { CheckSummary } from "../session/checkSummary.ts";
import { buildCheckSummaryFromConfirmResponse } from "../session/checkSummary.ts";
import type { Turn } from "../session/groupTurns.ts";

/** 확인을 기다리는 자원 변화 묶음(D-09/D-10) — `causedBySeq`는 이번 판정의
 * `resolve_seq`다. `confirm-resource-change`가 이 값으로 멱등성 창을 연다. */
interface PendingResourceChangeState {
  causedBySeq: number;
  changes: PendingResourceChangeView[];
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
  const [breakdown, setBreakdown] = useState<CheckSummary | null>(null);
  // D-09/D-10 — 숫자가 실제로 변할 때만 뜨는 확인 카드. 빈 목록이면 아예 안 켠다.
  const [pendingChange, setPendingChange] = useState<PendingResourceChangeState | null>(null);
  const [resourceBusy, setResourceBusy] = useState(false);
  const [resourceStatus, setResourceStatus] = useState<{ text: string; error: boolean } | null>(
    null,
  );

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
      // 서사가 실패하면 응답은 200이지만 `turn_voided`가 참이다(판 15,
      // TRUST-06/D-08 보완) — 이 턴 전체가 자동으로 되돌려졌다는 뜻이다.
      // `onTurnFailed`(클라이언트 쪽 표시)는 부르지 않는다 — 되돌림 표시의
      // 진짜 근거는 폴링으로 오는 `turn_voided` 사건(`groupTurns.ts`가
      // `Turn.voided`로 접는다)이고, 이 상태 문구는 지금 이 요청을 보낸
      // 사람에게만 즉시 보여줄 안내일 뿐이다.
      if (response.turn_voided) {
        setStatus({ text: COPY.turnVoided, error: true });
      } else {
        setStatus(null);
      }
      // D-04 — 판정이 실제로 있었을 때만(굴릴 필요 없는 행동에는 rolls가
      // 없다) 검산 표시를 켠다. `buildCheckSummaryFromConfirmResponse`
      // 하나가 「서버가 준 것을 어떻게 읽는가」를 정하고(D-14), 이 함수는
      // 값을 옮겨 담기만 한다 — 계산은 없다.
      if (response.rolls !== null && response.grade !== null && response.target !== null) {
        setBreakdown(
          buildCheckSummaryFromConfirmResponse({
            rolls: response.rolls,
            modifiers: response.modifiers ?? [],
            target: response.target,
            grade: response.grade,
            calculation: response.calculation ?? null,
          }),
        );
      }
      // D-09/D-10 — 숫자가 실제로 변할 때만 확인 카드를 켠다. 빈 목록이면
      // 판정마다 확인 창이 뜨는 것을 막는 서버 쪽 절반(`NO_CHANGE_CATEGORY_ID`)의
      // 화면 쪽 절반이다.
      const changes = response.pending_resource_changes ?? [];
      if (changes.length > 0 && response.resolve_seq !== null) {
        setResourceStatus(null);
        setPendingChange({ causedBySeq: response.resolve_seq, changes });
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

  /**
   * 확인 카드에서 「그대로 반영」/「반영 안 함」을 눌렀을 때(D-09/D-10).
   * `categoryIds`는 `pending_resource_changes`에 실렸던 식별자를 중복 없이
   * 되돌려 보낸다 — 서버가 `ordered_categories`로 다시 대조한다. 변화량
   * 숫자는 이 함수 어디에도 없다(T-12-26).
   */
  async function resolveResourceChange(confirmed: boolean): Promise<void> {
    const pending = pendingChange;
    if (pending === null || resourceBusy) {
      return;
    }
    const categoryIds = [...new Set(pending.changes.map((change) => change.category_id))];
    setResourceBusy(true);
    try {
      await confirmResourceChange(
        sessionId,
        characterId,
        pending.causedBySeq,
        categoryIds,
        confirmed,
      );
      setPendingChange(null);
      setResourceStatus(null);
      // 시트를 다시 그리는 것은 이 함수 몫이 아니다 — `SessionScreen`이
      // `resource_changed` 사건을 폴링에서 보고 시트를 다시 부른다(RULE-06).
      // 여기서는 그 사건이 최대한 빨리 도착하게 다음 폴링을 앞당길 뿐이다.
      pollNow();
    } catch (error) {
      const forbidden = error instanceof ApiError && error.status === 403;
      setResourceStatus({
        text: forbidden ? COPY.resourceChangeForbidden : COPY.resourceChangeFailed,
        error: true,
      });
    } finally {
      setResourceBusy(false);
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
      // 이 경로에는 애초에 판정이 없어 `turn_voided` 사건 자체가 안 남는다
      // (`VoidTurn`을 제출할 대상이 없다, `web/routes_actions.py`의
      // `ProceedResponse.turn_voided` 도크스트링) — 그래서 `confirmAction`
      // 분기와 달리 폴링(사건)에 기댈 수 없고, 이 즉시 응답이 유일한
      // 신호다. `onTurnFailed`(클라이언트 쪽 표시, `TurnCard.failed`)를
      // 그대로 쓴다 — 판정이 없는 턴이므로 일반 실패 문구
      // (`COPY.turnFailed`)가 정확하다("주사위도 취소됐어요"는 여기서는
      // 성립하지 않는 말이다).
      if (response.turn_voided) {
        onTurnFailed(pending.declare_seq);
        setStatus({ text: COPY.turnFailed, error: true });
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

        {breakdown !== null ? <CheckBreakdown summary={breakdown} /> : null}

        {pendingChange !== null ? (
          <div className="proposal resource-confirm">
            <p className="t-caps">{COPY.resourceChangeHeading}</p>
            <ul className="resource-confirm__list">
              {pendingChange.changes.map((change, index) => (
                <li className="resource-confirm__item" key={`${change.axis}-${index}`}>
                  <span className="resource-confirm__axis">{statLabel(change.axis)}</span>
                  <span className="resource-confirm__op">
                    {resourceOperationLabel(change.operation)} {change.amount_decl}
                  </span>
                </li>
              ))}
            </ul>
            <button
              type="button"
              className="btn btn--primary btn--wide"
              disabled={resourceBusy}
              onClick={() => void resolveResourceChange(true)}
            >
              {COPY.resourceChangeApply}
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--wide"
              disabled={resourceBusy}
              onClick={() => void resolveResourceChange(false)}
            >
              {COPY.resourceChangeDecline}
            </button>
            {resourceStatus !== null ? (
              <div
                className={
                  resourceStatus.error
                    ? "composer__status composer__status--error"
                    : "composer__status"
                }
                role="status"
                aria-live="polite"
              >
                {resourceStatus.text}
              </div>
            ) : null}
          </div>
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

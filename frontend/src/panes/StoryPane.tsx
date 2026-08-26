/**
 * 중앙 — 이야기.
 *
 * 사건을 시간순 한 줄로 펴지 않고 **턴 단위 카드**로 쌓는다. 두 사람이 동시에
 * 확인 버튼을 눌러도 카드 두 장이 각자 채워지므로 두 이야기가 문장 단위로
 * 섞이지 않는다(docs/PIPELINE.md §9-8이 지적한 문제).
 *
 * 자동 스크롤: 바닥 근처에 있을 때만 따라 내려간다. 위로 올려 읽는 중이면
 * 화면을 빼앗지 않고 대신 "새 소식 N" 알약을 띄운다 — 놓치게 두지도, 뺏지도
 * 않는 절충이다.
 */

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { OpeningCard } from "../components/OpeningCard.tsx";
import { TurnCard } from "../components/TurnCard.tsx";
import { Waiting } from "../components/Waiting.tsx";
import type { CheckCalculationView, ClockAdvancedEvent, SceneOpenedEvent } from "../api/types.ts";
import { COPY } from "../labels.ts";
import { isVisibleTurn, type Turn } from "../session/groupTurns.ts";

const NEAR_BOTTOM_PX = 48;

/**
 * 위협 시계가 왜 돌았는지를 사건이 실어 보낸 `trigger` 그대로 옮긴다.
 *
 * 2026-08-18 플레이테스트 회귀 — 여기가 원래 실패 문구 하나로 박혀 있어서,
 * 조건으로 돈 시계에도 「판정 실패가 쌓여」가 나왔다. 완전 성공을 한
 * 플레이어에게 "네가 실패해서 나빠졌다"고 말하는 셈이라 이유를 안 보여주는
 * 것보다 나빴다.
 *
 * `switch`에 기본 갈래를 두지 않는다 — `trigger`가 닫힌 세 값이므로, 넷째
 * 값이 생기면 이 함수가 타입 검사에서 걸려야 한다(조용히 실패 문구로
 * 떨어지는 것이 정확히 이 결함의 모양이었다).
 */
export function clockAdvanceReason(trigger: ClockAdvancedEvent["trigger"]): string {
  switch (trigger) {
    case "fail_counter":
      return COPY.clockAdvancedByFailCounter;
    case "condition":
      return COPY.clockAdvancedByCondition;
    case "ai_choice":
      return COPY.clockAdvancedByAiChoice;
  }
}

interface StoryPaneProps {
  turns: Turn[];
  nameOf: (playerId: string) => string;
  segmentCount: number;
  justRevealedSeq: number | null;
  /** 판정이 없는 경로(proceed())에서 서사 요청 자체가 실패했다고 내
   * 브라우저가 아는 턴들 — 판 15부터 판정이 있는 경로는 `turn.voided`
   * (사건, 폴링으로 모두에게 온다)를 쓴다(`SessionScreen.tsx`의
   * `failedDeclareSeqs` 도크스트링 참조). 재시도 단추는 이제 없다 —
   * 63aef0c의 전제가 틀렸다는 정정 이후, 실패한 턴을 위해 시스템이
   * 더 하는 일은 없다.
   */
  failedDeclareSeqs: Set<number>;
  /** 판정 사건의 `seq`로 찾는 계산 줄(Phase 12.2) — `TurnCard`가 이것으로
   * 검산 줄을 그린다(자체 산수 없음). */
  calculations: Map<number, CheckCalculationView>;
  /**
   * 오프닝 사건(SCENE-01) — 폴링이 실어 온 `scene_opened`를 호출부가
   * 이미 찾아 둔 것이다. `StoryPane`은 이것을 다시 찾지 않는다(D-04,
   * 값이 한 자리에서만 계산된다).
   */
  opening: SceneOpenedEvent | null;
  /** 명단 잠금 직후 오프닝 호출이 도는 중인가(D-02, 자동 발동). */
  openingPending: boolean;
  /** 오프닝 요청 자체가 실패했을 때만 채워진다(D-09) — AI가 이상하게
   * 답한 갈래는 서버가 조용히 원문으로 대체하므로 여기 안 온다. */
  openingError: string | null;
  /** 오프닝 재시도 단추가 부르는 콜백. */
  onRetryOpening: () => void;
}

export function StoryPane({
  turns,
  nameOf,
  segmentCount,
  justRevealedSeq,
  failedDeclareSeqs,
  calculations,
  opening,
  openingPending,
  openingError,
  onRetryOpening,
}: StoryPaneProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const pinnedRef = useRef(true);
  const [unseen, setUnseen] = useState(0);
  const [unseenAlert, setUnseenAlert] = useState(false);

  const visible = turns.filter(isVisibleTurn);
  const clockCount = visible.filter((turn) => turn.clock !== null).length;
  const narrationCount = visible.reduce((sum, turn) => sum + turn.narration.length, 0);
  // 삽화는 판정·서사보다 몇 초 늦게 도착해 카드를 키운다. 이 수를 세지 않으면
  // 바닥에 붙어 있던 사람이 그림이 뜨는 순간 그만큼 위로 밀린다.
  const illustrationCount = visible.filter((turn) => turn.illustration !== null).length;
  const previousRef = useRef({ cards: 0, clocks: 0 });

  const scrollToBottom = () => {
    const node = scrollRef.current;
    if (node !== null) {
      node.scrollTop = node.scrollHeight;
    }
  };

  useLayoutEffect(() => {
    const previous = previousRef.current;
    const newCards = visible.length - previous.cards;
    const newClocks = clockCount - previous.clocks;
    previousRef.current = { cards: visible.length, clocks: clockCount };

    if (pinnedRef.current) {
      scrollToBottom();
      setUnseen(0);
      setUnseenAlert(false);
      return;
    }
    if (newCards > 0 || newClocks > 0) {
      setUnseen((count) => count + Math.max(0, newCards) + Math.max(0, newClocks));
      if (newClocks > 0) {
        setUnseenAlert(true);
      }
    }
    // narrationCount·illustrationCount는 카드 높이를 바꾸므로 의존성에 남긴다 —
    // 바닥에 붙어 있는 동안 문장이 늘거나 그림이 붙을 때도 따라 내려가야 한다.
    // 오프닝 카드도 같은 이유로 존재 여부를 의존성에 더한다 — 늦게 도착해
    // 카드 높이를 바꾸는데 이것을 안 세면 바닥에 붙어 있던 사람이 그만큼
    // 위로 밀린다. 「새 소식」 알약은 세지 않는다: 이미 화면에 있는 카드가
    // 자라는 것은 새로 온 소식이 아니다.
  }, [visible.length, clockCount, narrationCount, illustrationCount, opening !== null]);

  useEffect(() => {
    const node = scrollRef.current;
    if (node === null) {
      return;
    }
    const onScroll = () => {
      const nearBottom =
        node.scrollHeight - node.scrollTop - node.clientHeight <= NEAR_BOTTOM_PX;
      pinnedRef.current = nearBottom;
      if (nearBottom) {
        setUnseen(0);
        setUnseenAlert(false);
      }
    };
    node.addEventListener("scroll", onScroll, { passive: true });
    return () => node.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <main className="pane pane--story">
      <div className="story" ref={scrollRef}>
        <div className="story__inner">
          {opening !== null || visible.length > 0 ? (
            <>
              {/* 오프닝은 턴이 아니다 — `groupTurns`를 지나가지 않고 이야기
                  판 맨 위에 따로 그린다(D-01, `.turn__head`/`.turn__quote`
                  없는 변형). */}
              {opening !== null ? <OpeningCard text={opening.text} /> : null}
              {visible.map((turn, turnIndex) => (
                <div key={turn.declareSeq}>
                  <TurnCard
                    turn={turn}
                    actorName={nameOf(turn.playerId)}
                    isLatest={turnIndex === visible.length - 1}
                    justRevealed={justRevealedSeq === turn.check?.seq}
                    failed={failedDeclareSeqs.has(turn.declareSeq)}
                    imageUrl={turn.illustration?.image_path ?? null}
                    calculation={
                      turn.check === null ? null : (calculations.get(turn.check.seq) ?? null)
                    }
                  />
                  {turn.clock !== null ? (
                    <div
                      className="clock-banner"
                      style={{ marginTop: "var(--space-md)" }}
                      role="status"
                      aria-live="polite"
                    >
                      <span className="clock-banner__mark">◆</span>
                      <div>
                        <div className="clock-banner__text">
                          위협 시계가 {Math.min(turn.clock.segment_index, segmentCount)}/
                          {segmentCount}칸으로 넘어갔습니다
                        </div>
                        <div className="clock-banner__sub">
                          {clockAdvanceReason(turn.clock.trigger)}
                        </div>
                      </div>
                    </div>
                  ) : null}
                </div>
              ))}
            </>
          ) : openingPending ? (
            // 명단이 잠긴 뒤 오프닝 호출이 도는 동안(D-02) — 새 스피너·새
            // 애니메이션을 만들지 않고 기존 `Waiting`을 그대로 쓴다.
            <div className="empty">
              <Waiting label={COPY.openingWaiting} />
            </div>
          ) : openingError !== null ? (
            // 오프닝 API 요청 자체가 실패했을 때만 온다(D-09) — AI가
            // 이상하게 답한 갈래는 서버가 조용히 원문으로 대체하므로 여기
            // 안 온다. 재시도가 또 실패해도 이 단추는 그대로 남는다 —
            // 사람이 쥘 수 있는 유일한 복구 경로를 뺏지 않는다.
            <div className="empty">
              <p className="t-label">{openingError}</p>
              <button
                type="button"
                className="btn btn--primary"
                disabled={openingPending}
                onClick={onRetryOpening}
              >
                {COPY.openingRetry}
              </button>
            </div>
          ) : (
            // 명단이 아직 안 잠긴 극히 짧은 창(D-01) — 기존 빈 화면
            // 문구를 그대로 쓴다. 새 문구를 만들지 않는다.
            <div className="empty">
              <span className="empty__mark">✦</span>
              <p className="t-heading">{COPY.emptyHeading}</p>
              <p className="t-label">{COPY.emptyBody}</p>
            </div>
          )}
        </div>
      </div>

      {unseen > 0 ? (
        <button
          type="button"
          className={unseenAlert ? "jump jump--alert" : "jump"}
          onClick={() => {
            pinnedRef.current = true;
            scrollToBottom();
            setUnseen(0);
            setUnseenAlert(false);
          }}
        >
          {unseenAlert ? "◆ " : ""}새 소식 {unseen} ↓
        </button>
      ) : null}
    </main>
  );
}

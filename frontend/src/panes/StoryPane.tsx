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
import { TurnCard } from "../components/TurnCard.tsx";
import { COPY } from "../labels.ts";
import { isConfirmedTurn, type Turn } from "../session/groupTurns.ts";

const NEAR_BOTTOM_PX = 48;

interface StoryPaneProps {
  turns: Turn[];
  nameOf: (playerId: string) => string;
  segmentCount: number;
  justRevealedSeq: number | null;
  failedDeclareSeqs: Set<number>;
}

export function StoryPane({
  turns,
  nameOf,
  segmentCount,
  justRevealedSeq,
  failedDeclareSeqs,
}: StoryPaneProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const pinnedRef = useRef(true);
  const [unseen, setUnseen] = useState(0);
  const [unseenAlert, setUnseenAlert] = useState(false);

  const visible = turns.filter(isConfirmedTurn);
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
    // 「새 소식」 알약은 세지 않는다: 이미 화면에 있는 카드가 자라는 것은
    // 새로 온 소식이 아니다.
  }, [visible.length, clockCount, narrationCount, illustrationCount]);

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
          {visible.length === 0 ? (
            <div className="empty">
              <span className="empty__mark">✦</span>
              <p className="t-heading">{COPY.emptyHeading}</p>
              <p className="t-label">{COPY.emptyBody}</p>
            </div>
          ) : (
            visible.map((turn) => (
              <div key={turn.declareSeq}>
                <TurnCard
                  turn={turn}
                  actorName={nameOf(turn.playerId)}
                  justRevealed={justRevealedSeq === turn.check?.seq}
                  failed={failedDeclareSeqs.has(turn.declareSeq)}
                  imageUrl={turn.illustration?.image_path ?? null}
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
                        판정 실패가 쌓여 시스템이 진행시켰어요
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            ))
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

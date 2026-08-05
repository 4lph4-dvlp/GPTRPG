/**
 * 턴 한 장 = 카드 한 장.
 *
 * 카드 안의 순서가 그대로 상태 메시지의 위계다:
 *   머리말(누가 무엇을) → 판정 줄(눈·등급) → 이미지 → 서사
 *
 * 판정 줄이 서사보다 위에 있는 것은 화면 취향이 아니라 코드 순서를 따른 것이다 —
 * `routes_actions.confirm`이 판정 사건을 서사보다 **먼저** 기록하므로(D-33 /
 * MEAS-02), 서사가 15초 걸려도 결과는 즉시 볼 수 있다.
 *
 * 모든 글자는 JSX 자식으로만 들어간다 — `dangerouslySetInnerHTML`은 이 저장소
 * 어디에도 쓰지 않는다. 이 화면이 AI 서사와 플레이어 원문을 스크립트 실행
 * 문맥에 넣는 지점이다(T-04-01).
 */

import { SHOW_IMAGE_PLACEHOLDER } from "../config.ts";
import { gradeLabel, gradeTone, moveLabel, statLabel } from "../labels.ts";
import type { Turn } from "../session/groupTurns.ts";

interface TurnCardProps {
  turn: Turn;
  actorName: string;
  /** 방금 주사위 모달이 내려간 턴이면 판정 줄을 잠깐 강조한다. */
  justRevealed: boolean;
  /** 이 턴의 서사 요청이 실패했다고 내 브라우저가 아는 경우. */
  failed: boolean;
  imageUrl?: string | null;
}

function CheckLine({ turn, justRevealed }: { turn: Turn; justRevealed: boolean }) {
  const check = turn.check;
  if (check === null) {
    return (
      <div className="check">
        <span className="narration__waiting">
          <span className="dots">
            <span />
            <span />
            <span />
          </span>
          판정을 기다리는 중
        </span>
      </div>
    );
  }

  const modifierTotal = check.modifiers.reduce((sum, modifier) => sum + modifier.value, 0);
  const rollTotal = check.rolls.reduce((sum, value) => sum + value, 0);
  const total = rollTotal + modifierTotal;

  return (
    <div
      className={justRevealed ? "check check--just-revealed" : "check"}
      role="status"
      aria-live="polite"
    >
      <span className="check__dice">
        {check.rolls.map((value, index) => (
          <span className="dice-pill" key={index}>
            {value}
          </span>
        ))}
      </span>
      <span className="check__total">{total}</span>
      {modifierTotal !== 0 ? (
        <span className="check__mods">
          ({rollTotal} {modifierTotal > 0 ? "+" : "−"} {Math.abs(modifierTotal)})
        </span>
      ) : null}
      <span className="check__target">목표 {check.target}</span>
      <span className={`stamp stamp--${gradeTone(check.grade)}`}>{gradeLabel(check.grade)}</span>
    </div>
  );
}

export function TurnCard({ turn, actorName, justRevealed, failed, imageUrl }: TurnCardProps) {
  const confirmed = turn.confirmed;
  const hasNarration = turn.narration.length > 0;

  return (
    <article className="turn">
      <header className="turn__head">
        <span className="turn__actor">{actorName}</span>
        <span className="turn__sep">·</span>
        <span className="turn__move">
          {confirmed === null
            ? "행동"
            : `${moveLabel(confirmed.move)} (${statLabel(confirmed.stat)})`}
        </span>
      </header>

      <p className="turn__quote">“{turn.rawText}”</p>

      <CheckLine turn={turn} justRevealed={justRevealed} />

      {imageUrl != null ? (
        <div className="turn__plate">
          {/* `alt`는 그림 내용을 옮기지 않는다 — 같은 장면을 서사 문장이 이미
              글로 말하고 있으므로, 화면 낭독기에 두 번 읽히게 만들지 않는다. */}
          <img className="turn__image" src={imageUrl} alt="장면 삽화" decoding="async" />
        </div>
      ) : SHOW_IMAGE_PLACEHOLDER ? (
        <div className="image-slot">
          <span className="image-slot__caption">이미지 자리</span>
        </div>
      ) : null}

      {hasNarration ? (
        <div className="narration">
          {turn.narration.map((chunk) => (
            <p key={chunk.seq}>{chunk.text}</p>
          ))}
        </div>
      ) : turn.check !== null && !failed ? (
        <div className="narration">
          <span className="narration__waiting">
            <span className="dots">
              <span />
              <span />
              <span />
            </span>
            이야기를 쓰는 중
          </span>
        </div>
      ) : null}

      {failed ? (
        <p className="turn__error">
          이번 턴을 처리하지 못했어요. 다시 시도해 주세요
        </p>
      ) : null}
    </article>
  );
}

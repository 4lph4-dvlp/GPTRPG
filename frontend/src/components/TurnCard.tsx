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
import type { CheckCalculationView } from "../api/types.ts";
import { COPY, directionLabel, gradeLabel, gradeTone, moveLabel, segmentRoleLabel, statLabel } from "../labels.ts";
import { buildCheckSummary } from "../session/checkSummary.ts";
import type { Turn } from "../session/groupTurns.ts";

interface TurnCardProps {
  turn: Turn;
  actorName: string;
  /** 이 턴이 화면에 보이는 턴 중 가장 마지막인지 — 「판정을 기다리는 중」과
   * 「판정이 끝내 안 났다」를 가르는 유일한 근거다. 뒤에 다른 턴이 생겼는데도
   * 판정 기록이 없다면 그 턴은 기다리는 중이 아니라 끝난 것이다. */
  isLatest: boolean;
  /** 방금 주사위 모달이 내려간 턴이면 판정 줄을 잠깐 강조한다. */
  justRevealed: boolean;
  /** 이 턴의 서사 요청이 실패했다고 내 브라우저가 아는 경우. */
  failed: boolean;
  /** 이 턴을 낸 사람이 나인가 — 재시도 단추는 남의 턴에는 안 뜬다
   * (서버가 그 캐릭터의 쿠키를 든 브라우저만 확인/진행을 받아들이므로,
   * 남에게 단추를 보여 봤자 403만 받는다, verify-13-06 결함1). */
  mine: boolean;
  /** 재시도 단추의 콜백 — `null`이면 단추를 안 그린다. `failed && mine`
   * 일 때만 실제 함수가 온다(호출부가 그 조합을 판단한다, D-04 — 판단은
   * 한 자리). */
  onRetry: (() => void) | null;
  /** 지금 이 턴을 재시도하는 요청이 도는 중인가 — 단추를 비활성화하고
   * 문구를 바꾼다(사라지게 하지 않는다, 단추가 있다가 없어지면 다시
   * 시도할 방법을 잃은 것처럼 보인다). */
  retrying: boolean;
  imageUrl?: string | null;
  /** 이 턴의 판정 계산 줄(Phase 12.2) — `null`이면 판 10 미만 기록이라
   * `COPY.checkTotalMissing`을 보인다(D-05). */
  calculation: CheckCalculationView | null;
}

function CheckLine({
  turn,
  isLatest,
  justRevealed,
  calculation,
}: {
  turn: Turn;
  isLatest: boolean;
  justRevealed: boolean;
  calculation: CheckCalculationView | null;
}) {
  const check = turn.check;
  if (check === null) {
    if (turn.confirmed === null) {
      // `StoryPane`은 `isVisibleTurn`을 거친 턴만 이 컴포넌트에 넘긴다 —
      // 그 필터를 통과했는데 `confirmed`가 없다는 것은 이 턴이 확인 경로가
      // 아니라 「이대로 진행」 경로(D-10 ②갈래, 11-06)라는 뜻이고, 그 경로는
      // 애초에 판정 자체가 없다(결정 1, `11-06-PLAN.md`). "기다리는 중"이
      // 아니라 처음부터 없는 것이므로 판정 줄을 아예 그리지 않는다 — 계속
      // 기다리는 것처럼 보이는 것은 이 정상 경로를 실패처럼 읽히게 만든다.
      return null;
    }
    // 확인은 됐는데 판정 기록이 없다. 이 턴이 아직 맨 뒤면 판정이 오는
    // 중일 수 있으니 기다린다. 하지만 **뒤에 다른 턴이 이미 생겼다면**
    // 이 턴에 판정이 올 일은 없다 — 판정 제출이 실패한 것이고, 그
    // 실패는 사건으로 남지 않는다(`confirm()`은 오류 상태 코드로만
    // 알린다). 그때도 점을 굴리면 새로고침한 사람에게 영원히 도는
    // 표시가 남아, 끝난 턴이 진행 중인 것처럼 보인다.
    if (!isLatest) {
      return (
        <div className="check">
          <span className="check__never-resolved">{COPY.checkNeverResolved}</span>
        </div>
      );
    }
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

  // 이 컴포넌트는 산수를 하지 않는다 — `buildCheckSummary`가 서버가 만든
  // 계산 줄을 그대로 옮겨 담고, 여기는 그 값을 순서대로 그리기만 한다
  // (D-08/D-09/D-14).
  const summary = buildCheckSummary(check, calculation);

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
      {summary.totalMissing ? (
        <span className="check__total check__total--missing">{COPY.checkTotalMissing}</span>
      ) : (
        <span className="check__mods">
          {summary.rows.map((row, rowIndex) => (
            <span className="calc-row" key={rowIndex}>
              {row.rowLabel !== null ? (
                <span className="calc-row-label">{row.rowLabel}</span>
              ) : null}
              {row.segments.map((segment, segmentIndex) => (
                <span
                  className={segment.discarded ? "calc-segment--discarded" : undefined}
                  key={segmentIndex}
                >
                  {segmentIndex > 0 ? " · " : ""}
                  {segmentRoleLabel(segment.role)} {segment.value}
                  {segment.discarded ? (
                    <span className="calc-segment__discarded-tag">{COPY.checkDiscarded}</span>
                  ) : null}
                </span>
              ))}
              {row.total !== null ? (
                <>
                  {" = "}
                  <span className="check__total">{row.total}</span>
                </>
              ) : null}
            </span>
          ))}
        </span>
      )}
      <span className="check__target">
        목표 {summary.target}
        {summary.direction !== null ? ` (${directionLabel(summary.direction)})` : ""}
      </span>
      <span className={`stamp stamp--${gradeTone(check.grade)}`}>{gradeLabel(check.grade)}</span>
    </div>
  );
}

export function TurnCard({
  turn,
  actorName,
  isLatest,
  justRevealed,
  failed,
  mine,
  onRetry,
  retrying,
  imageUrl,
  calculation,
}: TurnCardProps) {
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

      <CheckLine
        turn={turn}
        isLatest={isLatest}
        justRevealed={justRevealed}
        calculation={calculation}
      />

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
        <>
          <p className="turn__error">{COPY.turnFailed}</p>
          {/* 재시도는 이 턴을 낸 사람만 누를 수 있다(mine) — 서버가 남의
              캐릭터로 온 확인/진행 요청을 403으로 거절하므로, 남에게
              단추를 보여 봤자 실패만 한다. 누르면 새 선언(declareAction)이
              아니라 같은 declare_seq로 confirm()/proceed()를 다시
              부른다(`session/turnRetry.ts`) — 이미 굴린 주사위가 있으면
              그것을 그대로 두고 이야기만 다시 쓴다(verify-13-06 결함1). */}
          {mine && onRetry !== null ? (
            <button
              type="button"
              className="btn btn--ghost"
              disabled={retrying}
              onClick={onRetry}
            >
              {retrying ? COPY.turnRetrying : COPY.turnRetryButton}
            </button>
          ) : null}
        </>
      ) : null}
    </article>
  );
}

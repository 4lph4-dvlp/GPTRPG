/**
 * 주사위 모달 — 가운데에 떴다가 스스로 내려간다.
 *
 * **주사위는 이미 서버에서 굴려졌다.** `check_resolved` 사건에 `rolls`가 그대로
 * 남아 있고 브라우저는 폴링으로 지난 일을 받는다. 그래서 이 모달은 굴리는 것이
 * 아니라 **이미 정해진 눈을 연출로 되짚는 것**이다 — 구르는 동안 스쳐 가는
 * 숫자는 아무거나 써도 되지만 **착지값은 반드시 `rolls[i]`와 같다.** 이걸
 * 어기면 화면이 사건 기록과 다른 말을 하게 된다.
 *
 * 두 가지를 절대 하지 않는다:
 *  · 클릭을 삼키지 않는다 (`pointer-events: none`) — 뒤에서 입력·스크롤이 계속
 *    된다. 한 번이라도 클릭을 먹으면 "모달"이 아니라 "방해"가 된다.
 *  · 과거를 재생하지 않는다 — 새로고침하면 전 역사가 다시 오는데(D-41) 그걸로
 *    연출이 돌면 주사위가 수십 번 굴러간다. 걸러내는 일은 `usePolling`의
 *    `onLiveEvents`가 이미 했다.
 *
 * **합계는 이제 화면이 더한 값이 아니라 서버가 사건에 남긴 값이다**(Phase
 * 12.2, D-14) — `session/checkSummary.ts::buildCheckSummary`가 만든
 * `CheckSummary`를 그대로 그리고, 연출과 이야기 화면(`TurnCard`)·검산 창
 * (`CheckBreakdown`)이 같은 숫자를 말한다. 연출 자체(굴리는 눈·타이밍·
 * 착지값)는 안 건드린다 — `check.rolls`가 여전히 굴릴 주사위 개수와
 * 착지값의 유일한 출처다.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { CheckCalculationView, CheckResolvedEvent } from "../api/types.ts";
import { COPY, directionLabel, gradeLabel, gradeTone, moveLabel, segmentRoleLabel } from "../labels.ts";
import { buildCheckSummary } from "../session/checkSummary.ts";
import { DIE_FACES, Die } from "./Die.tsx";

export interface PendingRoll {
  check: CheckResolvedEvent;
  /** 이 판정의 계산 줄(Phase 12.2) — `null`이면 판 10 미만 기록이라
   * `COPY.checkTotalMissing`을 보인다(D-05). `usePolling`이 `seq`로 짝지어
   * 넘긴 값을 `SessionScreen`이 그대로 옮긴다 — 새 짝짓기를 안 만든다. */
  calculation: CheckCalculationView | null;
  actorName: string;
}

const TUMBLE_MS = 800;
const LAND_STEP_MS = 140;
const SUM_DELAY_MS = 250;
const STAMP_DELAY_MS = 260;
const HOLD_MS = 800;
const LEAVE_MS = 300;
const TUMBLE_TICK_MS = 70;

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function randomFace(): number {
  return 1 + Math.floor(Math.random() * DIE_FACES);
}

export function DiceModal({ roll, onDone }: { roll: PendingRoll; onDone: () => void }) {
  const { check, calculation, actorName } = roll;
  const diceCount = check.rolls.length;
  const summary = buildCheckSummary(check, calculation);

  const [landed, setLanded] = useState(0);
  const [showSum, setShowSum] = useState(false);
  const [showStamp, setShowStamp] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [tumbleFaces, setTumbleFaces] = useState<number[]>(() =>
    check.rolls.map(() => randomFace()),
  );

  const timersRef = useRef<number[]>([]);
  const doneRef = useRef(onDone);
  doneRef.current = onDone;

  const clearTimers = useCallback(() => {
    for (const timer of timersRef.current) {
      window.clearTimeout(timer);
    }
    timersRef.current = [];
  }, []);

  const after = useCallback((delay: number, run: () => void) => {
    timersRef.current.push(window.setTimeout(run, delay));
  }, []);

  const beginLeaving = useCallback(() => {
    setLeaving(true);
    after(LEAVE_MS, () => doneRef.current());
  }, [after]);

  /**
   * 클릭이나 Esc면 즉시 결과만 보여주고 내려간다.
   *
   * **아무 키나로 받지 않는 이유:** 서사를 기다리는 동안 다음 행동을 미리 치는
   * 사람이 있다. 아무 키나 건너뛰기로 받으면 그 사람은 주사위를 **한 번도**
   * 못 본다. 입력 중에 눌릴 일이 없는 키만 받는다.
   */
  const skip = useCallback(() => {
    clearTimers();
    setLanded(diceCount);
    setShowSum(true);
    setShowStamp(true);
    after(220, beginLeaving);
  }, [after, beginLeaving, clearTimers, diceCount]);

  const skipOnEscape = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        skip();
      }
    },
    [skip],
  );

  useEffect(() => {
    if (prefersReducedMotion()) {
      setLanded(diceCount);
      setShowSum(true);
      setShowStamp(true);
      after(HOLD_MS, beginLeaving);
      return clearTimers;
    }

    const tumbleTimer = window.setInterval(() => {
      setTumbleFaces((previous) => previous.map(() => randomFace()));
    }, TUMBLE_TICK_MS);

    for (let index = 0; index < diceCount; index += 1) {
      after(TUMBLE_MS + LAND_STEP_MS * index, () => setLanded(index + 1));
    }
    const allLandedAt = TUMBLE_MS + LAND_STEP_MS * (diceCount - 1);
    after(allLandedAt + SUM_DELAY_MS, () => setShowSum(true));
    after(allLandedAt + SUM_DELAY_MS + STAMP_DELAY_MS, () => setShowStamp(true));
    after(allLandedAt + SUM_DELAY_MS + STAMP_DELAY_MS + HOLD_MS, beginLeaving);

    return () => {
      window.clearInterval(tumbleTimer);
      clearTimers();
    };
  }, [after, beginLeaving, clearTimers, diceCount]);

  useEffect(() => {
    window.addEventListener("keydown", skipOnEscape);
    window.addEventListener("pointerdown", skip);
    return () => {
      window.removeEventListener("keydown", skipOnEscape);
      window.removeEventListener("pointerdown", skip);
    };
  }, [skip, skipOnEscape]);

  const tone = gradeTone(check.grade);

  return (
    <div
      className={leaving ? "dice-overlay dice-overlay--leaving" : "dice-overlay"}
      aria-hidden="true"
    >
      <div className="dice-modal">
        <p className="dice-modal__who">{actorName}</p>
        <p className="dice-modal__move">{moveLabel(check.move)}</p>

        <div className="dice-modal__tray">
          {check.rolls.map((value, index) => {
            const isLanded = index < landed;
            return (
              <Die
                key={index}
                value={isLanded ? value : (tumbleFaces[index] ?? value)}
                phase={isLanded ? "landed" : "rolling"}
                size={56}
              />
            );
          })}
        </div>

        <div className="dice-modal__sum">
          {showSum ? (
            <>
              <span className="dice-modal__total">
                {summary.totalMissing ? COPY.checkTotalMissing : summary.total}
              </span>
              {!summary.totalMissing ? (
                <span className="dice-modal__vs">
                  (
                  {summary.rows
                    .flatMap((row) => row.segments)
                    .map((segment, index) => (
                      <span key={index}>
                        {index > 0 ? " · " : ""}
                        {segmentRoleLabel(segment.role)} {segment.value}
                      </span>
                    ))}
                  )
                </span>
              ) : null}
              <span className="dice-modal__vs">
                목표 {summary.target}
                {summary.direction !== null ? ` (${directionLabel(summary.direction)})` : ""}
              </span>
            </>
          ) : null}
        </div>

        <div className="dice-modal__stamp">
          {showStamp ? (
            <span className={`stamp stamp--${tone}`}>{gradeLabel(check.grade)}</span>
          ) : null}
        </div>

        <p className="dice-modal__hint">클릭하거나 Esc를 누르면 넘어갑니다</p>
      </div>
    </div>
  );
}

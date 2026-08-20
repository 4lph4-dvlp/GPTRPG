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
 *
 * **두 번째 쓰임 — 만들기의 `roll_to_fill` 항목(Phase 12.3-04 Task 3,
 * D-07).** 같은 굴림은 같게 보여야 한다는 것이 이 컴포넌트를 재사용하는
 * 이유다. 만들기 주사위도 `check_resolved`와 똑같이 서버(주입된 `Roller`)가
 * 이미 굴린 값을 `creation_step_completed` 사건의 `rolls`에 남긴 것이고,
 * 브라우저는 그걸 되짚어 보여줄 뿐이다 — **눈의 개수·타이밍·착지값 코드는
 * 한 줄도 안 바뀐다**, `check.rolls` 대신 `creationStep.rolls`를 읽을
 * 뿐이다. 다만 만들기 굴림에는 성공/실패가 없다 — 등급 도장·목표값·
 * `buildCheckSummary` 호출을 만들지 않고, 대신 `axis_values`를 「축 이름
 * — 값」 줄로 보여준다. 판정 요약을 억지로 만들지 않는다.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  CheckCalculationView,
  CheckResolvedEvent,
  CreationStepCompletedEvent,
} from "../api/types.ts";
import {
  COPY,
  directionLabel,
  gradeLabel,
  gradeTone,
  moveLabel,
  segmentRoleLabel,
  statLabel,
} from "../labels.ts";
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

/** 만들기의 `roll_to_fill` 항목 하나(D-07, Phase 12.3-04 Task 3) —
 * `PendingRoll`과 같은 자리에서 쓰이는 두 번째 입력 모양. */
export interface PendingCreationRoll {
  creationStep: CreationStepCompletedEvent;
  /** `GET /creation/steps`에서 받아 둔 선언의 `label` — 못 찾으면
   * `step_id`를 그대로 쓴다(호출부 책임, `creationRollsFrom` 참조). */
  label: string;
  actorName: string;
}

const TUMBLE_MS = 800;
const LAND_STEP_MS = 140;
const SUM_DELAY_MS = 250;
const STAMP_DELAY_MS = 260;
const LEAVE_MS = 300;
const TUMBLE_TICK_MS = 70;

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function randomFace(): number {
  return 1 + Math.floor(Math.random() * DIE_FACES);
}

/** 눈 하나를 6면체 그림으로 그릴지 숫자로 그릴지 — **값이 아니라 서버가
 * 보낸 역할이 정한다.** `"die"`는 룰북이 선언한 주사위 한 알이라 눈 점이
 * 맞고, `"tens"`/`"units"`는 d100의 자릿수라 6면체가 아니다. 역할을 모르면
 * (계산 줄이 없는 판 10 미만 기록) `undefined`를 돌려 `Die`가 옛 규칙대로
 * 값으로 고르게 둔다. */
function shapeFor(role: string | undefined): "pips" | "number" | undefined {
  if (role === undefined) {
    return undefined;
  }
  return role === "die" ? "pips" : "number";
}

export function DiceModal({
  roll,
  onDone,
}: {
  roll: PendingRoll | PendingCreationRoll;
  onDone: () => void;
}) {
  const isCreationRoll = "creationStep" in roll;
  const { actorName } = roll;
  // 굴리는 눈의 개수·착지값의 유일한 출처 — 갈래별로 다른 사건 칸을 읽을
  // 뿐, 아래 애니메이션 코드는 이 배열 하나만 본다.
  const rolls = isCreationRoll ? (roll.creationStep.rolls ?? []) : roll.check.rolls;
  const diceCount = rolls.length;
  // 만들기 굴림에는 계산 줄이 없다(성공/실패가 없다) — summary가 null이면
  // 아래 렌더가 등급 도장·목표값을 그리지 않는다.
  const summary = isCreationRoll ? null : buildCheckSummary(roll.check, roll.calculation);

  const [landed, setLanded] = useState(0);
  const [showSum, setShowSum] = useState(false);
  const [showStamp, setShowStamp] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const [tumbleFaces, setTumbleFaces] = useState<number[]>(() => rolls.map(() => randomFace()));

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
   * **이 창은 저절로 닫히지 않는다.** 예전에는 결과를 보인 뒤 타이머로
   * 물러났는데, 눈에서 합계로 가는 길을 읽으려면 시간이 걸려 사람이 다
   * 읽기 전에 사라졌다. 닫는 것은 이제 사람이 정한다.
   *
   * 클릭·Esc는 **단계에 따라 뜻이 다르다** — 아직 구르는 중이면 연출을
   * 건너뛰어 결과를 즉시 드러내고(창은 그대로 열려 있다), 이미 다
   * 드러났으면 닫는다.
   *
   * **아무 키나로 받지 않는 이유:** 서사를 기다리는 동안 다음 행동을 미리 치는
   * 사람이 있다. 아무 키나 받으면 그 사람은 주사위를 **한 번도** 못 본다.
   * 입력 중에 눌릴 일이 없는 키만 받는다.
   */
  const reveal = useCallback(() => {
    clearTimers();
    setLanded(diceCount);
    setShowSum(true);
    setShowStamp(true);
  }, [clearTimers, diceCount]);

  const revealOrDismiss = useCallback(() => {
    if (showStamp) {
      beginLeaving();
      return;
    }
    reveal();
  }, [beginLeaving, reveal, showStamp]);

  const skipOnEscape = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        revealOrDismiss();
      }
    },
    [revealOrDismiss],
  );

  useEffect(() => {
    if (prefersReducedMotion()) {
      setLanded(diceCount);
      setShowSum(true);
      setShowStamp(true);
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

    return () => {
      window.clearInterval(tumbleTimer);
      clearTimers();
    };
  }, [after, beginLeaving, clearTimers, diceCount]);

  /**
   * **클릭은 「드러내기」에만 쓴다 — 닫기에는 안 쓴다.**
   *
   * 겹판은 `pointer-events: none`이라 클릭을 못 받는다(뒤의 입력칸·스크롤이
   * 살아 있어야 하므로 의도된 것이다). 그래서 창 전역에서 받는다. 다만
   * 그 클릭은 화면 아무 데나 눌린 것이라 **닫기 신호로 쓰면 안 된다** —
   * 결과를 읽는 동안 다음 행동을 치려고 입력칸을 누른 사람의 창이 그
   * 순간 닫혀, 저절로 사라지던 예전 문제가 그대로 돌아온다. 닫는 것은
   * 확인 단추와 Esc뿐이다.
   */
  useEffect(() => {
    if (showStamp) {
      return;
    }
    window.addEventListener("pointerdown", reveal);
    return () => {
      window.removeEventListener("pointerdown", reveal);
    };
  }, [reveal, showStamp]);

  useEffect(() => {
    window.addEventListener("keydown", skipOnEscape);
    return () => {
      window.removeEventListener("keydown", skipOnEscape);
    };
  }, [skipOnEscape]);

  const tone = isCreationRoll ? null : gradeTone(roll.check.grade);

  return (
    <div
      className={leaving ? "dice-overlay dice-overlay--leaving" : "dice-overlay"}
      role="dialog"
      aria-modal="true"
      aria-label={isCreationRoll ? COPY.creationRollTitle : COPY.diceModalTitle}
    >
      <div className="dice-modal">
        <p className="dice-modal__who">{actorName}</p>
        <p className="dice-modal__move">{isCreationRoll ? roll.label : moveLabel(roll.check.move)}</p>

        <div className="dice-modal__tray">
          {rolls.map((value, index) => {
            const isLanded = index < landed;
            // 착지가 전부 끝난 뒤(showSum)에만 버려짐 표시가 붙는다 — 연출이
            // 이야기(검산 줄)와 같은 순간에 같은 사실을 말한다(D-13). 만들기
            // 굴림에는 다시 굴림·버려짐 개념이 없다(summary가 null).
            const isDiscarded = showSum && summary?.rollDiscarded[index] === true;
            return (
              <span
                key={index}
                className={isDiscarded ? "dice-modal__die calc-segment--discarded" : "dice-modal__die"}
              >
                <Die
                  value={isLanded ? value : (tumbleFaces[index] ?? value)}
                  phase={isLanded ? "landed" : "rolling"}
                  size={56}
                  shape={shapeFor(summary?.rollRoles[index])}
                />
                {isDiscarded ? (
                  <span className="calc-segment__discarded-tag">{COPY.checkDiscarded}</span>
                ) : null}
              </span>
            );
          })}
        </div>

        <div className="dice-modal__sum">
          {showSum && isCreationRoll ? (
            <span className="dice-modal__vs">
              {(roll.creationStep.axis_values ?? []).map(({ axis_name, value }) => (
                <span className="calc-row" key={axis_name}>
                  {statLabel(axis_name)} {value}
                </span>
              ))}
            </span>
          ) : null}
          {showSum && !isCreationRoll && summary !== null ? (
            <>
              <span className="dice-modal__total">
                {summary.totalMissing ? COPY.checkTotalMissing : summary.total}
              </span>
              {!summary.totalMissing ? (
                <span className="dice-modal__vs">
                  (
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
                            <span className="calc-segment__discarded-tag">
                              {COPY.checkDiscarded}
                            </span>
                          ) : null}
                        </span>
                      ))}
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
          {/* 만들기 굴림에는 성공/실패가 없다 — 등급 도장을 그리지 않는다. */}
          {showStamp && !isCreationRoll ? (
            <span className={`stamp stamp--${tone}`}>{gradeLabel(roll.check.grade)}</span>
          ) : null}
        </div>

        {showStamp ? (
          <button
            type="button"
            className="dice-modal__confirm"
            onClick={beginLeaving}
            autoFocus
          >
            {COPY.diceModalConfirm}
          </button>
        ) : null}

        <p className="dice-modal__hint">
          {showStamp ? COPY.diceModalHintDone : COPY.diceModalHintRolling}
        </p>
      </div>
    </div>
  );
}

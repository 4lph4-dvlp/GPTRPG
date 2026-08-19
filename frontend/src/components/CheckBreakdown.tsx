/**
 * 판정 검산 표시 — 「주사위 7 + 힘 2 = 9, 목표 10」(D-04).
 *
 * 「사람이 검산할 수 있다」가 이 제품의 약속인데, 지금까지 능력치가 판정에
 * 실제로 들어갔는지 화면에서 확인할 방법이 없었다. 기록 쪽은
 * `CheckResolved.modifiers`가 이미 출처 칸을 갖고 있으므로(12-01) **이
 * 컴포넌트가 새로 하는 일은 화면 쪽뿐이다.**
 *
 * 합계는 이제 `session/checkSummary.ts::buildCheckSummary`가 만든
 * `CheckSummary`를 그대로 그린다(D-14) — 서버가 계산 줄과 방향을 보내고
 * 이 컴포넌트는 산수를 하지 않는다. 계산 줄이 없으면(`summary.totalMissing`,
 * 판 10 미만 기록 — D-05) 합계 자리에 `COPY.checkTotalMissing`을 보이고
 * 눈·보정치·목표값은 원시 값을 그대로 그린다.
 *
 * 목표값을 넘어야 성공인지 밑돌아야 성공인지는 이제 서버가 보낸
 * `summary.direction`으로 목표값 옆에 적힌다(D-07) — 룰북 이름으로 분기하는
 * 조건문은 없다(D-10 경계, 역할 이름은 꼬리표와 강조 정도로만 쓴다).
 */

import { Fragment } from "react";
import { COPY, directionLabel, modifierSourceLabel, segmentRoleLabel } from "../labels.ts";
import type { CheckSummary } from "../session/checkSummary.ts";

interface CheckBreakdownProps {
  summary: CheckSummary;
}

export function CheckBreakdown({ summary }: CheckBreakdownProps) {
  return (
    <div className="breakdown">
      <div className="breakdown__row">
        {summary.totalMissing ? (
          <>
            <span className="breakdown__dice">
              {summary.rolls.map((value, index) => (
                <span className="dice-pill" key={index}>
                  {value}
                </span>
              ))}
            </span>
            {summary.modifiers.map((modifier, index) => (
              <span className="breakdown__mod" key={index}>
                <span className="breakdown__mod-sign">
                  {modifier.value >= 0 ? "+" : "−"} {Math.abs(modifier.value)}
                </span>
                <span className="breakdown__mod-source">{modifierSourceLabel(modifier.source)}</span>
              </span>
            ))}
            <span className="breakdown__eq">=</span>
            <span className="breakdown__total breakdown__total--missing">
              {COPY.checkTotalMissing}
            </span>
          </>
        ) : (
          summary.rows.map((row, rowIndex) => (
            <Fragment key={rowIndex}>
              {row.segments.map((segment, segmentIndex) => (
                <span className="breakdown__mod" key={segmentIndex}>
                  <span className="breakdown__mod-sign">
                    {segmentRoleLabel(segment.role)} {segment.value}
                  </span>
                  {segment.source !== null ? (
                    <span className="breakdown__mod-source">
                      {modifierSourceLabel(segment.source)}
                    </span>
                  ) : null}
                </span>
              ))}
              <span className="breakdown__eq">=</span>
              <span className="breakdown__total">{row.total}</span>
            </Fragment>
          ))
        )}
        <span className="breakdown__target">
          {COPY.checkTarget} {summary.target}
          {summary.direction !== null ? ` (${directionLabel(summary.direction)})` : ""}
        </span>
      </div>
    </div>
  );
}

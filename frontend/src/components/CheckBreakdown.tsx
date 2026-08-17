/**
 * 판정 검산 표시 — 「주사위 7 + 힘 2 = 9, 목표 10」(D-04).
 *
 * 「사람이 검산할 수 있다」가 이 제품의 약속인데, 지금까지 능력치가 판정에
 * 실제로 들어갔는지 화면에서 확인할 방법이 없었다. 기록 쪽은
 * `CheckResolved.modifiers`가 이미 출처 칸을 갖고 있으므로(12-01) **이
 * 컴포넌트가 새로 하는 일은 화면 쪽뿐이다.**
 *
 * 합계는 `ConfirmResponse.total`(서버 값)을 안 쓴다 — `CheckResolved`가 그
 * 값을 저장하지 않아 항상 `null`이다(12-01 알려진 갭, `api/types.ts`
 * `ConfirmResponse.total` 참조). 대신 `TurnCard.tsx`/`DiceModal.tsx`가 이미
 * 하는 것과 같은 계산(눈 합 + 보정치 합)을 여기서도 그대로 한다 — 화면이
 * 하는 산수 자체가 검산 대상이므로, 빈 칸을 데이터인 척 보이지 않는다.
 *
 * 목표값을 넘어야 성공인지 밑돌아야 성공인지는 룰북마다 다르다(2d6 등급식 vs
 * d100 롤언더) — 이 컴포넌트는 그 비교를 말하지 않고 숫자만 보인다. 방향에
 * 대한 해석은 등급 도장(`gradeLabel`/`gradeTone`)이 이미 하고 있다.
 */

import { modifierSourceLabel } from "../labels.ts";
import { COPY } from "../labels.ts";
import type { ModifierView } from "../api/types.ts";

interface CheckBreakdownProps {
  rolls: number[];
  modifiers: ModifierView[];
  target: number | null;
}

export function CheckBreakdown({ rolls, modifiers, target }: CheckBreakdownProps) {
  const rollTotal = rolls.reduce((sum, value) => sum + value, 0);
  const modifierTotal = modifiers.reduce((sum, modifier) => sum + modifier.value, 0);
  const total = rollTotal + modifierTotal;

  return (
    <div className="breakdown">
      <div className="breakdown__row">
        <span className="breakdown__dice">
          {rolls.map((value, index) => (
            <span className="dice-pill" key={index}>
              {value}
            </span>
          ))}
        </span>
        {modifiers.map((modifier, index) => (
          <span className="breakdown__mod" key={index}>
            <span className="breakdown__mod-sign">
              {modifier.value >= 0 ? "+" : "−"} {Math.abs(modifier.value)}
            </span>
            <span className="breakdown__mod-source">{modifierSourceLabel(modifier.source)}</span>
          </span>
        ))}
        <span className="breakdown__eq">=</span>
        <span className="breakdown__total">{total}</span>
        {target !== null ? (
          <span className="breakdown__target">
            {COPY.checkTarget} {target}
          </span>
        ) : null}
      </div>
    </div>
  );
}

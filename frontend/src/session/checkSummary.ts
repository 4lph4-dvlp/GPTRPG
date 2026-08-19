/**
 * 판정 줄을 그리는 「한 곳」(D-14) — 산수가 한 줄도 없다.
 *
 * `TurnCard`(지난 판정 목록)·`CheckBreakdown`(즉시 응답)·`DiceModal`(굴림
 * 연출) 세 화면이 각자 눈을 더하던 것을 여기 하나로 모았고, 여기서도
 * 더하지 않는다 — 룰북마다 눈의 뜻이 달라 그 계산을 아는 곳은 규칙
 * 코어뿐이다. 서버가 만든 `CheckCalculationView`를 그대로 옮겨 담기만
 * 한다. 계산 줄이 없으면(`null`, 판 10 미만 기록 — D-05) `totalMissing`을
 * 참으로 세우고 `total`을 `null`로, `rows`를 빈 목록으로 두되 원시
 * 눈·보정치·목표값·등급은 그대로 싣는다 — 0으로 때우지 않는다.
 *
 * `groupTurns.ts`와 같은 성격 — React 훅이 아니라 순수 함수 모듈이다.
 */

import type {
  CheckCalculationView,
  CheckResolvedEvent,
  ModifierRecord,
} from "../api/types.ts";

/** `buildCheckSummary`가 실제로 읽는 칸만 — 폴링 사건(`CheckResolvedEvent`)과
 * 즉시 응답(`ConfirmResponse`) 양쪽이 이 모양으로 좁혀진다. `seq`·`person_id`
 * 같은 나머지 칸은 요약을 만드는 데 필요 없다. */
type CheckFacts = Pick<CheckResolvedEvent, "rolls" | "modifiers" | "target" | "grade">;

export interface CheckSummaryRow {
  segments: CheckCalculationView["rows"][number]["segments"];
  total: number | null;
}

export interface CheckSummary {
  rows: CheckSummaryRow[];
  total: number | null;
  totalMissing: boolean;
  target: number;
  direction: string | null;
  rolls: number[];
  modifiers: ModifierRecord[];
  grade: string;
}

/** 계산 줄 목록을 `seq`로 색인한다 — 판정 사건과 짝짓는 유일한 열쇠다. */
export function indexCalculations(
  list: CheckCalculationView[],
): Map<number, CheckCalculationView> {
  const bySeq = new Map<number, CheckCalculationView>();
  for (const calculation of list) {
    bySeq.set(calculation.seq, calculation);
  }
  return bySeq;
}

export function buildCheckSummary(
  check: CheckFacts,
  calculation: CheckCalculationView | null,
): CheckSummary {
  if (calculation === null) {
    return {
      rows: [],
      total: null,
      totalMissing: true,
      target: check.target,
      direction: null,
      rolls: check.rolls,
      modifiers: check.modifiers,
      grade: check.grade,
    };
  }
  return {
    rows: calculation.rows.map((row) => ({ segments: row.segments, total: row.total })),
    total: calculation.total,
    totalMissing: false,
    target: calculation.target,
    direction: calculation.direction,
    rolls: check.rolls,
    modifiers: check.modifiers,
    grade: check.grade,
  };
}

/** `ConfirmResponse`에서 온 값으로 요약을 만드는 얇은 진입점(12.2-02) —
 * 계산은 여전히 없다, `buildCheckSummary`에 그대로 위임한다. 호출부
 * (`ChatPane.tsx`)가 `response.rolls !== null`을 먼저 확인해 판정이 실제로
 * 있었던 응답만 이 함수에 넘긴다. */
export function buildCheckSummaryFromConfirmResponse(response: CheckFacts & {
  calculation: CheckCalculationView | null;
}): CheckSummary {
  return buildCheckSummary(response, response.calculation);
}

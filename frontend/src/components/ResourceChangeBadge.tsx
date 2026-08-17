/**
 * 자원 변화 표시 — 「변한 걸 아무도 못 알아챘다」(세션1)를 막는 화면 쪽
 * 장치(RULE-07, D-19).
 *
 * `StatusPane.tsx`의 여섯 `form` 분기 각각에 이 배지 하나를 얹는다 — 새
 * 렌더 갈래를 만들지 않는다. **모든 변화가 보이고, 큰 것은 더 강하게
 * 보인다**로 요구사항을 만족한다 — 「몇 % 이상이 크다」 같은 고정 문턱은
 * 코드 어디에도 없다(`changeIntensity` 도크스트링 참조).
 *
 * `ThreatClock.tsx`가 이미 세운 규율을 그대로 물려받는다 — **재촉하지
 * 않는다.** 실패 카운터가 2/3이어도 색이 붉어지지 않는 것과 같은 이유로,
 * 이 배지도 깜빡이거나 재촉하는 애니메이션을 쓰지 않는다. 잠시 떠 있다가
 * 조용히 가라앉는다(페이드는 `styles.css`의 CSS 애니메이션 하나가 전부다).
 */

import type { CSSProperties } from "react";
import type { StatEntry } from "../api/types.ts";

/** `--resource-intensity`는 표준 CSS 프로퍼티가 아니라 커스텀 속성이라
 * `CSSProperties`가 이 이름을 모른다 — 인라인 스타일 객체 자리에서만
 * 좁혀 쓰는 보조 타입이다. */
type BadgeStyle = CSSProperties & { "--resource-intensity": number };

/** 세기 계산이 형태별로 쓸 수 있는 최소 정보 — 실제 `ResourceChangeRecord`/
 * `ResourceChangeView`도 이 모양을 만족한다(구조적 타이핑). */
export interface ResourceChangeMagnitude {
  amount: number;
}

/** 상한이 없는 축(숫자·usage_die 등)의 부드러운 압축 배율 — 이 값 하나로
 * 「변화량이 클수록 1에 가까워지지만 넘지 않는다」는 연속·단조 곡선의
 * 기울기만 정한다. 「N 이상이면 크다」로 값을 이산화하는 문턱이
 * 아니다(RULE-07/D-19) — `softCap`은 어떤 입력에도 하나의 연속값을
 * 돌려준다. */
const SOFT_CAP_SCALE = 6;

function clamp01(value: number): number {
  if (value < 0) {
    return 0;
  }
  if (value > 1) {
    return 1;
  }
  return value;
}

/** 상한을 모르는 변화량을 0~1 사이로 부드럽게 누른다 — 값이 커질수록
 * 1에 점근하되(`x / (x + k)`) 절대 넘지 않고, 어떤 두 입력을 비교해도
 * 큰 쪽이 항상 크거나 같다(단조 비감소). 등급 이름으로 가르는 분기가
 * 없다. */
function softCap(magnitude: number): number {
  return magnitude / (magnitude + SOFT_CAP_SCALE);
}

/**
 * 자원 변화 하나의 표시 세기를 0(거의 안 보임) ~ 1(가장 강함) 사이의
 * 연속값으로 정한다(RULE-07/D-19) — **형태별로 계산할 수 있는 것만
 * 쓴다.**
 *
 * - 상한이 있는 숫자·진행 칸(`numeric`/`clock`, `stat.max`가 있음): 변화량
 *   대비 상한의 비율.
 * - 상한이 없는 숫자 축(`numeric`, `stat.max`가 `null`)·`usage_die`: 변화의
 *   절대 크기를 `softCap`으로 완만하게 누른다.
 * - `named_slots`: 바뀐 칸 수(변화량의 절대 크기) 대비 전체 칸 수.
 * - `tag_list`: 바뀐 태그 수 대비 지금 태그 목록 길이(둘 다 0이면 `softCap`).
 *
 * 이 함수가 순수 함수이기 때문에 시험이 "등급 이름으로 나누지 않는다"는
 * 성질을 등급 계산 자체가 아니라 **반환값의 단조성**으로 직접 단언할 수
 * 있다 — 문턱을 안 두고도 RULE-07을 시험으로 확인 가능하게 만드는 방법이다
 * (`ResourceChangeBadge.test.ts`).
 */
export function changeIntensity(change: ResourceChangeMagnitude, stat: StatEntry): number {
  const magnitude = Math.abs(change.amount);

  if ((stat.form === "numeric" || stat.form === "clock") && stat.max !== null && stat.max > 0) {
    return clamp01(magnitude / stat.max);
  }

  if (stat.form === "named_slots") {
    const slotCount = stat.slot_values?.length ?? 0;
    return slotCount > 0 ? clamp01(magnitude / slotCount) : clamp01(softCap(magnitude));
  }

  if (stat.form === "tag_list") {
    const tagCount = stat.tags?.length ?? 0;
    return tagCount > 0 ? clamp01(magnitude / tagCount) : clamp01(softCap(magnitude));
  }

  // 상한 없는 numeric·usage_die·그 밖 형태 — 계산할 수 있는 상한이 없으므로
  // 절대 크기를 부드럽게 누른다.
  return clamp01(softCap(magnitude));
}

interface ResourceChangeBadgeProps {
  amount: number;
  intensity: number;
}

export function ResourceChangeBadge({ amount, intensity }: ResourceChangeBadgeProps) {
  const clamped = clamp01(intensity);
  const tone = amount > 0 ? "up" : amount < 0 ? "down" : "flat";
  return (
    <span
      className={`resource-badge resource-badge--${tone}`}
      // 연속값을 CSS 커스텀 속성으로 넘긴다 — `styles.css`의 페이드
      // keyframes가 이 값을 그대로 읽어 세기(RULE-07/D-19)와 시간에 따른
      // 가라앉음을 하나의 opacity 계산식으로 합친다. 등급 이름으로 스타일을
      // 가르는 분기는 여기에도 없다.
      style={{ "--resource-intensity": clamped } as BadgeStyle}
    >
      {amount > 0 ? `+${amount}` : amount}
    </span>
  );
}

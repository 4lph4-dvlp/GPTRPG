/**
 * 주사위 한 알. 눈이 면 수를 넘으면(d100 룰북 등) 주사위 그림 대신 숫자로
 * 떨어뜨린다 — 6면체가 37을 보여주는 거짓말을 하지 않는다.
 */

/** 지금 룰북(dungeonworld_like)이 쓰는 면 수. 사건에 면 수 정보가 없어서
 * (룰북이 갖고 있고 폴링 응답에는 안 온다) 여기 상수 하나로 둔다. */
export const DIE_FACES = 6;

/** 3×3 자리 중 어느 칸에 점을 찍는지 — 눈별 배치. */
const PIP_LAYOUT: Record<number, [number, number][]> = {
  1: [[1, 1]],
  2: [
    [0, 0],
    [2, 2],
  ],
  3: [
    [0, 0],
    [1, 1],
    [2, 2],
  ],
  4: [
    [0, 0],
    [0, 2],
    [2, 0],
    [2, 2],
  ],
  5: [
    [0, 0],
    [0, 2],
    [1, 1],
    [2, 0],
    [2, 2],
  ],
  6: [
    [0, 0],
    [0, 1],
    [0, 2],
    [2, 0],
    [2, 1],
    [2, 2],
  ],
};

interface DieProps {
  value: number;
  size?: number;
  /** 구르는 중이면 흔들림 애니메이션, 착지 직후면 튕김 애니메이션. */
  phase?: "rolling" | "landed" | "static";
}

export function Die({ value, size = 56, phase = "static" }: DieProps) {
  const layout = PIP_LAYOUT[value];
  if (layout === undefined) {
    return (
      <div className="die-number" aria-label={`눈 ${value}`}>
        {value}
      </div>
    );
  }

  const cellStep = size / 4;
  const pipRadius = size * 0.075;
  const className =
    phase === "rolling" ? "die die--rolling" : phase === "landed" ? "die die--landed" : "die";

  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={`눈 ${value}`}
    >
      <defs>
        <linearGradient id={`die-face-${size}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#f5eedb" />
          <stop offset="100%" stopColor="#cdc2a5" />
        </linearGradient>
      </defs>
      <rect
        x="1"
        y="1"
        width={size - 2}
        height={size - 2}
        rx={size * 0.18}
        fill={`url(#die-face-${size})`}
        stroke="#8a7a4f"
        strokeWidth="1"
      />
      {layout.map(([row, column]) => (
        <circle
          key={`${row}-${column}`}
          cx={cellStep * (column + 1)}
          cy={cellStep * (row + 1)}
          r={pipRadius}
          fill="#221d10"
        />
      ))}
    </svg>
  );
}

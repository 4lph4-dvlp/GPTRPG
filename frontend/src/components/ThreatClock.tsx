/**
 * 위협 시계 — TRPG의 진행 시계(progress clock)를 그대로 옮긴 원형 눈금.
 *
 * 숫자만 조용히 1 올라가면 아무도 못 본다. 그래서 같은 사건을 두 곳에서
 * 표현한다: 흐름(중앙 배너 = 언제 넘어갔는지)과 이 눈금(지금 몇 칸인지).
 * 시계가 막 넘어간 직후에는 `pulsing`으로 잠깐 강조한다.
 *
 * 문구와 색에 재촉을 넣지 않는다 — 이 표시는 상태를 알려 주는 정보이지
 * 사람을 몰아세우는 장치가 아니다.
 */

interface ThreatClockProps {
  segment: number;
  segmentCount: number;
  size?: number;
  pulsing?: boolean;
}

/** 원의 중심에서 시작해 12시 방향부터 시계 방향으로 한 칸을 그리는 경로. */
function segmentPath(
  index: number,
  segmentCount: number,
  center: number,
  radius: number,
): string {
  const sweep = (Math.PI * 2) / segmentCount;
  const start = -Math.PI / 2 + sweep * index;
  const end = start + sweep;
  const x1 = center + radius * Math.cos(start);
  const y1 = center + radius * Math.sin(start);
  const x2 = center + radius * Math.cos(end);
  const y2 = center + radius * Math.sin(end);
  const largeArc = sweep > Math.PI ? 1 : 0;
  return `M ${center} ${center} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`;
}

export function ThreatClock({
  segment,
  segmentCount,
  size = 56,
  pulsing = false,
}: ThreatClockProps) {
  const center = size / 2;
  const radius = center - 3;
  // 액터가 마지막 칸에서 자동 진행을 멈추지만(actor._maybe_auto_advance),
  // 화면은 어떤 값이 와도 눈금을 벗어나 그리지 않는다.
  const filled = Math.max(0, Math.min(segment, segmentCount));
  const complete = filled >= segmentCount;

  return (
    <svg
      className={pulsing ? "clock__dial clock__dial--pulsing" : "clock__dial"}
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={`위협 시계 ${filled}/${segmentCount}칸`}
    >
      <circle cx={center} cy={center} r={radius} fill="#15141d" />
      {Array.from({ length: segmentCount }, (_, index) => (
        <path
          key={index}
          className="clock__seg"
          d={segmentPath(index, segmentCount, center, radius)}
          fill={
            index < filled ? (complete ? "#e05a4b" : "#c9a227") : "rgba(255, 255, 255, 0.03)"
          }
          stroke="#2c2a39"
          strokeWidth="1"
        />
      ))}
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={complete ? "#e05a4b" : "#6d5a1c"}
        strokeWidth="1.5"
      />
    </svg>
  );
}

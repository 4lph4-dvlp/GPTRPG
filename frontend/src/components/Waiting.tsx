/** 진행자를 기다리는 동안의 표시(G-12.3-9).
 *
 * 만들기 GM 호출은 실측 12~30초 걸린다(`CREATION_GM_TIMEOUT_S` 참조).
 * 그동안 화면에 아무 변화가 없으면 사람은 멈춘 줄 알고 새로고침한다 —
 * 실제 시험에서 사장님이 그 위험을 지적했다. 문구 하나로는 부족하다:
 * 문구는 정지 화면과 구분되지 않는다.
 */
export function Waiting({ label }: { label: string }) {
  return (
    <p className="t-label waiting" role="status" aria-live="polite">
      <span>{label}</span>
      <span className="waiting__dots" aria-hidden="true">
        <span className="waiting__dot" />
        <span className="waiting__dot" />
        <span className="waiting__dot" />
      </span>
    </p>
  );
}

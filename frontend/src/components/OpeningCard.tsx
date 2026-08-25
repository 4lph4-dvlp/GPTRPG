/**
 * 오프닝 서사 카드(SCENE-01, D-01) — 판정 없이 뜨는 첫 문단.
 *
 * `TurnCard`를 그대로 재사용하지 않는다 — 그 컴포넌트는 `turn.rawText`
 * (플레이어 원문 인용)를 항상 필수로 그리는데, 오프닝에는 그 값 자체가
 * 없다(선언이 없는 서사이므로). 그래서 이 컴포넌트는 `.turn` 컨테이너
 * (테두리·그라디언트·`turn-in` 320ms 입장 애니메이션)만 물려받고, 안에는
 * `.narration p`(명조 17px/1.75) 문단 하나만 그린다 — `.turn__head`(행위자·
 * 무브)와 `.turn__quote`(플레이어 원문 인용)는 렌더하지 않는다. 오프닝에는
 * 행위자도 판정도 없다.
 *
 * `text`는 서버(`render_scripted_opening`)가 다섯 요소를 이미 `"\n\n"`으로
 * 이어 붙인 한 덩어리다 — 화면은 다시 조립하지 않는다. `.narration p`에
 * 이미 걸린 `white-space: pre-wrap` 규칙이 그 구분자를 문단처럼 보이게
 * 만든다. 새 CSS 클래스를 만들지 않는다.
 */
export function OpeningCard({ text }: { text: string }) {
  return (
    <article className="turn">
      <div className="narration">
        <p>{text}</p>
      </div>
    </article>
  );
}

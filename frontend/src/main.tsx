/**
 * 글꼴은 **저장소에 담아서 같이 빌드된다** — 바깥 CDN을 부르지 않는다.
 * 실험이 로컬 네트워크에서 돌고, 세션 중에 외부 요청 하나가 늦어지면 네 명의
 * 화면이 동시에 글자 없는 상태로 멈춘다.
 *
 *  · Pretendard — 화면 글꼴. 한글 자간·획 굵기가 시스템 고딕보다 고르다.
 *    dynamic-subset은 실제로 쓰인 글자 묶음만 내려받는다.
 *  · 고운바탕 — 서사와 이름 전용 명조. 한글에 제대로 된 세리프가 붙어야
 *    "이야기"와 "화면 정보"가 눈으로 갈린다. **굵은 자족은 안 부른다** —
 *    한글 명조 굵은 판은 그것만 450KB인데, 명조로 쓰는 자리(이름·서사·배너)는
 *    크기와 색으로 위계를 내는 편이 보기에도 낫다.
 */
import "pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css";
import "@fontsource/gowun-batang/korean-400.css";
import "@fontsource/gowun-batang/latin-400.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App.tsx";
import { ErrorBoundary } from "./screens/Notices.tsx";
import "./styles.css";

const root = document.querySelector<HTMLDivElement>("#app");
if (root !== null) {
  // ErrorBoundary가 여기 없던 채로 안전한 맥락 전용 API 호출이 참가자
  // 전원의 첫 렌더를 예외로 끊었고(Phase 12.3-11, 6차 검증 gap), 그 예외가
  // 조용히 삼켜져 아무도 원인을 알 수 없는 빈 화면만 남았다 — 사람이
  // 먼저 겪고 나서야 그 사실을 알았다. 마운트·렌더 도중 어떤 예외든
  // 사람이 읽을 문장으로 남도록 이 겹을 둔다.
  createRoot(root).render(
    <StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </StrictMode>,
  );
}

/**
 * 전체 화면 안내 셋.
 *
 * `InvalidSession`은 이번에 새로 만든 화면이다 — `app.py`의
 * `validate_session_id`가 허용 범위를 벗어난 식별자를 400으로 거절하는데,
 * 이전 화면은 그 응답을 조용히 삼켜서 **아무 설명 없는 빈 화면에서 영원히
 * 기다리는** 상태가 됐다. 몇 번을 다시 물어도 같은 400이 오므로 재시도가
 * 의미 없는 유일한 경우이고, 그래서 폴링을 멈추고 이유를 말한다.
 */

import { Component, type ReactNode } from "react";
import { COPY } from "../labels.ts";

export function MissingSession() {
  return (
    <div className="screen">
      <div className="screen__inner">
        <div className="screen__title">
          <h1 className="t-display">세션 링크가 필요해요</h1>
        </div>
        <div className="notice">
          <p className="t-body">
            주소 끝에 <code>?session=세션식별자</code>가 빠졌어요. 진행자에게 받은 링크를 다시
            확인해 주세요.
          </p>
        </div>
      </div>
    </div>
  );
}

export function InvalidSession({ sessionId }: { sessionId: string }) {
  return (
    <div className="screen">
      <div className="screen__inner">
        <div className="screen__title">
          <h1 className="t-display">세션 식별자가 올바르지 않아요</h1>
        </div>
        <div className="notice">
          <p className="t-body">
            받은 주소의 <code>{sessionId}</code>는 서버가 받아들이는 형태가 아니에요.
          </p>
          <p className="t-label">
            영문·숫자·밑줄(_)·붙임표(-)만 쓸 수 있고 64자를 넘을 수 없어요. 진행자에게 링크를
            다시 받아 주세요.
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * 명단이 이미 잠겼는데 이 브라우저에 캐릭터가 없는 경우(Phase 12.3,
 * D-10). `CreationScreen`이 폴링에서 `party_roster_locked` 사건을 보면
 * 이 안내로 갈아탄다 — 만들기가 유일한 입장 경로이므로, 잠긴 뒤에는
 * 더 할 수 있는 조작이 없다(Phase 8 D-01의 쿠키 한계와 같은 결).
 */
export function RosterLocked() {
  return (
    <div className="screen">
      <div className="screen__inner">
        <div className="screen__title">
          <h1 className="t-display">파티 명단이 이미 잠겼어요</h1>
        </div>
        <div className="notice">
          <p className="t-body">{COPY.creationRosterLocked}</p>
        </div>
      </div>
    </div>
  );
}

export function Loading() {
  return (
    <div className="screen">
      <div className="screen__inner">
        <div className="spinner" aria-label={COPY.loading} />
      </div>
    </div>
  );
}

/**
 * 앱 최상단 오류 경계(Phase 12.3-11, 6차 검증 gap) — 마운트·렌더 도중 어떤
 * 예외든 빈 `#app`으로 끝나던 것을 막는다. 실제로 있었던 일: 안전한
 * 맥락(secure context)에서만 있는 브라우저 API를 `CreationScreen`의 렌더
 * 본문이 곧바로 불렀고, README가 참가자에게 나눠 주라고 지시하는 형태
 * (평문 http + 이 기계의 일반 IP)에서는 그 API가 없어 첫 렌더가 예외로
 * 끊겼다. `main.tsx`에 오류 경계가 없어 그 예외가 조용히 삼켜졌고,
 * 참가자 전원이 아무 설명 없는 빈 화면을 봤다.
 *
 * 오류 문장을 사람에게 그대로 보이는 이유 — 실험 현장에는 개발자 도구를
 * 열 사람이 없다. 진행자가 참가자에게 「무엇이 보이냐」고 물어 화면에
 * 적힌 문장으로 원인을 좁힐 수 있어야 한다(D-13/D-15의 연장).
 * 아래 예외 처리 훅이 `console.error`로도 원본 예외와 컴포넌트 스택을
 * 남긴다 — 화면과 콘솔 둘 다에 흔적을 남기는 것이 목표다.
 *
 * **이 경계가 못 잡는 것** — React 오류 경계의 구조적 한계다. 모듈을
 * 불러오는 시점에 터지는 예외(import 단계)와 이벤트 핸들러 안의 예외는
 * 이 경계를 안 거친다. 이 계획은 그 두 자리를 새로 처리하지 않는다.
 */
export class ErrorBoundary extends Component<{ children: ReactNode }, { message: string | null }> {
  state: { message: string | null } = { message: null };

  static getDerivedStateFromError(error: unknown): { message: string } {
    return { message: error instanceof Error ? error.message : String(error) };
  }

  componentDidCatch(error: unknown, info: { componentStack?: string | null }): void {
    // 삼키지 않는다 — 화면에 문구를 보이는 것과 콘솔에 흔적을 남기는 것은
    // 둘 다 필요하다(6차 검증 UAT가 「콘솔에도 아무것도 안 남는다」를
    // 문제로 적었다).
    console.error("앱 최상단에서 잡힌 예외:", error, info.componentStack);
  }

  render() {
    if (this.state.message === null) {
      return this.props.children;
    }
    return (
      <div className="screen">
        <div className="screen__inner">
          <div className="screen__title">
            <h1 className="t-display">{COPY.appCrashedTitle}</h1>
          </div>
          <div className="notice">
            <p className="t-body">{COPY.appCrashed}</p>
            <p className="t-label">
              <code>{this.state.message}</code>
            </p>
          </div>
        </div>
      </div>
    );
  }
}

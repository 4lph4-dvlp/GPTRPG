/**
 * 전체 화면 안내 셋.
 *
 * `InvalidSession`은 이번에 새로 만든 화면이다 — `app.py`의
 * `validate_session_id`가 허용 범위를 벗어난 식별자를 400으로 거절하는데,
 * 이전 화면은 그 응답을 조용히 삼켜서 **아무 설명 없는 빈 화면에서 영원히
 * 기다리는** 상태가 됐다. 몇 번을 다시 물어도 같은 400이 오므로 재시도가
 * 의미 없는 유일한 경우이고, 그래서 폴링을 멈추고 이유를 말한다.
 */

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

export function Loading() {
  return (
    <div className="screen">
      <div className="screen__inner">
        <div className="spinner" aria-label={COPY.loading} />
      </div>
    </div>
  );
}

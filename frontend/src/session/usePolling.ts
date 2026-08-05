/**
 * 폴링 루프 하나 — 화면 전체가 여기서 나오는 값만 본다.
 *
 * 규칙 셋은 백엔드 결정을 그대로 따른다:
 *  · 주기 1.5초 (D-38). 0.5초로 줄이지 않는다.
 *  · 7회 연속 실패(≈10.5초)면 끊김으로 본다 (D-40). 폴링은 계속 재시도한다.
 *  · 마지막 순번을 브라우저에 저장하지 않는다 — 새로고침·재접속은 언제나
 *    `from_seq=0`부터 전체 역사를 다시 받아 다시 그린다 (D-41).
 *
 * **첫 응답은 「과거」다.** D-41 때문에 새로고침하면 지난 사건 수백 개가 한꺼번에
 * 도착한다. 그 배치로 주사위 연출이 돌면 새로고침할 때마다 주사위가 수십 번
 * 굴러간다. 그래서 `onLiveEvents`는 첫 응답을 건너뛰고, 그 뒤로 실제로 새로
 * 생긴 사건에만 불린다.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, fetchEvents } from "../api/client.ts";
import type { GameEvent, GameStateView } from "../api/types.ts";

/** D-38의 1~2초 범위. */
export const POLL_INTERVAL_MS = 1500;

/** 1.5초 × 7 ≈ 10.5초 — D-40의 "약 10초". */
export const DISCONNECT_AFTER_FAILURES = 7;

export type FeedStatus = "loading" | "live" | "disconnected" | "invalid";

export interface SessionFeed {
  events: GameEvent[];
  state: GameStateView | null;
  status: FeedStatus;
  /** 마지막으로 성공한 폴링 시각(ms). 끊김 배너가 "N초 전"을 계산한다. */
  lastSuccessAt: number | null;
  /** 지금 즉시 한 번 더 폴링한다 — 확인 직후 결과를 1.5초 기다리지 않게. */
  pollNow: () => void;
}

export function usePolling(
  sessionId: string,
  onLiveEvents?: (events: GameEvent[]) => void,
): SessionFeed {
  const [events, setEvents] = useState<GameEvent[]>([]);
  const [state, setState] = useState<GameStateView | null>(null);
  const [status, setStatus] = useState<FeedStatus>("loading");
  const [lastSuccessAt, setLastSuccessAt] = useState<number | null>(null);

  const lastSeqRef = useRef(-1);
  const failuresRef = useRef(0);
  const primedRef = useRef(false);
  const inFlightRef = useRef(false);
  const aliveRef = useRef(true);
  const liveHandlerRef = useRef(onLiveEvents);
  liveHandlerRef.current = onLiveEvents;

  const poll = useCallback(async () => {
    if (inFlightRef.current) {
      return;
    }
    inFlightRef.current = true;
    try {
      const response = await fetchEvents(sessionId, lastSeqRef.current + 1);
      if (!aliveRef.current) {
        return;
      }
      failuresRef.current = 0;
      lastSeqRef.current = response.state.last_seq;
      setState(response.state);
      setStatus("live");
      setLastSuccessAt(Date.now());

      if (response.events.length > 0) {
        // 겹쳐 도착한 응답이 같은 사건을 두 번 넣지 않도록 순번으로 합친다.
        setEvents((previous) => {
          const merged = new Map<number, GameEvent>();
          for (const event of previous) {
            merged.set(event.seq, event);
          }
          for (const event of response.events) {
            merged.set(event.seq, event);
          }
          return [...merged.values()].sort((a, b) => a.seq - b.seq);
        });
        if (primedRef.current) {
          liveHandlerRef.current?.(response.events);
        }
      }
      primedRef.current = true;
    } catch (error) {
      if (!aliveRef.current) {
        return;
      }
      // 세션 식별자 자체가 허용 범위를 벗어나면(app.py의 validate_session_id)
      // 몇 번을 다시 물어도 같은 400이 온다 — 재시도가 의미 없는 유일한 경우다.
      if (error instanceof ApiError && error.status === 400) {
        setStatus("invalid");
        aliveRef.current = false;
        return;
      }
      failuresRef.current += 1;
      if (failuresRef.current >= DISCONNECT_AFTER_FAILURES) {
        setStatus("disconnected");
      }
    } finally {
      inFlightRef.current = false;
    }
  }, [sessionId]);

  useEffect(() => {
    aliveRef.current = true;
    void poll();
    const timer = window.setInterval(() => {
      if (aliveRef.current) {
        void poll();
      }
    }, POLL_INTERVAL_MS);
    return () => {
      aliveRef.current = false;
      window.clearInterval(timer);
    };
  }, [poll]);

  const pollNow = useCallback(() => {
    void poll();
  }, [poll]);

  return { events, state, status, lastSuccessAt, pollNow };
}

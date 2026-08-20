/**
 * 캐릭터 만들기 화면 — 이 세션의 유일한 입장 경로다(Phase 12.3, D-10).
 *
 * 만들기가 완성 순간 자동으로 점유까지 끝내므로(`complete_creation`) 새
 * 브라우저가 고를 목록이 애초에 없고, 쿠키가 있는 브라우저는
 * `selected === true`로 세션에 바로 들어가며, 쿠키를 잃은 브라우저는
 * 명단이 잠긴 뒤 목록을 보여줘도 전부 점유돼 있어 같은 막다른 길로
 * 되돌아온다(Phase 8 D-01의 한계) — 그래서 「고르는 화면」이 따로 있을
 * 자리가 없다.
 *
 * **이 계획(12.3-01)의 뼈대는 최소다.** GM 안내(`announce`) 한 갈래만
 * 사건 → 폴링 → 화면까지 흐른다 — 지목·되묻기·정리·동의·항목 입력은
 * 12.3-02~05가 옆으로 넓힌다. 배치·색·간격을 설계하지 않는다(Phase 16) —
 * 기존 `screen`/`screen__inner`/`t-label` 클래스만 쓴다.
 */

import { useState } from "react";
import { announceCreation } from "../api/client.ts";
import { COPY } from "../labels.ts";
import { creationErrorMessage, gmLinesFrom } from "../session/creationView.ts";
import { usePolling } from "../session/usePolling.ts";
import { RosterLocked } from "./Notices.tsx";

/**
 * 이 계획은 룰북 선택 화면을 만들지 않는다(범위 밖, 12.3-CONTEXT.md §범위
 * 밖) — 인원 확정이 이미 열려 있는 유일한 룰북으로 진행된다. 12.3-02
 * 이후 여러 룰북을 실제로 고르게 되면 이 상수 대신 세션 상태에서 읽는다.
 */
const DEFAULT_RULEBOOK_ID = "dungeonworld_like";

interface CreationScreenProps {
  sessionId: string;
}

export function CreationScreen({ sessionId }: CreationScreenProps) {
  const feed = usePolling(sessionId);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const rosterLocked = feed.events.some((event) => event.event_type === "party_roster_locked");
  if (rosterLocked) {
    return <RosterLocked />;
  }

  async function announce(): Promise<void> {
    setPending(true);
    setError(null);
    try {
      await announceCreation(sessionId, DEFAULT_RULEBOOK_ID);
      feed.pollNow();
    } catch (err) {
      setError(creationErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  const gmLines = gmLinesFrom(feed.events);

  return (
    <div className="screen">
      <div className="screen__inner">
        <div className="screen__title">
          <p className="t-caps screen__eyebrow">세션 {sessionId}</p>
          <h1 className="t-display">{COPY.creationTitle}</h1>
        </div>

        {feed.status === "disconnected" ? <p className="t-label">{COPY.disconnected}</p> : null}

        {gmLines.length === 0 ? (
          <p className="t-label">{COPY.loading}</p>
        ) : (
          <div>
            {gmLines.map((line) => (
              <p key={line.seq} className="t-body">
                {line.say}
              </p>
            ))}
          </div>
        )}

        {error !== null ? <p className="t-label">{error}</p> : null}

        <button type="button" disabled={pending} onClick={() => void announce()}>
          {COPY.creationAnnounce}
        </button>
      </div>
    </div>
  );
}

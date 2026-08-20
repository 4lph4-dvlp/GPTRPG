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
 * **항목 조작이 배선된 자리는 `CreationPane`이다(12.3-04, D-06/D-08/
 * D-09).** 룰북 식별자(`state.creation_rulebook_id`)가 채워지기 전에는
 * 인원이 아직 확정되지 않은 것이라 항목 선언(`GET /creation/steps`)을
 * 아예 부르지 않는다(D-05) — 그동안은 GM의 말만 그대로 그린다. 방장이
 * 인원을 정하는 화면(host UI)과 동의 관문은 12.3-05가 옆으로 넓힌다.
 * 배치·색·간격을 설계하지 않는다(Phase 16) — 기존 `screen`/
 * `screen__inner`/`t-label` 클래스만 쓴다.
 *
 * **주사위 큐(D-07, 12.3-04 Task 3).** 만들기의 주사위는 `check_resolved`가
 * 아니라 `creation_step_completed` 사건의 `rolls` 칸에 남는다 —
 * `SessionScreen.tsx`의 기존 큐가 자동으로 잡지 않으므로, 여기서 같은
 * 패턴(`shownRef`/`MAX_QUEUED_ROLLS`)을 그대로 복제한다. `SessionScreen.tsx`
 * 자체는 이 계획에서 건드리지 않는다.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { announceCreation, fetchCreationSteps } from "../api/client.ts";
import type { CreationStepView, GameEvent } from "../api/types.ts";
import { DiceModal } from "../components/DiceModal.tsx";
import { COPY } from "../labels.ts";
import { CreationPane } from "../panes/CreationPane.tsx";
import { getBrowserId, getCreationCharacterId } from "../session/browserIdentity.ts";
import {
  type CreationRollQueueItem,
  creationErrorMessage,
  creationRollsFrom,
  gmLinesFrom,
} from "../session/creationView.ts";
import { usePolling } from "../session/usePolling.ts";
import { RosterLocked } from "./Notices.tsx";

/**
 * 이 계획은 룰북 선택 화면을 만들지 않는다(범위 밖, 12.3-CONTEXT.md §범위
 * 밖) — 인원 확정이 이미 열려 있는 유일한 룰북으로 진행된다. 12.3-02
 * 이후 여러 룰북을 실제로 고르게 되면 이 상수 대신 세션 상태에서 읽는다.
 */
const DEFAULT_RULEBOOK_ID = "dungeonworld_like";

/** `SessionScreen.tsx`의 주사위 큐와 같은 상한 — 세 건 넘게 밀리면
 * 나머지는 모달을 건너뛴다. */
const MAX_QUEUED_ROLLS = 3;

interface CreationScreenProps {
  sessionId: string;
}

export function CreationScreen({ sessionId }: CreationScreenProps) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [steps, setSteps] = useState<CreationStepView[]>([]);
  const [stepsLoaded, setStepsLoaded] = useState(false);
  const [rollQueue, setRollQueue] = useState<CreationRollQueueItem[]>([]);
  const shownRef = useRef<Set<number>>(new Set());

  const stepsById = useMemo(() => new Map(steps.map((step) => [step.step_id, step])), [steps]);

  const onLiveEvents = useCallback(
    (events: GameEvent[]) => {
      const rolls = creationRollsFrom(events, stepsById).filter(
        (item) => !shownRef.current.has(item.creationStep.seq),
      );
      if (rolls.length === 0) {
        return;
      }
      for (const item of rolls) {
        shownRef.current.add(item.creationStep.seq);
      }
      setRollQueue((previous) => [...previous, ...rolls].slice(0, MAX_QUEUED_ROLLS));
    },
    [stepsById],
  );

  const feed = usePolling(sessionId, onLiveEvents);

  // 세션 중에 안 바뀌는 값이라 rulebookId 하나에 대해 한 번만 부른다(D-05).
  // 인원이 아직 확정되지 않았으면(creation_rulebook_id가 null) 아예 안 부른다.
  const rulebookId = feed.state?.creation_rulebook_id ?? null;
  useEffect(() => {
    if (rulebookId === null) {
      return;
    }
    let alive = true;
    fetchCreationSteps(sessionId, rulebookId)
      .then((list) => {
        if (alive) {
          setSteps(list);
          setStepsLoaded(true);
        }
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [sessionId, rulebookId]);

  // 굴림 모달에 보일 이름 — `head.creationStep.character_id`를 찾는다.
  // `feed.state`가 갱신될 때마다 새로 계산되므로 큐잉 시점(onLiveEvents)이
  // 아니라 그리는 시점에 이 지도를 쓴다(순환 참조를 피한다 — usePolling에
  // 넘길 콜백은 feed 자체가 생기기 전에 만들어져야 한다).
  const nameById = useMemo(
    () => new Map((feed.state?.creation_characters ?? []).map((c) => [c.character_id, c.display_name])),
    [feed.state],
  );

  const rosterLocked = feed.events.some((event) => event.event_type === "party_roster_locked");
  if (rosterLocked) {
    return <RosterLocked />;
  }

  async function announce(): Promise<void> {
    setPending(true);
    setError(null);
    try {
      await announceCreation(sessionId, rulebookId ?? DEFAULT_RULEBOOK_ID);
      feed.pollNow();
    } catch (err) {
      setError(creationErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  const gmLines = gmLinesFrom(feed.events);
  const head = rollQueue[0];

  return (
    <div className="screen">
      <div className="screen__inner">
        <div className="screen__title">
          <p className="t-caps screen__eyebrow">세션 {sessionId}</p>
          <h1 className="t-display">{COPY.creationTitle}</h1>
        </div>

        {feed.status === "disconnected" ? <p className="t-label">{COPY.disconnected}</p> : null}

        {feed.state !== null && rulebookId !== null && stepsLoaded ? (
          <CreationPane
            sessionId={sessionId}
            browserId={getBrowserId(sessionId)}
            myCharacterId={getCreationCharacterId(sessionId)}
            rulebookId={rulebookId}
            state={feed.state}
            events={feed.events}
            steps={steps}
            pollNow={feed.pollNow}
          />
        ) : gmLines.length === 0 ? (
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

        {feed.state === null || rulebookId === null || !stepsLoaded ? (
          <button type="button" disabled={pending} onClick={() => void announce()}>
            {COPY.creationAnnounce}
          </button>
        ) : null}
      </div>

      {head !== undefined ? (
        <DiceModal
          key={head.creationStep.seq}
          roll={{
            creationStep: head.creationStep,
            label: head.label,
            actorName: nameById.get(head.creationStep.character_id) ?? head.creationStep.character_id,
          }}
          onDone={() => setRollQueue((previous) => previous.slice(1))}
        />
      ) : null}
    </div>
  );
}

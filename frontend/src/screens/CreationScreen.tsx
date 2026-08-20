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
 * 아예 부르지 않는다(D-05) — 그동안은 인원 확정 관문(아래)이 화면을
 * 차지한다.
 *
 * **인원 확정 관문(12.3-05 Task 1, D-11).** 이 화면이 마운트되는 동안
 * `HOST_BEACON_MS`마다 `claimCreationHost`를 불러 방장 재실 신호를
 * 보낸다 — 명단이 잠기면(`party_roster`가 채워지면) 멈춘다. 그 응답의
 * `you_are_host`만으로 「내가 방장인가」를 안다 — 폴링의
 * `creation_host_claimed`는 「누군가 잡았다」만 말한다. `partySizeGate`
 * (`session/creationView.ts`)가 이 둘을 조합해 네 갈래를 고른다.
 *
 * **동의 관문과 세션 진입(12.3-05 Task 2, D-03/D-11).** 정리·동의는
 * `CreationPane`이 대화 줄기 안에서 보인다(D-06). `state.party_roster`가
 * 채워지면 이 화면은 서버를 다시 조회하지 않고 `onEntered(characterId)`로
 * `App`에 알린다 — `complete_creation`이 이미 쿠키를 구웠다. 명단이
 * 잠겼는데 내 캐릭터가 없으면(늦게 들어온 브라우저) `RosterLocked`로
 * 간다.
 *
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
import { announceCreation, claimCreationHost, fetchCreationSteps, fixPartySize } from "../api/client.ts";
import type { CreationStepView, GameEvent } from "../api/types.ts";
import { DiceModal } from "../components/DiceModal.tsx";
import { HOST_BEACON_MS } from "../config.ts";
import { COPY } from "../labels.ts";
import { CreationPane } from "../panes/CreationPane.tsx";
import { getBrowserId, getCreationCharacterId } from "../session/browserIdentity.ts";
import {
  type CreationRollQueueItem,
  creationErrorMessage,
  creationRollsFrom,
  gmLinesFrom,
  partySizeGate,
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

/**
 * 방장에게만 보이는 인원 확정 조작(D-11) — 인원 범위(예: 3~5명) 숫자를
 * 여기 하드코딩하지 않는다. 사람이 숫자를 고르면 서버가 룰북 범위
 * (`validate_party_size`)와 절대 상한(`PARTY_MEMBER_LIMIT`)을 검사하고,
 * 범위 밖이면 409 + `detail`로 거절한 문장을 그대로 보여준다(D-15).
 */
function PartySizeControl({
  sessionId,
  rulebookId,
  browserId,
  onDone,
  onError,
}: {
  sessionId: string;
  rulebookId: string;
  browserId: string;
  onDone: () => void;
  onError: (message: string) => void;
}) {
  const [count, setCount] = useState(1);
  const [busy, setBusy] = useState(false);

  async function confirm(): Promise<void> {
    setBusy(true);
    try {
      await fixPartySize(sessionId, count, rulebookId, browserId);
      onDone();
    } catch (err) {
      onError(creationErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="proposal">
      <p className="t-caps">{COPY.creationPartySizeTitle}</p>
      <input
        type="number"
        min={1}
        value={count}
        disabled={busy}
        onChange={(event) => setCount(Number(event.target.value))}
      />
      <button
        type="button"
        className="btn btn--primary btn--wide"
        disabled={busy}
        onClick={() => void confirm()}
      >
        {COPY.creationPartySizeConfirm}
      </button>
    </div>
  );
}

interface CreationScreenProps {
  sessionId: string;
  /** 명단이 잠기고 내 캐릭터가 그 안에 있으면 불린다(D-11 뒤, Task 2) —
   * `App`이 이 콜백으로 `Gate`를 `{ kind: "ready", characterId }`로
   * 바꾼다. `complete_creation`이 이미 쿠키를 구웠으므로 새 조회가
   * 필요 없다. */
  onEntered: (characterId: string) => void;
}

export function CreationScreen({ sessionId, onEntered }: CreationScreenProps) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [steps, setSteps] = useState<CreationStepView[]>([]);
  const [stepsLoaded, setStepsLoaded] = useState(false);
  const [rollQueue, setRollQueue] = useState<CreationRollQueueItem[]>([]);
  const [youAreHost, setYouAreHost] = useState(false);
  const shownRef = useRef<Set<number>>(new Set());

  const myBrowserId = getBrowserId(sessionId);
  const myCharacterId = getCreationCharacterId(sessionId);

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

  const partyRoster = feed.state?.party_roster ?? null;

  // 이 요청 시점에 방장이 「이미」 있었는지(폴링이 마지막으로 알려준
  // 값) — 렌더마다 갱신되는 ref라 beacon() 안에서 항상 최신 값을 읽는다
  // (effect 의존성에 넣으면 폴링마다 새 참조가 와서 타이머가 매번 다시
  // 서므로 안 된다, 아래 주석 참조). `creation_host_claimed`는 여부만
  // 담아 안전하다(T-12.3-05) — 이 자체가 새는 값이 아니다.
  const hostClaimedBeforeRef = useRef(false);
  hostClaimedBeforeRef.current = feed.state?.creation_host_claimed ?? false;

  // 방장이 사라져 내가 이어받았을 때만 붙는 짧은 맥락(D-11). **더는
  // 폴링 events에서 `creation_host_claimed.browser_id`를 읽지 않는다**
  // (12.3-REVIEW.md CR-03) — 그 칸은 남의 식별자를 실어 나르므로 세션의
  // 모든 브라우저가 방장의 값을 읽을 수 있었다. 이 신호는 이 브라우저
  // 자신의 `POST /creation/host` 응답(`changed`+`you_are_host`)과, 그
  // 직전 폴링이 이미 공개적으로 내려준 `creation_host_claimed`(여부만)
  // 조합만으로 판단한다 — 아무 것도 새로 새지 않는다.
  const [hostTookOver, setHostTookOver] = useState(false);

  // 방장 재실 신호(D-11, Task 1) — HOST_BEACON_MS(HOST_IDLE_S의 절반)마다
  // claimCreationHost를 부른다. 명단이 잠기면(partyRoster !== null) 멈춘다
  // — 그때는 방장 개념이 쓸모없고 서버도 아무 사건을 안 낸다.
  useEffect(() => {
    if (partyRoster !== null) {
      return;
    }
    let alive = true;
    async function beacon(): Promise<void> {
      try {
        const response = await claimCreationHost(sessionId, myBrowserId);
        if (!alive) {
          return;
        }
        setYouAreHost(response.you_are_host);
        // 「바뀌었고(changed) 지금 나(you_are_host)」인데 그 직전까지도
        // 방장이 이미 있었다면(hostClaimedBeforeRef) 승계다 — 방장이
        // 아직 아무도 없던 상태에서 changed===true면 그냥 내가 처음
        // 잡은 것뿐이라 안내 문구를 보일 이유가 없다.
        if (response.changed && response.you_are_host && hostClaimedBeforeRef.current) {
          setHostTookOver(true);
        }
      } catch {
        // 신호 실패는 다음 주기로 넘긴다 — 화면 오류로 보이지 않는다.
      }
    }
    void beacon();
    const timer = window.setInterval(() => void beacon(), HOST_BEACON_MS);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
    // partyRoster는 null 여부만 본다 — 배열 자체는 폴링마다 새 참조라
    // 매번 타이머를 다시 세우면 주기가 지켜지지 않는다.
  }, [sessionId, myBrowserId, partyRoster !== null]);

  // 명단 잠금 -> 세션 진입(D-11 뒤, Task 2). 서버를 다시 조회하지 않는다
  // — complete_creation이 이미 쿠키를 구웠다.
  useEffect(() => {
    if (partyRoster !== null && partyRoster.includes(myCharacterId)) {
      onEntered(myCharacterId);
    }
  }, [partyRoster, myCharacterId, onEntered]);

  if (partyRoster !== null) {
    if (!partyRoster.includes(myCharacterId)) {
      return <RosterLocked />;
    }
    // onEntered가 위 effect에서 이미 App의 Gate를 바꾸는 중이다 — 그
    // 렌더가 반영될 때까지 잠깐 이 화면 대신 로딩만 보인다.
    return (
      <div className="screen">
        <div className="screen__inner">
          <p className="t-label">{COPY.loading}</p>
        </div>
      </div>
    );
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
  const gate = feed.state !== null ? partySizeGate(feed.state, youAreHost) : null;

  return (
    <div className="screen">
      <div className="screen__inner">
        <div className="screen__title">
          <p className="t-caps screen__eyebrow">세션 {sessionId}</p>
          <h1 className="t-display">{COPY.creationTitle}</h1>
        </div>

        {feed.status === "disconnected" ? <p className="t-label">{COPY.disconnected}</p> : null}

        {gate === "fix" ? (
          <div>
            {hostTookOver ? <p className="t-label">{COPY.creationHostTookOver}</p> : null}
            <PartySizeControl
              sessionId={sessionId}
              rulebookId={DEFAULT_RULEBOOK_ID}
              browserId={myBrowserId}
              onDone={feed.pollNow}
              onError={setError}
            />
          </div>
        ) : gate === "waiting_for_host" ? (
          <p className="t-label">{COPY.creationWaitingForHost}</p>
        ) : gate === "done" ? (
          feed.state !== null && rulebookId !== null && stepsLoaded ? (
            <CreationPane
              sessionId={sessionId}
              browserId={myBrowserId}
              myCharacterId={myCharacterId}
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
          )
        ) : (
          <p className="t-label">{COPY.loading}</p>
        )}

        {error !== null ? <p className="t-label">{error}</p> : null}

        {/* CR-02 (12.3-REVIEW.md): stepsLoaded는 GET /creation/steps 조회가
            끝났는지일 뿐 안내 여부와 무관하다 — fetchCreationSteps는 AI를
            안 부르는 단순 조회라 안내를 누르기도 전에 이미 끝나는 것이
            보통이었다. 이 버튼은 "아직 안내가 없다"(gmLines가 비어 있다)
            로만 켜진다 — stepsLoaded와 별개로, CreationPane이 이미
            렌더되고 있어도 안내가 없으면 계속 보인다. */}
        {gate === "done" && gmLines.length === 0 ? (
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

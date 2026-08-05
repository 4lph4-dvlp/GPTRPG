/**
 * 세션 화면 — 3컬럼을 조립하고, 폴링에서 나오는 값을 세 판에 나눠 준다.
 *
 * 주사위 큐가 여기 있다: `usePolling`이 「진짜 새로 생긴 사건」만 넘겨주므로
 * (첫 응답 = 과거는 걸러져 있다) 그중 `check_resolved`만 모아 한 번에 하나씩
 * 모달로 흘린다. 세 건 넘게 밀리면 나머지는 모달을 건너뛴다 — 두 명이 동시에
 * 확인해서 주사위가 줄 서서 10초씩 뜨는 상황을 만들지 않는다. 건너뛴 판정도
 * 카드의 판정 줄에는 그대로 남는다(연출은 사라져도 기록은 남는다).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchCharacterSheet, fetchCharacters } from "../api/client.ts";
import { DiceModal } from "../components/DiceModal.tsx";
import { COPY } from "../labels.ts";
import { ChatPane } from "../panes/ChatPane.tsx";
import { StatusPane } from "../panes/StatusPane.tsx";
import { StoryPane } from "../panes/StoryPane.tsx";
import { groupTurns } from "../session/groupTurns.ts";
import { usePolling } from "../session/usePolling.ts";
import type {
  CharacterSheet,
  CharacterSummary,
  CheckResolvedEvent,
  GameEvent,
} from "../api/types.ts";

/** 동시에 밀릴 수 있는 주사위 연출의 최대 개수. */
const MAX_QUEUED_ROLLS = 3;

const CLOCK_PULSE_MS = 3000;
const CHECK_HIGHLIGHT_MS = 1800;

interface SessionScreenProps {
  sessionId: string;
  characterId: string;
  onChangeCharacter: () => void;
}

export function SessionScreen({
  sessionId,
  characterId,
  onChangeCharacter,
}: SessionScreenProps) {
  const [queue, setQueue] = useState<CheckResolvedEvent[]>([]);
  const [justRevealedSeq, setJustRevealedSeq] = useState<number | null>(null);
  const [clockPulsing, setClockPulsing] = useState(false);
  const [failedDeclareSeqs, setFailedDeclareSeqs] = useState<Set<number>>(new Set());
  const shownRef = useRef<Set<number>>(new Set());

  const onLiveEvents = useCallback((events: GameEvent[]) => {
    const checks: CheckResolvedEvent[] = [];
    let clockAdvanced = false;
    for (const event of events) {
      if (event.event_type === "check_resolved" && !shownRef.current.has(event.seq)) {
        shownRef.current.add(event.seq);
        checks.push(event);
      }
      if (event.event_type === "clock_advanced") {
        clockAdvanced = true;
      }
    }
    if (checks.length > 0) {
      setQueue((previous) => [...previous, ...checks].slice(0, MAX_QUEUED_ROLLS));
    }
    if (clockAdvanced) {
      setClockPulsing(true);
    }
  }, []);

  const feed = usePolling(sessionId, onLiveEvents);

  useEffect(() => {
    if (!clockPulsing) {
      return;
    }
    const timer = window.setTimeout(() => setClockPulsing(false), CLOCK_PULSE_MS);
    return () => window.clearTimeout(timer);
  }, [clockPulsing]);

  useEffect(() => {
    if (justRevealedSeq === null) {
      return;
    }
    const timer = window.setTimeout(() => setJustRevealedSeq(null), CHECK_HIGHLIGHT_MS);
    return () => window.clearTimeout(timer);
  }, [justRevealedSeq]);

  const [characters, setCharacters] = useState<CharacterSummary[]>([]);
  const [sheet, setSheet] = useState<CharacterSheet | null>(null);
  const [sheetError, setSheetError] = useState(false);

  useEffect(() => {
    let alive = true;
    fetchCharacters(sessionId)
      .then((list) => alive && setCharacters(list))
      .catch(() => undefined);
    fetchCharacterSheet(sessionId, characterId)
      .then((value) => alive && setSheet(value))
      .catch(() => alive && setSheetError(true));
    return () => {
      alive = false;
    };
  }, [sessionId, characterId]);

  const nameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const character of characters) {
      map.set(character.character_id, character.display_name);
    }
    return map;
  }, [characters]);

  // player_id === character_id (D-42). 목록을 아직 못 받았으면 원래 id를 그대로
  // 보여준다 — 화면이 막히지 않는다.
  const nameOf = useCallback(
    (playerId: string) => nameById.get(playerId) ?? playerId,
    [nameById],
  );

  const turns = useMemo(() => groupTurns(feed.events), [feed.events]);

  const head = queue[0];
  const headTurn =
    head === undefined ? undefined : turns.find((turn) => turn.check?.seq === head.seq);

  const archetype =
    characters.find((character) => character.character_id === characterId)?.archetype ?? null;

  const onTurnFailed = useCallback((declareSeq: number) => {
    setFailedDeclareSeqs((previous) => new Set(previous).add(declareSeq));
  }, []);

  // 끊긴 동안에는 폴링이 상태를 갱신하지 못하므로 "마지막 갱신 N초 전"이 그
  // 자리에 얼어붙는다. 멈춘 숫자는 끊겼다는 사실보다 더 헷갈리게 만든다.
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (feed.status !== "disconnected") {
      return;
    }
    const timer = window.setInterval(() => setTick((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [feed.status]);

  if (feed.status === "loading") {
    return (
      <div className="screen">
        <div className="screen__inner">
          <div className="spinner" aria-label={COPY.loading} />
        </div>
      </div>
    );
  }

  // `tick`은 1초마다 이 계산을 다시 돌리기 위한 것뿐이다 — 값 자체는 안 쓴다.
  void tick;
  const secondsSince =
    feed.lastSuccessAt === null ? null : Math.round((Date.now() - feed.lastSuccessAt) / 1000);

  return (
    <>
      {feed.status === "disconnected" ? (
        <div className="topstrip" role="status" aria-live="polite">
          <span className="topstrip__dot" />
          <span className="t-label" style={{ color: "#f0b0a8" }}>
            {COPY.disconnected}
            {secondsSince !== null ? ` · 마지막 갱신 ${secondsSince}초 전` : ""}
          </span>
        </div>
      ) : null}

      <div className="shell">
        <StatusPane
          sheet={sheet}
          sheetError={sheetError}
          archetype={archetype}
          state={feed.state}
          characters={characters}
          myCharacterId={characterId}
          clockPulsing={clockPulsing}
          onChangeCharacter={onChangeCharacter}
        />

        <StoryPane
          turns={turns}
          nameOf={nameOf}
          segmentCount={feed.state?.clock_segment_count ?? 4}
          justRevealedSeq={justRevealedSeq}
          failedDeclareSeqs={failedDeclareSeqs}
        />

        <ChatPane
          turns={turns}
          nameOf={nameOf}
          sessionId={sessionId}
          characterId={characterId}
          onTurnFailed={onTurnFailed}
          pollNow={feed.pollNow}
        />
      </div>

      {head !== undefined ? (
        <DiceModal
          key={head.seq}
          roll={{
            check: head,
            actorName: headTurn === undefined ? "" : nameOf(headTurn.playerId),
          }}
          onDone={() => {
            setJustRevealedSeq(head.seq);
            setQueue((previous) => previous.slice(1));
          }}
        />
      ) : null}
    </>
  );
}

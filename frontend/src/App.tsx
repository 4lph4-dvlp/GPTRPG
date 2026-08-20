/**
 * 화면 갈래 — 세션 식별자 확인 → 캐릭터 확인 → 만들기 또는 세션 화면.
 *
 * 세션 식별자는 `location.search`의 `session`에서만 읽는다. 네 명이 받는 링크는
 * `http://{host}/?session={id}` 하나뿐이다(D-42).
 *
 * **만들기가 이 세션의 유일한 입장 경로다(Phase 12.3, D-10).** 자기
 * 캐릭터가 없으면 항상 `CreationScreen`으로 간다 — 캐릭터 고르기 화면을
 * 거치지 않는다. 조회 자체가 실패해도(400 제외) `creating`으로 보낸다 —
 * 만들기가 유일한 입장 경로이므로 막다른 길이 구조적으로 안 생긴다.
 *
 * 캐릭터가 정해지기 전에는 판정 폴링을 시작하지 않는다 — `SessionScreen`이
 * 아예 마운트되지 않으므로 구조적으로 그렇게 된다(`CreationScreen`은 자기
 * 폴링을 따로 쓴다).
 */

import { useEffect, useState } from "react";
import { ApiError, fetchMyCharacter } from "./api/client.ts";
import { InvalidSession, Loading, MissingSession } from "./screens/Notices.tsx";
import { CreationScreen } from "./screens/CreationScreen.tsx";
import { SessionScreen } from "./screens/SessionScreen.tsx";

type Gate =
  | { kind: "checking" }
  | { kind: "invalid" }
  | { kind: "creating" }
  | { kind: "ready"; characterId: string };

export function App() {
  const sessionId = new URLSearchParams(window.location.search).get("session");
  const [gate, setGate] = useState<Gate>({ kind: "checking" });

  useEffect(() => {
    if (sessionId === null) {
      return;
    }
    let alive = true;
    fetchMyCharacter(sessionId)
      .then((response) => {
        if (!alive) {
          return;
        }
        // 쿠키가 이미 유효하면 입장 화면을 아예 그리지 않는다(D-43).
        setGate(
          response.selected && response.character_id !== null
            ? { kind: "ready", characterId: response.character_id }
            : { kind: "creating" },
        );
      })
      .catch((error: unknown) => {
        if (!alive) {
          return;
        }
        setGate(
          error instanceof ApiError && error.status === 400
            ? { kind: "invalid" }
            : // 조회가 실패한 것뿐이니 만들기 화면으로 보낸다 — 그 화면이
              // 자기 오류 문구를 띄운다.
              { kind: "creating" },
        );
      });
    return () => {
      alive = false;
    };
  }, [sessionId]);

  if (sessionId === null) {
    return <MissingSession />;
  }

  switch (gate.kind) {
    case "checking":
      return <Loading />;
    case "invalid":
      return <InvalidSession sessionId={sessionId} />;
    case "creating":
      return (
        <CreationScreen
          sessionId={sessionId}
          onEntered={(characterId) => setGate({ kind: "ready", characterId })}
        />
      );
    case "ready":
      return (
        <SessionScreen key={gate.characterId} sessionId={sessionId} characterId={gate.characterId} />
      );
  }
}

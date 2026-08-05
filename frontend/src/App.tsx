/**
 * 화면 갈래 — 세션 식별자 확인 → 캐릭터 확인 → 세션 화면.
 *
 * 세션 식별자는 `location.search`의 `session`에서만 읽는다. 네 명이 받는 링크는
 * `http://{host}/?session={id}` 하나뿐이다(D-42).
 *
 * 캐릭터가 정해지기 전에는 폴링을 시작하지 않는다 — `SessionScreen`이 아예
 * 마운트되지 않으므로 구조적으로 그렇게 된다.
 */

import { useEffect, useState } from "react";
import { ApiError, fetchMyCharacter } from "./api/client.ts";
import { CharacterSelect } from "./screens/CharacterSelect.tsx";
import { InvalidSession, Loading, MissingSession } from "./screens/Notices.tsx";
import { SessionScreen } from "./screens/SessionScreen.tsx";

type Gate =
  | { kind: "checking" }
  | { kind: "invalid" }
  | { kind: "choosing" }
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
            : { kind: "choosing" },
        );
      })
      .catch((error: unknown) => {
        if (!alive) {
          return;
        }
        setGate(
          error instanceof ApiError && error.status === 400
            ? { kind: "invalid" }
            : // 쿠키 조회가 실패한 것뿐이니 고르는 화면으로 보낸다 — 목록
              // 조회까지 실패하면 그 화면이 자기 오류 문구를 띄운다.
              { kind: "choosing" },
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
    case "choosing":
      return (
        <CharacterSelect
          sessionId={sessionId}
          onSelected={(characterId) => setGate({ kind: "ready", characterId })}
        />
      );
    case "ready":
      return (
        <SessionScreen
          key={gate.characterId}
          sessionId={sessionId}
          characterId={gate.characterId}
          // 쿠키는 httponly라 브라우저에서 지울 수 없다. 다시 고르면
          // `POST /select-character`가 같은 쿠키를 덮어쓴다 — 서버를 고치지
          // 않고 "캐릭터 바꾸기"를 만드는 방법이 이것뿐이다.
          onChangeCharacter={() => setGate({ kind: "choosing" })}
        />
      );
  }
}

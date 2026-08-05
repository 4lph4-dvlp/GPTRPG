/**
 * 입장 화면 — 캐릭터 고르기.
 *
 * 캐릭터가 하나뿐이어도 자동으로 고르지 않는다(D-42/D-43) — 쿠키는 사람이
 * 실제로 누른 결과로만 남는다.
 *
 * 카드는 세로줄이 아니라 격자다(넷이면 2×2). 개수를 세어 분기하지 않는다 —
 * `auto-fit`이 폭에 맞춰 접으므로 캐릭터가 여섯이든 아홉이든 같은 코드가
 * 3열까지 알아서 편다.
 *
 * 초상화는 **있으면 좋은 것**이다. 서버가 파일이 실제로 있는 캐릭터에만
 * `portrait_url`을 채워 주므로(`routes_characters.py`) 아직 안 뽑은 캐릭터는
 * 이름 첫 글자를 문장처럼 앉힌 자리로 대신한다 — 404 나는 `<img>`를 그리지
 * 않는다.
 */

import { useEffect, useState } from "react";
import { fetchCharacters, selectCharacter } from "../api/client.ts";
import type { CharacterSummary } from "../api/types.ts";
import { COPY } from "../labels.ts";

interface CharacterSelectProps {
  sessionId: string;
  onSelected: (characterId: string) => void;
}

function CharacterCard({
  character,
  disabled,
  onChoose,
}: {
  character: CharacterSummary;
  disabled: boolean;
  onChoose: () => void;
}) {
  return (
    <button
      type="button"
      className="char-card"
      aria-label={`${character.display_name} — 이 캐릭터로 입장하기`}
      disabled={disabled}
      onClick={onChoose}
    >
      <span className="char-card__portrait">
        {/* `!= null`은 일부러 느슨한 비교다 — 초상화를 붙이기 전 서버는 이 칸을
            아예 안 보내고, 그때 값은 `null`이 아니라 `undefined`다. 엄격 비교로
            두면 `<img src={undefined}>`가 그려진다. */}
        {character.portrait_url != null ? (
          <img src={character.portrait_url} alt="" />
        ) : (
          <span className="char-card__sigil" aria-hidden="true">
            {character.display_name.slice(0, 1)}
          </span>
        )}
      </span>
      <span className="char-card__body">
        <span className="char-card__name">{character.display_name}</span>
        <span className="char-card__divider" aria-hidden="true" />
        <span className="char-card__archetype">{character.archetype}</span>
      </span>
    </button>
  );
}

export function CharacterSelect({ sessionId, onSelected }: CharacterSelectProps) {
  const [characters, setCharacters] = useState<CharacterSummary[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [pending, setPending] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetchCharacters(sessionId)
      .then((list) => {
        if (alive) {
          setCharacters(list);
        }
      })
      .catch(() => {
        if (alive) {
          setFailed(true);
        }
      });
    return () => {
      alive = false;
    };
  }, [sessionId]);

  async function choose(characterId: string): Promise<void> {
    setPending(characterId);
    try {
      await selectCharacter(sessionId, characterId);
      onSelected(characterId);
    } catch {
      setPending(null);
      setFailed(true);
    }
  }

  return (
    <div className="screen">
      <div className="screen__inner screen__inner--wide">
        <div className="screen__title">
          <p className="t-caps screen__eyebrow">세션 {sessionId}</p>
          <h1 className="t-display">캐릭터를 선택하세요</h1>
        </div>

        {failed ? (
          <p className="t-label">{COPY.characterListError}</p>
        ) : characters === null ? (
          <div className="spinner" aria-label={COPY.loading} />
        ) : (
          <div className="char-grid">
            {characters.map((character) => (
              <CharacterCard
                key={character.character_id}
                character={character}
                disabled={pending !== null}
                onChoose={() => void choose(character.character_id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

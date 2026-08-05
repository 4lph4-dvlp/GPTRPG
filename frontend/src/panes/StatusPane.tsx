/**
 * 좌측 상태판 — 내가 누구고, 지금 판이 어디까지 왔는지.
 *
 * 여기 있는 값은 폴링이 매번 새로 그려도 흔들리지 않아야 한다. 캐릭터 시트는
 * 사건으로 변하지 않는 읽기 전용 자료라(`routes_characters.py`) 한 번만 불러
 * 두고, 시계·실패 카운터만 폴링 상태를 따라 움직인다.
 *
 * **재촉하지 않는다** — 실패 카운터가 2/3여도 색이 붉어지거나 "곧 시계가
 * 돕니다" 같은 말이 붙지 않는다. 지금 상태를 알려 주는 정보이지 사람을
 * 몰아세우는 장치가 아니다.
 */

import { ThreatClock } from "../components/ThreatClock.tsx";
import { COPY, statLabel } from "../labels.ts";
import type { CharacterSheet, CharacterSummary, GameStateView } from "../api/types.ts";

interface StatusPaneProps {
  sheet: CharacterSheet | null;
  sheetError: boolean;
  archetype: string | null;
  state: GameStateView | null;
  characters: CharacterSummary[];
  myCharacterId: string;
  clockPulsing: boolean;
  onChangeCharacter: () => void;
}

function StatRows({ sheet }: { sheet: CharacterSheet }) {
  return (
    <>
      {sheet.stats.map((stat) =>
        stat.max === null ? (
          <div className="stat-row" key={stat.name}>
            <span className="stat-row__name">{statLabel(stat.name)}</span>
            <span className="stat-row__value">
              {stat.current > 0 ? `+${stat.current}` : stat.current}
            </span>
          </div>
        ) : (
          <div className="stat-gauge" key={stat.name}>
            <div className="stat-gauge__head">
              <span className="stat-row__name">{statLabel(stat.name)}</span>
              <span className="stat-row__value">
                {stat.current}/{stat.max}
              </span>
            </div>
            <div className="gauge">
              <div
                className="gauge__fill"
                style={{
                  width: `${Math.max(0, Math.min(100, (stat.current / stat.max) * 100))}%`,
                }}
              />
            </div>
          </div>
        ),
      )}
    </>
  );
}

export function StatusPane({
  sheet,
  sheetError,
  archetype,
  state,
  characters,
  myCharacterId,
  clockPulsing,
  onChangeCharacter,
}: StatusPaneProps) {
  const segmentCount = state?.clock_segment_count ?? 4;
  const segment = state?.clock_segment ?? 0;
  const threshold = state?.auto_advance_threshold ?? 3;
  const fails = state?.fails_since_clock ?? 0;

  return (
    <aside className="pane pane--status">
      <div className="brand">
        <span className="brand__mark">GPTRPG</span>
      </div>

      <div className="status-block">
        <div className="identity">
          <div className="identity__name">{sheet?.display_name ?? "…"}</div>
          {archetype !== null ? <div className="identity__archetype">{archetype}</div> : null}
        </div>
        {sheet !== null ? (
          <div>
            <StatRows sheet={sheet} />
          </div>
        ) : sheetError ? (
          <p className="t-label">{COPY.characterSheetError}</p>
        ) : (
          <p className="t-label">{COPY.loading}</p>
        )}
        <button type="button" className="linkish" onClick={onChangeCharacter}>
          캐릭터 바꾸기
        </button>
      </div>

      <div className="status-block">
        <p className="t-caps">위협 시계</p>
        <div className="clock">
          <ThreatClock
            segment={segment}
            segmentCount={segmentCount}
            pulsing={clockPulsing}
            size={58}
          />
          <div className="clock__meta">
            <span className="clock__count">
              {Math.min(segment, segmentCount)}/{segmentCount}
            </span>
            <span className="t-label">
              {segment >= segmentCount ? "마지막 칸" : "판정 실패가 쌓이면 진행돼요"}
            </span>
          </div>
        </div>
      </div>

      <div className="status-block">
        <p className="t-caps">실패 카운터</p>
        <div className="pips" role="img" aria-label={`실패 ${fails}/${threshold}`}>
          {Array.from({ length: threshold }, (_, index) => (
            <span key={index} className={index < fails ? "pip pip--on" : "pip"} />
          ))}
        </div>
        <span className="t-label">
          {threshold - Math.min(fails, threshold)}번 더 실패하면 시계가 한 칸 넘어가요
        </span>
      </div>

      <div className="status-block status-block--party">
        <p className="t-caps">함께 하는 사람</p>
        <div>
          {characters.map((character) => (
            <div
              className={
                character.character_id === myCharacterId ? "party-row party-row--me" : "party-row"
              }
              key={character.character_id}
            >
              <span className="party-row__dot" />
              <span className="party-row__name">{character.display_name}</span>
            </div>
          ))}
        </div>
      </div>

      {state !== null ? (
        <details className="status-block status-block--record record">
          <summary className="t-caps">세션 기록 (진행자용)</summary>
          <div className="record__grid">
            <span>턴 수</span>
            <b>{state.turn_count}</b>
            <span>판정 수</span>
            <b>{state.check_count}</b>
            <span>실패 누적</span>
            <b>{state.failure_count}</b>
            <span>시계 진행</span>
            <b>{state.clock_advances}</b>
            <span>서사 조각</span>
            <b>{state.narration_count}</b>
            <span>AI 호출</span>
            <b>{state.ai_calls}</b>
            <span>토큰 합계</span>
            <b>{state.total_tokens.toLocaleString("ko-KR")}</b>
            <span>마지막 순번</span>
            <b>{state.last_seq}</b>
          </div>
        </details>
      ) : null}
    </aside>
  );
}

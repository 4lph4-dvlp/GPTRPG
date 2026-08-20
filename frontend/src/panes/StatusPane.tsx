/**
 * 좌측 상태판 — 내가 누구고, 지금 판이 어디까지 왔는지.
 *
 * **캐릭터 시트는 더 이상 한 번만 불러 두는 읽기 전용 자료가 아니다
 * (RULE-06, D-65, 12-01).** `characters_data.py`의 값은 「시작값」일
 * 뿐이고, 지금 값은 사건을 접어 만든다 — 그래서 시트는 자원이 변할 때마다
 * `SessionScreen`이 다시 불러 이 판에 새 값을 내려보낸다. 폴링이 매번
 * 새로 그려도 흔들리지 않아야 하는 것은 시계·실패 카운터뿐이었지만, 이제는
 * 시트 자체도 그 목록에 들어간다.
 *
 * **재촉하지 않는다** — 실패 카운터가 2/3여도 색이 붉어지거나 "곧 시계가
 * 돕니다" 같은 말이 붙지 않는다. 지금 상태를 알려 주는 정보이지 사람을
 * 몰아세우는 장치가 아니다. 자원 변화 표시(`ResourceChangeBadge`)도 같은
 * 규율을 물려받는다 — 깜빡이거나 재촉하지 않고 잠시 뒤 조용히 가라앉는다.
 */

import { ResourceChangeBadge } from "../components/ResourceChangeBadge.tsx";
import { ThreatClock } from "../components/ThreatClock.tsx";
import { COPY, statLabel } from "../labels.ts";
import type { CharacterSheet, CharacterSummary, GameStateView } from "../api/types.ts";

/** 방금 이 축에서 일어난 변화 하나 — `SessionScreen`이 `resource_changed`
 * 사건과 다시 불러온 시트로 `changeIntensity`를 계산해 채운다(D-19). 축
 * 이름이 이 맵에 없으면 최근에 변한 적이 없다는 뜻이고, 그 축은 배지를
 * 안 그린다. */
export interface RecentResourceChange {
  amount: number;
  intensity: number;
}

interface StatusPaneProps {
  sheet: CharacterSheet | null;
  sheetError: boolean;
  archetype: string | null;
  state: GameStateView | null;
  characters: CharacterSummary[];
  myCharacterId: string;
  clockPulsing: boolean;
  recentChanges: Record<string, RecentResourceChange>;
}

/** 이 축의 방금 변화가 있으면(D-19) `ResourceChangeBadge`를, 없으면
 * `null`을 돌려준다 — 여섯 형태 렌더 갈래마다 이 한 줄만 덧붙인다. */
function badgeFor(name: string, recentChanges: Record<string, RecentResourceChange>) {
  const change = recentChanges[name];
  if (change === undefined) {
    return null;
  }
  return <ResourceChangeBadge amount={change.amount} intensity={change.intensity} />;
}

/** `named_slots` 형태 — 고정 길이 격자. 칸 개수는 `slot_values`의 배열
 * 길이를 그대로 쓴다(상한 상수를 코드에 두지 않는다). 빈 칸은
 * `COPY.emptySlot`, 채워진 칸은 그 문자열을 보인다. */
function SlotGrid({
  name,
  slotValues,
  recentChanges,
}: {
  name: string;
  slotValues: (string | null)[];
  recentChanges: Record<string, RecentResourceChange>;
}) {
  return (
    <div className="stat-slots">
      <span className="stat-row__name">
        {statLabel(name)}
        {badgeFor(name, recentChanges)}
      </span>
      <div className="stat-slots__grid">
        {slotValues.map((value, index) => (
          <span key={index} className={value === null ? "slot slot--empty" : "slot slot--filled"}>
            {value ?? COPY.emptySlot}
          </span>
        ))}
      </div>
    </div>
  );
}

/** `tag_list` 형태 — 칩 목록. 빈 배열도 회색 비활성 패널이 아니라 축
 * 이름 + 「없음」 중립 표시로 그린다. */
function TagList({
  name,
  tags,
  recentChanges,
}: {
  name: string;
  tags: string[];
  recentChanges: Record<string, RecentResourceChange>;
}) {
  return (
    <div className="stat-tags">
      <span className="stat-row__name">
        {statLabel(name)}
        {badgeFor(name, recentChanges)}
      </span>
      {tags.length === 0 ? (
        <span className="t-label">없음</span>
      ) : (
        <div className="stat-tags__chips">
          {tags.map((tag) => (
            <span className="chip" key={tag}>
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/** `usage_die` 형태 — 남은 주사위 면수를 「d{면수}」로, `0`이면
 * `COPY.usageDieSpent`로 소진 상태를 보인다. */
function UsageDie({
  name,
  current,
  recentChanges,
}: {
  name: string;
  current: number;
  recentChanges: Record<string, RecentResourceChange>;
}) {
  return (
    <div className="stat-usage-die">
      <span className="stat-row__name">
        {statLabel(name)}
        {badgeFor(name, recentChanges)}
      </span>
      <span className="stat-row__value">{current === 0 ? COPY.usageDieSpent : `d${current}`}</span>
    </div>
  );
}

function StatRows({
  sheet,
  recentChanges,
}: {
  sheet: CharacterSheet;
  recentChanges: Record<string, RecentResourceChange>;
}) {
  if (sheet.stats.length === 0) {
    // 자원 축이 하나도 없는 룰북 — 회색 빈 패널이 아니라 의도된 한 줄을
    // 보인다(CONTEXT.md Claude's Discretion).
    return <p className="t-label">{COPY.noResourceAxes}</p>;
  }
  return (
    <>
      {sheet.stats.map((stat) => {
        if (stat.form === "numeric") {
          const current = stat.current ?? 0;
          return stat.max === null ? (
            <div className="stat-row" key={stat.name}>
              <span className="stat-row__name">
                {statLabel(stat.name)}
                {badgeFor(stat.name, recentChanges)}
              </span>
              <span className="stat-row__value">{current > 0 ? `+${current}` : current}</span>
            </div>
          ) : (
            <div className="stat-gauge" key={stat.name}>
              <div className="stat-gauge__head">
                <span className="stat-row__name">
                  {statLabel(stat.name)}
                  {badgeFor(stat.name, recentChanges)}
                </span>
                <span className="stat-row__value">
                  {current}/{stat.max}
                </span>
              </div>
              <div className="gauge">
                <div
                  className="gauge__fill"
                  style={{
                    width:
                      stat.max === 0
                        ? "0%"
                        : `${Math.max(0, Math.min(100, (current / stat.max) * 100))}%`,
                  }}
                />
              </div>
            </div>
          );
        }
        if (stat.form === "clock") {
          // 세그먼트 원 — 위협 시계용 ThreatClock을 그대로 재사용한다.
          // pulsing은 넘기지 않는다(자원 축은 재촉하는 장치가 아니다).
          return (
            <div className="stat-clock" key={stat.name}>
              <span className="stat-row__name">
                {statLabel(stat.name)}
                {badgeFor(stat.name, recentChanges)}
              </span>
              <ThreatClock segment={stat.current ?? 0} segmentCount={stat.max ?? 0} size={40} />
            </div>
          );
        }
        if (stat.form === "named_slots") {
          return (
            <SlotGrid
              key={stat.name}
              name={stat.name}
              slotValues={stat.slot_values ?? []}
              recentChanges={recentChanges}
            />
          );
        }
        if (stat.form === "tag_list") {
          return (
            <TagList
              key={stat.name}
              name={stat.name}
              tags={stat.tags ?? []}
              recentChanges={recentChanges}
            />
          );
        }
        if (stat.form === "usage_die") {
          return (
            <UsageDie
              key={stat.name}
              name={stat.name}
              current={stat.current ?? 0}
              recentChanges={recentChanges}
            />
          );
        }
        // stat.form === "none": 서버가 이 축을 응답에서 이미 뺐으므로
        // 화면은 이 갈래에 도달하지 않는다(RULE-12 성공 기준 2,
        // routes_characters.py의 _visible_stats). 도달 불가 갈래를
        // 명시적으로 null로 남기고, 「회색으로 보여주기」에 해당하는 어떤
        // 표시도 넣지 않는다.
        return null;
      })}
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
  recentChanges,
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
            <StatRows sheet={sheet} recentChanges={recentChanges} />
          </div>
        ) : sheetError ? (
          <p className="t-label">{COPY.characterSheetError}</p>
        ) : (
          <p className="t-label">{COPY.loading}</p>
        )}
        {/*
         * D-08 — 한 번 잡으면 놓을 수 없다. 「캐릭터 바꾸기」 버튼(눌러도
         * 서버가 거절하는 막다른 길, 12.1이 접어 둔 할 일)은 Phase 12.3
         * D-10이 캐릭터 고르기 화면 자체를 지우면서 함께 닫혔다 —
         * `App.tsx`에 되돌아갈 `choosing` 갈래가 이제 없다. 항상 이
         * 한계 문구만 보여준다.
         */}
        <p className="t-label">{COPY.characterIdentityLimit}</p>
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

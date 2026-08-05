/**
 * 사건 목록을 「턴」 단위로 묶는다.
 *
 * 서버는 사건을 한 줄로 이어서 쌓는다. 두 사람이 동시에 확인 버튼을 누르면
 * 두 서사가 각자 `narration_appended`를 제출하고 액터가 도착 순서대로 쌓으므로,
 * **사건 순서대로 그리면 두 이야기가 문장 단위로 교대로 섞인다**
 * (docs/PIPELINE.md §9-8). 사건마다 `caused_by_seq`가 있으므로 그 사슬을 거슬러
 * 올라가 뿌리(`action_declared`)를 찾으면 어느 턴에 속한 문장인지 알 수 있다.
 *
 * 사슬 모양 (routes_actions.py / actor.py가 만드는 그대로):
 *
 *   action_declared   seq N
 *     ├─ ai_invoked        caused_by N   (분류기)
 *     └─ action_confirmed  seq M, caused_by N
 *          ├─ ai_invoked       caused_by M   (진행자)
 *          └─ check_resolved   seq M+1, caused_by M
 *               ├─ clock_advanced      caused_by M+1
 *               ├─ narration_appended  caused_by M+1  (조각 0,1,2…)
 *               └─ scene_illustrated   caused_by M+1  (그림 기능이 켜졌을 때만)
 */

import type {
  ActionConfirmedEvent,
  ActionDeclaredEvent,
  CheckResolvedEvent,
  ClockAdvancedEvent,
  GameEvent,
  NarrationAppendedEvent,
  SceneIllustratedEvent,
} from "../api/types.ts";

export interface Turn {
  /** 뿌리 `action_declared`의 순번 — 턴의 신원이자 정렬 기준. */
  declareSeq: number;
  playerId: string;
  rawText: string;
  declaredAt: string;
  confirmed: ActionConfirmedEvent | null;
  check: CheckResolvedEvent | null;
  clock: ClockAdvancedEvent | null;
  narration: NarrationAppendedEvent[];
  /**
   * 이 턴의 장면 삽화. 그림 기능이 꺼져 있거나(기본값) 생성이 실패한 턴에는
   * `null`이다 — 서버가 그림 없는 턴에는 사건을 아예 남기지 않는다.
   *
   * **판정·서사보다 늦게 도착한다.** 삽화는 응답을 보낸 뒤 배경에서 만들어져
   * (`routes_actions._illustrate_scene`) 다음 폴링에 실려 오므로, 카드가
   * 그려진 몇 초 뒤에 이 칸이 채워지며 그림이 나타난다.
   */
  illustration: SceneIllustratedEvent | null;
}

/** 이 턴이 중앙 이야기 흐름에 카드로 올라갈 자격이 있는지. */
export function isConfirmedTurn(turn: Turn): boolean {
  return turn.confirmed !== null && turn.confirmed.player_confirmed;
}

/**
 * 사슬을 거슬러 올라가 뿌리 `action_declared`의 순번을 찾는다. 못 찾으면
 * `null` — 뿌리 없는 사건은 조용히 버린다(사슬이 끊긴 옛 기록도 화면을
 * 막지 않아야 한다).
 *
 * `seen`이 순환을 막는다. 서버가 순번을 단조 증가로만 발급하므로 실제로
 * 순환이 생길 수는 없지만, 여기서 무한 루프가 나면 화면 전체가 멈춘다.
 */
function findRootDeclareSeq(
  event: GameEvent,
  bySeq: Map<number, GameEvent>,
  memo: Map<number, number | null>,
): number | null {
  const cached = memo.get(event.seq);
  if (cached !== undefined) {
    return cached;
  }

  const seen = new Set<number>();
  let current: GameEvent | undefined = event;
  while (current !== undefined) {
    if (current.event_type === "action_declared") {
      memo.set(event.seq, current.seq);
      return current.seq;
    }
    if (seen.has(current.seq) || current.caused_by_seq === null) {
      break;
    }
    seen.add(current.seq);
    current = bySeq.get(current.caused_by_seq);
  }

  memo.set(event.seq, null);
  return null;
}

/**
 * 시간순(순번순) 턴 목록. 입력 순서를 신뢰하지 않고 `seq`로 다시 정렬한다.
 */
export function groupTurns(events: GameEvent[]): Turn[] {
  const bySeq = new Map<number, GameEvent>();
  for (const event of events) {
    bySeq.set(event.seq, event);
  }

  const turns = new Map<number, Turn>();
  for (const event of events) {
    if (event.event_type !== "action_declared") {
      continue;
    }
    const declared = event as ActionDeclaredEvent;
    turns.set(declared.seq, {
      declareSeq: declared.seq,
      playerId: declared.player_id,
      rawText: declared.raw_text,
      declaredAt: declared.recorded_at,
      confirmed: null,
      check: null,
      clock: null,
      narration: [],
      illustration: null,
    });
  }

  const memo = new Map<number, number | null>();
  for (const event of events) {
    if (event.event_type === "action_declared" || event.event_type === "ai_invoked") {
      continue;
    }
    const rootSeq = findRootDeclareSeq(event, bySeq, memo);
    if (rootSeq === null) {
      continue;
    }
    const turn = turns.get(rootSeq);
    if (turn === undefined) {
      continue;
    }
    switch (event.event_type) {
      case "action_confirmed":
        turn.confirmed = event;
        break;
      case "check_resolved":
        turn.check = event;
        break;
      case "clock_advanced":
        turn.clock = event;
        break;
      case "narration_appended":
        turn.narration.push(event);
        break;
      case "scene_illustrated":
        // 한 판정에 삽화는 한 장이지만, 마지막 것을 남긴다 — 같은 판정에
        // 두 장이 남는 일이 생기면(재생성 등) 새 그림이 이기는 쪽이 맞다.
        turn.illustration = event;
        break;
    }
  }

  const ordered = [...turns.values()].sort((a, b) => a.declareSeq - b.declareSeq);
  for (const turn of ordered) {
    turn.narration.sort((a, b) => a.seq - b.seq);
  }
  return ordered;
}

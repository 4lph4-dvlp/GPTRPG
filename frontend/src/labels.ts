/**
 * 화면 표시용 한국어 통칭 사전과 고정 문구.
 *
 * **이 파일은 순수 표시 계층이다** — 판정·분류 로직에 관여하지 않는다. 사전에
 * 없는 이름(세 번째 룰북 등)은 원문 그대로 찍는다. 플랫폼이 특정 룰북의
 * 어휘를 안다고 가정하지 않는다.
 */

/** `src/gptrpg/rulebooks/dungeonworld_like.py`의 등급 세 개. */
const GRADE_GLOSS: Record<string, string> = {
  strong_hit: "완전 성공",
  weak_hit: "대가 있는 성공",
  miss: "실패",
};

/** 등급별 시각 톤 — 화면 색을 고르는 데만 쓴다. 모르는 등급은 중립. */
export type GradeTone = "strong" | "weak" | "miss" | "neutral";

const GRADE_TONE: Record<string, GradeTone> = {
  strong_hit: "strong",
  weak_hit: "weak",
  miss: "miss",
  // openquest (rulebooks/openquest.py)
  critical: "strong",
  success: "strong",
  failure: "miss",
  fumble: "miss",
};

export function gradeLabel(grade: string): string {
  return GRADE_GLOSS[grade] ?? grade;
}

export function gradeTone(grade: string | null): GradeTone {
  if (grade === null) {
    return "neutral";
  }
  return GRADE_TONE[grade] ?? "neutral";
}

/**
 * `src/gptrpg/rulebooks/moves.py`의 `display_name`을 옮겨 적은 것 — 그 파일이
 * 권위고 이 사전은 사본이다. 두 룰북 다 담아 두어 세션이 어느 쪽으로 열려도
 * 무브 이름이 한국어로 보인다.
 */
const MOVE_NAME_GLOSS: Record<string, string> = {
  // dungeonworld_like
  hack_and_slash: "근접전으로 부딪히다",
  volley: "원거리로 쏘다",
  defy_danger: "위험을 무릅쓰다",
  discern_realities: "상황을 꿰뚫어 보다",
  parley: "담판을 짓다",
  aid_or_interfere: "돕거나 훼방 놓다",
  defend: "지키다",
  spout_lore: "아는 것을 풀어놓다",
  tracking: "흔적을 쫓다",
  pick_lock_or_trap: "자물쇠나 함정을 다루다",
  // openquest
  close_combat: "백병전",
  evade: "회피",
  stealth: "은신",
  perception: "지각",
  lore_common: "일반 지식",
  persuade: "설득",
  devices: "장치 다루기",
  athletics: "운동",
  willpower: "의지",
  ranged_combat: "원거리전",
};

export function moveLabel(move: string): string {
  return MOVE_NAME_GLOSS[move] ?? move;
}

/** 여러 룰북에 공통되는 서양식 능력치 약칭. 없는 이름은 원문 그대로. */
const STAT_NAME_GLOSS: Record<string, string> = {
  STR: "힘",
  DEX: "민첩",
  CON: "체질",
  INT: "지능",
  WIS: "지혜",
  CHA: "매력",
};

export function statLabel(name: string): string {
  return STAT_NAME_GLOSS[name] ?? name;
}

/**
 * 04-UI-SPEC.md의 Copywriting Contract 문구 — 문구는 그 표가 권위다.
 * 화면을 새로 짜면서 문구까지 바꾸지 않았다.
 */
export const COPY = {
  disconnected: "연결이 끊겼어요. 자동으로 다시 시도하고 있어요 — 새로고침하지 마세요",
  emptyHeading: "아직 아무 일도 일어나지 않았어요",
  emptyBody: "첫 행동을 입력해서 이야기를 시작해 보세요",
  turnFailed: "이번 턴을 처리하지 못했어요. 다시 시도해 주세요",
  serverConfigFailed: "서버 설정 문제로 처리하지 못했어요. 관리자에게 알려 주세요",
  noActionRecognized: "인식된 행동이 없어요. 다른 문장으로 다시 말해 보세요",
  classifying: "AI가 분류하는 중…",
  narrating: "AI가 생각하는 중…",
  confirmSingle: "이 행동으로 진행",
  reject: "다시 쓰기",
  characterListError: "캐릭터 목록을 불러오지 못했어요. 새로고침해 주세요",
  characterSheetError: "캐릭터 시트를 불러오지 못했어요",
  loading: "불러오는 중…",
} as const;

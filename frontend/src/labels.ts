/**
 * 화면 표시용 한국어 통칭 사전과 고정 문구.
 *
 * **이 파일은 순수 표시 계층이다** — 판정·분류 로직에 관여하지 않는다. 사전에
 * 없는 이름(세 번째 룰북 등)은 원문 그대로 찍는다. 플랫폼이 특정 룰북의
 * 어휘를 안다고 가정하지 않는다.
 */

/** `src/gptrpg/rulebooks/dungeonworld_like.py`의 등급 세 개 +
 * `src/gptrpg/rulebooks/openquest.py`의 등급 네 개(IN-01, 12.1-REVIEW.md).
 * OpenQuest는 아직 실제 플레이어 캐릭터를 만드는 경로가 없어 당장
 * 화면에 닿지 않지만(12.1 시점), `GRADE_TONE`에는 이미 이 네 등급이
 * 들어 있었다 — 여기 없으면 실제로 열릴 때 "critical"/"fumble" 같은
 * 영어 원문이 그대로 노출된다(이 파일의 "TRPG 비전문가도 읽을 수 있게
 * 옮긴다"는 방향과 어긋난다). 네 이름의 뜻은 `openquest.py`의
 * `OPENQUEST_GRADE_BANDS` 도크스트링이 근거다 — 크리티컬/성공/실패는
 * 굴림이 기술값 이하/초과로 갈리고, 두 주사위 눈이 같으면서 성공이면
 * 크리티컬, 실패면 펌블(대실패)이다. */
const GRADE_GLOSS: Record<string, string> = {
  strong_hit: "완전 성공",
  weak_hit: "대가 있는 성공",
  miss: "실패",
  // openquest (rulebooks/openquest.py)
  critical: "결정적 성공",
  success: "성공",
  failure: "실패",
  fumble: "대실패",
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
 * 판정 수정치의 출처 문자열(`ModifierView.source`)을 사람 말로 옮긴다(D-04).
 * 능력치 출처(`stat:STR` 형식, `rules_core/resolution.py::build_stat_check_input`)만
 * `statLabel`로 옮기고, 옮길 규칙이 없는 출처(예: `difficulty:hard`)는 조용히
 * 숨기지 않고 원문 그대로 보인다.
 */
const MODIFIER_SOURCE_STAT_PREFIX = "stat:";

export function modifierSourceLabel(source: string): string {
  if (source.startsWith(MODIFIER_SOURCE_STAT_PREFIX)) {
    return statLabel(source.slice(MODIFIER_SOURCE_STAT_PREFIX.length));
  }
  return source;
}

/** `resource_change.py::ResourceOperation`의 여덟 값(RULE-09) — 화면에서
 * 「무엇을 했는지」를 짧게 옮길 때만 쓴다. 새 동작이 추가되면 원문 그대로
 * 보인다(조용히 숨기지 않는다, D-04와 같은 규율). */
const RESOURCE_OPERATION_GLOSS: Record<string, string> = {
  delta: "변화",
  advance: "진행",
  fill: "채움",
  clear: "비움",
  add_tag: "추가",
  remove_tag: "제거",
  step_down: "감소",
  deplete: "소진",
};

export function resourceOperationLabel(operation: string): string {
  return RESOURCE_OPERATION_GLOSS[operation] ?? operation;
}

/**
 * 계산 조각의 역할 이름(`CalculationSegmentView.role`)을 사람 말로 옮긴다
 * (Phase 12.2, D-09). 역할 이름은 자유 문자열이고 닫힌 목록이 아니다
 * (D-10) — 이 표에 없는 이름은 `resourceOperationLabel`과 같은 규율로
 * 조용히 숨기지 않고 원문 그대로 보인다.
 */
const SEGMENT_ROLE_GLOSS: Record<string, string> = {
  die: "눈",
  tens: "십의 자리",
  units: "일의 자리",
  percentile: "백분위",
  flat: "보정치",
};

export function segmentRoleLabel(role: string): string {
  return SEGMENT_ROLE_GLOSS[role] ?? role;
}

/** 판정 방향(`CheckCalculationView.direction`, D-07) — 룰북 선언에서
 * 파생된 해석이라 사건이 아니라 응답으로만 온다. */
const DIRECTION_GLOSS: Record<string, string> = {
  roll_over: "넘어야 성공",
  roll_under: "밑돌아야 성공",
};

export function directionLabel(direction: string | null): string {
  if (direction === null) {
    return "";
  }
  return DIRECTION_GLOSS[direction] ?? direction;
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
  narrationFailed: "이번 턴의 이야기를 쓰지 못했어요. 주사위 결과는 그대로예요",
  serverConfigFailed: "서버 설정 문제로 처리하지 못했어요. 관리자에게 알려 주세요",
  noActionRecognized: "인식된 행동이 없어요. 다른 문장으로 다시 말해 보세요",
  noCheckNeeded: "굴릴 필요 없는 행동이에요",
  proceedWithoutCheck: "이대로 진행",
  classifying: "AI가 분류하는 중…",
  narrating: "AI가 생각하는 중…",
  confirmSingle: "이 행동으로 진행",
  reject: "다시 쓰기",
  characterListError: "캐릭터 목록을 불러오지 못했어요. 새로고침해 주세요",
  characterSheetError: "캐릭터 시트를 불러오지 못했어요",
  /**
   * 캐릭터 **선택**이 실패했을 때만 쓴다 — 목록 조회 실패와는 다른
   * 상태다(결함 B). 서버가 이유를 담아 보내면(409의 `detail`) 그 문장을
   * 그대로 보여주고, 이 문구는 이유가 없을 때의 대체일 뿐이다.
   * 다시 시도하라는 권유를 넣지 않는다 — 그 권유를 따라도 안 풀리는
   * 상태에서 그 안내를 하는 것이 12.1-06이 닫는 결함 B의 해악이었다.
   */
  characterSelectError: "캐릭터를 고르지 못했어요.",
  /** 만들어진 캐릭터가 하나도 없는 세션(빈 배열) — 「목록 조회 실패」가
   * 아니라 정상값이다(CHAR-02, 12.1-05가 정적 넷을 지운 뒤로 실제로
   * 일어나는 상태). */
  characterListEmpty: "아직 만들어진 캐릭터가 없어요. 캐릭터 만들기부터 시작합니다.",
  /**
   * D-08의 알려진 한계 — 감추지 않고 사람이 읽을 자리에 적는다. 캐릭터
   * 선택 화면과 상태 화면(`StatusPane`, 「변경하기」가 사라진 자리) 두
   * 곳에서 쓴다. 「곧 계정이 생깁니다」 같은 약속을 하지 않는다 — 다음
   * 마일스톤이라는 것은 계획의 사실이지 사람에게 하는 약속이 아니다.
   *
   * 「인터넷 사용 기록을 지울 때」를 명시적으로 적는다(12.1-06 사람 확인
   * 피드백) — 표시가 사라지는 실제 경로가 대부분 그것이기 때문이다.
   * 사람이 「표시를 지운다」를 자기가 할 법한 행동으로 옮기지 못하면,
   * 한계를 적어 둔 것이 한계를 알린 것이 되지 않는다.
   */
  characterIdentityLimit:
    "이 캐릭터로 이야기가 끝날 때까지 함께해요. 이 브라우저에 남는 표시로 알아보기 때문에, 다른 기기로 오면 이 캐릭터로 돌아올 수 없어요. 인터넷 사용 기록을 지울 때 그 표시도 같이 지워지니 조심해 주세요.",
  loading: "불러오는 중…",
  noResourceAxes: "이 룰북은 세는 수치를 쓰지 않아요",
  emptySlot: "빈 칸",
  usageDieSpent: "다 씀",
  /** D-04 — 판정 검산 표시(`CheckBreakdown.tsx`). */
  checkTarget: "목표",
  /** D-05 — 합계가 안 남은 판 10 미만 판정(`TurnCard.tsx`·`CheckBreakdown.tsx`). */
  checkTotalMissing: "합계 기록 없음",
  /** D-11/D-12/D-13 — 버려진 눈·다시 굴림 표시(`CheckBreakdown.tsx`·
   * `TurnCard.tsx`·`DiceModal.tsx`). */
  checkRollFirst: "처음 굴림",
  checkRollAgain: "다시 굴림",
  checkDiscarded: "안 골린 눈",
  checkNeverResolved: "판정이 이뤄지지 않았어요",
  diceModalTitle: "주사위 굴림 결과",
  diceModalConfirm: "확인",
  diceModalHintRolling: "클릭하거나 Esc를 누르면 결과를 바로 봅니다",
  diceModalHintDone: "확인을 누르면 닫힙니다 (클릭·Esc도 같습니다)",
  /** RULE-07/D-19, 12-06/12-07 — 자원 변화 확인 카드(`ChatPane.tsx`). */
  resourceChangeHeading: "이 판정으로 자원이 바뀔 예정이에요",
  resourceChangeApply: "그대로 반영",
  resourceChangeDecline: "반영 안 함",
  resourceChangeForbidden: "이 캐릭터를 잡은 사람만 반영할 수 있어요",
  resourceChangeFailed: "자원 변화를 반영하지 못했어요. 다시 시도해 주세요",
  /**
   * 위협 시계가 왜 돌았는지(`ClockAdvancedEvent.trigger`) — 2026-08-18
   * 플레이테스트 회귀. 이 문장이 원래 `StoryPane.tsx`에 실패 문구 하나로만
   * 박혀 있어서, 조건으로 돈 시계에도 「판정 실패가 쌓여」가 나왔다. 완전
   * 성공을 한 플레이어에게 "네가 실패해서 나빠졌다"고 말하는 셈이라
   * 안 보여주는 것보다 나빴다. 뒷단은 처음부터 세 갈래를 다 보내고 있었고
   * (`event_log/schema.py::ClockAdvanced.trigger`) 화면만 안 보고 있었다.
   */
  clockAdvancedByFailCounter: "판정 실패가 쌓여 시스템이 진행시켰어요",
  clockAdvancedByCondition: "이야기가 다음 단계에 닿아 진행됐어요",
  clockAdvancedByAiChoice: "진행자 판단으로 진행됐어요",
} as const;

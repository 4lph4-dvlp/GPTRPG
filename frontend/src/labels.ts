/**
 * 화면 표시용 한국어 통칭 사전과 고정 문구.
 *
 * **이 파일은 순수 표시 계층이다** — 판정·분류 로직에 관여하지 않는다. 사전에
 * 없는 이름(세 번째 룰북 등)은 원문 그대로 찍는다. 플랫폼이 특정 룰북의
 * 어휘를 안다고 가정하지 않는다.
 */

import type { CreationTurn } from "./session/creationView.ts";

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
  /**
   * 앱 최상단 오류 경계(`Notices.tsx`의 `ErrorBoundary`, Phase 12.3-11)
   * 문구 — 마운트·렌더 도중 예외가 나면 빈 화면 대신 이 문구가 남는다.
   * 오류 문장 자체는 여기 안 넣는다 — 실제로 잡힌 예외의 메시지를
   * 그대로 옆에 보인다(D-15 「이유는 한 자리에만」). 6차 검증이 안전한
   * 맥락 전용 API 호출이 이 화면을 빈 채로 끊었던 것을 gap으로 잡았고,
   * 그때 콘솔에도 아무 흔적이 안 남았다 — 이 경계는 화면과 콘솔 둘 다에
   * 흔적을 남긴다.
   */
  appCrashedTitle: "화면을 여는 중에 문제가 생겼어요",
  appCrashed: "이 브라우저에서 화면을 그리지 못했어요. 진행자에게 아래 문장을 그대로 알려 주세요.",
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
  /** 캐릭터 만들기 화면(Phase 12.3, D-10) — 세션 링크를 연 브라우저에
   * 자기 캐릭터가 없으면 이 화면으로 온다(캐릭터 고르기를 거치지
   * 않는다). */
  creationTitle: "캐릭터 만들기",
  /**
   * 인원이 확정되면 화면이 스스로 첫 안내를 부른다(G-12.3-5) — 사람이
   * 단추를 찾아 눌러야 이야기가 시작되는 구조가 「기다려야 하나 눌러야
   * 하나」를 만들었다. 이 문구는 **실제로 요청이 도는 동안에만** 뜬다.
   */
  creationAnnouncing: "진행자가 첫 안내를 준비하고 있어요",
  /**
   * 자동 호출이 실패했을 때만 보이는 재시도 단추(D-13) — 「기다리면 되는
   * 상황」과 「기다려도 안 되는 상황」을 화면이 섞지 않는다. 옛
   * `creationAnnounce`("진행자에게 안내를 부탁하기")는 「이야기를 시작하는
   * 방법」이었지만, 이제 이 단추는 **자동 호출이 실패했을 때의 재시도**로
   * 뜻이 바뀌었다 — 실패 문장 자체는 여기 없고 서버가 보낸 것을 그대로
   * 쓴다(D-15).
   */
  creationAnnounceRetry: "진행자를 다시 불러 보기",
  /** D-13 ② — AI 설정 자체가 없어 503이 났을 때. 기다려도 안 된다. */
  creationGmUnavailable: "진행자를 쓸 수 없는 상태입니다 — 운영자에게 알리세요",
  creationFailed: "만들기 요청을 처리하지 못했어요",
  /** 명단이 이미 잠긴 세션에 이 브라우저의 캐릭터가 없을 때(`Notices.tsx`). */
  creationRosterLocked:
    "이 세션의 파티 명단이 이미 잠겼어요. 이 브라우저로는 들어갈 수 있는 캐릭터가 없어요.",
  /**
   * 만들기 대화판(`CreationPane.tsx`, Phase 12.3-04) 문구. `creationGmSilent`는
   * D-13 ①(AI가 물러나 폴백값으로 200이 온 경우)의 문구다 — `needs_more:
   * false`로 끝난 되묻기는 서버 응답만으로는 진짜 GM 판단과 폴백을 구분할
   * 방법이 없어(둘 다 같은 모양으로 온다), 이 자리에서는 안전한 쪽으로
   * 항상 이 문구를 얹는다(「폴백을 조용히 정상처럼 보여주지 않는다」).
   */
  creationGmSilent: "진행자가 잠시 말을 잃었어요. 그대로 이어가도 괜찮아요.",
  /** GM이 멀쩡히 답했고, 다만 더 물을 것이 없다고 한 경우 — 정상이다.
   * 예전에는 이 경우에도 `creationGmSilent`가 떠서 잘 돌아간 판을
   * 고장난 것처럼 보이게 했다(G-12.3-14). */
  creationGmNothingMore: "진행자가 더 물을 것이 없대요. 이걸로 끝내도 좋아요.",
  /** 되물음을 받았을 때 「어디에 답하는가」를 가리키는 한 줄. 답을 적는
   * 칸은 판 맨 아래에 **항상** 있는데(D-08 「말은 항상 열려 있다」,
   * `InterjectBox`), 되물음 관문만 보고 있으면 그것이 안 보인다 —
   * 예전 「더 말하기」 단추는 상태만 되돌려 아무 일도 안 한 것처럼
   * 보였다(G-12.3-12). */
  creationAnswerBelow: "아래 입력칸에 답을 적을 수 있어요.",
  creationDoneTalking: "이걸로 끝",
  /** 「물어보기」가 아니다 — 사람이 하는 일은 자기 이야기를 진행자에게
   * 내는 것이고, 되물을지는 진행자가 정한다(G-12.3-19). */
  creationAskGm: "진행자에게 제출하기",
  /** 「제출하기」를 누른 뒤 기다리는 동안(G-12.3-9). */
  creationAskGmWaiting: "진행자가 읽고 있어요",
  creationEdit: "고치기",
  creationRoll: "굴리기",
  creationMyTurn: "내 차례예요",
  /**
   * 차례 문구의 공통 꼬리(G-12.3-7, D-06/D-08) — 「순서는 진행자가
   * 정해요」를 넣는 이유: 사장님이 「이 차례의 순서를 모르겠어」라고 적은
   * 것은 순서가 GM의 선택이라는 것을 몰라서다(D-06,
   * `nominate_speaker`). 「자유롭게 끼어들어 말할 수 있어요」는 D-08(남의
   * 차례에도 말은 항상 열려 있다)을 그대로 옮긴 것 — 이 계획은 그
   * 노출 규칙 자체를 바꾸지 않는다(WR-01은 다음 라운드).
   */
  creationTurnSuffix: "차례예요 — 순서는 진행자가 정해요. 자유롭게 끼어들어 말할 수 있어요",
  /**
   * 이름을 모를 때 차례 문구의 주어(G-12.3-7) — 서버가 이름을 주는 것은
   * **완성된** 캐릭터뿐이고, 이름 항목이 마지막인 룰북(예: 던전월드류)에서는
   * 지목받은 사람의 이름이 대개 아직 없다. 이때 식별자(`pc-xxxxxxxx`)를
   * 대신 보이지 않고 이 문구를 쓴다 — 없는 이름을 지어내지 않는다.
   */
  creationUnknownNameSubject: "아직 이름을 안 정한 분",
  creationInterjectPlaceholder: "끼어들어 말하기…",
  /** 자기 차례에는 「끼어드는」 것이 아니라 그냥 말하는 것이다 —
   * 같은 입력칸이지만 상황이 다르다(G-12.3-13). */
  creationSpeakPlaceholder: "말하기…",
  creationDerivedAuto: "자동 계산",
  creationStepKindUnsupported: "이 룰북 항목은 아직 화면에서 채울 수 없어요",
  creationBudgetLeft: "남은 배분",
  /** 만들기 주사위 굴림 모달 제목(Phase 12.3-04 Task 3, D-07) — 판정용
   * `diceModalTitle`("주사위 굴림 결과")을 재사용하지 않는다. 여기서는
   * 성공/실패가 아니라 무엇을 굴렸는지가 중요하다. */
  creationRollTitle: "만들기 굴림 결과",
  /** 인원 확정 관문(Phase 12.3-05 Task 1, D-11) — 방장에게만 보이는
   * 조작의 제목·확정 버튼, 그리고 방장이 아닌 사람에게 보이는 대기 문구.
   * 인원 범위(예: 3~5명) 숫자는 여기 없다 — 판정은 항상 서버가 한다. */
  creationPartySizeTitle: "이번 판 인원을 정해요",
  creationPartySizeConfirm: "인원 확정",
  creationWaitingForHost: "방을 연 사람이 인원을 정하는 중이에요",
  /** 방장이 조용해져 내가 이어받았을 때 조작 위에 붙는 짧은 맥락 —
   * 별도 알림 배너가 아니라 조작 바로 위 한 줄이다(D-11). */
  creationHostTookOver: "방을 연 사람이 자리를 비워 당신이 이어받았어요",
  /** 동의 관문(Phase 12.3-05 Task 2, D-03/D-11) 문구. */
  creationAskWrapUp: "진행자에게 정리를 부탁하기",
  /** 정리를 기다리는 동안 — 전원의 이야기를 한 번에 읽고 한 줄씩 쓰는
   * 일이라 네 호출 중 가장 오래 걸린다(G-12.3-9). */
  creationWrapUpWaiting2: "진행자가 모두의 이야기를 정리하고 있어요",
  /** 방장이 아닌 사람에게 — 단추 대신 이 줄을 본다. 예전에는 모두에게
   * 같은 단추가 떠서 「이걸 다 눌러야 하나」로 헷갈렸다(G-12.3-16). */
  creationWrapUpWaiting: "방을 연 분이 진행자에게 정리를 부탁하면 이어져요.",
  creationConsentTitle: "이대로 시작해도 될까요?",
  creationConsentYes: "이대로 시작",
  creationConsentNo: "고칠 게 있어요",
  creationConsentPending: "아직",
  creationConsentDone: "동의함",
  creationPickStepToReopen: "다시 열 항목을 골라 주세요",
} as const;

/**
 * 「지금 누구 차례인가」를 화면 문구 하나로 조립한다(G-12.3-7) —
 * `gradeLabel`/`statLabel` 계열이 이미 쓰는 관례(사전이 아니라 로직이
 * 필요한 조립은 export 함수로 둔다)를 그대로 따른다.
 *
 * 「아무 차례도 아님」이면 `null`이다 — 화면이 아무 말도 안 한다. 오늘은
 * 지목 전에도 「다른 사람의 차례예요」가 떠서 사람을 기다리게 만들었다
 * (G-12.3-7의 절반).
 */
export function creationTurnLabel(turn: CreationTurn): string | null {
  switch (turn.kind) {
    case "none":
      return null;
    case "me":
      return COPY.creationMyTurn;
    case "other": {
      const subject = turn.name ?? COPY.creationUnknownNameSubject;
      return `${subject} ${COPY.creationTurnSuffix}`;
    }
  }
}

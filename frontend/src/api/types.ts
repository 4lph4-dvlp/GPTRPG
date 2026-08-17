/**
 * 서버 응답 모양 — 파이썬 쪽 pydantic 모델과 칸 이름을 한 글자도 다르게 짓지
 * 않는다. 권위는 다음 세 파일이고 이쪽은 화면 전용 사본이다:
 *
 *   src/gptrpg/event_log/schema.py       사건 6종
 *   src/gptrpg/web/routes_events.py      폴링 응답
 *   src/gptrpg/web/routes_characters.py  캐릭터 목록·시트
 */

export interface EventEnvelope {
  session_id: string;
  seq: number;
  schema_version: number;
  visibility: string;
  caused_by_seq: number | null;
  recorded_at: string;
}

export interface ModifierRecord {
  type: string;
  value: number;
  source: string;
}

export interface ActionDeclaredEvent extends EventEnvelope {
  event_type: "action_declared";
  player_id: string;
  raw_text: string;
  /**
   * 이 선언을 낸 캐릭터(판 5+, D-03/TRUST-03). 판 5 미만 기록에는 이 칸이
   * 없었으므로 `null`이다 — "모른다"이지 "빈 문자열"이 아니다.
   */
  character_id: string | null;
}

export interface ActionConfirmedEvent extends EventEnvelope {
  event_type: "action_confirmed";
  player_id: string;
  move: string;
  stat: string;
  system_suggestion: Record<string, string>;
  player_confirmed: boolean;
  /** 확인하는 캐릭터(판 5+, D-03). `ActionDeclaredEvent.character_id`와 같다. */
  character_id: string | null;
}

export interface CheckResolvedEvent extends EventEnvelope {
  event_type: "check_resolved";
  move: string;
  rolls: number[];
  modifiers: ModifierRecord[];
  target: number;
  grade: string;
  counts_as_failure: boolean;
  /**
   * 「어느 브라우저가 · 어느 캐릭터로」(TRUST-04, D-12). 판 5 이상 기록에서만
   * 필수이고, 판 5 미만 기록은 `null`로 읽힌다.
   */
  person_id: string | null;
  character_id: string | null;
}

export interface NarrationAppendedEvent extends EventEnvelope {
  event_type: "narration_appended";
  text: string;
  chunk_index: number;
}

export interface ClockAdvancedEvent extends EventEnvelope {
  event_type: "clock_advanced";
  clock_id: string;
  segment_index: number;
  trigger: "fail_counter" | "condition" | "ai_choice";
}

/**
 * 자원 변화 사건 안의 항목 하나(판 8, `event_log/schema.py::ResourceChangeRecord`).
 * `before`/`after`는 이 계획 시점에도 항상 `null`이다(12-01 알려진 갭 — 액터가
 * 캐릭터 시작값에 접근하지 못해 계산하지 않는다) — 화면은 이 값이 데이터인
 * 척 렌더하지 않는다. 세기 표시(`changeIntensity`, `ResourceChangeBadge.tsx`)는
 * 이 칸이 아니라 `amount`와 시트에서 다시 읽은 지금 값(`StatEntry`)으로 만든다.
 */
export interface ResourceChangeRecord {
  axis: string;
  operation: string;
  amount: number;
  rolls: number[];
  before: number | null;
  after: number | null;
}

export interface ResourceChangedEvent extends EventEnvelope {
  event_type: "resource_changed";
  character_id: string;
  changes: ResourceChangeRecord[];
  category_id: string | null;
  source: "outcome_list" | "discretionary_ruling" | "retro_declaration";
}

export interface AiInvokedEvent extends EventEnvelope {
  event_type: "ai_invoked";
  agent_role: string;
  model: string;
  provider: string;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number;
  cached_prompt_tokens: number;
}

export interface SceneIllustratedEvent extends EventEnvelope {
  event_type: "scene_illustrated";
  /**
   * 서버가 지은 주소다(`/media/scenes/{session}/{seq}.png` — `web/media.py`).
   * **모델이 만든 글자가 경로에 섞이지 않는다**, 그래서 `<img src>`에 그대로
   * 넣어도 된다. `caused_by_seq`가 이 그림이 딸린 판정 사건을 가리킨다.
   */
  image_path: string;
  prompt: string;
  style: string;
  seed: number;
  steps: number;
  size: number;
  latency_ms: number;
}

export type GameEvent =
  | ActionDeclaredEvent
  | ActionConfirmedEvent
  | CheckResolvedEvent
  | NarrationAppendedEvent
  | ClockAdvancedEvent
  | AiInvokedEvent
  | SceneIllustratedEvent
  | ResourceChangedEvent;

export interface GameStateView {
  session_id: string;
  last_seq: number;
  turn_count: number;
  check_count: number;
  failure_count: number;
  fails_since_clock: number;
  clock_segment: number;
  clock_advances: number;
  narration_count: number;
  ai_calls: number;
  total_tokens: number;
  last_grade: string | null;
  clock_segment_count: number;
  auto_advance_threshold: number;
}

export interface PollResponse {
  events: GameEvent[];
  state: GameStateView;
}

export interface CharacterSummary {
  character_id: string;
  display_name: string;
  archetype: string;
  /**
   * 초상화를 아직 뽑지 않았으면 `null`이다 — 그때는 이름·소개만 그린다.
   * 미리 만드는 명령: `uv run python -m gptrpg.web.portraits`.
   */
  portrait_url: string | null;
}

export interface StatEntry {
  name: string;
  form: "numeric" | "clock" | "named_slots" | "tag_list" | "usage_die" | "none";
  current: number | null;
  max: number | null;
  depleted_effect_ref: string | null;
  slot_values: (string | null)[] | null;
  tags: string[] | null;
  none_kind: "discretionary" | "absent" | null;
}

export interface CharacterSheet {
  entity_id: string;
  display_name: string;
  rulebook_id: string;
  stats: StatEntry[];
}

export interface MyCharacterResponse {
  selected: boolean;
  character_id: string | null;
}

export interface MoveCandidate {
  move: string;
  stat: string;
}

export interface DeclareResponse {
  declare_seq: number;
  // 네 값(D-11, 11-05) — 옛 세 갈래의 마지막 값 하나를 개명해 "no_check"
  // (판정 불필요)와 "unclear"(무슨 말인지 모르겠음) 둘로 갈랐다. 이 계획
  // 시점에서는 두 값 모두 ChatPane.tsx에서 같은 화면(다시 쓰기)으로
  // 간다 — 11-06이 갈래를 쪼갠다.
  tier: "single" | "several" | "no_check" | "unclear";
  candidates: MoveCandidate[];
}

/**
 * 판정에 실제로 실린 수정치 하나(`routes_actions.py::ModifierView`,
 * D-04 검산 근거). `source`는 `stat:STR`/`difficulty:hard` 같은 내부
 * 문자열 그대로 온다 — 화면은 이 값을 그대로 찍지 않고
 * `labels.ts::modifierSourceLabel`을 거친다.
 */
export interface ModifierView {
  type: string;
  value: number;
  source: string;
}

/**
 * `POST .../actions/confirm-resource-change`가 실제로 적용한(또는 멱등
 * 재사용으로 되읽은) 자원 변화 하나(`routes_actions.py::ResourceChangeView`).
 * `before`/`after`는 `ResourceChangeRecord`와 같은 이유로 항상 `null`이다.
 */
export interface ResourceChangeView {
  axis: string;
  operation: string;
  amount: number;
  rolls: number[];
  before: number | null;
  after: number | null;
}

/**
 * 이번 판정으로 「변할 예정」인 자원 변화 하나(12-06, D-09) —
 * `routes_actions.py::PendingResourceChangeView`. `amount_decl`은 룰북 선언
 * 그대로다(정수 또는 주사위식 문자열, 또는 `fill`/`add_tag` 같은 동작의
 * 문자열 값) — 아직 굴리지 않았으므로 실제 적용량이 아니다.
 */
export interface PendingResourceChangeView {
  category_id: string;
  axis: string;
  operation: string;
  amount_decl: number | string;
  source: string;
}

/**
 * 룰북에 결과 목록이 없어도(RULE-13 empty) 재량 판정으로 자원이 변할 수
 * 있다는 신호(RULE-10) — `routes_actions.py::DiscretionaryProposalView`.
 * 이 계획은 실제 재량 제안 UI를 만들지 않는다(Known Stubs 참조) — `available`이
 * 참이어도 화면은 지금 아무것도 안 그린다.
 */
export interface DiscretionaryProposalView {
  available: boolean;
  axes: string[];
}

export interface ConfirmResponse {
  confirmed: boolean;
  confirm_seq: number;
  resolve_seq: number | null;
  rolls: number[] | null;
  grade: string | null;
  target: number | null;
  narration_chunk_count: number;
  /**
   * 서사 생성만 실패했다는 표시다(TRUST-06, D-08) — 이때도 `rolls`/`grade`/
   * `target`은 이미 채워져 있다. 응답 자체는 200이므로 `catch`가 아니라 이
   * 칸을 화면이 직접 읽어야 실패가 조용히 사라지지 않는다.
   */
  narration_failed: boolean;
  /**
   * 이 판정에 실제로 실린 수정치 전부(D-04). 서버가 기본값 `[]`를 갖고
   * 보내므로 선택 칸으로 둔다 — 판정이 없는 응답(`confirmed: false`)에는
   * 안 실린다.
   */
  modifiers?: ModifierView[];
  /**
   * 판정 합계 — `CheckResolved`가 이 값을 저장하지 않아 서버는 항상
   * `null`을 보낸다(12-01 알려진 갭). 화면은 이 칸을 신뢰하지 않고
   * `rolls`/`modifiers`에서 직접 다시 더한다(`CheckBreakdown.tsx`) — 그
   * 계산 자체가 검산 대상이므로 서버 값을 기다리지 않는다.
   */
  total?: number | null;
  /** AI가 고른 결과가 가리키는 자원 변화 — 아직 사건이 안 쌓였다(D-09). */
  pending_resource_changes?: PendingResourceChangeView[];
  discretionary?: DiscretionaryProposalView;
}

export interface ConfirmResourceChangeResponse {
  applied: boolean;
  resource_changes: ResourceChangeView[];
}

export interface ProceedResponse {
  proceeded: boolean;
  narration_chunk_count: number;
  /**
   * 서사 생성만 실패했다는 표시다(TRUST-06, D-08) — `ConfirmResponse.narration_failed`와
   * 같은 뜻·같은 기본값이다. 이 경로는 애초에 판정이 없으므로 `rolls`/`grade`/
   * `target` 칸 자체가 없다.
   */
  narration_failed: boolean;
}

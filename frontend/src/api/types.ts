/**
 * 서버 응답 모양 — 파이썬 쪽 pydantic 모델과 칸 이름을 한 글자도 다르게 짓지
 * 않는다. 권위는 다음 세 파일이고 이쪽은 화면 전용 사본이다:
 *
 *   src/gptrpg/event_log/schema.py             사건 19종
 *   src/gptrpg/web/routes_events.py            폴링 응답
 *   src/gptrpg/web/routes_characters.py        캐릭터 목록·시트
 *   src/gptrpg/rules_core/check_calculation.py 계산 조각 모양의 권위(Phase 12.2)
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
  /**
   * 규칙 코어 `CheckOutcome.total`을 그대로 옮긴 값(Phase 12.2, D-01). 판
   * 10 이상 기록에서만 필수이고, 판 10 미만 기록은 `null`로 읽힌다 —
   * 「합계 기록 없음」(D-05). 0으로 때우지 않는다.
   */
  total: number | null;
  /**
   * 이 판정이 어느 룰북으로 굴렸는지(Phase 12.2, D-03). `total`과 같은
   * 하위 호환 규칙 — 판 10 미만 기록은 `null`이다.
   */
  rulebook_id: string | null;
}

/** 계산 줄 하나를 이루는 조각 — 역할·값·출처·버려짐 여부(D-08/D-09/D-10).
 * `role`은 자유 문자열이다 — 유니온 리터럴 타입을 쓰지 않는다(D-10). */
export interface CalculationSegmentView {
  role: string;
  value: number;
  source: string | null;
  discarded: boolean;
}

/** 조각의 순서 있는 목록 하나. 다시 굴림이 있으면 줄이 여럿이고 합계는
 * 마지막 줄에만 붙는다(D-12) — 이번 계획은 줄이 하나뿐인 보통 판정만 만든다. */
export interface CalculationRowView {
  segments: CalculationSegmentView[];
  total: number | null;
}

/** 계산 줄 전체 — 줄 목록 + 합계 + 목표값 + 방향. `seq`가 이 계산 줄이
 * 딸린 `check_resolved` 사건의 순번이다(폴링 응답의 병렬 목록에서 쓴다). */
export interface CheckCalculationView {
  seq: number;
  rows: CalculationRowView[];
  total: number;
  target: number;
  direction: string;
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

/** 캐릭터를 처음 점유했다 — 먼저 잡은 사람이 임자다(D-05/D-06). 놓기
 * 사건은 없다(D-07) — `schema.py::CharacterOccupied`. */
export interface CharacterOccupiedEvent extends EventEnvelope {
  event_type: "character_occupied";
  character_id: string;
  browser_id: string;
}

/** AI 출력 안전 장치가 걸렀거나 의심스럽다고 표시한 운영자 기록(판 6+,
 * 10-06/10-07) — `schema.py::SafetyFlagged`. 상태를 바꾸지 않는다(`last_seq`만
 * 갱신) — 화면은 이 종류를 몰라도 안전하지만, 유니온에서 빠지면 폴링
 * 응답을 그대로 통과시키는 자리(`PollResponse.events`)에서 이 사건이 하나라도
 * 온 세션의 파싱이 깨진다(WR-02, 12.3-REVIEW.md). */
export interface SafetyFlaggedEvent extends EventEnvelope {
  event_type: "safety_flagged";
  source: "narration" | "classifier";
  reason: "think_block" | "source_overlap" | "character_break" | "unknown_move" | "corrupted_glyph";
  disposition: "blocked" | "flagged";
  matched_len: number;
  subject_len: number;
  chunk_index: number | null;
}

/** 분류기가 이 선언에 판정이 필요한지 최종 결정했다(판 7, 11-06 rework) —
 * `schema.py::ActionClassified`. */
export interface ActionClassifiedEvent extends EventEnvelope {
  event_type: "action_classified";
  no_check: boolean;
}

/** 만들기 항목 하나가 확정한 자원 축 값 하나(판 9) — `schema.py::CreationAxisValueRecord`. */
export interface CreationAxisValueRecord {
  axis_name: string;
  value: number;
}

/** `rules_core.entities.StatEntry`의 여덟 칸을 그대로 옮긴 것(판 9) —
 * `schema.py::CreationStatEntryRecord`. */
export interface CreationStatEntryRecord {
  name: string;
  form: string;
  current: number | null;
  max: number | null;
  depleted_effect_ref: string | null;
  slot_values: (string | null)[] | null;
  tags: string[] | null;
  none_kind: string | null;
}

export interface PartySizeFixedEvent extends EventEnvelope {
  event_type: "party_size_fixed";
  player_character_count: number;
  rulebook_id: string;
  rulebook_min: number;
  rulebook_max: number | null;
}

export interface CreationStepCompletedEvent extends EventEnvelope {
  event_type: "creation_step_completed";
  character_id: string;
  browser_id: string;
  step_id: string;
  kind: string;
  text_value: string | null;
  picked: string[] | null;
  axis_values: CreationAxisValueRecord[] | null;
  rolls: number[] | null;
  superseded_seq: number | null;
}

export interface CreationInterjectionEvent extends EventEnvelope {
  event_type: "creation_interjection";
  speaker_character_id: string;
  browser_id: string;
  during_character_id: string;
  mentioned_character_ids: string[];
  text: string;
}

export interface CharacterCreatedEvent extends EventEnvelope {
  event_type: "character_created";
  character_id: string;
  browser_id: string;
  display_name: string;
  rulebook_id: string;
  one_line_intro: string;
  stats: CreationStatEntryRecord[];
}

export interface PartyRosterLockedEvent extends EventEnvelope {
  event_type: "party_roster_locked";
  character_ids: string[];
  player_character_count: number;
}

/**
 * GM(진행자)이 만들기 중에 한 말 한 줄(D-02, 판 11) — 안내·지목·되묻기·정리
 * 네 갈래를 `kind`로 구분한다(12.3-01 Task 0 `one-event` 결정).
 */
export interface CreationGmSpokeEvent extends EventEnvelope {
  event_type: "creation_gm_spoke";
  kind: "announce" | "nominate" | "follow_up" | "wrap_up";
  say: string;
  target_character_id: string | null;
  dedupe_key: string;
}

/** 캐릭터 하나의 만들기 동의 여부(D-03, 판 11). */
export interface CreationConsentRecordedEvent extends EventEnvelope {
  event_type: "creation_consent_recorded";
  character_id: string;
  browser_id: string;
  agree: boolean;
  reopened_step_id: string | null;
}

/** 이 세션의 방장이 정해졌다(D-11, 판 11). */
export interface CreationHostClaimedEvent extends EventEnvelope {
  event_type: "creation_host_claimed";
  browser_id: string;
  reason: "first" | "succession";
  previous_browser_id: string | null;
}

export type GameEvent =
  | ActionDeclaredEvent
  | ActionConfirmedEvent
  | CheckResolvedEvent
  | NarrationAppendedEvent
  | ClockAdvancedEvent
  | AiInvokedEvent
  | SceneIllustratedEvent
  | CharacterOccupiedEvent
  | SafetyFlaggedEvent
  | ActionClassifiedEvent
  | ResourceChangedEvent
  | PartySizeFixedEvent
  | CreationStepCompletedEvent
  | CreationInterjectionEvent
  | CharacterCreatedEvent
  | PartyRosterLockedEvent
  | CreationGmSpokeEvent
  | CreationConsentRecordedEvent
  | CreationHostClaimedEvent;

/** 완성된 캐릭터 하나(D-04) — `consented`/`required_steps_filled`는
 * 서버가 이미 하는 판단을 그대로 옮긴 것이지 화면이 다시 계산하지 않는다. */
export interface CreationCharacterView {
  character_id: string;
  display_name: string;
  consented: boolean;
  required_steps_filled: boolean;
}

/** 지금 다시 열려 있는 항목 하나(D-11 부분 재진행). */
export interface CreationReopenedStepView {
  character_id: string;
  step_id: string;
}

/** 만들기 항목 하나가 접힌 뒤의 값 — `browser_id`는 싣지 않는다(T-12.3-05). */
export interface CreationStepValueView {
  character_id: string;
  step_id: string;
  kind: string;
  text_value: string | null;
  picked: string[] | null;
  axis_values: [string, number][] | null;
  rolls: number[] | null;
  seq: number;
}

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
  /** 방장이 확정한 이 세션의 인원(D-01) — `null`은 아직 확정 전. */
  party_size_fixed: number | null;
  /** 인원 확정과 함께 정해지는 이 세션의 룰북(D-01). `null`이면 만들기가
   * 아직 시작되지 않은 세션이다. */
  creation_rulebook_id: string | null;
  /** 잠긴 명단(D-08) — `null`과 빈 배열의 뜻이 다르다. `null`은 「아직 안
   * 잠겼다」다. */
  party_roster: string[] | null;
  /** 항목을 하나라도 냈지만 아직 완성되지 않은 사람의 닫힌 목록. */
  creation_unfinished_character_ids: string[];
  /** GM이 가장 최근에 지목한 사람 — 그 사람이 이미 완성됐으면 차례가
   * 끝난 것이므로 `null`이다. */
  creation_current_speaker_id: string | null;
  /** 완성된 캐릭터 목록. */
  creation_characters: CreationCharacterView[];
  /** 지금 다시 열려 있는 항목들(D-11). */
  creation_reopened_step_ids: CreationReopenedStepView[];
  /** 접힌 뒤의 항목 값 전부(D-09) — 확정한 항목이 목록으로 보이고 각
   * 항목 옆에 고치기가 있으려면 화면이 이 목록을 읽어야 한다. 접는 일은
   * 서버만 한다. */
  creation_step_values: CreationStepValueView[];
  /** 이 세션의 방장이 잡혔는지 여부만(D-11) — `creation_host_browser_id`
   * 값 자체는 절대 싣지 않는다(T-12.3-05). */
  creation_host_claimed: boolean;
}

export interface PollResponse {
  events: GameEvent[];
  state: GameStateView;
  /**
   * `events`와 나란한 파생값 목록(Phase 12.2) — 사건 객체 자체는 안
   * 바뀐다. 각 항목의 `seq`가 그 순번의 `check_resolved` 사건을 가리킨다.
   */
  check_calculations: CheckCalculationView[];
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
   * 판정 합계 — 판 10 이상 판정에서는 서버가 저장된 합계를 그대로
   * 보내고 화면은 그것을 그대로 쓴다(Phase 12.2). 판 10 미만 판정에서는
   * `null`이고, 그때 `CheckBreakdown`은 `COPY.checkTotalMissing`을
   * 보인다(D-05).
   */
  total?: number | null;
  /** 이 판정을 굴린 룰북 식별자(Phase 12.2, D-03) — `total`과 같은
   * 하위 호환 규칙. 판정이 없는 응답(`confirmed: false`)이나 판 10 미만
   * 판정에서는 `null`이다. */
  rulebook_id?: string | null;
  /** 눈이 어떻게 합계가 되는지의 조각 목록(D-08/D-09) — `total`과 같은
   * `null` 규칙을 따른다. `checkSummary.ts::buildCheckSummary`가 이 값을
   * 읽는 유일한 곳이다(D-14). */
  calculation?: CheckCalculationView | null;
  /** AI가 고른 결과가 가리키는 자원 변화 — 아직 사건이 안 쌓였다(D-09). */
  pending_resource_changes?: PendingResourceChangeView[];
  discretionary?: DiscretionaryProposalView;
}

export interface ConfirmResourceChangeResponse {
  applied: boolean;
  resource_changes: ResourceChangeView[];
}

/** `POST .../creation/announce`의 응답(Phase 12.3, D-02/D-12) —
 * `routes_creation.py::AnnounceCreationResponse`. `seq`는 이 안내가
 * 기록된(또는 이미 기록되어 있던) `creation_gm_spoke` 사건의 순번이다 —
 * 화면이 폴링이 그 사건을 실어 오기 전에도 조용히 기다릴 수 있다. */
export interface AnnounceCreationResponse {
  message: string;
  seq: number;
}

/** 만들기 항목 하나가 값을 채우는 방식(D-01, D-03/D-04) —
 * `rules_core/rulebook.py::CreationStepKind`와 같은 일곱 값. `kind`로
 * 분기할 때 tsc가 빠진 갈래를 잡도록 유니온 리터럴로 적는다. */
export type CreationStepKind =
  | "pick_one"
  | "pick_many"
  | "allocate_points"
  | "place_fixed_values"
  | "roll_to_fill"
  | "free_text"
  | "derive";

/** `GET .../creation/steps`가 내려주는 항목 선언 하나(D-05) —
 * `routes_creation.py::CreationStepView`. 룰북 **선언**만 담는다 — 진행
 * 상태(누가 무엇을 채웠는지)는 이 타입에 없다(그 값은 `GameStateView.
 * creation_step_values`, D-04). */
export interface CreationStepView {
  step_id: string;
  kind: CreationStepKind;
  label: string;
  required: boolean;
  provides_display_name: boolean;
  axis_names: string[];
  options: string[] | null;
  pick_count: number | null;
  fixed_values: number[] | null;
  point_budget: number | null;
  per_target_max: number | null;
  dice_expr: string | null;
  derive_base_axis: string | null;
  derive_multiplier: number | null;
  derive_offset: number | null;
  depends_on: string[];
  default_from: string | null;
}

/** `routes_creation.py::SeqResponse` — 사건 하나를 기록한 만들기 경로가
 * 공통으로 돌려주는 순번 하나. */
export interface SeqResponse {
  seq: number;
}

/** `POST .../creation/complete`의 응답 — `routes_creation.py::CreationCompleteResponse`. */
export interface CreationCompleteResponse {
  character_id: string;
  character_seq: number;
  occupy_seq: number;
}

/** `POST .../creation/nominate`의 응답(D-02/D-12) —
 * `routes_creation.py::NominateSpeakerResponse`. */
export interface NominateSpeakerResponse {
  character_id: string;
  say: string;
  seq: number;
}

/** `POST .../creation/follow-up`의 응답(D-02 ④) —
 * `routes_creation.py::CreationFollowUpResponse`. `seq`는 되물을 것이
 * 있을 때만(`needs_more === true`) 채워진다 — GM이 아무 말도 안 했으면
 * 사건이 없으므로 짝지어질 순번도 없다. */
export interface CreationFollowUpResponse {
  needs_more: boolean;
  question: string | null;
  required_steps_filled: boolean;
  seq: number | null;
}

/** 캐릭터 하나에 대한 GM의 한 줄 소개(CHAR-03/D-10) —
 * `routes_creation.py::CharacterIntroBody`. */
export interface CharacterIntroBody {
  character_id: string;
  intro: string;
}

/** `POST .../creation/wrap-up`의 응답(D-02/D-12) —
 * `routes_creation.py::WrapUpCreationResponse`. */
export interface WrapUpCreationResponse {
  say: string;
  intros: CharacterIntroBody[];
  seq: number;
}

/** `POST .../creation/consent`의 응답(D-03/D-11) —
 * `routes_creation.py::ConsentResponse`. `agree=false`일 때만
 * `reopened_step_id`가 채워진다. */
export interface ConsentResponse {
  locked: boolean;
  party_roster: string[] | null;
  reopened_step_id: string | null;
  message: string | null;
}

/** `POST .../creation/host`의 응답(D-11) —
 * `routes_creation.py::CreationHostResponse`. **`creation_host_browser_id`
 * 값 자체는 절대 담기지 않는다**(T-12.3-05) — 부른 사람에게 「너인가
 * 아닌가」만 답한다. */
export interface CreationHostResponse {
  you_are_host: boolean;
  host_claimed: boolean;
  changed: boolean;
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

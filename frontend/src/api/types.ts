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
}

export interface ActionConfirmedEvent extends EventEnvelope {
  event_type: "action_confirmed";
  player_id: string;
  move: string;
  stat: string;
  system_suggestion: Record<string, string>;
  player_confirmed: boolean;
}

export interface CheckResolvedEvent extends EventEnvelope {
  event_type: "check_resolved";
  move: string;
  rolls: number[];
  modifiers: ModifierRecord[];
  target: number;
  grade: string;
  counts_as_failure: boolean;
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
  | SceneIllustratedEvent;

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
  current: number;
  max: number | null;
  depleted_effect_ref: string | null;
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
  tier: "none" | "single" | "several";
  candidates: MoveCandidate[];
}

export interface ConfirmResponse {
  confirmed: boolean;
  confirm_seq: number;
  resolve_seq: number | null;
  rolls: number[] | null;
  grade: string | null;
  target: number | null;
  narration_chunk_count: number;
}

"""명령 큐 + 단일 소비자. 세션당 쓰기 주체 하나 (D-05, D-09①).

여섯 종류 명령(DeclareAction / ConfirmAction / ResolveCheck / AppendNarration /
AdvanceClock / RecordAiCall)을 전부 여기서만 처리한다. 절차는 늘 같은 네 단계다 —
① 명령 값을 검증한다 ② 필요하면 규칙 코어를 부른다(판정 명령만) ③ 순번을 얻고
시각을 찍어 사건 객체를 만든다 ④ 저장소에 append한다. ①·②가 ③보다 먼저 끝나므로,
거부되는 명령은 순번을 소모하지도 기록을 남기지도 않는다 — 반쪽 상태가 생기지
않는다.
"""

import asyncio
import sys
from collections.abc import Callable
from dataclasses import dataclass, replace as dataclass_replace
from pathlib import Path

from gptrpg.event_log.schema import (
    EVENT_SCHEMA_VERSION,
    ActionClassified,
    ActionConfirmed,
    ActionDeclared,
    AiInvoked,
    CharacterCreated,
    CharacterOccupied,
    CheckResolved,
    ClockAdvanced,
    CreationConsentRecorded,
    CreationGmSpoke,
    CreationHostClaimed,
    CreationInterjection,
    CreationStepCompleted,
    ModifierRecord,
    NarrationAppended,
    PartyRosterLocked,
    PartySizeFixed,
    ResourceChanged,
    SafetyFlagged,
    SceneIllustrated,
    SceneOpened,
    utc_now_iso,
)
from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.dice import Roller
from gptrpg.rules_core.entities import Entity, StatEntry
from gptrpg.rules_core.grading import DEFAULT_TARGET
from gptrpg.rules_core.reducer import (
    ConfirmedDeclareRecord,
    CreationGmLineFold,
    GameState,
    apply_event,
)
from gptrpg.rules_core.resolution import (
    Modifier,
    StatNotUsableInChecks,
    UnknownStatForCheck,
    UnsupportedModifier,
    build_stat_check_input,
    resolve_2d6,
)
from gptrpg.rules_core.resolution_d100 import resolve_d100
from gptrpg.rules_core.resource_change import ResourceOp, roll_amount
from gptrpg.rules_core.rulebook import (
    D100_ROLL_UNDER,
    TWO_D6,
    NoMatchingGradeBand,
    PartySizeOutOfRange,
    Rulebook,
    UnknownDifficultyLevel,
    UnknownGradeName,
    build_creation_stats,
    require_band,
    require_difficulty,
    validate_entity_axes,
    validate_party_size,
)
from gptrpg.rulebooks import UnknownRulebook, get_rulebook
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rulebooks.threat_clocks import THREAT_CLOCK_SEGMENT_COUNT
from gptrpg.session_actor.live_roller import LiveRoller
from gptrpg.session_actor.projection import rebuild_state
from gptrpg.session_actor.report import DEFAULT_REPORTS_DIR, UnsafeSessionId, write_report

AUTO_ADVANCE_FAILURE_THRESHOLD = 3
"""D-21이 적은 진행 규칙 기본값("N회 기본 3, 시계별 조절") — 시계별로
문턱값을 다르게 주는 것은 이 마일스톤 범위 밖이다(룰북 데이터의 칸 단위
구체 규격은 전부 M1, `.planning/PROJECT.md`의 M0 범위선).

**D-21의 진행 규칙 세 가지 중 ①(실패 누적)만 이 액터가 만든다.**
②조건 트리거와 ③AI 선택은 M0에 없다 — ③은 `prompt_assembly.build_gm_prompt`가
AI에게 명시적으로 금지하고, ②는 명령줄 `gptrpg submit clock --trigger condition`
으로만 닿는다. 그 결과 `failure_to_clock_ratio`는 이 문턱값에 고정되며
(실패 3회당 정확히 1칸) MEAS-03의 비율 자체로는 봐주기를 판별할 수 없다 —
Phase 6이 H2를 어떻게 읽어야 하는지는
`docs/experiment/hypothesis-scoring-rules.md`가 정한다."""


@dataclass(frozen=True)
class DeclareAction:
    """플레이어가 자유 문장으로 행동을 선언하는 명령."""

    player_id: str
    raw_text: str
    character_id: str | None = None
    """이 선언을 낸 캐릭터(D-03/TRUST-03). `None`이면 사건에도 `None`으로
    남는다(판 5 미만 호출부와의 하위 호환 — CLI처럼 캐릭터 개념이 없는
    호출부도 여전히 선언을 낼 수 있어야 한다)."""


@dataclass(frozen=True)
class ConfirmAction:
    """시스템이 제안한 무브·능력치를 플레이어가 확인(또는 거부)하는 명령."""

    player_id: str
    move: str
    stat: str
    system_suggestion: dict[str, str]
    player_confirmed: bool
    caused_by_seq: int | None = None
    character_id: str | None = None
    """확인하는 캐릭터(D-03). `ActionDeclared.character_id`와 같은 이유·같은
    선택 칸 형식이다."""


@dataclass(frozen=True)
class OccupyCharacter:
    """캐릭터 점유를 요청하는 명령 — 먼저 잡은 사람이 임자다(D-05), 놓기는 없다(D-07)."""

    character_id: str
    browser_id: str


@dataclass(frozen=True)
class FixPartySize:
    """방을 여는 사람이 이 세션의 인원을 확정하는 명령(D-01, Phase 12.1).

    재확정은 없다 — 이미 확정된 세션에서 다시 부르면 `CommandRejected`다.
    룰북 범위 대조(시나리오 범위 밖 거절, D-02)는 12.1-02가 붙인다."""

    player_character_count: int
    rulebook_id: str


@dataclass(frozen=True)
class CompleteCreationStep:
    """만들기 항목 하나의 값을 확정하는 명령(D-03, Phase 12.1).

    `axis_values`는 `place_fixed_values` 류가 쓰는 (축 이름, 값) 짝의
    튜플이다. 같은 `(character_id, step_id)`로 다시 제출하면 이전 값이
    `superseded_seq`로 남고 나중 값이 이긴다(D-07)."""

    character_id: str
    browser_id: str
    step_id: str
    rulebook_id: str
    text_value: str | None = None
    picked: tuple[str, ...] | None = None
    axis_values: tuple[tuple[str, int], ...] | None = None


@dataclass(frozen=True)
class CreateCharacter:
    """확정된 만들기 항목 값들을 `Entity`/`StatEntry`로 조립해 캐릭터
    하나를 완성하는 명령(D-03/CHAR-04, Phase 12.1). `one_line_intro`는
    GM이 쓴 산문이고 숫자에 관여하지 않는다(CHAR-03)."""

    character_id: str
    browser_id: str
    rulebook_id: str
    one_line_intro: str


@dataclass(frozen=True)
class LockPartyRoster:
    """파티 명단을 잠그는 명령(D-08, Phase 12.1) — 잠근 뒤에는 되돌릴 수
    없다(푸는 명령이 없다). **명단에서 사람을 빼는 명령은 없다** — 반대한
    사람을 빼고 시작하는 경로는 없다(D-11 경계, D-08, Phase 12.1-04)."""

    character_ids: tuple[str, ...]


@dataclass(frozen=True)
class RecordInterjection:
    """남의 차례에 자유롭게 끼어드는 말 하나(D-09, Phase 12.1-04).

    **이 명령은 어떤 캐릭터의 값도 바꾸지 않는다.** CHAR-04가 관계를
    담을 칸을 `Entity`/`StatEntry`에 두는 것을 금지하고, D-07이 지난
    차례를 잠그므로(끼어드는 사람의 차례는 지났거나 아직 오지 않았다),
    끼어든 말이 손댈 수 있는 「지금 고칠 수 있는 값」이 애초에 없다
    (D-09 결정, 12.1-04-PLAN.md § 조사가 확정한 것). 화자
    (`speaker_character_id`)와 언급 대상(`mentioned_character_ids`)을
    사건에 같이 남기는 것은 Phase 14(관계 장부)가 사건 스키마를 다시
    손대지 않고 이 사건들을 색인할 수 있게 하기 위해서다."""

    speaker_character_id: str
    browser_id: str
    during_character_id: str
    mentioned_character_ids: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class RecordGmSpoke:
    """GM이 만들기 중에 한 말 한 줄을 사건으로 남기는 명령(D-02/D-12,
    Phase 12.3). 사건 `creation_gm_spoke`에 그대로 옮겨진다 — `RecordInterjection`
    이 `CreationInterjection`에 대응하는 것과 같은 자리다.

    `dedupe_key`로 이미 말한 적이 있는지는 호출부(`routes_creation.py`의
    `_gm_dedupe_key` 조회)가 AI를 부르기 **전에** 먼저 본다(D-12) — 그
    조회가 겹친 요청 둘 다를 통과시킬 수 있으므로(단일 소비자 큐 밖의
    읽기라서, 12.3-REVIEW.md CR-04), `_prepare_gm_spoke`가 큐 **안에서**
    같은 검사를 다시 해 두 번째를 `AlreadyGmSpoken`으로 막는다."""

    kind: str
    say: str
    target_character_id: str | None
    dedupe_key: str


@dataclass(frozen=True)
class ClaimGmSlot:
    """AI를 부르기 전에 이 세션 안에서 슬롯 하나를 먼저 잡는 명령(D-02/D-03,
    Phase 13). 큐 **안**에서 슬롯을 먼저 잡고 그 뒤에야 무거운 일(AI 호출)을
    하라는 것이 D-03의 요구다 — `web/routes_creation.py`의 기존 GM 호출
    네 곳은 지금 「큐 밖 사전 검사 → AI 호출 → 큐 안 재검사」 순서라 겹친
    두 요청이 둘 다 AI를 부른다(13-RESEARCH.md Pitfall 1). 오프닝은 정확히
    같은 모양의 다섯 번째 자동 발동 호출이고, 이 명령이 그 순서를
    뒤집는다 — 슬롯을 못 딴 쪽은 AI를 아예 안 부른다.

    **사건을 남기지 않는다** — `SessionActor._gm_slots_in_flight`는 액터
    메모리(집합)일 뿐이다. 「지금 이 순간 누가 AI를 부르는 중인가」는 서버
    재시작을 넘겨 살아남을 필요가 없는 값이고, 오히려 살아남으면 재시작
    뒤 슬롯이 영구히 잠긴다.
    """

    slot_key: str


@dataclass(frozen=True)
class ReleaseGmSlot:
    """`ClaimGmSlot`으로 잡은 슬롯을 돌려주는 명령(D-03, Phase 13).

    호출부가 `try/finally`의 `finally`에서 무조건 부른다 — AI 호출이
    실패해도 슬롯이 영구히 잠기지 않는다(T-13-03). 없던 키를 지워도
    조용히 성공한다 — `finally`가 두 번 불릴 수 있다."""

    slot_key: str


@dataclass(frozen=True)
class OpenScene:
    """판정 없이 장면을 여는 명령(D-01/D-06, SCENE-01, Phase 13) —
    `declare_seq` 없이 기록되는 세 번째 진입점(`proceed()`가 이미 연 두
    번째 진입점은 여전히 `declare_seq`를 필수로 받는다).

    `text`는 호출부가 이미 완성한 오프닝 문단이다(낭독문형이면 저자의
    다섯 칸을 그대로 이은 것, 메모형이면 AI가 좁혀 쓴 것 또는 폴백) — 이
    명령 자신은 그 문단이 어떻게 만들어졌는지 모른다. `source`가 출처만
    사건에 남긴다."""

    scenario_id: str
    text: str
    source: str


@dataclass(frozen=True)
class RecordConsent:
    """동의 표시 하나(D-10, Phase 12.1-04) — **판 11부터(Phase 12.3)
    사건 `creation_consent_recorded`로 남는다.**

    12.1-04 시점에는 이 명령이 액터 메모리에만 담기고 사건을 안
    만들었다 — 개별 동의를 잠금 직전 몇 초의 상태로 보고, 판을 한 번
    더 올리는 비용이 그 몇 초를 지키는 이득보다 크다고 판단했기
    때문이다. 그런데 그 판단은 서버 재시작에 모인 동의가 통째로
    사라지는 대가를 치렀고, 화면도 「누가 아직 안 눌렀나」를 알 방법이
    없었다(12.3-CONTEXT.md D-03). 12.3-03이 그 판단을 뒤집어 사건으로
    옮겼다 — 잃는 것(판을 한 번 더 지나는 비용)보다 재시작 내구성과
    화면 가시성이 더 크다고 다시 판단한 것이다. 같은 `character_id`가
    두 번 동의해도(리듀서가 `character_id` 키로 덮어쓰므로) 두 번
    세어지지 않는다(멱등)."""

    character_id: str
    browser_id: str
    agree: bool


@dataclass(frozen=True)
class ReopenCreationStep:
    """만들기 항목 하나를 다시 여는 명령(D-11, Phase 12.1-04) — **판
    11부터(Phase 12.3) `RecordConsent`와 같은 사건
    (`creation_consent_recorded`, `agree=False`)으로 남는다** —
    `RecordConsent` 도크스트링이 그 판단이 왜 바뀌었는지 적는다.

    그 사람의 그 항목 하나만 다시 열린다 — `character_created`가
    무효가 되는 것이 아니라, 그 항목에 대한 `CompleteCreationStep`이
    다시 허용되고(재확정 뒤 `CreateCharacter`를 다시 제출해
    `character_created`를 갱신한다). **다시 열리면 앞서 받은 동의는
    전부 무효가 된다** — 바뀐 내용에 대한 동의를 다시 받아야 한다."""

    character_id: str
    browser_id: str
    step_id: str


@dataclass(frozen=True)
class ClaimCreationHost:
    """방장을 잡거나 승계하는 명령(D-11, 판 11, Phase 12.3).

    **캐릭터 점유 판정과 다른 규칙이다** — 점유는 한 번 잡으면 놓을 수
    없고(08 D-07) 방장은 조용해지면 넘어간다. 그래서 점유가 쓰는 검증
    메서드를 부르지도, 흉내 낸 헬퍼를 공유하지도 않는다(D-11 명시 —
    점유 코드를 방장에 재사용하지 않는다).

    `previous_browser_id`가 `None`이면 첫 선점 시도, 있으면 승계 시도다.
    액터는 이 값을 지금 상태의 `creation_host_browser_id`와 **비교한
    뒤에만 교체한다**(비교 후 교체, T-12.3-03) — 브라우저는 자기
    `browser_id` 하나만 정할 수 있고, 「누구를 이어받는지」는 호출부
    (`routes_creation.py`)가 지금 상태에서 읽어 이 명령에 실어 보낸다.
    브라우저가 스스로 「내가 방장이다」를 선언할 수 있는 경로가 없다."""

    browser_id: str
    previous_browser_id: str | None


@dataclass(frozen=True)
class ResolveCheck:
    """판정 하나를 요청하는 명령.

    **판정 방식은 이 명령에 넣지 않는다** — 방식은 룰북 선언(`Rulebook.
    resolution_method`)이 갖고 있고, 이 명령은 어느 룰북인지(`rulebook_id`)만
    말한다.
    """

    move: str
    modifiers: tuple[Modifier, ...]
    target: int = DEFAULT_TARGET
    rulebook_id: str = DUNGEONWORLD_LIKE_ID
    caused_by_seq: int | None = None
    person_id: str = ""
    character_id: str = ""
    """「어느 브라우저가 · 어느 캐릭터로」(TRUST-04, D-12). dataclass의
    기본값 순서 제약 때문에 빈 문자열을 기본값으로 두고, 빈 값 거부는
    `_prepare_resolve_check`가 한다(`_prepare_declare`의
    `if not command.player_id.strip():` 관례와 같은 형식) — 이 두 칸은
    `CheckResolved`에서 필수이므로(판 5+, D-12) 빈 채로 통과시키지 않는다."""
    stat: str = ""
    """이 판정에 싣는 능력치 이름(RULE-02/03, D-01). 빈 문자열이면 능력치
    보정치 조립을 건너뛴다 — `submit roll` 같은 저수준 디버그 통로나 옛
    호출부가 이 칸 없이도 계속 동작해야 하기 때문이다(person_id/character_id와
    달리 이 칸은 "비면 거부"가 아니라 "비면 건너뛴다"). 채워지면
    `build_stat_check_input`이 캐릭터가 그 이름의 능력치를 실제로 갖고
    있는지, 그 축이 판정에 쓰이도록 선언됐는지를 검증한다 — 조용히 0으로
    넘어가지 않는다(RULE-02 empty)."""
    character_stats: tuple[StatEntry, ...] = ()
    """`stat`이 가리키는 능력치 값을 찾을 캐릭터 상태값(D-01). 액터는
    `web` 계층의 캐릭터 데이터를 알 수 없으므로(층 계약) 호출부가 값으로
    넘긴다."""
    difficulty: str | None = None
    """룰북이 선언한 닫힌 이름 목록에서 고른 난이도(D-02). `None`이면
    난이도 수정치를 싣지 않는다. 값이 있으면 `require_difficulty`로
    찾아 그 선언의 수정치를 함께 싣는다 — 룰북 선언에 없는 이름은
    `UnknownDifficultyLevel`로 거절되어 `CommandRejected`가 된다."""


@dataclass(frozen=True)
class AppendNarration:
    """서사 문장 조각 하나를 덧붙이는 명령."""

    text: str
    chunk_index: int
    caused_by_seq: int | None = None


@dataclass(frozen=True)
class AdvanceClock:
    """위협 시계를 한 칸 돌리는 명령."""

    clock_id: str
    segment_index: int
    trigger: str
    caused_by_seq: int | None = None


@dataclass(frozen=True)
class RecordAiCall:
    """AI를 한 번 불렀다는 사실을 기록하는 명령.

    `cached_prompt_tokens`는 `prompt_tokens`의 부분집합이며 기본값이 0이다 —
    캐시 정보를 주지 않는 제공자와, 이 칸이 생기기 전에 쓰인 호출부를 위한
    기본값이다(`AgentResult`·`AiInvoked`의 같은 이름 칸과 같은 뜻).
    """

    agent_role: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    caused_by_seq: int | None = None
    cached_prompt_tokens: int = 0


@dataclass(frozen=True)
class RecordSceneIllustration:
    """장면 삽화 한 장이 만들어졌다는 사실을 기록하는 명령.

    **그림을 만드는 코드가 이 명령을 만들지 않는다.** `gptrpg.imagery`는
    `session_actor`를 import할 수 없으므로(contract:4) 그림 층에는 사건을 쓸
    수단이 없다. 그림 바이트를 받아 이 명령으로 옮기는 것은 `web`의 일이고,
    그 통로가 유일하다 — `agents`가 서사를 사건으로 바꾸는 방식과 같다.
    """

    image_path: str
    prompt: str
    style: str
    seed: int
    steps: int
    size: int
    latency_ms: int
    caused_by_seq: int | None = None


@dataclass(frozen=True)
class RecordSafetyFlag:
    """AI 출력 안전 장치가 걸렀거나 의심스럽다고 표시했다는 사실을 기록하는 명령(판 6).

    `AppendNarration`과 같은 모양이다 — 칸은 `SafetyFlagged` 사건의 칸과 짝이
    맞는다. `source`가 서사 검사(`"narration"`)인지 분류기 계약 위반
    (`"classifier"`)인지를 가른다(Task 1 checkpoint option-a).
    """

    source: str
    reason: str
    disposition: str
    matched_len: int = 0
    subject_len: int = 0
    chunk_index: int | None = None
    caused_by_seq: int | None = None


@dataclass(frozen=True)
class RecordActionClassification:
    """분류기가 이 선언에 대해 판정이 필요한지(`no_check`) 최종 결정했다는
    사실을 기록하는 명령(판 7, 11-06 rework, T-11-29 — CR 차단 결함 수정).

    `RecordAiCall`·`RecordSafetyFlag`와 같은 모양이다 — 운영 사실 하나를
    사건으로 남긴다. `no_check` 하나만 남기는 이유는
    `_prepare_verify_proceed_eligibility`가 서버 재시작 뒤에도 필요로 하는
    것이 그 값 하나뿐이기 때문이다(`single`/`several`/`unclear` 구분은
    웹 응답의 `tier` 칸이 이미 담당하고, 서버 상태에 중복해서 담지 않는다).
    """

    no_check: bool
    caused_by_seq: int | None = None


@dataclass(frozen=True)
class VerifyProceedEligibility:
    """`proceed()`(웹)·CLI `no_check` 갈래가 실제로 그 자격이 있는지 사건에서
    접은 상태로 확인만 하는 명령(11-06 rework, T-11-29 — CR 차단 결함 수정).

    성공해도 사건을 남기지 않는다 — 결과는 `ProceedEligible` 예외로
    돌아온다(`AlreadyOccupied`/`AlreadyConfirmed`와 같은 이유: `_prepare`가
    `(event_type, ...)` 튜플이 아니라 예외를 던지면 `_process`가 append
    이전에 멈춘다).
    """

    declare_seq: int
    character_id: str


@dataclass(frozen=True)
class RecordResourceChange:
    """판정(또는 재량 판정)에 딸린 자원 변화를 사건으로 남기는 명령(판 8,
    D-05/D-65/RULE-09).

    `changes`가 빈 튜플이면 `CommandRejected`다 — 변화 없음은 사건을 아예
    안 쓰는 것으로 표현한다(RULE-04/05/09 empty). 멱등성은 Phase 8
    멱등성 창 위에 올린다 — 같은 `caused_by_seq`로 두 번 제출하면
    `AlreadyChanged`가 두 번째를 단락시킨다(재시도가 자원을 두 번 깎지
    않는다).
    """

    character_id: str
    changes: tuple[ResourceOp, ...]
    source: str
    caused_by_seq: int | None = None
    category_id: str | None = None


Command = (
    DeclareAction
    | ConfirmAction
    | OccupyCharacter
    | ResolveCheck
    | AppendNarration
    | AdvanceClock
    | RecordAiCall
    | RecordSceneIllustration
    | RecordSafetyFlag
    | RecordActionClassification
    | VerifyProceedEligibility
    | RecordResourceChange
    | FixPartySize
    | CompleteCreationStep
    | CreateCharacter
    | LockPartyRoster
    | RecordInterjection
    | RecordGmSpoke
    | RecordConsent
    | ReopenCreationStep
    | ClaimCreationHost
    | ClaimGmSlot
    | ReleaseGmSlot
    | OpenScene
)

_VALID_CLOCK_TRIGGERS = frozenset({"fail_counter", "condition", "ai_choice"})
_VALID_SAFETY_FLAG_SOURCES = frozenset({"narration", "classifier"})
_VALID_SAFETY_FLAG_REASONS = frozenset(
    {"think_block", "source_overlap", "character_break", "unknown_move", "corrupted_glyph"}
)
_VALID_SAFETY_FLAG_DISPOSITIONS = frozenset({"blocked", "flagged"})
_VALID_RESOURCE_CHANGE_SOURCES = frozenset(
    {"outcome_list", "discretionary_ruling", "retro_declaration"}
)

_EVENT_CLASSES: dict[str, type] = {
    "action_declared": ActionDeclared,
    "action_confirmed": ActionConfirmed,
    "check_resolved": CheckResolved,
    "narration_appended": NarrationAppended,
    "clock_advanced": ClockAdvanced,
    "ai_invoked": AiInvoked,
    "scene_illustrated": SceneIllustrated,
    "character_occupied": CharacterOccupied,
    "safety_flagged": SafetyFlagged,
    "action_classified": ActionClassified,
    "resource_changed": ResourceChanged,
    "party_size_fixed": PartySizeFixed,
    "creation_step_completed": CreationStepCompleted,
    "creation_interjection": CreationInterjection,
    "character_created": CharacterCreated,
    "party_roster_locked": PartyRosterLocked,
    "creation_gm_spoke": CreationGmSpoke,
    "creation_consent_recorded": CreationConsentRecorded,
    "creation_host_claimed": CreationHostClaimed,
    "scene_opened": SceneOpened,
}


def _resolve_two_d6(roller, command: ResolveCheck, rulebook: Rulebook):
    return resolve_2d6(roller, command.move, command.modifiers, command.target)


def _resolve_d100_roll_under(roller, command: ResolveCheck, rulebook: Rulebook):
    return resolve_d100(
        roller, command.move, command.modifiers, command.target, rulebook.grade_bands
    )


_RESOLVERS: dict[str, Callable] = {
    TWO_D6: _resolve_two_d6,
    D100_ROLL_UNDER: _resolve_d100_roll_under,
}


class CommandRejected(Exception):
    """세션 액터가 명령을 처리할 수 없을 때 던진다. 이 명령에 대해 아무것도 기록되지 않는다."""


class AlreadyOccupied(CommandRejected):
    """이미 이 브라우저가 잡고 있는 캐릭터다 — 라우트는 이것을 성공으로 해석한다
    (본인 재접속은 그대로 통과한다, D-05). `CommandRejected`의 하위 클래스라
    기존 `except CommandRejected` 경로가 그대로 잡는다 — 구분이 필요한 자리에서만
    이 클래스를 먼저 잡는다."""


class AlreadyConfirmed(CommandRejected):
    """이미 확인된 선언에 **같은** move/stat로 다시 확인이 들어왔다 — 라우트는
    이것을 성공으로 해석하고 캐시된 판정을 재사용한다(D-09/D-10). `.prior`가
    이미 기록된 확인·판정 순번을 들고 있다. `CommandRejected`의 하위 클래스라
    기존 `except CommandRejected` 경로가 그대로 잡는다 — 재사용이 필요한
    자리에서만 이 클래스를 먼저 잡는다. 문구에 순번·캐릭터·무브 값을 넣지
    않는다(QUAL-05)."""

    def __init__(self, prior: ConfirmedDeclareRecord) -> None:
        super().__init__("이미 확인된 선언이다")
        self.prior = prior


class AlreadyResolved(CommandRejected):
    """이미 판정된 확인에 대해 두 번째 `ResolveCheck`가 들어왔다 (D-11, TEST-02).

    라우트 계층의 재사용 판단(`prior.resolve_seq`가 있으면 재사용, 없으면
    제출)은 확인↔판정 사이에 검사-후-사용(TOCTOU) 창을 남긴다 — 같은
    선언에 대한 확인 요청 두 개가 동시에 들어오면, 큐가 `ConfirmAction`
    자체는 직렬화해도(`AlreadyConfirmed`), 둘 다 "아직 판정 안 됨"을 보고
    라우트에서 각자 `ResolveCheck`를 제출할 수 있다. 이 예외가 그 창을
    액터 안에서 닫는다 — `.resolve_seq`가 이미 기록된 판정 순번을 들고
    있어 라우트는 그 값으로 기존 되읽기 경로를 그대로 탄다.
    `CommandRejected`의 하위 클래스다."""

    def __init__(self, resolve_seq: int) -> None:
        super().__init__("이미 판정된 확인이다")
        self.resolve_seq = resolve_seq


class AlreadyChanged(CommandRejected):
    """이미 같은 `caused_by_seq`로 기록된 자원 변화가 있다(판 8, Phase 8
    멱등성 창 재사용) — 재시도가 자원을 두 번 깎지 않는다. `.resource_seq`가
    이미 기록된 `resource_changed` 사건의 순번을 들고 있다.
    `CommandRejected`의 하위 클래스라 기존 `except CommandRejected` 경로가
    그대로 잡는다."""

    def __init__(self, resource_seq: int) -> None:
        super().__init__("이미 기록된 자원 변화다")
        self.resource_seq = resource_seq


class AlreadyGmSpoken(CommandRejected):
    """이미 같은 `dedupe_key`로 기록된 `creation_gm_spoke` 사건이 있다(D-12,
    판 11, 12.3-REVIEW.md CR-04). `announce`/`nominate`/`follow_up`/
    `wrap_up` 네 GM 경로가 겹쳐 들어와도(두 탭, 재시도) 큐 안에서 이
    단락이 두 번째를 막는다 — `.prior`가 이미 기록된 `CreationGmLineFold`를
    들고 있어 호출부가 그 값을 그대로 재사용한다. `CommandRejected`의
    하위 클래스라 기존 `except CommandRejected` 경로가 그대로 잡는다 —
    재사용이 필요한 자리에서만 이 클래스를 먼저 잡는다."""

    def __init__(self, prior: CreationGmLineFold) -> None:
        super().__init__("이미 같은 dedupe_key로 기록된 GM 말이 있다")
        self.prior = prior


class GmSlotBusy(CommandRejected):
    """이미 다른 요청이 같은 `slot_key`로 AI를 부르는 중이다(D-02/D-03,
    Phase 13). 라우트는 이것을 409로 끝낸다 — 다른 탭이 지금 부르고
    있으므로 화면은 폴링으로 결과를 받는다. `CommandRejected`의 하위
    클래스라 기존 `except CommandRejected` 경로가 그대로 잡는다 — 409로
    구분해야 하는 자리에서만 이 클래스를 먼저 잡는다."""


class GmSlotClaimed(CommandRejected):
    """`ClaimGmSlot`이 성공했다는 뜻이다 — `ProceedEligible`과 같은 자리
    (사건을 안 남기는 「확인만 하는」 명령의 성공을 예외로 표현해야
    `_process`가 append 이전에 멈춘다). **이름과 달리 실패가 아니다** —
    호출부는 이 예외를 성공으로 해석하고 그대로 진행한다."""


class GmSlotReleased(CommandRejected):
    """`ReleaseGmSlot`이 성공했다는 뜻이다 — `GmSlotClaimed`와 같은 자리·
    같은 이유. 호출부(라우트의 `finally`)는 반환값을 보지 않으므로 이
    예외를 굳이 잡을 필요조차 없다."""


class SceneAlreadyOpened(CommandRejected):
    """이 세션은 이미 오프닝이 열렸다(D-01, Phase 13). `.prior_seq`가
    이미 기록된 `scene_opened` 사건의 순번을 들고 있다 — 라우트는 이
    값으로 200 + `opened=False`를 돌려준다(겹친 탭에게 오류를 보이지
    않는다, `AlreadyGmSpoken`을 잡아 지난 문장을 그대로 돌려주는
    `announce_creation`의 규율과 같다).

    **슬롯(`GmSlotBusy`)과 이 예외는 서로 다른 갈래를 막는다** — 슬롯은
    「동시」를(두 요청이 같은 순간에 온다), 이 예외는 「이미 끝남」을
    (첫 호출이 이미 끝난 뒤 두 번째 요청이 온다) 막는다. 슬롯만 있으면
    첫 호출이 끝난 뒤 슬롯이 풀린 다음에 온 요청이 슬롯을 새로 따서
    오프닝을 다시 열려고 시도할 수 있다 — 둘 다 필요하다."""

    def __init__(self, prior_seq: int) -> None:
        super().__init__("이미 장면이 열렸다")
        self.prior_seq = prior_seq


class RosterAlreadyLocked(CommandRejected):
    """파티 명단이 이미 잠긴 뒤 만들기 관련 명령이 들어왔다(D-08) — 중간에
    추가·제외는 없다. `CommandRejected`의 하위 클래스라 기존
    `except CommandRejected` 경로가 그대로 잡는다."""


class ProceedEligible(CommandRejected):
    """`VerifyProceedEligibility` 검증이 전부 통과했다는 뜻이다 —
    `proceed()`(웹)·CLI `no_check` 갈래 전용(11-06 rework, T-11-29).

    `CommandRejected`의 하위 클래스인 이유는 `AlreadyOccupied`/
    `AlreadyConfirmed`와 같다 — 사건을 안 남기는 「확인만 하는」 명령의
    성공을 예외로 표현해야 `_process`가 append 이전에 멈춘다. **이름과
    달리 실패가 아니다** — 라우트/CLI는 이 예외를 성공으로 해석하고
    그대로 진행한다."""


class SessionActor:
    """asyncio.Queue 하나 + 그 큐를 소비하는 태스크 하나. 세션당 쓰기 주체는 이거 하나뿐이다."""

    def __init__(
        self,
        store: EventStore,
        session_id: str,
        roller: Roller,
        *,
        clock_id: str = "threat",
        clock_segment_count: int = THREAT_CLOCK_SEGMENT_COUNT,
        report_dir: Path | None = None,
    ) -> None:
        self._store = store
        self._session_id = session_id
        self._roller = roller
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None
        # **저장소에 이미 쌓인 사건을 그대로 다시 접어 시작한다** — `initial_state()`로
        # 시작하면 액터가 새로 만들어질 때마다(서버 재시작, 또는 CLI `submit`처럼
        # 명령 하나당 프로세스 하나가 뜨는 경로) 이 액터의 자기 인식이 빈 세션으로
        # 되돌아간다. 검증(순번 충돌은 예외다 — `EventStore.next_seq`가 프로세스
        # 경계와 무관하게 지킨다)과 `_maybe_auto_advance`의 `fails_since_clock` 문턱
        # 판정이 전부 `self.state`를 본다 — 이 칸이 사건 기록과 어긋나면 "현재
        # 상태는 그 기록에서만 재구성된다"는 이 프로젝트의 되돌릴 수 없는 결정
        # (PROJECT.md)이 액터 내부에서만 조용히 깨진다. `poll_events`가 이미 매
        # 요청마다 같은 `rebuild_state`로 화면 값을 다시 접는 것과 같은 이유,
        # 같은 함수다 — 두 번째 재구성 로직을 새로 만들지 않는다.
        self.state: GameState = rebuild_state(store, session_id)
        # clock_id를 생성 시점에 묶는다 — GameState는 마지막으로 쓴 clock_id를
        # 기억하지 않으므로, 첫 자동 진행이 일어날 때 참고할 값이 아무 데도
        # 없다. 세션당 위협 시계 하나(EXP-01)와 cli/turn_flow.py가 이미 쓰는
        # "threat" 관례에 맞춰 생성 인자로 받는 것이 닭-달걀 조회를 없애는
        # 가장 단순한 길이다.
        self._clock_id = clock_id
        # 자동 진행의 상한. 기본값의 출처는 `rulebooks.threat_clocks`이고
        # 그 값 하나가 프롬프트 분모(`turn.context`)·화면 분모
        # (`web.routes_events`)·이 상한까지 동시에 정한다 — 같은 숫자를
        # 세 자리에 따로 적지 않는다.
        self._clock_segment_count = clock_segment_count
        self._report_dir = report_dir if report_dir is not None else DEFAULT_REPORTS_DIR
        self._gm_slots_in_flight: set[str] = set()
        """지금 이 순간 AI를 부르는 중인 슬롯 키 집합(D-02/D-03, Phase 13).
        **사건이 아니다** — 서버 재시작을 넘겨 살아남을 필요가 없고,
        오히려 살아남으면 재시작 뒤 슬롯이 영구히 잠긴다. `ClaimGmSlot`/
        `ReleaseGmSlot`만 이 집합을 건드린다."""

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """소비자 루프에 종료 신호를 넣고 끝날 때까지 기다린다."""
        if self._task is not None:
            await self._queue.put(None)
            await self._task
            self._task = None

    async def submit(self, command: Command) -> int:
        """명령을 큐에 넣고 처리가 끝날 때까지 기다린 뒤, 기록된 사건의 순번을 돌려준다.

        검증에 실패하면 `CommandRejected`가, 순번 충돌이 나면 `SequenceConflict`가
        그대로 이 호출자에게 전달된다 — 액터는 어느 쪽도 삼키지 않는다.
        """
        future: asyncio.Future[int] = asyncio.get_running_loop().create_future()
        await self._queue.put((command, future))
        return await future

    async def _run(self) -> None:
        while True:
            item = await self._queue.get()
            if item is None:
                self._queue.task_done()
                break
            command, future = item
            try:
                seq = await self._process(command)
            except Exception as exc:  # noqa: BLE001 - 부르는 쪽에 그대로 전달한다, 삼키지 않는다
                if not future.done():
                    future.set_exception(exc)
            else:
                if not future.done():
                    future.set_result(seq)
            self._queue.task_done()

    async def _process(self, command: Command) -> int:
        event_type, caused_by_seq, fields = self._prepare(command)

        seq = self._store.next_seq(self._session_id)
        event = _EVENT_CLASSES[event_type](
            session_id=self._session_id,
            seq=seq,
            schema_version=EVENT_SCHEMA_VERSION,
            caused_by_seq=caused_by_seq,
            recorded_at=utc_now_iso(),
            event_type=event_type,
            **fields,
        )
        self._store.append(event)
        self.state = apply_event(self.state, event.event_type, event.model_dump())

        await self._maybe_auto_advance(event_type, seq)
        self._write_report_snapshot()
        return seq

    async def _maybe_auto_advance(self, event_type: str, check_seq: int) -> None:
        """이벤트 하나가 기록된 직후, 그 결과로 조건이 맞으면 다음 명령을
        **직접 재귀 호출**로 이어 붙인다 — 두 가지 경우다.

        ① 실패 판정이 문턱을 넘으면 위협 시계를 스스로 한 칸 돌린다
        (RIG-04, D-21). ② 완성된 캐릭터 전원이 동의하면 파티 명단을
        스스로 잠근다(D-03/D-10, 판 11부터 이 함수로 옮겨왔다 — 그
        전에는 동의를 처리하던 전용 메서드가 액터 메모리 위에서 같은
        재귀를 했다).

        `_process`를 큐에 다시 넣지 않고 **직접 재귀 호출**한다 — 큐로 돌리면
        그 사이에 다른 플레이어의 명령이 끼어들어 "3번째 실패와 그 실패가
        부른 시계 진행"(또는 "전원 동의와 그 순간의 명단 잠금") 사이가
        벌어지고, 최악의 경우 두 플레이어가 동시에 3번째 실패를 만들어
        시계가 두 칸 돌거나, 두 동의가 동시에 들어와 명단이 두 번 잠기려는
        경합이 생긴다. `_process`를 직접 부르면 이미 단일 소비자 안이므로
        원자적이다.

        재귀는 최대 한 겹이다 — 시계 진행 사건(`clock_advanced`)도 명단
        잠금 사건(`party_roster_locked`)도 `check_resolved`나
        `creation_consent_recorded`가 아니므로 이 메서드를 다시 부르지
        않는다.

        **마지막 칸에 도달하면 더 돌리지 않는다.** 예전에는 상한 없이
        `clock_segment + 1`을 썼기 때문에 파국(4/4) 이후 실패가 3번 더 쌓이면
        `5/4`, `6/4`가 기록되고 화면 머리띠에도 그대로 찍혔다 — 플레이어에게는
        버그로 보이는 값이다. D-47이 "코드로 상한선을 강제하지 않고, 파국
        이후에도 즉흥으로 계속 진행하지도 않는다"고 정한 것의 뒷문장을
        지키는 것이 이 상한이다: 진행자가 파국 서사 직후 세션을 마무리하는
        동안에도 자동 진행이 뒤에서 칸을 더 밀어 올리지 않는다. 실패 자체는
        계속 세어지므로(`failure_count`는 초기화되지 않는다) MEAS-03의 분자는
        잃지 않는다 — `fails_since_clock`만 문턱 위에 머문다.
        """
        if event_type == "creation_consent_recorded":
            if self._all_created_characters_consented():
                await self._process(
                    LockPartyRoster(character_ids=tuple(self.state.created_characters))
                )
            return
        if event_type != "check_resolved":
            return
        if self.state.fails_since_clock < AUTO_ADVANCE_FAILURE_THRESHOLD:
            return
        if self.state.clock_segment >= self._clock_segment_count:
            return
        await self._process(
            AdvanceClock(
                clock_id=self._clock_id,
                segment_index=self.state.clock_segment + 1,
                trigger="fail_counter",
                caused_by_seq=check_seq,
            )
        )

    def _unfinished_creation_candidates(self) -> tuple[str, ...]:
        """항목을 하나라도 냈지만 아직 완성되지 않은 사람의 닫힌 목록
        (CR-02, 12.1-REVIEW.md).

        `web/routes_creation.py`의 `_unfinished_candidates`와 정확히 같은
        계산이다 — 그 도우미를 여기서 import할 수 없으므로(`.importlinter`
        contract:2, `gptrpg.web`은 `gptrpg.session_actor`보다 위층이다)
        액터가 이미 갖고 있는 같은 두 값(`state.creation_step_values`의
        키·`state.created_characters`)으로 같은 계산을 이 층에서도 한다.
        「동의 집계」와 「명단 잠금」 둘 다 이 값이 비어 있어야만 진행할 수
        있다(아래 `_all_created_characters_consented`/`_prepare_lock_roster`
        참조) — 라우터만 이 검사를 하면 `LockPartyRoster`를 직접 부르는
        경로(라우터 우회 포함)가 막히지 않는다.
        """
        seen: list[str] = []
        for character_id, _step_id in self.state.creation_step_values:
            if character_id not in self.state.created_characters and character_id not in seen:
                seen.append(character_id)
        return tuple(seen)

    def _party_size_shortfall(self) -> int:
        """이번 판 인원으로 정한 수에서 아직 모자란 완성 캐릭터 수(G-12.3-11).

        `_unfinished_creation_candidates()`가 원리적으로 못 보는 것을 본다 —
        그 목록은 **항목을 하나라도 낸 사람**만 담으므로(그 함수의 doc 참조),
        들어와서 아직 아무것도 안 누른 참가자는 어느 검사에도 안 걸린다.
        그래서 먼저 끝낸 한 사람이 혼자 명단을 잠그고 판을 시작해 버릴 수
        있었다. 방장이 정한 `party_size_fixed`는 이 세션이 **몇 명짜리인지
        아는 유일한 닫힌 숫자**다 — 명단 잠금은 그 수만큼 실제로 완성된
        뒤에만 일어난다.

        인원이 아직 안 정해졌으면(`None`) 0을 낸다 — 그때는 이 검사가
        말할 수 있는 것이 없다.
        """
        if self.state.party_size_fixed is None:
            return 0
        return max(0, self.state.party_size_fixed - len(self.state.created_characters))

    def _all_created_characters_consented(self) -> bool:
        """완성된 캐릭터 전원이 동의했는가(D-10) — 빈 세션(아직 아무도
        안 만들었다)은 「전원 동의」로 세지 않는다.

        **CR-02 (12.1-REVIEW.md):** 아직 한창 만드는 중인 사람이 있으면
        (`_unfinished_creation_candidates()`가 비어 있지 않으면) 완성된
        전원이 동의했더라도 「전원 동의」로 세지 않는다 — 안 그러면 그
        사람이 끝나기도 전에 명단이 잠기고, D-08은 잠금을 되돌리는 사건을
        두지 않으므로 영구히 배제된다. 이 사람의 동의 자체는 그대로
        기록되어 남는다(`_prepare_consent`가 낸 `creation_consent_recorded`
        사건이 이 함수 호출 **전에** 이미 `self.state.creation_consents`에
        접혀 있다) — 나중에 한창 만들던 사람이 완성하고 동의하면 그
        시점에 다시 이 함수가 불리며(그 사람도 `RecordConsent`를 보내야
        한다) 전원 동의로 자연히 넘어간다.

        (판 11부터, Phase 12.3) 이 값의 출처가 액터 메모리에서
        `self.state.creation_consents`(사건에서 다시 접은 값)로
        바뀌었다 — 서버 재시작에도 살아남는다.
        """
        if self._unfinished_creation_candidates():
            return False
        if self._party_size_shortfall():
            return False
        if self.state.reopened_creation_steps:
            # G-12.3-22 — 다시 열어 놓고 아직 안 채운 항목이 있으면 「전원
            # 동의」로 세지 않는다. 이 검사가 여기 **없으면** 자동 진행이
            # 잠금을 시도하고 `_prepare_lock_roster`의 같은 검사가 거절해,
            # 그 거절이 동의 요청의 409로 튀어나온다 — 마지막에 동의한
            # 사람이 아무 잘못 없이 오류를 받는다. CR-02가 미완성자에게
            # 이미 쓰는 것과 같은 이중 배치다.
            return False
        return bool(self.state.created_characters) and all(
            self.state.creation_consents.get(character_id, False)
            for character_id in self.state.created_characters
        )

    def _prepare_consent(self, command: RecordConsent) -> tuple[str, int | None, dict]:
        """동의 표시 하나를 사건으로 남긴다(D-10, 판 11부터 — `RecordConsent`
        도크스트링 참조). 전원 동의가 모이는 순간의 자동 잠금은 이 함수가
        아니라 `_maybe_auto_advance`가 (사건이 접힌 뒤) 처리한다 — 이
        메서드는 다른 `_prepare_*`들과 같은 계약(검증만, 부수효과 없음)을
        지킨다.
        """
        if self.state.party_roster is not None:
            raise RosterAlreadyLocked("파티 명단이 이미 잠겼다")
        if command.character_id not in self.state.created_characters:
            raise CommandRejected("완성되지 않은 캐릭터는 동의를 표시할 수 없다")
        return (
            "creation_consent_recorded",
            None,
            {
                "character_id": command.character_id,
                "browser_id": command.browser_id,
                "agree": command.agree,
                "reopened_step_id": None,
            },
        )

    def _prepare_reopen(self, command: ReopenCreationStep) -> tuple[str, int | None, dict]:
        """그 (character_id, step_id) 하나만 다시 여는 사건을 남긴다
        (D-11, 판 11부터). **앞서 받은 동의를 전부 무효화한다** — 바뀐
        내용에 대한 동의를 다시 받아야 한다(위 「결정한 열린 지점 ③」,
        12.1-04-PLAN.md). 그 무효화는 이 메서드가 아니라 리듀서
        (`apply_event`의 `creation_consent_recorded` 분기, `agree=False`
        갈래)가 접는 시점에 한다.
        """
        if self.state.party_roster is not None:
            raise RosterAlreadyLocked("파티 명단이 이미 잠겨 다시 열 수 없다")
        if command.character_id not in self.state.created_characters:
            raise CommandRejected("완성되지 않은 캐릭터의 항목은 다시 열 필요가 없다")
        return (
            "creation_consent_recorded",
            None,
            {
                "character_id": command.character_id,
                "browser_id": command.browser_id,
                "agree": False,
                "reopened_step_id": command.step_id,
            },
        )

    def _write_report_snapshot(self) -> None:
        """`write_report`를 불러 집계 파일을 최신으로 갱신한다 (D-44).

        집계 파일을 못 써서 사건 기록이 막히면 안 된다 — 사건 기록이 이
        프로젝트의 진실이고 집계는 그 파생물이다. `OSError`/`UnsafeSessionId`를
        잡아 경고 한 줄만 찍고 그냥 돌아온다.
        """
        try:
            write_report(self.state, base_dir=self._report_dir)
        except (OSError, UnsafeSessionId) as exc:
            print(f"경고: 집계 파일 저장 실패 — {exc}", file=sys.stderr)

    def _prepare(self, command: Command) -> tuple[str, int | None, dict]:
        if isinstance(command, DeclareAction):
            return self._prepare_declare(command)
        if isinstance(command, ConfirmAction):
            return self._prepare_confirm(command)
        if isinstance(command, OccupyCharacter):
            return self._prepare_occupy(command)
        if isinstance(command, ResolveCheck):
            return self._prepare_resolve_check(command)
        if isinstance(command, AppendNarration):
            return self._prepare_narration(command)
        if isinstance(command, AdvanceClock):
            return self._prepare_clock(command)
        if isinstance(command, RecordAiCall):
            return self._prepare_ai_call(command)
        if isinstance(command, RecordSceneIllustration):
            return self._prepare_scene_illustration(command)
        if isinstance(command, RecordSafetyFlag):
            return self._prepare_safety_flag(command)
        if isinstance(command, RecordActionClassification):
            return self._prepare_record_action_classification(command)
        if isinstance(command, VerifyProceedEligibility):
            return self._prepare_verify_proceed_eligibility(command)
        if isinstance(command, RecordResourceChange):
            return self._prepare_record_resource_change(command)
        if isinstance(command, FixPartySize):
            return self._prepare_fix_party_size(command)
        if isinstance(command, CompleteCreationStep):
            return self._prepare_complete_creation_step(command)
        if isinstance(command, CreateCharacter):
            return self._prepare_create_character(command)
        if isinstance(command, LockPartyRoster):
            return self._prepare_lock_roster(command)
        if isinstance(command, RecordInterjection):
            return self._prepare_interjection(command)
        if isinstance(command, RecordGmSpoke):
            return self._prepare_gm_spoke(command)
        if isinstance(command, RecordConsent):
            return self._prepare_consent(command)
        if isinstance(command, ReopenCreationStep):
            return self._prepare_reopen(command)
        if isinstance(command, ClaimCreationHost):
            return self._prepare_claim_host(command)
        if isinstance(command, ClaimGmSlot):
            return self._prepare_claim_gm_slot(command)
        if isinstance(command, ReleaseGmSlot):
            return self._prepare_release_gm_slot(command)
        if isinstance(command, OpenScene):
            return self._prepare_open_scene(command)
        raise CommandRejected(f"알 수 없는 명령: {command!r}")

    def _validate_caused_by(self, caused_by_seq: int | None) -> None:
        """caused_by_seq가 있으면 이 세션에 실제로 존재하는 순번인지 확인한다.

        없는 순번을 가리키면 나중에 응답 시간 계산이 짝을 못 찾는다.
        """
        if caused_by_seq is None:
            return
        if caused_by_seq < 0 or caused_by_seq >= self._store.next_seq(self._session_id):
            raise CommandRejected(
                f"caused_by_seq {caused_by_seq}는 이 세션에 실제로 존재하는 순번이 아니다"
            )

    def _prepare_declare(self, command: DeclareAction) -> tuple[str, int | None, dict]:
        if not command.player_id.strip():
            raise CommandRejected("player_id는 비어 있을 수 없다")
        if not command.raw_text.strip():
            raise CommandRejected("raw_text는 비어 있을 수 없다")
        return (
            "action_declared",
            None,
            {
                "player_id": command.player_id,
                "raw_text": command.raw_text,
                "character_id": command.character_id,
            },
        )

    def _prepare_confirm(self, command: ConfirmAction) -> tuple[str, int | None, dict]:
        if not command.player_id.strip():
            raise CommandRejected("player_id는 비어 있을 수 없다")
        if not command.move.strip():
            raise CommandRejected("move는 비어 있을 수 없다")
        if not command.stat.strip():
            raise CommandRejected("stat는 비어 있을 수 없다")
        self._validate_caused_by(command.caused_by_seq)

        # TRUST-03 — 최종 방어선: 확인하는 쪽이 그 선언을 낸 쪽과 같은
        # 캐릭터인가. 라우트 계층 검사만으로는 우회 경로(CLI·시험·다음
        # 단계의 새 호출부)가 남는다(D-11) — 이 검사는 사건에서 다시 접은
        # `declare_owners`를 보므로 서버 재시작 뒤에도 그대로 성립한다.
        # 소유자가 `None`이면(판 5 미만 기록) 통과시킨다 — 옛 세션의 처리는
        # D-14가 08-02에서 따로 정한다. 문구는 어느 캐릭터인지 말하지 않는다
        # (QUAL-05).
        declared_owner = self.state.declare_owners.get(command.caused_by_seq)
        if declared_owner is not None and declared_owner != command.character_id:
            raise CommandRejected("이 선언은 다른 캐릭터가 낸 것이다")

        # D-10/TRUST-05 — 멱등 단락: 이 선언이 이미 확인된 적 있으면 두 번째
        # 확인은 여기서 끝난다. **다름 검사가 먼저**다 — 순서가 바뀌면
        # 「마음이 바뀌었다」(다른 move/stat)가 캐시 재사용으로 새어 나가고,
        # 사람이 정말로 다시 눌렀을 때만(같은 move/stat) 캐시를 재사용해야
        # 하는 이 검사의 의도가 깨진다.
        prior = self.state.confirmed_declares.get(command.caused_by_seq)
        if prior is not None:
            if prior.move != command.move or prior.stat != command.stat:
                raise CommandRejected("이미 다른 무브로 확인된 선언이다")
            raise AlreadyConfirmed(prior)

        return (
            "action_confirmed",
            command.caused_by_seq,
            {
                "player_id": command.player_id,
                "move": command.move,
                "stat": command.stat,
                "system_suggestion": command.system_suggestion,
                "player_confirmed": command.player_confirmed,
                "character_id": command.character_id,
            },
        )

    def _prepare_occupy(self, command: OccupyCharacter) -> tuple[str, int | None, dict]:
        """캐릭터 점유 판정 — 먼저 잡은 사람이 임자다(D-05). 놓기는 없다(D-07).

        검증 순서가 중요하다(주석은 각 단계가 무엇을 지키는지 적는다).
        """
        if not command.character_id.strip():
            raise CommandRejected("character_id는 비어 있을 수 없다")
        if not command.browser_id.strip():
            raise CommandRejected("browser_id는 비어 있을 수 없다")

        # D-14: 사건이 존재하는데(last_seq >= 0) 점유 사건이 하나도 없으면
        # 옛 세션(판 5 미만 기록)이다 — 다시보기만 된다. **세 조건을 반드시
        # 함께 본다** — occupied_by가 비었다는 사실 하나만으로 판정하면
        # 사건이 하나도 없는 새 세션도 같은 조건을 만족해 아무도 시작하지
        # 못하게 된다(D-14가 못박은 그 실수).
        #
        # **판 9부터 이 전제가 다시 깨진다(12.1-01 트레이서가 잡아낸 충돌).**
        # 만들기 사건 셋(party_size_fixed/creation_step_completed/
        # character_created)을 먼저 쌓은 **새** 세션은 정확히 "사건은 있는데
        # 점유가 없는" 모양이 된다 — CHAR-05가 요구하는 자동 점유(만들기
        # 완료 사건이 점유보다 먼저 기록된다)가 이 검사에 정면으로 걸린다.
        # `created_characters`가 하나라도 있으면 그것은 판 9 이후의 새
        # 세션이라는 뜻이므로 세 번째 조건으로 더한다 — 판 9가 "사건은
        # 있는데 점유가 없는 정상 상태"를 처음 만들었다.
        if (
            self.state.last_seq >= 0
            and not self.state.occupied_by
            and not self.state.created_characters
        ):
            raise CommandRejected("이 세션은 점유 기록이 없는 옛 세션이다 — 다시보기만 된다")

        holder = self.state.occupied_by.get(command.character_id)
        if holder is not None and holder == command.browser_id:
            # 본인 재접속 — 성공으로 해석되지만 새 사건은 남기지 않는다.
            raise AlreadyOccupied("이미 이 캐릭터를 점유하고 있다")
        if holder is not None:
            # 어느 브라우저가 쥐고 있는지 문구에 넣지 않는다(QUAL-05).
            raise CommandRejected("이미 다른 분이 고른 캐릭터예요")

        # 한 브라우저는 한 캐릭터만(D-07) — 이 browser_id가 이미 다른
        # 캐릭터를 쥐고 있으면 거부한다.
        for occupied_character_id, occupied_browser_id in self.state.occupied_by.items():
            if occupied_browser_id == command.browser_id and occupied_character_id != (
                command.character_id
            ):
                raise CommandRejected("이 브라우저는 이미 다른 캐릭터를 점유하고 있다")

        return (
            "character_occupied",
            None,
            {"character_id": command.character_id, "browser_id": command.browser_id},
        )

    def _prepare_resolve_check(self, command: ResolveCheck) -> tuple[str, int | None, dict]:
        self._validate_caused_by(command.caused_by_seq)

        # D-11/TEST-02 — 멱등 단락 둘째 겹: 이 확인(`caused_by_seq`)이 이미
        # 판정됐으면 여기서 끝난다. `AlreadyResolved` 도크스트링이 이 검사가
        # 막는 정확한 TOCTOU 창을 설명한다.
        declare_seq = self.state.confirm_to_declare.get(command.caused_by_seq)
        if declare_seq is not None:
            prior = self.state.confirmed_declares.get(declare_seq)
            if prior is not None and prior.resolve_seq is not None:
                raise AlreadyResolved(prior.resolve_seq)

        if not command.person_id.strip():
            raise CommandRejected("person_id는 비어 있을 수 없다")
        if not command.character_id.strip():
            raise CommandRejected("character_id는 비어 있을 수 없다")

        try:
            rulebook = get_rulebook(command.rulebook_id)
        except UnknownRulebook as exc:
            raise CommandRejected(str(exc)) from exc

        # RULE-02/03(D-01) — 능력치를 판정에 싣는다. `stat`이 빈 문자열이면
        # 건너뛴다(`ResolveCheck.stat` 도크스트링 — 저수준 디버그 통로가
        # 이 칸 없이도 계속 동작해야 한다). 채워지면 캐릭터가 그 능력치를
        # 실제로 갖고 있는지, 그 축이 판정에 쓰이도록 선언됐는지를
        # `build_stat_check_input`이 검증한다 — 조용히 0으로 넘어가지 않는다.
        modifiers = command.modifiers
        target = command.target
        if command.stat:
            try:
                stat_input = build_stat_check_input(
                    command.character_stats, command.stat, rulebook.resource_axes
                )
            except (UnknownStatForCheck, StatNotUsableInChecks) as exc:
                raise CommandRejected(str(exc)) from exc
            if stat_input.modifier is not None:
                modifiers = (stat_input.modifier, *modifiers)
            if stat_input.target is not None:
                target = stat_input.target

        # D-02 — 난이도는 룰북이 선언한 닫힌 이름 목록에서만 고른다. 목록에
        # 없는 이름은 사건을 남기기 전에 거절된다(자유 숫자가 아니라 이름만
        # 바깥에서 받는다).
        if command.difficulty is not None:
            try:
                level = require_difficulty(rulebook, command.difficulty)
            except UnknownDifficultyLevel as exc:
                raise CommandRejected(str(exc)) from exc
            modifiers = (
                *modifiers,
                Modifier(
                    type=level.modifier_type,
                    value=level.value,
                    source=f"difficulty:{level.name}",
                ),
            )

        effective_command = (
            command
            if modifiers is command.modifiers and target == command.target
            else dataclass_replace(command, modifiers=modifiers, target=target)
        )

        resolver = _RESOLVERS.get(rulebook.resolution_method)
        if resolver is None:
            raise CommandRejected(
                f"알 수 없는 판정 방식: {rulebook.resolution_method!r} "
                f"(룰북 {rulebook.rulebook_id!r})"
            )

        try:
            outcome = resolver(self._roller, effective_command, rulebook)
        except UnsupportedModifier as exc:
            raise CommandRejected(str(exc)) from exc
        except AttributeError as exc:
            raise CommandRejected(
                f"굴림 도구가 {rulebook.resolution_method!r} 판정에 필요한 메서드를 "
                f"갖추지 않았다: {exc}"
            ) from exc
        except NoMatchingGradeBand as exc:
            raise CommandRejected(
                f"룰북 {rulebook.rulebook_id!r}의 등급 밴드 선언이 이 판정 결과를 "
                f"덮지 않는다: {exc}"
            ) from exc

        try:
            band = require_band(rulebook.grade_bands, outcome.grade)
        except UnknownGradeName as exc:
            raise CommandRejected(str(exc)) from exc

        return (
            "check_resolved",
            command.caused_by_seq,
            {
                "move": outcome.move,
                "rolls": list(outcome.rolls),
                "modifiers": [
                    ModifierRecord(type=modifier.type, value=modifier.value, source=modifier.source)
                    for modifier in outcome.modifiers
                ],
                "target": outcome.target,
                "grade": outcome.grade,
                "counts_as_failure": band.counts_as_failure,
                "person_id": command.person_id,
                "character_id": command.character_id,
                "total": outcome.total,
                "rulebook_id": command.rulebook_id,
            },
        )

    def _prepare_narration(self, command: AppendNarration) -> tuple[str, int | None, dict]:
        if not command.text.strip():
            raise CommandRejected("text는 비어 있을 수 없다")
        if command.chunk_index < 0:
            raise CommandRejected("chunk_index는 0 이상이어야 한다")
        self._validate_caused_by(command.caused_by_seq)
        return (
            "narration_appended",
            command.caused_by_seq,
            {"text": command.text, "chunk_index": command.chunk_index},
        )

    def _prepare_clock(self, command: AdvanceClock) -> tuple[str, int | None, dict]:
        if not command.clock_id.strip():
            raise CommandRejected("clock_id는 비어 있을 수 없다")
        if command.segment_index < 0:
            raise CommandRejected("segment_index는 0 이상이어야 한다")
        if command.trigger not in _VALID_CLOCK_TRIGGERS:
            raise CommandRejected(
                f"trigger는 {sorted(_VALID_CLOCK_TRIGGERS)} 중 하나여야 한다: {command.trigger!r}"
            )
        self._validate_caused_by(command.caused_by_seq)
        return (
            "clock_advanced",
            command.caused_by_seq,
            {
                "clock_id": command.clock_id,
                "segment_index": command.segment_index,
                "trigger": command.trigger,
            },
        )

    def _prepare_ai_call(self, command: RecordAiCall) -> tuple[str, int | None, dict]:
        if not command.agent_role.strip():
            raise CommandRejected("agent_role은 비어 있을 수 없다")
        if not command.model.strip():
            raise CommandRejected("model은 비어 있을 수 없다")
        if not command.provider.strip():
            raise CommandRejected("provider는 비어 있을 수 없다")
        if command.prompt_tokens < 0 or command.completion_tokens < 0:
            raise CommandRejected("토큰 수는 0 이상이어야 한다")
        if command.cached_prompt_tokens < 0:
            raise CommandRejected("캐시 적중 토큰 수는 0 이상이어야 한다")
        if command.cached_prompt_tokens > command.prompt_tokens:
            # 이 칸의 정의가 「`prompt_tokens`의 부분집합」이다. 넘으면 어댑터가
            # 캐시 몫을 입력 몫에 포함시키지 않은 것이므로(Anthropic이 실제로
            # 그렇다 — `_input_token_counts`가 그래서 따로 더한다) 조용히
            # 통과시키면 원가가 음수 신규 입력으로 계산된다.
            raise CommandRejected(
                f"캐시 적중 토큰({command.cached_prompt_tokens})이 입력 토큰"
                f"({command.prompt_tokens})보다 많을 수 없다"
            )
        if command.latency_ms < 0:
            raise CommandRejected("소요 시간은 0 이상이어야 한다")
        self._validate_caused_by(command.caused_by_seq)
        return (
            "ai_invoked",
            command.caused_by_seq,
            {
                "agent_role": command.agent_role,
                "model": command.model,
                "provider": command.provider,
                "prompt_tokens": command.prompt_tokens,
                "completion_tokens": command.completion_tokens,
                "latency_ms": command.latency_ms,
                "cached_prompt_tokens": command.cached_prompt_tokens,
            },
        )

    def _prepare_scene_illustration(
        self, command: RecordSceneIllustration
    ) -> tuple[str, int | None, dict]:
        """빈 `image_path`를 거절한다 — 「그림이 있다」가 이 사건의 뜻이다.

        그림을 못 만든 턴은 사건이 없는 턴으로 남아야 한다(`SceneIllustrated`
        도크스트링). 빈 경로를 통과시키면 읽는 쪽마다 빈 값 검사를 다시 해야
        하고, 「삽화 사건이 있다」로 세는 집계가 실제 그림 수와 어긋난다.
        """
        if not command.image_path.strip():
            raise CommandRejected("image_path는 비어 있을 수 없다")
        if not command.prompt.strip():
            raise CommandRejected("prompt는 비어 있을 수 없다")
        if not command.style.strip():
            raise CommandRejected("style은 비어 있을 수 없다")
        if command.steps < 1:
            raise CommandRejected("steps는 1 이상이어야 한다")
        if command.size < 1:
            raise CommandRejected("size는 1 이상이어야 한다")
        if command.latency_ms < 0:
            raise CommandRejected("소요 시간은 0 이상이어야 한다")
        self._validate_caused_by(command.caused_by_seq)
        return (
            "scene_illustrated",
            command.caused_by_seq,
            {
                "image_path": command.image_path,
                "prompt": command.prompt,
                "style": command.style,
                "seed": command.seed,
                "steps": command.steps,
                "size": command.size,
                "latency_ms": command.latency_ms,
            },
        )

    def _prepare_safety_flag(self, command: RecordSafetyFlag) -> tuple[str, int | None, dict]:
        """닫힌 목록 밖 값·음수 길이·말 안 되는 source×reason 조합을 거절한다
        (`_prepare_narration`과 같은 검증 모양).

        자유 문자열이 사건에 들어갈 길이 하나 없다 — `source`/`reason`/
        `disposition` 셋 다 여기서 닫힌 목록으로 강제된다(T-10-03). 개별
        검증 뒤에는 `source`와 `reason`의 조합 검증을 잇는다(10-07, WR-03) —
        `event_log.schema.SafetyFlagged`의 같은 이름 검증자와 짝을 이룬다.
        """
        if command.source not in _VALID_SAFETY_FLAG_SOURCES:
            raise CommandRejected(
                f"source는 {sorted(_VALID_SAFETY_FLAG_SOURCES)} 중 하나여야 한다: {command.source!r}"
            )
        if command.reason not in _VALID_SAFETY_FLAG_REASONS:
            raise CommandRejected(
                f"reason은 {sorted(_VALID_SAFETY_FLAG_REASONS)} 중 하나여야 한다: {command.reason!r}"
            )
        if command.disposition not in _VALID_SAFETY_FLAG_DISPOSITIONS:
            raise CommandRejected(
                f"disposition은 {sorted(_VALID_SAFETY_FLAG_DISPOSITIONS)} 중 하나여야 한다: "
                f"{command.disposition!r}"
            )
        # source×reason 조합 검증(10-07, WR-03) — 개별 검증(위 세 줄) 뒤에
        # 잇는다(개별 검증이 먼저 걸러야 오류 메시지가 정확하다). 이 검증이
        # event_log/schema.py의 SafetyFlagged._require_source_reason_pairing과
        # 중복이 아닌 이유는 그 검증자 도크스트링과 같다 — 이 액터 검증은
        # 명령이 저장소에 닿기 전에 막고, 스키마 검증은 저장소를 우회해 만든
        # 객체까지 막는다. `CheckResolved`가 이미 같은 이중 구조다.
        is_classifier = command.source == "classifier"
        is_unknown_move = command.reason == "unknown_move"
        if is_classifier != is_unknown_move:
            raise CommandRejected(
                "source='classifier'와 reason='unknown_move'는 서로 필요충분이다 — "
                f"받은 조합: source={command.source!r}, reason={command.reason!r}"
            )
        if command.matched_len < 0:
            raise CommandRejected("matched_len은 0 이상이어야 한다")
        if command.subject_len < 0:
            raise CommandRejected("subject_len은 0 이상이어야 한다")
        if command.chunk_index is not None and command.chunk_index < 0:
            raise CommandRejected("chunk_index는 0 이상이어야 한다")
        self._validate_caused_by(command.caused_by_seq)
        return (
            "safety_flagged",
            command.caused_by_seq,
            {
                "source": command.source,
                "reason": command.reason,
                "disposition": command.disposition,
                "matched_len": command.matched_len,
                "subject_len": command.subject_len,
                "chunk_index": command.chunk_index,
            },
        )

    def _prepare_record_action_classification(
        self, command: RecordActionClassification
    ) -> tuple[str, int | None, dict]:
        """분류 결정 기록 — 이 명령 자체는 열린 값을 검증할 게 없다
        (`no_check`는 불리언, `RecordSafetyFlag`류의 닫힌 목록 검증이
        필요 없다). `caused_by_seq`만 존재하는 순번인지 확인한다."""
        self._validate_caused_by(command.caused_by_seq)
        return (
            "action_classified",
            command.caused_by_seq,
            {"no_check": command.no_check},
        )

    def _prepare_verify_proceed_eligibility(
        self, command: VerifyProceedEligibility
    ) -> tuple[str, int | None, dict]:
        """TRUST-03 확장 — `proceed()`(웹)·CLI `no_check` 갈래 전용 이중
        검사(11-06 rework, T-11-29).

        라우트 계층 검사(「내가 이 캐릭터의 주인인가」)만으로는 두 우회가
        남는다 — ① **다른 캐릭터가 낸 선언**에 진행 버튼을 누르는 것(라우트는
        "내 캐릭터"만 보고 "이 선언을 낸 캐릭터"는 안 본다) ② **판정이
        필요했던 선언**(`tier`가 `no_check`가 아니었다)에 진행 버튼을 눌러
        판정을 건너뛰는 것. 두 검사 다 사건에서 접은 상태(`declare_owners`/
        `declare_no_check`)를 본다 — `_prepare_confirm`의 소유권 검사와
        정확히 같은 이유다(우회 경로가 CLI·시험·다음 단계의 새 호출부로
        남는다, D-11 — 서버 재시작 뒤에도 이 검사는 성립한다).

        검증을 전부 통과하면 `ProceedEligible`을 던진다 — 사건을 남기지
        않는다(결정 1, `11-06-PLAN.md`가 여전히 유효하다: 이 검증 자체는
        「판정 없이 진행」 턴의 사건 모양을 하나도 늘리지 않는다).
        """
        if command.declare_seq < 0 or command.declare_seq >= self._store.next_seq(
            self._session_id
        ):
            raise CommandRejected(
                f"declare_seq {command.declare_seq}는 이 세션에 실제로 존재하는 순번이 아니다"
            )

        declared_owner = self.state.declare_owners.get(command.declare_seq)
        if declared_owner is not None and declared_owner != command.character_id:
            raise CommandRejected("이 선언은 다른 캐릭터가 낸 것이다")

        # `declare_owners`와 반대 방향의 "모르면 어떻게 하나" 규칙이다 —
        # `GameState.declare_no_check` 도크스트링 참조. 모르면 통과시키지
        # 않는다: 통과시키면 이 검사가 막으려는 구멍이 다시 열린다.
        if not self.state.declare_no_check.get(command.declare_seq, False):
            raise CommandRejected("이 선언은 판정이 필요해 판정 없이 진행할 수 없다")

        raise ProceedEligible()

    def _prepare_record_resource_change(
        self, command: RecordResourceChange
    ) -> tuple[str, int | None, dict]:
        """판정에 딸린 자원 변화 기록 — 멱등성은 Phase 8 멱등성 창 위에
        올린다(판 8, D-05/D-65).

        `state.resource_change_by_cause.get(command.caused_by_seq)`가 있으면
        `AlreadyChanged(resource_seq)`를 던진다 — 재시도가 자원을 두 번
        깎지 않는다. `changes`가 빈 튜플이면 `CommandRejected` — 변화
        없음은 사건을 아예 안 쓰는 것으로 표현한다(RULE-04/05/09 empty).
        """
        self._validate_caused_by(command.caused_by_seq)
        if command.caused_by_seq is not None:
            prior_seq = self.state.resource_change_by_cause.get(command.caused_by_seq)
            if prior_seq is not None:
                raise AlreadyChanged(prior_seq)

        if not command.character_id.strip():
            raise CommandRejected("character_id는 비어 있을 수 없다")
        if not command.changes:
            raise CommandRejected(
                "changes가 비어 있으면 사건을 남기지 않는다 — 변화 없음은 사건 자체를"
                " 안 쓰는 것으로 표현한다"
            )
        if command.source not in _VALID_RESOURCE_CHANGE_SOURCES:
            raise CommandRejected(
                f"source는 {sorted(_VALID_RESOURCE_CHANGE_SOURCES)} 중 하나여야 한다: "
                f"{command.source!r}"
            )

        changes_payload = [
            {
                "axis": op.axis,
                "operation": op.operation,
                "amount": op.amount,
                "rolls": list(op.rolls),
                # `before`/`after`는 이 계층(액터)이 캐릭터 시작값에 접근할
                # 수 없어(층 계약 — `web` 계층의 캐릭터 데이터는 `session_actor`
                # 아래가 아니다) 계산하지 못한다 — "계산 안 함"을 `None`으로
                # 남긴다("0"과 섞이지 않는다). 캐릭터 시트가 실제 지금 값을
                # 돌려주는 것(RULE-06)은 `resolve_character_stats`가 시작값 +
                # 이 사건들의 이력을 접어 만드는 몫이다.
                "before": None,
                "after": None,
            }
            for op in command.changes
        ]
        return (
            "resource_changed",
            command.caused_by_seq,
            {
                "character_id": command.character_id,
                "changes": changes_payload,
                "category_id": command.category_id,
                "source": command.source,
            },
        )

    def _prepare_fix_party_size(self, command: FixPartySize) -> tuple[str, int | None, dict]:
        """인원 확정 — 재확정은 없다(D-01, Phase 12.1). 룰북 범위 대조는
        `validate_party_size`가 한다(D-02, 12.1-02 Task 2).

        `PARTY_MEMBER_LIMIT`(절대 안전 밸브)은 여기서 검사하지 않는다 —
        `session_actor`는 `agents`를 import할 수 없다(`.importlinter`
        contract:2, `agents`가 `session_actor` 위 층이다). 그 상한은 이
        명령을 만드는 호출부(`web/routes_creation.py`)가 검사해 400으로
        거절한다 — 룰북이 인원을 데이터로 정하므로 이 상한은 이제 인원의
        출처가 아니라 프롬프트 폭주를 막는 코드 상한이다.
        """
        if command.player_character_count < 1:
            raise CommandRejected("인원은 1명 이상이어야 한다")
        if self.state.party_size_fixed is not None:
            raise CommandRejected("인원은 이미 확정됐다 — 재확정은 없다")
        rulebook = get_rulebook(command.rulebook_id)  # UnknownRulebook을 그대로 올린다.
        if rulebook.party_size_range is None:
            raise CommandRejected(
                f"룰북 {command.rulebook_id!r}은 권장 인원을 아직 선언하지 않았다"
            )
        try:
            validate_party_size(rulebook.party_size_range, command.player_character_count)
        except PartySizeOutOfRange as exc:
            # 사람 화면까지 통째로 나가는 유일한 지점이었다(G-12.3-3) —
            # 예외 전체(`str(exc)`)를 그대로 실으면 dataclass repr
            # (`allowed=PartySizeRange(...)`)이 사람 눈에 그대로 나간다.
            # 사람이 읽을 절반은 예외에 이미 따로 있다(`exc.reason`,
            # 「2명은 최소 3명보다 적다」). 예외 자체(`rules_core/rulebook.py`)
            # 는 안 고친다 — 개발자용 로그에는 repr이 유용하므로 두 쓰임을
            # 갈라 둔다(D-15 「이유는 한 자리에만」은 사람용 이유가 한
            # 자리라는 뜻이지, 예외가 정보를 덜 담으라는 뜻이 아니다).
            raise CommandRejected(exc.reason) from exc
        return (
            "party_size_fixed",
            None,
            {
                "player_character_count": command.player_character_count,
                "rulebook_id": command.rulebook_id,
                "rulebook_min": rulebook.party_size_range.min_player_characters,
                "rulebook_max": rulebook.party_size_range.max_player_characters,
            },
        )

    def _prepare_complete_creation_step(
        self, command: CompleteCreationStep
    ) -> tuple[str, int | None, dict]:
        """만들기 항목 하나의 값을 확정한다(D-03, Phase 12.1).

        일곱 kind 전부 값의 모양을 검증한다(12.1-02). `place_fixed_values`는
        배치된 값 묶음이 선언된 `fixed_values`와 다중집합으로 같은지
        검사한다(사람이 없는 숫자를 만들어 넣는 경로를 막는다, T-12.1-04).
        `pick_one`/`pick_many`는 `web/routes_actions.py:603-663`의
        `_pending_resource_changes`가 쓰는 「AI/바깥이 고른 것을 코드가 닫힌
        목록으로 다시 대조」 패턴을 그대로 쓴다. `roll_to_fill`은 브라우저가
        보낸 값을 무시하고 주입된 `Roller`로 직접 굴린다(D14) — 에이전트가
        값을 만들 수 있는 경로가 없다. `derive`는 `depends_on` 단계의 확정된
        축 값을 찾아 `기준값 × derive_multiplier + derive_offset`으로 계산한다.

        **D-07 경계(Phase 12.1-04)** — 그 캐릭터에 `character_created`가
        이미 있으면(차례가 끝났다) 이 명령은 `CommandRejected`다. 유일한
        예외는 `ReopenCreationStep`이 그 (character_id, step_id)를 다시
        열어 둔 경우다(D-11) — 그 경우 이 확정이 통과하고 성공하는 순간
        그 표에서 지워진다(한 번 다시 채우면 다시 닫힌다). 판 11부터
        (Phase 12.3) 그 표는 `self.state.reopened_creation_steps`이고,
        지우는 일은 이 메서드가 아니라 리듀서가 `creation_step_completed`를
        접는 시점에 한다 — 이제 리듀서가 접을 때 닫는다.
        """
        if self.state.party_roster is not None:
            raise RosterAlreadyLocked("파티 명단이 이미 잠겨 만들기를 더 진행할 수 없다")
        reopen_key = (command.character_id, command.step_id)
        if (
            command.character_id in self.state.created_characters
            and reopen_key not in self.state.reopened_creation_steps
        ):
            raise CommandRejected(
                "차례가 끝난 캐릭터의 항목은 고칠 수 없다 — 정리 뒤 동의 관문에서"
                " 말해야 한다"
            )
        rulebook = get_rulebook(command.rulebook_id)
        step = next(
            (decl for decl in rulebook.creation_steps if decl.step_id == command.step_id),
            None,
        )
        if step is None:
            raise CommandRejected(f"룰북 선언에 없는 만들기 단계다: {command.step_id!r}")

        text_value = command.text_value
        picked = command.picked
        axis_values_payload: list[dict] | None = None
        rolls_payload: tuple[int, ...] | None = None

        if step.kind == "free_text":
            if command.text_value is None or not command.text_value.strip():
                raise CommandRejected("free_text 단계는 text_value가 필요하다")
            picked = None
        elif step.kind == "place_fixed_values":
            if not command.axis_values:
                raise CommandRejected("place_fixed_values 단계는 axis_values가 필요하다")
            provided_names = {name for name, _ in command.axis_values}
            if provided_names != set(step.axis_names):
                raise CommandRejected("배치한 축 이름이 룰북 선언과 다르다")
            provided_values = sorted(value for _, value in command.axis_values)
            expected_values = sorted(step.fixed_values or ())
            if provided_values != expected_values:
                raise CommandRejected(
                    "배치된 값 묶음이 선언된 fixed_values와 다르다 — 사람이 없는"
                    " 숫자를 만들어 넣을 수 없다"
                )
            axis_values_payload = [
                {"axis_name": name, "value": value} for name, value in command.axis_values
            ]
            text_value = None
            picked = None
        elif step.kind in ("pick_one", "pick_many"):
            if not command.picked:
                raise CommandRejected(f"{step.kind} 단계는 picked가 필요하다")
            if len(command.picked) != len(set(command.picked)):
                raise CommandRejected("같은 선택지를 두 번 골랐다")
            allowed_options = set(step.options or ())
            unknown = [item for item in command.picked if item not in allowed_options]
            if unknown:
                raise CommandRejected(f"룰북 선언에 없는 선택지다: {unknown!r}")
            if step.kind == "pick_one":
                if len(command.picked) != 1:
                    raise CommandRejected("pick_one은 정확히 하나만 골라야 한다")
            else:
                if len(command.picked) != step.pick_count:
                    raise CommandRejected(
                        f"pick_many는 정확히 {step.pick_count}개를 골라야 한다"
                        f" (받은 개수: {len(command.picked)})"
                    )
            text_value = None
        elif step.kind == "allocate_points":
            if not command.axis_values:
                raise CommandRejected("allocate_points 단계는 axis_values가 필요하다")
            provided_names = [name for name, _ in command.axis_values]
            if len(provided_names) != len(set(provided_names)):
                raise CommandRejected("같은 축에 배분을 두 번 제출했다")
            outside_axes = [name for name in provided_names if name not in step.axis_names]
            if outside_axes:
                raise CommandRejected(f"룰북 선언에 없는 축에 배분했다: {outside_axes!r}")
            if any(value < 0 for _, value in command.axis_values):
                raise CommandRejected("배분 값은 음수일 수 없다")
            total = sum(value for _, value in command.axis_values)
            if total != step.point_budget:
                raise CommandRejected(
                    f"배분 합계({total})가 예산({step.point_budget})과 다르다 —"
                    " 남는 점수를 조용히 버릴 수 없다"
                )
            if step.per_target_max is not None:
                over_cap = [
                    (name, value)
                    for name, value in command.axis_values
                    if value > step.per_target_max
                ]
                if over_cap:
                    raise CommandRejected(
                        f"배분 값이 항목별 상한({step.per_target_max})을 넘는다:"
                        f" {over_cap!r}"
                    )
            axis_values_payload = [
                {"axis_name": name, "value": value} for name, value in command.axis_values
            ]
            text_value = None
            picked = None
        elif step.kind == "roll_to_fill":
            # 브라우저/에이전트가 보낸 값을 무시하고 주입된 Roller로 직접
            # 굴린다 — AI가 이 값을 만들 수 있는 경로가 없다(D14). 에이전트는
            # 굴려서 나온 결과를 서술로 옮기기만 한다.
            assert step.dice_expr is not None  # CreationStepDecl 선언 시점 규약
            all_rolls: list[int] = []
            filled_axis_values: list[dict] = []
            for axis_name in step.axis_names:
                total, rolls = roll_amount(self._roller, step.dice_expr)
                all_rolls.extend(rolls)
                filled_axis_values.append({"axis_name": axis_name, "value": total})
            axis_values_payload = filled_axis_values
            rolls_payload = tuple(all_rolls)
            text_value = None
            picked = None
        elif step.kind == "derive":
            for dep_step_id in step.depends_on:
                if (command.character_id, dep_step_id) not in self.state.creation_step_values:
                    raise CommandRejected(
                        f"의존 단계가 아직 채워지지 않았다: {dep_step_id!r}"
                    )
            base_value: int | None = None
            for dep_step_id in step.depends_on:
                dep_fold = self.state.creation_step_values[(command.character_id, dep_step_id)]
                for axis_name, value in dep_fold.axis_values or ():
                    if axis_name == step.derive_base_axis:
                        base_value = value
                        break
                if base_value is not None:
                    break
            if base_value is None:
                raise CommandRejected(
                    f"기준 축 {step.derive_base_axis!r}의 값을 의존 단계에서 찾을 수 없다"
                )
            assert step.derive_multiplier is not None and step.derive_offset is not None
            derived_value = base_value * step.derive_multiplier + step.derive_offset
            axis_values_payload = [
                {"axis_name": step.axis_names[0], "value": derived_value}
            ]
            text_value = None
            picked = None
        else:
            raise CommandRejected(f"알 수 없는 만들기 단계 kind다: {step.kind!r}")

        key = (command.character_id, command.step_id)
        prior = self.state.creation_step_values.get(key)
        superseded_seq = prior.seq if prior is not None else None

        # D-11 — 다시 열린 항목을 성공적으로 재확정하면 그 표시가 소비된다
        # (한 번 다시 채우면 다시 닫힌다). 이제 리듀서가 접을 때 닫는다
        # (`apply_event`의 `creation_step_completed` 분기) — 이 메서드는
        # 사건을 준비만 할 뿐 상태를 직접 바꾸지 않는다(다른 `_prepare_*`와
        # 같은 계약).

        return (
            "creation_step_completed",
            None,
            {
                "character_id": command.character_id,
                "browser_id": command.browser_id,
                "step_id": command.step_id,
                "kind": step.kind,
                "text_value": text_value,
                "picked": list(picked) if picked is not None else None,
                "axis_values": axis_values_payload,
                "rolls": list(rolls_payload) if rolls_payload is not None else None,
                "superseded_seq": superseded_seq,
            },
        )

    def _prepare_create_character(
        self, command: CreateCharacter
    ) -> tuple[str, int | None, dict]:
        """확정된 만들기 항목 값들을 `Entity`/`StatEntry`로 조립한다(D-03/
        CHAR-04, Phase 12.1). AI가 이 지점에 닿지 않는다(D14) — 값 조립은
        전부 이미 확정된 사건 값을 그대로 옮기는 코드다.

        **하이재킹 항목(12.1-REVIEW.md CR-01 "추가로" 절, 사용자 승인) —
        브라우저 연속성 관문.** `/creation/complete`는 정의상 쿠키가 아직
        없는 상태에서도 성공해야 한다(D22 흐름 — 자기소개를 채운 그
        브라우저는 완성해야 비로소 쿠키를 받는다, `routes_creation.py`의
        `complete_creation` 도크스트링). 그래서 이 관문을 "쿠키가 있어야
        한다"로 세우면 정당한 첫 완성 자체를 막는다. 대신 세우는 것은
        **연속성**이다 — 이 캐릭터의 `creation_step_completed` 사건들을
        실제로 제출한 브라우저와 지금 완성을 요청하는 브라우저가 같은가.
        항목을 채운 적 없는 브라우저가 남이 이미 다 채운 `character_id`를
        알아내 자기 `browser_id`로 먼저 `/creation/complete`를 불러
        가로채는 경로(하이재킹)를 이 대조가 막는다 — `OccupyCharacter`가
        "먼저 잡은 사람이 임자"(D-05)이므로, 만들기 완료 자체에 이 관문이
        없으면 그 완료가 사실상 점유 경쟁의 승자를 대신 정해 버린다.

        **판정 기준을 "포함"이 아니라 "전부 일치"로 세운 이유:** 이
        캐릭터의 만들기 단계는 정의상 한 참가자(=한 브라우저)가 자기
        차례 안에서 채운다(D-03·D-07) — 완성 전 같은 `character_id`에
        서로 다른 브라우저가 항목을 섞어 낼 정당한 경우가 없다. 그래서
        `command.browser_id`가 이 캐릭터의 folds 중 **하나라도** 다른
        브라우저와 짝지어져 있으면(=항목이 이미 섞였으면) 통과시키지
        않는다 — "일부만 내 것"이라는 절반의 소유권을 인정하지 않는다.
        이 검사가 닫지 **않는** 구멍은 `/creation/step` 자체의 위조
        (완성 전 다른 브라우저가 이 캐릭터의 항목 하나를 몰래 제출하는
        것)다 — 그 방어는 12.1-03/04와 이 항목 둘 다 문서로 이미 밝힌
        범위 밖이다(`routes_creation.py`의 `complete_creation_step`
        도크스트링). 이 관문은 그 범위 밖 구멍이 있더라도, 최소한 항목을
        하나도 낸 적 없는 브라우저가 남의 캐릭터를 통째로 가로채는
        가장 값싼 공격은 막는다.

        **놓는 경로를 만들지 않는다(D-08).** 이 검사는 완성을 거절할 뿐
        누구의 점유도 풀지 않는다 — 이미 점유된 캐릭터를 다시 놓게 하는
        새 경로는 D-08이 금지한 것과 정확히 같은 종류라 만들지 않는다.
        """
        if self.state.party_roster is not None:
            raise RosterAlreadyLocked("파티 명단이 이미 잠겨 새 캐릭터를 만들 수 없다")
        rulebook = get_rulebook(command.rulebook_id)

        folds = {
            step_id: fold
            for (character_id, step_id), fold in self.state.creation_step_values.items()
            if character_id == command.character_id
        }
        if not folds:
            raise CommandRejected("확정된 만들기 단계 값이 하나도 없다")

        if any(fold.browser_id != command.browser_id for fold in folds.values()):
            raise CommandRejected(
                "이 캐릭터의 항목을 채운 브라우저와 다른 브라우저는 완성할 수 없다"
            )

        for step in rulebook.creation_steps:
            if step.required and step.step_id not in folds:
                raise CommandRejected(f"필수 단계가 채워지지 않았다: {step.step_id!r}")

        display_name: str | None = None
        axis_value_map: dict[str, int] = {}
        for step in rulebook.creation_steps:
            fold = folds.get(step.step_id)
            if fold is None:
                continue
            if step.provides_display_name:
                if fold.text_value:
                    display_name = fold.text_value
                elif fold.picked:
                    display_name = ", ".join(fold.picked)
            if fold.axis_values:
                for axis_name, value in fold.axis_values:
                    axis_value_map[axis_name] = value

        if display_name is None:
            raise CommandRejected("표시 이름을 만들 확정된 단계 값이 없다")

        # 조립 규칙이 한 자리(build_creation_stats)에만 있다 — 룰북에 선언되지
        # 않은 축을 가리키면 InvalidResourceAxis가 그대로 위로 올라간다.
        stats = build_creation_stats(axis_value_map, rulebook.resource_axes)

        entity = Entity(
            entity_id=command.character_id,
            display_name=display_name,
            rulebook_id=command.rulebook_id,
            stats=stats,
        )
        # 조립한 Entity가 룰북 선언과 어긋나면 EntityAxisMismatch가 그대로
        # 위로 올라간다(D-01) — 여기서 삼키지 않는다.
        validate_entity_axes(entity, rulebook)

        stats_payload = [
            {
                "name": stat.name,
                "form": stat.form,
                "current": stat.current,
                "max": stat.max,
                "depleted_effect_ref": stat.depleted_effect_ref,
                "slot_values": list(stat.slot_values) if stat.slot_values is not None else None,
                "tags": list(stat.tags) if stat.tags is not None else None,
                "none_kind": stat.none_kind,
            }
            for stat in entity.stats
        ]
        return (
            "character_created",
            None,
            {
                "character_id": command.character_id,
                "browser_id": command.browser_id,
                "display_name": display_name,
                "rulebook_id": command.rulebook_id,
                "one_line_intro": command.one_line_intro,
                "stats": stats_payload,
            },
        )

    def _prepare_lock_roster(self, command: LockPartyRoster) -> tuple[str, int | None, dict]:
        """파티 명단을 잠근다(D-08) — 빈 명단은 잠글 수 없고, 이미 잠긴
        세션에서 다시 부르면 `RosterAlreadyLocked`다.

        **D-10 — 동의 표시 없이 잠글 수 없다(Phase 12.1-04).** 완성된
        캐릭터 전원이 `self.state.creation_consents`(판 11부터 사건에서
        다시 접은 값, Phase 12.3 — 예전에는 액터 메모리의 동의 집계였다)에
        동의로 올라 있어야 한다. 이 검사는 `_maybe_auto_advance`가 전원
        동의 순간 이 명령을 재귀 호출할 때도 자연히 통과한다(그 호출은
        정의상 전원 동의가 갓 접힌 뒤에 일어난다) — 이 명령을 **직접**
        부르는 경로(라우터 우회 포함)를 막는 것이 이 검사의 목적이다.

        **CR-02 (12.1-REVIEW.md) — 아직 한창 만드는 중인 사람이 있으면
        잠글 수 없다.** `_maybe_auto_advance`가 `_all_created_characters_consented()`를
        거쳐 이 명령을 재귀 호출할 때는 이제 그 함수 안에서 이미
        `_unfinished_creation_candidates()`를 확인한다(위 함수 참조) —
        하지만 이 검사를 여기 **다시** 두는 이유는 바로 위 문단과 같다:
        이 명령을 라우터 우회 등으로 **직접** 부르는 경로는 그 재귀 호출
        경로를 거치지 않으므로, 이 함수 자신도 독립적으로 막아야 한다.
        """
        if self.state.party_roster is not None:
            raise RosterAlreadyLocked("파티 명단이 이미 잠겼다")
        if not command.character_ids:
            raise CommandRejected(
                "명단이 비어 있으면 잠글 수 없다 — 빈 명단 잠금은 「아직 아무도 안"
                " 만들었다」와 구분되지 않는다"
            )
        for character_id in command.character_ids:
            if character_id not in self.state.created_characters:
                raise CommandRejected(
                    f"만들어지지 않은 캐릭터는 명단에 넣을 수 없다: {character_id!r}"
                )
        if not all(
            self.state.creation_consents.get(character_id, False)
            for character_id in self.state.created_characters
        ):
            raise CommandRejected(
                "동의 표시 없이 파티 명단을 잠글 수 없다 — 완성된 전원이 동의해야"
                " 한다(D-10)"
            )
        unfinished = self._unfinished_creation_candidates()
        if unfinished:
            raise CommandRejected(
                "아직 한창 만드는 중인 사람이 있어 파티 명단을 잠글 수 없다"
                f"(CR-02): {unfinished!r}"
            )
        if self.state.reopened_creation_steps:
            # G-12.3-22 — 「고칠 게 있어요」로 다시 연 항목이 아직 안
            # 채워진 채로 잠그면, 고치는 중이던 값 대신 **옛 값으로** 판이
            # 시작된다. 화면도 이 상태에서 「이대로 시작」을 안 그리지만
            # (`consentGate`), 이 명령을 직접 부르는 경로는 그 화면을
            # 안 지나므로 여기서도 막는다 — 위 CR-02 검사와 같은 이유다.
            still_open = sorted(
                f"{character_id}:{step_id}"
                for character_id, step_id in self.state.reopened_creation_steps
            )
            raise CommandRejected(
                "아직 다시 채우지 않은 항목이 있어 파티 명단을 잠글 수 없다"
                f": {still_open!r}"
            )
        shortfall = self._party_size_shortfall()
        if shortfall:
            raise CommandRejected(
                f"이번 판은 {self.state.party_size_fixed}명인데 아직"
                f" {len(self.state.created_characters)}명만 캐릭터를 끝냈다 —"
                f" {shortfall}명이 더 끝내야 시작할 수 있다"
            )
        return (
            "party_roster_locked",
            None,
            {
                "character_ids": list(command.character_ids),
                "player_character_count": len(command.character_ids),
            },
        )

    def _prepare_interjection(self, command: RecordInterjection) -> tuple[str, int | None, dict]:
        """끼어든 말 하나를 사건으로 남긴다(D-09) — 검증 순서가 중요하다.

        ①본문이 비었으면 거절 ②명단이 잠겼으면 `RosterAlreadyLocked`
        ③`during_character_id`
        자신이 이 세션에 실재하는 `character_id`인지 확인한다(WR-01,
        12.1-REVIEW.md) ⑤언급 대상이 전부 이 세션에 존재하는 `character_id`인지
        확인한다 — 없는 사람을 가리키는 기록을 남기면 Phase 14가 그 색인을
        못 푼다.

        **G-12.3-13 (12.3-UAT.md) — 자기 차례에 하는 말을 더 이상 막지
        않는다.** 예전에는 화자가 지금 차례인 사람과 같으면 거절하며
        "자기 차례에는 끼어드는 것이 아니라 말하는 것이다"라고 냈다. 그
        규칙은 「자기 차례에 하는 말은 전부 만들기 항목으로 낸다」를
        전제했는데, **GM의 되물음이 그 전제를 깬다** — 되물음이 왔을 때는
        항목이 이미 전부 차 있어서 어떤 항목으로도 답할 수 없다. 실제
        시험(2026-08-23)에서 사람이 답을 적을 때마다 이 문구가 화면에
        떴고, 되물음에 답할 길이 아예 없었다.

        `speaker_character_id == during_character_id`는 이제 「자기 차례에
        말했다」는 뜻이다 — 오류가 아니다. 이 값을 읽는 곳(대화록·Phase 14
        관계 장부)에 자기 자신이 들어가도 가리키는 대상이 실재하므로
        WR-01이 막으려던 종류의 문제가 아니다.

        **WR-01 (12.1-REVIEW.md):** 예전에는 `mentioned_character_ids`만
        `known_character_ids`와 대조하고 `during_character_id`(누구의
        차례에 끼어들었는가) 자신은 전혀 대조하지 않았다 — 존재하지 않는
        `during_character_id`로도 사건이 그대로 기록되어 Phase 14(관계
        장부)가 가리키는 대상이 없는 색인을 만났다. 같은 `known_character_ids`
        집합, 같은 「닫힌 목록 밖은 거절」 방식으로 `during_character_id`도
        대조한다 — 이 파일이 이미 `mentioned_character_ids`에 쓰는 검증
        모양을 그대로 옮긴 것이지 새 방식을 만들지 않는다.

        **이 명령은 어떤 캐릭터의 값도 바꾸지 않는다** — `RecordInterjection`
        도크스트링이 그 근거(CHAR-04가 관계 칸을 금지하고 D-07이 지난
        차례를 잠근다)를 적는다.
        """
        if not command.text.strip():
            raise CommandRejected("text는 비어 있을 수 없다")
        if self.state.party_roster is not None:
            raise RosterAlreadyLocked("파티 명단이 이미 잠겨 끼어들 수 없다")

        known_character_ids = set(self.state.created_characters) | {
            character_id for character_id, _step_id in self.state.creation_step_values
        }
        if command.during_character_id not in known_character_ids:
            raise CommandRejected(
                f"이 세션에 없는 캐릭터의 차례를 가리켰다: {command.during_character_id!r}"
            )
        unknown_mentions = [
            character_id
            for character_id in command.mentioned_character_ids
            if character_id not in known_character_ids
        ]
        if unknown_mentions:
            raise CommandRejected(
                f"이 세션에 없는 캐릭터를 언급했다: {unknown_mentions!r}"
            )

        return (
            "creation_interjection",
            None,
            {
                "speaker_character_id": command.speaker_character_id,
                "browser_id": command.browser_id,
                "during_character_id": command.during_character_id,
                "mentioned_character_ids": list(command.mentioned_character_ids),
                "text": command.text,
            },
        )

    def _prepare_gm_spoke(self, command: RecordGmSpoke) -> tuple[str, int | None, dict]:
        """GM이 한 말 한 줄을 사건으로 남긴다(D-02, 판 11).

        호출부(`routes_creation.py::_gm_dedupe_key` 조회)가 AI를 부르기
        **전에** 먼저 「이미 같은 dedupe_key로 말했는가」를 본다 — 하지만
        그 조회는 단일 소비자 큐 밖의 일반 속성 읽기라 두 요청이 겹치면
        (두 탭, 재시도) 둘 다 조회를 통과해 둘 다 여기까지 온다. **그래서
        이 메서드가 큐 안에서 같은 검사를 다시 한다** — `_prepare_confirm`
        의 `AlreadyConfirmed`/`_prepare_resolve_check`의 `AlreadyResolved`/
        `_prepare_record_resource_change`의 `AlreadyChanged`와 같은 자리
        (12.3-REVIEW.md CR-04, D-12). 이 단락이 없으면 겹친 두 요청이
        `creation_gm_spoke`를 두 번 append한다 — 리듀서가 `dedupe_key`로
        덮어써 `creation_gm_said`엔 하나만 남지만 `events` 테이블엔 둘 다
        남고, 그보다 먼저 AI 제공자가 실제로 두 번 불린 뒤다(D-12 위반).
        `RecordInterjection`처럼 명단 잠금 여부는 검사하지 않는다 — GM의
        안내·지목·되묻기·정리는 명단이 잠기기 **전**에만 호출되는 경로이고
        (라우트가 이미 `party_roster is not None`을 409로 막는다), 이
        명령 자신이 그 경계를 다시 검사할 이유가 없다.
        """
        prior = self.state.creation_gm_said.get(command.dedupe_key)
        if prior is not None:
            raise AlreadyGmSpoken(prior)
        if not command.say.strip():
            raise CommandRejected("say는 비어 있을 수 없다")
        return (
            "creation_gm_spoke",
            None,
            {
                "kind": command.kind,
                "say": command.say,
                "target_character_id": command.target_character_id,
                "dedupe_key": command.dedupe_key,
            },
        )

    def _prepare_claim_gm_slot(self, command: ClaimGmSlot) -> tuple[str, int | None, dict]:
        """슬롯 하나를 잡는다(D-02/D-03, Phase 13) — 이미 다른 요청이
        같은 `slot_key`를 잡고 있으면 `GmSlotBusy`, 아니면 집합에 넣고
        `GmSlotClaimed`를 던진다(사건을 안 남긴다, `ClaimGmSlot` 도크스트링
        참조). 이 메서드는 단일 소비자 큐 안에서만 불리므로 집합을 직접
        건드려도 경합이 없다."""
        if command.slot_key in self._gm_slots_in_flight:
            raise GmSlotBusy(f"이미 다른 요청이 슬롯을 잡고 있다: {command.slot_key!r}")
        self._gm_slots_in_flight.add(command.slot_key)
        raise GmSlotClaimed("슬롯을 잡았다")

    def _prepare_release_gm_slot(self, command: ReleaseGmSlot) -> tuple[str, int | None, dict]:
        """`ClaimGmSlot`으로 잡은 슬롯을 돌려준다(D-03, Phase 13) — 없던
        키를 지워도 조용히 성공한다(`ReleaseGmSlot` 도크스트링 참조,
        호출부의 `finally`가 두 번 불릴 수 있다). `discard`는 없는 원소를
        지워도 예외를 던지지 않는다."""
        self._gm_slots_in_flight.discard(command.slot_key)
        raise GmSlotReleased("슬롯을 돌려줬다")

    def _prepare_open_scene(self, command: OpenScene) -> tuple[str, int | None, dict]:
        """판정 없이 장면을 연다(D-01/D-06, SCENE-01, Phase 13).

        검증 순서:
        ① 파티 명단이 아직 안 잠겼으면 거부한다(D-01의 경계 — 「첫
           사람이 완성한 순간」이 아니다. 라우트만 보면 서버 재시작·직접
           호출을 못 막으므로 액터가 다시 지킨다, `_prepare_confirm`의
           소유권 검사와 같은 이유).
        ② 이미 오프닝이 열렸으면 `SceneAlreadyOpened`(슬롯이 막지 못하는
           갈래 — 「동시」가 아니라 「이미 끝남」을 막는다).
        ③ 빈 문자열이나 공백뿐인 오프닝은 절대 기록되지 않는다
           (SCENE-02 empty).
        """
        if self.state.party_roster is None:
            raise CommandRejected("파티 명단이 아직 안 잠겨 장면을 열 수 없다")
        if self.state.scene_opened_seq is not None:
            raise SceneAlreadyOpened(self.state.scene_opened_seq)
        if not command.text.strip():
            raise CommandRejected("오프닝 text는 비어 있을 수 없다")
        return (
            "scene_opened",
            None,
            {
                "scenario_id": command.scenario_id,
                "text": command.text,
                "source": command.source,
            },
        )

    def _prepare_claim_host(self, command: ClaimCreationHost) -> tuple[str, int | None, dict]:
        """방장을 잡거나 승계한다(D-11, 판 11).

        검증 순서(`ClaimCreationHost` 도크스트링이 점유와 왜 다른지 적는다):

        ① 명단이 잠긴 뒤에는 방장 개념이 쓸모없다.
        ② `previous_browser_id is None`(첫 선점)인데 이미 방장이 있으면
           거절 — 두 브라우저가 동시에 첫 선점을 시도해도 하나만
           통과한다(단일 소비자 큐가 순서를 매긴다).
        ③ `previous_browser_id`가 있는데(승계 시도) 지금 방장과 다르면
           거절 — **비교 후 교체다.** 둘이 동시에 같은 방장의 승계를
           시도하면(같은 `previous_browser_id`) 먼저 처리된 쪽만
           통과하고, 나중 것은 이 시점에 이미 방장이 바뀌어 있어
           거절된다 — 방장이 한 번에 한 번만 바뀐다.

        누구를 이어받는지는 이 메서드가 스스로 정하지 않는다 — 호출부
        (`routes_creation.py`)가 유휴 판정을 하고 `previous_browser_id`에
        지금 방장을 실어 보낸다. 브라우저는 자기 `browser_id` 하나만
        고를 수 있다.
        """
        if self.state.party_roster is not None:
            raise RosterAlreadyLocked("파티 명단이 이미 잠겨 방장 개념이 더 이상 쓸모없다")
        current = self.state.creation_host_browser_id
        if command.previous_browser_id is None:
            if current is not None:
                raise CommandRejected("방장이 이미 있다")
            reason = "first"
        else:
            if current != command.previous_browser_id:
                raise CommandRejected("방장이 이미 바뀌었다 — 다시 시도해야 한다")
            reason = "succession"
        return (
            "creation_host_claimed",
            None,
            {
                "browser_id": command.browser_id,
                "reason": reason,
                "previous_browser_id": command.previous_browser_id,
            },
        )


class SessionRegistry:
    """세션 식별자당 액터를 하나만 보관한다 (D-09① 첫 겹).

    같은 식별자로 두 번 요청하면 새로 만들지 않고 이미 살아 있는 액터를 돌려준다.
    두 번째 겹(순번 유일성 제약, 프로세스 경계를 넘어서도 유효)은 `EventStore`가 진다.
    """

    def __init__(
        self,
        store: EventStore,
        roller_factory: Callable[[], Roller] | None = None,
        *,
        clock_id: str = "threat",
        clock_segment_count: int = THREAT_CLOCK_SEGMENT_COUNT,
        report_dir: Path | None = None,
    ) -> None:
        self._store = store
        self._roller_factory: Callable[[], Roller] = roller_factory or LiveRoller
        self._actors: dict[str, SessionActor] = {}
        self._clock_id = clock_id
        self._clock_segment_count = clock_segment_count
        self._report_dir = report_dir

    def get_or_create(self, session_id: str) -> SessionActor:
        actor = self._actors.get(session_id)
        if actor is None:
            actor = SessionActor(
                self._store,
                session_id,
                self._roller_factory(),
                clock_id=self._clock_id,
                clock_segment_count=self._clock_segment_count,
                report_dir=self._report_dir,
            )
            actor.start()
            self._actors[session_id] = actor
        return actor

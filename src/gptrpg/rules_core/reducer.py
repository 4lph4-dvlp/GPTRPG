"""사건 하나 + 이전 상태 → 새 상태, 그리고 전체 접기.

규칙 코어는 event_log를 모르므로 pydantic 사건 객체가 아니라
(event_type: str, payload: Mapping) 짝을 받는다 — 두 층을 이어 붙이는
일은 session_actor가 한다.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace

from gptrpg.rules_core.entities import Entity, StatEntry
from gptrpg.rules_core.grading import Grade
from gptrpg.rules_core.resource_change import ResourceOp


@dataclass(frozen=True)
class ConfirmedDeclareRecord:
    """선언 하나가 확인된 뒤의 상태 — 재확인이 왔을 때 무엇을 대조하고
    무엇을 재사용해야 하는지가 이 네 칸에 다 있다 (D-10, Phase 8 Plan 3).

    `resolve_seq`가 `None`이면 확인은 됐는데 판정이 아직 없다는 뜻이다 —
    확인 사건과 판정 사건 사이에 서버가 죽으면 이 상태로 남는다. 이때는
    재확인이 와도 캐시된 판정이 없으므로 `ResolveCheck`를 평소대로 다시
    제출한다."""

    confirm_seq: int
    resolve_seq: int | None
    move: str
    stat: str


@dataclass(frozen=True)
class CreationStepFold:
    """만들기 항목 하나(`(character_id, step_id)`)가 확정한 값 — 접힌 결과
    (판 9+, Phase 12.1, D-03/D-07). `ConfirmedDeclareRecord`와 같은 자리·
    같은 형식이다.

    같은 키로 두 번째 `creation_step_completed` 사건이 오면 이 레코드는
    통째로 새 값으로 **덮인다** — 앞선 사건은 기록에서 지워지지 않지만
    (append-only), 접은 결과에서는 나중 것만 남는다(D-07 되돌리기).

    `browser_id`는 이 사건을 실제로 제출한 브라우저다(하이재킹 항목,
    12.1-REVIEW.md CR-01 "추가로" 절). `SessionActor._prepare_create_character`가
    이 칸으로 「항목을 채운 브라우저가 완성도 낸 브라우저인가」를 대조한다
    — 완성 전에는 쿠키가 없을 수 있으므로(D22 흐름) 쿠키 대신 사건에서
    다시 접은 이 값이 유일하게 서버 재시작에도 살아남는 신원 근거다.
    """

    seq: int
    kind: str
    text_value: str | None
    picked: tuple[str, ...] | None
    axis_values: tuple[tuple[str, int], ...] | None
    rolls: tuple[int, ...] | None
    browser_id: str


@dataclass(frozen=True)
class CreationGmLineFold:
    """GM이 만들기 중에 한 말 한 줄 — 접힌 결과(판 11+, Phase 12.3, D-02).
    `CreationStepFold`와 같은 자리·같은 형식이다.

    같은 `dedupe_key`로 두 번째 `creation_gm_spoke` 사건이 오면 이
    레코드는 통째로 새 값으로 덮인다(D-12 「이미 말했나」를 서버가
    여기서 본다) — 실제로는 서버가 같은 키를 다시 내지 않으므로
    (`_gm_dedupe_key` 조회가 AI 호출 앞에 온다) 이 자리가 두 번
    덮이는 일은 정상 흐름에서 일어나지 않는다.
    """

    seq: int
    kind: str
    say: str
    target_character_id: str | None


@dataclass(frozen=True)
class GameState:
    """사건 기록을 처음부터 훑어 만드는 현재 상태.

    `failure_count`와 `fails_since_clock`은 둘 다 판정 실패를 세지만 서로
    다른 값이고, 둘 다 남아야 한다. `failure_count`는 **절대 초기화되지
    않는** 누적값이다 — 세션 전체에서 실패가 몇 번 났는지를 세고, MEAS-03의
    「판정 실패 대비 시계 진행」 비율의 분자로 쓰인다. `fails_since_clock`은
    화면에 보이는 「다음 강제 진행까지 얼마나 남았나」이고, `clock_advanced`
    사건이 접힐 때마다(어떤 `trigger`로 돌았든) 0으로 돌아간다(RIG-04).

    누적값을 화면에 쓰면 카운터가 세션 내내 올라가기만 해서 "실패 3회에
    초기화"라는 RIG-04 문장이 성립하지 않는다. 반대로 초기화되는 값을
    MEAS-03의 비율에 쓰면 "실패는 많은데 시계가 안 돌았다"라는 관측이
    구조적으로 불가능해진다 — 초기화된 순간 분자도 함께 사라지기 때문이다.
    그래서 두 칸을 분리해서 둔다.

    **토큰은 세 칸으로 나눠서 센다.** `total_tokens`(입력+출력 합계) 하나만
    있으면 원가를 계산할 수 없다 — 입력과 출력의 단가가 보통 4~5배 다르므로
    합계에 단가 하나를 곱하는 계산이 성립하지 않는다. H5(원가)가 프로젝트를
    멈출 수 있는 조건이라 이 구분은 편의가 아니라 요구사항이다.
    `cached_prompt_tokens`는 `prompt_tokens`의 부분집합이고(합계가 아니다)
    캐시 읽기 단가를 따로 곱할 몫이다. `total_tokens`는 기존 화면·집계 호출부가
    쓰던 이름이라 그대로 남기되, `prompt_tokens + completion_tokens`의 파생값일
    뿐이다.
    """

    session_id: str
    last_seq: int = -1
    turn_count: int = 0
    check_count: int = 0
    failure_count: int = 0
    fails_since_clock: int = 0
    clock_segment: int = 0
    clock_advances: int = 0
    narration_count: int = 0
    ai_calls: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_prompt_tokens: int = 0
    last_grade: Grade | None = None
    declare_owners: dict[int, str] = field(default_factory=dict)
    """선언 순번 -> 그 선언을 낸 character_id (판 5+, TRUST-03). `apply_event`가
    `action_declared`를 접을 때만 채운다 — 판 5 미만 기록은 이 칸의 소스인
    `character_id`가 아예 없었으므로 순번이 이 표에 들어오지 않는다("모른다"가
    "빈 문자열이다"와 섞이지 않는다, D-13). `SessionActor._prepare_confirm`이
    서버 재시작 뒤에도 이 표에서 소유권을 판정한다 — 액터의 메모리 상태가
    아니라 사건에서 다시 접어 만든 값이라 재시작에도 살아남는다."""
    occupied_by: dict[str, str] = field(default_factory=dict)
    """character_id -> browser_id (판 5+, D-05/D-06). `character_occupied`
    사건에서만 채워진다 — 점유를 요청하는 명령 자체는 08-02가 만든다. 이
    단계는 사건 종류와 이 파생 칸만 열어 둔다."""
    confirmed_declares: dict[int, ConfirmedDeclareRecord] = field(default_factory=dict)
    """선언 순번(declare_seq) -> 그 선언이 확인된 뒤의 기록 (D-10, TRUST-05).
    `player_confirmed=True`인 `action_confirmed`만 채운다 — 거부는 주사위를
    하나도 굴리지 않았으므로 그 선언을 잠글 이유가 없다. `SessionActor.
    _prepare_confirm`이 서버 재시작 뒤에도 이 표에서 멱등 단락을 판정한다."""
    confirm_to_declare: dict[int, int] = field(default_factory=dict)
    """확인 순번(confirm_seq) -> 그 확인이 붙은 선언 순번(declare_seq). `check_resolved`
    사건은 자기 `caused_by_seq`로 **확인** 사건을 가리키고 선언 사건을 직접
    가리키지 않는다 — 이 되짚는 표가 없으면 판정을 어느 선언에 붙여야
    하는지 알 수 없고, 매번 사건 전체를 다시 훑게 된다."""
    declare_no_check: dict[int, bool] = field(default_factory=dict)
    """선언 순번(declare_seq) -> 그 선언이 실제로 `no_check`로 분류됐는지
    (판 7+, 11-06 rework, T-11-29). `action_classified` 사건에서만 채워진다.
    `SessionActor._prepare_verify_proceed_eligibility`가 서버 재시작 뒤에도
    이 표에서 판단한다 — `declare_owners`와 같은 이유로 사건에서 다시 접은
    값이라 재시작에도 살아남는다.

    **`declare_owners`와 다른 「모르면 어떻게 하나」 규칙:** `declare_owners`는
    소유자를 모르면 통과시킨다(캐릭터 개념이 없던 호출부의 정당한 「모른다」).
    이 표는 반대다 — `declare_seq`가 이 표에 없으면 **거부**로 읽는다(아래
    소비부는 `.get(declare_seq, False)`를 쓴다). 이 표에 없다는 것은 "이
    선언이 실제로 `no_check`로 분류됐다는 증거가 없다"는 뜻이고, 그것을
    통과시키면 이 표가 막으려는 구멍(판정이 필요한 선언을 판정 없이 진행)이
    다시 열린다."""
    character_resource_ops: dict[tuple[str, str], tuple[ResourceOp, ...]] = field(
        default_factory=dict
    )
    """(character_id, axis 이름) -> 그 축에 적용된 연산 이력 튜플(판 8+,
    D-05/D-65/RULE-09). `resource_changed` 사건에서만 채워진다 — 이 표 +
    캐릭터 시작값(만들기 완료 사건이 기록한 `Entity`, `rules_core` 밖)을
    `resource_change.resolve_character_stats`에 넘긴 결과가 「지금 값」이다
    (RULE-06). 사건 순번 순서를 보존한 튜플이라 접는 순서를 바꾸면 결과가
    달라질 수 있는 연산에서도 순서가 기록 순서와 같다(RULE-09 ordering)."""
    resource_change_by_cause: dict[int, int] = field(default_factory=dict)
    """caused_by_seq(그 자원 변화를 일으킨 판정 사건의 순번) -> 그
    `resource_changed` 사건 자신의 순번(판 8+, Phase 8 멱등성 창 재사용).
    `SessionActor._prepare_record_resource_change`가 이 표로 재시도를
    단락시킨다 — 같은 원인 사건으로 두 번 제출해도 자원이 두 번 깎이지
    않는다."""
    party_size_fixed: int | None = None
    """이 세션의 확정 인원(판 9+, D-01, Phase 12.1). `party_size_fixed`
    사건에서만 채워진다. `None`은 「아직 인원이 확정되지 않았다」다 —
    사건에서 다시 접은 값이라 서버 재시작에도 살아남는다."""
    creation_step_values: dict[tuple[str, str], CreationStepFold] = field(
        default_factory=dict
    )
    """(character_id, step_id) -> 그 항목이 확정한 값(판 9+, D-03/D-07).
    `creation_step_completed` 사건에서만 채워진다. 같은 키로 다시 오면
    나중 값으로 덮인다 — 앞선 사건은 기록에 남지만 접은 결과는 나중 것만
    반영한다. 액터 메모리가 아니라 사건에서 다시 접은 값이라 만들기 도중
    서버가 재시작해도 그대로 복원된다(D-11 부분 재진행의 전제)."""
    created_characters: dict[str, Entity] = field(default_factory=dict)
    """character_id -> 완성된 `Entity`(판 9+, D-03/CHAR-04). `character_created`
    사건에서만 채워진다 — 만들기 산출물이 지금 `Entity`/`StatEntry` 그릇에
    그대로 들어간다는 CHAR-04의 무변경이 이 칸에서 성립한다.
    `_prepare_occupy`의 옛 세션 판별(판 9부터는 이 칸도 함께 본다)이 이
    칸에 의존한다."""
    party_roster: tuple[str, ...] | None = None
    """잠긴 파티 명단(판 9+, D-08). `party_roster_locked` 사건에서만
    채워진다. **`None`과 빈 튜플의 뜻이 다르다** — `None`은 「아직 안
    잠겼다」이고, 빈 튜플은 나오지 않는다(잠금 명령이 빈 명단을 거절한다,
    `LockPartyRoster`). 한 번 채워지면 다시 `None`으로 돌아가지 않는다 —
    푸는 사건이 없다(D-08)."""
    creation_gm_said: dict[str, CreationGmLineFold] = field(default_factory=dict)
    """dedupe_key -> 그 시점 GM이 한 말(판 11+, Phase 12.3, D-02/D-12).
    `creation_gm_spoke` 사건에서만 채워진다. 같은 키로 다시 오면 나중
    것이 이긴다 — D-12의 「이미 말했나」를 서버가 여기서 본다. 액터
    메모리가 아니라 사건에서 다시 접은 값이라 서버 재시작에도 그대로
    복원된다."""
    creation_consents: dict[str, bool] = field(default_factory=dict)
    """character_id -> 동의 여부(판 11+, Phase 12.3, D-03). `creation_consent_recorded`
    사건에서만 채워진다. 지금 액터 메모리 `_creation_consents`가 하던
    일을 사건에서 다시 접은 값으로 옮긴 것이라 서버 재시작에도 살아남고,
    화면이 「누가 아직 안 눌렀는지」를 이름까지 보여줄 수 있다."""
    reopened_creation_steps: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    """다시 열린 `(character_id, step_id)` 집합(판 11+, Phase 12.3,
    D-11 부분 재진행). `creation_consent_recorded` 사건이 `agree=False`로
    올 때만 채워진다. 지금 액터 메모리 `_reopened_creation_steps`가 하던
    일을 사건에서 다시 접은 값으로 옮긴 것이다."""
    creation_host_browser_id: str | None = None
    """이 세션의 방장(판 11+, Phase 12.3, D-11). `creation_host_claimed`
    사건에서만 채워진다. `None`은 「아직 아무도 방장을 안 잡았다」다."""
    creation_rulebook_id: str | None = None
    """이 세션이 어느 룰북으로 캐릭터를 만드는가(판 11+, Phase 12.3).
    새 사건 칸이 아니라 기존 `party_size_fixed` 사건의 `rulebook_id`
    칸에서 채운다 — 인원 확정과 룰북 선택이 같은 사건에서 함께
    일어나므로 새 사건을 만들 이유가 없다. `None`은 「아직 인원이 확정
    안 됐다」다."""


def initial_state(session_id: str) -> GameState:
    """사건이 하나도 없는 세션의 시작 상태."""
    return GameState(session_id=session_id)


class UnknownEventType(Exception):
    """apply_event가 모르는 event_type을 받았을 때 발생한다.

    조용히 last_seq만 갱신하고 넘어가는 경로를 두면, 사건 종류를 하나
    추가하고 리듀서를 안 고쳐도 아무 일도 일어나지 않아 버그가 숨는다.
    거부는 반드시 예외로 드러나야 한다.
    """

    def __init__(self, event_type: str) -> None:
        super().__init__(f"모르는 사건 종류: {event_type!r}")
        self.event_type = event_type


class OutOfOrderEvent(Exception):
    """`fold`가 순번이 어긋난 사건을 만났을 때 던진다(QUAL-01, 12-02 Task 3).

    지금은 `EventStore.read_events`가 `ORDER BY seq`로 항상 정렬해서
    넘겨주기 때문에 **우연히** 이 문제가 안 생긴다(REQUIREMENTS.md 원문
    문장) — `fold`는 스스로는 순서를 검사하지 않았다. 이 예외는 `UnknownEventType`과
    같은 모양(사유를 문구에, 값을 속성에 노출)이다.
    """

    def __init__(self, expected_after: int, got: int) -> None:
        super().__init__(
            f"사건 순번이 어긋났다: last_seq={expected_after} 다음에 seq={got}가 왔다"
        )
        self.expected_after = expected_after
        self.got = got


def _legacy_v1_counts_as_failure(grade: str) -> bool:
    """판 1 기록에는 `counts_as_failure` 칸이 없다. 그때는 룰북이 하나뿐이었으므로
    등급 이름이 곧 실패 여부였다 — 이것은 규칙이 아니라 이미 쓰인 기록에 대한
    사실이다(D-12 옛 판 해석 경로). 판 1 기록을 손대지 않기 위해, 판 2 코드가
    옛 기록을 읽을 때만 이 함수를 거친다.
    """
    return grade == "miss"


def apply_event(state: GameState, event_type: str, payload: Mapping) -> GameState:
    """사건 하나를 이전 상태에 접어 새 상태를 돌려준다.

    열아홉 종류를 전부 다룬다(판 9가 캐릭터 만들기 다섯 종류를, 판 11이
    만들기 화면 줄기 세 종류를 늘렸다). 모르는 종류가 오면
    UnknownEventType을 던진다 — 조용히 넘어가지 않는다.
    """
    seq = payload["seq"]
    if event_type == "action_declared":
        # 판 5부터 `character_id`가 늘었다(TRUST-03) — 판 5 미만 기록에는 이
        # 칸 자체가 없었으므로 `declare_owners`에 넣지 않는다("모른다"가
        # "빈 문자열이다"와 섞이지 않는다, D-13). 이 판 올리기와 이 갈래는
        # `EVENT_SCHEMA_VERSION` 4->5와 반드시 같은 커밋에 들어간다 — 빠뜨리면
        # 이 종류의 사건이 하나라도 있는 세션이 폴링마다 소유권 근거를 잃는다.
        schema_version = payload.get("schema_version", 1)
        character_id = payload.get("character_id") if schema_version >= 5 else None
        declare_owners = dict(state.declare_owners)
        if character_id is not None:
            declare_owners[seq] = character_id
        return replace(
            state,
            last_seq=seq,
            turn_count=state.turn_count + 1,
            declare_owners=declare_owners,
        )
    if event_type == "action_confirmed":
        # D-10/TRUST-05 — 확인(player_confirmed=True)만 접어 만든다. 거부는
        # 주사위를 하나도 굴리지 않았으므로 그 선언을 잠글 이유가 없다(TRUST-05가
        # 지키려는 것은 「굴림이 두 번」이지 「확인 사건이 두 개」가 아니다).
        # `caused_by_seq`가 없으면(=선언 없이 확인만 낸 옛 호출부·CLI) 대조할
        # 선언이 없으므로 역시 건너뛴다. 판 5 미만 기록에도 `move`·`stat`·
        # `player_confirmed`는 이미 있었으므로 schema_version 게이팅이
        # 필요 없다 — 멱등성 판정은 character_id에 의존하지 않는다.
        confirmed_declares = state.confirmed_declares
        confirm_to_declare = state.confirm_to_declare
        if payload.get("player_confirmed") and payload.get("caused_by_seq") is not None:
            declare_seq = payload["caused_by_seq"]
            confirmed_declares = dict(confirmed_declares)
            confirmed_declares[declare_seq] = ConfirmedDeclareRecord(
                confirm_seq=seq,
                resolve_seq=None,
                move=payload["move"],
                stat=payload["stat"],
            )
            confirm_to_declare = dict(confirm_to_declare)
            confirm_to_declare[seq] = declare_seq
        return replace(
            state,
            last_seq=seq,
            confirmed_declares=confirmed_declares,
            confirm_to_declare=confirm_to_declare,
        )
    if event_type == "check_resolved":
        grade = payload["grade"]
        schema_version = payload.get("schema_version", 1)
        if schema_version >= 2:
            counts_as_failure = payload["counts_as_failure"]
        else:
            counts_as_failure = _legacy_v1_counts_as_failure(grade)
        # D-10/TRUST-05 — 이 판정이 어느 선언의 확인 기록에 붙는지를
        # `confirm_to_declare`로 되짚어, 그 기록의 `resolve_seq`를 채운다.
        # 되짚을 확인이 없으면(=확인 없이 판정만 낸 옛 호출부·CLI) 그대로
        # 둔다 — 멱등 단락은 이 칸이 채워진 기록에만 적용된다.
        confirmed_declares = state.confirmed_declares
        declare_seq = state.confirm_to_declare.get(payload.get("caused_by_seq"))
        if declare_seq is not None and declare_seq in confirmed_declares:
            confirmed_declares = dict(confirmed_declares)
            confirmed_declares[declare_seq] = replace(
                confirmed_declares[declare_seq], resolve_seq=seq
            )
        return replace(
            state,
            last_seq=seq,
            check_count=state.check_count + 1,
            failure_count=state.failure_count + (1 if counts_as_failure else 0),
            fails_since_clock=state.fails_since_clock + (1 if counts_as_failure else 0),
            last_grade=grade,
            confirmed_declares=confirmed_declares,
        )
    if event_type == "narration_appended":
        return replace(state, last_seq=seq, narration_count=state.narration_count + 1)
    if event_type == "clock_advanced":
        # trigger 값(fail_counter/condition/ai_choice)과 무관하게 초기화한다 —
        # 어떤 이유로든 시계가 한 칸 갔으면 "다음 강제 진행까지" 세기는
        # 처음부터 다시 시작한다.
        return replace(
            state,
            last_seq=seq,
            clock_advances=state.clock_advances + 1,
            clock_segment=payload["segment_index"],
            fails_since_clock=0,
        )
    if event_type == "ai_invoked":
        prompt_tokens = payload["prompt_tokens"]
        completion_tokens = payload["completion_tokens"]
        # 판 3에서 늘어난 칸이다. 판 1·2로 쓰인 기록에는 이 칸이 없으므로
        # 0으로 읽는다 — 그때는 캐시 정보를 남기는 자리 자체가 없었다는
        # 뜻이고, 「캐시 적중이 0이었다」와 구분이 필요하면 그 기록의
        # `schema_version`을 보면 된다(D-12: 옛 기록을 고쳐 쓰지 않는다).
        cached_prompt_tokens = payload.get("cached_prompt_tokens", 0)
        return replace(
            state,
            last_seq=seq,
            ai_calls=state.ai_calls + 1,
            total_tokens=state.total_tokens + prompt_tokens + completion_tokens,
            prompt_tokens=state.prompt_tokens + prompt_tokens,
            completion_tokens=state.completion_tokens + completion_tokens,
            cached_prompt_tokens=state.cached_prompt_tokens + cached_prompt_tokens,
        )
    if event_type == "scene_illustrated":
        # 삽화는 게임 상태를 하나도 바꾸지 않는다 — 판정·실패 누적·시계 어디에도
        # 닿지 않고 `last_seq`만 따라 올린다. **그래도 분기가 있어야 한다:**
        # 이 분기가 없으면 삽화가 한 장 남은 세션은 폴링마다 `UnknownEventType`을
        # 맞고(폴링 경로가 사건 전체를 이 함수로 접는다) 화면이 통째로 죽는다.
        # 그림 기능을 끄면 낫는 종류의 고장이 아니다 — 이미 기록된 삽화 사건은
        # 사라지지 않으므로, 한 번 켰던 세션은 영구히 열리지 않게 된다.
        return replace(state, last_seq=seq)
    if event_type == "character_occupied":
        # 점유를 요청하는 명령 자체는 08-02가 만든다 — 이 갈래는 사건 종류만
        # 먼저 열어 둔다. **이 갈래를 빠뜨리면 점유 사건이 하나라도 있는
        # 세션은 폴링마다 UnknownEventType을 맞고 영구히 안 열린다**(141~148줄의
        # 삽화 갈래 주석이 같은 사고를 기록해 두었다).
        occupied_by = dict(state.occupied_by)
        occupied_by[payload["character_id"]] = payload["browser_id"]
        return replace(state, last_seq=seq, occupied_by=occupied_by)
    if event_type == "safety_flagged":
        # AI 출력 안전 장치 기록(판 6, Phase 10 SAFE-01/03/07)은 게임 상태를
        # 하나도 바꾸지 않는다 — 판정·실패 누적·시계 어디에도 닿지 않고
        # `last_seq`만 따라 올린다(`scene_illustrated` 분기와 같은 최소 모양).
        # **그래도 분기가 있어야 한다:** 이 분기가 없으면 안전 장치가 한 번이라도
        # 걸린 세션은 폴링마다 `UnknownEventType`을 맞고(폴링 경로가 사건 전체를
        # 이 함수로 접는다) 화면이 통째로 죽는다. 이 판 올리기(`EVENT_SCHEMA_VERSION`
        # 5->6)와 이 분기는 반드시 같은 커밋이다(08-CONTEXT.md D-06, 이미 두 번
        # 난 사고).
        return replace(state, last_seq=seq)
    if event_type == "action_classified":
        # 분류 결정 기록(판 7, 11-06 rework, T-11-29)은 게임 상태를 `declare_no_check`
        # 표 하나 말고는 바꾸지 않는다 — 판정·실패 누적·시계 어디에도 안 닿는다
        # (`scene_illustrated`/`safety_flagged` 분기와 같은 최소 모양 + 표 하나).
        # **그래도 분기가 있어야 한다:** 이 분기가 없으면 이 종류가 하나라도 있는
        # 세션이 폴링마다 UnknownEventType을 맞고 영구히 안 열린다(08-CONTEXT.md
        # D-06, 이미 여러 번 난 사고 — 이 판 올리기와 이 분기는 반드시 같은 커밋).
        declare_seq = payload.get("caused_by_seq")
        declare_no_check = state.declare_no_check
        if declare_seq is not None:
            declare_no_check = dict(declare_no_check)
            declare_no_check[declare_seq] = payload["no_check"]
        return replace(state, last_seq=seq, declare_no_check=declare_no_check)
    if event_type == "resource_changed":
        # 자원 변화 기록(판 8, Phase 12 D-05/D-65)은 「dict 복사 → 갱신 →
        # replace」 모양을 그대로 따른다(`character_occupied` 분기와 같은
        # 패턴). **그래도 분기가 있어야 한다:** 이 분기가 없으면 이 종류가
        # 하나라도 있는 세션이 폴링마다 UnknownEventType을 맞고 영구히 안
        # 열린다(08-CONTEXT.md D-06, 이미 여러 번 난 사고 — `scene_illustrated`
        # · `character_occupied` · `action_classified`에 이어 이번이 네 번째
        # 사례).
        character_id = payload["character_id"]
        character_resource_ops = dict(state.character_resource_ops)
        for change in payload["changes"]:
            key = (character_id, change["axis"])
            op = ResourceOp(
                axis=change["axis"],
                operation=change["operation"],
                amount=change["amount"],
                rolls=tuple(change.get("rolls", ())),
            )
            character_resource_ops[key] = character_resource_ops.get(key, ()) + (op,)
        resource_change_by_cause = state.resource_change_by_cause
        caused_by_seq = payload.get("caused_by_seq")
        if caused_by_seq is not None:
            resource_change_by_cause = dict(resource_change_by_cause)
            resource_change_by_cause[caused_by_seq] = seq
        return replace(
            state,
            last_seq=seq,
            character_resource_ops=character_resource_ops,
            resource_change_by_cause=resource_change_by_cause,
        )
    if event_type == "party_size_fixed":
        # 인원 확정 기록(판 9, Phase 12.1 D-01)은 `party_size_fixed` 한
        # 칸만 채운다. **그래도 분기가 있어야 한다:** 이 분기가 없으면 이
        # 종류가 하나라도 있는 세션이 폴링마다 UnknownEventType을 맞고
        # 영구히 안 열린다(08-CONTEXT.md D-06, 이미 여러 번 난 사고 —
        # `resource_changed`에 이어 이번이 다섯 번째 사례).
        # 판 11+(Phase 12.3)부터는 같은 사건에서 룰북 식별자도 함께
        # 접는다(creation_rulebook_id) — 새 사건 칸이 아니라 이미 있는
        # rulebook_id 칸을 두 번째 GameState 칸에 옮겨 적는 것뿐이다.
        return replace(
            state,
            last_seq=seq,
            party_size_fixed=payload["player_character_count"],
            creation_rulebook_id=payload["rulebook_id"],
        )
    if event_type == "creation_step_completed":
        # 만들기 항목 값 확정(판 9, D-03/D-07)은 (character_id, step_id)
        # 키로 **덮어쓴다** — 앞선 사건은 기록에서 지워지지 않고, 접은
        # 결과에서만 나중 것이 이긴다(D-07).
        key = (payload["character_id"], payload["step_id"])
        creation_step_values = dict(state.creation_step_values)
        axis_values_payload = payload.get("axis_values")
        picked_payload = payload.get("picked")
        rolls_payload = payload.get("rolls")
        creation_step_values[key] = CreationStepFold(
            seq=seq,
            kind=payload["kind"],
            text_value=payload.get("text_value"),
            picked=tuple(picked_payload) if picked_payload is not None else None,
            axis_values=(
                tuple((v["axis_name"], v["value"]) for v in axis_values_payload)
                if axis_values_payload is not None
                else None
            ),
            rolls=tuple(rolls_payload) if rolls_payload is not None else None,
            browser_id=payload["browser_id"],
        )
        return replace(state, last_seq=seq, creation_step_values=creation_step_values)
    if event_type == "creation_interjection":
        # 끼어든 말(판 9, D-09)은 어느 캐릭터의 구조화된 데이터도 바꾸지
        # 않는다 — `scene_illustrated`/`safety_flagged`와 같은 최소 모양
        # (last_seq만 갱신). **그래도 분기가 있어야 한다** — 없으면 이
        # 종류가 하나라도 있는 세션이 폴링마다 UnknownEventType을 맞고
        # 영구히 안 열린다.
        return replace(state, last_seq=seq)
    if event_type == "character_created":
        # 캐릭터 완성(판 9, D-03/CHAR-04) — 페이로드의 stats를
        # StatEntry(...)로 되살려 Entity(...)를 만든다. StatEntry의
        # __post_init__이 다시 돌아 형태 규약(D-13)이 접는 시점에도
        # 강제된다.
        stats = tuple(
            StatEntry(
                name=entry["name"],
                form=entry["form"],
                current=entry.get("current"),
                max=entry.get("max"),
                depleted_effect_ref=entry.get("depleted_effect_ref"),
                slot_values=(
                    tuple(entry["slot_values"]) if entry.get("slot_values") is not None else None
                ),
                tags=tuple(entry["tags"]) if entry.get("tags") is not None else None,
                none_kind=entry.get("none_kind"),
            )
            for entry in payload["stats"]
        )
        entity = Entity(
            entity_id=payload["character_id"],
            display_name=payload["display_name"],
            rulebook_id=payload["rulebook_id"],
            stats=stats,
        )
        created_characters = dict(state.created_characters)
        created_characters[payload["character_id"]] = entity
        return replace(state, last_seq=seq, created_characters=created_characters)
    if event_type == "party_roster_locked":
        # 명단 잠금(판 9, D-08) — party_roster가 None에서 튜플로 바뀐다.
        # 이 이후로는 이 칸이 다시 None으로 돌아가지 않는다(푸는 사건이
        # 없다).
        return replace(state, last_seq=seq, party_roster=tuple(payload["character_ids"]))
    if event_type == "creation_gm_spoke":
        # GM이 한 말 한 줄(판 11, D-02/D-12)은 dedupe_key로 덮어쓴다 —
        # creation_step_completed와 같은 「같은 키로 다시 오면 나중
        # 것이 이긴다」 방식이다.
        creation_gm_said = dict(state.creation_gm_said)
        creation_gm_said[payload["dedupe_key"]] = CreationGmLineFold(
            seq=seq,
            kind=payload["kind"],
            say=payload["say"],
            target_character_id=payload.get("target_character_id"),
        )
        return replace(state, last_seq=seq, creation_gm_said=creation_gm_said)
    if event_type == "creation_consent_recorded":
        # 동의 기록(판 11, D-03/D-11)은 두 갈래다 — agree=True는 그
        # 캐릭터의 동의를 켠다. agree=False는 지금 _process_reopen이
        # 액터 메모리에서 하는 두 동작과 정확히 같다: 모인 동의를
        # 전부 비우고, 다시 연 항목을 집합에 더한다.
        if payload["agree"]:
            creation_consents = dict(state.creation_consents)
            creation_consents[payload["character_id"]] = True
            return replace(state, last_seq=seq, creation_consents=creation_consents)
        reopened_creation_steps = state.reopened_creation_steps | {
            (payload["character_id"], payload["reopened_step_id"])
        }
        return replace(
            state,
            last_seq=seq,
            creation_consents={},
            reopened_creation_steps=reopened_creation_steps,
        )
    if event_type == "creation_host_claimed":
        # 방장 기록(판 11, D-11)은 한 칸만 덮어쓴다 — 처음 잡든
        # 승계든 최종 상태는 「지금 방장이 누구인가」 하나뿐이다.
        return replace(state, last_seq=seq, creation_host_browser_id=payload["browser_id"])
    raise UnknownEventType(event_type)


def fold(session_id: str, pairs: Iterable[tuple[str, Mapping]]) -> GameState:
    """사건 (event_type, payload) 짝들을 순서대로 접어 최종 상태를 만든다.

    중간 저장을 쓰지 않는다 — 언제나 initial_state에서 다시 시작한다 (D-08).

    **순번을 스스로 검사한다(QUAL-01, 12-02 Task 3).** 지금은
    `EventStore.read_events`가 `ORDER BY seq`로 항상 정렬해서 넘겨주기
    때문에 **우연히** 순서 문제가 안 생긴다(REQUIREMENTS.md 원문 문장) —
    이 함수는 그 우연에 기대지 않고 각 사건을 접기 **전에**
    `payload["seq"] <= state.last_seq`면 `OutOfOrderEvent`로 멈춘다.
    `initial_state`의 `last_seq`가 `-1`이므로 첫 사건의 순번 0은 정상으로
    통과한다. **사이가 빈 순번은 어긋남이 아니다** — 가시성 필터나 부분
    읽기로 건너뛴 사건이 있을 수 있고, `read_events`의 계약이 「순번
    순서대로」이지 「연속」이 아니다. 검사는 이 자리 한 곳에만 둔다(두
    자리에 두면 서로 다른 규칙으로 갈릴 수 있다 — `_band_matches`가 세운
    「한 헬퍼를 공유한다」 관례와 같은 이유) — `apply_event` 자체는
    건드리지 않는다.
    """
    state = initial_state(session_id)
    for event_type, payload in pairs:
        seq = payload["seq"]
        if seq <= state.last_seq:
            raise OutOfOrderEvent(expected_after=state.last_seq, got=seq)
        state = apply_event(state, event_type, payload)
    return state

"""사건 하나 + 이전 상태 → 새 상태, 그리고 전체 접기.

규칙 코어는 event_log를 모르므로 pydantic 사건 객체가 아니라
(event_type: str, payload: Mapping) 짝을 받는다 — 두 층을 이어 붙이는
일은 session_actor가 한다.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace

from gptrpg.rules_core.grading import Grade


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


def _legacy_v1_counts_as_failure(grade: str) -> bool:
    """판 1 기록에는 `counts_as_failure` 칸이 없다. 그때는 룰북이 하나뿐이었으므로
    등급 이름이 곧 실패 여부였다 — 이것은 규칙이 아니라 이미 쓰인 기록에 대한
    사실이다(D-12 옛 판 해석 경로). 판 1 기록을 손대지 않기 위해, 판 2 코드가
    옛 기록을 읽을 때만 이 함수를 거친다.
    """
    return grade == "miss"


def apply_event(state: GameState, event_type: str, payload: Mapping) -> GameState:
    """사건 하나를 이전 상태에 접어 새 상태를 돌려준다.

    여덟 종류를 전부 다룬다. 모르는 종류가 오면 UnknownEventType을 던진다 —
    조용히 넘어가지 않는다.
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
    raise UnknownEventType(event_type)


def fold(session_id: str, pairs: Iterable[tuple[str, Mapping]]) -> GameState:
    """사건 (event_type, payload) 짝들을 순서대로 접어 최종 상태를 만든다.

    중간 저장을 쓰지 않는다 — 언제나 initial_state에서 다시 시작한다 (D-08).
    """
    state = initial_state(session_id)
    for event_type, payload in pairs:
        state = apply_event(state, event_type, payload)
    return state

"""사건 봉투와 일곱 종류 사건의 모양. 빠진 필드·오타 필드를 거부한다.

event_log는 rules_core를 모른다 (경계 계약이 양방향으로 강제한다) — 그래서
등급 리터럴을 rules_core.grading에서 가져오지 않고 여기서 다시 선언한다.

**schema_version 규약(D-12):** 이미 쓴 기록은 손대지 않는다. 사건 모양이
실제로 바뀌면 이 모듈의 `EVENT_SCHEMA_VERSION`을 올리고, 읽는 쪽(재생·재구성
경로)에 옛 판을 해석하는 경로를 추가한다. 예전 기록을 고쳐 쓰는 방식은
재구성 자체를 믿을 수 없게 만든다 — Phase 5는 두 세션 사이가 1주이고 그
사이에 코드가 바뀔 수 있는데, Phase 6은 두 기록을 다 읽어야 한다.
"""

from datetime import UTC, datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

EVENT_SCHEMA_VERSION = 4
"""판 1 -> 판 2: `CheckResolved`에 `counts_as_failure` 필수 칸이 늘었다(D-12).
판 3 -> 판 4: 사건 종류가 하나 늘었다 — `SceneIllustrated`. 기존 여섯 종류의
칸은 하나도 바뀌지 않았으므로 판 1~3으로 쓰인 기록은 글자 그대로 다시 읽힌다
(늘어난 것이 「새 종류」일 뿐이어서, 옛 기록에는 그 종류의 사건이 없다).
반대 방향은 성립하지 않는다 — 판 4로 쓴 기록을 판 3 코드로 읽으면 새 종류에서
막힌다. 그래서 판을 올린다.

판 2 -> 판 3: `AiInvoked`에 `cached_prompt_tokens` 칸이 늘었다 — 캐시에서
읽어 온 입력 토큰 몫을 남기지 않으면 H5(원가)의 지배 변수인 캐싱 효과를
실측으로 검증할 수 없다(D19 "캐싱 없으면 3.7배").

**이미 쓰인 기록은 어느 판이든 손대지 않는다.** 판 3의 새 칸은 기본값 0이
있는 선택 칸이라, 판 1·2로 쓰인 기록도 그대로 다시 읽힌다 — 옛 기록에서는
「캐시 정보가 기록되지 않았다」와 「캐시 적중이 0이었다」가 구분되지 않으며,
그 구분이 필요한 자리는 `schema_version`을 보면 된다. `counts_as_failure`와
달리 필수 칸으로 만들지 않은 이유가 이것이다(필수로 만들면 옛 기록이 아예
파싱되지 않아 Phase 6이 두 세션 기록을 함께 읽을 수 없다)."""

Visibility = Literal["public"]

# rules_core.grading.Grade와 값은 같지만 별도로 선언한다 — 두 층은 서로를 모른다.
# str로 넓힌 이유: 등급 이름의 권위가 이제 룰북 선언에 있고(D32), 룰북마다
# 서로 다른 이름 집합을 쓸 수 있어야 하므로 고정 Literal로는 두 번째 룰북을
# 표현할 수 없다. 실제 이름 목록은 gptrpg.rulebooks 아래 각 룰북 선언에만 있다.
Grade = str


def utc_now_iso() -> str:
    """UTC 기준 ISO8601 문자열을 밀리초 자리까지 만들어 'Z'로 맺는다.

    저장 왕복에서 값이 변하지 않도록 형식을 여기서 한 번만 정한다.
    """
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


class EventEnvelope(BaseModel):
    """모든 사건이 공유하는 봉투 칸.

    extra="forbid"가 오타로 생긴 여분 칸을 거부하고, frozen=True가 만들어진
    사건 객체를 못 고치게 한다 (append-only 정신, D-12).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    seq: int
    schema_version: int
    visibility: Visibility = "public"
    caused_by_seq: int | None = None
    recorded_at: str


class ModifierRecord(BaseModel):
    """판정 사건 안에 남는 수정치 하나 — 유형·값·출처."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str
    value: int
    source: str


class ActionDeclared(EventEnvelope):
    """플레이어가 자유 문장으로 행동을 선언했다. 다듬거나 잘라 넣지 않는다."""

    event_type: Literal["action_declared"]
    player_id: str
    raw_text: str


class ActionConfirmed(EventEnvelope):
    """시스템이 제안한 무브·능력치를 플레이어가 확인(또는 거부)했다.

    `system_suggestion`과 `player_confirmed`, 그리고 `ActionDeclared.raw_text`가
    함께 있어야 나중에 정답 데이터가 된다. 신뢰도 숫자는 저장하지 않는다 —
    모든 분류가 어차피 사람 확인을 거치므로 게임의 진실이 아니다.
    """

    event_type: Literal["action_confirmed"]
    player_id: str
    move: str
    stat: str
    system_suggestion: dict[str, str]
    player_confirmed: bool


class CheckResolved(EventEnvelope):
    """판정 한 번 = 사건 하나 (D-17). 계산 과정 전체를 담는다 (D-16)."""

    event_type: Literal["check_resolved"]
    move: str
    rolls: list[int]
    modifiers: list[ModifierRecord]
    target: int
    grade: Grade
    counts_as_failure: bool


class NarrationAppended(EventEnvelope):
    """서사 문장 조각 하나. 한 번의 서사가 여러 사건으로 흘러나온다.

    `chunk_index`가 0인 사건의 시각이 "서사 첫 글자" 시점이다. 판정과 서사를
    굳이 나눈 이유는, 응답이 늦을 때 판정 결과를 먼저 내보내고 서사를 뒤이어
    붙이는 규칙이 있어 어차피 시점이 갈리기 때문이다.
    """

    event_type: Literal["narration_appended"]
    text: str
    chunk_index: int


class ClockAdvanced(EventEnvelope):
    """위협 시계가 한 칸 돌았다.

    `trigger`는 시계가 왜 돌았는지다 — 실패 누적 때문인지, 조건이 걸려서인지,
    진행자가 골라서인지. 이 세 값을 구분해 두어야 나중에 "실패는 많은데
    시계가 안 돈다"를 잡아낼 수 있다.
    """

    event_type: Literal["clock_advanced"]
    clock_id: str
    segment_index: int
    trigger: Literal["fail_counter", "condition", "ai_choice"]


class AiInvoked(EventEnvelope):
    """AI를 한 번 불렀다. 실제 호출 코드와 제공자 추상화 계층은 Phase 3이
    만든다 — 이 계획은 칸만 확정한다. 자리가 없으면 Phase 6에서 원가를
    계산할 수 없고, 원가는 프로젝트를 멈출 수 있는 조건이다.

    **입력·출력 토큰을 끝까지 나눠서 남긴다.** 두 값을 합쳐 하나로 세면
    원가를 계산할 수 없다 — 입력과 출력의 단가가 보통 4~5배 다르기 때문이다.
    `cached_prompt_tokens`는 `prompt_tokens`의 부분집합이고(합계가 아니다),
    캐시 정보를 주지 않는 제공자에서는 0이다.
    """

    event_type: Literal["ai_invoked"]
    agent_role: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    cached_prompt_tokens: int = 0


class SceneIllustrated(EventEnvelope):
    """판정 하나에 딸린 장면 삽화가 만들어졌다. `caused_by_seq`가 그 판정 사건이다.

    **그림은 게임 상태가 아니다.** 이 사건은 상태 숫자를 하나도 바꾸지 않으며
    (`rules_core.reducer`가 이 종류를 받아도 상태를 그대로 돌려준다), 판정·서사
    어느 것에도 영향을 주지 않는다. 화면에 무엇을 덧붙였는지에 대한 기록일 뿐이다.

    **실패는 이 사건으로 남지 않는다.** 그림을 못 만든 턴에는 사건이 아예
    없다 — `image_path`가 빈 문자열인 사건을 남기면 「그림이 있다」는 이 사건의
    뜻이 무너지고, 읽는 쪽마다 빈 값 검사를 다시 해야 한다. 그림 없는 턴은
    삽화 사건이 없는 턴으로 표현된다.

    `prompt`·`seed`·`steps`·`size`를 다 남기는 이유는 재현이다 — 이 네 값과
    `style`이 있으면 같은 그림을 다시 만들 수 있다. `latency_ms`는 그림이
    턴 응답을 늦추지 않았음을 확인하는 데 쓴다(생성은 응답 뒤 배경에서 돈다).
    """

    event_type: Literal["scene_illustrated"]
    image_path: str
    prompt: str
    style: str
    seed: int
    steps: int
    size: int
    latency_ms: int


GameEvent = Annotated[
    Union[
        ActionDeclared,
        ActionConfirmed,
        CheckResolved,
        NarrationAppended,
        ClockAdvanced,
        AiInvoked,
        SceneIllustrated,
    ],
    Field(discriminator="event_type"),
]

EVENT_ADAPTER: TypeAdapter[GameEvent] = TypeAdapter(GameEvent)


def parse_event(raw: str) -> GameEvent:
    """JSON 문자열을 사건 객체로 되돌린다. 순수 JSON 파서만 쓴다 — pickle/eval 없음."""
    return EVENT_ADAPTER.validate_json(raw)

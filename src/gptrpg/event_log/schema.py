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

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

EVENT_SCHEMA_VERSION = 8
"""판 7 -> 판 8: 능력치가 판정에 실리고 판정에 딸린 자원 변화가 기록에
남는 첫 줄기(Phase 12, D-05/D-65)가 사건 형식에 닿았다. 새 사건 종류가
하나 늘었다 — `ResourceChanged`(캐릭터 하나의 자원 축 여러 개가 「축 ·
동작 · 양」 세 칸짜리 항목 목록으로 한 번에 바뀌었다는 사실). `caused_by_seq`가
그 변화를 일으킨 `check_resolved`(또는 재량 판정) 사건이다. `source`가
그 변화가 어디서 나왔는지(룰북 결과 목록/재량 판정/역선언 중 하나)를
가른다 — 지금은 판정 직후 서버가 결정한 고정 변화 하나뿐이지만(이 단계의
탐색적 한 줄기), 12-04·12-06이 나머지 두 갈래를 실제로 채운다. 기존 열
종류의 칸은 하나도 바뀌지 않았으므로 판 1~7로 쓰인 기록은 글자 그대로
다시 읽힌다(늘어난 것이 「새 종류」일 뿐이라 옛 기록에는 그 종류의 사건이
없다) — `rules_core/reducer.py`의 `resource_changed` 분기는 이 판 올리기와
반드시 같은 커밋이다(08-CONTEXT.md D-06, 이미 여러 번 난 사고 — 이번이
네 번째 사례).

판 6 -> 판 7: `proceed()`(웹)/CLI `no_check` 갈래의 서버 쪽 안전 검사(11-06
rework, T-11-29 — 판정이 필요했던 선언을 판정 없이 진행할 수 있던 차단
결함)가 사건 형식에 닿았다. 새 사건 종류가 하나 늘었다 — `ActionClassified`
(분류기가 이 선언에 대해 `no_check` 여부를 최종 결정했다는 운영 사실).
`caused_by_seq`가 그 `action_declared` 사건이다. `no_check` 불리언 하나만
남긴다 — `single`/`several`/`unclear`의 구분은 웹 응답의 `tier` 칸이 이미
담당하므로 서버 상태에 중복해서 담지 않는다. 기존 아홉 종류의 칸은 하나도
바뀌지 않았으므로 판 1~6으로 쓰인 기록은 글자 그대로 다시 읽힌다(늘어난
것이 「새 종류」일 뿐이라 옛 기록에는 그 종류의 사건이 없다) —
`rules_core/reducer.py`의 `action_classified` 분기는 이 판 올리기와 반드시
같은 커밋이다(08-CONTEXT.md D-06). **옛 기록(이 사건이 없는 declare_seq)의
처리:** `SessionActor._prepare_verify_proceed_eligibility`는 이 표에 없는
declare_seq를 「no_check로 분류된 적이 없다」로 읽어 **거부**한다 —
`declare_owners`의 "모르면 통과" 관례와 다른 선택이다(그 관례는 캐릭터
개념이 없던 호출부의 정당한 「모른다」를 반영하지만, 여기서 "모른다"를
통과시키면 이 판 올리기가 막으려는 바로 그 구멍이 다시 열린다).

판 1 -> 판 2: `CheckResolved`에 `counts_as_failure` 필수 칸이 늘었다(D-12).
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
파싱되지 않아 Phase 6이 두 세션 기록을 함께 읽을 수 없다).

판 4 -> 판 5: 신원 검증(Phase 8, TRUST-01~04)이 사건 형식에 닿았다. 새
사건 종류가 하나 늘었다 — `CharacterOccupied`(캐릭터를 처음 점유했다,
D-05/D-06). `ActionDeclared`·`ActionConfirmed`에 선택 칸
`character_id: str | None = None`이 늘었다 — 판 5 미만 기록에는 이 칸이
없었으므로 소유자를 「모른다」로 읽는다(값을 추측해 채우지 않는다, D-13).
`CheckResolved`에는 `person_id`·`character_id`가 늘었고, 판 5 이상 기록에서만
**필수**다(D-12) — 판 5 미만 기록은 이 두 칸이 없어도 그대로 읽힌다. 이
구분이 `.gptrpg/events.db`에 실제로 살아 있는 판 2 기록 895건을 판 5 코드가
예외 없이 읽는 유일한 길이다.

판 5 -> 판 6: AI 출력 검증(Phase 10, SAFE-01/03, D-04)이 사건 형식에 닿았다.
새 사건 종류가 하나 늘었다 — `SafetyFlagged`(서사 안전 장치가 걸렀거나,
분류기가 닫힌 목록 밖 응답을 냈다는 운영자 기록). 서사 검사(`source=
"narration"`)와 분류기 계약 위반(`source="classifier"`) 둘을 한 종류로
묶는다 — 판 올리기가 되돌릴 수 없는 조작이므로 한 번에 둘 다 덮는다
(10-01-PLAN.md Task 1 checkpoint, option-a). 자유 문자열 칸은 없다 — 닫힌
목록 셋과 숫자 둘뿐이다(T-10-03, 사람이 읽을 발췌는 사건이 아니라 표준오류
에만). 기존 여덟 종류의 칸은 하나도 바뀌지 않았으므로 판 1~5로 쓰인
기록은 글자 그대로 다시 읽힌다 — `.gptrpg/events.db`의 판 2 기록 895건과
`.gptrpg/uat9.db`의 판 5 기록 221건 둘 다 이 판 올리기 뒤에도 예외 없이
읽혀야 한다(`rules_core/reducer.py`의 `safety_flagged` 분기가 이 판 올리기와
반드시 같은 커밋이다, 08-CONTEXT.md D-06)."""

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
    character_id: str | None = None
    """이 선언을 낸 캐릭터(판 5+, D-03/TRUST-03). 판 5 미만 기록은 이 칸이
    없었으므로 `None`으로 읽힌다 — 「그 시절에는 안 적었다」이지 「빈 문자열」이
    아니다. `SessionActor`가 서버 재시작 뒤에도 확인 요청의 소유권을 판정할
    근거가 이 칸에 남는다."""


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
    character_id: str | None = None
    """확인하는 캐릭터(판 5+, D-03). `ActionDeclared.character_id`와 같은
    이유·같은 선택 칸 형식이다."""


class CheckResolved(EventEnvelope):
    """판정 한 번 = 사건 하나 (D-17). 계산 과정 전체를 담는다 (D-16)."""

    event_type: Literal["check_resolved"]
    move: str
    rolls: list[int]
    modifiers: list[ModifierRecord]
    target: int
    grade: Grade
    counts_as_failure: bool
    person_id: str | None = None
    character_id: str | None = None
    """「어느 브라우저가 · 어느 캐릭터로」(TRUST-04, D-12). 판 5 이상
    기록에서는 아래 검증기가 두 칸을 필수로 강제한다 — 판정 기록에 누구의
    판정인지가 반드시 남는다. 판 5 미만 기록은 이 칸이 없어도 그대로 읽힌다
    (`.gptrpg/events.db`의 판 2 판정 기록 38건, D-13)."""

    @model_validator(mode="after")
    def _require_identity_from_schema_5(self) -> "CheckResolved":
        if self.schema_version >= 5 and (self.person_id is None or self.character_id is None):
            raise ValueError("판 5부터 person_id·character_id는 필수 칸이다")
        return self


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


class CharacterOccupied(EventEnvelope):
    """캐릭터를 처음 점유했다 — 먼저 잡은 사람이 임자다(D-05/D-06).

    놓기 사건은 없다(D-07) — 한 번 잡으면 놓을 수 없다는 결정이 사건 종류
    목록에도 그대로 반영된다. 서버를 껐다 켜도 이 사건을 다시 읽으면 점유가
    복원된다.
    """

    event_type: Literal["character_occupied"]
    character_id: str
    browser_id: str


class SafetyFlagged(EventEnvelope):
    """AI 출력 안전 장치가 걸렀거나 의심스럽다고 표시한 사실의 운영자 기록(판 6).

    `source`가 어느 방어가 남긴 기록인지를 가른다 — `"narration"`은 서사
    스트림 검사(`narration_guard.inspect_sentence`, Phase 10), `"classifier"`는
    분류기가 룰북 목록 밖 무브를 낸 계약 위반(D-12/SAFE-07)이다. 둘을 한
    종류로 묶은 것은 Task 1 checkpoint의 명시적 선택(option-a)이다 — 판
    올리기는 되돌릴 수 없는 조작이므로(D-04 Reversibility: one-way) 한 번에
    두 운영자 기록을 다 덮는다.

    **자유 문자열 칸을 두지 않는다** — `reason`·`disposition`은 닫힌 목록,
    `matched_len`·`subject_len`은 코드포인트 개수 숫자뿐이다(T-10-03). 모델이
    쓴 글자나 걸린 원문의 부분열은 이 사건 어디에도 담기지 않는다 — 사람이
    읽을 발췌는 표준오류에만 찍힌다(`agents/master_gm._judge_sentence`).

    **상태를 하나도 바꾸지 않는다** — `rules_core.reducer.apply_event`의
    `safety_flagged` 분기는 `scene_illustrated`와 같은 최소 모양
    (`last_seq`만 갱신)이다. 그래도 그 분기가 있어야 한다 — 없으면 이 종류의
    사건이 하나라도 있는 세션이 폴링마다 `UnknownEventType`을 맞고 영구히
    안 열린다(08-CONTEXT.md D-06, 이미 두 번 난 사고).
    """

    event_type: Literal["safety_flagged"]
    source: Literal["narration", "classifier"]
    reason: Literal[
        "think_block", "source_overlap", "character_break", "unknown_move", "corrupted_glyph"
    ]
    # `corrupted_glyph`(10-06, SAFE-01)를 더해도 EVENT_SCHEMA_VERSION은 6에서
    # 안 올린다 — ① `reason`은 쓰기 검증에서만 쓰이고(session_actor/actor.py의
    # _VALID_SAFETY_FLAG_REASONS, 읽기 경로는 안 봄) ② rules_core.reducer.py의
    # `safety_flagged` 분기는 `reason`을 아예 안 보고 `last_seq`만 올린다.
    # 따라서 이미 쓰인 기록의 해석이 한 글자도 안 바뀐다 — 판을 올리면 없는
    # 비호환을 있다고 알리는 잘못된 신호가 된다(10-06-PLAN.md 설계 판단 3,
    # tests/test_event_schema_migration.py가 못박는다).
    disposition: Literal["blocked", "flagged"]
    matched_len: int = 0
    subject_len: int = 0
    chunk_index: int | None = None

    @model_validator(mode="after")
    def _require_source_reason_pairing(self) -> "SafetyFlagged":
        """`source`와 `reason`의 말 안 되는 조합을 거절한다(10-07, WR-03).

        `reason == "unknown_move"`인 것과 `source == "classifier"`인 것은
        서로 필요충분이다 — 분류기(`action_classifier`)는 닫힌 목록 밖 응답
        하나만 신고하고(SAFE-07/D-12), 나머지 넷(`think_block`/`source_overlap`/
        `character_break`/`corrupted_glyph`)은 전부 서사 검사
        (`narration_guard.inspect_sentence`)가 내는 사유다. 이 둘을 갈라
        두는 이유는 "새 사유를 더하는 사람이 어느 쪽에 속하는지 반드시
        정하게 만드는 것"이다 — `CheckResolved._require_identity_from_schema_5`가
        이미 쓰는 `model_validator(mode="after")` 모양을 그대로 따른다(새
        방식을 만들지 않는다).

        **이 검증이 `session_actor/actor.py`의 `_prepare_safety_flag`와
        중복이 아닌 이유** — 액터 검증은 명령이 저장소에 닿기 전에 막고,
        이 스키마 검증은 저장소를 우회해(예: 직접 `SafetyFlagged(...)` 생성)
        만든 객체까지 막는다. 한쪽만 있으면 다른 경로로 우회된다.
        """
        is_classifier = self.source == "classifier"
        is_unknown_move = self.reason == "unknown_move"
        if is_classifier != is_unknown_move:
            raise ValueError(
                "source='classifier'와 reason='unknown_move'는 서로 필요충분이다 — "
                f"받은 조합: source={self.source!r}, reason={self.reason!r}"
            )
        return self


class ActionClassified(EventEnvelope):
    """분류기가 이 선언에 대해 판정이 필요한지를 최종 결정했다(판 7,
    11-06 rework, T-11-29). `caused_by_seq`가 그 `action_declared` 사건이다.

    **이 사건은 오직 하나의 목적을 갖는다** — `proceed()`(웹)·CLI
    `no_check` 갈래가 서버 재시작 후에도 「이 선언이 실제로 `no_check`로
    분류됐는가」를 사건에서 다시 접어 확인할 수 있게 한다(TRUST-03 확장).
    `declare_owners`가 같은 이유로 판 5에 늘었던 것과 같은 자리다.

    `no_check` 불리언 하나만 남기고 `single`/`several`/`unclear`를 구분해
    담지 않는다 — 이 안전 검사가 필요로 하는 것이 그 값 하나뿐이고, 화면이
    보여줄 나머지 구분(웹 응답의 `tier` 칸)은 서버 상태에 중복해서 담을
    이유가 없다(YAGNI, 구분이 필요해지면 그때 넓힌다).

    **상태를 그 외에는 하나도 바꾸지 않는다** — `rules_core.reducer.
    apply_event`의 `action_classified` 분기는 `declare_no_check` 표 하나만
    채우고 판정·실패 누적·시계 어디에도 닿지 않는다.
    """

    event_type: Literal["action_classified"]
    no_check: bool


class ResourceChangeRecord(BaseModel):
    """자원 변화 사건 안에 남는 항목 하나 — 「축 · 동작 · 양」(D-05, RULE-09).

    `ModifierRecord`와 같은 `extra="forbid", frozen=True` 설정이다. `before`/
    `after`는 이 변화가 적용되기 전/후의 값이다 — 이 계획은 `numeric` 축만
    다루므로 항상 정수지만, 값을 아직 계산하지 않은 경로(사건을 쓰는 쪽이
    시작값에 접근할 수 없는 경우)는 `None`으로 남긴다("계산 안 함"과 "0"이
    섞이지 않는다).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    axis: str
    operation: str
    amount: int
    rolls: list[int] = []
    before: int | None
    after: int | None


class ResourceChanged(EventEnvelope):
    """판정(또는 재량 판정)에 딸린 자원 변화 하나 — 캐릭터 하나의 자원 축
    여러 개가 한 번에 바뀐다(판 8, D-05/D-65/RULE-04).

    `caused_by_seq`가 이 변화를 일으킨 `check_resolved` 사건(또는 재량
    판정 흐름)이다. `source`가 이 변화가 어디서 나왔는지를 가른다 —
    `outcome_list`(룰북 결과 목록, 12-04가 실제로 채운다), `discretionary_ruling`
    (재량 판정, 12-06), `retro_declaration`(역선언, 12-04/Cairn류). 이
    계획(12-01)이 만드는 첫 줄기는 던전월드류의 「대가가 붙는 등급 하나」에
    붙는 고정 변화 하나이고, `source="outcome_list"`로 남긴다 — 12-04가
    실제 결과 목록 인프라를 놓는 뒤에도 이 이름을 그대로 쓴다(값이 아니라
    이름이 먼저 자리를 잡는다).
    """

    event_type: Literal["resource_changed"]
    character_id: str
    changes: list[ResourceChangeRecord]
    category_id: str | None = None
    source: Literal["outcome_list", "discretionary_ruling", "retro_declaration"]


GameEvent = Annotated[
    Union[
        ActionDeclared,
        ActionConfirmed,
        CheckResolved,
        NarrationAppended,
        ClockAdvanced,
        AiInvoked,
        SceneIllustrated,
        CharacterOccupied,
        SafetyFlagged,
        ActionClassified,
        ResourceChanged,
    ],
    Field(discriminator="event_type"),
]

EVENT_ADAPTER: TypeAdapter[GameEvent] = TypeAdapter(GameEvent)


def parse_event(raw: str) -> GameEvent:
    """JSON 문자열을 사건 객체로 되돌린다. 순수 JSON 파서만 쓴다 — pickle/eval 없음."""
    return EVENT_ADAPTER.validate_json(raw)

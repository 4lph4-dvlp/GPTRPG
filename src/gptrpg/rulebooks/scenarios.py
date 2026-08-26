"""등록된 시나리오 이름 -> 선언을 잇는 등록소(D-18). `rulebooks/__init__.py`의
`RULEBOOKS`/`validate_registered_rulebooks`와 같은 모양이다 — 새 시나리오는
여기 등록만 하면 된다.
"""

from gptrpg.rulebooks.lamplight_vigil import LAMPLIGHT_VIGIL, LAMPLIGHT_VIGIL_ID
from gptrpg.rulebooks.threat_clocks import (
    THREAT_CLOCK_SEGMENT_COUNT,
    WELL_BELOW,
    WELL_BELOW_ID,
)
from gptrpg.rules_core.scenario import InvalidOpening, InvalidScenarioDecl, ScenarioDecl

SCENARIOS: dict[str, ScenarioDecl] = {
    LAMPLIGHT_VIGIL_ID: LAMPLIGHT_VIGIL,
    WELL_BELOW_ID: WELL_BELOW,
}
"""**13-03이 「우물 아래의 것」(`WELL_BELOW`)을 두 번째 항목으로 등록했다**
— 이 순간 등록소에 `opening_kind`가 서로 다른(scripted/sketch) 시나리오
둘이 있으므로, 아래 `validate_registered_scenarios()`의 「등록된 시나리오가
둘 이상인데 종류가 전부 같으면 거부」 검사가 이번에 처음 실제로 걸린다
(D-21/D-06의 실현)."""

DEFAULT_SCENARIO_ID = WELL_BELOW_ID
"""오프닝 라우트(`web/routes_actions.py`)의 `OpeningRequest.scenario_id`
기본값 — **13-03이 재판단한 값**이다. 13-01은 이 시나리오가 아직
등록되지 않아 `LAMPLIGHT_VIGIL_ID`(형식 검증용 최소 시나리오)를 임시
기본값으로 뒀었다(13-01-SUMMARY.md 승인된 편차) — 그 SUMMARY가 명시적으로
「13-03이 우물 시나리오를 등록하는 시점에 이 기본값을 다시 판단해야
한다」고 남겨 뒀다. 지금 재판단한 결과는 `WELL_BELOW`다:
`lamplight_vigil`은 형식이 두 종류(낭독문형/메모형)를 다 받는다는 것을
증명하기 위해 이 단계가 새로 지은 최소 분량의 시나리오일 뿐, 실제 플레이를
겨냥한 것이 아니다(D-21 — "완결편을 쓰는 것이 아니라 최소"). 실제 세션1
경험과 이 프로젝트의 위협 시계 설계 전체가 `WELL_BELOW`(우물 아래의 것)를
전제로 만들어졌고, 시나리오 선택 화면이 아직 없으므로(13-01 assumption
⑤) 모든 실제 세션이 이 기본값 하나로 열린다 — 그 자리는 데모용 시나리오가
아니라 이 프로젝트의 실제 시나리오여야 한다."""


class UnknownScenario(Exception):
    """등록되지 않은 scenario_id로 조회했을 때 던진다.

    기본 시나리오로 조용히 대체하면 요청한 것과 다른 이야기로 오프닝이
    열린다(`UnknownRulebook`과 같은 이유, T-02-04)."""

    def __init__(self, scenario_id: str) -> None:
        super().__init__(f"등록되지 않은 시나리오: {scenario_id!r}")
        self.scenario_id = scenario_id


def get_scenario(scenario_id: str) -> ScenarioDecl:
    """등록된 시나리오를 이름으로 찾는다. 없으면 `UnknownScenario`."""
    scenario = SCENARIOS.get(scenario_id)
    if scenario is None:
        raise UnknownScenario(scenario_id)
    return scenario


_IMAGERY_SETTING_MAX_CHARS = 300
"""`imagery.scene_prompt.MAX_PROMPT_CHARS`와 **같은 값이어야 한다**(지금
300). 그 상수를 여기서 직접 import하지 못하는 이유는 층 계약
(`.importlinter` contract:2)이 이 파일이 속한 층(`gptrpg.rulebooks`)보다
`gptrpg.imagery`가 위 층이라 아래 층이 위 층을 import하는 것을 금지하기
때문이다 — `ScenarioDecl.imagery_setting` 도크스트링이 이미 같은 이유로
"이 칸은 그 상수를 참조하지 않고 값만 담는다"고 적어 뒀다. 두 상수가
갈라지면 이 등록 시점 검사가 실제 그림 생성 상한과 어긋난다 — **값을
바꿀 때는 반드시 두 자리(`imagery/scene_prompt.py`의 `MAX_PROMPT_CHARS`와
여기)를 함께 고친다.**"""


def validate_registered_scenarios() -> None:
    """`SCENARIOS`에 등록된 각 시나리오에 검사를 돌린다 — 다섯 요소
    (D-07ⓐ)가 채워졌는지, `opening_kind == "sketch"`이면 `hook_terms`가
    있는지, `improv_people`/`improv_things`/`threat_clock`을 실제로
    선언했는지(D-18, 「아직 선언하지 않았다」가 조용히 통과하면 게임 중에
    발견된다), `cast`의 이름이 시나리오 안에서 유일한지, 그리고 등록된
    시나리오들이 `opening_kind`를 서로 다르게 쓰는지(D-21/D-06, 형식이
    두 종류를 다 받는다는 것이 실제로 증명되는지). **13-03이 두 검사를
    더했다:** `threat_clock.segment_descriptions`의 칸 수가
    `THREAT_CLOCK_SEGMENT_COUNT`와 같은지(칸 수가 다른 시나리오가 들어오면
    프롬프트 분모와 화면 머리띠 분모가 어긋난다 — `turn/context.py`의
    `CLOCK_SEGMENT_COUNT` 도크스트링 참고), `imagery_setting`이 그림 층의
    상한(`imagery.scene_prompt.MAX_PROMPT_CHARS`, 300자)을 넘지 않는지
    (등록 시점에 걸어 실제 그림 생성에서 조용히 잘리는 일을 막는다).
    위반이 있으면 이 모듈이 임포트되는 순간 예외로 죽는다.

    **등록 시점 검사는 런타임 방어선을 대체하지 않는다**
    (`rulebooks/__init__.py`의 `validate_registered_rulebooks` 도크스트링과
    같은 경계) — 이 함수는 "정적으로 등록된 시나리오가 처음부터 깨져
    있지 않은가"만 지킨다.
    """
    opening_kinds: list[str] = []
    for scenario_id, scenario in SCENARIOS.items():
        opening = scenario.opening
        if not opening.who_you_are.strip():
            raise InvalidOpening("who_you_are가 비었다", scenario_id=scenario_id)
        if not opening.what_you_sense.strip():
            raise InvalidOpening("what_you_sense가 비었다", scenario_id=scenario_id)
        if not opening.why_it_matters.strip():
            raise InvalidOpening("why_it_matters가 비었다", scenario_id=scenario_id)
        if not opening.hooks or any(not hook.strip() for hook in opening.hooks):
            raise InvalidOpening(
                "hooks가 비었거나 빈 문자열을 담고 있다", scenario_id=scenario_id
            )
        if not opening.invitation.strip():
            raise InvalidOpening("invitation이 비었다", scenario_id=scenario_id)
        # 메모형은 생성 검사(13-03)가 대조할 손잡이가 있어야 한다 —
        # 낭독문형에는 요구하지 않는다(hook_terms는 낭독문형에서 안
        # 쓰인다, OpeningDecl 도크스트링).
        if scenario.opening_kind == "sketch" and not opening.hook_terms:
            raise InvalidOpening(
                "opening_kind가 sketch인데 hook_terms가 비었다",
                scenario_id=scenario_id,
            )
        if scenario.improv_people is None:
            raise InvalidScenarioDecl(
                "improv_people을 선언하지 않았다", scenario_id=scenario_id
            )
        if scenario.improv_things is None:
            raise InvalidScenarioDecl(
                "improv_things를 선언하지 않았다", scenario_id=scenario_id
            )
        if scenario.threat_clock is None:
            raise InvalidScenarioDecl(
                "threat_clock을 선언하지 않았다", scenario_id=scenario_id
            )
        segment_count = len(scenario.threat_clock.segment_descriptions)
        if segment_count != THREAT_CLOCK_SEGMENT_COUNT:
            raise InvalidScenarioDecl(
                f"threat_clock.segment_descriptions 칸 수가 {segment_count}인데"
                f" THREAT_CLOCK_SEGMENT_COUNT({THREAT_CLOCK_SEGMENT_COUNT})와"
                " 다르다 — 프롬프트 분모와 화면 머리띠 분모가 어긋난다",
                scenario_id=scenario_id,
            )
        if len(scenario.imagery_setting) > _IMAGERY_SETTING_MAX_CHARS:
            raise InvalidScenarioDecl(
                f"imagery_setting이 {len(scenario.imagery_setting)}자로 그림"
                f" 층의 상한({_IMAGERY_SETTING_MAX_CHARS}자,"
                " imagery.scene_prompt.MAX_PROMPT_CHARS)을 넘는다",
                scenario_id=scenario_id,
            )
        names = [entity.display_name for entity in scenario.cast]
        if len(names) != len(set(names)):
            raise InvalidScenarioDecl(
                "cast 안에 같은 display_name이 둘 이상이다 — 대상 대조가"
                " 어느 쪽을 고를지 정해지지 않는다",
                scenario_id=scenario_id,
            )
        opening_kinds.append(scenario.opening_kind)

    # 「셋 다 같은 값이면 형식이 검증되지 않는다」(D-04류, D-21/D-06) —
    # 등록된 시나리오가 둘 이상인데 opening_kind가 전부 같으면 형식이
    # 두 종류를 다 받는다는 것이 실제로 증명되지 않는다.
    if len(opening_kinds) > 1 and len(set(opening_kinds)) == 1:
        raise InvalidScenarioDecl(
            "등록된 시나리오가 전부 같은 opening_kind를 쓰면 이 형식이"
            " 낭독문형·메모형을 둘 다 받는다는 것이 검증되지 않는다"
            " (D-21/D-06)"
        )


validate_registered_scenarios()

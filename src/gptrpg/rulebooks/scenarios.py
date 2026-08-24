"""등록된 시나리오 이름 -> 선언을 잇는 등록소(D-18). `rulebooks/__init__.py`의
`RULEBOOKS`/`validate_registered_rulebooks`와 같은 모양이다 — 새 시나리오는
여기 등록만 하면 된다.
"""

from gptrpg.rulebooks.lamplight_vigil import LAMPLIGHT_VIGIL, LAMPLIGHT_VIGIL_ID
from gptrpg.rules_core.scenario import InvalidOpening, InvalidScenarioDecl, ScenarioDecl

SCENARIOS: dict[str, ScenarioDecl] = {
    LAMPLIGHT_VIGIL_ID: LAMPLIGHT_VIGIL,
}
"""**기존 「우물 아래의 것」(`rulebooks/threat_clocks.py`)은 아직 여기
등록되지 않는다** — 그 이관은 13-03이 한다(이 파일이 `turn/context.py`·
`imagery/scene_prompt.py`와 함께 파일이 겹치기 때문). 이 판에서는 항목이
하나이므로 아래 `validate_registered_scenarios()`의 「둘 이상일 때 종류가
갈려야 한다」 검사는 아직 안 걸린다 — 13-03이 두 번째를 넣는 순간 걸린다."""


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


def validate_registered_scenarios() -> None:
    """`SCENARIOS`에 등록된 각 시나리오에 검사를 돌린다 — 다섯 요소
    (D-07ⓐ)가 채워졌는지, `opening_kind == "sketch"`이면 `hook_terms`가
    있는지, `improv_people`/`improv_things`/`threat_clock`을 실제로
    선언했는지(D-18, 「아직 선언하지 않았다」가 조용히 통과하면 게임 중에
    발견된다), `cast`의 이름이 시나리오 안에서 유일한지, 그리고 등록된
    시나리오들이 `opening_kind`를 서로 다르게 쓰는지(D-21/D-06, 형식이
    두 종류를 다 받는다는 것이 실제로 증명되는지). 위반이 있으면 이
    모듈이 임포트되는 순간 예외로 죽는다.

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

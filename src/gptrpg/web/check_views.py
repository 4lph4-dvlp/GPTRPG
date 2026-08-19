"""판정 계산 줄의 응답 View — `routes_actions.py`와 `routes_events.py`가
같은 모양을 쓰도록 이 한 곳에 둔다(라우터끼리 서로 import하지 않는다).

`calculation_view_for`는 사건에서 계산 줄을 만드는 유일한 어댑터다. 두
정상 갈래(판 10 미만 기록 · 등록 안 된 룰북)는 `None`을 돌려주고, 그
밖의 실패는 예외를 그대로 올린다. **판 10 기록에 등록된 룰북이 붙어
있는데 계산 줄을 못 만드는 것은 빌더의 결함이다** — 이 저장소는 그런
것을 조용히 넘기지 않는다(굴릴 수 있으면 그릴 수 있다 불변식은
`rules_core.check_calculation._BUILDERS`와 `session_actor.actor._RESOLVERS`가
같은 열쇠 집합을 갖는다는 시험이 지킨다).
"""

from pydantic import BaseModel

from gptrpg.event_log.schema import CheckResolved
from gptrpg.rulebooks import UnknownRulebook, get_rulebook
from gptrpg.rules_core.check_calculation import build_check_calculation
from gptrpg.rules_core.resolution import Modifier


class CalculationSegmentView(BaseModel):
    role: str
    value: int
    source: str | None = None
    discarded: bool = False


class CalculationRowView(BaseModel):
    segments: list[CalculationSegmentView]
    total: int | None = None


class CheckCalculationView(BaseModel):
    seq: int
    rows: list[CalculationRowView]
    total: int
    target: int
    direction: str


def calculation_view_for(event: CheckResolved) -> CheckCalculationView | None:
    """판정 사건 하나에서 계산 줄을 만든다.

    `event.total`이나 `event.rulebook_id`가 `None`이면(판 10 미만 기록)
    `None`을 돌려준다 — D-05의 정상 경로다. `event.rulebook_id`가 등록
    안 된 룰북이면(`UnknownRulebook`) 역시 `None`을 돌려준다 — 무엇으로
    계산할지 모르는 것을 아는 척하지 않는다. 그 밖의 빌더 실패는 예외를
    그대로 올린다.
    """
    if event.total is None or event.rulebook_id is None:
        return None
    try:
        rulebook = get_rulebook(event.rulebook_id)
    except UnknownRulebook:
        return None

    modifiers = tuple(
        Modifier(type=m.type, value=m.value, source=m.source) for m in event.modifiers
    )
    calculation = build_check_calculation(
        resolution_method=rulebook.resolution_method,
        rolls=event.rolls,
        modifiers=modifiers,
        total=event.total,
        target=event.target,
    )
    return CheckCalculationView(
        seq=event.seq,
        rows=[
            CalculationRowView(
                segments=[
                    CalculationSegmentView(
                        role=segment.role,
                        value=segment.value,
                        source=segment.source,
                        discarded=segment.discarded,
                    )
                    for segment in row.segments
                ],
                total=row.total,
            )
            for row in calculation.rows
        ],
        total=calculation.total,
        target=calculation.target,
        direction=calculation.direction,
    )

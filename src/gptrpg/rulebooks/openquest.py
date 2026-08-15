"""OpenQuest System Resource Document (CC BY 4.0)의 스킬 판정 규칙 선언.

출처: https://openquestrpg.com/srd/skills/skill-rules/ — 굴림이 기술값
이하면 성공, 초과면 실패, 두 주사위 눈이 같으면서 성공이면 크리티컬, 두 눈이
같으면서 실패면 펌블. 라이선스 첨부 문구와 표기 범위는 저장소 최상위
`LICENSES.md`를 본다(D-18: CC 라이선스가 있는 실제 룰북 자료).
"""

from gptrpg.rules_core.resolution import Modifier
from gptrpg.rules_core.resolution_d100 import TARGET_SHIFT
from gptrpg.rules_core.rulebook import D100_ROLL_UNDER, GradeBand, ResourceAxisDecl, Rulebook

OPENQUEST_ID = "openquest"

OPENQUEST_GRADE_BANDS: tuple[GradeBand, ...] = (
    GradeBand(name="critical", counts_as_failure=False, margin_at_least=0, requires_doubles=True),
    GradeBand(name="success", counts_as_failure=False, margin_at_least=0),
    GradeBand(name="fumble", counts_as_failure=True, margin_at_most=-1, requires_doubles=True),
    GradeBand(name="failure", counts_as_failure=True),
)

OPENQUEST_RESOURCE_AXES: tuple[ResourceAxisDecl, ...] = (
    # 크리처가 실제로 갖고 있는 열 축 — 이 단계는 numeric 형태 하나만
    # 관통시킨다(11-01).
    ResourceAxisDecl(name="STR", form="numeric"),
    ResourceAxisDecl(name="CON", form="numeric"),
    ResourceAxisDecl(name="DEX", form="numeric"),
    ResourceAxisDecl(name="SIZ", form="numeric"),
    ResourceAxisDecl(name="INT", form="numeric"),
    ResourceAxisDecl(name="POW", form="numeric"),
    ResourceAxisDecl(name="CHA", form="numeric"),
    ResourceAxisDecl(name="Hit Points", form="numeric"),
    ResourceAxisDecl(name="Magic Points", form="numeric"),
    ResourceAxisDecl(name="Armour Points", form="numeric"),
    # 아래 열 축은 `rulebooks/moves.py`의 `OPENQUEST_MOVES`가 이미 쓰고
    # 있던 기술 이름을 그대로 옮긴 것이다(11-02) — 새로 지어내지 않았다.
    # 지금 등록된 크리처(고블린·스켈레톤)는 이 축들의 `StatEntry`를 갖지
    # 않는데, 그것은 위반이 아니다(D-04) — 개체가 룰북 선언 축을 전부 가질
    # 필요는 없다. 이 선언이 없으면 `validate_move_stats`가 무브의
    # `default_stat`을 대조할 축 자체가 없어 등록이 통째로 막힌다(T-11-07).
    ResourceAxisDecl(name="근접 무기 기술", form="numeric"),
    ResourceAxisDecl(name="회피 기술", form="numeric"),
    ResourceAxisDecl(name="은신 기술", form="numeric"),
    ResourceAxisDecl(name="지각 기술", form="numeric"),
    ResourceAxisDecl(name="일반 지식 기술", form="numeric"),
    ResourceAxisDecl(name="설득 기술", form="numeric"),
    ResourceAxisDecl(name="장치 기술", form="numeric"),
    ResourceAxisDecl(name="운동 기술", form="numeric"),
    ResourceAxisDecl(name="의지 기술", form="numeric"),
    ResourceAxisDecl(name="원거리 무기 기술", form="numeric"),
)

OPENQUEST = Rulebook(
    rulebook_id=OPENQUEST_ID,
    display_name="OpenQuest",
    resolution_method=D100_ROLL_UNDER,
    grade_bands=OPENQUEST_GRADE_BANDS,
    resource_axes=OPENQUEST_RESOURCE_AXES,
)

OPENQUEST_DIFFICULTY: dict[str, int] = {
    "easy": 50,
    "simple": 20,
    "normal": 0,
    "difficult": -20,
    "hard": -50,
}
"""OpenQuest SRD 난이도 다섯 단계 — 기술값에 가산할 목표값 변경 폭.
출처: https://openquestrpg.com/srd/skills/difficulty/ (`[CITED]`).
"""


def difficulty_modifier(name: str) -> Modifier:
    """난이도 이름 하나를 `TARGET_SHIFT` 수정치로 바꾼다.

    SRD 원문은 "판정 하나에 난이도 수정치는 하나만 쓴다"고 정하지만, 그것은
    룰북의 운용 규칙이지 플랫폼의 계산 제약이 아니다 — 플랫폼은 여러 개를
    합산할 수 있어야 한다(다른 룰북은 여러 개를 허용한다). 이 함수는 하나만
    돌려주고, 여러 개를 합칠지는 호출부(룰북 운용 규칙)가 정한다.
    """
    return Modifier(
        type=TARGET_SHIFT,
        value=OPENQUEST_DIFFICULTY[name],
        source=f"openquest:difficulty:{name}",
    )

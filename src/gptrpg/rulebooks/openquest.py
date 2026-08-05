"""OpenQuest System Resource Document (CC BY 4.0)의 스킬 판정 규칙 선언.

출처: https://openquestrpg.com/srd/skills/skill-rules/ — 굴림이 기술값
이하면 성공, 초과면 실패, 두 주사위 눈이 같으면서 성공이면 크리티컬, 두 눈이
같으면서 실패면 펌블. 라이선스 첨부 문구와 표기 범위는 저장소 최상위
`LICENSES.md`를 본다(D-18: CC 라이선스가 있는 실제 룰북 자료).
"""

from gptrpg.rules_core.resolution import Modifier
from gptrpg.rules_core.resolution_d100 import TARGET_SHIFT
from gptrpg.rules_core.rulebook import D100_ROLL_UNDER, GradeBand, Rulebook

OPENQUEST_ID = "openquest"

OPENQUEST_GRADE_BANDS: tuple[GradeBand, ...] = (
    GradeBand(name="critical", counts_as_failure=False, margin_at_least=0, requires_doubles=True),
    GradeBand(name="success", counts_as_failure=False, margin_at_least=0),
    GradeBand(name="fumble", counts_as_failure=True, margin_at_most=-1, requires_doubles=True),
    GradeBand(name="failure", counts_as_failure=True),
)

OPENQUEST = Rulebook(
    rulebook_id=OPENQUEST_ID,
    display_name="OpenQuest",
    resolution_method=D100_ROLL_UNDER,
    grade_bands=OPENQUEST_GRADE_BANDS,
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

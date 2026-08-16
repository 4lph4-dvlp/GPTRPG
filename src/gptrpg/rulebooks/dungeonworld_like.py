"""던전월드 계열 2d6 등급 세 이름을, `grading.grade_for_total`의 실제 경계
규칙 그대로 룰북 선언으로 명시한다.

이 선언은 지금 등급 **계산**에 쓰이지 않는다 — `grade_for_total`이 이미
계산을 하고, 세션 액터가 그 함수가 돌려준 이름을 이 선언과 대조하고
`counts_as_failure`를 여기서 읽는다. 즉 이름의 권위가 선언 쪽에 있다.

`EXAMPLE_SINGLE_STAT_FOE`는 이 룰북(또는 어떤 룰북)의 원문에서 온 것이
아니다 — 상태값 하나만 담긴 `Entity`도 OpenQuest 크리처(상태값 열 개)와
같은 클래스로 코드 수정 없이 만들어짐을 보이기 위한 자체 작성 예시다.
"""

from gptrpg.rules_core.entities import Entity, StatEntry
from gptrpg.rules_core.grading import WEAK_HIT_BAND
from gptrpg.rules_core.rulebook import TWO_D6, GradeBand, ResourceAxisDecl, Rulebook

DUNGEONWORLD_LIKE_ID = "dungeonworld_like"

DUNGEONWORLD_GRADE_BANDS: tuple[GradeBand, ...] = (
    GradeBand(name="strong_hit", counts_as_failure=False, margin_at_least=0),
    GradeBand(name="weak_hit", counts_as_failure=False, margin_at_least=-WEAK_HIT_BAND),
    GradeBand(name="miss", counts_as_failure=True),
)

DUNGEONWORLD_RESOURCE_AXES: tuple[ResourceAxisDecl, ...] = (
    # 캐릭터·적이 실제로 갖고 있는 여덟 축 그대로 — 이 단계는 numeric 형태
    # 하나만 관통시킨다(11-01). 여섯 형태 전부는 11-03이 붙인다.
    ResourceAxisDecl(name="체력", form="numeric"),
    ResourceAxisDecl(name="STR", form="numeric"),
    ResourceAxisDecl(name="DEX", form="numeric"),
    ResourceAxisDecl(name="CON", form="numeric"),
    ResourceAxisDecl(name="INT", form="numeric"),
    ResourceAxisDecl(name="WIS", form="numeric"),
    ResourceAxisDecl(name="CHA", form="numeric"),
    ResourceAxisDecl(name="방어구", form="numeric"),
)

DUNGEONWORLD_LIKE = Rulebook(
    rulebook_id=DUNGEONWORLD_LIKE_ID,
    display_name="Dungeonworld-like",
    resolution_method=TWO_D6,
    grade_bands=DUNGEONWORLD_GRADE_BANDS,
    resource_axes=DUNGEONWORLD_RESOURCE_AXES,
    check_trigger_mode="declared_list",
)

# 자체 작성 예시 — 어떤 룰북 원문에서도 오지 않았다(D-18이 배제한 자체 창작
# 미니 룰북과 혼동하지 않도록, 이 사실을 라벨로 남긴다). 그릇에 상태값
# 하나만 담아도 되는지 보이기 위한 것일 뿐, 실제 던전월드 계열 몬스터
# 스탯블록이 아니다.
EXAMPLE_SINGLE_STAT_FOE = Entity(
    entity_id="dungeonworld_like.example_single_stat_foe",
    display_name="상태값 하나짜리 예시 적",
    rulebook_id=DUNGEONWORLD_LIKE_ID,
    stats=(
        StatEntry(
            name="체력",
            form="numeric",
            current=5,
            max=5,
            depleted_effect_ref="dungeonworld_like.hp_depleted",
        ),
    ),
)

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
from gptrpg.rules_core.resource_change import ResourceChangeDecl
from gptrpg.rules_core.rulebook import TWO_D6, GradeBand, ResourceAxisDecl, Rulebook

DUNGEONWORLD_LIKE_ID = "dungeonworld_like"

DUNGEONWORLD_GRADE_BANDS: tuple[GradeBand, ...] = (
    # succeeded/costs/counts_as_failure — D-13이 직접 든 예. strong_hit은
    # 이루었고(succeeded) 대가가 없다(costs=False).
    GradeBand(
        name="strong_hit",
        counts_as_failure=False,
        succeeded=True,
        costs=False,
        margin_at_least=0,
    ),
    # weak_hit: 이뤘지만 대가가 붙는다(PbtA류 부분 성공, D-13/D-14가 직접
    # 든 예) — 실패로는 안 센다(counts_as_failure=False, 기존 값 불변).
    GradeBand(
        name="weak_hit",
        counts_as_failure=False,
        succeeded=True,
        costs=True,
        margin_at_least=-WEAK_HIT_BAND,
    ),
    # miss: 못 이뤘고 대가(피해 등)가 붙으며 위협 시계 입력으로도 센다.
    GradeBand(name="miss", counts_as_failure=True, succeeded=False, costs=True),
)

DUNGEONWORLD_RESOURCE_AXES: tuple[ResourceAxisDecl, ...] = (
    # 캐릭터·적이 실제로 갖고 있는 여덟 축 그대로 — 이 단계는 numeric 형태
    # 하나만 관통시킨다(11-01). 여섯 형태 전부는 11-03이 붙인다. 능력치
    # 여섯(STR~CHA)에는 12-01이 `stat_usage="add_to_dice_total"`을 더한다
    # (D-01) — 능력치 값이 판정 합계에 더해진다. 체력·방어구·소지품에는
    # 더하지 않는다(판정에 쓰이는 축이 아니다).
    ResourceAxisDecl(name="체력", form="numeric"),
    ResourceAxisDecl(name="STR", form="numeric", stat_usage="add_to_dice_total"),
    ResourceAxisDecl(name="DEX", form="numeric", stat_usage="add_to_dice_total"),
    ResourceAxisDecl(name="CON", form="numeric", stat_usage="add_to_dice_total"),
    ResourceAxisDecl(name="INT", form="numeric", stat_usage="add_to_dice_total"),
    ResourceAxisDecl(name="WIS", form="numeric", stat_usage="add_to_dice_total"),
    ResourceAxisDecl(name="CHA", form="numeric", stat_usage="add_to_dice_total"),
    ResourceAxisDecl(name="방어구", form="numeric"),
    # 소지품 — 이 룰북은 소지품을 규칙으로 세지 않는다(RULE-12, D-67, 11-07).
    # 이 파일이 이 선언을 담아도 되는 이유: 이 모듈 도크스트링이 이미
    # "던전월드 계열의 판정 방식을 참고한 자체 선언"이며 원문 옮김이
    # 아니라고 밝히고 있고, PbtA 계열이 소지품을 규칙으로 세지 않고 "말이
    # 되면 갖고 있는 것으로 친다"로 다룬다는 것은 특정 저작물의 원문이
    # 아니라 `RULEBOOK-SURVEY.md` §3-A·§4가 정리한 스펙트럼상의 사실이다
    # (특정 저작물의 고유명사·원문을 옮기지 않는다).
    #
    # **D-09를 이 자리에 문장으로 남긴다.** `none_kind="discretionary"`이므로
    # 이 룰북에는 "소지품에 없는 것을 쓰겠다"는 판단 자체가 성립하지 않는다
    # — 대조할 목록이 없으니 그냥 서사로 흘러간다. Phase 12가 만들 "소지품에
    # 없는 것을 쓰면 재량 판정으로 간다"는 **세는 룰북에만** 적용되고, 이
    # 단계는 그 대조 경로·재량 판정 분기를 여기서 새로 만들지 않는다.
    ResourceAxisDecl(name="소지품", form="none", none_kind="discretionary"),
)

DUNGEONWORLD_LIKE = Rulebook(
    rulebook_id=DUNGEONWORLD_LIKE_ID,
    display_name="Dungeonworld-like",
    resolution_method=TWO_D6,
    grade_bands=DUNGEONWORLD_GRADE_BANDS,
    resource_axes=DUNGEONWORLD_RESOURCE_AXES,
    check_trigger_mode="declared_list",
)

DUNGEONWORLD_MISS_HP_COST = ResourceChangeDecl(axis="체력", operation="delta", amount=-6)
"""「대가가 붙는 등급(miss)이 나오면 체력이 고정 6 깎인다」— 이 계획(12-01)이
뚫는 탐색적 한 줄기를 위한 상수다. 자원 변화 한 줄기를 실제로 관통시키는
것이 목적이라 지금은 이 파일 안의 상수 하나일 뿐이고, `rules_core`는 이
이름도 「체력」이라는 축 이름도 모른다. 12-04가 이 값을 결과 목록
(outcome_list) 항목 안으로 옮긴다 — 그때까지는 `web/routes_actions.py`가
이 상수를 직접 참조해 자원 변화 사건을 제출한다."""

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

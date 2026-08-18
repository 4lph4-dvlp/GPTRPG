"""Cairn SRD(CC BY-SA 4.0)의 세이브 판정 규칙 선언 — 스펙트럼 반대쪽 끝 룰북.

출처: https://cairnrpg.com/first-edition/cairn-srd/ — d20을 굴려 능력치
이하면 통과(1은 항상 성공, 20은 항상 실패), Hit Protection은 체력이 아니라
「피해를 피하는 능력」(시작값 1d6), 소지품은 배낭 6 + 양손 각 1 + 상체 2 =
총 10칸(부피 큰 물건은 2칸), Fatigue는 그 칸을 채우는 값, **고정된 무브/행동
목록이 없다**(진행자가 그 자리에서 정한다). 필수 첨부 문구와 표기 범위,
그리고 ShareAlike 조건이 위 OpenQuest(CC BY 4.0)와 다르다는 것은 저장소
최상위 `LICENSES.md`를 본다(D-18).

**D-14의 시험대:** 이 파일이 `ResourceAxisDecl`/`StatEntry`/`GradeBand`/
`Entity` 그릇의 칸을 하나도 늘리지 않고 등록된다는 것 자체가, 11-01이 만든
그릇 설계가 던전월드류·OpenQuest 두 룰북에만 맞춰진 것이 아니라는 증거다.
`git diff --stat src/gptrpg/rules_core/entities.py`가 이 파일이 존재하는
동안에도 계속 비어 있어야 한다.
"""

from gptrpg.rules_core.entities import Entity, StatEntry
from gptrpg.rules_core.rulebook import (
    D20_ROLL_UNDER,
    CreationStepDecl,
    GradeBand,
    OutcomeList,
    PartySizeRange,
    ResourceAxisDecl,
    RetroDeclarationDecl,
    Rulebook,
)

CAIRN_ID = "cairn"

CAIRN_GRADE_BANDS: tuple[GradeBand, ...] = (
    # Cairn의 세이브 결과는 통과/실패 둘뿐이다 — 등급 이름이 두 개뿐이라는
    # 것 자체가 던전월드류(셋)·OpenQuest(넷)와 다른 스펙트럼 끝이라는 증거다.
    # SRD의 "1은 항상 성공, 20은 항상 실패" 규칙은 margin 구간 어휘로 표현할
    # 수 없는 주사위 눈 자체의 규칙(margin이 아니라 굴림 결과 원문을 봐야
    # 한다)이므로 이번에 담지 않는다 — 지어내 넣지 않는다.
    GradeBand(name="pass", counts_as_failure=False, succeeded=True, costs=False, margin_at_least=0),
    # fail: 세이브 실패는 정의상 대가가 따른다(피해·상태 등, "세이브"라는
    # 개념 자체의 뜻) — SRD가 그 대가의 구체적 종류를 절차로 정하지 않을
    # 뿐이다(이 판단이 이 파일이 outcome_list를 빈 튜플로 선언하는 이유,
    # Task 3). costs=True는 "대가가 있다"는 사실만 담고, 그 대가가
    # 무엇인지는 재량 판정으로 간다(RULE-13 — 목록이 없는 룰북은 전부
    # 재량 판정으로 간다).
    GradeBand(name="fail", counts_as_failure=True, succeeded=False, costs=True),
)

CAIRN_RESOURCE_AXES: tuple[ResourceAxisDecl, ...] = (
    # SRD가 실제로 정한 것만 담는다 — 무기·주문·이동력 등 나머지 항목은
    # `openquest_creatures.py`가 세운 "필드 단위 상세 규격은 M0 범위 밖"
    # 관례 그대로 담지 않는다.
    ResourceAxisDecl(name="STR", form="numeric"),
    ResourceAxisDecl(name="DEX", form="numeric"),
    ResourceAxisDecl(name="WIL", form="numeric"),
    # Hit Protection은 체력이 아니라 "피해를 피하는 능력"이고 상한이 있는
    # 축이므로(시작값 1d6) 개체 쪽에서 max를 채운다.
    ResourceAxisDecl(name="Hit Protection", form="numeric"),
    # 소지품 총 10칸(배낭 6 + 양손 각 1 + 상체 2) — named_slots 형태가 실제
    # 데이터에 등장하는 첫 자리다(RULE-11).
    ResourceAxisDecl(name="Inventory", form="named_slots", slot_count=10),
    # Fatigue는 별도 축이 아니라 소지품 칸을 채우는 값이다 — 축으로 만들지
    # 않는다(SRD 원문: Fatigue 한 칸을 소진하면 소지품 칸 하나가 그만큼 준다).
)

CAIRN_OUTCOME_LIST = OutcomeList(categories=())
"""빈 튜플이다 — SRD가 세이브 실패 시의 결과를 절차로 정하지 않는다(이
파일 도크스트링이 이미 "고정된 무브/행동 목록이 없다"로 같은 성질을
적었다). `fail` 밴드는 `costs=True`로 대가가 있다는 사실만 선언하고,
그 대가가 구체적으로 무엇인지는 지어내 넣지 않는다 — 재량 판정(12-06)
으로 간다(RULE-13)."""

CAIRN_RETRO_DECLARATION = RetroDeclarationDecl(
    allowed=True,
    # 축은 Hit Protection이 아니라 Inventory다 — SRD가 실제로 정한 사실은
    # "Fatigue가 소지품 칸을 차지한다"는 것뿐이다(이 파일 위쪽
    # `CAIRN_RESOURCE_AXES` 주석·`LICENSES.md`가 인용하는 SRD 조항). 소급
    # 선언("사실 나 그거 챙겨왔었어")의 대가를 이 자리에 태운다 — 이미
    # SRD가 정한 Fatigue 형태(소지품 칸 하나를 채운다)를 그대로 재사용한다
    # (D-16 — 새 형식을 만들지 않는다). 소지품을 세는 유일한 룰북이라
    # "없는 것을 쓴다"가 데이터로 성립하는 유일한 자리다(RULE-16).
    cost_axis="Inventory",
    operation="fill",
)

CAIRN_CREATION_STEPS: tuple[CreationStepDecl, ...] = (
    # 주사위 위주 만들기 — 세 능력치를 한 단계로 굴린다(`roll_to_fill`은
    # `axis_names` 각각에 대해 독립적으로 굴린다). 3d6은 `CAIRN_EXAMPLE_ADVENTURER`가
    # 이미 쓰는 값(current=10, 3d6 평균)과 일치한다(웹 검색으로 확인한 SRD
    # 내용 — 원문 PDF 직접 확인은 아니다).
    CreationStepDecl(
        step_id="abilities", kind="roll_to_fill", label="능력치 굴리기",
        required=True, axis_names=("STR", "DEX", "WIL"), dice_expr="3d6",
    ),
    # Hit Protection — 체력이 아니라 "피해를 피하는 능력", 시작값 1d6
    # (`CAIRN_RESOURCE_AXES` 주석). 별도 단계인 이유: 세 능력치와 굴림
    # 시점이 SRD상 자연스럽게 갈리는 값이라 같은 dice_expr로 묶이지
    # 않는다(1d6 vs 3d6).
    CreationStepDecl(
        step_id="hit_protection", kind="roll_to_fill", label="Hit Protection 굴리기",
        required=True, axis_names=("Hit Protection",), dice_expr="1d6",
    ),
    # 배경/트린켓 — SRD 표 항목을 고른다(`pick_one`). "굴려서 표를 뽑는다"는
    # 이 형식으로 표현되지 않는다(알려진 한계, RQ-1 유형 8의 사촌) — 지금
    # 형식으로는 사람이 고르는 것까지만 표현 가능하다.
    CreationStepDecl(
        step_id="background", kind="pick_one", label="배경", required=True,
        options=(
            "폐허를 뒤지던 도굴꾼",
            "장돌뱅이 행상인",
            "파문당한 사제",
            "몰락한 용병",
        ),
    ),
    CreationStepDecl(
        step_id="name", kind="free_text", label="이름", required=True,
        provides_display_name=True,
    ),
    # 소지품(named_slots 10칸)은 이번 만들기 단계에서 채우지 않는다(알려진
    # 한계) — 만들기 단계 형식이 `named_slots` 축을 채우는 조작을 갖고
    # 있지 않다. `place_fixed_values`/`allocate_points`/`roll_to_fill`은
    # 전부 정수 축을 채운다.
)

CAIRN_PARTY_SIZE_RANGE = PartySizeRange(min_player_characters=1, max_player_characters=4)
"""가볍고 소규모로 도는 계열의 권장 범위(D-01) — 던전월드류(3~5)·
OpenQuest(2~6)와 또 다른 숫자를 실제로 써서 세 룰북이 같은 범위를 복사해
붙이지 않았음을 보인다. 1인 전용(최소=최대=1)이 정상값이라는 것은
`tests/test_rulebook.py`의 단위 시험이 별도로 확인한다 — 이 범위(1~4)
자체는 1인 전용이 아니다."""

CAIRN = Rulebook(
    rulebook_id=CAIRN_ID,
    display_name="Cairn",
    resolution_method=D20_ROLL_UNDER,
    grade_bands=CAIRN_GRADE_BANDS,
    resource_axes=CAIRN_RESOURCE_AXES,
    # Cairn에는 고정 무브 목록이 없다 — 진행자가 그 자리에서 정한다(D-12).
    check_trigger_mode="gm_discretion",
    outcome_list=CAIRN_OUTCOME_LIST,
    retro_declaration=CAIRN_RETRO_DECLARATION,
    creation_steps=CAIRN_CREATION_STEPS,
    party_size_range=CAIRN_PARTY_SIZE_RANGE,
)

# 자체 작성 예시 — 어떤 룰북 원문에서도 오지 않았다(D-18이 배제한 자체 창작
# 미니 룰북과 혼동하지 않도록, dungeonworld_like.py의 EXAMPLE_SINGLE_STAT_FOE와
# 같은 라벨 관례를 따른다). 이 개체의 존재 이유는 "10칸 소지품이라는 형태가
# 그릇에 실제로 들어간다"를 보이는 것이므로, SRD 몬스터 수치를 옮기지 않는다.
CAIRN_EXAMPLE_ADVENTURER = Entity(
    entity_id="cairn.example_adventurer",
    display_name="10칸 소지품 예시 모험가",
    rulebook_id=CAIRN_ID,
    stats=(
        StatEntry(name="STR", form="numeric", current=10),
        StatEntry(name="DEX", form="numeric", current=10),
        StatEntry(name="WIL", form="numeric", current=10),
        StatEntry(
            name="Hit Protection",
            form="numeric",
            current=4,
            max=4,
            depleted_effect_ref="cairn.hp_depleted",
        ),
        StatEntry(
            name="Inventory",
            form="named_slots",
            slot_values=(
                "장검",
                "랜턴",
                "밧줄 15m",
                "휴대식량 3일치",
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        ),
    ),
)

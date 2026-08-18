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
from gptrpg.rules_core.rulebook import (
    NO_CHANGE_CATEGORY_ID,
    TWO_D6,
    CreationStepDecl,
    GradeBand,
    OutcomeCategory,
    OutcomeList,
    PartySizeRange,
    ResourceAxisDecl,
    Rulebook,
)

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

DUNGEONWORLD_OUTCOME_LIST = OutcomeList(
    categories=(
        # 「판정이 나빴을 때(또는 대가가 붙을 때) 진행자가 고르는 대응」
        # 계열 — 던전월드 GM 대응 목록이 8~10개 고정 카테고리로 실재하는
        # 표준 형태라는 것은 `RULEBOOK-SURVEY.md` §2-C가 정리한 스펙트럼상의
        # 사실이다. 이 파일 도크스트링이 이미 "원문 옮김이 아니라 자체
        # 선언"이라고 밝히고 있으므로, 카테고리 식별자는 특정 출간작의
        # 원문·고유명사가 아니라 플랫폼 어휘로 짓는다. 이 룰북이 실제로
        # 가진 축(체력·방어구)만 가리킨다 — 없는 축을 지어내 넣지 않는다.
        OutcomeCategory(
            category_id="대상을 다치게 한다",
            # 12-01이 이 파일에 임시로 뒀던 `DUNGEONWORLD_MISS_HP_COST`
            # (체력 -6)를 그대로 흡수한다 — 값(축·동작·양)은 안 바뀌었다,
            # 목록 항목 안으로 자리만 옮겼다. `web/routes_actions.py`는 이제
            # 이 항목을 `require_outcome_category`로 찾아 쓴다.
            changes=(ResourceChangeDecl(axis="체력", operation="delta", amount=-6),),
        ),
        OutcomeCategory(
            category_id="가진 것을 빼앗는다",
            changes=(ResourceChangeDecl(axis="방어구", operation="delta", amount=-1),),
        ),
        OutcomeCategory(
            category_id="자원을 소모시킨다",
            # 고정값이 아니라 주사위식(D-06) — 12-02가 연 통로가 실제
            # 룰북 데이터에 처음 쓰이는 자리다.
            changes=(ResourceChangeDecl(axis="체력", operation="delta", amount="-1d4"),),
        ),
        OutcomeCategory(
            category_id="대가를 요구하되 이득을 준다",
            changes=(ResourceChangeDecl(axis="방어구", operation="delta", amount=-1),),
        ),
        # 「이번엔 숫자가 안 변한다」(D-09) — 이 항목 하나가 확인 창을
        # 정말 변할 때만 뜨게 만든다. 변화가 빈 항목은 이것 하나뿐이다.
        OutcomeCategory(category_id=NO_CHANGE_CATEGORY_ID, changes=()),
    ),
    # 이 계열은 실제로 한 번에 하나씩 돈다 — GM 대응은 한 번에 한 가지를
    # 고르는 절차다(RULEBOOK-SURVEY.md §2-C).
    max_picks=1,
)

DUNGEONWORLD_CREATION_STEPS: tuple[CreationStepDecl, ...] = (
    # `docs/experiment/character-creation-script.md`의 만들기 대본 1~4단계
    # 전체를 데이터로 옮긴다(12.1-02 Task 3) — 이 파일에 들어가는 값은
    # 전부 룰북 콘텐츠다(항목 이름·선택지 문구·숫자·체력 공식의 16과 2가
    # 전부 여기 있고 플랫폼 코드에는 하나도 없다). `web/characters_data.py`의
    # `NEW_CHARACTER_*` 상수가 지금 같은 값을 중복해서 갖고 있고, 12.1-05가
    # 그 파일을 시험 재료로 옮길 때 중복이 해소된다.
    #
    # 순서가 곧 의존 방향이다(`Rulebook.__post_init__`) — "archetype"이
    # "ability_array"의 `default_from`과 "backstory" 앞에 오고,
    # "ability_array"가 "hp"의 `depends_on` 앞에 온다.
    CreationStepDecl(
        # 대본 1단계 앞부분 — ① 목록에서 하나 고르기.
        step_id="archetype", kind="pick_one", label="사람됨", required=True,
        options=(
            "몸으로 먼저 막아선다",
            "그림자 속에서 조용히, 들키지 않게 움직인다",
            "무슨 일이 벌어지고 있는지 먼저 알아내려 한다",
            "말로 상대의 마음을 움직이려 한다",
        ),
    ),
    CreationStepDecl(
        # 대본 1단계 뒷부분 — ⑥ 자유롭게 쓰기("왜 여기 있는가").
        step_id="backstory", kind="free_text", label="왜 여기 있는가", required=True,
    ),
    CreationStepDecl(
        # 대본 2단계 — ④ 정해진 숫자를 자리에 배치. `default_from`이
        # "archetype"을 가리킨다 — 대본 61~66행의 「1단계 선택 → 추천
        # 배치」 표가 이 칸이 표현해야 하는 것이다(추천 배치 자체의 숫자는
        # 룰북 콘텐츠라 여기 선언에는 없다 — 이 형식은 "누구를 따라 추천을
        # 뽑을지"만 표현하고, 추천값 계산은 GM 대화 쪽(12.1-03)이 대본을
        # 그대로 읽는다).
        step_id="ability_array", kind="place_fixed_values", label="능력치 배치",
        required=True, axis_names=("STR", "DEX", "CON", "INT", "WIS", "CHA"),
        # 이 여섯 숫자는 룰북 콘텐츠이고 지금 web/characters_data.py:32의
        # NEW_CHARACTER_STAT_ARRAY와 같은 값이다 — 같은 값이 두 곳에 있는
        # 것은 12.1-05가 그 정적 상수를 지울 때 해소된다.
        fixed_values=(2, 1, 1, 0, 0, -1), default_from="archetype",
    ),
    CreationStepDecl(
        # 대본 3단계 체력 — ⑦ 자동 계산. `16 + CON 값 × 2`.
        step_id="hp", kind="derive", label="체력", required=True,
        axis_names=("체력",), derive_base_axis="CON", derive_multiplier=2,
        derive_offset=16, depends_on=("ability_array",),
    ),
    CreationStepDecl(
        # 대본 3단계 방어구 — 조건부 제안(랜드마인, 12.1-RESEARCH.md).
        # `required=False`로 「이 단계를 안 채워도 캐릭터가 완성된다」만
        # 표현한다 — 「1단계에서 무엇을 골랐느냐에 따라 제안 여부가
        # 갈린다」는 알려진 한계로 표현하지 않는다(조건 언어를 만들면
        # 결국 유형 8을 만들게 된다). 대본에서 이 대목은 GM이 대화로
        # 「방어구를 가지시겠어요?」를 물으면 되는 자리다(D-03).
        step_id="armor", kind="pick_one", label="방어구", required=False,
        options=("가벼운 방어구를 갖춘다", "방어구 없이 시작한다"),
    ),
    CreationStepDecl(
        # 대본 4단계 — ⑥ 자유롭게 쓰기(이름·모습). 표시 이름의 유일한
        # 출처다(provides_display_name).
        step_id="name", kind="free_text", label="이름·모습", required=True,
        provides_display_name=True,
    ),
    # 대본 5단계(완성 순간 되읽기)·6단계(애착 질문)는 만들기 단계가
    # 아니다 — 5단계는 D-10의 GM 정리 절차이고 6단계는 M0 계측용
    # 질문이다. 둘 다 여기 `CreationStepDecl`로 나타나지 않는다는 것을
    # `tests/test_creation_script_fixture.py`가 명시적으로 단언한다.
)

DUNGEONWORLD_PARTY_SIZE_RANGE = PartySizeRange(
    min_player_characters=3, max_player_characters=5
)
"""던전월드 계열 출간작이 실제로 적는 권장 인원(D-01) — `docs/experiment/
character-creation-script.md`가 이 실험의 참가자 규모(둘)로 진행됐다고
해서 룰북 콘텐츠 자체의 권장 범위가 바뀌지는 않는다(그 대본은 「시간이
모자랄 때」 절에서 이미 시간 예산을 줄여 진행하는 것을 명시한다)."""

DUNGEONWORLD_LIKE = Rulebook(
    rulebook_id=DUNGEONWORLD_LIKE_ID,
    display_name="Dungeonworld-like",
    resolution_method=TWO_D6,
    grade_bands=DUNGEONWORLD_GRADE_BANDS,
    resource_axes=DUNGEONWORLD_RESOURCE_AXES,
    check_trigger_mode="declared_list",
    outcome_list=DUNGEONWORLD_OUTCOME_LIST,
    creation_steps=DUNGEONWORLD_CREATION_STEPS,
    party_size_range=DUNGEONWORLD_PARTY_SIZE_RANGE,
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

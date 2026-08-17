"""`ResourceAxisDecl`/`Rulebook.resource_axes`의 모양과 검증, 그리고 등급
밴드의 「가려짐/구멍」 등록 검증을 확인한다(D-01, D-02, D-04, D-13, D-15).

이 파일은 11-01이 새로 만든 `ResourceAxisDecl` 신설과 `Rulebook.resource_axes`
필수화에 대한 회귀 방지 시험으로 시작해서, 11-02가 「가려짐/구멍」 검증
(D-15, QUAL-03)과 개체-룰북 축 정합성 검증(D-01) 시험을 이어 붙인다.
`tests/test_entities.py`가 `StatEntry`(개체 쪽 값 그릇)를 담당하는 것과
짝을 이뤄, 이 파일은 `Rulebook`/`ResourceAxisDecl`/`GradeBand`(룰북 쪽
선언)를 담당한다.
"""

import dataclasses

import pytest

from gptrpg.rules_core.entities import (
    ENTITY_FIELD_NAMES,
    STAT_ENTRY_FIELD_NAMES,
    Entity,
    StatEntry,
)
from gptrpg.rules_core.resource_change import ResourceChangeDecl
from gptrpg.rules_core.rulebook import (
    NO_CHANGE_CATEGORY_ID,
    TWO_D6,
    EntityAxisMismatch,
    GradeBand,
    InvalidOutcomeList,
    InvalidResourceAxis,
    InvalidTriggerMode,
    OutcomeCategory,
    OutcomeList,
    ResourceAxisDecl,
    RetroDeclarationDecl,
    Rulebook,
    ShadowedGradeBand,
    UncoveredOutcomeGap,
    UnknownOutcomeCategory,
    ordered_categories,
    require_band,
    require_outcome_category,
    validate_entity_axes,
    validate_grade_bands,
    validate_move_stats,
    validate_outcome_list,
    validate_trigger_mode,
)
from gptrpg.rulebooks import RULEBOOKS, get_rulebook, validate_registered_rulebooks
from gptrpg.rulebooks.cairn import (
    CAIRN,
    CAIRN_EXAMPLE_ADVENTURER,
    CAIRN_GRADE_BANDS,
    CAIRN_ID,
    CAIRN_RESOURCE_AXES,
)
from gptrpg.rulebooks.dungeonworld_like import (
    DUNGEONWORLD_GRADE_BANDS,
    DUNGEONWORLD_LIKE,
    DUNGEONWORLD_LIKE_ID,
    DUNGEONWORLD_RESOURCE_AXES,
    EXAMPLE_SINGLE_STAT_FOE,
)
from gptrpg.rulebooks.openquest import (
    OPENQUEST,
    OPENQUEST_GRADE_BANDS,
    OPENQUEST_ID,
    OPENQUEST_RESOURCE_AXES,
)
from gptrpg.rulebooks.moves import get_moves
from gptrpg.rulebooks.openquest_creatures import OPENQUEST_CREATURES
from gptrpg.web.characters_data import PLAYER_CHARACTERS

_EMPTY_BANDS: tuple[GradeBand, ...] = ()


def _rulebook(resource_axes: tuple[ResourceAxisDecl, ...]) -> Rulebook:
    return Rulebook(
        rulebook_id="test-only",
        display_name="시험 전용",
        resolution_method=TWO_D6,
        grade_bands=_EMPTY_BANDS,
        resource_axes=resource_axes,
        check_trigger_mode="no_dice",
    )


def test_rulebook_without_resource_axes_raises_type_error():
    """`resource_axes`는 기본값 없는 필수 필드다(D-02) — 「없다」를 말하려면
    `resource_axes=()`를 명시해야 한다."""
    with pytest.raises(TypeError):
        Rulebook(
            rulebook_id="test-only",
            display_name="시험 전용",
            resolution_method=TWO_D6,
            grade_bands=_EMPTY_BANDS,
            check_trigger_mode="no_dice",
        )


def test_rulebook_with_empty_resource_axes_is_valid():
    """빈 튜플로 「없다」를 명시하면 정상 등록된다."""
    rulebook = _rulebook(())
    assert rulebook.resource_axes == ()


def test_rulebook_with_duplicate_axis_names_raises():
    """같은 이름의 자원 축을 두 번 선언하면 `InvalidResourceAxis`다(RULE-11
    adjacency) — 이름이 겹치면 어느 선언이 이기는지 정해지지 않는다."""
    with pytest.raises(InvalidResourceAxis):
        _rulebook(
            (
                ResourceAxisDecl(name="체력", form="numeric"),
                ResourceAxisDecl(name="체력", form="numeric"),
            )
        )


def test_resource_axis_names_differing_only_by_trailing_whitespace_are_distinct():
    """이름 비교는 유니코드 정규화·대소문자 접기 없이 파이썬 `==` 완전
    일치다 — 앞뒤 공백만 다른 두 이름은 서로 다른 축으로 취급된다(RULE-11
    encoding)."""
    rulebook = _rulebook(
        (
            ResourceAxisDecl(name="체력", form="numeric"),
            ResourceAxisDecl(name="체력 ", form="numeric"),
        )
    )
    assert len(rulebook.resource_axes) == 2


def test_resource_axis_decl_with_whitespace_only_name_raises():
    """공백뿐인 이름은 `InvalidResourceAxis`다(RULE-11 encoding)."""
    with pytest.raises(InvalidResourceAxis):
        ResourceAxisDecl(name="   ", form="numeric")


def test_resource_axis_decl_none_form_without_none_kind_raises():
    """`form == "none"`이면 `none_kind`가 필수다(D-05)."""
    with pytest.raises(InvalidResourceAxis):
        ResourceAxisDecl(name="소지품", form="none")


def test_resource_axis_decl_none_kind_forbidden_outside_none_form():
    """`form != "none"`인데 `none_kind`를 채우면 거부된다."""
    with pytest.raises(InvalidResourceAxis):
        ResourceAxisDecl(name="체력", form="numeric", none_kind="absent")


def test_resource_axis_decl_named_slots_requires_slot_count():
    """`form == "named_slots"`이면 `slot_count`가 1 이상 필수다."""
    with pytest.raises(InvalidResourceAxis):
        ResourceAxisDecl(name="가방", form="named_slots")

    with pytest.raises(InvalidResourceAxis):
        ResourceAxisDecl(name="가방", form="named_slots", slot_count=0)

    valid = ResourceAxisDecl(name="가방", form="named_slots", slot_count=10)
    assert valid.slot_count == 10


def test_resource_axis_decl_slot_count_forbidden_outside_named_slots():
    """`form != "named_slots"`인데 `slot_count`를 채우면 거부된다."""
    with pytest.raises(InvalidResourceAxis):
        ResourceAxisDecl(name="체력", form="numeric", slot_count=5)


def test_dungeonworld_and_openquest_resource_axes_have_no_internal_duplicates():
    """실제 등록된 두 룰북 모두 자기 축 목록 안에서 이름이 겹치지 않는다
    (이미 `Rulebook.__post_init__`이 등록 시점에 강제하지만, 여기서도
    회귀 방지로 한 번 더 고정한다)."""
    for axes in (DUNGEONWORLD_RESOURCE_AXES, OPENQUEST_RESOURCE_AXES):
        names = [axis.name for axis in axes]
        assert len(names) == len(set(names))


def test_dungeonworld_resource_axes_are_eight_numeric_and_one_discretionary_none():
    """11-01이 관통시킨 numeric 여덟 축은 그대로다. 11-07이 아홉 번째 축
    ("소지품", `form="none"`, `none_kind="discretionary"`)을 추가해
    RULE-12를 실제 데이터로 실증한다 — "이 룰북은 소지품을 규칙으로 세지
    않는다"는 선언이 시험 픽스처가 아니라 저장소에 출하되는 룰북에 있다."""
    numeric_axes = [axis for axis in DUNGEONWORLD_RESOURCE_AXES if axis.form == "numeric"]
    none_axes = [axis for axis in DUNGEONWORLD_RESOURCE_AXES if axis.form == "none"]
    assert len(DUNGEONWORLD_RESOURCE_AXES) == 9
    assert len(numeric_axes) == 8
    assert [axis.name for axis in none_axes] == ["소지품"]
    assert none_axes[0].none_kind == "discretionary"
    assert DUNGEONWORLD_LIKE.resource_axes == DUNGEONWORLD_RESOURCE_AXES


def test_openquest_resource_axes_are_all_numeric_form():
    """11-01 당시 열 축(능력치+HP/MP/AP)이었던 것이, 11-02에서
    `validate_move_stats`가 `OPENQUEST_MOVES`의 기술 이름 열 개를 대조할
    축이 필요해지면서 스무 축으로 늘었다(주석 참조, T-11-07)."""
    assert len(OPENQUEST_RESOURCE_AXES) == 20
    assert all(axis.form == "numeric" for axis in OPENQUEST_RESOURCE_AXES)
    assert OPENQUEST.resource_axes == OPENQUEST_RESOURCE_AXES


# ---------------------------------------------------------------------------
# 등급 밴드 「가려짐/구멍」 등록 검증 (D-15, QUAL-03) — 11-02
# ---------------------------------------------------------------------------


def test_existing_rulebooks_pass_validation():
    """던전월드류·OpenQuest 둘 다 새 검증을 통과한다 — 두 룰북은 지금
    일부러 겹치게 선언돼 있고(D-15 회귀), 겹침을 오류로 잡으면 이 저장소
    자신의 룰북 둘이 등록 거부된다."""
    validate_grade_bands(DUNGEONWORLD_GRADE_BANDS)
    validate_grade_bands(OPENQUEST_GRADE_BANDS)


def test_shadowed_band_rejected():
    """앞 밴드들에 완전히 가려져 어떤 조합에서도 이길 수 없는 밴드는
    `ShadowedGradeBand`다 — `strong_hit`(margin>=0) 뒤의 `never`(margin>=5)는
    `strong_hit`가 이미 margin>=0을 전부 먹어서 영영 안 나온다."""
    bands = (
        GradeBand(name="strong_hit", counts_as_failure=False, succeeded=True, costs=False, margin_at_least=0),
        GradeBand(name="weak_hit", counts_as_failure=False, succeeded=True, costs=False, margin_at_least=-3),
        GradeBand(name="never", counts_as_failure=False, succeeded=True, costs=False, margin_at_least=5),
        GradeBand(name="miss", counts_as_failure=True, succeeded=False, costs=False),
    )
    with pytest.raises(ShadowedGradeBand) as exc_info:
        validate_grade_bands(bands)
    assert exc_info.value.band_name == "never"


def test_hole_rejected():
    """`success`(margin>=0) 하나만 있으면 margin<0인 조합이 어느 밴드에도
    안 맞는 구멍이라 `UncoveredOutcomeGap`이다."""
    bands = (GradeBand(name="success", counts_as_failure=False, succeeded=True, costs=False, margin_at_least=0),)
    with pytest.raises(UncoveredOutcomeGap):
        validate_grade_bands(bands)


def test_empty_grade_bands_rejected_as_hole():
    """`grade_bands=()`인 룰북은 모든 조합이 구멍이라 `UncoveredOutcomeGap`이다."""
    with pytest.raises(UncoveredOutcomeGap):
        validate_grade_bands(())


def test_simple_overlap_is_legal():
    """겹치는 구간이 있어도 선언 순서로 해소되고 정수선 전체가 덮이면
    거부되지 않는다(D-15) — `strong`과 `weak`가 margin>=0에서 겹친다."""
    bands = (
        GradeBand(name="strong", counts_as_failure=False, succeeded=True, costs=False, margin_at_least=0),
        GradeBand(name="weak", counts_as_failure=False, succeeded=True, costs=False, margin_at_least=-3),
        GradeBand(name="miss", counts_as_failure=True, succeeded=False, costs=False),
    )
    validate_grade_bands(bands)  # 예외 없이 통과한다


def test_touching_bands_leave_no_gap():
    """앞 밴드의 상한(`margin_at_most=-1`)과 뒤 밴드의 하한(`margin_at_least=0`)이
    정확히 맞닿으면 구멍도 가려짐도 아니다."""
    bands = (
        GradeBand(name="fumble", counts_as_failure=True, succeeded=False, costs=False, margin_at_most=-1),
        GradeBand(name="success", counts_as_failure=False, succeeded=True, costs=False, margin_at_least=0),
    )
    validate_grade_bands(bands)  # 예외 없이 통과한다


def test_declaration_order_decides_shadowing():
    """같은 밴드 집합이라도 선언 순서를 뒤집으면 가려짐 판정이 달라진다 —
    `grade_for_margin`과 정확히 같은 「선언 순서 첫 매치」 규칙을 쓴다는 증거다."""
    catch_all_first = (
        GradeBand(name="catch_all", counts_as_failure=True, succeeded=False, costs=False),
        GradeBand(name="strong", counts_as_failure=False, succeeded=True, costs=False, margin_at_least=0),
    )
    with pytest.raises(ShadowedGradeBand) as exc_info:
        validate_grade_bands(catch_all_first)
    assert exc_info.value.band_name == "strong"

    catch_all_last = (
        GradeBand(name="strong", counts_as_failure=False, succeeded=True, costs=False, margin_at_least=0),
        GradeBand(name="catch_all", counts_as_failure=True, succeeded=False, costs=False),
    )
    validate_grade_bands(catch_all_last)  # 예외 없이 통과한다 — 순서를 바꾸면 결과가 바뀐다


# ---------------------------------------------------------------------------
# 등급 밴드 세 칸 독립 — 성공했나 · 대가가 붙나 · 실패로 세나 (D-13/D-14,
# RULE-14) — 12-04
# ---------------------------------------------------------------------------


def test_grade_band_requires_succeeded_and_costs_with_no_default():
    """`succeeded`/`costs`는 `counts_as_failure`와 같은 이유로 기본값이
    없는 필수 칸이다 — 하나라도 빠뜨린 `GradeBand` 생성은 `TypeError`다."""
    with pytest.raises(TypeError):
        GradeBand(name="test-only", counts_as_failure=False, costs=False)  # succeeded 없음
    with pytest.raises(TypeError):
        GradeBand(name="test-only", counts_as_failure=False, succeeded=True)  # costs 없음
    with pytest.raises(TypeError):
        GradeBand(name="test-only", succeeded=True, costs=False)  # counts_as_failure 없음
    # 셋 다 채우면 통과한다.
    GradeBand(name="test-only", counts_as_failure=False, succeeded=True, costs=False)


def test_succeeded_and_counts_as_failure_can_both_be_true_registration_not_rejected():
    """`succeeded=True`이면서 `counts_as_failure=True`인 밴드를 선언해도
    등록이 거부되지 않는다 — 「성공했는데도 상황은 나빠진다」를 쓰는
    룰북을 표현할 수 있어야 한다는 것이 D-14가 지키려는 성질 그 자체다.
    셋 중 어느 것도 다른 것에서 자동으로 파생되지 않는다는 직접 증거다."""
    band = GradeBand(
        name="pyrrhic",
        counts_as_failure=True,
        succeeded=True,
        costs=True,
        margin_at_least=0,
    )
    # 검증 함수(가려짐/구멍) 자체가 이 조합을 거부하지 않는다는 것도 확인한다.
    validate_grade_bands((band, GradeBand(name="rest", counts_as_failure=True, succeeded=False, costs=False)))


def test_dungeonworld_weak_hit_band_has_succeeded_true_costs_true_not_a_failure():
    """`weak_hit`은 `succeeded=True, costs=True, counts_as_failure=False`다
    — D-13이 직접 든 예이자 이 저장소가 실제로 출하하는 데이터."""
    weak_hit = [b for b in DUNGEONWORLD_GRADE_BANDS if b.name == "weak_hit"][0]
    assert weak_hit.succeeded is True
    assert weak_hit.costs is True
    assert weak_hit.counts_as_failure is False


def test_dungeonworld_strong_hit_band_has_succeeded_true_costs_false():
    """`strong_hit`은 이뤘고(succeeded) 대가가 없다(costs=False)."""
    strong_hit = [b for b in DUNGEONWORLD_GRADE_BANDS if b.name == "strong_hit"][0]
    assert strong_hit.succeeded is True
    assert strong_hit.costs is False
    assert strong_hit.counts_as_failure is False


def test_dungeonworld_miss_band_has_succeeded_false_costs_true():
    """`miss`는 못 이뤘고 대가가 붙으며 위협 시계 입력으로도 센다 — 세
    칸이 서로 다른 값으로 각자 독립임을 보여준다."""
    miss = [b for b in DUNGEONWORLD_GRADE_BANDS if b.name == "miss"][0]
    assert miss.succeeded is False
    assert miss.costs is True
    assert miss.counts_as_failure is True


def test_dungeonworld_counts_as_failure_values_unchanged_by_new_fields():
    """`succeeded`/`costs` 신설이 기존 `counts_as_failure` 값을 한 글자도
    안 바꿨다 — 기존 실패 누적·시계 동작이 이 계획 전후로 전부 같다."""
    by_name = {b.name: b.counts_as_failure for b in DUNGEONWORLD_GRADE_BANDS}
    assert by_name == {"strong_hit": False, "weak_hit": False, "miss": True}


def test_openquest_counts_as_failure_values_unchanged_by_new_fields():
    """OpenQuest도 마찬가지로 `counts_as_failure` 값이 그대로다."""
    by_name = {b.name: b.counts_as_failure for b in OPENQUEST_GRADE_BANDS}
    assert by_name == {
        "critical": False,
        "success": False,
        "fumble": True,
        "failure": True,
    }


def test_cairn_counts_as_failure_values_unchanged_by_new_fields():
    """Cairn도 마찬가지로 `counts_as_failure` 값이 그대로다."""
    by_name = {b.name: b.counts_as_failure for b in CAIRN_GRADE_BANDS}
    assert by_name == {"pass": False, "fail": True}


def test_require_band_exposes_all_three_independent_fields():
    """이름으로 찾은 밴드에서 세 값을 전부 읽을 수 있다."""
    band = require_band(DUNGEONWORLD_GRADE_BANDS, "weak_hit")
    assert (band.succeeded, band.costs, band.counts_as_failure) == (True, True, False)


# ---------------------------------------------------------------------------
# 결과 카테고리 닫힌 목록 — 그릇과 등록 시점 검증 (RULE-13, D-05/D-07/D-09/
# D-11/D-12) — 12-04
# ---------------------------------------------------------------------------


def _test_rulebook_with_outcome_list(
    resource_axes: tuple[ResourceAxisDecl, ...],
    outcome_list: OutcomeList,
    retro_declaration: RetroDeclarationDecl | None = None,
) -> Rulebook:
    kwargs = {}
    if retro_declaration is not None:
        kwargs["retro_declaration"] = retro_declaration
    return Rulebook(
        rulebook_id="test-only-outcome-list",
        display_name="결과 목록 시험 전용",
        resolution_method=TWO_D6,
        grade_bands=_EMPTY_BANDS,
        resource_axes=resource_axes,
        check_trigger_mode="no_dice",
        outcome_list=outcome_list,
        **kwargs,
    )


def test_outcome_category_has_no_narration_field():
    """`OutcomeCategory`는 `category_id`/`changes` 두 칸뿐이다 — 서술
    문장을 담는 필드가 없다(D-11)."""
    category = OutcomeCategory(
        category_id="자원을 소모시킨다",
        changes=(ResourceChangeDecl(axis="체력", operation="delta", amount=-1),),
    )
    assert [f.name for f in dataclasses.fields(category)] == ["category_id", "changes"]


def test_outcome_category_with_empty_changes_is_normal_the_no_change_item():
    """빈 변화 목록이 정상값이다(D-09, 「이번엔 숫자가 안 변한다」)."""
    category = OutcomeCategory(category_id=NO_CHANGE_CATEGORY_ID, changes=())
    assert category.changes == ()


def test_outcome_list_with_empty_categories_is_normal_and_registers():
    """빈 목록이 정상값이고, 그것을 담은 `Rulebook`이 등록을 통과한다
    (D-12/RULE-13)."""
    rulebook = _test_rulebook_with_outcome_list((), OutcomeList(categories=()))
    assert rulebook.outcome_list.categories == ()


def test_outcome_list_with_zero_max_picks_and_nonempty_categories_raises():
    """목록이 있는데 하나도 못 고르는 선언(`max_picks=0`)은 어긋남이다."""
    with pytest.raises(InvalidOutcomeList):
        OutcomeList(
            categories=(OutcomeCategory(category_id=NO_CHANGE_CATEGORY_ID, changes=()),),
            max_picks=0,
        )


def test_outcome_list_with_duplicate_category_id_raises():
    """같은 `category_id`가 둘 있으면 `InvalidOutcomeList`다(adjacency)."""
    with pytest.raises(InvalidOutcomeList):
        OutcomeList(
            categories=(
                OutcomeCategory(category_id="같은이름", changes=()),
                OutcomeCategory(category_id="같은이름", changes=()),
            )
        )


def test_outcome_list_with_max_picks_greater_than_category_count_raises():
    """`max_picks`가 `categories` 길이보다 크면 `InvalidOutcomeList`다 —
    고를 수 있는 개수가 목록보다 많을 수 없다."""
    with pytest.raises(InvalidOutcomeList):
        OutcomeList(
            categories=(OutcomeCategory(category_id=NO_CHANGE_CATEGORY_ID, changes=()),),
            max_picks=2,
        )


def test_validate_outcome_list_rejects_unknown_axis_name():
    """변화가 가리키는 축 이름이 룰북의 `resource_axes`에 없으면
    `InvalidOutcomeList`다."""
    outcome_list = OutcomeList(
        categories=(
            OutcomeCategory(
                category_id="자원을 소모시킨다",
                changes=(ResourceChangeDecl(axis="없는축", operation="delta", amount=-1),),
            ),
        )
    )
    rulebook = _test_rulebook_with_outcome_list(
        (ResourceAxisDecl(name="체력", form="numeric"),), outcome_list
    )
    with pytest.raises(InvalidOutcomeList):
        validate_outcome_list(rulebook.outcome_list, rulebook)


def test_validate_outcome_list_rejects_none_form_axis():
    """`form="none"`인 축을 가리키는 변화를 담은 목록이 거부된다 — 그
    축에는 바꿀 값 자체가 없다."""
    outcome_list = OutcomeList(
        categories=(
            OutcomeCategory(
                category_id="소지품을 빼앗는다",
                changes=(ResourceChangeDecl(axis="소지품", operation="delta", amount=-1),),
            ),
        )
    )
    rulebook = _test_rulebook_with_outcome_list(
        (ResourceAxisDecl(name="소지품", form="none", none_kind="discretionary"),),
        outcome_list,
    )
    with pytest.raises(InvalidOutcomeList):
        validate_outcome_list(rulebook.outcome_list, rulebook)


def test_validate_outcome_list_rejects_form_operation_mismatch():
    """축의 `form`과 변화의 `operation`이 어긋나면(`numeric`에 `add_tag`)
    `InvalidOutcomeList`다."""
    outcome_list = OutcomeList(
        categories=(
            OutcomeCategory(
                category_id="상태를 붙인다",
                changes=(ResourceChangeDecl(axis="체력", operation="add_tag", amount=1),),
            ),
        )
    )
    rulebook = _test_rulebook_with_outcome_list(
        (ResourceAxisDecl(name="체력", form="numeric"),), outcome_list
    )
    with pytest.raises(InvalidOutcomeList):
        validate_outcome_list(rulebook.outcome_list, rulebook)


def test_validate_outcome_list_passes_for_matching_axis_form_operation():
    """축 이름·형태·동작이 전부 맞으면 예외 없이 통과한다."""
    outcome_list = OutcomeList(
        categories=(
            OutcomeCategory(
                category_id="자원을 소모시킨다",
                changes=(ResourceChangeDecl(axis="체력", operation="delta", amount=-2),),
            ),
            OutcomeCategory(category_id=NO_CHANGE_CATEGORY_ID, changes=()),
        )
    )
    rulebook = _test_rulebook_with_outcome_list(
        (ResourceAxisDecl(name="체력", form="numeric"),), outcome_list
    )
    validate_outcome_list(rulebook.outcome_list, rulebook)  # 예외 없이 통과한다


def test_require_outcome_category_raises_for_unknown_id():
    """선언에 없는 식별자면 `UnknownOutcomeCategory`다 — `require_band`와
    같은 모양."""
    outcome_list = OutcomeList(
        categories=(OutcomeCategory(category_id=NO_CHANGE_CATEGORY_ID, changes=()),)
    )
    with pytest.raises(UnknownOutcomeCategory):
        require_outcome_category(outcome_list, "존재하지 않는 항목")
    assert require_outcome_category(outcome_list, NO_CHANGE_CATEGORY_ID).category_id == (
        NO_CHANGE_CATEGORY_ID
    )


def test_ordered_categories_ignores_pick_order_uses_declaration_order():
    """`ordered_categories`가 고른 순서를 뒤집어 넣어도 선언 순서로 정렬된
    같은 튜플을 돌려준다(RULE-13 ordering) — 순서를 고정하면 같은 조합은
    항상 같은 결과다."""
    a = OutcomeCategory(category_id="a", changes=())
    b = OutcomeCategory(category_id="b", changes=())
    c = OutcomeCategory(category_id="c", changes=())
    outcome_list = OutcomeList(categories=(a, b, c), max_picks=3)

    forward = ordered_categories(outcome_list, ["a", "c"])
    reversed_pick = ordered_categories(outcome_list, ["c", "a"])

    assert forward == (a, c)
    assert reversed_pick == (a, c)
    assert forward == reversed_pick


def test_ordered_categories_rejects_the_same_category_picked_twice():
    """같은 결과 카테고리를 두 번 고르면 `InvalidOutcomeList`다."""
    a = OutcomeCategory(category_id="a", changes=())
    outcome_list = OutcomeList(categories=(a,), max_picks=1)
    with pytest.raises(InvalidOutcomeList):
        ordered_categories(outcome_list, ["a", "a"])


def test_retro_declaration_allowed_requires_cost_axis_and_operation():
    """허용한다면 비용 축·동작을 반드시 선언해야 한다(D-16)."""
    with pytest.raises(InvalidOutcomeList):
        RetroDeclarationDecl(allowed=True)
    with pytest.raises(InvalidOutcomeList):
        RetroDeclarationDecl(allowed=True, cost_axis="Hit Protection")
    valid = RetroDeclarationDecl(allowed=True, cost_axis="Hit Protection", operation="delta")
    assert valid.cost_axis == "Hit Protection"
    assert valid.operation == "delta"


def test_retro_declaration_not_allowed_forbids_cost_axis():
    """소급 선언을 아예 안 쓰는 룰북(`allowed=False`)이 정상값이고, 그때
    비용 축은 채울 수 없다."""
    RetroDeclarationDecl(allowed=False)  # 예외 없이 통과한다
    with pytest.raises(InvalidOutcomeList):
        RetroDeclarationDecl(allowed=False, cost_axis="Hit Protection", operation="delta")


def test_validate_outcome_list_checks_retro_declaration_cost_axis_too():
    """`RetroDeclarationDecl.cost_axis`도 축 이름·형태·동작 세 검증을
    지난다 — 존재하지 않는 축을 가리키면 거부된다."""
    rulebook = _test_rulebook_with_outcome_list(
        (ResourceAxisDecl(name="소지품", form="named_slots", slot_count=10),),
        OutcomeList(categories=()),
        retro_declaration=RetroDeclarationDecl(
            allowed=True, cost_axis="없는축", operation="fill"
        ),
    )
    with pytest.raises(InvalidOutcomeList):
        validate_outcome_list(rulebook.outcome_list, rulebook)


# ---------------------------------------------------------------------------
# 세 룰북의 실제 결과 목록·소급 선언 (RULE-13, RULE-16) — 12-04
# ---------------------------------------------------------------------------


def test_dungeonworld_outcome_list_has_at_least_four_categories_with_changes():
    """던전월드류가 결과 목록을 실제로 갖는다 — 항목마다 「축 · 동작 · 양」
    변화가 붙어 있다(변화가 빈 no-change 항목 하나는 제외)."""
    changeful = [c for c in DUNGEONWORLD_LIKE.outcome_list.categories if c.changes]
    assert len(changeful) >= 4
    for category in changeful:
        for change in category.changes:
            assert change.axis in {"체력", "방어구"}


def test_dungeonworld_outcome_list_has_exactly_one_no_change_item():
    """변화가 빈 항목이 정확히 하나(`NO_CHANGE_CATEGORY_ID`)다."""
    empty_change_categories = [
        c for c in DUNGEONWORLD_LIKE.outcome_list.categories if c.changes == ()
    ]
    assert len(empty_change_categories) == 1
    assert empty_change_categories[0].category_id == NO_CHANGE_CATEGORY_ID


def test_dungeonworld_outcome_list_absorbs_the_former_miss_hp_cost_constant():
    """12-01이 임시로 뒀던 `DUNGEONWORLD_MISS_HP_COST`(체력 -6)가 목록
    항목 안으로 흡수됐다 — 값(축·동작·양)은 그대로다."""
    category = require_outcome_category(DUNGEONWORLD_LIKE.outcome_list, "대상을 다치게 한다")
    change = category.changes[0]
    assert (change.axis, change.operation, change.amount) == ("체력", "delta", -6)


def test_openquest_outcome_list_is_empty():
    """OpenQuest는 SRD가 실패 결과를 절차로 정하지 않으므로 빈 목록이다."""
    assert OPENQUEST.outcome_list.categories == ()


def test_cairn_outcome_list_is_empty_and_registers_without_exception():
    """Cairn의 결과 목록이 빈 튜플이고 그 룰북이 예외 없이 등록된다."""
    assert CAIRN.outcome_list.categories == ()
    assert get_rulebook(CAIRN_ID) is CAIRN


def test_cairn_allows_retro_declaration_with_a_locked_cost_axis():
    """Cairn이 소급 선언을 허용하고 비용 축을 함께 선언한다(D-16, RULE-16)
    — 소지품을 세는 유일한 룰북이라 「없는 것을 쓴다」가 성립하는 유일한
    자리다."""
    assert CAIRN.retro_declaration.allowed is True
    assert CAIRN.retro_declaration.cost_axis == "Inventory"
    assert CAIRN.retro_declaration.operation == "fill"


def test_dungeonworld_does_not_declare_retro_declaration():
    """던전월드류는 소급 선언을 선언하지 않는다 — 소지품이
    `form="none", none_kind="discretionary"`라 대조할 목록 자체가 없다
    (11-CONTEXT D-09)."""
    assert DUNGEONWORLD_LIKE.retro_declaration.allowed is False
    assert DUNGEONWORLD_LIKE.retro_declaration.cost_axis is None


def test_all_three_rulebooks_pass_validate_outcome_list():
    """세 룰북 전부가 `validate_outcome_list`를 통과한다."""
    for rulebook in (DUNGEONWORLD_LIKE, OPENQUEST, CAIRN):
        validate_outcome_list(rulebook.outcome_list, rulebook)  # 예외 없이 통과한다


def test_outcome_category_declarations_have_no_korean_narration_field():
    """결과 카테고리 선언 어디에도 한국어 서술 문장을 담는 필드가 없다
    (D-11) — `OutcomeCategory`의 필드 이름 목록으로 단언한다."""
    assert {f.name for f in dataclasses.fields(OutcomeCategory)} == {"category_id", "changes"}


# ---------------------------------------------------------------------------
# 개체-룰북 축 정합성 검증 (D-01) — 11-02
# ---------------------------------------------------------------------------


def test_all_player_characters_match_their_rulebook_axes():
    """브람·나리·선·호두 넷 전부 던전월드류 축 선언을 통과한다."""
    for entity in PLAYER_CHARACTERS.values():
        validate_entity_axes(entity, get_rulebook(entity.rulebook_id))


def test_all_openquest_creatures_match_their_rulebook_axes():
    """OpenQuest 고블린·스켈레톤 둘 다 OpenQuest 축 선언을 통과한다."""
    for entity in OPENQUEST_CREATURES:
        validate_entity_axes(entity, get_rulebook(entity.rulebook_id))


def test_example_single_stat_foe_matches_its_rulebook_axes():
    """`EXAMPLE_SINGLE_STAT_FOE`가 통과한다."""
    validate_entity_axes(EXAMPLE_SINGLE_STAT_FOE, DUNGEONWORLD_LIKE)


def test_undeclared_axis_name_on_entity_is_rejected():
    """룰북이 선언하지 않은 이름의 `StatEntry`를 가진 개체는
    `EntityAxisMismatch`다."""
    entity = Entity(
        entity_id="test.undeclared_axis",
        display_name="시험용",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(StatEntry(name="존재하지 않는 축", form="numeric", current=1),),
    )
    with pytest.raises(EntityAxisMismatch):
        validate_entity_axes(entity, DUNGEONWORLD_LIKE)


def test_entity_form_must_match_declared_axis_form():
    """축은 `form="numeric"`으로 선언됐는데 개체의 `StatEntry.form`이
    다르면 `EntityAxisMismatch`다."""
    entity = Entity(
        entity_id="test.form_mismatch",
        display_name="시험용",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(StatEntry(name="체력", form="clock", current=1, max=1),),
    )
    with pytest.raises(EntityAxisMismatch):
        validate_entity_axes(entity, DUNGEONWORLD_LIKE)


def test_axis_name_comparison_is_exact_no_normalization():
    """이름 비교는 완전 일치다 — `"체력 "`(뒤 공백)은 `"체력"` 축으로
    인정되지 않는다."""
    entity = Entity(
        entity_id="test.trailing_space",
        display_name="시험용",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(StatEntry(name="체력 ", form="numeric", current=1),),
    )
    with pytest.raises(EntityAxisMismatch):
        validate_entity_axes(entity, DUNGEONWORLD_LIKE)


def test_declared_axis_not_present_on_entity_is_legal():
    """룰북이 선언한 축 중 개체가 안 가진 것은 위반이 아니다(D-04) —
    방향은 개체 → 룰북 한쪽뿐이다."""
    entity = Entity(
        entity_id="test.partial_axes",
        display_name="시험용",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(StatEntry(name="체력", form="numeric", current=10, max=10),),
    )
    validate_entity_axes(entity, DUNGEONWORLD_LIKE)  # 예외 없이 통과한다


def test_move_default_stat_must_be_a_declared_axis():
    """`MoveDecl.default_stat`이 축 목록에 없는 이름이면 `EntityAxisMismatch`다."""
    validate_move_stats(("체력", "STR"), DUNGEONWORLD_LIKE)  # 예외 없이 통과한다
    with pytest.raises(EntityAxisMismatch):
        validate_move_stats(("존재하지 않는 능력치",), DUNGEONWORLD_LIKE)


# ---------------------------------------------------------------------------
# 등록소 임포트 시점 검증 (D-15/D-01/T-11-07) — 11-02
# ---------------------------------------------------------------------------


def test_importing_rulebooks_package_runs_registration_validation():
    """`gptrpg.rulebooks`는 이미 임포트됐다(이 모듈 상단 import에서) — 그때
    죽지 않았다는 것 자체가 첫 증거이고, 재호출도 예외 없이 끝난다."""
    validate_registered_rulebooks()


def test_registration_rejects_a_shadowed_rulebook():
    """가려짐이 있는 룰북을 `RULEBOOKS`에 임시로 넣으면
    `validate_registered_rulebooks()`가 `ShadowedGradeBand`로 거부한다."""
    shadowed_rulebook = Rulebook(
        rulebook_id="test-shadowed-registration-only",
        display_name="가려짐 시험 전용",
        resolution_method=TWO_D6,
        grade_bands=(
            GradeBand(name="catch_all", counts_as_failure=True, succeeded=False, costs=False),
            GradeBand(name="strong", counts_as_failure=False, succeeded=True, costs=False, margin_at_least=0),
        ),
        resource_axes=(),
        check_trigger_mode="no_dice",
    )
    RULEBOOKS["test-shadowed-registration-only"] = shadowed_rulebook
    try:
        with pytest.raises(ShadowedGradeBand):
            validate_registered_rulebooks()
    finally:
        del RULEBOOKS["test-shadowed-registration-only"]
    validate_registered_rulebooks()  # 지운 뒤에는 다시 예외 없이 통과한다


def test_registration_rejects_a_rulebook_with_a_hole():
    """구멍이 있는 룰북을 `RULEBOOKS`에 임시로 넣으면
    `validate_registered_rulebooks()`가 `UncoveredOutcomeGap`으로 거부한다."""
    gapped_rulebook = Rulebook(
        rulebook_id="test-gapped-registration-only",
        display_name="구멍 시험 전용",
        resolution_method=TWO_D6,
        grade_bands=(GradeBand(name="success", counts_as_failure=False, succeeded=True, costs=False, margin_at_least=0),),
        resource_axes=(),
        check_trigger_mode="no_dice",
    )
    RULEBOOKS["test-gapped-registration-only"] = gapped_rulebook
    try:
        with pytest.raises(UncoveredOutcomeGap):
            validate_registered_rulebooks()
    finally:
        del RULEBOOKS["test-gapped-registration-only"]
    validate_registered_rulebooks()  # 지운 뒤에는 다시 예외 없이 통과한다


# ---------------------------------------------------------------------------
# 판정 트리거 목록 빈 값의 두 갈래 (D-12) — 11-04
# ---------------------------------------------------------------------------


def test_declared_list_mode_requires_a_non_empty_move_list():
    """`declared_list`인데 무브 목록이 비어 있으면 `InvalidTriggerMode`다 —
    던전월드류·OpenQuest처럼 실제 목록을 적은 룰북이 이 값을 쓴다."""
    with pytest.raises(InvalidTriggerMode):
        validate_trigger_mode("declared_list", move_count=0)
    validate_trigger_mode("declared_list", move_count=1)  # 예외 없이 통과한다


def test_empty_move_list_is_valid_with_gm_discretion_mode():
    """무브 목록이 빈 룰북이 `gm_discretion`(Cairn류 — 언제 굴릴지 그 자리에서
    정한다)이면 통과한다."""
    validate_trigger_mode("gm_discretion", move_count=0)  # 예외 없이 통과한다


def test_empty_move_list_is_valid_with_no_dice_mode():
    """무브 목록이 빈 룰북이 `no_dice`(이 게임은 주사위를 안 굴린다)면
    통과한다."""
    validate_trigger_mode("no_dice", move_count=0)  # 예외 없이 통과한다


def test_non_empty_move_list_rejects_no_dice_mode():
    """무브 목록이 있는데 `no_dice`면 `InvalidTriggerMode`다 — 주사위를 안
    굴리는 게임에 판정 트리거 목록이 있는 것은 모순이다."""
    with pytest.raises(InvalidTriggerMode):
        validate_trigger_mode("no_dice", move_count=1)


def test_non_empty_move_list_rejects_gm_discretion_mode():
    """무브 목록이 있는데 `gm_discretion`이면 `InvalidTriggerMode`다 — 목록이
    있다면 그 목록에서 고르는 `declared_list`여야 한다."""
    with pytest.raises(InvalidTriggerMode):
        validate_trigger_mode("gm_discretion", move_count=1)


def test_rulebook_without_check_trigger_mode_raises_type_error():
    """`check_trigger_mode`는 `resource_axes`와 같은 이유로 기본값 없는
    필수 필드다(D-06의 "빠뜨림 불가능") — 생성자 호출 자체가 `TypeError`로
    실패한다."""
    with pytest.raises(TypeError):
        Rulebook(
            rulebook_id="test-only",
            display_name="시험 전용",
            resolution_method=TWO_D6,
            grade_bands=_EMPTY_BANDS,
            resource_axes=(),
        )


def test_dungeonworld_and_openquest_declare_declared_list_mode():
    """실제 등록된 두 룰북 모두 목록을 실제로 적어 뒀으니 `declared_list`다."""
    assert DUNGEONWORLD_LIKE.check_trigger_mode == "declared_list"
    assert OPENQUEST.check_trigger_mode == "declared_list"


# ---------------------------------------------------------------------------
# 세 번째 룰북(Cairn) — 플랫폼 그릇을 안 고치고 데이터로 등록 (D-14) — 11-04
# ---------------------------------------------------------------------------


def test_third_rulebook_registers_without_platform_changes():
    """`get_rulebook("cairn")`이 `CAIRN`을 돌려주고, `named_slots` 축이
    실재하며, `StatEntry`/`GradeBand`/`Entity`의 필드 개수가 11-01이 고정한
    값 그대로다 — Cairn이 그릇의 칸을 하나도 늘리지 않았다는 증거."""
    assert get_rulebook(CAIRN_ID) is CAIRN
    assert any(axis.form == "named_slots" for axis in CAIRN.resource_axes)
    assert STAT_ENTRY_FIELD_NAMES == {
        "name",
        "form",
        "current",
        "max",
        "depleted_effect_ref",
        "slot_values",
        "tags",
        "none_kind",
    }
    assert ENTITY_FIELD_NAMES == {"entity_id", "display_name", "rulebook_id", "stats"}
    # GradeBand 필드 집합 — 12-04가 succeeded/costs 두 칸을 더했다(D-13/
    # D-14, RULE-14). 이 두 칸은 Cairn 전용 확장이 아니라 세 룰북 전부에
    # 적용되는 플랫폼 그릇 변경이다 — 그래도 Cairn의 통과/실패 두 밴드가
    # 이 일곱 필드만으로 표현된다는 것(named_slots처럼 Cairn만을 위한
    # 새 칸이 또 필요하지 않았다는 것)은 여전히 성립한다.
    assert {f for f in CAIRN_GRADE_BANDS[0].__dataclass_fields__} == {
        "name",
        "counts_as_failure",
        "succeeded",
        "costs",
        "margin_at_least",
        "margin_at_most",
        "requires_doubles",
    }


def test_cairn_move_list_is_empty_and_get_moves_returns_it():
    """`get_moves("cairn")`이 예외 없이 빈 튜플을 돌려준다 — 빈 목록이
    미완성이 아니라 정상값이다(RULE-15)."""
    assert get_moves(CAIRN_ID) == ()


def test_cairn_grade_bands_pass_validation():
    """Cairn의 통과/실패 두 밴드가 11-02의 가려짐·구멍 검증을 통과한다."""
    validate_grade_bands(CAIRN_GRADE_BANDS)  # 예외 없이 통과한다


def test_cairn_example_adventurer_matches_declared_axes():
    """`CAIRN_EXAMPLE_ADVENTURER`가 `CAIRN`이 선언한 축과 어긋나지 않는다."""
    validate_entity_axes(CAIRN_EXAMPLE_ADVENTURER, CAIRN)  # 예외 없이 통과한다


def test_cairn_inventory_axis_has_ten_named_slots():
    """`CAIRN_RESOURCE_AXES`에 `named_slots` 형태이고 `slot_count == 10`인
    축이 있다 — 10칸 소지품이 실제 데이터로 들어왔다는 증거(RULE-11)."""
    inventory_axes = [
        axis
        for axis in CAIRN_RESOURCE_AXES
        if axis.form == "named_slots" and axis.slot_count == 10
    ]
    assert len(inventory_axes) == 1


def test_cairn_declares_gm_discretion_mode():
    """Cairn은 고정 무브 목록이 없으므로 `check_trigger_mode`가
    `gm_discretion`이다(D-12) — 목록이 비었는데 `declared_list`가 아니다."""
    assert CAIRN.check_trigger_mode == "gm_discretion"


def test_all_three_rulebooks_registered():
    """`RULEBOOKS`에 정확히 세 항목(던전월드류·OpenQuest·Cairn)이 있다."""
    assert sorted(RULEBOOKS) == [CAIRN_ID, DUNGEONWORLD_LIKE_ID, OPENQUEST_ID]


def test_cairn_example_adventurer_registered_for_axis_check():
    """`CAIRN_EXAMPLE_ADVENTURER`가 등록 시점 개체 축 검사 대상에 들어 있다
    — 이미 `validate_registered_rulebooks()`가 임포트 시점에 통과했다는
    것(이 파일 상단 import)이 첫 증거이고, 여기서 다시 명시적으로 확인한다."""
    validate_registered_rulebooks()  # 예외 없이 통과한다(재확인)

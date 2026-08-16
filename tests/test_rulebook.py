"""`ResourceAxisDecl`/`Rulebook.resource_axes`의 모양과 검증, 그리고 등급
밴드의 「가려짐/구멍」 등록 검증을 확인한다(D-01, D-02, D-04, D-13, D-15).

이 파일은 11-01이 새로 만든 `ResourceAxisDecl` 신설과 `Rulebook.resource_axes`
필수화에 대한 회귀 방지 시험으로 시작해서, 11-02가 「가려짐/구멍」 검증
(D-15, QUAL-03)과 개체-룰북 축 정합성 검증(D-01) 시험을 이어 붙인다.
`tests/test_entities.py`가 `StatEntry`(개체 쪽 값 그릇)를 담당하는 것과
짝을 이뤄, 이 파일은 `Rulebook`/`ResourceAxisDecl`/`GradeBand`(룰북 쪽
선언)를 담당한다.
"""

import pytest

from gptrpg.rules_core.entities import Entity, StatEntry
from gptrpg.rules_core.rulebook import (
    TWO_D6,
    EntityAxisMismatch,
    GradeBand,
    InvalidResourceAxis,
    InvalidTriggerMode,
    ResourceAxisDecl,
    Rulebook,
    ShadowedGradeBand,
    UncoveredOutcomeGap,
    validate_entity_axes,
    validate_grade_bands,
    validate_move_stats,
    validate_trigger_mode,
)
from gptrpg.rulebooks import RULEBOOKS, get_rulebook, validate_registered_rulebooks
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
    OPENQUEST_RESOURCE_AXES,
)
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


def test_dungeonworld_resource_axes_are_all_numeric_form():
    """이 단계(11-01)는 numeric 형태 하나만 관통시킨다 — 던전월드류가
    선언한 여덟 축 전부가 아직 numeric이다. 나머지 다섯 형태는 11-03이
    붙인다."""
    assert len(DUNGEONWORLD_RESOURCE_AXES) == 8
    assert all(axis.form == "numeric" for axis in DUNGEONWORLD_RESOURCE_AXES)
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
        GradeBand(name="strong_hit", counts_as_failure=False, margin_at_least=0),
        GradeBand(name="weak_hit", counts_as_failure=False, margin_at_least=-3),
        GradeBand(name="never", counts_as_failure=False, margin_at_least=5),
        GradeBand(name="miss", counts_as_failure=True),
    )
    with pytest.raises(ShadowedGradeBand) as exc_info:
        validate_grade_bands(bands)
    assert exc_info.value.band_name == "never"


def test_hole_rejected():
    """`success`(margin>=0) 하나만 있으면 margin<0인 조합이 어느 밴드에도
    안 맞는 구멍이라 `UncoveredOutcomeGap`이다."""
    bands = (GradeBand(name="success", counts_as_failure=False, margin_at_least=0),)
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
        GradeBand(name="strong", counts_as_failure=False, margin_at_least=0),
        GradeBand(name="weak", counts_as_failure=False, margin_at_least=-3),
        GradeBand(name="miss", counts_as_failure=True),
    )
    validate_grade_bands(bands)  # 예외 없이 통과한다


def test_touching_bands_leave_no_gap():
    """앞 밴드의 상한(`margin_at_most=-1`)과 뒤 밴드의 하한(`margin_at_least=0`)이
    정확히 맞닿으면 구멍도 가려짐도 아니다."""
    bands = (
        GradeBand(name="fumble", counts_as_failure=True, margin_at_most=-1),
        GradeBand(name="success", counts_as_failure=False, margin_at_least=0),
    )
    validate_grade_bands(bands)  # 예외 없이 통과한다


def test_declaration_order_decides_shadowing():
    """같은 밴드 집합이라도 선언 순서를 뒤집으면 가려짐 판정이 달라진다 —
    `grade_for_margin`과 정확히 같은 「선언 순서 첫 매치」 규칙을 쓴다는 증거다."""
    catch_all_first = (
        GradeBand(name="catch_all", counts_as_failure=True),
        GradeBand(name="strong", counts_as_failure=False, margin_at_least=0),
    )
    with pytest.raises(ShadowedGradeBand) as exc_info:
        validate_grade_bands(catch_all_first)
    assert exc_info.value.band_name == "strong"

    catch_all_last = (
        GradeBand(name="strong", counts_as_failure=False, margin_at_least=0),
        GradeBand(name="catch_all", counts_as_failure=True),
    )
    validate_grade_bands(catch_all_last)  # 예외 없이 통과한다 — 순서를 바꾸면 결과가 바뀐다


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
            GradeBand(name="catch_all", counts_as_failure=True),
            GradeBand(name="strong", counts_as_failure=False, margin_at_least=0),
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
        grade_bands=(GradeBand(name="success", counts_as_failure=False, margin_at_least=0),),
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

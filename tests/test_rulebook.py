"""`ResourceAxisDecl`/`Rulebook.resource_axes`의 모양과 검증을 확인한다
(D-01, D-02, D-04, D-13).

이 파일은 11-01이 새로 만든 `ResourceAxisDecl` 신설과 `Rulebook.resource_axes`
필수화에 대한 회귀 방지 시험이다. `tests/test_entities.py`가 `StatEntry`(개체
쪽 값 그릇)를 담당하는 것과 짝을 이뤄, 이 파일은 `Rulebook`/`ResourceAxisDecl`
(룰북 쪽 선언)을 담당한다. 「가려짐/구멍」 검증(D-15, QUAL-03)은 이 계획의
범위 밖이다 — 11-02가 이 파일에 그 시험들을 이어 붙인다.
"""

import pytest

from gptrpg.rules_core.rulebook import (
    TWO_D6,
    GradeBand,
    InvalidResourceAxis,
    ResourceAxisDecl,
    Rulebook,
)
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE, DUNGEONWORLD_RESOURCE_AXES
from gptrpg.rulebooks.openquest import OPENQUEST, OPENQUEST_RESOURCE_AXES

_EMPTY_BANDS: tuple[GradeBand, ...] = ()


def _rulebook(resource_axes: tuple[ResourceAxisDecl, ...]) -> Rulebook:
    return Rulebook(
        rulebook_id="test-only",
        display_name="시험 전용",
        resolution_method=TWO_D6,
        grade_bands=_EMPTY_BANDS,
        resource_axes=resource_axes,
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
    assert len(OPENQUEST_RESOURCE_AXES) == 10
    assert all(axis.form == "numeric" for axis in OPENQUEST_RESOURCE_AXES)
    assert OPENQUEST.resource_axes == OPENQUEST_RESOURCE_AXES

"""적/NPC 그릇(Entity/StatEntry)의 모양과 검증을 확인한다 (D-20, D-21)."""

import dataclasses

import pytest

from gptrpg.rules_core.entities import (
    Entity,
    InvalidEntity,
    InvalidStatEntry,
    StatEntry,
)
from gptrpg.rulebooks.dungeonworld_like import (
    DUNGEONWORLD_LIKE_ID,
    EXAMPLE_SINGLE_STAT_FOE,
)
from gptrpg.rulebooks.openquest import OPENQUEST_ID
from gptrpg.rulebooks.openquest_creatures import (
    OPENQUEST_CREATURES,
    OPENQUEST_GOBLIN,
    OPENQUEST_SKELETON,
)


def test_stat_entry_field_names_are_exactly_eight():
    """이 시험의 목적은 칸 개수 자체가 아니라 「누가 몰래 칸을 늘리면 즉시
    드러난다」는 것이다(D-03) — 완전 일치, 부분집합이 아니다."""
    names = {f.name for f in dataclasses.fields(StatEntry)}
    assert names == {
        "name",
        "form",
        "current",
        "max",
        "depleted_effect_ref",
        "slot_values",
        "tags",
        "none_kind",
    }


def test_entity_field_names_are_exactly_four():
    names = {f.name for f in dataclasses.fields(Entity)}
    assert names == {"entity_id", "display_name", "rulebook_id", "stats"}


# ---------------------------------------------------------------------------
# 11-01 Task 2 — 여섯 형태 정합성 + 「값 0 / 개념 없음 / 규칙으로 안 셈」 구분
# (D-13, D-05, RULE-11, RULE-12)
# ---------------------------------------------------------------------------

_FORM_PAYLOAD_CASES: tuple[tuple[str, dict, dict], ...] = (
    # (form, 그 형태의 올바른 페이로드, 다른 형태의 페이로드를 섞은 잘못된 조합)
    ("numeric", {"current": 5}, {"current": 5, "tags": ("젖음",)}),
    ("clock", {"current": 2, "max": 4}, {"current": 2}),  # max 누락
    ("named_slots", {"slot_values": ("검", None, "물약")}, {"current": 1}),
    ("tag_list", {"tags": ()}, {"current": 1}),
    ("usage_die", {"current": 3, "max": 6}, {"tags": ()}),  # current 누락
    ("none", {"none_kind": "absent"}, {"current": 0}),  # none_kind 누락
)


@pytest.mark.parametrize("form,valid_kwargs,invalid_kwargs", _FORM_PAYLOAD_CASES)
def test_axis_form_payload_mismatch_is_rejected(form, valid_kwargs, invalid_kwargs):
    """여섯 형태 각각 — 자기 페이로드 칸만 채우면 통과하고, 다른 형태의
    페이로드를 섞으면 `InvalidStatEntry`다(Pitfall 1, T-11-01). 두 형태가
    동시에 채워진 값이 화면·판정 코드에서 `None` 역참조를 일으키는 경로를
    생성자 단계에서 막는다."""
    entry = StatEntry(name="시험축", form=form, **valid_kwargs)
    assert entry.form == form

    with pytest.raises(InvalidStatEntry):
        StatEntry(name="시험축", form=form, **invalid_kwargs)


def test_zero_value_and_absent_concept_are_different_entries():
    """`form="numeric", current=0`과 `form="none", none_kind="absent"`이
    서로 같지 않다 — 값이 0인 것과 개념 자체가 없는 것은 다른 사실이다
    (RULE-12 성공 기준 3)."""
    zero_value = StatEntry(name="마법점", form="numeric", current=0)
    absent_concept = StatEntry(name="마법점", form="none", none_kind="absent")

    assert zero_value != absent_concept
    assert zero_value.current == 0
    assert absent_concept.current is None


def test_discretionary_and_absent_are_different_none_kinds():
    """D-05의 두 갈래(`discretionary`="규칙으로 안 센다" /
    `absent`="개념 자체가 없다")가 한 값으로 뭉개지지 않는다."""
    discretionary = StatEntry(name="소지품", form="none", none_kind="discretionary")
    absent = StatEntry(name="소지품", form="none", none_kind="absent")

    assert discretionary != absent
    assert discretionary.none_kind == "discretionary"
    assert absent.none_kind == "absent"


def test_numeric_max_zero_is_valid_and_negative_max_is_rejected():
    """`max=0`인 `numeric`은 정상(RULE-11 boundary) — 0으로 나누는 자리가
    아니라 "상한이 0인 정상값"이다. `max=-1`은 여전히 거부된다."""
    entry = StatEntry(name="마법점", form="numeric", current=0, max=0)
    assert entry.max == 0

    with pytest.raises(InvalidStatEntry):
        StatEntry(name="마법점", form="numeric", current=0, max=-1)


def test_clock_current_may_equal_max_but_not_exceed_it():
    """`clock`은 원이 다 찬 상태(`current == max`)와 빈 상태(`current == 0`)가
    둘 다 정상이고, `current > max`는 거부된다(RULE-11 boundary)."""
    full = StatEntry(name="위협 시계", form="clock", current=4, max=4)
    assert full.current == full.max == 4

    empty = StatEntry(name="위협 시계", form="clock", current=0, max=4)
    assert empty.current == 0

    with pytest.raises(InvalidStatEntry):
        StatEntry(name="위협 시계", form="clock", current=5, max=4)


def test_tag_list_accepts_empty_tags():
    """`tag_list`는 태그가 하나도 없는 상태(`tags=()`)도 정상이다 — 빈
    목록이 정상값이라는 것이 RULE-15의 자원 축 쪽 대응이다."""
    entry = StatEntry(name="상태 이상", form="tag_list", tags=())
    assert entry.tags == ()


def test_entity_with_one_stat_and_entity_with_ten_stats_use_same_class():
    """개수를 막는 검사가 없다 — 한 개짜리와 열 개짜리가 같은 클래스로 만들어진다."""
    one_stat = Entity(
        entity_id="e1",
        display_name="한 칸짜리",
        rulebook_id="dungeonworld_like",
        stats=(StatEntry(name="체력", form="numeric", current=5, max=5),),
    )
    ten_stats = Entity(
        entity_id="e2",
        display_name="열 칸짜리",
        rulebook_id="openquest",
        stats=tuple(StatEntry(name=f"stat{i}", form="numeric", current=i) for i in range(10)),
    )
    assert type(one_stat) is type(ten_stats)
    assert len(one_stat.stats) == 1
    assert len(ten_stats.stats) == 10


def test_entity_with_empty_stats_tuple_is_valid():
    """상태값이 없는 NPC도 만들어진다."""
    npc = Entity(entity_id="npc1", display_name="행인", rulebook_id="dungeonworld_like", stats=())
    assert npc.stats == ()


def test_stat_entry_with_none_max_is_valid():
    """max가 None인 상태값(상한이 없는 값)이 정상이다."""
    entry = StatEntry(name="사기", form="numeric", current=3, max=None)
    assert entry.max is None


def test_stat_entry_with_zero_current_is_valid():
    """값이 0인 상태값(예: 마법점 0)은 정상이며 거부되지 않는다."""
    entry = StatEntry(name="마법점", form="numeric", current=0, max=10)
    assert entry.current == 0


def test_stat_entry_with_negative_current_is_valid():
    """current가 음수여도 거부되지 않는다 — 0 아래로 깎인 값의 뜻은 룰북이 정한다."""
    entry = StatEntry(name="체력", form="numeric", current=-3, max=10)
    assert entry.current == -3


def test_stat_entry_with_negative_max_raises():
    with pytest.raises(InvalidStatEntry):
        StatEntry(name="체력", form="numeric", current=5, max=-1)


def test_stat_entry_with_empty_name_raises():
    with pytest.raises(InvalidStatEntry):
        StatEntry(name="", form="numeric", current=5)


def test_stat_entry_with_whitespace_only_name_raises():
    with pytest.raises(InvalidStatEntry):
        StatEntry(name="   ", form="numeric", current=5)


def test_stat_entry_with_empty_depleted_effect_ref_raises():
    with pytest.raises(InvalidStatEntry):
        StatEntry(name="체력", form="numeric", current=5, depleted_effect_ref="")


def test_stat_entry_with_none_depleted_effect_ref_is_valid():
    entry = StatEntry(name="체력", form="numeric", current=5, depleted_effect_ref=None)
    assert entry.depleted_effect_ref is None


def test_entity_with_duplicate_stat_names_raises():
    with pytest.raises(InvalidEntity):
        Entity(
            entity_id="e1",
            display_name="중복 적",
            rulebook_id="dungeonworld_like",
            stats=(
                StatEntry(name="체력", form="numeric", current=5),
                StatEntry(name="체력", form="numeric", current=3),
            ),
        )


def test_entity_with_empty_entity_id_raises():
    with pytest.raises(InvalidEntity):
        Entity(entity_id="", display_name="적", rulebook_id="dungeonworld_like")


def test_entity_with_empty_display_name_raises():
    with pytest.raises(InvalidEntity):
        Entity(entity_id="e1", display_name="", rulebook_id="dungeonworld_like")


def test_entity_with_empty_rulebook_id_raises():
    with pytest.raises(InvalidEntity):
        Entity(entity_id="e1", display_name="적", rulebook_id="")


def test_stat_entry_is_frozen():
    entry = StatEntry(name="체력", form="numeric", current=5)
    with pytest.raises(Exception):  # noqa: B017 - dataclasses.FrozenInstanceError
        entry.current = 999


def test_entity_is_frozen():
    entity = Entity(entity_id="e1", display_name="적", rulebook_id="dungeonworld_like")
    with pytest.raises(Exception):  # noqa: B017 - dataclasses.FrozenInstanceError
        entity.display_name = "다른 이름"


def _find_stat(entity: Entity, name: str) -> StatEntry:
    for stat in entity.stats:
        if stat.name == name:
            return stat
    raise AssertionError(f"{entity.entity_id}에 상태값 {name!r}이 없다")


def test_openquest_creatures_have_ten_stats_each():
    """능력치 일곱 + 체력 + 마법점 + 방어점 = 열 개 (D-18, SRD 원문 그대로)."""
    assert len(OPENQUEST_GOBLIN.stats) == 10
    assert len(OPENQUEST_SKELETON.stats) == 10
    assert OPENQUEST_GOBLIN.rulebook_id == OPENQUEST_ID
    assert OPENQUEST_SKELETON.rulebook_id == OPENQUEST_ID


def test_openquest_creatures_hit_points_and_magic_points_match_srd():
    """SRD 원문 수치 — 고블린 체력 9/마법점 10, 스켈레톤 체력 8/마법점 0."""
    assert _find_stat(OPENQUEST_GOBLIN, "Hit Points").current == 9
    assert _find_stat(OPENQUEST_GOBLIN, "Magic Points").current == 10
    assert _find_stat(OPENQUEST_SKELETON, "Hit Points").current == 8
    assert _find_stat(OPENQUEST_SKELETON, "Magic Points").current == 0


def test_openquest_skeleton_int_pow_cha_and_magic_points_are_zero_and_valid():
    """스켈레톤의 마법점·지력·의지·매력이 0이고, 그 0이 거부되지 않는다."""
    for name in ("Magic Points", "INT", "POW", "CHA"):
        stat = _find_stat(OPENQUEST_SKELETON, name)
        assert stat.current == 0


def test_openquest_hit_points_have_depleted_effect_ref_but_ability_scores_do_not():
    """체력에 해당하는 상태값에는 depleted_effect_ref가 붙어 있고, 능력치에는 없다."""
    hp = _find_stat(OPENQUEST_GOBLIN, "Hit Points")
    assert hp.depleted_effect_ref is not None
    ability = _find_stat(OPENQUEST_GOBLIN, "STR")
    assert ability.depleted_effect_ref is None


def test_example_single_stat_foe_has_exactly_one_stat():
    """던전월드 계열 예시 적은 상태값이 하나뿐이고, 같은 Entity 클래스로 만들어진다."""
    assert type(EXAMPLE_SINGLE_STAT_FOE) is Entity
    assert len(EXAMPLE_SINGLE_STAT_FOE.stats) == 1
    assert EXAMPLE_SINGLE_STAT_FOE.rulebook_id == DUNGEONWORLD_LIKE_ID


def test_openquest_creatures_tuple_contains_both():
    assert OPENQUEST_CREATURES == (OPENQUEST_GOBLIN, OPENQUEST_SKELETON)


def test_mixed_stat_count_entities_iterate_without_branching():
    """상태값 하나짜리와 열 개짜리를 한 목록에 담아 순회해도 어떤 분기도 필요 없다.

    D-21의 실물 증거 — `stats` 튜플 길이만 다를 뿐, 이름으로 찾아 합계를 내는
    코드에는 룰북별 분기가 하나도 없다.
    """
    mixed_entities: tuple[Entity, ...] = (
        OPENQUEST_GOBLIN,
        OPENQUEST_SKELETON,
        EXAMPLE_SINGLE_STAT_FOE,
    )
    totals = {entity.entity_id: sum(stat.current for stat in entity.stats) for entity in mixed_entities}
    assert totals[OPENQUEST_GOBLIN.entity_id] > 0
    assert totals[OPENQUEST_SKELETON.entity_id] > 0
    assert totals[EXAMPLE_SINGLE_STAT_FOE.entity_id] == EXAMPLE_SINGLE_STAT_FOE.stats[0].current

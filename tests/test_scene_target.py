"""층 밖 지목이 시나리오의 열림/닫힘 선언대로 갈린다(Phase 13-05, SCENE-04,
D-13①②, D-14/D-15/D-16).

`turn.emerged_entities.apply_declared_target`을 `tests/test_scene_layers.py`의
`_make_actor` 패턴으로 직접 부른다 — 실제 `classify()`/AI 호출 없이, 이미
`RecordActionClassification`으로 사건에 남은 `declare_targets` 표에서
시작한다(서버가 실제로 확인/진행 시점에 하는 일과 같은 진입점).
"""

import pytest

from gptrpg.agents.context import TARGET_ABSENT_FACT
from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.scenario import OpeningDecl, ScenarioDecl, ThreatClockContent
from gptrpg.session_actor.actor import RecordActionClassification, SessionActor
from gptrpg.turn.emerged_entities import apply_declared_target
from gptrpg.turn.judgments import build_narration_facts, empty_turn_judgments


class _FixedRoller:
    def roll_d6(self) -> int:
        raise AssertionError("이 시험은 주사위를 굴리지 않는다")


def _make_actor(tmp_db_path, session_id: str = "s1") -> tuple[EventStore, SessionActor]:
    store = EventStore(tmp_db_path)
    store.initialize()
    actor = SessionActor(store, session_id, _FixedRoller())
    actor.start()
    return store, actor


def _opening() -> OpeningDecl:
    return OpeningDecl(
        who_you_are="시험용 인물들이다.",
        what_you_sense="시험용 감각 서술.",
        why_it_matters="시험용 긴박함.",
        hooks=("시험용 실마리",),
        invitation="무엇을 하시겠습니까?",
    )


def _clock() -> ThreatClockContent:
    return ThreatClockContent(
        clock_id="test",
        name="시험용 시계",
        identity="시험용 정체",
        wants="시험용 소망",
        segment_descriptions=("칸1", "칸2", "칸3", "칸4"),
        catastrophe="시험용 파국",
    )


def _scenario(*, improv_people: bool, improv_things: bool, target_check: bool = True) -> ScenarioDecl:
    return ScenarioDecl(
        scenario_id="test-target-scenario",
        display_name="시험용 시나리오",
        opening_kind="scripted",
        opening=_opening(),
        improv_people=improv_people,
        improv_things=improv_things,
        target_check=target_check,
        threat_clock=_clock(),
    )


async def _declare_and_classify_target(
    actor: SessionActor,
    *,
    name: str | None,
    presence: str,
    kind: str | None,
) -> int:
    """대상 지목 하나를 사건 두 개(선언 + 분류)로 미리 심는다 — 확인/진행
    시점에 `apply_declared_target`이 이 표를 다시 읽는다."""
    from gptrpg.session_actor.actor import DeclareAction

    declare_seq = await actor.submit(DeclareAction(player_id="bram", raw_text="아무 문장"))
    await actor.submit(
        RecordActionClassification(
            no_check=False,
            target_name=name,
            target_presence=presence,
            target_kind=kind,
            caused_by_seq=declare_seq,
        )
    )
    return declare_seq


# ---------------------------------------------------------------------------
# 허용/금지 — 사람·사물 두 축이 따로 걸린다(D-16)
# ---------------------------------------------------------------------------


async def test_improv_allowed_unknown_person_records_event_and_returns_no_facts(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    scenario = _scenario(improv_people=True, improv_things=True)
    declare_seq = await _declare_and_classify_target(
        actor, name="검은 개", presence="unknown", kind="person"
    )
    extra_facts = await apply_declared_target(
        actor, scenario=scenario, declare_seq=declare_seq, caused_by_seq=declare_seq
    )
    assert extra_facts == ()
    emerged_events = [e for e in store.read_events("s1") if e.event_type == "scene_entity_emerged"]
    assert len(emerged_events) == 1
    assert emerged_events[0].name == "검은 개"
    assert actor.state.scene_entities_emerged[0].name == "검은 개"
    await actor.stop()
    store.close()


async def test_improv_forbidden_unknown_person_records_no_event_and_returns_absent_fact(
    tmp_db_path,
):
    store, actor = _make_actor(tmp_db_path)
    scenario = _scenario(improv_people=False, improv_things=True)
    declare_seq = await _declare_and_classify_target(
        actor, name="검은 개", presence="unknown", kind="person"
    )
    extra_facts = await apply_declared_target(
        actor, scenario=scenario, declare_seq=declare_seq, caused_by_seq=declare_seq
    )
    assert extra_facts == (TARGET_ABSENT_FACT("검은 개"),)
    emerged_events = [e for e in store.read_events("s1") if e.event_type == "scene_entity_emerged"]
    assert emerged_events == []
    assert actor.state.scene_entities_emerged == ()
    await actor.stop()
    store.close()


async def test_improv_person_forbidden_thing_allowed_same_session_splits_by_kind(tmp_db_path):
    """D-16의 두 축이 실제로 갈린다 — 같은 세션에서 사람 지목은 안 쌓이고
    사물 지목은 쌓인다."""
    store, actor = _make_actor(tmp_db_path)
    scenario = _scenario(improv_people=False, improv_things=True)

    person_seq = await _declare_and_classify_target(
        actor, name="검은 개", presence="unknown", kind="person"
    )
    person_facts = await apply_declared_target(
        actor, scenario=scenario, declare_seq=person_seq, caused_by_seq=person_seq
    )
    assert person_facts == (TARGET_ABSENT_FACT("검은 개"),)

    thing_seq = await _declare_and_classify_target(
        actor, name="부서진 등불", presence="unknown", kind="thing"
    )
    thing_facts = await apply_declared_target(
        actor, scenario=scenario, declare_seq=thing_seq, caused_by_seq=thing_seq
    )
    assert thing_facts == ()

    names = [f.name for f in actor.state.scene_entities_emerged]
    assert names == ["부서진 등불"]
    await actor.stop()
    store.close()


async def test_improv_kind_none_accumulates_only_when_both_axes_open(tmp_db_path):
    """`kind=None`인 층 밖 지목은 두 축이 모두 열린 시나리오에서만
    쌓인다 — 하나라도 닫히면 임의로 person/thing 중 하나로 지어내지
    않고, 명부에도 사실에도 안 남는다(구조적 제약, EmergedEntityFold가
    kind를 person/thing 중 하나로만 받는다)."""
    store, actor = _make_actor(tmp_db_path)
    both_open = _scenario(improv_people=True, improv_things=True)
    declare_seq = await _declare_and_classify_target(
        actor, name="정체불명의 존재", presence="unknown", kind=None
    )
    facts = await apply_declared_target(
        actor, scenario=both_open, declare_seq=declare_seq, caused_by_seq=declare_seq
    )
    assert facts == ()
    assert actor.state.scene_entities_emerged == ()
    await actor.stop()
    store.close()


async def test_improv_kind_none_one_axis_closed_yields_absent_fact_not_event(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    one_closed = _scenario(improv_people=False, improv_things=True)
    declare_seq = await _declare_and_classify_target(
        actor, name="정체불명의 존재", presence="unknown", kind=None
    )
    facts = await apply_declared_target(
        actor, scenario=one_closed, declare_seq=declare_seq, caused_by_seq=declare_seq
    )
    assert facts == (TARGET_ABSENT_FACT("정체불명의 존재"),)
    assert actor.state.scene_entities_emerged == ()
    await actor.stop()
    store.close()


# ---------------------------------------------------------------------------
# adjacency / empty (SCENE-04)
# ---------------------------------------------------------------------------


async def test_known_target_records_no_event_list_size_unchanged(tmp_db_path):
    """이미 확정된 대상을 지목하면 즉흥이 발동하지 않는다 — 확정 목록에
    같은 것이 두 번 안 들어간다."""
    store, actor = _make_actor(tmp_db_path)
    scenario = _scenario(improv_people=True, improv_things=True)
    declare_seq = await _declare_and_classify_target(
        actor, name="촌장 담녹", presence="known", kind=None
    )
    facts = await apply_declared_target(
        actor, scenario=scenario, declare_seq=declare_seq, caused_by_seq=declare_seq
    )
    assert facts == ()
    assert actor.state.scene_entities_emerged == ()
    await actor.stop()
    store.close()


async def test_presence_none_yields_no_improv_no_facts(tmp_db_path):
    store, actor = _make_actor(tmp_db_path)
    scenario = _scenario(improv_people=True, improv_things=True)
    declare_seq = await _declare_and_classify_target(
        actor, name=None, presence="none", kind=None
    )
    facts = await apply_declared_target(
        actor, scenario=scenario, declare_seq=declare_seq, caused_by_seq=declare_seq
    )
    assert facts == ()
    assert actor.state.scene_entities_emerged == ()
    await actor.stop()
    store.close()


async def test_missing_declare_seq_in_declare_targets_reads_as_none(tmp_db_path):
    """판 14 미만 기록(대상 칸이 아예 없던 시절)이나 대상 검사를 안 쓰는
    시나리오에서 온 `declare_seq`는 `declare_targets`에 없다 — 「대상
    없음」으로 읽는다(모르면 어떻게 하나 규칙)."""
    store, actor = _make_actor(tmp_db_path)
    scenario = _scenario(improv_people=True, improv_things=True)
    from gptrpg.session_actor.actor import DeclareAction

    declare_seq = await actor.submit(DeclareAction(player_id="bram", raw_text="아무 문장"))
    # RecordActionClassification 자체를 안 낸다 — declare_targets에 없다.
    facts = await apply_declared_target(
        actor, scenario=scenario, declare_seq=declare_seq, caused_by_seq=declare_seq
    )
    assert facts == ()
    await actor.stop()
    store.close()


# ---------------------------------------------------------------------------
# ordering — 같은 입력 두 번
# ---------------------------------------------------------------------------


async def test_repeated_same_unknown_target_input_yields_same_order(tmp_db_path):
    """같은 입력을 두 번 넣어도 확정 목록의 순서가 같다(SCENE-04
    ordering) — 두 번째는 `EntityAlreadyEmerged`로 성공 흡수되어 목록에
    같은 이름이 두 번 들어가지 않는다."""
    store, actor = _make_actor(tmp_db_path)
    scenario = _scenario(improv_people=True, improv_things=True)

    first_seq = await _declare_and_classify_target(
        actor, name="검은 개", presence="unknown", kind="thing"
    )
    first_facts = await apply_declared_target(
        actor, scenario=scenario, declare_seq=first_seq, caused_by_seq=first_seq
    )
    order_after_first = [f.name for f in actor.state.scene_entities_emerged]

    second_seq = await _declare_and_classify_target(
        actor, name="검은 개", presence="unknown", kind="thing"
    )
    second_facts = await apply_declared_target(
        actor, scenario=scenario, declare_seq=second_seq, caused_by_seq=second_seq
    )
    order_after_second = [f.name for f in actor.state.scene_entities_emerged]

    assert first_facts == ()
    assert second_facts == ()  # EntityAlreadyEmerged는 성공으로 읽는다
    assert order_after_first == order_after_second == ["검은 개"]
    emerged_events = [e for e in store.read_events("s1") if e.event_type == "scene_entity_emerged"]
    assert len(emerged_events) == 1
    await actor.stop()
    store.close()


# ---------------------------------------------------------------------------
# D-15: 금지 갈래의 서술에 거절 문구가 없다
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("banned_phrase", ["없습니다", "다시 입력", "혹시"])
def test_target_absent_fact_has_no_system_rejection_phrasing(banned_phrase):
    fact = TARGET_ABSENT_FACT("검은 개")
    assert banned_phrase not in fact


def test_target_absent_fact_flows_into_narration_facts_via_extra_facts():
    """`build_narration_facts(..., extra_facts=...)`가 실제로 이 사실
    문장을 `NarrationFacts.facts`에 싣는다."""
    from gptrpg.agents.context import ClockState, TurnContext
    from gptrpg.rulebooks.dungeonworld_like import EXAMPLE_SINGLE_STAT_FOE

    ctx = TurnContext(
        scene_entities=(),
        party_state=(EXAMPLE_SINGLE_STAT_FOE,),
        actor_character_id=EXAMPLE_SINGLE_STAT_FOE.entity_id,
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=6),
        recent_turns=(),
    )
    fact = TARGET_ABSENT_FACT("검은 개")
    facts = build_narration_facts(
        ctx=ctx,
        check_summary="아무 판정",
        judgments=empty_turn_judgments(),
        extra_facts=(fact,),
    )
    assert fact in facts.facts


def test_build_narration_facts_default_extra_facts_is_byte_identical_regression():
    """`extra_facts` 기본값 `()`이면 기존 호출부의 결과가 한 글자도 안
    바뀐다 — 회귀 시험."""
    from gptrpg.agents.context import ClockState, TurnContext
    from gptrpg.rulebooks.dungeonworld_like import EXAMPLE_SINGLE_STAT_FOE

    ctx = TurnContext(
        scene_entities=(),
        party_state=(EXAMPLE_SINGLE_STAT_FOE,),
        actor_character_id=EXAMPLE_SINGLE_STAT_FOE.entity_id,
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=6),
        recent_turns=(),
    )
    without_kwarg = build_narration_facts(
        ctx=ctx, check_summary="아무 판정", judgments=empty_turn_judgments()
    )
    with_empty_kwarg = build_narration_facts(
        ctx=ctx, check_summary="아무 판정", judgments=empty_turn_judgments(), extra_facts=()
    )
    assert without_kwarg == with_empty_kwarg

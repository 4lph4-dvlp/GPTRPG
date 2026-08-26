"""`ScenarioDecl`/`OpeningDecl`의 구조와, 시나리오 등록소
(`gptrpg.rulebooks.scenarios`)의 등록 시점 검사를 확인한다(D-07ⓐ/D-18,
Phase 13).

`tests/test_rulebook.py`의 `test_registration_rejects_a_shadowed_rulebook`류
패턴을 그대로 따른다 — `SCENARIOS`에 깨진 시나리오를 임시로 넣고
`validate_registered_scenarios()`가 거부하는지 확인한 뒤 지운다.
"""

import dataclasses

import pytest

from gptrpg.event_log.store import EventStore
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rulebooks.lamplight_vigil import LAMPLIGHT_VIGIL, LAMPLIGHT_VIGIL_ID
from gptrpg.rulebooks.scenarios import (
    DEFAULT_SCENARIO_ID,
    SCENARIOS,
    UnknownScenario,
    get_scenario,
    validate_registered_scenarios,
)
from gptrpg.rulebooks.threat_clocks import (
    M0_THREAT_CLOCK,
    THREAT_CAST,
    THREAT_CLOCK_SEGMENT_COUNT,
    WELL_BELOW,
    WELL_BELOW_ID,
)
from gptrpg.rules_core.entities import Entity
from gptrpg.rules_core.scenario import (
    InvalidOpening,
    InvalidScenarioDecl,
    OpeningDecl,
    ScenarioDecl,
    ThreatClockContent,
    render_scripted_opening,
)
from gptrpg.turn.context import build_turn_context

# ---------------------------------------------------------------------------
# 등록소 전체 순회 — assumption-delta 불변식 시험
# ---------------------------------------------------------------------------


def test_importing_scenarios_package_runs_registration_validation():
    """`gptrpg.rulebooks.scenarios`는 이미 임포트됐다(이 모듈 상단
    import에서) — 그때 죽지 않았다는 것 자체가 첫 증거이고, 재호출도
    예외 없이 끝난다."""
    validate_registered_scenarios()


def test_every_registered_scenario_has_all_five_opening_elements_filled():
    """등록된 모든 시나리오가 다섯 요소를 채웠고 `opening_kind`가 두 값
    중 하나임을 등록소 전체 순회로 고정한다 — 여섯 번째 시나리오가 단수
    가정을 되살리면 이 시험이 즉시 빨개진다(assumption-delta 채택 불변식)."""
    assert SCENARIOS, "등록된 시나리오가 하나도 없다"
    for scenario_id, scenario in SCENARIOS.items():
        opening = scenario.opening
        assert opening.who_you_are.strip(), scenario_id
        assert opening.what_you_sense.strip(), scenario_id
        assert opening.why_it_matters.strip(), scenario_id
        assert opening.hooks, scenario_id
        assert all(hook.strip() for hook in opening.hooks), scenario_id
        assert opening.invitation.strip(), scenario_id
        assert scenario.opening_kind in ("scripted", "sketch"), scenario_id


def test_lamplight_vigil_is_registered():
    assert SCENARIOS[LAMPLIGHT_VIGIL_ID] is LAMPLIGHT_VIGIL
    assert get_scenario(LAMPLIGHT_VIGIL_ID) is LAMPLIGHT_VIGIL


def test_get_scenario_unknown_id_raises():
    with pytest.raises(UnknownScenario):
        get_scenario("no-such-scenario")


# ---------------------------------------------------------------------------
# 다섯 요소 등록 시점 검사 — 다섯 갈래(D-07ⓐ)
# ---------------------------------------------------------------------------


def _valid_opening() -> OpeningDecl:
    return OpeningDecl(
        who_you_are="당신들은 시험용 인물들이다.",
        what_you_sense="시험용 감각 서술.",
        why_it_matters="시험용 긴박함.",
        hooks=("시험용 실마리 하나",),
        invitation="무엇을 하시겠습니까?",
    )


def _valid_scenario(**overrides) -> ScenarioDecl:
    defaults = dict(
        scenario_id="test-scenario-registration-only",
        display_name="시험 전용 시나리오",
        opening_kind="scripted",
        opening=_valid_opening(),
        improv_people=False,
        improv_things=False,
        threat_clock=ThreatClockContent(
            clock_id="test",
            name="시험용 시계",
            identity="시험용 정체",
            wants="시험용 소망",
            segment_descriptions=("칸1", "칸2", "칸3", "칸4"),
            catastrophe="시험용 파국",
        ),
    )
    defaults.update(overrides)
    return ScenarioDecl(**defaults)


def _register_and_validate(scenario: ScenarioDecl) -> None:
    """`scenario`를 `SCENARIOS`에 임시로 넣고 검사한 뒤 반드시 지운다."""
    SCENARIOS[scenario.scenario_id] = scenario
    try:
        validate_registered_scenarios()
    finally:
        del SCENARIOS[scenario.scenario_id]
    validate_registered_scenarios()  # 지운 뒤에는 다시 예외 없이 통과한다


@pytest.mark.parametrize(
    "field_name,blank_value",
    [
        ("who_you_are", ""),
        ("what_you_sense", "   "),
        ("why_it_matters", ""),
        ("hooks", ()),
        ("invitation", ""),
    ],
)
def test_registration_rejects_invalid_opening_missing_one_of_five_elements(field_name, blank_value):
    """다섯 요소 중 하나라도 비면 `InvalidOpening`으로 거부된다 — 다섯
    갈래를 각각 고정한다(D-07ⓐ)."""
    opening = dataclasses.replace(_valid_opening(), **{field_name: blank_value})
    scenario = _valid_scenario(opening=opening)
    with pytest.raises(InvalidOpening):
        _register_and_validate(scenario)


def test_registration_rejects_invalid_opening_hooks_containing_a_blank_entry():
    """`hooks`가 비지 않았어도 그 안의 원소가 공백뿐이면 거부된다."""
    opening = dataclasses.replace(_valid_opening(), hooks=("실마리", "   "))
    scenario = _valid_scenario(opening=opening)
    with pytest.raises(InvalidOpening):
        _register_and_validate(scenario)


def test_registration_requires_hook_terms_for_sketch_scenarios():
    """`opening_kind == "sketch"`인데 `hook_terms`가 비었으면 거부된다 —
    메모형은 13-03의 생성 검사가 대조할 손잡이가 있어야 한다. 낭독문형에는
    요구하지 않는다."""
    opening = _valid_opening()  # hook_terms 기본값 () — sketch에는 부족하다
    scenario = _valid_scenario(opening_kind="sketch", opening=opening)
    with pytest.raises(InvalidOpening):
        _register_and_validate(scenario)

    opening_with_terms = dataclasses.replace(opening, hook_terms=("실마리",))
    scenario_with_terms = _valid_scenario(opening_kind="sketch", opening=opening_with_terms)
    # 등록된 시나리오가 lamplight_vigil(scripted) + 이 sketch 하나로
    # opening_kind가 갈리므로 형식 단조성 검사도 함께 통과해야 한다.
    _register_and_validate(scenario_with_terms)


# ---------------------------------------------------------------------------
# improv_people / improv_things / threat_clock — 「아직 선언하지 않았다」
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_name", ["improv_people", "improv_things", "threat_clock"])
def test_registration_rejects_invalid_scenario_decl_unset_declaration_fields(field_name):
    """`improv_people`/`improv_things`/`threat_clock`이 `None`이면
    `InvalidScenarioDecl`로 거부된다 — 「아직 선언하지 않았다」가 조용히
    통과하면 게임 중에 발견된다(D-18)."""
    scenario = _valid_scenario(**{field_name: None})
    with pytest.raises(InvalidScenarioDecl):
        _register_and_validate(scenario)


# ---------------------------------------------------------------------------
# cast 이름 중복
# ---------------------------------------------------------------------------


def test_registration_rejects_duplicate_cast_display_names():
    """같은 `display_name`을 가진 캐스트 둘이면 거부된다 — 대상 대조가
    어느 쪽을 고를지 정해지지 않는다."""
    duplicate_cast = (
        Entity(
            entity_id="scenario.a",
            display_name="같은이름",
            rulebook_id=DUNGEONWORLD_LIKE_ID,
        ),
        Entity(
            entity_id="scenario.b",
            display_name="같은이름",
            rulebook_id=DUNGEONWORLD_LIKE_ID,
        ),
    )
    scenario = _valid_scenario(cast=duplicate_cast)
    with pytest.raises(InvalidScenarioDecl):
        _register_and_validate(scenario)


# ---------------------------------------------------------------------------
# opening_kind 형식 단조성 — 둘 이상인데 전부 같은 종류면 거부
# ---------------------------------------------------------------------------


def test_registration_rejects_all_scenarios_sharing_one_opening_kind(monkeypatch):
    """등록된 시나리오가 둘 이상인데 `opening_kind`가 전부 같으면 거부된다
    — 형식이 낭독문형·메모형을 둘 다 받는다는 것이 검증되지 않는다
    (D-21/D-06). **13-03이 `WELL_BELOW`(sketch)를 등록해 실제 등록소가 이제
    두 종류를 갖게 됐으므로**, 이 시험이 재현하려는 "전부 같은 종류" 상태를
    만들려면 `WELL_BELOW`를 잠시 빼서 `lamplight_vigil`(scripted) 하나만
    남긴다 — `lamplight_vigil`은 `scripted`이므로 같은 종류의 시나리오
    하나를 더 등록하면 이 검사가 걸린다."""
    monkeypatch.delitem(SCENARIOS, WELL_BELOW_ID)
    scenario = _valid_scenario(opening_kind="scripted")
    with pytest.raises(InvalidScenarioDecl):
        _register_and_validate(scenario)


def test_registration_accepts_a_second_scenario_with_a_different_opening_kind():
    """`lamplight_vigil`(scripted)과 다른 종류(sketch)를 등록하면 형식
    단조성 검사를 통과한다 — 두 종류를 다 받는다는 것이 실제로 증명된다."""
    opening = dataclasses.replace(_valid_opening(), hook_terms=("실마리",))
    scenario = _valid_scenario(opening_kind="sketch", opening=opening)
    _register_and_validate(scenario)


# ---------------------------------------------------------------------------
# render_scripted_opening — 순서·구분자 고정, 한글 코드 포인트 보존
# ---------------------------------------------------------------------------


def test_render_scripted_opening_orders_and_joins_five_elements():
    opening = OpeningDecl(
        who_you_are="① 당신은 누구",
        what_you_sense="② 지금 감각",
        why_it_matters="③ 왜 중요",
        hooks=("④가 실마리 하나", "④나 실마리 둘"),
        invitation="⑤ 초대",
    )
    rendered = render_scripted_opening(opening)
    assert rendered == "\n\n".join(
        [
            "① 당신은 누구",
            "② 지금 감각",
            "③ 왜 중요",
            "④가 실마리 하나",
            "④나 실마리 둘",
            "⑤ 초대",
        ]
    )
    assert rendered.strip() != ""


def test_render_scripted_opening_preserves_korean_code_points_not_bytes():
    """오프닝 서사에 걸리는 길이 검사·자르기·예산이 있다면 한국어를
    유니코드 코드 포인트로 재고 바이트로 재지 않는다는 것을 확인한다
    (SCENE-02 encoding) — 이 함수는 애초에 자르지 않으므로, 한글이
    글자 중간에서 끊기지 않고 온전히 보존되는지를 직접 잰다. 한글 한
    글자는 UTF-8에서 3바이트다 — 바이트 상한이 새어 들어가면 글자 수가
    아니라 바이트 수 기준으로 잘려 이 단언이 깨진다."""
    long_hook = "우물" * 200  # 400 코드 포인트 = UTF-8로 1200바이트
    opening = OpeningDecl(
        who_you_are="한글 서술",
        what_you_sense="한글 감각",
        why_it_matters="한글 긴박함",
        hooks=(long_hook,),
        invitation="한글 초대",
    )
    rendered = render_scripted_opening(opening)
    assert long_hook in rendered
    assert len(long_hook) == 400  # 코드 포인트 수 — 바이트 수(1200)가 아니다
    assert rendered.count("우물") == 200


# ---------------------------------------------------------------------------
# 13-03 Task 2 — 「우물 아래의 것」이관 + 등록소가 형식 둘을 실제로 받는다
# ---------------------------------------------------------------------------


def test_well_below_is_registered_alongside_lamplight_vigil_with_a_different_kind():
    """등록소에 시나리오가 둘 있고(`WELL_BELOW`/`LAMPLIGHT_VIGIL`)
    `opening_kind`가 서로 다르다 — 형식이 낭독문형·메모형을 둘 다 받는다는
    것이 실제 데이터로 증명된다(D-21/D-06). 기본 시나리오는 `WELL_BELOW`다
    (13-03 재판단, `DEFAULT_SCENARIO_ID` 도크스트링 참고)."""
    assert SCENARIOS[WELL_BELOW_ID] is WELL_BELOW
    assert get_scenario(WELL_BELOW_ID) is WELL_BELOW
    assert WELL_BELOW.opening_kind == "sketch"
    assert LAMPLIGHT_VIGIL.opening_kind == "scripted"
    assert {s.opening_kind for s in SCENARIOS.values()} == {"scripted", "sketch"}
    assert DEFAULT_SCENARIO_ID == WELL_BELOW_ID


def test_well_below_cast_and_threat_clock_are_the_original_objects_unchanged():
    """이관이 이야기를 안 바꿨다는 증거 — `WELL_BELOW.cast`/`.threat_clock`이
    기존 `THREAT_CAST`/`M0_THREAT_CLOCK`과 **같은 객체**이고, 네 인물의
    이름이 그대로다."""
    assert WELL_BELOW.cast is THREAT_CAST
    assert WELL_BELOW.threat_clock is M0_THREAT_CLOCK
    assert [entity.display_name for entity in WELL_BELOW.cast] == [
        "촌장 담녹",
        "우물지기 이슬",
        "순찰대장 곽서리",
        "홀린 아이 나울",
    ]


def test_registration_rejects_threat_clock_segment_count_mismatch():
    """`threat_clock.segment_descriptions` 칸 수가
    `THREAT_CLOCK_SEGMENT_COUNT`와 다르면 거부된다 — 프롬프트 분모와 화면
    머리띠 분모가 어긋나는 일을 등록 시점에 막는다."""
    mismatched_clock = ThreatClockContent(
        clock_id="test",
        name="칸 수가 틀린 시계",
        identity="시험용 정체",
        wants="시험용 소망",
        segment_descriptions=("칸1", "칸2", "칸3"),  # THREAT_CLOCK_SEGMENT_COUNT(4)와 다름
        catastrophe="시험용 파국",
    )
    assert len(mismatched_clock.segment_descriptions) != THREAT_CLOCK_SEGMENT_COUNT
    scenario = _valid_scenario(threat_clock=mismatched_clock)
    with pytest.raises(InvalidScenarioDecl):
        _register_and_validate(scenario)


def test_registration_rejects_imagery_setting_over_the_imagery_layer_char_limit():
    """`imagery_setting`이 그림 층의 상한(`imagery.scene_prompt.
    MAX_PROMPT_CHARS`, 300자)을 넘으면 거부된다 — 실제 그림 생성에서 조용히
    잘리는 일을 등록 시점에 막는다."""
    from gptrpg.imagery.scene_prompt import MAX_PROMPT_CHARS

    too_long_setting = "a" * (MAX_PROMPT_CHARS + 1)
    scenario = _valid_scenario(imagery_setting=too_long_setting)
    with pytest.raises(InvalidScenarioDecl):
        _register_and_validate(scenario)


def test_build_turn_context_with_and_without_scenario_are_equivalent(tmp_path):
    """`build_turn_context(scenario=WELL_BELOW)`와 `build_turn_context()`
    (인자 없음)이 **같은 `TurnContext`를 만든다** — `WELL_BELOW`가
    `THREAT_CAST`/`M0_THREAT_CLOCK`을 그대로 참조하므로, 시나리오를 옮기기
    전후로 실행 중 동작이 하나도 안 바뀌었다는 회귀 증거다."""
    store = EventStore(str(tmp_path / "events.db"))
    store.initialize()
    try:
        session_id = "well-below-equivalence"
        without_scenario = build_turn_context(store, session_id, DUNGEONWORLD_LIKE_ID)
        with_scenario = build_turn_context(
            store, session_id, DUNGEONWORLD_LIKE_ID, scenario=WELL_BELOW
        )
        assert with_scenario == without_scenario
    finally:
        store.close()

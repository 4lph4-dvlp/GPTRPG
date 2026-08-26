"""장면 신규 대상 판단(scene_entity_judge)의 계약 시험 — D-03 (a), ARCH-05·ARCH-06
(09-03 Task 1).

`tests/test_clock_judge.py`/`tests/test_situation_judge.py`의 패턴(호출
횟수·타임아웃을 기록하는 이중체)을 그대로 빌린다.
"""

import dataclasses
import json

import pytest

from gptrpg.agents.context import (
    ContextCapExceeded,
    EntityJudgeContext,
    NEW_ENTITY_LIMIT,
    NarrationFacts,
)
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import MAX_ATTEMPTS, SCENE_ENTITY_TIMEOUT_S
from gptrpg.agents.scene_entity_judge import EntityJudgment, NewEntity, judge_new_entity
from gptrpg.rules_core.entities import Entity


def _scene_entities() -> tuple[Entity, ...]:
    return (
        Entity(entity_id="guard-1", display_name="경비병", rulebook_id="dungeonworld_like"),
    )


def _ctx(**overrides) -> EntityJudgeContext:
    base = dict(
        scene_entities=_scene_entities(),
        recent_turns=("플레이어: 문을 두드린다",),
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
    )
    base.update(overrides)
    return EntityJudgeContext(**base)


def _narration_facts(**overrides) -> NarrationFacts:
    base = dict(
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
        scene_summary="문이 부서지고 서늘한 바람이 흘러든다.",
        facts=("경비병이 쓰러졌다",),
        scene_entities=_scene_entities(),
        party_state=(),
        actor_character_id=None,
        recent_turns=("플레이어: 문을 두드린다",),
        new_entities=(),
    )
    base.update(overrides)
    return NarrationFacts(**base)


# ---------------------------------------------------------------------------
# EntityJudgeContext — 상한·필드 모양(ARCH-06)
# ---------------------------------------------------------------------------


def test_entity_judge_context_raises_when_recent_turns_exceed_limit():
    with pytest.raises(ContextCapExceeded):
        _ctx(recent_turns=tuple(f"턴 {i}" for i in range(5)))


def test_entity_judge_context_at_the_limit_does_not_raise():
    _ctx(recent_turns=tuple(f"턴 {i}" for i in range(4)))


def test_entity_judge_context_field_names_have_no_clock_or_character_state_slot():
    field_names = {f.name for f in dataclasses.fields(EntityJudgeContext)}
    assert field_names == {"scene_entities", "recent_turns", "check_summary"}
    assert "clock_state" not in field_names
    assert "character_state" not in field_names


# ---------------------------------------------------------------------------
# NarrationFacts.new_entities — 상한(ARCH-06)
# ---------------------------------------------------------------------------


def test_narration_facts_raises_when_new_entities_exceed_limit():
    with pytest.raises(ContextCapExceeded):
        _narration_facts(new_entities=tuple(f"대상 {i}" for i in range(NEW_ENTITY_LIMIT + 1)))


def test_narration_facts_at_new_entity_limit_does_not_raise():
    _narration_facts(new_entities=tuple(f"대상 {i}" for i in range(NEW_ENTITY_LIMIT)))


# ---------------------------------------------------------------------------
# judge_new_entity — D-05/ARCH-05 실패 계약 + 강건 파싱 + 상한 자르기 + 중복 제거
# ---------------------------------------------------------------------------


class _EntityJudgeStub:
    """`scene_entity_judge` 판단 시험 전용 이중체 — 호출 횟수·타임아웃을
    기록하고, `fail_times`번까지는 예외를 던진 뒤 `complete_value`를
    돌려준다."""

    name = "entity-judge-stub"

    def __init__(self, *, fail_times: int = 0, complete_value: str = "[]") -> None:
        self.fail_times = fail_times
        self.complete_value = complete_value
        self.call_count = 0
        self.timeouts: list[float] = []

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        self.call_count += 1
        self.timeouts.append(timeout_s)
        if self.call_count <= self.fail_times:
            raise RuntimeError("entity judge provider unavailable")
        return AgentResult(
            ok=True, value=self.complete_value, elapsed_ms=2, prompt_tokens=1, completion_tokens=1
        )

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise NotImplementedError("scene_entity_judge는 스트리밍하지 않는다")

    def last_result(self) -> AgentResult:
        raise NotImplementedError("이 이중체는 complete()만 시험한다")


def test_judge_new_entity_both_attempts_fail_yields_empty_judgment_without_raising():
    provider = _EntityJudgeStub(fail_times=99)
    judgment = judge_new_entity(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert isinstance(judgment, EntityJudgment)
    assert judgment.entities == ()
    assert judgment.ai.ok is False


def test_judge_new_entity_calls_provider_exactly_max_attempts_when_failing():
    provider = _EntityJudgeStub(fail_times=99)
    judge_new_entity(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert provider.call_count == MAX_ATTEMPTS


def test_judge_new_entity_uses_scene_entity_timeout():
    provider = _EntityJudgeStub()
    judge_new_entity(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert provider.timeouts == [SCENE_ENTITY_TIMEOUT_S]


def test_judge_new_entity_think_block_and_code_fence_wrapped_json_still_parses():
    raw = (
        "<think>부서진 등불이 새로 눈에 띈다</think>\n"
        '```json\n[{"name": "부서진 등불", "kind": "thing"}]\n```'
    )
    provider = _EntityJudgeStub(complete_value=raw)
    judgment = judge_new_entity(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert judgment.entities == (NewEntity(name="부서진 등불", kind="thing"),)


def test_judge_new_entity_completely_broken_response_yields_empty_judgment_not_a_crash():
    provider = _EntityJudgeStub(complete_value="이건 JSON이 전혀 아닙니다")
    judgment = judge_new_entity(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert judgment.entities == ()


def test_judge_new_entity_truncates_over_limit_to_new_entity_limit():
    over_limit = [{"name": f"대상{i}", "kind": "person"} for i in range(NEW_ENTITY_LIMIT + 2)]
    provider = _EntityJudgeStub(complete_value=json.dumps(over_limit))
    judgment = judge_new_entity(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert len(judgment.entities) == NEW_ENTITY_LIMIT


def test_judge_new_entity_skips_element_with_kind_outside_closed_list_keeps_rest():
    raw = json.dumps(
        [
            {"name": "닫힌 목록 밖", "kind": "monster"},
            {"name": "부서진 등불", "kind": "thing"},
        ]
    )
    provider = _EntityJudgeStub(complete_value=raw)
    judgment = judge_new_entity(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert judgment.entities == (NewEntity(name="부서진 등불", kind="thing"),)


def test_judge_new_entity_skips_element_missing_name_keeps_rest():
    raw = json.dumps(
        [
            {"kind": "thing"},
            {"name": "부서진 등불", "kind": "thing"},
        ]
    )
    provider = _EntityJudgeStub(complete_value=raw)
    judgment = judge_new_entity(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert judgment.entities == (NewEntity(name="부서진 등불", kind="thing"),)


def test_judge_new_entity_drops_name_already_in_scene_entities():
    raw = json.dumps(
        [
            {"name": "경비병", "kind": "person"},
            {"name": "부서진 등불", "kind": "thing"},
        ]
    )
    provider = _EntityJudgeStub(complete_value=raw)
    judgment = judge_new_entity(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert judgment.entities == (NewEntity(name="부서진 등불", kind="thing"),)


# ---------------------------------------------------------------------------
# 받는 쪽 — confirm()이 scene_entity_judge 판단을 사건으로 적립한다
# (D-13②/D-14, Phase 13-04, HTTP 통합 시험). `conftest.web_client_with_fake_provider`
# / `tests/test_web_actions.py`의 declare/confirm 도우미 패턴을 그대로 빌린다.
# ---------------------------------------------------------------------------

from conftest import FakeProvider
from conftest import select_character as _select_character_at
from gptrpg.event_log.store import EventStore
from gptrpg.rulebooks.threat_clocks import THREAT_CAST
from gptrpg.turn.context import build_turn_context

_EMERGED_SESSION_ID = "s1"


def _events(client, session_id: str = _EMERGED_SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events")
    assert response.status_code == 200
    return response.json()["events"]


def _emerged_declare_body(**overrides) -> dict:
    body = {
        "player_id": "bram",
        "character_id": "bram",
        "raw_text": "경비병을 설득해 통로를 열어 보려 한다",
    }
    body.update(overrides)
    return body


def _emerged_declare(client, **overrides):
    body = _emerged_declare_body(**overrides)
    _select_character_at(client, _EMERGED_SESSION_ID, body["character_id"])
    return client.post(f"/api/sessions/{_EMERGED_SESSION_ID}/actions/declare", json=body)


def _emerged_confirm_body(declare_seq: int, **overrides) -> dict:
    body = {
        "player_id": "bram",
        "move": "parley",
        "stat": "CHA",
        "suggestion_move": "parley",
        "suggestion_stat": "CHA",
        "confirmed": True,
        "declare_seq": declare_seq,
        "character_id": "bram",
    }
    body.update(overrides)
    return body


def _run_one_turn(client, *, raw_text: str) -> None:
    declare_response = _emerged_declare(client, raw_text=raw_text)
    assert declare_response.status_code == 200
    declare_seq = declare_response.json()["declare_seq"]
    confirm_response = client.post(
        f"/api/sessions/{_EMERGED_SESSION_ID}/actions/confirm",
        json=_emerged_confirm_body(declare_seq),
    )
    assert confirm_response.status_code == 200


def test_emerged_entity_recorded_and_present_in_next_turn_scene_entities(
    web_client_with_fake_provider, tmp_db_path
) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text="문이 열린다.")
    entity_first_turn = FakeProvider(complete_value=json.dumps([{"name": "검은 개", "kind": "thing"}]))
    entity_second_turn = FakeProvider(complete_value="[]")

    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=gm, scene_entity_judge=entity_first_turn
    ) as client:
        _run_one_turn(client, raw_text="문을 두드린다")
        events = [e for e in _events(client, _EMERGED_SESSION_ID) if e["event_type"] == "scene_entity_emerged"]
        assert len(events) == 1
        assert events[0]["name"] == "검은 개"
        assert events[0]["kind"] == "thing"

    # 다음 턴의 ctx.scene_entities에 들어 있는지 — 직접 build_turn_context를
    # 다시 불러 확인한다(D-14: 즉흥으로 생긴 것은 그 뒤로 계속 거기 있다).
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        from gptrpg.session_actor.projection import rebuild_state_from_events

        state = rebuild_state_from_events(
            _EMERGED_SESSION_ID, store.read_events(_EMERGED_SESSION_ID)
        )
        ctx = build_turn_context(
            store,
            _EMERGED_SESSION_ID,
            "dungeonworld_like",
            emerged_entities=state.scene_entities_emerged,
        )
    finally:
        store.close()

    assert "검은 개" in [e.display_name for e in ctx.scene_entities]


def test_emerged_entity_same_name_two_turns_in_a_row_records_exactly_one_event(
    web_client_with_fake_provider,
) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text="문이 열린다.")
    entity_provider = FakeProvider(
        complete_value=json.dumps([{"name": "검은 개", "kind": "thing"}])
    )

    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=gm, scene_entity_judge=entity_provider
    ) as client:
        _run_one_turn(client, raw_text="문을 두드린다")
        _run_one_turn(client, raw_text="다시 문을 두드린다")
        events = [
            e
            for e in _events(client, _EMERGED_SESSION_ID)
            if e["event_type"] == "scene_entity_emerged"
        ]

    assert len(events) == 1


def test_emerged_entity_overlapping_scenario_cast_does_not_get_recorded(
    web_client_with_fake_provider,
) -> None:
    cast_name = THREAT_CAST[0].display_name
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text="문이 열린다.")
    entity_provider = FakeProvider(
        complete_value=json.dumps([{"name": cast_name, "kind": "person"}])
    )

    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=gm, scene_entity_judge=entity_provider
    ) as client:
        _run_one_turn(client, raw_text="문을 두드린다")
        events = [
            e
            for e in _events(client, _EMERGED_SESSION_ID)
            if e["event_type"] == "scene_entity_emerged"
        ]

    assert events == []

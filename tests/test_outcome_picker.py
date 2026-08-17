"""결과 선택 판단(outcome_picker)의 계약 시험 — RULE-13, D-11, ARCH-05/06 (12-06 Task 1).

`tests/test_scene_entity_judge.py`/`tests/test_clock_judge.py`의 패턴(호출
횟수·타임아웃을 기록하는 이중체)을 그대로 빌린다.
"""

import dataclasses
import json

import pytest

from gptrpg.agents.context import ContextCapExceeded, OutcomePickerContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import MAX_ATTEMPTS, SCENE_ENTITY_TIMEOUT_S
from gptrpg.agents.outcome_picker import (
    OutcomePick,
    UnknownOutcomeCategoryFromAI,
    pick_outcome,
)
from gptrpg.rules_core.entities import StatEntry
from gptrpg.rules_core.resource_change import ResourceChangeDecl
from gptrpg.rules_core.rulebook import NO_CHANGE_CATEGORY_ID, OutcomeCategory, OutcomeList


def _category_ids() -> tuple[str, ...]:
    return ("hurts_target", NO_CHANGE_CATEGORY_ID)


def _outcome_list(*, max_picks: int = 2) -> OutcomeList:
    return OutcomeList(
        categories=(
            OutcomeCategory(
                category_id="hurts_target",
                changes=(ResourceChangeDecl(axis="체력", operation="delta", amount=-2),),
            ),
            OutcomeCategory(category_id=NO_CHANGE_CATEGORY_ID, changes=()),
        ),
        max_picks=max_picks,
    )


def _ctx(**overrides) -> OutcomePickerContext:
    base = dict(
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
        actor_stats=(StatEntry(name="체력", form="numeric", current=20, max=20),),
        recent_turns=("플레이어: 문을 두드린다",),
        category_ids=_category_ids(),
    )
    base.update(overrides)
    return OutcomePickerContext(**base)


# ---------------------------------------------------------------------------
# OutcomePickerContext — 상한·필드 모양(ARCH-06)
# ---------------------------------------------------------------------------


def test_outcome_picker_context_raises_when_recent_turns_exceed_limit():
    with pytest.raises(ContextCapExceeded):
        _ctx(recent_turns=tuple(f"턴 {i}" for i in range(5)))


def test_outcome_picker_context_at_the_limit_does_not_raise():
    _ctx(recent_turns=tuple(f"턴 {i}" for i in range(4)))


def test_outcome_picker_context_field_names_have_no_party_state_slot():
    field_names = {f.name for f in dataclasses.fields(OutcomePickerContext)}
    assert field_names == {"check_summary", "actor_stats", "recent_turns", "category_ids"}
    assert "party_state" not in field_names
    assert "clock_state" not in field_names


# ---------------------------------------------------------------------------
# pick_outcome — 두 조기 반환(모델을 아예 안 부른다)
# ---------------------------------------------------------------------------


class _OutcomePickerStub:
    """`outcome_picker` 판단 시험 전용 이중체 — 호출 횟수·타임아웃을 기록하고,
    `fail_times`번까지는 예외를 던진 뒤 `complete_value`를 돌려준다."""

    name = "outcome-picker-stub"

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
            raise RuntimeError("outcome picker provider unavailable")
        return AgentResult(
            ok=True, value=self.complete_value, elapsed_ms=2, prompt_tokens=1, completion_tokens=1
        )

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise NotImplementedError("outcome_picker는 스트리밍하지 않는다")

    def last_result(self) -> AgentResult:
        raise NotImplementedError("이 이중체는 complete()만 시험한다")


def test_pick_outcome_with_empty_outcome_list_calls_provider_zero_times():
    provider = _OutcomePickerStub()
    pick = pick_outcome(
        provider=provider,
        model="stub-model",
        ctx=_ctx(category_ids=()),
        outcome_list=OutcomeList(categories=()),
        costs=True,
        rulebook_display_name="OpenQuest",
    )
    assert pick.category_ids == ()
    assert provider.call_count == 0


def test_pick_outcome_with_costs_false_calls_provider_zero_times():
    provider = _OutcomePickerStub()
    pick = pick_outcome(
        provider=provider,
        model="stub-model",
        ctx=_ctx(),
        outcome_list=_outcome_list(),
        costs=False,
        rulebook_display_name="던전월드 계열",
    )
    assert pick.category_ids == ()
    assert provider.call_count == 0


# ---------------------------------------------------------------------------
# pick_outcome — D-05/ARCH-05 제공자 실패 계약 + 강건 파싱 + 상한 자르기
# ---------------------------------------------------------------------------


def test_pick_outcome_both_attempts_fail_yields_empty_pick_without_raising():
    provider = _OutcomePickerStub(fail_times=99)
    pick = pick_outcome(
        provider=provider,
        model="stub-model",
        ctx=_ctx(),
        outcome_list=_outcome_list(),
        costs=True,
        rulebook_display_name="던전월드 계열",
    )
    assert isinstance(pick, OutcomePick)
    assert pick.category_ids == ()
    assert pick.ai.ok is False


def test_pick_outcome_calls_provider_exactly_max_attempts_when_failing():
    provider = _OutcomePickerStub(fail_times=99)
    pick_outcome(
        provider=provider,
        model="stub-model",
        ctx=_ctx(),
        outcome_list=_outcome_list(),
        costs=True,
        rulebook_display_name="던전월드 계열",
    )
    assert provider.call_count == MAX_ATTEMPTS


def test_pick_outcome_uses_scene_entity_timeout():
    provider = _OutcomePickerStub(complete_value=json.dumps(["hurts_target"]))
    pick_outcome(
        provider=provider,
        model="stub-model",
        ctx=_ctx(),
        outcome_list=_outcome_list(),
        costs=True,
        rulebook_display_name="던전월드 계열",
    )
    assert provider.timeouts == [SCENE_ENTITY_TIMEOUT_S]


def test_pick_outcome_think_block_and_code_fence_wrapped_json_still_parses():
    raw = "<think>목표를 다치게 했다</think>\n```json\n[\"hurts_target\"]\n```"
    provider = _OutcomePickerStub(complete_value=raw)
    pick = pick_outcome(
        provider=provider,
        model="stub-model",
        ctx=_ctx(),
        outcome_list=_outcome_list(),
        costs=True,
        rulebook_display_name="던전월드 계열",
    )
    assert pick.category_ids == ("hurts_target",)


def test_pick_outcome_completely_broken_response_yields_empty_pick_not_a_crash():
    provider = _OutcomePickerStub(complete_value="이건 JSON이 전혀 아닙니다")
    pick = pick_outcome(
        provider=provider,
        model="stub-model",
        ctx=_ctx(),
        outcome_list=_outcome_list(),
        costs=True,
        rulebook_display_name="던전월드 계열",
    )
    assert pick.category_ids == ()


def test_pick_outcome_truncates_over_max_picks_to_max_picks():
    over_limit = ["hurts_target", NO_CHANGE_CATEGORY_ID, "hurts_target"]
    # max_picks=1인 목록으로 시험 — 두 개 이상 와도 하나로 잘린다.
    provider = _OutcomePickerStub(complete_value=json.dumps(over_limit))
    pick = pick_outcome(
        provider=provider,
        model="stub-model",
        ctx=_ctx(),
        outcome_list=_outcome_list(max_picks=1),
        costs=True,
        rulebook_display_name="던전월드 계열",
    )
    assert len(pick.category_ids) == 1


def test_pick_outcome_skips_non_string_element_keeps_rest():
    raw = json.dumps([{"not": "a string"}, "hurts_target"])
    provider = _OutcomePickerStub(complete_value=raw)
    pick = pick_outcome(
        provider=provider,
        model="stub-model",
        ctx=_ctx(),
        outcome_list=_outcome_list(),
        costs=True,
        rulebook_display_name="던전월드 계열",
    )
    assert pick.category_ids == ("hurts_target",)


# ---------------------------------------------------------------------------
# pick_outcome — 목록 밖 식별자는 UnknownOutcomeCategoryFromAI (T-12-27)
# ---------------------------------------------------------------------------


def test_pick_outcome_raises_unknown_outcome_category_for_id_outside_closed_list():
    provider = _OutcomePickerStub(complete_value=json.dumps(["닫힌_목록_밖"]))
    with pytest.raises(UnknownOutcomeCategoryFromAI) as excinfo:
        pick_outcome(
            provider=provider,
            model="stub-model",
            ctx=_ctx(),
            outcome_list=_outcome_list(),
            costs=True,
            rulebook_display_name="던전월드 계열",
        )
    assert excinfo.value.category_id == "닫힌_목록_밖"


def test_unknown_outcome_category_from_ai_message_does_not_contain_raw_model_string():
    raw_value = "이것은-모델이-지어낸-매우-특이한-식별자-문자열"
    exc = UnknownOutcomeCategoryFromAI(raw_value)
    assert raw_value not in str(exc)
    assert exc.category_id == raw_value

"""ARCH-04를 세 층(행동·구문·시각)에서 잡는 회귀 방지 그물 (09-03 Task 3).

**왜 구문 트리로도 보는가:** 주석·도크스트링 문구는 구문 트리에 영향을 주지
않는다 — 문자열 검색과 달리 이 검사는 설명을 고쳐 쓴다고 통과하거나 깨지지
않는다. `gather_turn_judgments`에 조건부 병렬화(`if ...: gather(...) else:
순차`)가 슬며시 들어오면, 행동 층 시험은 입력별로 다른 경로를 밟았을 때만
잡지만 구문 층 시험은 코드 모양 자체를 본다 — 어느 쪽이 먼저 깨지든 이
파일이 회귀를 놓치지 않는다.
"""

import ast
import inspect
import threading
import time

from gptrpg.agents.clock_judge import ClockSignal
from gptrpg.agents.context import ClockState, TurnContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.scene_entity_judge import EntityJudgment
from gptrpg.agents.situation_judge import SituationJudgment
from gptrpg.rules_core.entities import Entity
from gptrpg.turn import judgments as judgments_module
from gptrpg.turn.judgments import gather_turn_judgments

_EMPTY_AI = AgentResult(ok=True, value=None, elapsed_ms=1, prompt_tokens=1, completion_tokens=1)


def _ctx(**overrides) -> TurnContext:
    base = dict(
        scene_entities=(
            Entity(entity_id="guard-1", display_name="경비병", rulebook_id="dungeonworld_like"),
        ),
        party_state=(),
        actor_character_id=None,
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=4),
        recent_turns=("플레이어: 문을 두드린다",),
    )
    base.update(overrides)
    return TurnContext(**base)


class _FakeProvider:
    """`gather_turn_judgments`가 넘기는 provider 인자는 이 시험의 대역
    함수들이 아예 안 읽으므로 값 없는 자리표시자로만 쓰인다."""

    name = "unused"


# ---------------------------------------------------------------------------
# 행동 층 — 네 가지 서로 다른 입력에서 세 대역이 각각 정확히 한 번씩 불린다
# ---------------------------------------------------------------------------


def _install_counting_stubs(monkeypatch) -> dict[str, int]:
    """`gptrpg.turn.judgments` 이름공간의 세 이름을 호출 횟수를 세는 대역으로 갈아 끼운다."""
    counts = {"situation": 0, "entity": 0, "clock": 0}

    def _stub_judge_situation(*, provider, model, ctx, check_summary, rulebook_display_name, resource_axes=()):
        counts["situation"] += 1
        return SituationJudgment(scene_summary="장면.", facts=(), ai=_EMPTY_AI)

    def _stub_judge_new_entity(*, provider, model, ctx, rulebook_display_name):
        counts["entity"] += 1
        return EntityJudgment(entities=(), ai=_EMPTY_AI)

    def _stub_judge_clock_signal(*, provider, model, ctx, rulebook_display_name):
        counts["clock"] += 1
        return ClockSignal(should_check=False, why="", ai=_EMPTY_AI)

    monkeypatch.setattr(judgments_module, "judge_situation", _stub_judge_situation)
    monkeypatch.setattr(judgments_module, "judge_new_entity", _stub_judge_new_entity)
    monkeypatch.setattr(judgments_module, "judge_clock_signal", _stub_judge_clock_signal)
    return counts


async def _gather(ctx: TurnContext, check_summary: str) -> None:
    await gather_turn_judgments(
        situation_provider=_FakeProvider(),
        situation_model="stub-model",
        entity_provider=_FakeProvider(),
        entity_model="stub-model",
        clock_provider=_FakeProvider(),
        clock_model="stub-model",
        ctx=ctx,
        check_summary=check_summary,
        rulebook_display_name="던전월드 계열",
    )


async def test_each_judgment_called_exactly_once_for_ordinary_success_check(monkeypatch):
    counts = _install_counting_stubs(monkeypatch)
    await _gather(_ctx(), "hack_and_slash 판정 결과 strong_hit (목표 10)")
    assert counts == {"situation": 1, "entity": 1, "clock": 1}


async def test_each_judgment_called_exactly_once_for_failed_check(monkeypatch):
    counts = _install_counting_stubs(monkeypatch)
    await _gather(_ctx(), "hack_and_slash 판정 결과 miss (목표 10)")
    assert counts == {"situation": 1, "entity": 1, "clock": 1}


async def test_each_judgment_called_exactly_once_when_no_scene_entities(monkeypatch):
    counts = _install_counting_stubs(monkeypatch)
    await _gather(_ctx(scene_entities=()), "hack_and_slash 판정 결과 miss (목표 10)")
    assert counts == {"situation": 1, "entity": 1, "clock": 1}


async def test_each_judgment_called_exactly_once_when_recent_turns_empty(monkeypatch):
    counts = _install_counting_stubs(monkeypatch)
    await _gather(_ctx(recent_turns=()), "hack_and_slash 판정 결과 miss (목표 10)")
    assert counts == {"situation": 1, "entity": 1, "clock": 1}


# ---------------------------------------------------------------------------
# 구문 층 — gather_turn_judgments 본문에 조건 분기가 없고, asyncio.gather
# 호출이 정확히 하나이며 위치 인자가 정확히 셋, 셋 다 asyncio.to_thread다.
# ---------------------------------------------------------------------------


def _find_function_def(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"함수 {name!r}를 찾지 못했다")


def _is_attribute_call(node: ast.expr, module: str, attr: str) -> bool:
    """`module.attr(...)` 모양의 `ast.Call`인지 확인한다."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == attr
        and isinstance(func.value, ast.Name)
        and func.value.id == module
    )


def _gather_turn_judgments_source() -> str:
    return inspect.getsource(judgments_module)


def test_gather_turn_judgments_body_has_no_if_or_ternary():
    tree = ast.parse(_gather_turn_judgments_source())
    func = _find_function_def(tree, "gather_turn_judgments")
    for node in ast.walk(func):
        assert not isinstance(node, ast.If), "gather_turn_judgments 본문에 if가 있다"
        assert not isinstance(node, ast.IfExp), "gather_turn_judgments 본문에 삼항 연산자가 있다"


def test_gather_turn_judgments_has_exactly_one_gather_call_with_three_positional_args():
    tree = ast.parse(_gather_turn_judgments_source())
    func = _find_function_def(tree, "gather_turn_judgments")

    gather_calls = [
        node
        for node in ast.walk(func)
        if _is_attribute_call(node, "asyncio", "gather")
    ]
    assert len(gather_calls) == 1, f"asyncio.gather 호출이 {len(gather_calls)}개다"

    gather_call = gather_calls[0]
    assert len(gather_call.args) == 3, f"위치 인자가 {len(gather_call.args)}개다"


def test_gather_turn_judgments_all_three_gather_args_are_to_thread_calls():
    tree = ast.parse(_gather_turn_judgments_source())
    func = _find_function_def(tree, "gather_turn_judgments")

    gather_call = next(
        node for node in ast.walk(func) if _is_attribute_call(node, "asyncio", "gather")
    )
    for arg in gather_call.args:
        assert _is_attribute_call(arg, "asyncio", "to_thread"), (
            f"gather 인자가 asyncio.to_thread 호출이 아니다: {ast.dump(arg)[:80]}"
        )


# ---------------------------------------------------------------------------
# 동시성 증거 — 세 호출의 실행 구간이 실제로 겹친다(순차 실행 회귀를 잡는 그물)
# ---------------------------------------------------------------------------

_SLEEP_S = 0.05


async def test_three_judgments_actually_overlap_in_time(monkeypatch):
    starts: dict[str, float] = {}
    ends: dict[str, float] = {}
    lock = threading.Lock()

    def _record(name: str) -> None:
        with lock:
            starts[name] = time.monotonic()
        time.sleep(_SLEEP_S)
        with lock:
            ends[name] = time.monotonic()

    def _stub_judge_situation(*, provider, model, ctx, check_summary, rulebook_display_name, resource_axes=()):
        _record("situation")
        return SituationJudgment(scene_summary="", facts=(), ai=_EMPTY_AI)

    def _stub_judge_new_entity(*, provider, model, ctx, rulebook_display_name):
        _record("entity")
        return EntityJudgment(entities=(), ai=_EMPTY_AI)

    def _stub_judge_clock_signal(*, provider, model, ctx, rulebook_display_name):
        _record("clock")
        return ClockSignal(should_check=False, why="", ai=_EMPTY_AI)

    monkeypatch.setattr(judgments_module, "judge_situation", _stub_judge_situation)
    monkeypatch.setattr(judgments_module, "judge_new_entity", _stub_judge_new_entity)
    monkeypatch.setattr(judgments_module, "judge_clock_signal", _stub_judge_clock_signal)

    await _gather(_ctx(), "hack_and_slash 판정 결과 miss (목표 10)")

    assert set(starts) == {"situation", "entity", "clock"}
    assert set(ends) == {"situation", "entity", "clock"}

    # 마지막으로 시작한 대역의 시작 시각이 가장 먼저 끝난 대역의 종료 시각보다
    # 이르다 — 세 구간이 실제로 겹친다는 증거다. 순차 실행이었다면 마지막
    # 시작 시각이 항상 첫 종료 시각보다 늦다(겹침이 전혀 없다).
    last_start = max(starts.values())
    first_end = min(ends.values())
    assert last_start < first_end, "세 호출의 실행 구간이 겹치지 않는다 — 순차 실행 회귀"

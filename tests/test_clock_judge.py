"""판단 함수 층의 계약 — 판단이 두 시도 모두 실패하거나 계약을 어겨도
예외 없이 거짓 신호로 떨어진다 (09-01 Task 3, ARCH-05/D-05).

`tests/test_agents_retry.py`의 패턴(호출 횟수·타임아웃을 기록하는 이중체)을
그대로 빌린다. 소스는 고치지 않는다 — 시험이 실패하면 그때 Task 1/2의
소스를 고친다는 것이 이 태스크의 전제였고, 실제로는 전부 통과했다.
"""

from gptrpg.agents.clock_judge import (
    ClockConditionVerdict,
    ClockSignal,
    judge_clock_condition,
    judge_clock_signal,
)
from gptrpg.agents.context import ClockJudgeContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import CLOCK_JUDGE_TIMEOUT_S, MAX_ATTEMPTS


def _ctx() -> ClockJudgeContext:
    return ClockJudgeContext(
        clock_position="0/4",
        next_segment_description="우물물이 탁하게 흐려진다",
        recent_turns=(),
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
    )


class _ClockJudgeStub:
    """`clock_judge` 판단 시험 전용 이중체 — 호출 횟수·타임아웃을 기록하고,
    `fail_times`번까지는 예외를 던진 뒤 `complete_value`를 돌려준다."""

    name = "clock-judge-stub"

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
            raise RuntimeError("clock judge provider unavailable")
        return AgentResult(
            ok=True, value=self.complete_value, elapsed_ms=2, prompt_tokens=1, completion_tokens=1
        )

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise NotImplementedError("clock_judge는 스트리밍하지 않는다")

    def last_result(self) -> AgentResult:
        raise NotImplementedError("이 이중체는 complete()만 시험한다")


# ---------------------------------------------------------------------------
# judge_clock_signal
# ---------------------------------------------------------------------------


def test_judge_clock_signal_both_attempts_fail_yields_false_signal_without_raising():
    provider = _ClockJudgeStub(fail_times=99)
    signal = judge_clock_signal(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert isinstance(signal, ClockSignal)
    assert signal.should_check is False
    assert signal.ai.ok is False


def test_judge_clock_signal_calls_provider_exactly_max_attempts_when_failing():
    provider = _ClockJudgeStub(fail_times=99)
    judge_clock_signal(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert provider.call_count == MAX_ATTEMPTS


def test_judge_clock_signal_out_of_closed_list_value_falls_to_false_without_raising():
    provider = _ClockJudgeStub(complete_value='[{"signal": "예", "why": "닫힌 목록 밖 값"}]')
    signal = judge_clock_signal(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert signal.should_check is False


def test_judge_clock_signal_think_block_and_code_fence_wrapped_json_still_parses():
    raw = (
        "<think>이번 판정이 다음 칸과 관련 있어 보인다</think>\n"
        '```json\n[{"signal": "check", "why": "관련 있음"}]\n```'
    )
    provider = _ClockJudgeStub(complete_value=raw)
    signal = judge_clock_signal(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert signal.should_check is True


def test_judge_clock_signal_completely_broken_response_yields_false_signal_not_a_crash():
    provider = _ClockJudgeStub(complete_value="이건 JSON이 전혀 아닙니다")
    signal = judge_clock_signal(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert signal.should_check is False


def test_judge_clock_signal_uses_clock_judge_timeout():
    provider = _ClockJudgeStub()
    judge_clock_signal(
        provider=provider, model="stub-model", ctx=_ctx(), rulebook_display_name="던전월드 계열"
    )
    assert provider.timeouts == [CLOCK_JUDGE_TIMEOUT_S]


# ---------------------------------------------------------------------------
# judge_clock_condition
# ---------------------------------------------------------------------------


def test_judge_clock_condition_both_attempts_fail_yields_false_verdict_without_raising():
    provider = _ClockJudgeStub(fail_times=99)
    verdict = judge_clock_condition(
        provider=provider,
        model="stub-model",
        ctx=_ctx(),
        rulebook_display_name="던전월드 계열",
        narration_text="우물물이 실제로 검게 변했다.",
    )
    assert isinstance(verdict, ClockConditionVerdict)
    assert verdict.condition_met is False
    assert verdict.ai.ok is False


def test_judge_clock_condition_calls_provider_exactly_max_attempts_when_failing():
    provider = _ClockJudgeStub(fail_times=99)
    judge_clock_condition(
        provider=provider,
        model="stub-model",
        ctx=_ctx(),
        rulebook_display_name="던전월드 계열",
        narration_text="우물물이 실제로 검게 변했다.",
    )
    assert provider.call_count == MAX_ATTEMPTS


def test_judge_clock_condition_out_of_closed_list_value_falls_to_false_without_raising():
    provider = _ClockJudgeStub(complete_value='[{"verdict": "아마도", "why": "닫힌 목록 밖 값"}]')
    verdict = judge_clock_condition(
        provider=provider,
        model="stub-model",
        ctx=_ctx(),
        rulebook_display_name="던전월드 계열",
        narration_text="우물물이 실제로 검게 변했다.",
    )
    assert verdict.condition_met is False


def test_judge_clock_condition_think_block_and_code_fence_wrapped_json_still_parses():
    raw = (
        "<think>서사를 보니 조건이 충족된 것 같다</think>\n"
        '```json\n[{"verdict": "advance", "why": "조건 충족"}]\n```'
    )
    provider = _ClockJudgeStub(complete_value=raw)
    verdict = judge_clock_condition(
        provider=provider,
        model="stub-model",
        ctx=_ctx(),
        rulebook_display_name="던전월드 계열",
        narration_text="우물물이 실제로 검게 변했다.",
    )
    assert verdict.condition_met is True


def test_judge_clock_condition_completely_broken_response_yields_false_verdict_not_a_crash():
    provider = _ClockJudgeStub(complete_value="이건 JSON이 전혀 아닙니다")
    verdict = judge_clock_condition(
        provider=provider,
        model="stub-model",
        ctx=_ctx(),
        rulebook_display_name="던전월드 계열",
        narration_text="우물물이 실제로 검게 변했다.",
    )
    assert verdict.condition_met is False

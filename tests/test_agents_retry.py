"""호출 한 번을 감싸는 타임아웃·재시도 층의 시험 (03-03 Task 1·2).

`conftest.py`는 03-01 소유이므로 이 파일 안에서만 쓰는 이중체를 여기에
선언한다 — 호출 횟수를 세고 지정한 횟수만큼 지정한 예외를 던지는 작은
호출 가능 객체(Task 1)와 `Provider` 프로토콜을 구현하며 실패를 주입할 수
있는 이중체 둘(Task 2, `action_classifier`/`master_gm`용)이다.
"""

import json
from collections.abc import Callable

from gptrpg.agents.action_classifier import UnknownMove, classify
from gptrpg.agents.context import ClockState, TurnContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import CLASSIFIER_TIMEOUT_S, GM_TIMEOUT_S, MAX_ATTEMPTS, call_with_one_retry
from gptrpg.agents.master_gm import narrate
from gptrpg.rulebooks.moves import DUNGEONWORLD_LIKE_MOVES


class _CountingFailer:
    """호출 횟수를 세고, `fail_times`번까지는 지정한 예외를 던진 뒤 성공한다.

    `fail_times`가 `MAX_ATTEMPTS` 이상이면 재시도까지 전부 실패시키는
    시험에 쓰인다.
    """

    def __init__(
        self,
        *,
        fail_times: int,
        exc_factory: Callable[[], Exception] = lambda: RuntimeError("provider exploded"),
        success_result: AgentResult | None = None,
    ) -> None:
        self.fail_times = fail_times
        self.exc_factory = exc_factory
        self.success_result = success_result or AgentResult(
            ok=True, value="ok", elapsed_ms=1, prompt_tokens=3, completion_tokens=4
        )
        self.call_count = 0

    def __call__(self) -> AgentResult:
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise self.exc_factory()
        return self.success_result


def test_constants_match_locked_decisions() -> None:
    assert (CLASSIFIER_TIMEOUT_S, GM_TIMEOUT_S, MAX_ATTEMPTS) == (5.0, 15.0, 2)


def test_first_attempt_success_calls_provider_exactly_once() -> None:
    fn = _CountingFailer(fail_times=0)
    result, error_text = call_with_one_retry(fn, timeout_s=CLASSIFIER_TIMEOUT_S)
    assert fn.call_count == 1
    assert result.ok is True
    assert error_text is None


def test_first_fails_second_succeeds_calls_provider_exactly_twice() -> None:
    fn = _CountingFailer(fail_times=1)
    result, error_text = call_with_one_retry(fn, timeout_s=CLASSIFIER_TIMEOUT_S)
    assert fn.call_count == 2
    assert result.ok is True
    assert error_text is None


def test_both_attempts_fail_calls_provider_exactly_twice_never_three() -> None:
    fn = _CountingFailer(fail_times=99)
    result, error_text = call_with_one_retry(fn, timeout_s=CLASSIFIER_TIMEOUT_S)
    assert fn.call_count == 2
    assert result.ok is False
    assert error_text is not None


def test_both_failed_envelope_has_zero_tokens_and_nonnegative_elapsed() -> None:
    fn = _CountingFailer(fail_times=99)
    result, _error_text = call_with_one_retry(fn, timeout_s=CLASSIFIER_TIMEOUT_S)
    assert result.ok is False
    assert result.value is None
    assert result.elapsed_ms >= 0
    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0


def test_both_attempts_failing_prints_last_error_text_to_stderr(capsys) -> None:
    """실패 사유가 사건 기록 어디에도 안 남으므로(D-30), 표준오류로라도 남아야
    운영자가 "무브 없음"과 "호출 자체가 죽었다"를 구분할 수 있다 (03-04 Task 3
    라이브 검증에서 이 구분이 안 돼 원인 규명이 막혔다)."""
    fn = _CountingFailer(fail_times=99, exc_factory=lambda: TimeoutError("nim timed out"))
    call_with_one_retry(fn, timeout_s=CLASSIFIER_TIMEOUT_S)
    err = capsys.readouterr().err
    assert "nim timed out" in err


def test_successful_call_prints_nothing_to_stderr(capsys) -> None:
    fn = _CountingFailer(fail_times=0)
    call_with_one_retry(fn, timeout_s=CLASSIFIER_TIMEOUT_S)
    err = capsys.readouterr().err
    assert err == ""


def test_exception_kind_does_not_change_behavior_timeout_error() -> None:
    fn = _CountingFailer(fail_times=99, exc_factory=lambda: TimeoutError("too slow"))
    result, error_text = call_with_one_retry(fn, timeout_s=CLASSIFIER_TIMEOUT_S)
    assert fn.call_count == 2
    assert result.ok is False
    assert "too slow" in error_text


def test_exception_kind_does_not_change_behavior_value_error() -> None:
    fn = _CountingFailer(fail_times=99, exc_factory=lambda: ValueError("bad response"))
    result, error_text = call_with_one_retry(fn, timeout_s=CLASSIFIER_TIMEOUT_S)
    assert fn.call_count == 2
    assert result.ok is False
    assert "bad response" in error_text


def test_success_elapsed_ms_is_total_wall_clock_not_providers_own_value() -> None:
    """성공한 껍데기의 elapsed_ms는 fn()이 스스로 넣은 값이 아니라, 총 경과로 갈아 끼워진다."""
    stale = AgentResult(ok=True, value="ok", elapsed_ms=999_999, prompt_tokens=1, completion_tokens=1)
    fn = _CountingFailer(fail_times=0, success_result=stale)
    result, _error_text = call_with_one_retry(fn, timeout_s=CLASSIFIER_TIMEOUT_S)
    assert result.elapsed_ms != 999_999
    assert result.elapsed_ms >= 0


# ---------------------------------------------------------------------------
# Task 2: 두 에이전트를 타임아웃·재시도 층 뒤로 옮기고, 실패를 「무브 없음」으로
# 떨어뜨린다 — action_classifier/master_gm 전용 이중체와 시험.
# ---------------------------------------------------------------------------


class _FailingCompleteProvider:
    """`classify()` 시험용 — `complete()`이 처음 `fail_times`번 예외를 던진 뒤 성공한다."""

    name = "failing-complete"

    def __init__(self, *, fail_times: int, complete_value: str = "[]") -> None:
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
            raise RuntimeError("provider unavailable")
        return AgentResult(
            ok=True, value=self.complete_value, elapsed_ms=5, prompt_tokens=1, completion_tokens=1
        )

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise NotImplementedError("이 이중체는 complete()만 시험한다")

    def last_result(self) -> AgentResult:
        raise NotImplementedError("이 이중체는 complete()만 시험한다")


class _StreamThenFailProvider:
    """`narrate()` 시험용 — 지정한 조각을 흘려보낸 뒤 예외를 던진다(스트림 도중 실패)."""

    name = "stream-then-fail"

    def __init__(self, *, chunks: tuple[str, ...]) -> None:
        self.chunks = chunks
        self.stream_call_count = 0
        self.timeouts: list[float] = []
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        self.stream_call_count += 1
        self.timeouts.append(timeout_s)
        yield from self.chunks
        raise RuntimeError("stream interrupted")

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def _blank_ctx() -> TurnContext:
    return TurnContext(
        scene_entities=(),
        character_state=(),
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=6),
        recent_turns=(),
    )


def test_classify_falls_back_to_empty_candidates_when_provider_fails_twice() -> None:
    provider = _FailingCompleteProvider(fail_times=99)
    proposal = classify(
        provider=provider,
        model="stub-model",
        ctx=_blank_ctx(),
        raw_text="문을 두드린다",
        moves=DUNGEONWORLD_LIKE_MOVES,
        rulebook_display_name="던전월드 계열",
    )
    assert provider.call_count == 2
    assert proposal.candidates == ()
    assert proposal.ai.ok is False


def test_classify_failed_envelope_has_nonnegative_elapsed_and_zero_tokens() -> None:
    provider = _FailingCompleteProvider(fail_times=99)
    proposal = classify(
        provider=provider,
        model="stub-model",
        ctx=_blank_ctx(),
        raw_text="문을 두드린다",
        moves=DUNGEONWORLD_LIKE_MOVES,
        rulebook_display_name="던전월드 계열",
    )
    assert proposal.ai.elapsed_ms >= 0
    assert proposal.ai.prompt_tokens == 0
    assert proposal.ai.completion_tokens == 0


def test_classify_raises_unknown_move_without_retrying() -> None:
    """목록 위반은 재시도 대상이 아니다 — call_with_one_retry 밖에서 즉시 드러난다."""
    provider = _FailingCompleteProvider(
        fail_times=0, complete_value=json.dumps([{"move": "fireball", "stat": "INT"}])
    )
    try:
        classify(
            provider=provider,
            model="stub-model",
            ctx=_blank_ctx(),
            raw_text="불덩이를 던진다",
            moves=DUNGEONWORLD_LIKE_MOVES,
            rulebook_display_name="던전월드 계열",
        )
    except UnknownMove:
        pass
    else:
        raise AssertionError("UnknownMove가 뜨지 않았다")
    assert provider.call_count == 1


def test_classify_uses_classifier_timeout() -> None:
    provider = _FailingCompleteProvider(fail_times=0)
    classify(
        provider=provider,
        model="stub-model",
        ctx=_blank_ctx(),
        raw_text="문을 두드린다",
        moves=DUNGEONWORLD_LIKE_MOVES,
        rulebook_display_name="던전월드 계열",
    )
    assert provider.timeouts == [CLASSIFIER_TIMEOUT_S]


def test_narrate_uses_gm_timeout() -> None:
    provider = _StreamThenFailProvider(chunks=())
    list(
        narrate(
            provider=provider,
            model="stub-model",
            ctx=_blank_ctx(),
            check_summary="hack_and_slash 판정 결과 hit (목표 10)",
            rulebook_display_name="던전월드 계열",
        )
    )
    assert provider.timeouts and all(t == GM_TIMEOUT_S for t in provider.timeouts)


def test_narrate_mid_stream_failure_keeps_emitted_chunks_and_marks_failure() -> None:
    provider = _StreamThenFailProvider(chunks=("문이 요란하게 부서진다. ", "안에서 서늘한 바람이 흘러나온다. "))
    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            ctx=_blank_ctx(),
            check_summary="hack_and_slash 판정 결과 hit (목표 10)",
            rulebook_display_name="던전월드 계열",
        )
    )
    assert sentences == ["문이 요란하게 부서진다.", "안에서 서늘한 바람이 흘러나온다."]
    # 조각이 이미 나갔으므로 재시도하지 않는다 — stream()은 딱 한 번만 불린다
    assert provider.stream_call_count == 1
    assert provider.last_result().ok is False
